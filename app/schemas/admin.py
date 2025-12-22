"""Admin schemas for dashboard, reports, and client management."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.schemas.base import BaseSchema


class ProgramEnrollmentCount(BaseSchema):
    """Schema for program enrollment count."""

    id: str
    name: str
    count: int


class TodayClassInfo(BaseSchema):
    """Schema for today's class info."""

    id: str
    name: str
    school_name: str
    start_time: Optional[str]
    end_time: Optional[str]
    enrolled_count: int


class DashboardMetricsResponse(BaseSchema):
    """Schema for dashboard metrics response."""

    # Revenue metrics
    total_revenue: float
    revenue_this_month: float
    revenue_this_week: float

    # Counts
    active_enrollments: int
    total_students: int
    total_classes: int
    total_schools: int
    total_areas: int
    total_programs: int

    # Activity metrics
    attendance_rate: float
    new_enrollments_this_week: int
    pending_orders: int
    checked_in_today: int

    # Registration/Cancellation breakdown
    registrations_24h: int
    registrations_7d: int
    registrations_30d: int
    cancellations_24h: int
    cancellations_7d: int
    cancellations_30d: int

    # Program breakdown
    programs_with_counts: List[ProgramEnrollmentCount]

    # Today's classes
    today_classes: List[TodayClassInfo]

    # Monthly enrollment data for chart
    monthly_enrollments: List[Dict[str, Any]]


class RevenueReportResponse(BaseSchema):
    """Schema for revenue report response."""

    start_date: date
    end_date: date
    total_revenue: float
    revenue_by_type: Dict[str, float]  # {"one_time": 1000, "subscription": 500, ...}
    revenue_by_date: Dict[str, Dict[str, float]]  # {"2025-01-15": {"one_time": 100, ...}}
    group_by: str  # day, week, month


class ClientListItemResponse(BaseSchema):
    """Schema for client list item."""

    id: str
    email: str
    full_name: str
    phone: Optional[str]
    children_count: int
    active_enrollments: int
    created_at: datetime


class ClientListResponse(BaseSchema):
    """Schema for paginated client list."""

    items: List[Dict[str, Any]]  # Flexible dict for client data
    total: int
    skip: int
    limit: int


class ChildSummary(BaseSchema):
    """Schema for child summary in client detail."""

    id: str
    first_name: str
    last_name: str
    date_of_birth: date


class EnrollmentSummary(BaseSchema):
    """Schema for enrollment summary in client detail."""

    id: str
    child_name: str
    class_name: str
    start_date: date
    end_date: date
    status: str


class PaymentSummary(BaseSchema):
    """Schema for payment summary in client detail."""

    id: str
    amount: float
    payment_type: str
    status: str
    created_at: datetime


class ClientDetailResponse(BaseSchema):
    """Schema for detailed client information."""

    id: str
    email: str
    full_name: str
    phone: Optional[str]
    created_at: datetime
    children: List[Dict[str, Any]]
    active_enrollments: List[Dict[str, Any]]
    recent_payments: List[Dict[str, Any]]
    total_spent: float


class RosterStudentResponse(BaseSchema):
    """Schema for student in class roster."""

    enrollment_id: str
    child_id: str
    child_name: str
    child_age: Optional[int]
    child_dob: date
    parent_id: str
    parent_name: str
    parent_email: str
    parent_phone: Optional[str]
    enrollment_status: str
    enrolled_at: Optional[datetime]
    payment_status: str  # paid, pending, failed


class ClassRosterResponse(BaseSchema):
    """Schema for class roster with all enrolled students."""

    class_id: str
    class_name: str
    program_name: str
    school_name: str
    start_date: date
    end_date: date
    capacity: int
    current_enrollment: int
    students: List[RosterStudentResponse]


class RefundItemResponse(BaseSchema):
    """Schema for individual refund in search results."""

    payment_id: str
    order_id: str
    user_id: str
    user_email: str
    user_name: str
    original_amount: float
    refund_amount: float
    payment_status: str
    payment_type: str
    refunded_at: Optional[datetime]
    created_at: datetime
    order_items: List[Dict[str, Any]]  # Order line items with class/enrollment info


class RefundSearchResponse(BaseSchema):
    """Schema for refund search results."""

    items: List[RefundItemResponse]
    total: int
    skip: int
    limit: int
    total_refunded: float  # Sum of all refund amounts in results


class PendingRefundResponse(BaseSchema):
    """Schema for pending refund in approval queue."""

    payment_id: str
    order_id: str
    user_id: str
    user_email: str
    user_name: str
    original_amount: float
    refund_amount: float
    refund_requested_at: datetime
    payment_type: str
    order_details: Optional[str]  # Brief order summary


class PendingRefundsListResponse(BaseSchema):
    """Schema for list of pending refunds."""

    items: List[PendingRefundResponse]
    total: int


class RefundApprovalRequest(BaseSchema):
    """Schema for refund approval/rejection request."""

    rejection_reason: Optional[str] = None  # Required for rejection
