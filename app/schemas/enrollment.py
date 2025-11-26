"""Enrollment-related schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.schemas.base import BaseSchema


class EnrollmentResponse(BaseSchema):
    """Enrollment response."""

    id: str
    child_id: str
    class_id: str
    user_id: str
    status: str
    enrolled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    base_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    created_at: datetime
    updated_at: datetime
    # Related data
    child_name: Optional[str] = None
    class_name: Optional[str] = None


class EnrollmentListResponse(BaseSchema):
    """List of enrollments."""

    items: list[EnrollmentResponse]
    total: int


class EnrollmentCancel(BaseSchema):
    """Cancel enrollment request."""

    reason: Optional[str] = None


class CancellationRefundPreview(BaseSchema):
    """Preview of cancellation refund calculation."""

    enrollment_id: str
    enrollment_amount: Decimal
    enrolled_at: date
    days_enrolled: int
    refund_amount: Decimal
    policy_applied: str
    processing_fee: Decimal


class EnrollmentTransfer(BaseSchema):
    """Transfer enrollment to different class."""

    new_class_id: str
