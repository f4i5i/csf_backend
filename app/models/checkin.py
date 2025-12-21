"""Check-in model for tracking student arrivals."""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.enrollment import Enrollment


class CheckIn(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Student check-in record for a class session."""

    __tablename__ = "checkins"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment")
    class_: Mapped["Class"] = relationship("Class")

    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "class_id", "check_in_date", name="unique_checkin_per_date"
        ),
    )

    @classmethod
    async def get_by_class(
        cls, db_session: AsyncSession, class_id: str, check_in_date: Optional[date] = None
    ) -> Sequence["CheckIn"]:
        """Get all check-ins for a class, optionally filtered by date."""
        conditions = [cls.class_id == class_id]
        if check_in_date:
            conditions.append(cls.check_in_date == check_in_date)

        stmt = (
            select(cls)
            .where(*conditions)
            .order_by(cls.checked_in_at.asc())
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_by_enrollment_date(
        cls, db_session: AsyncSession, enrollment_id: str, check_in_date: date
    ) -> Optional["CheckIn"]:
        """Get check-in for enrollment on specific date."""
        stmt = select(cls).where(
            cls.enrollment_id == enrollment_id, cls.check_in_date == check_in_date
        )
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def check_in_student(
        cls,
        db_session: AsyncSession,
        enrollment_id: str,
        class_id: str,
        check_in_date: date,
        is_late: bool = False,
        organization_id: str = None,
    ) -> "CheckIn":
        """Check in a student for a class session."""
        # Check if already checked in
        stmt = select(cls).where(
            cls.enrollment_id == enrollment_id,
            cls.class_id == class_id,
            cls.check_in_date == check_in_date,
        )
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing  # Already checked in

        # Create check-in record
        checkin = cls(
            enrollment_id=enrollment_id,
            class_id=class_id,
            check_in_date=check_in_date,
            is_late=is_late,
            organization_id=organization_id,
        )
        db_session.add(checkin)
        return checkin

    @classmethod
    async def bulk_check_in(
        cls,
        db_session: AsyncSession,
        class_id: str,
        enrollment_ids: list[str],
        check_in_date: date,
        organization_id: str = None,
    ) -> list["CheckIn"]:
        """Bulk check in multiple students."""
        checkins = []
        for enrollment_id in enrollment_ids:
            checkin = await cls.check_in_student(
                db_session, enrollment_id, class_id, check_in_date,
                organization_id=organization_id
            )
            checkins.append(checkin)

        await db_session.commit()
        return checkins

    @classmethod
    async def get_check_in_status(
        cls, db_session: AsyncSession, class_id: str, check_in_date: date, enrollment_ids: list[str]
    ) -> dict[str, bool]:
        """Get check-in status for multiple enrollments on a specific date.

        Returns dict of enrollment_id -> is_checked_in
        """
        stmt = select(cls.enrollment_id).where(
            cls.class_id == class_id,
            cls.check_in_date == check_in_date,
            cls.enrollment_id.in_(enrollment_ids),
        )
        result = await db_session.execute(stmt)
        checked_in_ids = {row[0] for row in result.all()}

        return {
            enrollment_id: enrollment_id in checked_in_ids
            for enrollment_id in enrollment_ids
        }
