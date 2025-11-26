"""Discount and scholarship schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from app.schemas.base import BaseSchema


# ============== Discount Code Schemas ==============


class DiscountCodeValidate(BaseSchema):
    """Validate a discount code."""

    code: str
    order_amount: Decimal
    program_id: Optional[str] = None
    class_id: Optional[str] = None


class DiscountValidationResponse(BaseSchema):
    """Discount validation result."""

    is_valid: bool
    error_message: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None


class DiscountCodeCreate(BaseSchema):
    """Create a new discount code (admin only)."""

    code: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None
    discount_type: str = Field(..., pattern="^(percentage|fixed_amount)$")
    discount_value: Decimal = Field(..., gt=0)
    valid_from: datetime
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = Field(None, gt=0)
    max_uses_per_user: Optional[int] = Field(None, gt=0)
    min_order_amount: Optional[Decimal] = None
    applies_to_program_id: Optional[str] = None
    applies_to_class_id: Optional[str] = None


class DiscountCodeUpdate(BaseSchema):
    """Update discount code."""

    description: Optional[str] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None


class DiscountCodeResponse(BaseSchema):
    """Discount code response."""

    id: str
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    valid_from: datetime
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    current_uses: int
    max_uses_per_user: Optional[int] = None
    min_order_amount: Optional[Decimal] = None
    applies_to_program_id: Optional[str] = None
    applies_to_class_id: Optional[str] = None
    is_active: bool
    created_by_id: str
    created_at: datetime
    updated_at: datetime


class DiscountCodeListResponse(BaseSchema):
    """List of discount codes."""

    items: list[DiscountCodeResponse]
    total: int


# ============== Scholarship Schemas ==============


class ScholarshipCreate(BaseSchema):
    """Create a scholarship (admin only)."""

    user_id: str
    child_id: Optional[str] = None
    scholarship_type: str = Field(..., max_length=100)
    discount_percentage: Decimal = Field(..., gt=0, le=100)
    valid_until: Optional[date] = None
    notes: Optional[str] = None


class ScholarshipUpdate(BaseSchema):
    """Update scholarship."""

    discount_percentage: Optional[Decimal] = Field(None, gt=0, le=100)
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ScholarshipResponse(BaseSchema):
    """Scholarship response."""

    id: str
    user_id: str
    child_id: Optional[str] = None
    scholarship_type: str
    discount_percentage: Decimal
    approved_by_id: str
    approved_at: datetime
    valid_until: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScholarshipListResponse(BaseSchema):
    """List of scholarships."""

    items: list[ScholarshipResponse]
    total: int
