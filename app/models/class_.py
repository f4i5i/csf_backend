import enum
from datetime import date, time
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    and_,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.program import Program, School
from core.db import Base, TimestampMixin


class ClassType(str, enum.Enum):
    """Type of class offering."""

    SHORT_TERM = "short_term"
    MEMBERSHIP = "membership"


class Weekday(str, enum.Enum):
    """Days of the week."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Class(Base, TimestampMixin):
    """Class model representing sports class offerings."""

    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ledger_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # For accounting export
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Class photo/logo
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id"), nullable=False
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id"), nullable=False
    )
    class_type: Mapped[ClassType] = mapped_column(Enum(ClassType), nullable=False)

    # Schedule
    weekdays: Mapped[List[str]] = mapped_column(
        JSON, nullable=False
    )  # ["monday", "wednesday"]
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Capacity
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_enrollment: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    waitlist_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    membership_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    installments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Age requirements
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age: Mapped[int] = mapped_column(Integer, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="classes")
    school: Mapped["School"] = relationship("School", back_populates="classes")

    @property
    def has_capacity(self) -> bool:
        """Check if class has available spots."""
        return self.current_enrollment < self.capacity

    @property
    def available_spots(self) -> int:
        """Get number of available spots."""
        return max(0, self.capacity - self.current_enrollment)

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Class"]:
        """Get class by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_filtered(
        cls,
        db_session: AsyncSession,
        program_id: Optional[str] = None,
        school_id: Optional[str] = None,
        area_id: Optional[str] = None,
        has_capacity: Optional[bool] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence["Class"], int]:
        """Get classes with optional filters and pagination."""
        conditions = [cls.is_active == True]

        if program_id:
            conditions.append(cls.program_id == program_id)
        if school_id:
            conditions.append(cls.school_id == school_id)
        if area_id:
            conditions.append(cls.school.has(School.area_id == area_id))
        if has_capacity is True:
            conditions.append(cls.current_enrollment < cls.capacity)
        if min_age is not None:
            conditions.append(cls.max_age >= min_age)
        if max_age is not None:
            conditions.append(cls.min_age <= max_age)

        # Get total count
        count_result = await db_session.execute(
            select(func.count(cls.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db_session.execute(
            select(cls)
            .where(and_(*conditions))
            .order_by(cls.start_date, cls.start_time)
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    @classmethod
    async def create_class(cls, db_session: AsyncSession, **kwargs) -> "Class":
        """Create a new class."""
        class_obj = cls(**kwargs)
        db_session.add(class_obj)
        await db_session.commit()
        await db_session.refresh(class_obj)
        return class_obj

    async def increment_enrollment(self, db_session: AsyncSession) -> bool:
        """Increment enrollment atomically if capacity is available."""
        model = type(self)
        stmt = (
            update(model)
            .where(
                model.id == self.id,
                model.current_enrollment < model.capacity,
            )
            .values(current_enrollment=model.current_enrollment + 1)
        )
        result = await db_session.execute(stmt)
        if result.rowcount == 0:
            return False
        await db_session.commit()
        await db_session.refresh(self)
        return True

    async def decrement_enrollment(self, db_session: AsyncSession) -> None:
        """Decrement enrollment atomically without going below zero."""
        model = type(self)
        stmt = (
            update(model)
            .where(model.id == self.id, model.current_enrollment > 0)
            .values(current_enrollment=model.current_enrollment - 1)
        )
        result = await db_session.execute(stmt)
        if result.rowcount > 0:
            await db_session.commit()
            await db_session.refresh(self)
