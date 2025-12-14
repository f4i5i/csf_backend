"""Photo gallery models."""

from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    select,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.user import User


class PhotoCategory(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Photo category for organizing class photos."""

    __tablename__ = "photo_categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class")
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "class_id",
            "name",
            name="uq_photo_categories_organization_class_name",
        ),
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["PhotoCategory"]:
        """Get category by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_class(
        cls, db_session: AsyncSession, class_id: str
    ) -> Sequence["PhotoCategory"]:
        """Get all categories for a class."""
        stmt = (
            select(cls)
            .where(cls.class_id == class_id, cls.is_active == True)
            .order_by(cls.name)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()


class Photo(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Photo model for class gallery."""

    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=False, index=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("photo_categories.id"), nullable=True, index=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class")
    category: Mapped[Optional["PhotoCategory"]] = relationship(
        "PhotoCategory", back_populates="photos"
    )
    uploader: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Photo"]:
        """Get photo by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_class(
        cls,
        db_session: AsyncSession,
        class_id: str,
        category_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence["Photo"]:
        """Get photos for a class, optionally filtered by category."""
        stmt = (
            select(cls)
            .where(cls.class_id == class_id, cls.is_active == True)
            .options(selectinload(cls.category))
        )

        if category_id:
            stmt = stmt.where(cls.category_id == category_id)

        stmt = stmt.order_by(cls.created_at.desc()).offset(skip).limit(limit)

        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def count_by_class(
        cls,
        db_session: AsyncSession,
        class_id: str,
        category_id: Optional[str] = None,
    ) -> int:
        """Count photos for a class."""
        stmt = select(func.count(cls.id)).where(
            cls.class_id == class_id, cls.is_active == True
        )

        if category_id:
            stmt = stmt.where(cls.category_id == category_id)

        result = await db_session.execute(stmt)
        return result.scalar() or 0
