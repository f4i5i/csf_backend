"""Enrollment model for child-to-class registration."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
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


class Enrollment(Base, TimestampMixin):
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
