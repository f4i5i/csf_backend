"""Order API endpoints for managing orders and checkout."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_admin, get_current_user
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderLineItem, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.user import User
from app.schemas.order import (
    OrderCalculateRequest,
    OrderCalculation,
    OrderCreate,
    OrderLineItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.schemas.payment import PaymentIntentResponse
from app.services.pricing_service import OrderItemInput, PricingService
from app.services.stripe_service import stripe_service, StripeService
from app.tasks.email_tasks import send_order_confirmation_email
from core.db import get_db
from core.exceptions.base import BadRequestException, ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


def order_to_response(order: Order) -> OrderResponse:
    """Convert Order model to response."""
    line_items = []
    if order.line_items:
        for li in order.line_items:
            line_items.append(
                OrderLineItemResponse(
                    id=li.id,
                    order_id=li.order_id,
                    enrollment_id=li.enrollment_id,
                    description=li.description,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    discount_code_id=li.discount_code_id,
                    discount_amount=li.discount_amount,
                    discount_description=li.discount_description,
                    line_total=li.line_total,
                )
            )

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status.value,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        total=order.total,
        stripe_payment_intent_id=order.stripe_payment_intent_id,
        stripe_customer_id=order.stripe_customer_id,
        paid_at=order.paid_at,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        line_items=line_items,
    )


# ============== Order Calculation ==============


@router.post("/calculate", response_model=OrderCalculation)
async def calculate_order(
    data: OrderCalculateRequest,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> OrderCalculation:
    """
    Calculate order total with all applicable discounts.

    Applies discounts in order:
    1. Sibling discounts (auto-applied)
    2. Scholarships (if any for user/child)
    3. Promo code discount

    Returns itemized breakdown of all discounts.
    """
    logger.info(f"Calculate order for user: {current_user.id}")

    pricing_service = PricingService(db_session)

    items = [OrderItemInput(child_id=i.child_id, class_id=i.class_id) for i in data.items]

    calculation = await pricing_service.calculate_order(
        user_id=current_user.id,
        items=items,
        discount_code=data.discount_code,
    )

    return OrderCalculation(
        line_items=[
            {
                "child_id": li.child_id,
                "child_name": li.child_name,
                "class_id": li.class_id,
                "class_name": li.class_name,
                "unit_price": li.unit_price,
                "sibling_discount": li.sibling_discount,
                "sibling_discount_description": li.sibling_discount_description,
                "promo_discount": li.promo_discount,
                "promo_discount_description": li.promo_discount_description,
                "scholarship_discount": li.scholarship_discount,
                "scholarship_discount_description": li.scholarship_discount_description,
                "line_total": li.line_total,
            }
            for li in calculation.line_items
        ],
        subtotal=calculation.subtotal,
        sibling_discount_total=calculation.sibling_discount_total,
        promo_discount_total=calculation.promo_discount_total,
        scholarship_discount_total=calculation.scholarship_discount_total,
        discount_total=calculation.discount_total,
        total=calculation.total,
        discount_code=calculation.discount_code,
        discount_code_id=calculation.discount_code_id,
    )


# ============== Order CRUD ==============


@router.post("/", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create an order from items.

    Creates draft order with enrollments. Payment is handled separately.
    """
    logger.info(f"Create order for user: {current_user.id}")

    pricing_service = PricingService(db_session)

    items = [OrderItemInput(child_id=i.child_id, class_id=i.class_id) for i in data.items]

    calculation = await pricing_service.calculate_order(
        user_id=current_user.id,
        items=items,
        discount_code=data.discount_code,
    )

    if not calculation.line_items:
        raise BadRequestException(message="No valid items in order")

    # Create order
    order = Order(
        id=str(uuid4()),
        user_id=current_user.id,
        status=OrderStatus.DRAFT,
        subtotal=calculation.subtotal,
        discount_total=calculation.discount_total,
        total=calculation.total,
        notes=data.notes,
    )
    db_session.add(order)

    # Create enrollments and line items
    for li in calculation.line_items:
        # Create enrollment
        enrollment = Enrollment(
            id=str(uuid4()),
            child_id=li.child_id,
            class_id=li.class_id,
            user_id=current_user.id,
            status=EnrollmentStatus.PENDING,
            base_price=li.unit_price,
            discount_amount=li.sibling_discount + li.promo_discount + li.scholarship_discount,
            final_price=li.line_total,
        )
        db_session.add(enrollment)

        # Build discount description
        discount_desc_parts = []
        if li.sibling_discount_description:
            discount_desc_parts.append(li.sibling_discount_description)
        if li.scholarship_discount_description:
            discount_desc_parts.append(li.scholarship_discount_description)
        if li.promo_discount_description:
            discount_desc_parts.append(li.promo_discount_description)

        # Create line item
        line_item = OrderLineItem(
            id=str(uuid4()),
            order_id=order.id,
            enrollment_id=enrollment.id,
            description=f"{li.child_name} - {li.class_name}",
            quantity=1,
            unit_price=li.unit_price,
            discount_code_id=calculation.discount_code_id,
            discount_amount=li.sibling_discount + li.promo_discount + li.scholarship_discount,
            discount_description="; ".join(discount_desc_parts) if discount_desc_parts else None,
            line_total=li.line_total,
        )
        db_session.add(line_item)

    await db_session.commit()

    # Reload with relationships
    result = await db_session.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .where(Order.id == order.id)
    )
    order = result.scalar_one()

    # Send order confirmation email
    order_items = []
    for line_item in order.line_items:
        order_items.append({
            "class_name": line_item.description.split(" - ")[-1],  # Extract class name
            "child_name": line_item.description.split(" - ")[0],  # Extract child name
            "price": f"${line_item.line_total:.2f}",
        })

    send_order_confirmation_email.delay(
        user_email=current_user.email,
        user_name=current_user.full_name,
        order_id=order.id,
        order_items=order_items,
        subtotal=str(order.subtotal),
        discount_total=str(order.discount_total),
        total=str(order.total),
        payment_type="Pending",
    )

    logger.info(f"Order created: {order.id}")
    return order_to_response(order)


