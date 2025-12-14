"""Enrollment model for child-to-class registration."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.child import Child
    from app.models.class_ import Class
    from app.models.user import User


class EnrollmentStatus(str, enum.Enum):
    """Status of an enrollment."""

    PENDING = "pending"  # Awaiting payment
    ACTIVE = "active"  # Paid and enrolled
    CANCELLED = "cancelled"  # Cancelled by user
    COMPLETED = "completed"  # Class finished
    WAITLISTED = "waitlisted"  # On waitlist


class WaitlistPriority(str, enum.Enum):
    """Priority level for waitlisted enrollments."""

    PRIORITY = "priority"  # Auto-charge when spot opens (requires CC)
    REGULAR = "regular"  # 12-hour claim window


class Enrollment(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Enrollment record linking a child to a class."""

    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign keys
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus), default=EnrollmentStatus.PENDING, nullable=False
    )

    # Timestamps
    enrolled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Waitlist priority system
    waitlist_priority: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )  # "priority" or "regular", null if not waitlisted
    auto_promote: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Auto-charge and promote for priority waitlist
    claim_window_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Expiration time for regular waitlist claim window
    promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When promoted from waitlist to active
    waitlist_payment_method_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Stripe payment method used for priority auto-charge
    waitlist_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # Draft order ID associated with waitlist entry

    # Pricing snapshot at enrollment time
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    final_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )

    # Subscription tracking (for recurring billing)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    subscription_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # active, canceled, past_due, unpaid, etc.
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When user requested cancellation
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # If true, subscription will cancel at period end

    __table_args__ = (
        # Enforce uniqueness of child/class within an organization
        UniqueConstraint(
            "organization_id",
            "child_id",
            "class_id",
            name="uq_enrollment_child_class_organization",
        ),
    )

    # Relationships
    child: Mapped["Child"] = relationship("Child", lazy="selectin")
    class_: Mapped["Class"] = relationship("Class", lazy="selectin")
    user: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Enrollment"]:
        """Get enrollment by ID."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.class_))
            .where(cls.id == id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_user_id(
        cls, db_session: AsyncSession, user_id: str, status: EnrollmentStatus = None
    ) -> Sequence["Enrollment"]:
        """Get all enrollments for a user."""
        conditions = [cls.user_id == user_id]
        if status:
            conditions.append(cls.status == status)

        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.class_))
            .where(*conditions)
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_by_child_and_class(
        cls, db_session: AsyncSession, child_id: str, class_id: str
    ) -> Optional["Enrollment"]:
        """Check if child is already enrolled in a class."""
        result = await db_session.execute(
            select(cls).where(
                cls.child_id == child_id,
                cls.class_id == class_id,
                cls.status.in_([EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE]),
            )
        )
        return result.scalars().first()

    @classmethod
    async def get_active_by_class(
        cls, db_session: AsyncSession, class_id: str
    ) -> Sequence["Enrollment"]:
        """Get all active enrollments for a class (roster)."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.user))
            .where(cls.class_id == class_id, cls.status == EnrollmentStatus.ACTIVE)
            .order_by(cls.enrolled_at)
        )
        return result.scalars().all()

    @classmethod
    async def create_enrollment(
        cls, db_session: AsyncSession, **kwargs
    ) -> "Enrollment":
        """Create a new enrollment."""
        enrollment = cls(**kwargs)
        db_session.add(enrollment)
        await db_session.commit()
        await db_session.refresh(enrollment)
        return enrollment

    async def activate(self, db_session: AsyncSession) -> None:
        """Activate enrollment after payment."""
        self.status = EnrollmentStatus.ACTIVE
        self.enrolled_at = func.now()
        await db_session.commit()

    async def cancel(
        self, db_session: AsyncSession, reason: str = None
    ) -> None:
        """Cancel enrollment."""
        self.status = EnrollmentStatus.CANCELLED
        self.cancelled_at = func.now()
        self.cancellation_reason = reason
        await db_session.commit()

    @property
    def is_cancellable(self) -> bool:
        """Check if enrollment can be cancelled."""
        return self.status in [EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE]

    @property
    def days_since_enrollment(self) -> int:
        """Calculate days since enrollment (for refund policy)."""
        if not self.enrolled_at:
            return 0
        delta = datetime.now(self.enrolled_at.tzinfo) - self.enrolled_at
        return delta.days

    @classmethod
    async def get_waitlisted_by_class(
        cls, db_session: AsyncSession, class_id: str, priority: str = None
    ) -> Sequence["Enrollment"]:
        """Get waitlisted enrollments for a class, ordered by priority and created_at."""
        conditions = [
            cls.class_id == class_id,
            cls.status == EnrollmentStatus.WAITLISTED,
        ]
        if priority:
            conditions.append(cls.waitlist_priority == priority)

        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.user))
            .where(*conditions)
            .order_by(
                # Priority waitlist first
                cls.waitlist_priority.desc(),
                # Then by creation time (FIFO)
                cls.created_at,
            )
        )
        return result.scalars().all()

    @classmethod
    async def get_next_in_waitlist(
        cls, db_session: AsyncSession, class_id: str
    ) -> Optional["Enrollment"]:
        """Get next person in waitlist for a class (priority first, then FIFO)."""
        enrollments = await cls.get_waitlisted_by_class(db_session, class_id)
        return enrollments[0] if enrollments else None

    async def promote_from_waitlist(
        self, db_session: AsyncSession, auto_charged: bool = False
    ) -> None:
        """Promote enrollment from waitlist to active."""
        if self.status != EnrollmentStatus.WAITLISTED:
            raise ValueError("Can only promote waitlisted enrollments")

        self.status = EnrollmentStatus.ACTIVE
        self.promoted_at = func.now()
        self.enrolled_at = func.now()
        self.waitlist_priority = None
        self.auto_promote = False
        self.claim_window_expires_at = None
        await db_session.commit()

    async def start_claim_window(self, db_session: AsyncSession) -> None:
        """Start 12-hour claim window for regular waitlist."""
        if self.status != EnrollmentStatus.WAITLISTED:
            raise ValueError("Can only start claim window for waitlisted enrollments")
        if self.waitlist_priority != WaitlistPriority.REGULAR.value:
            raise ValueError("Claim windows are only for regular waitlist")

        # Set expiration to 12 hours from now
        from datetime import timedelta

        self.claim_window_expires_at = datetime.now(datetime.UTC) + timedelta(hours=12)
        await db_session.commit()

    async def claim_waitlist_spot(self, db_session: AsyncSession) -> None:
        """Claim a regular waitlist spot (user completed payment)."""
        if self.status != EnrollmentStatus.WAITLISTED:
            raise ValueError("Can only claim waitlisted enrollments")
        if self.waitlist_priority != WaitlistPriority.REGULAR.value:
            raise ValueError("Only regular waitlist can be claimed")
        if not self.claim_window_expires_at:
            raise ValueError("No active claim window")
        if datetime.now(datetime.UTC) > self.claim_window_expires_at:
            raise ValueError("Claim window has expired")

        await self.promote_from_waitlist(db_session, auto_charged=False)

    async def expire_claim_window(self, db_session: AsyncSession) -> None:
        """Expire an unclaimed regular waitlist spot."""
        if self.status != EnrollmentStatus.WAITLISTED:
            return  # Already processed

        self.status = EnrollmentStatus.CANCELLED
        self.cancelled_at = func.now()
        self.cancellation_reason = "Claim window expired (12 hours)"
        await db_session.commit()

    async def schedule_subscription_cancellation(self, db_session: AsyncSession) -> None:
        """Schedule subscription cancellation at period end."""
        if not self.stripe_subscription_id:
            raise ValueError("No active subscription to cancel")

        self.cancel_at_period_end = True
        self.subscription_cancelled_at = func.now()
        await db_session.commit()

    async def cancel_subscription_immediately(self, db_session: AsyncSession) -> None:
        """Cancel subscription immediately (will trigger proration)."""
        if not self.stripe_subscription_id:
            raise ValueError("No active subscription to cancel")

        self.subscription_status = "canceled"
        self.subscription_cancelled_at = func.now()
        await db_session.commit()

    async def update_subscription_status(
        self, db_session: AsyncSession, status: str,
        period_start: datetime = None, period_end: datetime = None
    ) -> None:
        """Update subscription status from Stripe webhook."""
        self.subscription_status = status
        if period_start:
            self.current_period_start = period_start
        if period_end:
            self.current_period_end = period_end
        await db_session.commit()

    @property
    def is_subscription_active(self) -> bool:
        """Check if enrollment has an active subscription."""
        return (
            self.stripe_subscription_id is not None
            and self.subscription_status == "active"
        )

    @classmethod
    async def get_by_subscription_id(
        cls, db_session: AsyncSession, subscription_id: str
    ) -> Optional["Enrollment"]:
        """Get enrollment by Stripe subscription ID."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.class_), selectinload(cls.user))
            .where(cls.stripe_subscription_id == subscription_id)
        )
        return result.scalars().first()

    @classmethod
    async def get_active_subscriptions_by_user(
        cls, db_session: AsyncSession, user_id: str
    ) -> Sequence["Enrollment"]:
        """Get all active subscriptions for a user."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.child), selectinload(cls.class_))
            .where(
                cls.user_id == user_id,
                cls.stripe_subscription_id.isnot(None),
                cls.subscription_status == "active"
            )
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_expired_claim_windows(
        cls, db_session: AsyncSession
    ) -> Sequence["Enrollment"]:
        """Get enrollments with expired claim windows that need processing."""
        now = datetime.now(datetime.UTC)
        result = await db_session.execute(
            select(cls)
            .where(
                cls.status == EnrollmentStatus.WAITLISTED,
                cls.waitlist_priority == WaitlistPriority.REGULAR.value,
                cls.claim_window_expires_at.isnot(None),
                cls.claim_window_expires_at < now,
            )
            .options(selectinload(cls.child), selectinload(cls.user))
        )
        return result.scalars().all()
