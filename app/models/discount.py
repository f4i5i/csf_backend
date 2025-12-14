"""Discount code and Scholarship models."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin

if TYPE_CHECKING:
    from app.models.child import Child
    from app.models.class_ import Class
    from app.models.order import Order
    from app.models.program import Program
    from app.models.user import User


class DiscountType(str, enum.Enum):
    """Type of discount."""

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class DiscountCode(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Discount/promo code model."""

    __tablename__ = "discount_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Code details
    code: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType), nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Percentage (0-100) or fixed amount

    # Validity period
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage limits
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = unlimited
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_user: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Restrictions
    min_order_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    applies_to_program_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("programs.id"), nullable=True, index=True
    )
    applies_to_class_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=True, index=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Audit
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_discount_codes_organization_code"
        ),
    )

    # Relationships
    created_by: Mapped["User"] = relationship("User")
    applies_to_program: Mapped[Optional["Program"]] = relationship("Program")
    applies_to_class: Mapped[Optional["Class"]] = relationship("Class")

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["DiscountCode"]:
        """Get discount code by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_code(
        cls, db_session: AsyncSession, code: str
    ) -> Optional["DiscountCode"]:
        """Get discount code by code string."""
        result = await db_session.execute(
            select(cls).where(cls.code == code.upper())
        )
        return result.scalars().first()

    @classmethod
    async def get_all_active(
        cls, db_session: AsyncSession
    ) -> Sequence["DiscountCode"]:
        """Get all active discount codes."""
        result = await db_session.execute(
            select(cls)
            .where(cls.is_active == True)
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def create_code(
        cls, db_session: AsyncSession, **kwargs
    ) -> "DiscountCode":
        """Create a new discount code."""
        # Ensure code is uppercase
        if "code" in kwargs:
            kwargs["code"] = kwargs["code"].upper()
        code = cls(**kwargs)
        db_session.add(code)
        await db_session.commit()
        await db_session.refresh(code)
        return code

    def is_valid(
        self,
        order_amount: Decimal = None,
        program_id: str = None,
        class_id: str = None,
        user_id: str = None,
    ) -> tuple[bool, str]:
        """
        Validate if discount code can be used.

        Args:
            order_amount: Order total for min amount validation
            program_id: Program ID for program restriction
            class_id: Class ID for class restriction and per-class usage tracking
            user_id: User ID for per-class usage tracking

        Returns (is_valid, error_message)

        Note: For async per-class usage check, use is_valid_async() instead.
        This method only checks basic validations.
        """
        now = datetime.now(self.valid_from.tzinfo) if self.valid_from.tzinfo else datetime.now()

        # Check if active
        if not self.is_active:
            return False, "This discount code is no longer active"

        # Check validity period
        if now < self.valid_from:
            return False, "This discount code is not yet valid"

        if self.valid_until and now > self.valid_until:
            return False, "This discount code has expired"

        # Check usage limit (global)
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "This discount code has reached its usage limit"

        # Check minimum order amount
        if self.min_order_amount and order_amount:
            if order_amount < self.min_order_amount:
                return False, f"Minimum order amount of ${self.min_order_amount} required"

        # Check program restriction
        if self.applies_to_program_id and program_id:
            if self.applies_to_program_id != program_id:
                return False, "This discount code is not valid for this program"

        # Check class restriction
        if self.applies_to_class_id and class_id:
            if self.applies_to_class_id != class_id:
                return False, "This discount code is not valid for this class"

        return True, ""

    async def is_valid_async(
        self,
        db_session: AsyncSession,
        order_amount: Decimal = None,
        program_id: str = None,
        class_id: str = None,
        user_id: str = None,
    ) -> tuple[bool, str]:
        """
        Async validation that includes per-class usage check.

        Returns (is_valid, error_message)
        """
        # First run basic synchronous validations
        is_valid, error = self.is_valid(order_amount, program_id, class_id, user_id)
        if not is_valid:
            return False, error

        # Check per-class usage if user_id and class_id provided
        if user_id and class_id:
            already_used = await self.check_usage_for_user_class(
                db_session, user_id, class_id
            )
            if already_used:
                return False, "You have already used this discount code for this class"

        return True, ""

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """Calculate discount amount for a given price."""
        if self.discount_type == DiscountType.PERCENTAGE:
            return (amount * self.discount_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        else:  # FIXED_AMOUNT
            return min(self.discount_value, amount)

    async def increment_usage(self, db_session: AsyncSession) -> None:
        """Increment usage count."""
        self.current_uses += 1
        await db_session.commit()

    async def check_usage_for_user_class(
        self, db_session: AsyncSession, user_id: str, class_id: str
    ) -> bool:
        """Check if user has already used this code for a specific class."""
        result = await db_session.execute(
            select(DiscountCodeUsage).where(
                DiscountCodeUsage.discount_code_id == self.id,
                DiscountCodeUsage.user_id == user_id,
                DiscountCodeUsage.class_id == class_id,
            )
        )
        return result.scalars().first() is not None

    async def record_usage(
        self,
        db_session: AsyncSession,
        user_id: str,
        class_id: str,
        order_id: Optional[str] = None,
    ) -> "DiscountCodeUsage":
        """Record usage of this discount code for a user and class."""
        usage = DiscountCodeUsage(
            discount_code_id=self.id,
            user_id=user_id,
            class_id=class_id,
            order_id=order_id,
        )
        db_session.add(usage)
        await self.increment_usage(db_session)
        return usage


class DiscountCodeUsage(Base, TimestampMixin):
    """Track discount code usage per user per class."""

    __tablename__ = "discount_code_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    discount_code_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("discount_codes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "discount_code_id",
            "user_id",
            "class_id",
            name="uq_discount_code_usage_user_class",
        ),
    )

    # Relationships
    discount_code: Mapped["DiscountCode"] = relationship("DiscountCode")
    user: Mapped["User"] = relationship("User")
    class_: Mapped["Class"] = relationship("Class")
    order: Mapped[Optional["Order"]] = relationship("Order")

    @classmethod
    async def get_usage_count_for_code(
        cls, db_session: AsyncSession, discount_code_id: str
    ) -> int:
        """Get total usage count for a discount code."""
        result = await db_session.execute(
            select(func.count(cls.id)).where(cls.discount_code_id == discount_code_id)
        )
        return result.scalar() or 0

    @classmethod
    async def get_usage_for_user(
        cls, db_session: AsyncSession, discount_code_id: str, user_id: str
    ) -> Sequence["DiscountCodeUsage"]:
        """Get all usage records for a user and discount code."""
        result = await db_session.execute(
            select(cls).where(
                cls.discount_code_id == discount_code_id,
                cls.user_id == user_id,
            )
        )
        return result.scalars().all()


class Scholarship(Base, TimestampMixin, SoftDeleteMixin, OrganizationMixin):
    """Scholarship record for financial assistance."""

    __tablename__ = "scholarships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    child_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("children.id"), nullable=True, index=True
    )
    class_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("classes.id"), nullable=True, index=True
    )

    # Scholarship details
    scholarship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )  # 0-100

    # Approval
    approved_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    # Validity
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    child: Mapped[Optional["Child"]] = relationship("Child")
    class_: Mapped[Optional["Class"]] = relationship("Class")
    approved_by: Mapped["User"] = relationship("User", foreign_keys=[approved_by_id])

    @property
    def effective_valid_until(self) -> Optional[date]:
        """
        Get effective expiration date.

        If scholarship is tied to a class, it expires when the class ends.
        Otherwise, uses the manually set valid_until date.
        """
        if self.class_id and self.class_:
            return self.class_.end_date
        return self.valid_until

    @classmethod
    async def get_by_id(
        cls, db_session: AsyncSession, id: str
    ) -> Optional["Scholarship"]:
        """Get scholarship by ID."""
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_active_for_user(
        cls, db_session: AsyncSession, user_id: str
    ) -> Sequence["Scholarship"]:
        """Get all active scholarships for a user."""
        from sqlalchemy.orm import selectinload
        from app.models.class_ import Class

        today = date.today()

        # Load with class relationship to check class end_date
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.class_))
            .where(
                cls.user_id == user_id,
                cls.is_active == True,
                # Check both manual valid_until and class end_date
                (
                    # Case 1: No class_id - check valid_until only
                    (cls.class_id.is_(None) & (cls.valid_until.is_(None) | (cls.valid_until >= today)))
                    |
                    # Case 2: Has class_id - check class end_date
                    (cls.class_id.isnot(None) &
                     (select(Class.end_date).where(Class.id == cls.class_id).scalar_subquery() >= today))
                )
            )
        )
        return result.scalars().all()

    @classmethod
    async def get_for_child(
        cls, db_session: AsyncSession, child_id: str
    ) -> Optional["Scholarship"]:
        """Get active scholarship for a specific child."""
        from sqlalchemy.orm import selectinload
        from app.models.class_ import Class

        today = date.today()

        # Load with class relationship to check class end_date
        result = await db_session.execute(
            select(cls)
            .options(selectinload(cls.class_))
            .where(
                cls.child_id == child_id,
                cls.is_active == True,
                # Check both manual valid_until and class end_date
                (
                    # Case 1: No class_id - check valid_until only
                    (cls.class_id.is_(None) & (cls.valid_until.is_(None) | (cls.valid_until >= today)))
                    |
                    # Case 2: Has class_id - check class end_date
                    (cls.class_id.isnot(None) &
                     (select(Class.end_date).where(Class.id == cls.class_id).scalar_subquery() >= today))
                )
            )
        )
        return result.scalars().first()

    @classmethod
    async def create_scholarship(
        cls, db_session: AsyncSession, **kwargs
    ) -> "Scholarship":
        """Create a new scholarship."""
        scholarship = cls(**kwargs)
        db_session.add(scholarship)
        await db_session.commit()
        await db_session.refresh(scholarship)
        return scholarship
