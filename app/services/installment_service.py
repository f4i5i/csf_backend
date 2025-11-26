"""Installment plan service for managing payment schedules."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.payment import (
    InstallmentFrequency,
    InstallmentPayment,
    InstallmentPaymentStatus,
    InstallmentPlan,
    InstallmentPlanStatus,
    Payment,
    PaymentStatus,
    PaymentType,
)
from app.models.user import User
from app.services.pricing_service import InstallmentScheduleItem, PricingService
from app.services.stripe_service import StripeService
from core.exceptions.base import BadRequestException, NotFoundException, ForbiddenException
from core.logging import get_logger

logger = get_logger(__name__)


class InstallmentService:
    """Service for managing installment payment plans."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.stripe_service = StripeService()

    async def create_installment_plan(
        self,
        user: User,
        order_id: str,
        num_installments: int,
        frequency: InstallmentFrequency,
        payment_method_id: str,
        start_date: date = None,
    ) -> InstallmentPlan:
        """
        Create an installment plan for an order.

        Args:
            user: Current user
            order_id: Order to create installment plan for
            num_installments: Number of installments (2-12)
            frequency: Payment frequency (weekly, biweekly, monthly)
            payment_method_id: Stripe payment method ID
            start_date: First installment date (default: today)

        Returns:
            Created installment plan

        Raises:
            NotFoundException: Order not found
            ForbiddenException: User doesn't own the order
            BadRequestException: Invalid installment configuration
        """
        # Validate order
        order = await Order.get_by_id(self.db_session, order_id)
        if not order:
            raise NotFoundException(f"Order {order_id} not found")

        if order.user_id != user.id:
            raise ForbiddenException("You don't have permission to access this order")

        # Validate order is not already paid
        if order.status in ["paid", "cancelled", "refunded"]:
            raise BadRequestException(
                f"Cannot create installment plan for {order.status} order"
            )

        # Validate installment count
        if num_installments < 2 or num_installments > 12:
            raise BadRequestException("Number of installments must be between 2 and 12")

        # Validate minimum amount per installment ($10)
        min_installment = Decimal("10.00")
        installment_amount = (order.total / num_installments).quantize(Decimal("0.01"))
        if installment_amount < min_installment:
            raise BadRequestException(
                f"Installment amount (${installment_amount}) is below minimum (${min_installment})"
            )

        # Set start date
        if start_date is None:
            start_date = date.today()
        elif start_date < date.today():
            raise BadRequestException("Start date cannot be in the past")

        # Get or create Stripe customer
        stripe_customer_id = order.stripe_customer_id
        if not stripe_customer_id:
            stripe_customer_id = await self.stripe_service.get_or_create_customer(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                user_id=user.id,
            )
            order.stripe_customer_id = stripe_customer_id
            await self.db_session.commit()

        # Calculate installment schedule
        schedule = PricingService.calculate_installment_schedule(
            total=order.total,
            num_installments=num_installments,
            start_date=start_date,
            frequency=frequency.value,
        )

        # Create Stripe subscription for installment billing
        interval = "week" if frequency == InstallmentFrequency.WEEKLY else "month"
        if frequency == InstallmentFrequency.BIWEEKLY:
            interval = "week"

        try:
            stripe_result = await self.stripe_service.create_installment_subscription(
                customer_id=stripe_customer_id,
                amount_cents=self.stripe_service.dollars_to_cents(installment_amount),
                num_installments=num_installments,
                interval=interval,
                payment_method_id=payment_method_id,
                metadata={
                    "order_id": order_id,
                    "user_id": user.id,
                    "installment_plan": "true",
                },
            )
        except Exception as e:
            logger.error(f"Failed to create Stripe subscription: {e}")
            raise BadRequestException(f"Payment setup failed: {str(e)}")

        # Create installment plan in database
        plan = await InstallmentPlan.create_plan(
            self.db_session,
            order_id=order_id,
            user_id=user.id,
            total_amount=order.total,
            num_installments=num_installments,
            installment_amount=installment_amount,
            frequency=frequency,
            start_date=start_date,
            stripe_subscription_id=stripe_result["id"],
            status=InstallmentPlanStatus.ACTIVE,
        )

        # Create individual installment payment records
        for item in schedule:
            await self.db_session.execute(
                InstallmentPayment.__table__.insert().values(
                    installment_plan_id=plan.id,
                    installment_number=item.installment_number,
                    due_date=item.due_date,
                    amount=item.amount,
                    status=InstallmentPaymentStatus.PENDING,
                )
            )

        await self.db_session.commit()
        await self.db_session.refresh(plan)

        # Update order status
        order.status = "partially_paid"
        await self.db_session.commit()

        logger.info(
            f"Created installment plan {plan.id} for order {order_id} "
            f"({num_installments} payments of ${installment_amount})"
        )

        return plan

    async def get_installment_plan(
        self, user: User, plan_id: str, is_admin: bool = False
    ) -> InstallmentPlan:
        """
        Get installment plan details.

        Args:
            user: Current user
            plan_id: Installment plan ID
            is_admin: Whether user is admin (can view any plan)

        Returns:
            Installment plan with payment schedule

        Raises:
            NotFoundException: Plan not found
            ForbiddenException: User doesn't own the plan
        """
        plan = await InstallmentPlan.get_by_id(self.db_session, plan_id)
        if not plan:
            raise NotFoundException(f"Installment plan {plan_id} not found")

        if not is_admin and plan.user_id != user.id:
            raise ForbiddenException(
                "You don't have permission to access this installment plan"
            )

        return plan

    async def list_user_installment_plans(
        self, user_id: str, status: InstallmentPlanStatus = None
    ) -> Sequence[InstallmentPlan]:
        """
        List all installment plans for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of installment plans
        """
        plans = await InstallmentPlan.get_by_user_id(self.db_session, user_id)

        if status:
            plans = [p for p in plans if p.status == status]

        return plans

    async def cancel_installment_plan(
        self, user: User, plan_id: str, is_admin: bool = False
    ) -> InstallmentPlan:
        """
        Cancel an installment plan.

        Args:
            user: Current user
            plan_id: Installment plan ID
            is_admin: Whether user is admin

        Returns:
            Updated installment plan

        Raises:
            NotFoundException: Plan not found
            ForbiddenException: User doesn't own the plan
            BadRequestException: Plan already cancelled/completed
        """
        plan = await self.get_installment_plan(user, plan_id, is_admin)

        if plan.status != InstallmentPlanStatus.ACTIVE:
            raise BadRequestException(
                f"Cannot cancel {plan.status.value} installment plan"
            )

        # Cancel Stripe subscription
        if plan.stripe_subscription_id:
            try:
                await self.stripe_service.cancel_subscription(
                    plan.stripe_subscription_id
                )
            except Exception as e:
                logger.error(
                    f"Failed to cancel Stripe subscription {plan.stripe_subscription_id}: {e}"
                )
                # Continue with cancellation even if Stripe fails

        # Update plan status AND cancel all pending installment payments in single transaction
        plan.status = InstallmentPlanStatus.CANCELLED

        # Access the relationship BEFORE committing to avoid greenlet errors
        for installment in plan.installment_payments:
            if installment.status == InstallmentPaymentStatus.PENDING:
                installment.status = InstallmentPaymentStatus.SKIPPED

        # Single commit for all changes
        await self.db_session.commit()

        # Refresh the plan object to avoid expired attribute access errors
        await self.db_session.refresh(plan)

        logger.info(f"Cancelled installment plan {plan_id}")

        return plan

    async def get_upcoming_installments(
        self, user_id: str, days_ahead: int = 7
    ) -> Sequence[InstallmentPayment]:
        """
        Get upcoming installment payments for a user.

        Args:
            user_id: User ID
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming installment payments
        """
        future_date = date.today() + timedelta(days=days_ahead)

        # Get all active plans for user
        plans = await InstallmentPlan.get_by_user_id(self.db_session, user_id)
        active_plans = [p for p in plans if p.status == InstallmentPlanStatus.ACTIVE]

        # Collect upcoming payments
        upcoming = []
        for plan in active_plans:
            for installment in plan.installment_payments:
                if (
                    installment.status == InstallmentPaymentStatus.PENDING
                    and installment.due_date <= future_date
                ):
                    upcoming.append(installment)

        # Sort by due date
        upcoming.sort(key=lambda x: x.due_date)

        return upcoming

    async def process_due_installments(
        self, as_of_date: date = None
    ) -> dict[str, int]:
        """
        Process all installment payments due on or before a date.

        This is typically called by a background job (Celery task).

        Args:
            as_of_date: Date to check (default: today)

        Returns:
            Dictionary with counts: {processed, succeeded, failed, skipped}
        """
        if as_of_date is None:
            as_of_date = date.today()

        due_installments = await InstallmentPayment.get_pending_due(
            self.db_session, as_of_date
        )

        processed = 0
        succeeded = 0
        failed = 0
        skipped = 0

        for installment in due_installments:
            plan = installment.installment_plan

            # Skip if plan is not active
            if plan.status != InstallmentPlanStatus.ACTIVE:
                installment.status = InstallmentPaymentStatus.SKIPPED
                skipped += 1
                continue

            processed += 1

            # Note: Actual payment processing is handled by Stripe subscription webhooks
            # This method is for reconciliation and retry logic

            # Increment attempt count
            installment.attempt_count += 1

            # After 3 failed attempts, mark plan as defaulted
            if installment.attempt_count > 3:
                plan.status = InstallmentPlanStatus.DEFAULTED
                installment.status = InstallmentPaymentStatus.FAILED
                failed += 1
                logger.warning(
                    f"Installment plan {plan.id} defaulted after 3 failed attempts"
                )

        await self.db_session.commit()

        logger.info(
            f"Processed {processed} due installments: "
            f"{succeeded} succeeded, {failed} failed, {skipped} skipped"
        )

        return {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
        }

    async def mark_installment_paid(
        self, installment_id: str, payment_id: str
    ) -> InstallmentPayment:
        """
        Mark an installment as paid (called from webhook handler).

        Args:
            installment_id: Installment payment ID
            payment_id: Associated payment record ID

        Returns:
            Updated installment payment
        """
        # Get installment using ORM query (not __table__.select())
        installment = await self.db_session.get(InstallmentPayment, installment_id)

        if not installment:
            raise NotFoundException(f"Installment payment {installment_id} not found")

        installment.status = InstallmentPaymentStatus.PAID
        installment.payment_id = payment_id
        installment.paid_at = date.today()

        await self.db_session.commit()

        # Check if plan is complete
        plan = await InstallmentPlan.get_by_id(
            self.db_session, installment.installment_plan_id
        )
        if plan and plan.is_complete:
            plan.status = InstallmentPlanStatus.COMPLETED
            await self.db_session.commit()
            logger.info(f"Installment plan {plan.id} completed")

        return installment
