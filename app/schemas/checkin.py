"""Check-in schemas."""

from datetime import date, datetime
from typing import List

from pydantic import Field

from app.schemas.base import BaseSchema


class CheckInCreate(BaseSchema):
    """Schema for creating a check-in."""

    enrollment_id: str
    class_id: str
    check_in_date: date
    is_late: bool = False


class BulkCheckInRequest(BaseSchema):
    """Schema for bulk check-in request."""

    class_id: str
    enrollment_ids: List[str] = Field(..., min_items=1)
    check_in_date: date


class CheckInResponse(BaseSchema):
    """Schema for check-in response."""

    id: str
    enrollment_id: str
    class_id: str
    checked_in_at: datetime
    check_in_date: date
    is_late: bool
    created_at: datetime


class CheckInListResponse(BaseSchema):
    """Schema for check-in list response."""

    items: List[CheckInResponse]
    total: int


class CheckInStatusResponse(BaseSchema):
    """Schema for check-in status response."""

    enrollment_id: str
    is_checked_in: bool
    checked_in_at: datetime | None = None


class CheckInStatusListResponse(BaseSchema):
    """Schema for multiple enrollment check-in statuses."""

    class_id: str
    check_in_date: date
    statuses: List[CheckInStatusResponse]
