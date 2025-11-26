"""Order-related schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from app.schemas.base import BaseSchema


# ============== Order Item Schemas ==============


class OrderItemInput(BaseSchema):
    """Input item for order calculation."""

    child_id: str
    class_id: str


class LineItemCalculation(BaseSchema):
    """Calculated line item with discounts."""

    child_id: str
    child_name: str
    class_id: str
    class_name: str
    unit_price: Decimal
    sibling_discount: Decimal
    sibling_discount_description: Optional[str] = None
    promo_discount: Decimal
    promo_discount_description: Optional[str] = None
    scholarship_discount: Decimal
    scholarship_discount_description: Optional[str] = None
    line_total: Decimal


class OrderLineItemResponse(BaseSchema):
    """Order line item response."""

    id: str
    order_id: str
    enrollment_id: Optional[str] = None
    description: str
    quantity: int
    unit_price: Decimal
    discount_code_id: Optional[str] = None
    discount_amount: Decimal
    discount_description: Optional[str] = None
    line_total: Decimal


# ============== Order Calculation Schemas ==============


class OrderCalculateRequest(BaseSchema):
    """Request to calculate order total."""

    items: list[OrderItemInput] = Field(..., min_length=1)
    discount_code: Optional[str] = None


class OrderCalculation(BaseSchema):
    """Order calculation result showing all discounts."""

    line_items: list[LineItemCalculation]
    subtotal: Decimal
    sibling_discount_total: Decimal
    promo_discount_total: Decimal
    scholarship_discount_total: Decimal
    discount_total: Decimal
    total: Decimal
    discount_code: Optional[str] = None
    discount_code_id: Optional[str] = None


# ============== Order CRUD Schemas ==============


class OrderCreate(BaseSchema):
    """Create an order from calculated items."""

    items: list[OrderItemInput] = Field(..., min_length=1)
    discount_code: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseSchema):
    """Order response."""

    id: str
    user_id: str
    status: str
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    stripe_payment_intent_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    line_items: list[OrderLineItemResponse] = []


class OrderListResponse(BaseSchema):
    """List of orders."""

    items: list[OrderResponse]
    total: int


class OrderSummary(BaseSchema):
    """Minimal order summary for lists."""

    id: str
    status: str
    total: Decimal
    created_at: datetime


# ============== Order Status Update ==============


class OrderStatusUpdate(BaseSchema):
    """Update order status (admin only)."""

    status: str = Field(..., pattern="^(pending_payment|paid|cancelled|refunded)$")
    notes: Optional[str] = None
