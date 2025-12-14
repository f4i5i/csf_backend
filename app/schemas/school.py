"""School-related schemas."""

from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema


class SchoolCreate(BaseSchema):
    """Create a new school."""

    name: str
    code: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    area_id: str
    is_active: Optional[bool] = True


class SchoolUpdate(BaseSchema):
    """Update a school."""

    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    area_id: Optional[str] = None
    is_active: Optional[bool] = None


class SchoolResponse(BaseSchema):
    """School response."""

    id: str
    name: str
    code: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    area_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
