"""Payment and Installment models for transaction tracking."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Date,
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

from core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class PaymentType(str, enum.Enum):
    """Type of payment."""

    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    INSTALLMENT = "installment"


class PaymentStatus(str, enum.Enum):
    """Status of a payment."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class Payment(Base, TimestampMixin):
    """Payment record for transactions."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # Payment details
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), default="usd", nullable=False
    )

    # Stripe references
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Metadata
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    user: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Payment"]:
        """Get payment by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_payment_intent(
        cls, db_session: AsyncSession, payment_intent_id: str
    ) -> Optional["Payment"]:
        """Get payment by Stripe payment intent ID."""
        result = await db_session.execute(
            select(cls).where(cls.stripe_payment_intent_id == payment_intent_id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_order_id(
        cls, db_session: AsyncSession, order_id: str
    ) -> Sequence["Payment"]:
        """Get all payments for an order."""
        result = await db_session.execute(
            select(cls)
            .where(cls.order_id == order_id)
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_by_user_id(
        cls, db_session: AsyncSession, user_id: str, limit: int = 50
    ) -> Sequence["Payment"]:
        """Get payments for a user."""
        result = await db_session.execute(
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def create_payment(
        cls, db_session: AsyncSession, **kwargs
    ) -> "Payment":
        """Create a new payment record."""
        payment = cls(**kwargs)
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)
        return payment

    async def mark_succeeded(self, db_session: AsyncSession) -> None:
        """Mark payment as succeeded."""
        self.status = PaymentStatus.SUCCEEDED
        self.paid_at = func.now()
        await db_session.commit()

    async def mark_failed(self, db_session: AsyncSession, reason: str = None) -> None:
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED
        self.failure_reason = reason
        await db_session.commit()


class InstallmentPlanStatus(str, enum.Enum):
    """Status of an installment plan."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFAULTED = "defaulted"


class InstallmentFrequency(str, enum.Enum):
    """Frequency of installment payments."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class InstallmentPlan(Base, TimestampMixin):
    """Installment plan for split payments."""

    __tablename__ = "installment_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # Plan details
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    num_installments: Mapped[int] = mapped_column(Integer, nullable=False)
    installment_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    frequency: Mapped[InstallmentFrequency] = mapped_column(
        Enum(InstallmentFrequency), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Stripe
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Status
    status: Mapped[InstallmentPlanStatus] = mapped_column(
        Enum(InstallmentPlanStatus), default=InstallmentPlanStatus.ACTIVE, nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    user: Mapped["User"] = relationship("User")
    installment_payments: Mapped[List["InstallmentPayment"]] = relationship(
        "InstallmentPayment", back_populates="installment_plan", cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["InstallmentPlan"]:
        """Get installment plan by ID."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.installment_payments))
            .where(cls.id == id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_user_id(
        cls, db_session: AsyncSession, user_id: str
    ) -> Sequence["InstallmentPlan"]:
        """Get all installment plans for a user."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.installment_payments))
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def create_plan(
        cls, db_session: AsyncSession, **kwargs
    ) -> "InstallmentPlan":
        """Create a new installment plan."""
        plan = cls(**kwargs)
        db_session.add(plan)
        await db_session.commit()
        await db_session.refresh(plan)
        return plan

    @property
    def paid_count(self) -> int:
        """Count of paid installments."""
        return sum(
            1 for p in self.installment_payments
            if p.status == InstallmentPaymentStatus.PAID
        )

    @property
    def is_complete(self) -> bool:
        """Check if all installments are paid."""
        return self.paid_count >= self.num_installments


class InstallmentPaymentStatus(str, enum.Enum):
    """Status of an individual installment payment."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    SKIPPED = "skipped"


class InstallmentPayment(Base, TimestampMixin):
    """Individual installment payment record."""

    __tablename__ = "installment_payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    installment_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("installment_plans.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("payments.id"), nullable=True
    )

    # Payment details
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[InstallmentPaymentStatus] = mapped_column(
        Enum(InstallmentPaymentStatus),
        default=InstallmentPaymentStatus.PENDING,
        nullable=False,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    installment_plan: Mapped["InstallmentPlan"] = relationship(
        "InstallmentPlan", back_populates="installment_payments"
    )
    payment: Mapped[Optional["Payment"]] = relationship("Payment")

    @classmethod
    async def get_pending_due(
        cls, db_session: AsyncSession, as_of_date: date = None
    ) -> Sequence["InstallmentPayment"]:
        """Get pending installments due on or before a date."""
        if as_of_date is None:
            as_of_date = date.today()

        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.installment_plan))
            .where(
                cls.status == InstallmentPaymentStatus.PENDING,
                cls.due_date <= as_of_date,
            )
            .order_by(cls.due_date)
        )
        return result.scalars().all()
