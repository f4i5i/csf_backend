from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.class_ import Class


class Program(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Program model representing sports programs (e.g., Basketball, Soccer)."""

    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    classes: Mapped[list["Class"]] = relationship("Class", back_populates="program")

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Program"]:
        """Get program by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_name(
        cls, db_session: AsyncSession, name: str
    ) -> Optional["Program"]:
        """Get program by name."""
        result = await db_session.execute(select(cls).where(cls.name == name))
        return result.scalars().first()

    @classmethod
    async def get_all_active(cls, db_session: AsyncSession) -> Sequence["Program"]:
        """Get all active programs."""
        result = await db_session.execute(
            select(cls).where(cls.is_active == True).order_by(cls.name)
        )
        return result.scalars().all()

    @classmethod
    async def create_program(
        cls,
        db_session: AsyncSession,
        name: str,
        description: Optional[str] = None,
    ) -> "Program":
        """Create a new program."""
        program = cls(name=name, description=description)
        db_session.add(program)
        await db_session.commit()
        await db_session.refresh(program)
        return program


class Area(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Area model representing geographic regions."""

    __tablename__ = "areas"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    schools: Mapped[list["School"]] = relationship("School", back_populates="area")

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Area"]:
        """Get area by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_name(cls, db_session: AsyncSession, name: str) -> Optional["Area"]:
        """Get area by name."""
        result = await db_session.execute(select(cls).where(cls.name == name))
        return result.scalars().first()

    @classmethod
    async def get_all_active(cls, db_session: AsyncSession) -> Sequence["Area"]:
        """Get all active areas."""
        result = await db_session.execute(
            select(cls).where(cls.is_active == True).order_by(cls.name)
        )
        return result.scalars().all()

    @classmethod
    async def create_area(
        cls,
        db_session: AsyncSession,
        name: str,
        description: Optional[str] = None,
    ) -> "Area":
        """Create a new area."""
        area = cls(name=name, description=description)
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)
        return area


class School(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """School model representing class locations."""

    __tablename__ = "schools"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Ledger code
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    area_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("areas.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    area: Mapped["Area"] = relationship("Area", back_populates="schools")
    classes: Mapped[list["Class"]] = relationship("Class", back_populates="school")

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["School"]:
        """Get school by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_area(
        cls, db_session: AsyncSession, area_id: str
    ) -> Sequence["School"]:
        """Get all schools in an area."""
        result = await db_session.execute(
            select(cls)
            .where(cls.area_id == area_id, cls.is_active == True)
            .order_by(cls.name)
        )
        return result.scalars().all()

    @classmethod
    async def get_all_active(cls, db_session: AsyncSession) -> Sequence["School"]:
        """Get all active schools."""
        result = await db_session.execute(
            select(cls).where(cls.is_active == True).order_by(cls.name)
        )
        return result.scalars().all()

    @classmethod
    async def create_school(
        cls,
        db_session: AsyncSession,
        name: str,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        area_id: str,
        code: Optional[str] = None,
    ) -> "School":
        """Create a new school."""
        school = cls(
            name=name,
            code=code,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            area_id=area_id,
        )
        db_session.add(school)
        await db_session.commit()
        await db_session.refresh(school)
        return school
