from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.models.waiver import WaiverType
from app.schemas.base import BaseSchema


class WaiverTemplateCreate(BaseSchema):
    """Schema for creating a waiver template."""

    name: str = Field(..., min_length=1, max_length=200)
    waiver_type: WaiverType
    content: str = Field(..., min_length=1)  # HTML content
    is_active: bool = True
    is_required: bool = True

    # Scope - null means global
    applies_to_program_id: Optional[str] = None
    applies_to_school_id: Optional[str] = None


class WaiverTemplateUpdate(BaseSchema):
    """Schema for updating a waiver template."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None
    is_required: Optional[bool] = None
    applies_to_program_id: Optional[str] = None
    applies_to_school_id: Optional[str] = None


class WaiverTemplateResponse(BaseSchema):
    """Schema for waiver template response."""

    id: str
    name: str
    waiver_type: WaiverType
    content: str
    version: int
    is_active: bool
    is_required: bool
    applies_to_program_id: Optional[str]
    applies_to_school_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class WaiverTemplateListResponse(BaseSchema):
    """Schema for paginated waiver template list."""

    items: List[WaiverTemplateResponse]
    total: int


class WaiverAcceptanceCreate(BaseSchema):
    """Schema for accepting a waiver."""

    waiver_template_id: str
    signer_name: str = Field(..., min_length=1, max_length=200)


class WaiverAcceptanceResponse(BaseSchema):
    """Schema for waiver acceptance response."""

    id: str
    user_id: str
    waiver_template_id: str
    waiver_version: int
    signer_name: str
    accepted_at: datetime
    waiver_template: Optional[WaiverTemplateResponse] = None
    created_at: datetime
    updated_at: datetime


class WaiverAcceptanceListResponse(BaseSchema):
    """Schema for waiver acceptance list."""

    items: List[WaiverAcceptanceResponse]
    total: int


class WaiverStatusResponse(BaseSchema):
    """Schema showing waiver status for a user."""

    waiver_template: WaiverTemplateResponse
    is_accepted: bool
    acceptance: Optional[WaiverAcceptanceResponse] = None
    needs_reconsent: bool


class WaiverStatusListResponse(BaseSchema):
    """Schema for user's waiver status list."""

    items: List[WaiverStatusResponse]
    pending_count: int
    total: int
