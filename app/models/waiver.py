import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.program import Program, School
    from app.models.user import User


class WaiverType(str, enum.Enum):
    """Types of waivers."""

    MEDICAL_RELEASE = "medical_release"
    LIABILITY = "liability"
    PHOTO_RELEASE = "photo_release"
    CANCELLATION_POLICY = "cancellation_policy"


class WaiverTemplate(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Waiver template model with versioning."""

    __tablename__ = "waiver_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    waiver_type: Mapped[WaiverType] = mapped_column(Enum(WaiverType, native_enum=False), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # HTML content
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Scope - null means global
    applies_to_program_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("programs.id"), nullable=True, index=True
    )
    applies_to_school_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("schools.id"), nullable=True, index=True
    )

    # Relationships
    applies_to_program: Mapped[Optional["Program"]] = relationship(
        "Program", foreign_keys=[applies_to_program_id]
    )
    applies_to_school: Mapped[Optional["School"]] = relationship(
        "School", foreign_keys=[applies_to_school_id]
    )
    acceptances: Mapped[list["WaiverAcceptance"]] = relationship(
        "WaiverAcceptance", back_populates="waiver_template"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["WaiverTemplate"]:
        """Get waiver template by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_active_waivers(
        cls,
        db_session: AsyncSession,
        organization_id: Optional[str] = None,
        program_id: Optional[str] = None,
        school_id: Optional[str] = None,
    ) -> Sequence["WaiverTemplate"]:
        """
        Get active required waivers applicable to given context.

        Returns global waivers plus any program/school specific ones.
        """
        # Get global waivers (no program or school restriction)
        global_condition = (
            (cls.applies_to_program_id.is_(None)) & (cls.applies_to_school_id.is_(None))
        )

        conditions = [cls.is_active == True, cls.is_required == True]

        # Filter by organization
        if organization_id:
            conditions.append(cls.organization_id == organization_id)

        if program_id and school_id:
            # Get global + program-specific + school-specific waivers
            scope_condition = (
                global_condition
                | (cls.applies_to_program_id == program_id)
                | (cls.applies_to_school_id == school_id)
            )
            conditions.append(scope_condition)
        elif program_id:
            scope_condition = global_condition | (
                cls.applies_to_program_id == program_id
            )
            conditions.append(scope_condition)
        elif school_id:
            scope_condition = global_condition | (cls.applies_to_school_id == school_id)
            conditions.append(scope_condition)
        else:
            conditions.append(global_condition)

        result = await db_session.execute(
            select(cls).where(*conditions).order_by(cls.waiver_type)
        )
        return result.scalars().all()

    @classmethod
    async def get_all(
        cls,
        db_session: AsyncSession,
        organization_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> Sequence["WaiverTemplate"]:
        """Get all waiver templates for an organization."""
        conditions = []
        if organization_id:
            conditions.append(cls.organization_id == organization_id)
        if not include_inactive:
            conditions.append(cls.is_active == True)

        result = await db_session.execute(
            select(cls)
            .where(*conditions)
            .order_by(cls.waiver_type, cls.version.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_latest_version(
        cls, db_session: AsyncSession, waiver_type: WaiverType
    ) -> int:
        """Get the latest version number for a waiver type."""
        result = await db_session.execute(
            select(func.max(cls.version)).where(cls.waiver_type == waiver_type)
        )
        max_version = result.scalar()
        return max_version or 0

    @classmethod
    async def create_template(
        cls, db_session: AsyncSession, **kwargs
    ) -> "WaiverTemplate":
        """Create a new waiver template with auto-incremented version."""
        waiver_type = kwargs.get("waiver_type")
        if waiver_type:
            latest_version = await cls.get_latest_version(db_session, waiver_type)
            kwargs["version"] = latest_version + 1

        template = cls(**kwargs)
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        return template


class WaiverAcceptance(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Record of a user accepting a waiver."""

    __tablename__ = "waiver_acceptances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    waiver_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("waiver_templates.id"), nullable=False, index=True
    )

    # Snapshot of version at acceptance time
    waiver_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Signer information for legal compliance
    signer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv6 max
    signer_user_agent: Mapped[str] = mapped_column(String(500), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    waiver_template: Mapped["WaiverTemplate"] = relationship(
        "WaiverTemplate", back_populates="acceptances"
    )

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["WaiverAcceptance"]:
        """Get waiver acceptance by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_user_acceptances(
        cls, db_session: AsyncSession, user_id: str
    ) -> Sequence["WaiverAcceptance"]:
        """Get all waiver acceptances for a user."""
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.waiver_template))
            .where(cls.user_id == user_id)
            .order_by(cls.accepted_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_user_acceptance_for_waiver(
        cls,
        db_session: AsyncSession,
        user_id: str,
        waiver_template_id: str,
    ) -> Optional["WaiverAcceptance"]:
        """Get user's acceptance for a specific waiver template."""
        result = await db_session.execute(
            select(cls).where(
                cls.user_id == user_id,
                cls.waiver_template_id == waiver_template_id,
            )
        )
        return result.scalars().first()

    @classmethod
    async def create_acceptance(
        cls, db_session: AsyncSession, **kwargs
    ) -> "WaiverAcceptance":
        """Create a waiver acceptance record."""
        acceptance = cls(**kwargs)
        db_session.add(acceptance)
        await db_session.commit()
        await db_session.refresh(acceptance)
        return acceptance

    @classmethod
    async def needs_reconsent(
        cls,
        db_session: AsyncSession,
        user_id: str,
        waiver_template: "WaiverTemplate",
    ) -> bool:
        """
        Check if user needs to re-consent to a waiver.

        Returns True if:
        - User has never accepted this waiver
        - User's acceptance is for an older version
        """
        acceptance = await cls.get_user_acceptance_for_waiver(
            db_session, user_id, waiver_template.id
        )
        if not acceptance:
            return True
        return acceptance.waiver_version < waiver_template.version
