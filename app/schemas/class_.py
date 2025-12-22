from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import Field, field_validator, model_validator, computed_field, field_serializer
from sqlalchemy.orm import object_session
from sqlalchemy.inspection import inspect as sqlalchemy_inspect

from app.models.class_ import ClassType, Weekday
from app.schemas.base import BaseSchema

if TYPE_CHECKING:
    from app.schemas.school import SchoolResponse


class PaymentOption(BaseSchema):
    """Schema for payment option configuration."""

    name: str = Field(..., min_length=1, max_length=200, description="Display name for this payment option")
    type: Literal["one_time", "recurring"] = Field(..., description="Payment type")
    amount: Decimal = Field(..., gt=0, description="Amount in dollars (e.g., 99.00)")
    interval: Optional[Literal["month", "year"]] = Field(
        None, description="Billing interval (required for recurring payments)"
    )
    interval_count: int = Field(
        default=1, ge=1, le=12, description="Number of intervals between charges"
    )
    description: Optional[str] = Field(None, max_length=500, description="Description of this payment option")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount has at most 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount can have at most 2 decimal places")
        return v

    @model_validator(mode="after")
    def validate_recurring_fields(self):
        """Validate that recurring payments have interval set."""
        if self.type == "recurring" and not self.interval:
            raise ValueError("interval is required for recurring payment options")
        if self.type == "one_time" and self.interval:
            raise ValueError("interval should not be set for one_time payment options")
        return self


