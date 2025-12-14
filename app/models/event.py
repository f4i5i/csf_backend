"""Event models for calendar functionality."""

import enum
from datetime import date
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.user import User


class EventType(str, enum.Enum):
    """Type of event."""

    TOURNAMENT = "tournament"
    MATCH = "match"
    TRAINING = "training"
    WORKSHOP = "workshop"
    OTHER = "other"


class Event(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Event model for one-time events (tournaments, workshops, etc.)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class")
    creator: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Event"]:
        """Get event by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_class_and_date_range(
        cls,
        db_session: AsyncSession,
        class_id: str,
        start_date: date,
        end_date: date,
    ) -> Sequence["Event"]:
        """Get events for a class within a date range."""
        stmt = (
            select(cls)
            .where(
                cls.class_id == class_id,
                cls.is_active == True,
                cls.event_date >= start_date,
                cls.event_date <= end_date,
            )
            .order_by(cls.event_date, cls.start_time)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_calendar_view(
        cls, db_session: AsyncSession, class_id: str, year: int, month: int
    ) -> Sequence["Event"]:
        """Get events for calendar view (month)."""
        import calendar

        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        return await cls.get_by_class_and_date_range(
            db_session, class_id, start_date, end_date
        )

    @classmethod
    async def get_by_class(
        cls, db_session: AsyncSession, class_id: str
    ) -> Sequence["Event"]:
        """Get all events for a class."""
        stmt = (
            select(cls)
            .where(cls.class_id == class_id, cls.is_active == True)
            .order_by(cls.event_date, cls.start_time)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    async def update(self, db_session: AsyncSession, **kwargs) -> "Event":
        """Update event fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        await db_session.commit()
        await db_session.refresh(self)
        return self
