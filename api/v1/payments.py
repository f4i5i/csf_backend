"""Payment API endpoints for managing payment methods and transactions."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import (
    PaymentListResponse,
    PaymentMethodListResponse,
    PaymentMethodResponse,
    PaymentResponse,
    RefundCreate,
    RefundResponse,
    SetupIntentResponse,
)
from app.services.stripe_service import stripe_service, StripeService
from core.db import get_db
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ============== Payment Methods ==============


@router.post("/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    current_user: User = Depends(get_current_user),
) -> SetupIntentResponse:
    """
    Create a SetupIntent to save a payment method.

    Returns a client_secret for Stripe Elements to collect card details.
    """
    logger.info(f"Create SetupIntent for user: {current_user.id}")

    # Get or create Stripe customer
    customer_id = await stripe_service.get_or_create_customer(
        email=current_user.email,
        name=f"{current_user.first_name} {current_user.last_name}",
        user_id=current_user.id,
    )

    # Update user's Stripe customer ID if needed
    if not current_user.stripe_customer_id:
        current_user.stripe_customer_id = customer_id

    # Create SetupIntent
    setup_intent = await stripe_service.create_setup_intent(customer_id)

    return SetupIntentResponse(
        id=setup_intent["id"],
        client_secret=setup_intent["client_secret"],
    )


@router.get("/methods", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    current_user: User = Depends(get_current_user),
) -> PaymentMethodListResponse:
    """
    List saved payment methods for the current user.

    Returns card details (brand, last4, expiration).
    """
    logger.info(f"List payment methods for user: {current_user.id}")

    if not current_user.stripe_customer_id:
        return PaymentMethodListResponse(items=[], total=0)

    methods = await stripe_service.list_payment_methods(current_user.stripe_customer_id)

    return PaymentMethodListResponse(
        items=[PaymentMethodResponse(**m) for m in methods],
        total=len(methods),
    )


@router.delete("/methods/{payment_method_id}")
async def detach_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Remove a saved payment method.

    The payment method will be detached from the customer.
    """
    logger.info(f"Detach payment method {payment_method_id} for user: {current_user.id}")

    # Verify the payment method belongs to this user
    if current_user.stripe_customer_id:
        methods = await stripe_service.list_payment_methods(current_user.stripe_customer_id)
        method_ids = [m["id"] for m in methods]

        if payment_method_id not in method_ids:
            raise NotFoundException(message="Payment method not found")

    await stripe_service.detach_payment_method(payment_method_id)

    return {"message": "Payment method removed successfully"}


# ============== Payment History ==============


@router.get("/my", response_model=PaymentListResponse)
async def list_my_payments(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """
    List all payments for the current user.

    Returns payment history including status and amounts.
    """
    logger.info(f"List payments for user: {current_user.id}")

    result = await db_session.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=len(payments),
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Get payment details by ID.

    Users can only view their own payments. Admins can view any payment.
    """
    logger.info(f"Get payment {payment_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise NotFoundException(message="Payment not found")

    # Check access
    if payment.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise NotFoundException(message="Payment not found")

    return PaymentResponse.model_validate(payment)


# ============== Refunds (Admin) ==============


@router.post("/refund", response_model=RefundResponse)
async def create_refund(
    data: RefundCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """
    Create a refund for a payment (admin only).

    Can refund full amount or specify partial refund.
    """
    logger.info(f"Create refund for payment {data.payment_id} by admin: {current_user.id}")

    # Get payment
    result = await db_session.execute(
        select(Payment).where(Payment.id == data.payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise NotFoundException(message="Payment not found")

    if not payment.stripe_payment_intent_id:
        raise BadRequestException(message="Payment cannot be refunded - no Stripe payment found")

    # Create refund
    amount_cents = None
    if data.amount:
        amount_cents = StripeService.dollars_to_cents(data.amount)

    refund = await stripe_service.create_refund(
        payment.stripe_payment_intent_id,
        amount_cents=amount_cents,
    )

    # Update payment record
    if data.amount:
        payment.refund_amount += data.amount
    else:
        payment.refund_amount = payment.amount

    from app.models.payment import PaymentStatus
    if payment.refund_amount >= payment.amount:
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED

    await db_session.commit()

    return RefundResponse(
        id=refund["id"],
        status=refund["status"],
        amount=refund["amount"],
    )


# ============== Admin Endpoints ==============


@router.get("/", response_model=PaymentListResponse)
async def list_all_payments(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """
    List all payments (admin only).

    Can filter by status.
    """
    logger.info(f"List all payments by admin: {current_user.id}")

    query = select(Payment)

    if status:
        from app.models.payment import PaymentStatus
        query = query.where(Payment.status == PaymentStatus(status))

    query = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit)

    result = await db_session.execute(query)
    payments = result.scalars().all()

    # Get total count
    count_result = await db_session.execute(select(Payment))
    total = len(count_result.scalars().all())

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
    )
