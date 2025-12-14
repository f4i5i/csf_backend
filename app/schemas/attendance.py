"""Attendance schemas for request/response validation."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from app.models.attendance import AttendanceStatus
from app.schemas.base import BaseSchema


class AttendanceMarkRecord(BaseSchema):
    """Schema for marking a single attendance record."""

    enrollment_id: str
    date: date
    status: AttendanceStatus
    notes: Optional[str] = None


class AttendanceMarkBulk(BaseSchema):
    """Schema for bulk marking attendance."""

    class_id: str
    records: List[AttendanceMarkRecord] = Field(..., min_items=1)


class AttendanceResponse(BaseSchema):
    """Schema for attendance response."""

    id: str
    enrollment_id: str
    class_id: str
    date: date
    status: AttendanceStatus
    notes: Optional[str]
    created_at: datetime


class AttendanceListResponse(BaseSchema):
    """Schema for paginated attendance list response."""

    items: List[AttendanceResponse]
    total: int
    skip: int
    limit: int


class AttendanceStreakResponse(BaseSchema):
    """Schema for attendance streak response."""

    enrollment_id: str
    streak: int


class ClassInstanceAttendanceResponse(BaseSchema):
    """Schema for class attendance response."""

    class_instance_id: str  # Keeping this name for backwards compatibility
    records: List[AttendanceResponse]


class EnrollmentAttendanceStats(BaseSchema):
    """Attendance stats for a single enrollment."""

    enrollment_id: str
    class_name: str
    sessions_attended: int
    sessions_missed: int
    sessions_excused: int
    total_sessions: int
    attendance_rate: float  # 0-100
    current_streak: int
    status: str  # active, completed, etc.


class AttendanceStatsResponse(BaseSchema):
    """Aggregated attendance statistics for a child."""

    child_id: str
    total_sessions_attended: int
    total_sessions_missed: int
    total_sessions_excused: int
    overall_attendance_rate: float  # 0-100
    longest_streak: int
    total_sessions: int
    by_enrollment: List[EnrollmentAttendanceStats]
