"""Enrollment API endpoints for managing class enrollments."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_admin, get_current_user
from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User
from app.tasks.email_tasks import send_cancellation_confirmation_email
from app.schemas.enrollment import (
    CancellationRefundPreview,
    EnrollmentCancel,
    EnrollmentListResponse,
    EnrollmentResponse,
    EnrollmentTransfer,
)
from app.services.pricing_service import PricingService
from core.db import get_db
from core.exceptions.base import BadRequestException, ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


async def enrollment_to_response(
    enrollment: Enrollment,
    db_session: AsyncSession,
) -> EnrollmentResponse:
    """Convert Enrollment model to response with related data."""
    # Get child and class names
    child_name = None
    class_name = None

    child_result = await db_session.execute(
        select(Child).where(Child.id == enrollment.child_id)
    )
    child = child_result.scalar_one_or_none()
    if child:
        child_name = child.full_name

    class_result = await db_session.execute(
        select(Class).where(Class.id == enrollment.class_id)
    )
    class_ = class_result.scalar_one_or_none()
    if class_:
        class_name = class_.name

    return EnrollmentResponse(
        id=enrollment.id,
        child_id=enrollment.child_id,
        class_id=enrollment.class_id,
        user_id=enrollment.user_id,
        status=enrollment.status.value,
        enrolled_at=enrollment.enrolled_at,
        cancelled_at=enrollment.cancelled_at,
        cancellation_reason=enrollment.cancellation_reason,
        base_price=enrollment.base_price,
        discount_amount=enrollment.discount_amount,
        final_price=enrollment.final_price,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
        child_name=child_name,
        class_name=class_name,
    )


# ============== User Endpoints ==============


@router.get("/my", response_model=EnrollmentListResponse)
async def list_my_enrollments(
    status: str = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentListResponse:
    """
    List all enrollments for the current user.

    Can filter by status.
    """
    logger.info(f"List enrollments for user: {current_user.id}")

    query = select(Enrollment).where(Enrollment.user_id == current_user.id)

    if status:
        query = query.where(Enrollment.status == EnrollmentStatus(status))

    query = query.order_by(Enrollment.created_at.desc())

    result = await db_session.execute(query)
    enrollments = result.scalars().all()

    items = [await enrollment_to_response(e, db_session) for e in enrollments]

    return EnrollmentListResponse(items=items, total=len(items))


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Get enrollment details by ID.
    """
    logger.info(f"Get enrollment {enrollment_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this enrollment")

    return await enrollment_to_response(enrollment, db_session)


# ============== Cancellation ==============


