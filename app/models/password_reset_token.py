"""Password reset token model for forgot password flow."""

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, OrganizationMixin


class PasswordResetToken(Base, OrganizationMixin):
    """
    Password reset token model.

    Stores tokens for password reset with expiration.
    Tokens expire after 1 hour.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return token_urlsafe(32)

    @classmethod
    async def create_token(
        cls, db_session: AsyncSession, user_id: str, organization_id: str, expires_in_hours: int = 1
    ) -> "PasswordResetToken":
        """
        Create a new password reset token.

        Args:
            db_session: Database session
            user_id: User ID
            organization_id: Organization ID
            expires_in_hours: Token expiration time in hours (default: 1)

        Returns:
            New password reset token
        """
        token = cls.generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        reset_token = cls(
            user_id=user_id,
            organization_id=organization_id,
            token=token,
            expires_at=expires_at,
        )
        db_session.add(reset_token)
        await db_session.commit()
        await db_session.refresh(reset_token)
        return reset_token

    @classmethod
    async def get_by_token(
        cls, db_session: AsyncSession, token: str
    ) -> Optional["PasswordResetToken"]:
        """Get password reset token by token string."""
        result = await db_session.execute(
            select(cls).where(cls.token == token)
        )
        return result.scalars().first()

    def is_valid(self) -> bool:
        """Check if token is still valid (not expired and not used)."""
        if self.used_at:
            return False
        return datetime.now(timezone.utc) < self.expires_at

    async def mark_as_used(self, db_session: AsyncSession) -> None:
        """Mark token as used."""
        self.used_at = datetime.now(timezone.utc)
        await db_session.commit()

    @classmethod
    async def invalidate_user_tokens(
        cls, db_session: AsyncSession, user_id: str
    ) -> None:
        """Invalidate all existing tokens for a user."""
        result = await db_session.execute(
            select(cls).where(
                cls.user_id == user_id,
                cls.used_at.is_(None)
            )
        )
        tokens = result.scalars().all()

        for token in tokens:
            token.used_at = datetime.now(timezone.utc)

        await db_session.commit()
