"""Area-related schemas."""

from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema


class AreaCreate(BaseSchema):
    """Create a new area."""

    name: str
    description: Optional[str] = None


class AreaUpdate(BaseSchema):
    """Update an area."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AreaResponse(BaseSchema):
    """Area response."""

    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
