"""Account credit transaction model for transfer downgrades/upgrades."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.user import User


class CreditTransactionType(str, enum.Enum):
    """Type of credit transaction."""

    EARNED = "earned"  # Credit earned (e.g., promotional)
    SPENT = "spent"  # Credit applied to purchase
    EXPIRED = "expired"  # Credit expired
    REFUND_TO_CREDIT = "refund_to_credit"  # Refund converted to credit
    TRANSFER_DOWNGRADE = "transfer_downgrade"  # Transfer to cheaper class


class AccountCreditTransaction(Base, TimestampMixin):
    """Track account credit transactions."""

    __tablename__ = "account_credit_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Positive for credit, negative for spend
    transaction_type: Mapped[CreditTransactionType] = mapped_column(
        Enum(CreditTransactionType), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # References
    order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )

    # Balance tracking
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_account_credit_transactions_created_at",
            "created_at",
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    order: Mapped[Optional["Order"]] = relationship("Order")
    enrollment: Mapped[Optional["Enrollment"]] = relationship("Enrollment")
    payment: Mapped[Optional["Payment"]] = relationship("Payment")

    @classmethod
    async def create_transaction(
        cls,
        db_session: AsyncSession,
        user_id: str,
        amount: Decimal,
        transaction_type: CreditTransactionType,
        description: str = None,
        order_id: str = None,
        enrollment_id: str = None,
        payment_id: str = None,
    ) -> "AccountCreditTransaction":
        """Create a new credit transaction and update user balance."""
        from app.models.user import User

        # Get user and update balance
        user = await db_session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Update balance
        user.account_credit = user.account_credit + amount
        balance_after = user.account_credit

        # Create transaction record
        transaction = cls(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            order_id=order_id,
            enrollment_id=enrollment_id,
            payment_id=payment_id,
            balance_after=balance_after,
        )
        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)
        return transaction

    @classmethod
    async def get_user_transactions(
        cls,
        db_session: AsyncSession,
        user_id: str,
        limit: int = 50,
    ) -> Sequence["AccountCreditTransaction"]:
        """Get transaction history for a user."""
        result = await db_session.execute(
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def add_credit(
        cls,
        db_session: AsyncSession,
        user_id: str,
        amount: Decimal,
        transaction_type: CreditTransactionType,
        description: str,
        **kwargs,
    ) -> "AccountCreditTransaction":
        """Add credit to user account."""
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        return await cls.create_transaction(
            db_session=db_session,
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            **kwargs,
        )

    @classmethod
    async def spend_credit(
        cls,
        db_session: AsyncSession,
        user_id: str,
        amount: Decimal,
        description: str,
        **kwargs,
    ) -> "AccountCreditTransaction":
        """Spend/apply credit from user account."""
        from app.models.user import User

        if amount <= 0:
            raise ValueError("Spend amount must be positive")

        # Check if user has sufficient credit
        user = await db_session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if user.account_credit < amount:
            raise ValueError(
                f"Insufficient credit. Available: ${user.account_credit}, Requested: ${amount}"
            )

        # Create negative transaction (spending)
        return await cls.create_transaction(
            db_session=db_session,
            user_id=user_id,
            amount=-amount,  # Negative for spending
            transaction_type=CreditTransactionType.SPENT,
            description=description,
            **kwargs,
        )
