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
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.models.program import Program, School
from app.models.user import User
from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin


class ClassType(str, enum.Enum):
    """Type of class offering."""

    SHORT_TERM = "short_term"
    MEMBERSHIP = "membership"
    ONE_TIME = "one-time"  # Single session class


class BillingModel(str, enum.Enum):
    """Billing model for class pricing."""

    ONE_TIME = "one_time"  # Single payment
    MONTHLY = "monthly"  # Recurring monthly subscription
    QUARTERLY = "quarterly"  # Recurring quarterly subscription
    ANNUAL = "annual"  # Recurring annual subscription


class Weekday(str, enum.Enum):
    """Days of the week."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Class(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
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
    school_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # School ledger code
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Class photo/logo
    website_link: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # External class information URL
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id"), nullable=False, index=True
    )
    area_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # Location/Area identifier
    school_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("schools.id"), nullable=True, index=True
    )
    coach_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )  # Coach/instructor assignment
    class_type: Mapped[ClassType] = mapped_column(
        Enum(ClassType, name="classtype", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Schedule
    weekdays: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )  # ["monday", "wednesday"]
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Registration Period
    registration_start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )  # When registration opens
    registration_end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )  # When registration closes

    # Recurrence Pattern
    recurrence_pattern: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # weekly, monthly, one-time
    repeat_every_weeks: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=1
    )  # Number of weeks between repetitions

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

    # Billing model (determines payment structure)
    billing_model: Mapped[BillingModel] = mapped_column(
        Enum(BillingModel, native_enum=False), default=BillingModel.ONE_TIME, nullable=False
    )
    monthly_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    quarterly_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    annual_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Payment Options (JSON array for flexible payment configurations)
    # Stores: [{"name": str, "type": str, "amount": float, "interval": str|null, "interval_count": int}]
    # Example: [{"name": "Full Payment", "type": "one_time", "amount": 299.00, "interval": null, "interval_count": 1}]
    payment_options: Mapped[Optional[List[dict]]] = mapped_column(
        JSON, nullable=True
    )

    # Stripe Product/Price IDs (for subscription billing)
    stripe_product_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_monthly_price_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_quarterly_price_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_annual_price_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Age requirements
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age: Mapped[int] = mapped_column(Integer, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="classes")
    school: Mapped[Optional["School"]] = relationship("School", back_populates="classes")
    coach: Mapped[Optional["User"]] = relationship(
        "User", back_populates="classes_coached", foreign_keys=[coach_id]
    )

    @property
    def has_capacity(self) -> bool:
        """Check if class has available spots."""
        return self.current_enrollment < self.capacity

    @property
    def available_spots(self) -> int:
        """Get number of available spots."""
        return max(0, self.capacity - self.current_enrollment)

    def get_subscription_price(self) -> Optional[Decimal]:
        """Get subscription price based on billing model."""
        if self.billing_model == BillingModel.ONE_TIME:
            return None
        elif self.billing_model == BillingModel.MONTHLY:
            return self.monthly_price or self.membership_price
        elif self.billing_model == BillingModel.QUARTERLY:
            return self.quarterly_price
        elif self.billing_model == BillingModel.ANNUAL:
            return self.annual_price
        return None

    def get_stripe_price_id(self) -> Optional[str]:
        """Get Stripe Price ID based on billing model."""
        if self.billing_model == BillingModel.ONE_TIME:
            return None
        elif self.billing_model == BillingModel.MONTHLY:
            return self.stripe_monthly_price_id
        elif self.billing_model == BillingModel.QUARTERLY:
            return self.stripe_quarterly_price_id
        elif self.billing_model == BillingModel.ANNUAL:
            return self.stripe_annual_price_id
        return None

    @property
    def is_subscription_based(self) -> bool:
        """Check if this class uses subscription billing."""
        return self.billing_model != BillingModel.ONE_TIME

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Class"]:
        """Get class by ID."""
        result = await db_session.execute(
            select(cls).options(selectinload(cls.school), selectinload(cls.coach)).where(cls.id == id)
        )
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
        search: Optional[str] = None,
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
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    cls.name.ilike(search_pattern),
                    cls.description.ilike(search_pattern)
                )
            )

        # Get total count
        count_result = await db_session.execute(
            select(func.count(cls.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.school), selectinload(cls.coach))
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

    async def sync_enrollment_count(self, db_session: AsyncSession) -> int:
        """Recalculate and sync current_enrollment with actual ACTIVE and PENDING enrollments."""
        from app.models.enrollment import Enrollment, EnrollmentStatus

        # Count active AND pending enrollments for this class
        # PENDING enrollments reserve spots during checkout to prevent overbooking
        count_result = await db_session.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.class_id == self.id,
                Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING]),
                Enrollment.is_deleted == False,
            )
        )
        actual_count = count_result.scalar() or 0

        # Update if different
        if self.current_enrollment != actual_count:
            self.current_enrollment = actual_count
            await db_session.commit()
            await db_session.refresh(self)

        return actual_count
