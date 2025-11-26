"""Photo schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.base import BaseSchema


class PhotoResponse(BaseSchema):
    """Schema for photo response."""

    id: str
    class_id: str
    category_id: Optional[str]
    uploaded_by: str
    file_name: str
    file_path: str
    thumbnail_path: Optional[str]
    file_size: int
    width: Optional[int]
    height: Optional[int]
    created_at: datetime


class PhotoListResponse(BaseSchema):
    """Schema for paginated photo list response."""

    items: List[PhotoResponse]
    total: int
    skip: int
    limit: int


class PhotoCategoryCreate(BaseSchema):
    """Schema for creating photo category."""

    name: str = Field(..., min_length=1, max_length=100)
    class_id: str


class PhotoCategoryResponse(BaseSchema):
    """Schema for photo category response."""

    id: str
    name: str
    class_id: str
    created_at: datetime


class PhotoCategoryListResponse(BaseSchema):
    """Schema for photo category list response."""

    items: List[PhotoCategoryResponse]
