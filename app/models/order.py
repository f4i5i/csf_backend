"""Order and OrderLineItem models for purchase tracking."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.discount import DiscountCode
    from app.models.enrollment import Enrollment
    from app.models.user import User


class OrderStatus(str, enum.Enum):
    """Status of an order."""

    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Order(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Order record for purchases."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False
    )

    # Pricing
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )

    # Stripe references
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Timestamps
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    line_items: Mapped[List["OrderLineItem"]] = relationship(
        "OrderLineItem", back_populates="order", cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Order"]:
        """Get order by ID with line items."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.line_items))
            .where(cls.id == id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_payment_intent(
        cls, db_session: AsyncSession, payment_intent_id: str
    ) -> Optional["Order"]:
        """Get order by Stripe payment intent ID."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.line_items))
            .where(cls.stripe_payment_intent_id == payment_intent_id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_user_id(
        cls, db_session: AsyncSession, user_id: str, limit: int = 50
    ) -> Sequence["Order"]:
        """Get orders for a user."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.line_items))
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def create_order(
        cls, db_session: AsyncSession, **kwargs
    ) -> "Order":
        """Create a new order."""
        order = cls(**kwargs)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        return order

    async def mark_paid(self, db_session: AsyncSession) -> None:
        """Mark order as paid."""
        self.status = OrderStatus.PAID
        self.paid_at = func.now()
        await db_session.commit()

    async def mark_refunded(self, db_session: AsyncSession) -> None:
        """Mark order as refunded."""
        self.status = OrderStatus.REFUNDED
        await db_session.commit()

    def calculate_totals(self) -> None:
        """Recalculate order totals from line items."""
        self.subtotal = sum(item.line_total for item in self.line_items)
        self.discount_total = sum(item.discount_amount for item in self.line_items)
        self.total = self.subtotal - self.discount_total


class OrderLineItem(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Individual line item in an order."""

    __tablename__ = "order_line_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrollment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("enrollments.id"), nullable=True, index=True
    )

    # Item details
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )

    # Discount
    discount_code_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("discount_codes.id"), nullable=True, index=True
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    discount_description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )

    # Calculated
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="line_items")
    enrollment: Mapped[Optional["Enrollment"]] = relationship("Enrollment")
    discount_code: Mapped[Optional["DiscountCode"]] = relationship("DiscountCode")

    def calculate_total(self) -> None:
        """Calculate line total."""
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount
