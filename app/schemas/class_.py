from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from pydantic import Field, field_validator

from app.models.class_ import ClassType, Weekday
from app.schemas.base import BaseSchema


class ClassCreate(BaseSchema):
    """Schema for creating a new class."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    ledger_code: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    program_id: str
    school_id: str
    class_type: ClassType

    # Schedule
    weekdays: List[Weekday] = Field(..., min_length=1)
    start_time: time
    end_time: time
    start_date: date
    end_date: date

    # Capacity
    capacity: int = Field(..., gt=0)
    waitlist_enabled: bool = True

    # Pricing
    price: Decimal = Field(..., gt=0)
    membership_price: Optional[Decimal] = Field(None, gt=0)
    installments_enabled: bool = False

    # Age requirements
    min_age: int = Field(..., ge=0)
    max_age: int = Field(..., ge=0)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: time, info) -> time:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("max_age")
    @classmethod
    def validate_max_age(cls, v: int, info) -> int:
        if "min_age" in info.data and v < info.data["min_age"]:
            raise ValueError("max_age must be greater than or equal to min_age")
        return v


class ClassUpdate(BaseSchema):
    """Schema for updating a class."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    ledger_code: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    class_type: Optional[ClassType] = None

    # Schedule
    weekdays: Optional[List[Weekday]] = Field(None, min_length=1)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Capacity
    capacity: Optional[int] = Field(None, gt=0)
    waitlist_enabled: Optional[bool] = None

    # Pricing
    price: Optional[Decimal] = Field(None, gt=0)
    membership_price: Optional[Decimal] = Field(None, gt=0)
    installments_enabled: Optional[bool] = None

    # Age requirements
    min_age: Optional[int] = Field(None, ge=0)
    max_age: Optional[int] = Field(None, ge=0)

    is_active: Optional[bool] = None

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[date], info):
        start_date = info.data.get("start_date")
        if v and start_date and v < start_date:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: Optional[time], info):
        start_time = info.data.get("start_time")
        if v and start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("max_age")
    @classmethod
    def validate_max_age(cls, v: Optional[int], info):
        min_age = info.data.get("min_age")
        if v is not None and min_age is not None and v < min_age:
            raise ValueError("max_age must be greater than or equal to min_age")
        return v


class ClassResponse(BaseSchema):
    """Schema for class response."""

    id: str
    name: str
    description: Optional[str]
    ledger_code: Optional[str]
    image_url: Optional[str]
    program_id: str
    school_id: str
    class_type: ClassType

    # Schedule
    weekdays: List[str]
    start_time: time
    end_time: time
    start_date: date
    end_date: date

    # Capacity
    capacity: int
    current_enrollment: int
    available_spots: int
    has_capacity: bool
    waitlist_enabled: bool

    # Pricing
    price: Decimal
    membership_price: Optional[Decimal]
    installments_enabled: bool

    # Age requirements
    min_age: int
    max_age: int

    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClassListResponse(BaseSchema):
    """Schema for paginated class list response."""

    items: List[ClassResponse]
    total: int
    skip: int
    limit: int