class ClassCreate(BaseSchema):
    """Schema for creating a new class."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    ledger_code: Optional[str] = Field(None, max_length=50)
    school_code: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    website_link: Optional[str] = Field(None, max_length=500)
    program_id: str
    area_id: Optional[str] = None
    school_id: Optional[str] = None
    coach_id: Optional[str] = None
    class_type: ClassType

    # Schedule
    weekdays: Optional[List[Weekday]] = Field(None, min_length=1)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_date: date
    end_date: date

    # Registration Period
    registration_start_date: Optional[date] = None
    registration_end_date: Optional[date] = None

    # Recurrence Pattern
    recurrence_pattern: Optional[str] = Field(None, max_length=20)
    repeat_every_weeks: Optional[int] = Field(None, ge=1)

    # Capacity
    capacity: int = Field(..., gt=0)
    waitlist_enabled: bool = True

    # Pricing (Legacy - kept for backward compatibility)
    price: Decimal = Field(..., gt=0)
    membership_price: Optional[Decimal] = Field(None, gt=0)
    installments_enabled: bool = False

    # Payment Options (New flexible payment system)
    payment_options: Optional[List[PaymentOption]] = Field(
        None,
        description="Flexible payment options. If provided, Stripe Products/Prices will be auto-created.",
        min_length=1,
    )
    auto_create_stripe_prices: bool = Field(
        default=True,
        description="Automatically create Stripe Products and Prices from payment_options",
    )

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
    def validate_end_time(cls, v: Optional[time], info) -> Optional[time]:
        start_time = info.data.get("start_time")
        if v and start_time and v <= start_time:
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
    school_code: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    website_link: Optional[str] = Field(None, max_length=500)
    area_id: Optional[str] = None
    coach_id: Optional[str] = None
    class_type: Optional[ClassType] = None

    # Schedule
    weekdays: Optional[List[Weekday]] = Field(None, min_length=1)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Registration Period
    registration_start_date: Optional[date] = None
    registration_end_date: Optional[date] = None

    # Recurrence Pattern
    recurrence_pattern: Optional[str] = Field(None, max_length=20)
    repeat_every_weeks: Optional[int] = Field(None, ge=1)

    # Capacity
    capacity: Optional[int] = Field(None, gt=0)
    waitlist_enabled: Optional[bool] = None

    # Pricing (Legacy)
    price: Optional[Decimal] = Field(None, gt=0)
    membership_price: Optional[Decimal] = Field(None, gt=0)
    installments_enabled: Optional[bool] = None

    # Payment Options (New flexible payment system)
    payment_options: Optional[List[PaymentOption]] = Field(
        None,
        description="Flexible payment options. If provided, Stripe Products/Prices will be auto-created.",
        min_length=1,
    )
    auto_create_stripe_prices: bool = Field(
        default=True,
        description="Automatically create Stripe Products and Prices from payment_options",
    )

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
    school_code: Optional[str]
    image_url: Optional[str]
    website_link: Optional[str]
    program_id: str
    area_id: Optional[str]
    school_id: Optional[str]
    school_name: Optional[str]
    school_address: Optional[str] = None
    school_city: Optional[str] = None
    school_state: Optional[str] = None
    school_zip_code: Optional[str] = None
    coach_id: Optional[str]
    coach: Optional[Dict[str, Any]] = None
    class_type: ClassType

    # Schedule
    weekdays: Optional[List[str]]
    start_time: Optional[time]  # Will be serialized as 12-hour format with AM/PM
    end_time: Optional[time]  # Will be serialized as 12-hour format with AM/PM
    start_date: date
    end_date: date

    # Registration Period
    registration_start_date: Optional[date]
    registration_end_date: Optional[date]

    # Recurrence Pattern
    recurrence_pattern: Optional[str]
    repeat_every_weeks: Optional[int]

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

    # Payment Options
    payment_options: Optional[List[dict]] = None

    # Age requirements
    min_age: int
    max_age: int

    is_active: bool
    status: str = "active"  # Class lifecycle status: active, completed, cancelled
    created_at: datetime
    updated_at: datetime

    @field_serializer('start_time', 'end_time')
    def serialize_time_12hr(self, value: Optional[time]) -> Optional[str]:
        """Convert time to 12-hour format with AM/PM."""
        if value is None:
            return None

        hour = value.hour
        minute = value.minute

        # Determine AM/PM
        ampm = 'AM' if hour < 12 else 'PM'

        # Convert to 12-hour format
        hour_12 = hour % 12
        if hour_12 == 0:
            hour_12 = 12

        # Format with zero-padded minutes
        return f"{hour_12}:{minute:02d} {ampm}"

    @field_serializer('weekdays')
    def serialize_weekdays(self, value: Optional[List[str]]) -> Optional[List[str]]:
        """Convert weekday names to full capitalized names."""
        if value is None:
            return None

        day_mapping = {
            'monday': 'Monday',
            'tuesday': 'Tuesday',
            'wednesday': 'Wednesday',
            'thursday': 'Thursday',
            'friday': 'Friday',
            'saturday': 'Saturday',
            'sunday': 'Sunday'
        }

        return [day_mapping.get(day.lower(), day.capitalize()) for day in value]

    @model_validator(mode='before')
    @classmethod
    def extract_school_info(cls, data: Any) -> Any:
        """Extract school information from school relationship if available."""
        if isinstance(data, dict):
            # If data is already a dict, return as is
            return data

        # If it's a SQLAlchemy model instance, extract school fields
        if hasattr(data, 'school') and data.school:
            try:
                # Extract individual school fields
                object.__setattr__(data, 'school_name', getattr(data.school, 'name', None))
                object.__setattr__(data, 'school_address', getattr(data.school, 'address', None))
                object.__setattr__(data, 'school_city', getattr(data.school, 'city', None))
                object.__setattr__(data, 'school_state', getattr(data.school, 'state', None))
                object.__setattr__(data, 'school_zip_code', getattr(data.school, 'zip_code', None))
            except AttributeError:
                # If school attributes are not accessible, set to None
                object.__setattr__(data, 'school_name', None)
                object.__setattr__(data, 'school_address', None)
                object.__setattr__(data, 'school_city', None)
                object.__setattr__(data, 'school_state', None)
                object.__setattr__(data, 'school_zip_code', None)
        elif hasattr(data, 'school'):
            # School is None
            object.__setattr__(data, 'school_name', None)
            object.__setattr__(data, 'school_address', None)
            object.__setattr__(data, 'school_city', None)
            object.__setattr__(data, 'school_state', None)
            object.__setattr__(data, 'school_zip_code', None)

        # Extract coach information from coach relationship if available
        if hasattr(data, 'coach'):
            try:
                # Access coach directly (should be loaded via selectinload)
                coach_obj = data.coach
                if coach_obj is not None:
                    # Create a simple dict with coach info
                    coach_dict = {
                        'id': coach_obj.id,
                        'first_name': coach_obj.first_name,
                        'last_name': coach_obj.last_name,
                        'email': coach_obj.email,
                    }
                    # Override the coach attribute with dict before Pydantic processes it
                    data.__dict__['coach'] = coach_dict
                else:
                    data.__dict__['coach'] = None
            except (AttributeError, Exception) as e:
                # If there's any error accessing coach, set to None
                data.__dict__['coach'] = None

        return data


class ClassListResponse(BaseSchema):
    """Schema for paginated class list response."""

    items: List[ClassResponse]
    total: int
    skip: int
    limit: int
