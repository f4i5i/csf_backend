"""Pydantic schemas for Stripe Product and Price management."""

from decimal import Decimal
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    """Schema for creating a Stripe Product."""

    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict, description="Product metadata")


class ProductUpdate(BaseModel):
    """Schema for updating a Stripe Product."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, str]] = None
    active: Optional[bool] = None


class ProductResponse(BaseModel):
    """Schema for Stripe Product response."""

    id: str
    name: str
    description: Optional[str]
    metadata: Dict[str, str]
    active: bool
    created: int

    model_config = {"from_attributes": True}


class PriceCreate(BaseModel):
    """Schema for creating a Stripe Price."""

    product_id: str = Field(..., description="Stripe Product ID")
    amount: Decimal = Field(..., gt=0, description="Price amount in dollars")
    currency: str = Field(default="usd", pattern="^[a-z]{3}$", description="Currency code")
    interval: str = Field(..., pattern="^(month|year)$", description="Billing interval")
    interval_count: int = Field(default=1, ge=1, le=12, description="Interval count")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict, description="Price metadata")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and has max 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        # Check decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount can have at most 2 decimal places")
        return v


class OneTimePriceCreate(BaseModel):
    """Schema for creating a one-time Stripe Price."""

    product_id: str = Field(..., description="Stripe Product ID")
    amount: Decimal = Field(..., gt=0, description="Price amount in dollars")
    currency: str = Field(default="usd", pattern="^[a-z]{3}$", description="Currency code")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict, description="Price metadata")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and has max 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount can have at most 2 decimal places")
        return v


class PriceUpdate(BaseModel):
    """Schema for updating a Stripe Price."""

    metadata: Optional[Dict[str, str]] = None
    active: Optional[bool] = None


class PriceResponse(BaseModel):
    """Schema for Stripe Price response."""

    id: str
    product: str
    amount: Decimal
    currency: str
    interval: Optional[str]
    interval_count: Optional[int]
    metadata: Dict[str, str]
    active: bool

    model_config = {"from_attributes": True}


class ClassProductCreate(BaseModel):
    """Schema for creating Stripe Product for a class."""

    class_id: str = Field(..., description="Class ID")


class ClassPricesCreate(BaseModel):
    """Schema for creating Stripe Prices for a class."""

    class_id: str = Field(..., description="Class ID")
    create_monthly: bool = Field(default=False, description="Create monthly price")
    create_quarterly: bool = Field(default=False, description="Create quarterly price")
    create_annual: bool = Field(default=False, description="Create annual price")


class ClassProductSyncRequest(BaseModel):
    """Schema for syncing class with Stripe."""

    class_id: str = Field(..., description="Class ID")


class ClassProductSyncResponse(BaseModel):
    """Schema for class Stripe sync response."""

    product: ProductResponse
    prices: Dict[str, PriceResponse]

    model_config = {"from_attributes": True}
