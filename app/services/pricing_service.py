"""Pricing service for calculating order totals and discounts."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.models.class_ import Class
from app.models.discount import DiscountCode, Scholarship
from core.logging import get_logger

logger = get_logger(__name__)


# Sibling discount rates (auto-applied)
SIBLING_DISCOUNTS = {
    2: Decimal("0.25"),  # 2nd child: 25% off
    3: Decimal("0.35"),  # 3rd child: 35% off
    4: Decimal("0.45"),  # 4th+ child: 45% off
}


@dataclass
class LineItemCalculation:
    """Calculated line item details."""

    child_id: str
    child_name: str
    class_id: str
    class_name: str
    unit_price: Decimal
    sibling_discount: Decimal
    sibling_discount_description: Optional[str]
    promo_discount: Decimal
    promo_discount_description: Optional[str]
    scholarship_discount: Decimal
    scholarship_discount_description: Optional[str]
    line_total: Decimal


@dataclass
class OrderCalculation:
    """Complete order calculation result."""

    line_items: list[LineItemCalculation]
    subtotal: Decimal
    sibling_discount_total: Decimal
    promo_discount_total: Decimal
    scholarship_discount_total: Decimal
    discount_total: Decimal
    total: Decimal
    discount_code: Optional[str]
    discount_code_id: Optional[str]


@dataclass
class InstallmentScheduleItem:
    """Single installment in a payment schedule."""

    installment_number: int
    due_date: date
    amount: Decimal


@dataclass
class DiscountValidation:
    """Result of discount code validation."""

    is_valid: bool
    error_message: Optional[str]
    discount_type: Optional[str]
    discount_value: Optional[Decimal]
    discount_amount: Optional[Decimal]  # Calculated for given amount


@dataclass
class OrderItemInput:
    """Input for order calculation."""

    child_id: str
    class_id: str


class PricingService:
    """Service for calculating pricing and discounts."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def calculate_order(
        self,
        user_id: str,
        items: list[OrderItemInput],
        discount_code: str = None,
    ) -> OrderCalculation:
        """
        Calculate complete order with all applicable discounts.

        Applies in order:
        1. Sibling discounts (auto-applied based on number of children)
        2. Scholarships (if any active for user/child)
        3. Promo code discount (if provided and valid)
        """
        if not items:
            return OrderCalculation(
                line_items=[],
                subtotal=Decimal("0.00"),
                sibling_discount_total=Decimal("0.00"),
                promo_discount_total=Decimal("0.00"),
                scholarship_discount_total=Decimal("0.00"),
                discount_total=Decimal("0.00"),
                total=Decimal("0.00"),
                discount_code=None,
                discount_code_id=None,
            )

        # Load classes and children
        line_items = []
        subtotal = Decimal("0.00")
        sibling_discount_total = Decimal("0.00")
        promo_discount_total = Decimal("0.00")
        scholarship_discount_total = Decimal("0.00")

        # Validate and load discount code
        discount_code_obj = None
        if discount_code:
            discount_code_obj = await DiscountCode.get_by_code(
                self.db_session, discount_code
            )

        # Get scholarships for user
        scholarships = await Scholarship.get_active_for_user(self.db_session, user_id)
        scholarship_map = {s.child_id: s for s in scholarships if s.child_id}
        user_scholarship = next((s for s in scholarships if not s.child_id), None)

        # Sort items by price descending (highest price first - no sibling discount)
        items_with_prices = []
        for item in items:
            class_ = await Class.get_by_id(self.db_session, item.class_id)
            child = await Child.get_by_id(self.db_session, item.child_id)

            if not class_ or not child:
                continue

            items_with_prices.append({
                "item": item,
                "class": class_,
                "child": child,
                "price": class_.price,
            })

        # Sort by price descending (most expensive first gets no sibling discount)
        items_with_prices.sort(key=lambda x: x["price"], reverse=True)

        # Calculate each line item
        for idx, item_data in enumerate(items_with_prices):
            item = item_data["item"]
            class_ = item_data["class"]
            child = item_data["child"]
            unit_price = class_.price

            # Sibling discount (skip first child - most expensive)
            sibling_discount = Decimal("0.00")
            sibling_description = None
            if idx > 0:
                child_number = idx + 1
                discount_rate = SIBLING_DISCOUNTS.get(
                    min(child_number, 4), Decimal("0.00")
                )
                if discount_rate > 0:
                    sibling_discount = (unit_price * discount_rate).quantize(
                        Decimal("0.01")
                    )
                    percent = int(discount_rate * 100)
                    sibling_description = f"Sibling discount ({percent}% off)"

            # Scholarship discount
            scholarship_discount = Decimal("0.00")
            scholarship_description = None
            scholarship = scholarship_map.get(child.id) or user_scholarship
            if scholarship:
                remaining = unit_price - sibling_discount
                scholarship_discount = (
                    remaining * scholarship.discount_percentage / Decimal("100")
                ).quantize(Decimal("0.01"))
                scholarship_description = (
                    f"{scholarship.scholarship_type} ({scholarship.discount_percentage}%)"
                )

            # Promo code discount (applied after other discounts)
            promo_discount = Decimal("0.00")
            promo_description = None
            if discount_code_obj:
                remaining = unit_price - sibling_discount - scholarship_discount
                is_valid, _ = discount_code_obj.is_valid(
                    order_amount=remaining,
                    program_id=class_.program_id if hasattr(class_, "program_id") else None,
                    class_id=class_.id,
                )
                if is_valid:
                    promo_discount = discount_code_obj.calculate_discount(remaining)
                    promo_description = f"Promo: {discount_code_obj.code}"

            # Calculate line total
            line_total = unit_price - sibling_discount - scholarship_discount - promo_discount

            line_items.append(
                LineItemCalculation(
                    child_id=child.id,
                    child_name=child.full_name,
                    class_id=class_.id,
                    class_name=class_.name,
                    unit_price=unit_price,
                    sibling_discount=sibling_discount,
                    sibling_discount_description=sibling_description,
                    promo_discount=promo_discount,
                    promo_discount_description=promo_description,
                    scholarship_discount=scholarship_discount,
                    scholarship_discount_description=scholarship_description,
                    line_total=line_total,
                )
            )

            subtotal += unit_price
            sibling_discount_total += sibling_discount
            promo_discount_total += promo_discount
            scholarship_discount_total += scholarship_discount

        discount_total = sibling_discount_total + promo_discount_total + scholarship_discount_total
        total = subtotal - discount_total

        return OrderCalculation(
            line_items=line_items,
            subtotal=subtotal,
            sibling_discount_total=sibling_discount_total,
            promo_discount_total=promo_discount_total,
            scholarship_discount_total=scholarship_discount_total,
            discount_total=discount_total,
            total=max(total, Decimal("0.00")),  # Never negative
            discount_code=discount_code_obj.code if discount_code_obj else None,
            discount_code_id=discount_code_obj.id if discount_code_obj else None,
        )

    async def validate_discount_code(
        self,
        code: str,
        order_amount: Decimal,
        program_id: str = None,
        class_id: str = None,
    ) -> DiscountValidation:
        """Validate a discount code and calculate its value."""
        discount = await DiscountCode.get_by_code(self.db_session, code)

        if not discount:
            return DiscountValidation(
                is_valid=False,
                error_message="Invalid discount code",
                discount_type=None,
                discount_value=None,
                discount_amount=None,
            )

        is_valid, error_message = discount.is_valid(
            order_amount=order_amount,
            program_id=program_id,
            class_id=class_id,
        )

        if not is_valid:
            return DiscountValidation(
                is_valid=False,
                error_message=error_message,
                discount_type=None,
                discount_value=None,
                discount_amount=None,
            )

        discount_amount = discount.calculate_discount(order_amount)

        return DiscountValidation(
            is_valid=True,
            error_message=None,
            discount_type=discount.discount_type.value,
            discount_value=discount.discount_value,
            discount_amount=discount_amount,
        )

    @staticmethod
    def calculate_installment_schedule(
        total: Decimal,
        num_installments: int,
        start_date: date,
        frequency: str,  # "weekly", "biweekly", "monthly"
    ) -> list[InstallmentScheduleItem]:
        """Generate installment payment schedule."""
        if num_installments < 2:
            raise ValueError("Minimum 2 installments required")

        # Calculate installment amount (spread evenly, last one gets remainder)
        base_amount = (total / num_installments).quantize(Decimal("0.01"))
        remainder = total - (base_amount * num_installments)

        # Determine interval
        if frequency == "weekly":
            interval = timedelta(weeks=1)
        elif frequency == "biweekly":
            interval = timedelta(weeks=2)
        else:  # monthly
            interval = timedelta(days=30)  # Approximate

        schedule = []
        current_date = start_date

        for i in range(num_installments):
            amount = base_amount
            if i == num_installments - 1:
                # Last installment gets any remainder
                amount += remainder

            schedule.append(
                InstallmentScheduleItem(
                    installment_number=i + 1,
                    due_date=current_date,
                    amount=amount,
                )
            )
            current_date += interval

        return schedule

    @staticmethod
    def calculate_cancellation_refund(
        enrollment_amount: Decimal,
        enrolled_at: date,
        cancel_date: date = None,
        processing_fee: Decimal = Decimal("25.00"),
    ) -> tuple[Decimal, str]:
        """
        Calculate refund amount based on 15-day cancellation policy.

        Returns (refund_amount, policy_applied)
        """
        if cancel_date is None:
            cancel_date = date.today()

        days_enrolled = (cancel_date - enrolled_at).days

        if days_enrolled < 15:
            # Full refund minus processing fee
            refund = max(enrollment_amount - processing_fee, Decimal("0.00"))
            return refund, "Full refund (within 15 days) minus $25 processing fee"
        else:
            # No refund after 15 days
            return Decimal("0.00"), "No refund (enrolled more than 15 days)"
