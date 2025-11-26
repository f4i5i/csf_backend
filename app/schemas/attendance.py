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
