"""Badge schemas."""

from datetime import datetime
from typing import List, Optional

from app.models.badge import BadgeCategory, BadgeCriteria
from app.schemas.base import BaseSchema


class BadgeResponse(BaseSchema):
    """Schema for badge response."""

    id: str
    name: str
    description: str
    category: BadgeCategory
    criteria: BadgeCriteria
    icon_url: Optional[str]


class BadgeListResponse(BaseSchema):
    """Schema for badge list response."""

    items: List[BadgeResponse]


class StudentBadgeResponse(BaseSchema):
    """Schema for student badge response."""

    id: str
    enrollment_id: str
    badge_id: str
    awarded_at: datetime
    awarded_by: Optional[str]
    progress: Optional[int]
    progress_max: Optional[int]


class StudentBadgeStatusResponse(BaseSchema):
    """Schema for student badge with locked/unlocked status."""

    badge: BadgeResponse
    is_unlocked: bool
    awarded_at: Optional[datetime]
    progress: Optional[int]
    progress_max: Optional[int]


class StudentBadgeListResponse(BaseSchema):
    """Schema for student badge list with status."""

    enrollment_id: str
    badges: List[StudentBadgeStatusResponse]


class BadgeAward(BaseSchema):
    """Schema for manually awarding a badge."""

    enrollment_id: str
    badge_id: str


class BadgeProgressResponse(BaseSchema):
    """Schema for badge progress response."""

    enrollment_id: str
    progress: List[dict]
