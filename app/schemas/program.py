"""Program-related schemas."""

from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema


class ProgramCreate(BaseSchema):
    """Create a new program."""

    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True


class ProgramUpdate(BaseSchema):
    """Update a program."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProgramResponse(BaseSchema):
    """Program response."""

    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
