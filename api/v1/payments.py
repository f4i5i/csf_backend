"""Payment API endpoints for managing payment methods and transactions."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_parent_or_admin, get_current_user
from app.models.order import Order
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
from app.services.invoice_service import InvoiceService
from app.services.stripe_service import stripe_service, StripeService
from core.db import get_db
from core.exceptions.base import BadRequestException, ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ============== Payment Methods ==============


@router.post("/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    current_user: User = Depends(get_current_parent_or_admin),
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
    current_user: User = Depends(get_current_parent_or_admin),
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
    current_user: User = Depends(get_current_parent_or_admin),
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
    current_user: User = Depends(get_current_parent_or_admin),
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
    current_user: User = Depends(get_current_parent_or_admin),
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


# ============== Invoice Download ==============


@router.get("/{payment_id}/invoice/download")
async def download_invoice(
    payment_id: str,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Download invoice PDF for a payment.

    Returns a PDF file that can be saved or viewed.
    """
    logger.info(f"Generate invoice for payment: {payment_id} by user: {current_user.id}")

    # Get payment
    payment = await Payment.get_by_id(db_session, payment_id)
    if not payment:
        raise NotFoundException(f"Payment {payment_id} not found")

    # Verify user owns this payment
    if payment.user_id != current_user.id:
        raise ForbiddenException("You don't have permission to access this invoice")

    # Get order details
    order = await Order.get_by_id(db_session, payment.order_id)
    if not order:
        raise NotFoundException(f"Order {payment.order_id} not found")

    # Build invoice number from payment ID
    invoice_number = f"#INV-{payment.id[:8].upper()}"

    # Build line items
    items = []
    if order.line_items:
        for item in order.line_items:
            items.append({
                "description": "Class Enrollment",
                "amount": item.price
            })
    else:
        # Fallback if no line items
        items.append({
            "description": "Class Registration",
            "amount": payment.amount
        })

    # Generate PDF
    pdf_buffer = InvoiceService.generate_invoice_pdf(
        invoice_number=invoice_number,
        invoice_date=payment.paid_at or payment.created_at,
        customer_name=f"{current_user.first_name} {current_user.last_name}",
        customer_email=current_user.email,
        items=items,
        subtotal=order.subtotal,
        discount=order.discount_total,
        total=payment.amount,
        payment_method=payment.payment_type.value.replace("_", " ").title(),
        transaction_id=payment.stripe_payment_intent_id or payment.id,
    )

    # Return PDF as streaming response
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{payment.id}.pdf"
        }
    )
