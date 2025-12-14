"""Photo schemas."""

import base64
from datetime import datetime
from typing import Any, List, Optional

from pydantic import Field, computed_field

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
    content_type: Optional[str] = None
    created_at: datetime

    # Binary data fields (excluded from dict by default for performance)
    file_data: Optional[bytes] = Field(None, exclude=True)
    thumbnail_data: Optional[bytes] = Field(None, exclude=True)

    # MIME type (alias for content_type)
    @computed_field
    @property
    def mime_type(self) -> str:
        """MIME type of the image (e.g., image/jpeg, image/png)."""
        return self.content_type or "image/jpeg"

    # URL endpoints for displaying images
    @computed_field
    @property
    def image_url(self) -> str:
        """URL to fetch the full image."""
        return f"/api/v1/photos/{self.id}/image"

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        """URL to fetch the thumbnail image."""
        return f"/api/v1/photos/{self.id}/thumbnail"

    # Base64 encoded data (optional, computed on demand)
    @computed_field
    @property
    def image_base64(self) -> Optional[str]:
        """Base64 encoded full image for direct embedding."""
        if self.file_data:
            encoded = base64.b64encode(self.file_data).decode('utf-8')
            return f"data:{self.content_type or 'image/jpeg'};base64,{encoded}"
        return None

    @computed_field
    @property
    def thumbnail_base64(self) -> Optional[str]:
        """Base64 encoded thumbnail for direct embedding."""
        if self.thumbnail_data:
            encoded = base64.b64encode(self.thumbnail_data).decode('utf-8')
            return f"data:{self.content_type or 'image/jpeg'};base64,{encoded}"
        return None


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
