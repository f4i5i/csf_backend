import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.child import Child


class Role(str, enum.Enum):
    """User roles in the system."""
    OWNER = "owner"
    ADMIN = "admin"
    COACH = "coach"
    PARENT = "parent"


class User(Base, TimestampMixin):
    """User model with class methods for database operations."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role), default=Role.PARENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    children: Mapped[List["Child"]] = relationship(
        "Child", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize emails so uniqueness checks are case-insensitive."""
        return email.strip().lower()

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["User"]:
        """Get user by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_email(
        cls, db_session: AsyncSession, email: str
    ) -> Optional["User"]:
        """Get user by email."""
        normalized_email = cls.normalize_email(email)
        result = await db_session.execute(
            select(cls).where(cls.email == normalized_email)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_google_id(
        cls, db_session: AsyncSession, google_id: str
    ) -> Optional["User"]:
        """Get user by Google ID."""
        result = await db_session.execute(
            select(cls).where(cls.google_id == google_id)
        )
        return result.scalars().first()

    @classmethod
    async def create_user(
        cls,
        db_session: AsyncSession,
        email: str,
        first_name: str,
        last_name: str,
        hashed_password: Optional[str] = None,
        google_id: Optional[str] = None,
        role: Role = Role.PARENT,
        phone: Optional[str] = None,
    ) -> "User":
        """Create a new user."""
        normalized_email = cls.normalize_email(email)
        user = cls(
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            hashed_password=hashed_password,
            google_id=google_id,
            role=role,
            phone=phone,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @classmethod
    async def get_all(
        cls, db_session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence["User"]:
        """Get all users with pagination."""
        result = await db_session.execute(
            select(cls).offset(skip).limit(limit).order_by(cls.created_at.desc())
        )
        return result.scalars().all()
