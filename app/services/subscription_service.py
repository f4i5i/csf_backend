"""Subscription service for managing recurring membership billing."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.user import User
from app.services.stripe_service import StripeService
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)


class SubscriptionService:
    """Service for managing membership subscriptions."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.stripe_service = StripeService()

    async def create_membership_subscription(
        self,
        user: User,
        class_id: str,
        child_id: str,
        stripe_price_id: str,
        payment_method_id: str,
    ) -> dict:
        """
        Create a recurring monthly membership subscription.

        Args:
            user: Current user
            class_id: Membership class ID
            child_id: Child being enrolled
            stripe_price_id: Stripe price ID for the subscription
            payment_method_id: Stripe payment method ID

        Returns:
            Dictionary with subscription details

        Raises:
            BadRequestException: Invalid configuration
            NotFoundException: Class or child not found
        """
        from app.models.class_ import Class
        from app.models.child import Child

        # Validate class exists
        class_ = await Class.get_by_id(self.db_session, class_id)
        if not class_:
            raise NotFoundException(f"Class {class_id} not found")

        # Validate child exists and belongs to user
        child = await Child.get_by_id(self.db_session, child_id)
        if not child or child.user_id != user.id:
            raise NotFoundException(f"Child {child_id} not found")

        # Check if already enrolled
        existing = await self.db_session.execute(
            select(Enrollment).where(
                Enrollment.child_id == child_id,
                Enrollment.class_id == class_id,
                Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING])
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException("Child is already enrolled in this class")

        # Get or create Stripe customer
        stripe_customer_id = await self.stripe_service.get_or_create_customer(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            user_id=user.id,
        )

        # Create order for subscription
        order = await Order.create_order(
            self.db_session,
            user_id=user.id,
            status=OrderStatus.PENDING_PAYMENT,
            subtotal=class_.price,
            discount_total=Decimal("0.00"),
            total=class_.price,
            stripe_customer_id=stripe_customer_id,
        )

        # Create Stripe subscription
        try:
            subscription_result = await self.stripe_service.create_subscription(
                customer_id=stripe_customer_id,
                price_id=stripe_price_id,
                payment_method_id=payment_method_id,
                metadata={
                    "order_id": order.id,
                    "user_id": user.id,
                    "child_id": child_id,
                    "class_id": class_id,
                    "subscription_type": "membership",
                },
            )
        except Exception as e:
            logger.error(f"Failed to create Stripe subscription: {e}")
            raise BadRequestException(f"Subscription setup failed: {str(e)}")

        # Create enrollment
        enrollment = Enrollment(
            id=str(uuid4()),
            user_id=user.id,
            child_id=child_id,
            class_id=class_id,
            status=EnrollmentStatus.ACTIVE,  # Active immediately for subscriptions
            enrolled_at=datetime.now(timezone.utc),
        )
        self.db_session.add(enrollment)

        # Create initial payment record
        payment = Payment(
            id=str(uuid4()),
            order_id=order.id,
            user_id=user.id,
            payment_type=PaymentType.SUBSCRIPTION,
            status=PaymentStatus.SUCCEEDED,
            amount=class_.price,
            currency="USD",
            stripe_subscription_id=subscription_result["id"],
            paid_at=datetime.now(timezone.utc),
            refund_amount=Decimal("0.00"),
        )
        self.db_session.add(payment)

        # Update order
        order.status = OrderStatus.PAID
        order.paid_at = datetime.now(timezone.utc)

        # Update class enrollment count
        class_.current_enrollment += 1

        await self.db_session.commit()

        logger.info(
            f"Created membership subscription {subscription_result['id']} "
            f"for user {user.id}, child {child_id}, class {class_id}"
        )

        return {
            "subscription_id": subscription_result["id"],
            "enrollment_id": enrollment.id,
            "order_id": order.id,
            "payment_id": payment.id,
            "status": subscription_result["status"],
            "current_period_end": subscription_result.get("current_period_end"),
        }

    async def cancel_membership_subscription(
        self,
        user: User,
        enrollment_id: str,
        is_admin: bool = False,
    ) -> Enrollment:
        """
        Cancel a membership subscription.

        Args:
            user: Current user
            enrollment_id: Enrollment ID to cancel
            is_admin: Whether user is admin

        Returns:
            Updated enrollment

        Raises:
            NotFoundException: Enrollment not found
            BadRequestException: Not a subscription or already cancelled
        """
        # Get enrollment
        enrollment = await Enrollment.get_by_id(self.db_session, enrollment_id)
        if not enrollment:
            raise NotFoundException(f"Enrollment {enrollment_id} not found")

        if not is_admin and enrollment.user_id != user.id:
            raise BadRequestException("You don't have permission to access this enrollment")

        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise BadRequestException(f"Cannot cancel {enrollment.status.value} enrollment")

        # Find subscription payment
        result = await self.db_session.execute(
            select(Payment).where(
                Payment.user_id == enrollment.user_id,
                Payment.payment_type == PaymentType.SUBSCRIPTION,
                Payment.stripe_subscription_id.isnot(None),
            ).order_by(Payment.created_at.desc()).limit(1)
        )
        payment = result.scalar_one_or_none()

        if not payment or not payment.stripe_subscription_id:
            raise BadRequestException("No active subscription found for this enrollment")

        # Cancel Stripe subscription
        try:
            await self.stripe_service.cancel_subscription(payment.stripe_subscription_id)
        except Exception as e:
            logger.error(f"Failed to cancel Stripe subscription: {e}")
            # Continue with cancellation even if Stripe fails

        # Update enrollment
        enrollment.status = EnrollmentStatus.CANCELLED
        enrollment.cancelled_at = datetime.now(timezone.utc)

        # Update class enrollment count
        from app.models.class_ import Class
        class_ = await Class.get_by_id(self.db_session, enrollment.class_id)
        if class_ and class_.current_enrollment > 0:
            class_.current_enrollment -= 1

        await self.db_session.commit()

        logger.info(f"Cancelled membership subscription for enrollment {enrollment_id}")

        return enrollment

    async def get_active_subscriptions(self, user_id: str) -> Sequence[dict]:
        """
        Get all active subscription enrollments for a user.

        Args:
            user_id: User ID

        Returns:
            List of active subscription enrollments with details
        """
        result = await self.db_session.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        enrollments = result.scalars().all()

        # Get subscription payment info for each
        subscriptions = []
        for enrollment in enrollments:
            payment_result = await self.db_session.execute(
                select(Payment).where(
                    Payment.user_id == user_id,
                    Payment.payment_type == PaymentType.SUBSCRIPTION,
                    Payment.stripe_subscription_id.isnot(None),
                ).order_by(Payment.created_at.desc()).limit(1)
            )
            payment = payment_result.scalar_one_or_none()

            if payment:
                subscriptions.append({
                    "enrollment_id": enrollment.id,
                    "child_id": enrollment.child_id,
                    "class_id": enrollment.class_id,
                    "subscription_id": payment.stripe_subscription_id,
                    "amount": str(payment.amount),
                    "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                })

        return subscriptions
