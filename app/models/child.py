import enum
from datetime import date
from typing import TYPE_CHECKING, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.user import User


class JerseySize(str, enum.Enum):
    """Jersey size options."""

    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"
    XXL = "xxl"


class Grade(str, enum.Enum):
    """Grade level options."""

    PRE_K = "pre_k"
    KINDERGARTEN = "k"
    GRADE_1 = "1"
    GRADE_2 = "2"
    GRADE_3 = "3"
    GRADE_4 = "4"
    GRADE_5 = "5"
    GRADE_6 = "6"
    GRADE_7 = "7"
    GRADE_8 = "8"
    GRADE_9 = "9"
    GRADE_10 = "10"
    GRADE_11 = "11"
    GRADE_12 = "12"


class HowHeardAboutUs(str, enum.Enum):
    """How the user heard about us options."""

    FRIEND = "friend"
    SOCIAL_MEDIA = "social_media"
    SCHOOL = "school"
    FLYER = "flyer"
    GOOGLE = "google"
    OTHER = "other"


class Child(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Child model representing a player/student."""

    __tablename__ = "children"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # Basic info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    # Size and grade
    jersey_size: Mapped[Optional[JerseySize]] = mapped_column(
        Enum(JerseySize), nullable=True
    )
    grade: Mapped[Optional[Grade]] = mapped_column(Enum(Grade), nullable=True)

    # Medical info (encrypted)
    medical_conditions_encrypted: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    has_no_medical_conditions: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_medical_alert: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default='false'
    )

    # After school
    after_school_attendance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    after_school_program: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )

    # Insurance (encrypted)
    health_insurance_number_encrypted: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Marketing
    how_heard_about_us: Mapped[Optional[HowHeardAboutUs]] = mapped_column(
        Enum(HowHeardAboutUs), nullable=True
    )
    how_heard_other_text: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )

    # Coach notes (for coaches/admins to add notes about the child)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="children")
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(
        "EmergencyContact", back_populates="child", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Get child's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate current age from date of birth."""
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def age_on_date(self, target_date: date) -> int:
        """Calculate age on a specific date (e.g., class start date)."""
        return (
            target_date.year
            - self.date_of_birth.year
            - (
                (target_date.month, target_date.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Child"]:
        """Get child by ID."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.emergency_contacts))
            .where(cls.id == id)
        )
        return result.scalars().first()

    @classmethod
    async def get_by_user_id(
        cls, db_session: AsyncSession, user_id: str
    ) -> Sequence["Child"]:
        """Get all children for a user."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.emergency_contacts))
            .where(cls.user_id == user_id, cls.is_active == True)
            .order_by(cls.first_name)
        )
        return result.scalars().all()

    @classmethod
    async def create_child(
        cls, db_session: AsyncSession, user_id: str, **kwargs
    ) -> "Child":
        """Create a new child."""
        child = cls(user_id=user_id, **kwargs)
        db_session.add(child)
        await db_session.commit()
        # Reload with eager loading for relationships
        return await cls.get_by_id(db_session, child.id)


class EmergencyContact(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Emergency contact for a child."""

    __tablename__ = "emergency_contacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    relation: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    child: Mapped["Child"] = relationship("Child", back_populates="emergency_contacts")

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["EmergencyContact"]:
        """Get emergency contact by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_child_id(
        cls, db_session: AsyncSession, child_id: str
    ) -> Sequence["EmergencyContact"]:
        """Get all emergency contacts for a child."""
        result = await db_session.execute(
            select(cls).where(cls.child_id == child_id).order_by(cls.is_primary.desc())
        )
        return result.scalars().all()

    @classmethod
    async def create_contact(
        cls, db_session: AsyncSession, child_id: str, **kwargs
    ) -> "EmergencyContact":
        """Create a new emergency contact."""
        contact = cls(child_id=child_id, **kwargs)
        db_session.add(contact)
        await db_session.commit()
        await db_session.refresh(contact)
        return contact