@router.get("/my", response_model=OrderListResponse)
async def list_my_orders(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """
    List all orders for the current user.
    """
    logger.info(f"List orders for user: {current_user.id}")

    result = await db_session.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    return OrderListResponse(
        items=[order_to_response(o) for o in orders],
        total=len(orders),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Get order details by ID.
    """
    logger.info(f"Get order {order_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundException(message="Order not found")

    # Check access
    if order.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this order")

    return order_to_response(order)


# ============== Payment ==============


@router.post("/{order_id}/pay", response_model=PaymentIntentResponse)
async def create_payment_for_order(
    order_id: str,
    payment_method_id: str = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> PaymentIntentResponse:
    """
    Create payment intent for an order.

    If payment_method_id provided, attempts to charge immediately.
    Otherwise returns client_secret for frontend to complete payment.
    """
    logger.info(f"Create payment for order {order_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundException(message="Order not found")

    if order.user_id != current_user.id:
        raise ForbiddenException(message="You don't have access to this order")

    if order.status not in [OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT]:
        raise BadRequestException(message=f"Order cannot be paid - status is {order.status.value}")

    # Get or create Stripe customer
    customer_id = await stripe_service.get_or_create_customer(
        email=current_user.email,
        name=f"{current_user.first_name} {current_user.last_name}",
        user_id=current_user.id,
    )

    # Create payment intent
    amount_cents = StripeService.dollars_to_cents(order.total)

    payment_intent = await stripe_service.create_payment_intent(
        amount=amount_cents,
        customer_id=customer_id,
        payment_method_id=payment_method_id,
        metadata={
            "order_id": order.id,
            "user_id": current_user.id,
        },
        description=f"Order {order.id}",
    )

    # Update order
    order.status = OrderStatus.PENDING_PAYMENT
    order.stripe_payment_intent_id = payment_intent["id"]
    order.stripe_customer_id = customer_id
    await db_session.commit()

    return PaymentIntentResponse(
        id=payment_intent["id"],
        client_secret=payment_intent["client_secret"],
        status=payment_intent["status"],
        amount=payment_intent["amount"],
    )


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Cancel a draft or pending order.

    Cannot cancel paid orders - use refund instead.
    """
    logger.info(f"Cancel order {order_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundException(message="Order not found")

    if order.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this order")

    if order.status not in [OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT]:
        raise BadRequestException(message="Cannot cancel a paid order")

    # Cancel enrollments
    for li in order.line_items:
        if li.enrollment_id:
            enrollment_result = await db_session.execute(
                select(Enrollment).where(Enrollment.id == li.enrollment_id)
            )
            enrollment = enrollment_result.scalar_one_or_none()
            if enrollment and enrollment.status == EnrollmentStatus.PENDING:
                enrollment.status = EnrollmentStatus.CANCELLED
                enrollment.cancelled_at = datetime.now(timezone.utc)

    order.status = OrderStatus.CANCELLED
    await db_session.commit()

    return {"message": "Order cancelled successfully"}


# ============== Admin Endpoints ==============


@router.get("/", response_model=OrderListResponse)
async def list_all_orders(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """
    List all orders (admin only).
    """
    logger.info(f"List all orders by admin: {current_user.id}")

    query = select(Order).options(selectinload(Order.line_items))

    if status:
        query = query.where(Order.status == OrderStatus(status))

    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)

    result = await db_session.execute(query)
    orders = result.scalars().all()

    # Get total
    count_result = await db_session.execute(select(Order))
    total = len(count_result.scalars().all())

    return OrderListResponse(
        items=[order_to_response(o) for o in orders],
        total=total,
    )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Update order status (admin only).
    """
    logger.info(f"Update order {order_id} status by admin: {current_user.id}")

    result = await db_session.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundException(message="Order not found")

    order.status = OrderStatus(data.status)
    if data.notes:
        order.notes = data.notes

    await db_session.commit()

    return order_to_response(order)
