"""Discount and scholarship API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.discount import DiscountCode, DiscountType, Scholarship
from app.models.user import User
from app.schemas.discount import (
    DiscountCodeCreate,
    DiscountCodeListResponse,
    DiscountCodeResponse,
    DiscountCodeUpdate,
    DiscountCodeValidate,
    DiscountValidationResponse,
    ScholarshipCreate,
    ScholarshipListResponse,
    ScholarshipResponse,
    ScholarshipUpdate,
)
from app.services.pricing_service import PricingService
from core.db import get_db
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/discounts", tags=["Discounts"])


# ============== Discount Code Validation (Public) ==============


@router.post("/validate", response_model=DiscountValidationResponse)
async def validate_discount_code(
    data: DiscountCodeValidate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> DiscountValidationResponse:
    """
    Validate a discount code and calculate its value.

    Returns whether the code is valid and the discount amount for given order.
    """
    logger.info(f"Validate discount code {data.code} for user: {current_user.id}")

    pricing_service = PricingService(db_session)

    validation = await pricing_service.validate_discount_code(
        code=data.code,
        order_amount=data.order_amount,
        program_id=data.program_id,
        class_id=data.class_id,
    )

    return DiscountValidationResponse(
        is_valid=validation.is_valid,
        error_message=validation.error_message,
        discount_type=validation.discount_type,
        discount_value=validation.discount_value,
        discount_amount=validation.discount_amount,
    )


# ============== Discount Code Admin CRUD ==============


@router.post("/codes", response_model=DiscountCodeResponse)
async def create_discount_code(
    data: DiscountCodeCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> DiscountCodeResponse:
    """
    Create a new discount code (admin only).
    """
    logger.info(f"Create discount code {data.code} by admin: {current_user.id}")

    # Check for existing code
    existing = await DiscountCode.get_by_code(db_session, data.code)
    if existing:
        raise BadRequestException(message="Discount code already exists")

    discount = DiscountCode(
        id=str(uuid4()),
        code=data.code.upper().strip(),
        description=data.description,
        discount_type=DiscountType(data.discount_type),
        discount_value=data.discount_value,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        max_uses=data.max_uses,
        current_uses=0,
        max_uses_per_user=data.max_uses_per_user,
        min_order_amount=data.min_order_amount,
        applies_to_program_id=data.applies_to_program_id,
        applies_to_class_id=data.applies_to_class_id,
        is_active=True,
        created_by_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)

    logger.info(f"Discount code created: {discount.id}")
    return DiscountCodeResponse.model_validate(discount)


@router.get("/codes", response_model=DiscountCodeListResponse)
async def list_discount_codes(
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> DiscountCodeListResponse:
    """
    List all discount codes (admin only).
    """
    logger.info(f"List discount codes by admin: {current_user.id}")

    query = select(DiscountCode)

    if is_active is not None:
        query = query.where(DiscountCode.is_active == is_active)

    query = query.order_by(DiscountCode.created_at.desc()).offset(offset).limit(limit)

    result = await db_session.execute(query)
    codes = result.scalars().all()

    # Get total
    count_query = select(DiscountCode)
    if is_active is not None:
        count_query = count_query.where(DiscountCode.is_active == is_active)
    count_result = await db_session.execute(count_query)
    total = len(count_result.scalars().all())

    return DiscountCodeListResponse(
        items=[DiscountCodeResponse.model_validate(c) for c in codes],
        total=total,
    )


@router.get("/codes/{code_id}", response_model=DiscountCodeResponse)
async def get_discount_code(
    code_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> DiscountCodeResponse:
    """
    Get discount code details (admin only).
    """
    logger.info(f"Get discount code {code_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(DiscountCode).where(DiscountCode.id == code_id)
    )
    discount = result.scalar_one_or_none()

    if not discount:
        raise NotFoundException(message="Discount code not found")

    return DiscountCodeResponse.model_validate(discount)


@router.put("/codes/{code_id}", response_model=DiscountCodeResponse)
async def update_discount_code(
    code_id: str,
    data: DiscountCodeUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> DiscountCodeResponse:
    """
    Update discount code (admin only).
    """
    logger.info(f"Update discount code {code_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(DiscountCode).where(DiscountCode.id == code_id)
    )
    discount = result.scalar_one_or_none()

    if not discount:
        raise NotFoundException(message="Discount code not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(discount, field, value)

    await db_session.commit()
    await db_session.refresh(discount)

    logger.info(f"Discount code updated: {code_id}")
    return DiscountCodeResponse.model_validate(discount)


@router.delete("/codes/{code_id}")
async def delete_discount_code(
    code_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Deactivate a discount code (admin only).

    Soft delete - sets is_active to False.
    """
    logger.info(f"Delete discount code {code_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(DiscountCode).where(DiscountCode.id == code_id)
    )
    discount = result.scalar_one_or_none()

    if not discount:
        raise NotFoundException(message="Discount code not found")

    discount.is_active = False
    await db_session.commit()

    return {"message": "Discount code deactivated successfully"}


# ============== Scholarship Admin CRUD ==============


