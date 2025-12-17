"""Payment API endpoints for managing payment methods and transactions."""

from datetime import date
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
    status: str = None,
    start_date: date = None,
    end_date: date = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """
    List all payments for the current user with filtering options.

    Args:
        status: Filter by payment status (succeeded, pending, failed, etc.)
        start_date: Filter payments created on or after this date
        end_date: Filter payments created on or before this date
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (default 50)

    Returns payment history including status, amounts, and installment plan details.
    """
    from app.models.payment import PaymentStatus, PaymentType, InstallmentPlan, InstallmentPayment, InstallmentPaymentStatus
    from decimal import Decimal

    logger.info(f"List payments for user: {current_user.id} with filters: status={status}, start_date={start_date}, end_date={end_date}")

    # Build query with filters
    query = select(Payment).where(Payment.user_id == current_user.id)

    if status:
        try:
            query = query.where(Payment.status == PaymentStatus(status))
        except ValueError:
            logger.warning(f"Invalid status filter: {status}")

    if start_date:
        query = query.where(Payment.created_at >= start_date)

    if end_date:
        query = query.where(Payment.created_at <= end_date)

    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)

    result = await db_session.execute(query)
    payments = result.scalars().all()

    # Build response items with installment plan details
    response_items = []
    for payment in payments:
        payment_dict = {
            "id": payment.id,
            "order_id": payment.order_id,
            "user_id": payment.user_id,
            "payment_type": payment.payment_type.value,
            "status": payment.status.value,
            "amount": payment.amount,
            "currency": payment.currency,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "stripe_charge_id": payment.stripe_charge_id,
            "failure_reason": payment.failure_reason,
            "refund_amount": payment.refund_amount,
            "paid_at": payment.paid_at,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            "installment_plan": None,
        }

        # If this is an installment payment, load plan details
        if payment.payment_type == PaymentType.INSTALLMENT:
            # Find the installment payment record for this payment
            installment_payment_result = await db_session.execute(
                select(InstallmentPayment)
                .options(selectinload(InstallmentPayment.installment_plan))
                .where(InstallmentPayment.payment_id == payment.id)
            )
            installment_payment = installment_payment_result.scalar_one_or_none()

            if installment_payment and installment_payment.installment_plan:
                plan = installment_payment.installment_plan

                # Calculate paid count
                paid_count = sum(
                    1 for ip in plan.installment_payments
                    if ip.status == InstallmentPaymentStatus.PAID
                )

                # Calculate remaining amount
                total_paid = sum(
                    ip.amount for ip in plan.installment_payments
                    if ip.status == InstallmentPaymentStatus.PAID
                )
                remaining_amount = plan.total_amount - total_paid

                # Find next due date
                next_due_date = None
                for ip in plan.installment_payments:
                    if ip.status == InstallmentPaymentStatus.PENDING:
                        if next_due_date is None or ip.due_date < next_due_date:
                            next_due_date = ip.due_date

                payment_dict["installment_plan"] = {
                    "id": plan.id,
                    "num_installments": plan.num_installments,
                    "installment_number": installment_payment.installment_number,
                    "paid_count": paid_count,
                    "total_amount": plan.total_amount,
                    "remaining_amount": remaining_amount,
                    "next_due_date": next_due_date,
                    "status": plan.status.value,
                }

        response_items.append(PaymentResponse(**payment_dict))

    return PaymentListResponse(
        items=response_items,
        total=len(response_items),
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
