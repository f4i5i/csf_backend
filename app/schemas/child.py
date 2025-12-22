from datetime import date, datetime
from typing import List, Optional

from pydantic import EmailStr, Field, field_validator

from app.models.child import Grade, HowHeardAboutUs, JerseySize
from app.schemas.base import BaseSchema


class EmergencyContactCreate(BaseSchema):
    """Schema for creating an emergency contact."""

    name: str = Field(..., min_length=1, max_length=200)
    relation: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=1, max_length=20)
    email: Optional[EmailStr] = None
    is_primary: bool = False


class EmergencyContactUpdate(BaseSchema):
    """Schema for updating an emergency contact."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    relation: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    email: Optional[EmailStr] = None
    is_primary: Optional[bool] = None


class EmergencyContactResponse(BaseSchema):
    """Schema for emergency contact response."""

    id: str
    child_id: str
    name: str
    relation: str
    phone: str
    email: Optional[str]
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ChildCreate(BaseSchema):
    """Schema for creating a child."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date

    jersey_size: Optional[JerseySize] = None
    grade: Optional[Grade] = None

    # Medical info
    medical_conditions: Optional[str] = None
    has_no_medical_conditions: bool = False

    # After school
    after_school_attendance: bool = False
    after_school_program: Optional[str] = Field(None, max_length=200)

    # Insurance
    health_insurance_number: Optional[str] = Field(None, max_length=100)

    # Marketing
    how_heard_about_us: Optional[HowHeardAboutUs] = None
    how_heard_other_text: Optional[str] = Field(None, max_length=200)

    # Coach notes
    additional_notes: Optional[str] = None

    # Optional emergency contacts on creation
    emergency_contacts: Optional[List[EmergencyContactCreate]] = Field(None, max_length=3)

    @field_validator("emergency_contacts")
    @classmethod
    def validate_emergency_contacts(cls, v: Optional[List[EmergencyContactCreate]]) -> Optional[List[EmergencyContactCreate]]:
        if v and len(v) > 3:
            raise ValueError("Maximum 3 emergency contacts allowed")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v

    @field_validator("how_heard_other_text")
    @classmethod
    def validate_other_text(cls, v: Optional[str], info) -> Optional[str]:
        how_heard = info.data.get("how_heard_about_us")
        if how_heard == HowHeardAboutUs.OTHER and not v:
            raise ValueError("Please specify how you heard about us")
        return v


class ChildUpdate(BaseSchema):
    """Schema for updating a child."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None

    jersey_size: Optional[JerseySize] = None
    grade: Optional[Grade] = None

    medical_conditions: Optional[str] = None
    has_no_medical_conditions: Optional[bool] = None

    after_school_attendance: Optional[bool] = None
    after_school_program: Optional[str] = Field(None, max_length=200)

    health_insurance_number: Optional[str] = Field(None, max_length=100)

    how_heard_about_us: Optional[HowHeardAboutUs] = None
    how_heard_other_text: Optional[str] = Field(None, max_length=200)

    additional_notes: Optional[str] = None

    is_active: Optional[bool] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v and v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v


class ChildEnrollmentInfo(BaseSchema):
    """Schema for child's enrollment information."""

    enrollment_id: str
    class_id: str
    class_name: str
    school_id: Optional[str]
    school_name: Optional[str]
    weekdays: Optional[List[str]]
    status: str  # Enrollment status: pending, active, completed, cancelled
    class_status: str = "active"  # Class lifecycle status: active, completed, cancelled
    enrolled_at: Optional[datetime]


class ChildResponse(BaseSchema):
    """Schema for child response."""

    id: str
    user_id: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: date
    age: int

    jersey_size: Optional[JerseySize]
    grade: Optional[Grade]

    # Medical info (decrypted for authorized users)
    medical_conditions: Optional[str]
    has_no_medical_conditions: bool
    has_medical_alert: bool

    after_school_attendance: bool
    after_school_program: Optional[str]

    # Insurance (masked or shown based on permissions)
    health_insurance_number: Optional[str]

    how_heard_about_us: Optional[HowHeardAboutUs] = None
    how_heard_other_text: Optional[str] = None

    additional_notes: Optional[str] = None

    is_active: bool
    created_at: datetime
    updated_at: datetime

    emergency_contacts: List[EmergencyContactResponse] = []
    enrollments: List[ChildEnrollmentInfo] = []


class ChildListResponse(BaseSchema):
    """Schema for paginated child list response."""

    items: List[ChildResponse]
    total: int
