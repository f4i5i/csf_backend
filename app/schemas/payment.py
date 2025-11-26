"""Payment-related schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from app.schemas.base import BaseSchema


# ============== Payment Method Schemas ==============


class SetupIntentResponse(BaseSchema):
    """Response for creating a setup intent to save payment method."""

    id: str
    client_secret: str


class PaymentMethodResponse(BaseSchema):
    """Saved payment method details."""

    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class PaymentMethodListResponse(BaseSchema):
    """List of saved payment methods."""

    items: list[PaymentMethodResponse]
    total: int


# ============== Payment Intent Schemas ==============


class PaymentIntentCreate(BaseSchema):
    """Create a payment intent for one-time payment."""

    order_id: str
    payment_method_id: Optional[str] = None


class PaymentIntentResponse(BaseSchema):
    """Payment intent response."""

    id: str
    client_secret: str
    status: str
    amount: int  # In cents


class PaymentIntentConfirm(BaseSchema):
    """Confirm a payment intent."""

    payment_intent_id: str
    payment_method_id: str


# ============== Payment Record Schemas ==============


class PaymentResponse(BaseSchema):
    """Payment transaction response."""

    id: str
    order_id: str
    user_id: str
    payment_type: str
    status: str
    amount: Decimal
    currency: str
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    failure_reason: Optional[str] = None
    refund_amount: Decimal
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseSchema):
    """List of payments."""

    items: list[PaymentResponse]
    total: int


# ============== Installment Schemas ==============


class InstallmentScheduleItem(BaseSchema):
    """Single installment in a schedule."""

    installment_number: int
    due_date: date
    amount: Decimal


class InstallmentSchedulePreview(BaseSchema):
    """Preview installment schedule before creating."""

    total_amount: Decimal
    num_installments: int
    frequency: str
    schedule: list[InstallmentScheduleItem]


class InstallmentPlanCreate(BaseSchema):
    """Create an installment plan."""

    order_id: str
    num_installments: int = Field(..., ge=2, le=12)
    frequency: str = Field(..., pattern="^(weekly|biweekly|monthly)$")
    payment_method_id: str


class InstallmentPlanResponse(BaseSchema):
    """Installment plan response."""

    id: str
    order_id: str
    user_id: str
    total_amount: Decimal
    num_installments: int
    installment_amount: Decimal
    frequency: str
    start_date: date
    stripe_subscription_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class InstallmentPaymentResponse(BaseSchema):
    """Individual installment payment."""

    id: str
    installment_plan_id: str
    payment_id: Optional[str] = None
    installment_number: int
    due_date: date
    amount: Decimal
    status: str
    paid_at: Optional[datetime] = None
    attempt_count: int


# ============== Refund Schemas ==============


class RefundCreate(BaseSchema):
    """Create a refund request."""

    payment_id: str
    amount: Optional[Decimal] = None  # None = full refund
    reason: Optional[str] = None


class RefundResponse(BaseSchema):
    """Refund response."""

    id: str
    status: str
    amount: int  # In cents
