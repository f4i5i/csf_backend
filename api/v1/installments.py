"""Installment plan API endpoints for managing payment schedules."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_parent_or_admin, get_current_user
from app.models.order import Order
from app.models.payment import (
    InstallmentFrequency,
    InstallmentPayment,
    InstallmentPlan,
    InstallmentPlanStatus,
)
from app.models.user import User
from app.schemas.payment import (
    InstallmentPaymentResponse,
    InstallmentPlanCreate,
    InstallmentPlanResponse,
    InstallmentScheduleItem,
    InstallmentSchedulePreview,
    InstallmentSummaryResponse,
)
from app.services.installment_service import InstallmentService
from app.services.pricing_service import PricingService
from core.db import get_db
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/installments", tags=["Installments"])


def plan_to_response(plan: InstallmentPlan) -> InstallmentPlanResponse:
    """Convert InstallmentPlan model to response."""
    return InstallmentPlanResponse(
        id=plan.id,
        order_id=plan.order_id,
        user_id=plan.user_id,
        total_amount=plan.total_amount,
        num_installments=plan.num_installments,
        installment_amount=plan.installment_amount,
        frequency=plan.frequency.value,
        start_date=plan.start_date,
        stripe_subscription_id=plan.stripe_subscription_id,
        status=plan.status.value,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def installment_payment_to_response(
    payment: InstallmentPayment,
) -> InstallmentPaymentResponse:
    """Convert InstallmentPayment model to response."""
    return InstallmentPaymentResponse(
        id=payment.id,
        installment_plan_id=payment.installment_plan_id,
        payment_id=payment.payment_id,
        installment_number=payment.installment_number,
        due_date=payment.due_date,
        amount=payment.amount,
        status=payment.status.value,
        paid_at=payment.paid_at,
        attempt_count=payment.attempt_count,
    )


# ============== Preview Installment Schedule ==============


@router.post("/preview", response_model=InstallmentSchedulePreview)
async def preview_installment_schedule(
    order_id: str,
    num_installments: int = Query(..., ge=2, le=2),  # Max 2 installments
    frequency: str = Query(..., regex="^(weekly|biweekly|monthly)$"),
    start_date: Optional[date] = None,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentSchedulePreview:
    """
    Preview installment payment schedule before creating plan (max 2 payments).

    Shows breakdown of payment amounts and due dates.
    """
    logger.info(
        f"Preview installment schedule for order: {order_id}, user: {current_user.id}"
    )

    # Validate order exists and belongs to user
    order = await Order.get_by_id(db_session, order_id)
    if not order:
        raise NotFoundException(f"Order {order_id} not found")

    if order.user_id != current_user.id:
        raise BadRequestException("You don't have permission to access this order")

    # Set start date if not provided
    if start_date is None:
        start_date = date.today()
    elif start_date < date.today():
        raise BadRequestException("Start date cannot be in the past")

    # Calculate schedule
    schedule_items = PricingService.calculate_installment_schedule(
        total=order.total,
        num_installments=num_installments,
        start_date=start_date,
        frequency=frequency,
    )

    schedule = [
        InstallmentScheduleItem(
            installment_number=item.installment_number,
            due_date=item.due_date,
            amount=item.amount,
        )
        for item in schedule_items
    ]

    return InstallmentSchedulePreview(
        total_amount=order.total,
        num_installments=num_installments,
        frequency=frequency,
        schedule=schedule,
    )


# ============== Create Installment Plan ==============


@router.post("/", response_model=InstallmentPlanResponse)
async def create_installment_plan(
    data: InstallmentPlanCreate,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentPlanResponse:
    """
    Create an installment payment plan for an order.

    Requires:
    - Order must be in draft or pending_payment status
    - Minimum 2 installments, maximum 12
    - Each installment must be at least $10
    - Valid payment method

    Creates:
    - Stripe subscription for recurring billing
    - Installment plan record
    - Individual installment payment records
    """
    logger.info(
        f"Create installment plan for order: {data.order_id}, user: {current_user.id}"
    )

    service = InstallmentService(db_session)

    # Convert frequency string to enum
    frequency = InstallmentFrequency(data.frequency)

    plan = await service.create_installment_plan(
        user=current_user,
        order_id=data.order_id,
        num_installments=data.num_installments,
        frequency=frequency,
        payment_method_id=data.payment_method_id,
    )

    return plan_to_response(plan)


# ============== Get My Installment Plans ==============


@router.get("/my", response_model=list[InstallmentPlanResponse])
async def get_my_installment_plans(
    status: Optional[str] = Query(
        None, regex="^(active|completed|cancelled|defaulted)$"
    ),
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> list[InstallmentPlanResponse]:
    """
    Get all installment plans for current user.

    Optionally filter by status:
    - active: Currently billing
    - completed: All payments made
    - cancelled: Plan cancelled
    - defaulted: Failed after 3 attempts
    """
    logger.info(f"Get installment plans for user: {current_user.id}")

    service = InstallmentService(db_session)

    status_filter = InstallmentPlanStatus(status) if status else None

    plans = await service.list_user_installment_plans(current_user.id, status_filter)

    return [plan_to_response(plan) for plan in plans]


@router.get("/summary", response_model=InstallmentSummaryResponse)
async def get_installment_summary(
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentSummaryResponse:
    """
    Get summary of all installment plans for current user.

    Returns aggregated statistics including:
    - Count of plans by status
    - Total amount owed (sum of pending installments)
    - Next upcoming payment details
    - Total paid installments count
    """
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from decimal import Decimal

    logger.info(f"Get installment summary for user: {current_user.id}")

    # Get all installment plans for user with their payments
    stmt = (
        select(InstallmentPlan)
        .where(InstallmentPlan.user_id == current_user.id)
        .options(selectinload(InstallmentPlan.installment_payments))
    )
    result = await db_session.execute(stmt)
    plans = result.scalars().all()

    if not plans:
        # No plans - return empty summary
        return InstallmentSummaryResponse(
            active_plans_count=0,
            completed_plans_count=0,
            cancelled_plans_count=0,
            total_amount_owed=Decimal("0.00"),
            next_payment_amount=None,
            next_payment_due=None,
            total_paid_count=0,
        )

    # Initialize counters
    active_count = 0
    completed_count = 0
    cancelled_count = 0
    total_owed = Decimal("0.00")
    total_paid = 0
    next_payment_amount = None
    next_payment_due = None

    # Process each plan
    for plan in plans:
        # Count by status
        if plan.status == InstallmentPlanStatus.ACTIVE:
            active_count += 1
        elif plan.status == InstallmentPlanStatus.COMPLETED:
            completed_count += 1
        elif plan.status == InstallmentPlanStatus.CANCELLED:
            cancelled_count += 1

        # Process payments
        for payment in plan.installment_payments:
            from app.models.payment import InstallmentPaymentStatus

            if payment.status == InstallmentPaymentStatus.PAID:
                total_paid += 1
            elif payment.status == InstallmentPaymentStatus.PENDING:
                # Add to total owed
                total_owed += payment.amount

                # Check if this is the earliest upcoming payment
                if next_payment_due is None or payment.due_date < next_payment_due:
                    next_payment_due = payment.due_date
                    next_payment_amount = payment.amount

    return InstallmentSummaryResponse(
        active_plans_count=active_count,
        completed_plans_count=completed_count,
        cancelled_plans_count=cancelled_count,
        total_amount_owed=total_owed,
        next_payment_amount=next_payment_amount,
        next_payment_due=next_payment_due,
        total_paid_count=total_paid,
    )


# ============== Get Installment Plan Details ==============


@router.get("/{plan_id}", response_model=InstallmentPlanResponse)
async def get_installment_plan(
    plan_id: str,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentPlanResponse:
    """
    Get installment plan details.

    Returns plan information and payment schedule.
    """
    logger.info(f"Get installment plan: {plan_id}, user: {current_user.id}")

    service = InstallmentService(db_session)
    plan = await service.get_installment_plan(current_user, plan_id)

    return plan_to_response(plan)


# ============== Get Installment Payment Schedule ==============


@router.get("/{plan_id}/schedule", response_model=list[InstallmentPaymentResponse])
async def get_installment_schedule(
    plan_id: str,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> list[InstallmentPaymentResponse]:
    """
    Get payment schedule for an installment plan.

    Shows all installments with their status and due dates.
    """
    logger.info(
        f"Get installment schedule for plan: {plan_id}, user: {current_user.id}"
    )

    service = InstallmentService(db_session)
    plan = await service.get_installment_plan(current_user, plan_id)

    return [
        installment_payment_to_response(payment)
        for payment in plan.installment_payments
    ]


# ============== Get Upcoming Installments ==============


@router.get("/upcoming/due", response_model=list[InstallmentPaymentResponse])
async def get_upcoming_installments(
    days_ahead: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> list[InstallmentPaymentResponse]:
    """
    Get upcoming installment payments for current user.

    Args:
        days_ahead: Number of days to look ahead (1-90)

    Returns:
        List of upcoming installments sorted by due date
    """
    logger.info(
        f"Get upcoming installments for user: {current_user.id} ({days_ahead} days)"
    )

    service = InstallmentService(db_session)
    upcoming = await service.get_upcoming_installments(current_user.id, days_ahead)

    return [installment_payment_to_response(payment) for payment in upcoming]


# ============== Cancel Installment Plan ==============


@router.post("/{plan_id}/cancel", response_model=InstallmentPlanResponse)
async def cancel_installment_plan(
    plan_id: str,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentPlanResponse:
    """
    Cancel an installment plan.

    Cancels Stripe subscription and marks all pending payments as skipped.
    Already paid installments are not refunded.
    """
    logger.info(f"Cancel installment plan: {plan_id}, user: {current_user.id}")

    service = InstallmentService(db_session)
    plan = await service.cancel_installment_plan(current_user, plan_id)

    return plan_to_response(plan)


# ============== Admin Endpoints ==============


@router.get("/", response_model=list[InstallmentPlanResponse])
async def list_all_installment_plans(
    status: Optional[str] = Query(
        None, regex="^(active|completed|cancelled|defaulted)$"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> list[InstallmentPlanResponse]:
    """
    List all installment plans (Admin only).

    Supports filtering by status and pagination.
    """
    logger.info(f"Admin list installment plans (admin: {current_admin.id})")

    from sqlalchemy import select

    query = select(InstallmentPlan).order_by(InstallmentPlan.created_at.desc())

    if status:
        status_filter = InstallmentPlanStatus(status)
        query = query.where(InstallmentPlan.status == status_filter)

    query = query.limit(limit).offset(offset)

    result = await db_session.execute(query)
    plans = result.scalars().all()

    return [plan_to_response(plan) for plan in plans]


@router.post("/{plan_id}/cancel-admin", response_model=InstallmentPlanResponse)
async def cancel_installment_plan_admin(
    plan_id: str,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> InstallmentPlanResponse:
    """
    Cancel an installment plan as admin.

    Admins can cancel any installment plan.
    """
    logger.info(f"Admin cancel installment plan: {plan_id} (admin: {current_admin.id})")

    service = InstallmentService(db_session)
    plan = await service.cancel_installment_plan(
        current_admin, plan_id, is_admin=True
    )

    return plan_to_response(plan)