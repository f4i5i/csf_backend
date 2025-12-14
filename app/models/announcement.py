"""Announcement models for coaches to create posts with attachments."""

import enum
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.user import User


class AnnouncementType(str, enum.Enum):
    """Type of announcement."""

    GENERAL = "general"
    IMPORTANT = "important"
    URGENT = "urgent"


class AttachmentType(str, enum.Enum):
    """Type of attachment file."""

    PDF = "pdf"
    IMAGE = "image"


class Announcement(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Announcement/Post model created by coaches."""

    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AnnouncementType] = mapped_column(
        Enum(AnnouncementType), default=AnnouncementType.GENERAL, nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    author: Mapped["User"] = relationship("User")
    attachments: Mapped[List["AnnouncementAttachment"]] = relationship(
        "AnnouncementAttachment", back_populates="announcement", cascade="all, delete-orphan"
    )
    targets: Mapped[List["AnnouncementTarget"]] = relationship(
        "AnnouncementTarget", back_populates="announcement", cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Announcement"]:
        """Get announcement by ID with attachments."""
        result = await db_session.execute(
            select(cls)
            .options(
                selectinload(cls.author),
                selectinload(cls.attachments),
                selectinload(cls.targets)
            )
            .where(cls.id == id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_class(
        cls,
        db_session: AsyncSession,
        class_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence["Announcement"]:
        """Get announcements for a specific class."""
        stmt = (
            select(cls)
            .join(AnnouncementTarget)
            .where(
                AnnouncementTarget.class_id == class_id,
                cls.is_active == True
            )
            .options(
                selectinload(cls.author),
                selectinload(cls.attachments)
            )
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def count_by_class(
        cls, db_session: AsyncSession, class_id: str
    ) -> int:
        """Count announcements for a class."""
        from sqlalchemy import func
        stmt = (
            select(func.count(cls.id))
            .join(AnnouncementTarget)
            .where(
                AnnouncementTarget.class_id == class_id,
                cls.is_active == True
            )
        )
        result = await db_session.execute(stmt)
        return result.scalar() or 0

    @classmethod
    async def get_all(
        cls, db_session: AsyncSession, skip: int = 0, limit: int = 20
    ) -> Sequence["Announcement"]:
        """Get all active announcements."""
        stmt = (
            select(cls)
            .where(cls.is_active == True)
            .options(
                selectinload(cls.author),
                selectinload(cls.attachments)
            )
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def count_all(cls, db_session: AsyncSession) -> int:
        """Count all active announcements."""
        from sqlalchemy import func
        stmt = select(func.count(cls.id)).where(cls.is_active == True)
        result = await db_session.execute(stmt)
        return result.scalar() or 0

    @classmethod
    async def create_with_targets(
        cls,
        db_session: AsyncSession,
        class_ids: List[str],
        **kwargs
    ) -> "Announcement":
        """Create announcement with target classes."""
        announcement = cls(**kwargs)
        db_session.add(announcement)
        await db_session.flush()

        # Get organization_id from announcement
        organization_id = announcement.organization_id

        # Create targets
        for class_id in class_ids:
            target = AnnouncementTarget(
                announcement_id=announcement.id,
                class_id=class_id,
                organization_id=organization_id
            )
            db_session.add(target)

        await db_session.commit()
        await db_session.refresh(announcement)

        # Reload with relationships
        return await cls.get_by_id(db_session, announcement.id)

    async def update(
        self, db_session: AsyncSession, **kwargs
    ) -> "Announcement":
        """Update announcement fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        await db_session.commit()
        await db_session.refresh(self)
        return self


class AnnouncementAttachment(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Attachment files for announcements (PDFs, images)."""

    __tablename__ = "announcement_attachments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    announcement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("announcements.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    announcement: Mapped["Announcement"] = relationship(
        "Announcement", back_populates="attachments"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["AnnouncementAttachment"]:
        """Get attachment by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()


class AnnouncementTarget(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Many-to-many relationship between announcements and classes."""

    __tablename__ = "announcement_targets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    announcement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("announcements.id"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )

    # Relationships
    announcement: Mapped["Announcement"] = relationship(
        "Announcement", back_populates="targets"
    )
    class_: Mapped["Class"] = relationship("Class")

    __table_args__ = (
        UniqueConstraint(
            "announcement_id", "class_id", name="unique_announcement_class"
        ),
    )

    @classmethod
    async def get_by_announcement(
        cls, db_session: AsyncSession, announcement_id: str
    ) -> Sequence["AnnouncementTarget"]:
        """Get all targets for an announcement."""
        result = await db_session.execute(
            select(cls).where(cls.announcement_id == announcement_id)
        )
        return result.scalars().all()
