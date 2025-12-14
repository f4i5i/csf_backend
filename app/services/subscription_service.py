"""Subscription service for managing per-class recurring billing."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class, BillingModel
from app.models.enrollment import Enrollment
from app.models.order import Order
from app.models.payment import Payment, PaymentType, PaymentStatus
from app.services.stripe_service import StripeService
from core.logging import get_logger

logger = get_logger(__name__)


class SubscriptionService:
    """Service for managing per-class subscription billing."""

    def __init__(self, stripe_service: StripeService):
        self.stripe_service = stripe_service

    async def create_subscription_for_enrollment(
        self,
        db_session: AsyncSession,
        enrollment: Enrollment,
        class_: Class,
        order: Order,
        payment_method_id: str,
    ) -> Payment:
        """
        Create a subscription for a class enrollment.

        Args:
            db_session: Database session
            enrollment: Enrollment record
            class_: Class being enrolled in
            order: Order for the enrollment
            payment_method_id: Stripe payment method ID

        Returns:
            Payment record for the subscription

        Raises:
            ValueError: If class is not subscription-based
        """
        if not class_.is_subscription_based:
            raise ValueError(f"Class {class_.id} is not subscription-based")

        # Get subscription price based on billing model
        subscription_price = class_.get_subscription_price()
        if not subscription_price:
            raise ValueError(f"No subscription price set for class {class_.id}")

        # Ensure user has a Stripe customer ID
        user = enrollment.user
        if not user.stripe_customer_id:
            customer = await self.stripe_service.get_or_create_customer(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                user_id=user.id,
            )
            user.stripe_customer_id = customer
            await db_session.commit()

        # Attach payment method to customer
        try:
            await stripe.PaymentMethod.attach_async(
                payment_method_id,
                customer=user.stripe_customer_id,
            )
            # Set as default payment method
            await stripe.Customer.modify_async(
                user.stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )
        except stripe.StripeError as e:
            logger.error(f"Failed to attach payment method: {e}")
            raise ValueError(f"Failed to attach payment method: {str(e)}")

        # Get or create Stripe Price ID
        stripe_price_id = class_.get_stripe_price_id()

        if stripe_price_id:
            # Use existing Price ID from class
            logger.info(f"Using existing Stripe Price ID: {stripe_price_id}")
        else:
            # Create inline price (fallback for classes without pre-created prices)
            logger.warning(
                f"No Stripe Price ID configured for class {class_.id}. "
                f"Creating inline price. Consider running sync_class_with_stripe."
            )

            # Determine billing interval based on class billing model
            interval_map = {
                BillingModel.MONTHLY: "month",
                BillingModel.QUARTERLY: "month",  # Will set interval_count=3
                BillingModel.ANNUAL: "year",
            }
            interval = interval_map.get(class_.billing_model)
            interval_count = 3 if class_.billing_model == BillingModel.QUARTERLY else 1

            # Create product and price if needed
            if not class_.stripe_product_id:
                from app.services.stripe_product_service import StripeProductService
                product = await StripeProductService.create_product_for_class(
                    db_session, class_.id
                )
                logger.info(f"Created Stripe product {product['id']} for class {class_.id}")

            # Create price
            from app.services.stripe_product_service import StripeProductService
            price = await StripeProductService.create_price(
                product_id=class_.stripe_product_id,
                amount=subscription_price,
                currency="usd",
                interval=interval,
                interval_count=interval_count,
                metadata={
                    "class_id": class_.id,
                    "billing_model": class_.billing_model.value,
                },
            )
            stripe_price_id = price["id"]

            # Update class with new price ID
            if class_.billing_model == BillingModel.MONTHLY:
                class_.stripe_monthly_price_id = stripe_price_id
            elif class_.billing_model == BillingModel.QUARTERLY:
                class_.stripe_quarterly_price_id = stripe_price_id
            elif class_.billing_model == BillingModel.ANNUAL:
                class_.stripe_annual_price_id = stripe_price_id
            await db_session.commit()
            logger.info(f"Created and linked Stripe Price ID: {stripe_price_id}")

        # Create subscription using Price ID
        try:
            subscription = await self.stripe_service.create_subscription(
                customer_id=user.stripe_customer_id,
                price_id=stripe_price_id,
                payment_method_id=payment_method_id,
                metadata={
                    "enrollment_id": enrollment.id,
                    "class_id": class_.id,
                    "child_id": enrollment.child_id,
                    "order_id": order.id,
                },
            )
        except stripe.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise ValueError(f"Failed to create subscription: {str(e)}")

        # Update enrollment with subscription details
        enrollment.stripe_subscription_id = subscription.id
        enrollment.subscription_status = subscription.status
        enrollment.current_period_start = datetime.fromtimestamp(
            subscription.current_period_start
        )
        enrollment.current_period_end = datetime.fromtimestamp(
            subscription.current_period_end
        )
        await db_session.commit()

        # Create payment record
        payment = await Payment.create_payment(
            db_session=db_session,
            order_id=order.id,
            user_id=user.id,
            payment_type=PaymentType.SUBSCRIPTION,
            status=PaymentStatus.SUCCEEDED if subscription.status == "active" else PaymentStatus.PENDING,
            amount=subscription_price,
            currency="usd",
            stripe_subscription_id=subscription.id,
            organization_id=enrollment.organization_id,
        )

        logger.info(
            f"Created subscription {subscription.id} for enrollment {enrollment.id}, "
            f"class {class_.id}, billing model {class_.billing_model.value}"
        )

        return payment

    async def cancel_subscription(
        self,
        db_session: AsyncSession,
        enrollment: Enrollment,
        cancel_immediately: bool = False,
        prorate: bool = True,
    ) -> None:
        """
        Cancel a subscription.

        Args:
            db_session: Database session
            enrollment: Enrollment with active subscription
            cancel_immediately: If True, cancel now. If False, cancel at period end.
            prorate: If canceling immediately, whether to prorate and refund

        Raises:
            ValueError: If no active subscription found
        """
        if not enrollment.stripe_subscription_id:
            raise ValueError("No active subscription to cancel")

        try:
            if cancel_immediately:
                # Cancel immediately with optional proration
                subscription = await stripe.Subscription.cancel_async(
                    enrollment.stripe_subscription_id,
                    prorate=prorate,
                )
                enrollment.subscription_status = "canceled"
                enrollment.subscription_cancelled_at = datetime.now(datetime.UTC)
                logger.info(f"Immediately canceled subscription {enrollment.stripe_subscription_id}")
            else:
                # Cancel at period end (Stripe Smart Retries will continue until then)
                subscription = await stripe.Subscription.modify_async(
                    enrollment.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
                enrollment.cancel_at_period_end = True
                enrollment.subscription_cancelled_at = datetime.now(datetime.UTC)
                logger.info(
                    f"Scheduled subscription {enrollment.stripe_subscription_id} "
                    f"for cancellation at period end"
                )

            await db_session.commit()

        except stripe.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise ValueError(f"Failed to cancel subscription: {str(e)}")

    async def reactivate_subscription(
        self,
        db_session: AsyncSession,
        enrollment: Enrollment,
    ) -> None:
        """
        Reactivate a subscription scheduled for cancellation.

        Args:
            db_session: Database session
            enrollment: Enrollment with subscription scheduled for cancellation

        Raises:
            ValueError: If subscription not scheduled for cancellation
        """
        if not enrollment.cancel_at_period_end:
            raise ValueError("Subscription is not scheduled for cancellation")

        try:
            # Remove cancellation from Stripe
            subscription = await stripe.Subscription.modify_async(
                enrollment.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            # Update enrollment
            enrollment.cancel_at_period_end = False
            enrollment.subscription_cancelled_at = None
            await db_session.commit()

            logger.info(f"Reactivated subscription {enrollment.stripe_subscription_id}")

        except stripe.StripeError as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            raise ValueError(f"Failed to reactivate subscription: {str(e)}")

    async def update_payment_method(
        self,
        db_session: AsyncSession,
        enrollment: Enrollment,
        payment_method_id: str,
    ) -> None:
        """
        Update payment method for a subscription.

        Args:
            db_session: Database session
            enrollment: Enrollment with active subscription
            payment_method_id: New payment method ID

        Raises:
            ValueError: If no active subscription found
        """
        if not enrollment.stripe_subscription_id:
            raise ValueError("No active subscription found")

        user = enrollment.user
        if not user.stripe_customer_id:
            raise ValueError("No Stripe customer ID found")

        try:
            # Attach new payment method
            await stripe.PaymentMethod.attach_async(
                payment_method_id,
                customer=user.stripe_customer_id,
            )

            # Update subscription to use new payment method
            await stripe.Subscription.modify_async(
                enrollment.stripe_subscription_id,
                default_payment_method=payment_method_id,
            )

            # Update customer default
            await stripe.Customer.modify_async(
                user.stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

            logger.info(
                f"Updated payment method for subscription {enrollment.stripe_subscription_id}"
            )

        except stripe.StripeError as e:
            logger.error(f"Failed to update payment method: {e}")
            raise ValueError(f"Failed to update payment method: {str(e)}")

    async def get_subscription_details(
        self,
        subscription_id: str,
    ) -> dict:
        """
        Get subscription details from Stripe.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription details dict
        """
        try:
            subscription = await stripe.Subscription.retrieve_async(subscription_id)
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
                "ended_at": datetime.fromtimestamp(subscription.ended_at) if subscription.ended_at else None,
                "trial_end": datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
            }
        except stripe.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {e}")
            raise ValueError(f"Failed to retrieve subscription: {str(e)}")

    async def update_enrollment_from_subscription_event(
        self,
        db_session: AsyncSession,
        subscription_id: str,
        status: str,
        period_start: Optional[int] = None,
        period_end: Optional[int] = None,
    ) -> Optional[Enrollment]:
        """
        Update enrollment from Stripe subscription webhook event.

        Args:
            db_session: Database session
            subscription_id: Stripe subscription ID
            status: New subscription status
            period_start: Current period start timestamp
            period_end: Current period end timestamp

        Returns:
            Updated enrollment or None if not found
        """
        enrollment = await Enrollment.get_by_subscription_id(db_session, subscription_id)
        if not enrollment:
            logger.warning(f"No enrollment found for subscription {subscription_id}")
            return None

        period_start_dt = datetime.fromtimestamp(period_start) if period_start else None
        period_end_dt = datetime.fromtimestamp(period_end) if period_end else None

        await enrollment.update_subscription_status(
            db_session=db_session,
            status=status,
            period_start=period_start_dt,
            period_end=period_end_dt,
        )

        logger.info(
            f"Updated enrollment {enrollment.id} from subscription event: "
            f"status={status}, period={period_start_dt} to {period_end_dt}"
        )

        return enrollment
