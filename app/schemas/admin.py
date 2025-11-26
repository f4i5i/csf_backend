"""Admin schemas for dashboard, reports, and client management."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.schemas.base import BaseSchema


class DashboardMetricsResponse(BaseSchema):
    """Schema for dashboard metrics response."""

    total_revenue: float
    revenue_this_month: float
    revenue_this_week: float
    active_enrollments: int
    total_students: int
    total_classes: int
    attendance_rate: float
    new_enrollments_this_week: int
    pending_orders: int


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
