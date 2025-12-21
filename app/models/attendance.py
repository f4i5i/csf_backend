"""Attendance tracking models with streak calculation."""

import enum
from datetime import date
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
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
    from app.models.class_ import Class
    from app.models.enrollment import Enrollment
    from app.models.user import User


class AttendanceStatus(str, enum.Enum):
    """Status of attendance."""

    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"


class Attendance(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Attendance record for class sessions."""

    __tablename__ = "attendances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, native_enum=False), nullable=False
    )
    marked_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment")
    class_: Mapped["Class"] = relationship("Class")
    marker: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "enrollment_id",
            "class_id",
            "date",
            name="unique_enrollment_class_date_attendance",
        ),
        Index("idx_attendance_date_enrollment", "enrollment_id", "date"),
    )

    @classmethod
    async def get_streak(cls, db_session: AsyncSession, enrollment_id: str) -> int:
        """
        Calculate current attendance streak for an enrollment.

        Counts consecutive PRESENT statuses from most recent date backwards.
        """
        stmt = (
            select(cls.date, cls.status)
            .where(cls.enrollment_id == enrollment_id)
            .order_by(cls.date.desc())
        )
        result = await db_session.execute(stmt)
        records = result.all()

        if not records:
            return 0

        streak = 0
        for record in records:
            if record.status == AttendanceStatus.PRESENT:
                streak += 1
            else:
                break  # Streak broken

        return streak

    @classmethod
    async def get_by_enrollment(
        cls,
        db_session: AsyncSession,
        enrollment_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence["Attendance"]:
        """Get attendance history for an enrollment."""
        stmt = (
            select(cls)
            .where(cls.enrollment_id == enrollment_id)
            .options(selectinload(cls.class_))
            .order_by(cls.date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def count_by_enrollment(
        cls, db_session: AsyncSession, enrollment_id: str
    ) -> int:
        """Count attendance records for an enrollment."""
        stmt = select(func.count(cls.id)).where(cls.enrollment_id == enrollment_id)
        result = await db_session.execute(stmt)
        return result.scalar() or 0

    @classmethod
    async def mark_bulk(
        cls,
        db_session: AsyncSession,
        class_id: str,
        attendance_data: List[dict],
        marked_by: str,
        organization_id: str = None,
    ) -> None:
        """Bulk mark attendance for a class session."""
        for data in attendance_data:
            # Check if already marked
            stmt = select(cls).where(
                cls.enrollment_id == data["enrollment_id"],
                cls.class_id == class_id,
                cls.date == data["date"],
            )
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.status = data["status"]
                existing.notes = data.get("notes")
            else:
                # Create new
                attendance = cls(
                    enrollment_id=data["enrollment_id"],
                    class_id=class_id,
                    date=data["date"],
                    status=data["status"],
                    marked_by=marked_by,
                    notes=data.get("notes"),
                    organization_id=organization_id,
                )
                db_session.add(attendance)

        await db_session.commit()

    @classmethod
    async def get_by_class(
        cls, db_session: AsyncSession, class_id: str, attendance_date: Optional[date] = None
    ) -> Sequence["Attendance"]:
        """Get all attendance for a class, optionally filtered by date."""
        conditions = [cls.class_id == class_id]
        if attendance_date:
            conditions.append(cls.date == attendance_date)

        stmt = (
            select(cls)
            .where(*conditions)
            .options(
                selectinload(cls.enrollment).selectinload("child")  # type: ignore
            )
            .order_by(cls.date.desc(), cls.created_at)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()
