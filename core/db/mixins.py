from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.organization import Organization


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )



class SoftDeleteMixin:
    """Mixin that adds soft delete semantics."""

    @declared_attr.directive
    def is_deleted(cls) -> Mapped[bool]:  # type: ignore[override]
        return mapped_column(
            Boolean,
            default=False,
            server_default="false",
            nullable=False,
            index=True,
        )

    @declared_attr.directive
    def deleted_at(cls) -> Mapped[Optional[datetime]]:  # type: ignore[override]
        return mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        """Mark the record as deleted without removing it."""
        self.is_deleted = True
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore a previously soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class OrganizationMixin:
    """Mixin that adds multi-tenant organization scoping."""

    @declared_attr.directive
    def organization_id(cls) -> Mapped[str]:  # type: ignore[override]
        return mapped_column(
            String(36), ForeignKey("organizations.id"), nullable=False, index=True
        )

    @declared_attr.directive
    def organization(cls) -> Mapped["Organization"]:  # type: ignore[override]
        return relationship("Organization")


__all__ = ["TimestampMixin", "SoftDeleteMixin", "OrganizationMixin"]
