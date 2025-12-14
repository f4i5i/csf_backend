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
    # Waitlist fields
    waitlist_priority: Optional[str] = None
    auto_promote: bool = False
    claim_window_expires_at: Optional[datetime] = None
    promoted_at: Optional[datetime] = None
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


class JoinWaitlistRequest(BaseSchema):
    """Request to join waitlist for a class."""

    child_id: str
    class_id: str
    priority: str  # "priority" or "regular"
    payment_method_id: Optional[str] = None  # Required for priority waitlist


class WaitlistEntryResponse(BaseSchema):
    """Waitlist entry with position information."""

    enrollment_id: str
    child_id: str
    child_name: str
    class_id: str
    class_name: str
    waitlist_priority: str
    position: int  # Position in waitlist (1-indexed)
    auto_promote: bool
    claim_window_expires_at: Optional[datetime] = None
    created_at: datetime


class WaitlistListResponse(BaseSchema):
    """List of waitlist entries for a class."""

    class_id: str
    class_name: str
    total_waitlisted: int
    priority_count: int
    regular_count: int
    entries: list[WaitlistEntryResponse]


class ClaimWaitlistRequest(BaseSchema):
    """Request to claim a regular waitlist spot."""

    payment_method_id: str  # Payment method for claiming the spot


class PromoteWaitlistRequest(BaseSchema):
    """Admin request to manually promote from waitlist."""

    enrollment_id: str
    skip_payment: bool = False  # Admin can skip payment requirement
