from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, field_validator, model_validator

from app.models.user import Role
from app.schemas.base import BaseSchema
from app.utils.email_validator import is_disposable_email


class UserCreate(BaseSchema):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email and block disposable email addresses."""
        if is_disposable_email(v):
            raise ValueError("Disposable email addresses are not allowed")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseSchema):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserResponse(BaseSchema):
    """Schema for user response."""

    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: Role
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseSchema):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseSchema):
    """Schema for JWT token payload."""

    sub: str  # user_id
    role: str
    exp: int
    type: str  # "access" or "refresh"


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token request."""

    refresh_token: str


class GoogleAuthRequest(BaseSchema):
    """Schema for Google OAuth authentication."""

    token: str


class ForgotPasswordRequest(BaseSchema):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    """Schema for reset password request."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# ============== Admin User Management Schemas ==============


class AdminUserCreate(BaseSchema):
    """Schema for admin to create a new user."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: Role = Role.PARENT
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email and block disposable email addresses."""
        if is_disposable_email(v):
            raise ValueError("Disposable email addresses are not allowed")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class AdminUserUpdate(BaseSchema):
    """Schema for admin to update a user."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserListResponse(BaseSchema):
    """Schema for paginated user list response."""

    items: list[UserResponse]
    total: int
    skip: int = 0
    limit: int = 20
