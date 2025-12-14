"""Password history model for tracking user password changes."""

from datetime import datetime
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, SoftDeleteMixin, OrganizationMixin


class PasswordHistory(Base, SoftDeleteMixin, OrganizationMixin):
    """
    Password history model for tracking recent password hashes.

    Stores the last 5 password hashes per user to prevent password reuse.
    """

    __tablename__ = "password_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    @classmethod
    async def get_recent_passwords(
        cls, db_session: AsyncSession, user_id: str, limit: int = 5
    ) -> Sequence["PasswordHistory"]:
        """
        Get most recent password hashes for a user.

        Args:
            db_session: Database session
            user_id: User ID
            limit: Number of recent passwords to retrieve (default: 5)

        Returns:
            List of recent password history records, newest first
        """
        result = await db_session.execute(
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def add_password(
        cls, db_session: AsyncSession, user_id: str, hashed_password: str
    ) -> "PasswordHistory":
        """
        Add a new password to history and maintain limit of 5 most recent.

        Args:
            db_session: Database session
            user_id: User ID
            hashed_password: Hashed password to store

        Returns:
            New password history record
        """
        # Get user's organization_id
        from app.models.user import User
        user = await User.get_by_id(db_session, user_id)
        organization_id = user.organization_id if user else None

        # Add new password
        new_record = cls(
            user_id=user_id,
            hashed_password=hashed_password,
            organization_id=organization_id
        )
        db_session.add(new_record)

        # Get all existing passwords for this user
        existing = await cls.get_recent_passwords(db_session, user_id, limit=100)

        # If more than 5, delete oldest ones
        if len(existing) >= 5:
            # Keep 4 newest + the new one = 5 total
            to_delete = existing[4:]
            for record in to_delete:
                await db_session.delete(record)

        await db_session.commit()
        await db_session.refresh(new_record)
        return new_record

    @classmethod
    async def check_password_reuse(
        cls,
        db_session: AsyncSession,
        user_id: str,
        plain_password: str
    ) -> bool:
        """
        Check if a password has been used in recent history.

        Args:
            db_session: Database session
            user_id: User ID
            plain_password: New password in plain text to check

        Returns:
            True if password was used recently, False otherwise
        """
        from app.utils.security import verify_password

        recent_passwords = await cls.get_recent_passwords(db_session, user_id, limit=5)

        for record in recent_passwords:
            if verify_password(plain_password, record.hashed_password):
                return True

        return False