@router.post("/scholarships", response_model=ScholarshipResponse)
async def create_scholarship(
    data: ScholarshipCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ScholarshipResponse:
    """
    Create a scholarship for a user (admin only).

    Can apply to all children or a specific child.
    """
    logger.info(f"Create scholarship for user {data.user_id} by admin: {current_user.id}")

    scholarship = Scholarship(
        id=str(uuid4()),
        user_id=data.user_id,
        child_id=data.child_id,
        scholarship_type=data.scholarship_type,
        discount_percentage=data.discount_percentage,
        approved_by_id=current_user.id,
        approved_at=datetime.now(timezone.utc),
        valid_until=data.valid_until,
        is_active=True,
        notes=data.notes,
        organization_id=current_user.organization_id,
    )
    db_session.add(scholarship)
    await db_session.commit()
    await db_session.refresh(scholarship)

    logger.info(f"Scholarship created: {scholarship.id}")
    return ScholarshipResponse.model_validate(scholarship)


@router.get("/scholarships", response_model=ScholarshipListResponse)
async def list_scholarships(
    user_id: str = None,
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ScholarshipListResponse:
    """
    List all scholarships (admin only).
    """
    logger.info(f"List scholarships by admin: {current_user.id}")

    query = select(Scholarship)

    if user_id:
        query = query.where(Scholarship.user_id == user_id)
    if is_active is not None:
        query = query.where(Scholarship.is_active == is_active)

    query = query.order_by(Scholarship.created_at.desc()).offset(offset).limit(limit)

    result = await db_session.execute(query)
    scholarships = result.scalars().all()

    # Get total
    count_query = select(Scholarship)
    if user_id:
        count_query = count_query.where(Scholarship.user_id == user_id)
    if is_active is not None:
        count_query = count_query.where(Scholarship.is_active == is_active)
    count_result = await db_session.execute(count_query)
    total = len(count_result.scalars().all())

    return ScholarshipListResponse(
        items=[ScholarshipResponse.model_validate(s) for s in scholarships],
        total=total,
    )


@router.get("/scholarships/{scholarship_id}", response_model=ScholarshipResponse)
async def get_scholarship(
    scholarship_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ScholarshipResponse:
    """
    Get scholarship details (admin only).
    """
    logger.info(f"Get scholarship {scholarship_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(Scholarship).where(Scholarship.id == scholarship_id)
    )
    scholarship = result.scalar_one_or_none()

    if not scholarship:
        raise NotFoundException(message="Scholarship not found")

    return ScholarshipResponse.model_validate(scholarship)


@router.put("/scholarships/{scholarship_id}", response_model=ScholarshipResponse)
async def update_scholarship(
    scholarship_id: str,
    data: ScholarshipUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ScholarshipResponse:
    """
    Update scholarship (admin only).
    """
    logger.info(f"Update scholarship {scholarship_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(Scholarship).where(Scholarship.id == scholarship_id)
    )
    scholarship = result.scalar_one_or_none()

    if not scholarship:
        raise NotFoundException(message="Scholarship not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scholarship, field, value)

    await db_session.commit()
    await db_session.refresh(scholarship)

    logger.info(f"Scholarship updated: {scholarship_id}")
    return ScholarshipResponse.model_validate(scholarship)


@router.delete("/scholarships/{scholarship_id}")
async def delete_scholarship(
    scholarship_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Deactivate a scholarship (admin only).
    """
    logger.info(f"Delete scholarship {scholarship_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(Scholarship).where(Scholarship.id == scholarship_id)
    )
    scholarship = result.scalar_one_or_none()

    if not scholarship:
        raise NotFoundException(message="Scholarship not found")

    scholarship.is_active = False
    await db_session.commit()

    return {"message": "Scholarship deactivated successfully"}


# ============== User's Scholarships ==============


@router.get("/my-scholarships", response_model=ScholarshipListResponse)
async def list_my_scholarships(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> ScholarshipListResponse:
    """
    List scholarships for the current user.
    """
    logger.info(f"List scholarships for user: {current_user.id}")

    result = await db_session.execute(
        select(Scholarship)
        .where(Scholarship.user_id == current_user.id)
        .where(Scholarship.is_active == True)
        .order_by(Scholarship.created_at.desc())
    )
    scholarships = result.scalars().all()

    return ScholarshipListResponse(
        items=[ScholarshipResponse.model_validate(s) for s in scholarships],
        total=len(scholarships),
    )


# ============== Sibling Discount Eligibility ==============


@router.get("/sibling-eligibility/{child_id}")
async def check_sibling_discount_eligibility(
    child_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if a child is eligible for sibling discount.

    Returns the number of siblings with active enrollments and applicable discount percentage.
    """
    from app.models.child import Child
    from app.models.enrollment import Enrollment, EnrollmentStatus

    logger.info(f"Check sibling discount for child {child_id} by user: {current_user.id}")

    # Get all children for this user
    result = await db_session.execute(
        select(Child).where(Child.parent_user_id == current_user.id)
    )
    all_children = result.scalars().all()

    # Count active enrollments across all children
    all_child_ids = [c.id for c in all_children]
    enrollment_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.child_id.in_(all_child_ids), Enrollment.status == EnrollmentStatus.ACTIVE
        )
    )
    active_enrollments = enrollment_result.scalars().all()

    # Determine discount tier based on sibling count
    # Count how many children have active enrollments (this is the sibling count)
    sibling_count = len(active_enrollments)

    # Get discount percentage from PricingService
    discount_percentage = PricingService.SIBLING_DISCOUNTS.get(sibling_count, 0)

    return {
        "eligible": sibling_count >= 2,
        "sibling_count": sibling_count,
        "discount_percentage": discount_percentage,
        "discount_label": (
            f"{discount_percentage}% off for {sibling_count}{'nd' if sibling_count == 2 else 'rd' if sibling_count == 3 else 'th'} child"
            if discount_percentage
            else None
        ),
    }
