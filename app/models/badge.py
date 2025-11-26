"""Badge and achievement models."""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.user import User


class BadgeCategory(str, enum.Enum):
    """Category of badge."""

    ATTENDANCE = "attendance"
    ACHIEVEMENT = "achievement"
    SKILL = "skill"
    MILESTONE = "milestone"


class BadgeCriteria(str, enum.Enum):
    """Badge unlock criteria."""

    # Attendance-based (auto-award)
    PERFECT_ATTENDANCE_5 = "perfect_attendance_5"
    PERFECT_ATTENDANCE_10 = "perfect_attendance_10"
    PERFECT_ATTENDANCE_20 = "perfect_attendance_20"
    EARLY_BIRD = "early_bird"
    PUNCTUALITY_KING = "punctuality_king"

    # Milestone-based (auto-award)
    FIRST_CLASS = "first_class"
    FIRST_MONTH = "first_month"
    FIRST_SEASON = "first_season"

    # Manual awards (coach-given)
    FIRST_GOAL = "first_goal"
    HAT_TRICK = "hat_trick"
    TEAM_PLAYER = "team_player"
    GOAL_MACHINE = "goal_machine"
    ASSIST_MASTER = "assist_master"
    DEFENSIVE_WALL = "defensive_wall"
    SPEEDSTER = "speedster"
    ENDURANCE = "endurance"
    SKILLS_MASTER = "skills_master"
    LEADERSHIP = "leadership"


class Badge(Base, TimestampMixin):
    """Badge definition."""

    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[BadgeCategory] = mapped_column(Enum(BadgeCategory), nullable=False)
    criteria: Mapped[BadgeCriteria] = mapped_column(
        Enum(BadgeCriteria), nullable=False, unique=True
    )
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    student_badges: Mapped[List["StudentBadge"]] = relationship(
        "StudentBadge", back_populates="badge"
    )

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Badge"]:
        """Get badge by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_all_active(cls, db_session: AsyncSession) -> Sequence["Badge"]:
        """Get all active badges."""
        stmt = (
            select(cls)
            .where(cls.is_active == True)
            .order_by(cls.category, cls.name)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_by_criteria(
        cls, db_session: AsyncSession, criteria: BadgeCriteria
    ) -> Optional["Badge"]:
        """Get badge by criteria."""
        stmt = select(cls).where(cls.criteria == criteria, cls.is_active == True)
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()


class StudentBadge(Base, TimestampMixin):
    """Student's earned badge."""

    __tablename__ = "student_badges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    badge_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("badges.id"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    awarded_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    progress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    progress_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment")
    badge: Mapped["Badge"] = relationship("Badge", back_populates="student_badges")
    awarder: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("enrollment_id", "badge_id", name="unique_student_badge"),
    )

    @classmethod
    async def get_by_enrollment(
        cls, db_session: AsyncSession, enrollment_id: str
    ) -> Sequence["StudentBadge"]:
        """Get all badges for an enrollment."""
        stmt = (
            select(cls)
            .where(cls.enrollment_id == enrollment_id)
            .options(selectinload(cls.badge))
            .order_by(cls.awarded_at.desc())
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def check_and_award(
        cls, db_session: AsyncSession, enrollment_id: str
    ) -> None:
        """Check criteria and auto-award badges based on attendance."""
        from app.models.attendance import Attendance

        # Get attendance streak
        streak = await Attendance.get_streak(db_session, enrollment_id)

        # Perfect Attendance badges
        if streak >= 5:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_5)
        if streak >= 10:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_10)
        if streak >= 20:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_20)

        # Check first class
        attendance_count = await Attendance.count_by_enrollment(db_session, enrollment_id)
        if attendance_count == 1:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.FIRST_CLASS)

        # Check first month (4+ weeks)
        if streak >= 4:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.FIRST_MONTH)

        await db_session.commit()

    @classmethod
    async def try_award(
        cls, db_session: AsyncSession, enrollment_id: str, criteria: BadgeCriteria
    ) -> None:
        """Try to award badge if not already awarded."""
        badge = await Badge.get_by_criteria(db_session, criteria)
        if not badge:
            return

        # Check if already awarded
        stmt = select(cls).where(
            cls.enrollment_id == enrollment_id, cls.badge_id == badge.id
        )
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return  # Already awarded

        # Award badge
        student_badge = cls(
            enrollment_id=enrollment_id, badge_id=badge.id, awarded_by=None
        )
        db_session.add(student_badge)