@router.get("/{enrollment_id}/cancellation-preview", response_model=CancellationRefundPreview)
async def preview_cancellation(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> CancellationRefundPreview:
    """
    Preview refund for cancelling an enrollment.

    Shows 15-day policy calculation and expected refund amount.
    """
    logger.info(f"Preview cancellation for enrollment {enrollment_id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this enrollment")

    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise BadRequestException(message="Only active enrollments can be cancelled")

    if not enrollment.enrolled_at:
        raise BadRequestException(message="Enrollment date not set")

    enrolled_date = enrollment.enrolled_at.date()
    today = date.today()
    days_enrolled = (today - enrolled_date).days

    refund_amount, policy = PricingService.calculate_cancellation_refund(
        enrollment_amount=enrollment.final_price,
        enrolled_at=enrolled_date,
        cancel_date=today,
    )

    return CancellationRefundPreview(
        enrollment_id=enrollment.id,
        enrollment_amount=enrollment.final_price,
        enrolled_at=enrolled_date,
        days_enrolled=days_enrolled,
        refund_amount=refund_amount,
        policy_applied=policy,
        processing_fee=25 if days_enrolled < 15 else 0,
    )


@router.post("/{enrollment_id}/cancel")
async def cancel_enrollment(
    enrollment_id: str,
    data: EnrollmentCancel = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Cancel an enrollment.

    Refund is calculated based on 15-day policy:
    - Within 15 days: Full refund minus $25 processing fee
    - After 15 days: No refund
    """
    logger.info(f"Cancel enrollment {enrollment_id} by user: {current_user.id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this enrollment")

    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise BadRequestException(message="Only active enrollments can be cancelled")

    # Calculate refund
    refund_amount = None
    if enrollment.enrolled_at:
        refund_amount, policy = PricingService.calculate_cancellation_refund(
            enrollment_amount=enrollment.final_price,
            enrolled_at=enrollment.enrolled_at.date(),
        )

    # Update enrollment
    enrollment.status = EnrollmentStatus.CANCELLED
    enrollment.cancelled_at = datetime.now(timezone.utc)
    enrollment.cancellation_reason = data.reason if data else None

    # Get child and class details for email
    child_result = await db_session.execute(select(Child).where(Child.id == enrollment.child_id))
    child = child_result.scalar_one_or_none()

    class_result = await db_session.execute(select(Class).where(Class.id == enrollment.class_id))
    class_ = class_result.scalar_one_or_none()

    await db_session.commit()

    # Send cancellation confirmation email
    if child and class_:
        send_cancellation_confirmation_email.delay(
            user_email=current_user.email,
            user_name=current_user.full_name,
            child_name=child.full_name,
            class_name=class_.name,
            cancellation_date=datetime.now(timezone.utc).date().isoformat(),
            refund_amount=str(refund_amount) if refund_amount else None,
            effective_date=datetime.now(timezone.utc).date().isoformat(),
        )

    return {
        "message": "Enrollment cancelled successfully",
        "refund_amount": str(refund_amount) if refund_amount else "0.00",
    }


@router.post("/{enrollment_id}/transfer", response_model=EnrollmentResponse)
async def transfer_enrollment(
    enrollment_id: str,
    data: EnrollmentTransfer,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Transfer enrollment to a different class.

    Must be within same program and price must be equal or less.
    Price difference refunds are handled separately.
    """
    logger.info(f"Transfer enrollment {enrollment_id} to class {data.new_class_id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.user_id != current_user.id and current_user.role.value not in ["owner", "admin"]:
        raise ForbiddenException(message="You don't have access to this enrollment")

    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise BadRequestException(message="Only active enrollments can be transferred")

    # Get new class
    class_result = await db_session.execute(
        select(Class).where(Class.id == data.new_class_id)
    )
    new_class = class_result.scalar_one_or_none()

    if not new_class:
        raise NotFoundException(message="Target class not found")

    if not new_class.is_active:
        raise BadRequestException(message="Target class is not active")

    if new_class.current_enrollment >= new_class.capacity:
        raise BadRequestException(message="Target class is full")

    # Check for existing enrollment in target class
    existing_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.child_id == enrollment.child_id,
            Enrollment.class_id == data.new_class_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if existing_result.scalar_one_or_none():
        raise BadRequestException(message="Child is already enrolled in target class")

    # Update enrollment
    old_class_id = enrollment.class_id
    enrollment.class_id = data.new_class_id

    # Update class enrollment counts
    old_class_result = await db_session.execute(
        select(Class).where(Class.id == old_class_id)
    )
    old_class = old_class_result.scalar_one_or_none()
    if old_class:
        old_class.current_enrollment = max(0, old_class.current_enrollment - 1)

    new_class.current_enrollment += 1

    await db_session.commit()

    return await enrollment_to_response(enrollment, db_session)


# ============== Admin Endpoints ==============


@router.get("/", response_model=EnrollmentListResponse)
async def list_all_enrollments(
    status: str = None,
    class_id: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentListResponse:
    """
    List all enrollments (admin only).

    Can filter by status and class.
    """
    logger.info(f"List all enrollments by admin: {current_user.id}")

    query = select(Enrollment)

    if status:
        query = query.where(Enrollment.status == EnrollmentStatus(status))
    if class_id:
        query = query.where(Enrollment.class_id == class_id)

    query = query.order_by(Enrollment.created_at.desc()).offset(offset).limit(limit)

    result = await db_session.execute(query)
    enrollments = result.scalars().all()

    items = [await enrollment_to_response(e, db_session) for e in enrollments]

    # Get total
    count_query = select(Enrollment)
    if status:
        count_query = count_query.where(Enrollment.status == EnrollmentStatus(status))
    if class_id:
        count_query = count_query.where(Enrollment.class_id == class_id)
    count_result = await db_session.execute(count_query)
    total = len(count_result.scalars().all())

    return EnrollmentListResponse(items=items, total=total)


@router.post("/{enrollment_id}/activate", response_model=EnrollmentResponse)
async def activate_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Activate a pending enrollment (admin only).

    Usually done after payment confirmation.
    """
    logger.info(f"Activate enrollment {enrollment_id} by admin: {current_user.id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    if enrollment.status != EnrollmentStatus.PENDING:
        raise BadRequestException(message="Only pending enrollments can be activated")

    # Get class to update count
    class_result = await db_session.execute(
        select(Class).where(Class.id == enrollment.class_id)
    )
    class_ = class_result.scalar_one_or_none()

    if class_ and class_.current_enrollment >= class_.capacity:
        raise BadRequestException(message="Class is full")

    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.enrolled_at = datetime.now(timezone.utc)

    if class_:
        class_.current_enrollment += 1

    await db_session.commit()

    return await enrollment_to_response(enrollment, db_session)
