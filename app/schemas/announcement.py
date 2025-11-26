"""Announcement schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.models.announcement import AnnouncementType, AttachmentType
from app.schemas.base import BaseSchema


class AnnouncementCreate(BaseSchema):
    """Schema for creating an announcement."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    class_ids: List[str] = Field(..., min_items=1)
    type: AnnouncementType = Field(default=AnnouncementType.GENERAL)


class AnnouncementUpdate(BaseSchema):
    """Schema for updating an announcement."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    type: Optional[AnnouncementType] = None


class AnnouncementAttachmentResponse(BaseSchema):
    """Schema for announcement attachment response."""

    id: str
    file_name: str
    file_path: str
    file_size: int
    file_type: AttachmentType
    mime_type: str
    created_at: datetime


class AnnouncementResponse(BaseSchema):
    """Schema for announcement response."""

    id: str
    title: str
    description: str
    type: AnnouncementType
    author_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    attachments: List[AnnouncementAttachmentResponse] = []


class AnnouncementListResponse(BaseSchema):
    """Schema for paginated announcement list response."""

    items: List[AnnouncementResponse]
    total: int
    skip: int
    limit: int
