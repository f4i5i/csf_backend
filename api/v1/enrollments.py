"""Enrollment API endpoints for managing class enrollments."""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import (
    get_current_admin,
    get_current_parent_or_admin,
    get_current_user,
    get_current_staff,
)
from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import OrderLineItem
from app.models.user import User
from app.tasks.email_tasks import send_cancellation_confirmation_email
from app.schemas.enrollment import (
    AdminEnrollmentCreate,
    AdminEnrollmentUpdate,
    CancellationRefundPreview,
    ClaimWaitlistRequest,
    EnrollmentCancel,
    EnrollmentListResponse,
    EnrollmentResponse,
    EnrollmentTransfer,
    JoinWaitlistRequest,
    PromoteWaitlistRequest,
    WaitlistEntryResponse,
    WaitlistListResponse,
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
        waitlist_priority=enrollment.waitlist_priority,
        auto_promote=enrollment.auto_promote,
        claim_window_expires_at=enrollment.claim_window_expires_at,
        promoted_at=enrollment.promoted_at,
        child_name=child_name,
        class_name=class_name,
    )


# ============== User Endpoints ==============


@router.get("/my", response_model=EnrollmentListResponse)
async def list_my_enrollments(
    status: str = None,
    child_id: Optional[str] = None,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentListResponse:
    """
    List all enrollments for the current user.

    Can filter by status and child_id.
    """
    logger.info(f"List enrollments for user: {current_user.id}, child_id: {child_id}")

    # If child_id is provided, verify child belongs to current user (security check)
    if child_id:
        child_result = await db_session.execute(
            select(Child).where(Child.id == child_id, Child.user_id == current_user.id)
        )
        child = child_result.scalar_one_or_none()
        if not child and current_user.role.value not in ["owner", "admin"]:
            raise ForbiddenException(message="You don't have access to this child")

    query = select(Enrollment).where(Enrollment.user_id == current_user.id)

    if status:
        query = query.where(Enrollment.status == EnrollmentStatus(status))

    if child_id:
        query = query.where(Enrollment.child_id == child_id)

    query = query.order_by(Enrollment.created_at.desc())

    result = await db_session.execute(query)
    enrollments = result.scalars().all()

    items = [await enrollment_to_response(e, db_session) for e in enrollments]

    return EnrollmentListResponse(items=items, total=len(items))


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_parent_or_admin),
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
    current_user: User = Depends(get_current_parent_or_admin),
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
        processing_fee=0,  # No processing fee
    )


@router.post("/{enrollment_id}/cancel")
async def cancel_enrollment(
    enrollment_id: str,
    data: EnrollmentCancel = None,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Cancel an enrollment.

    Refund is calculated based on 15-day policy from cancellation request date:
    - Within 15 days: Full refund (no processing fee)
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

    # Decrement class enrollment count
    if class_:
        await class_.decrement_enrollment(db_session)

    await db_session.commit()

    # Send cancellation confirmation email (non-blocking)
    if child and class_:
        try:
            send_cancellation_confirmation_email.delay(
                user_email=current_user.email,
                user_name=current_user.full_name,
                child_name=child.full_name,
                class_name=class_.name,
                cancellation_date=datetime.now(timezone.utc).date().isoformat(),
                refund_amount=str(refund_amount) if refund_amount else None,
                effective_date=datetime.now(timezone.utc).date().isoformat(),
            )
        except Exception as email_error:
            # Don't fail the cancellation if email task queuing fails (e.g., Redis down)
            logger.warning(f"Failed to queue cancellation confirmation email: {email_error}")

    return {
        "message": "Enrollment cancelled successfully",
        "refund_amount": str(refund_amount) if refund_amount else "0.00",
    }


@router.post("/{enrollment_id}/transfer", response_model=EnrollmentResponse)
async def transfer_enrollment(
    enrollment_id: str,
    data: EnrollmentTransfer,
    current_user: User = Depends(get_current_parent_or_admin),
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


# ============== Waitlist Endpoints ==============


@router.post("/waitlist/join", response_model=EnrollmentResponse)
async def join_waitlist(
    data: JoinWaitlistRequest,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Join waitlist for a full class.

    Priority waitlist (auto-charge): Requires payment method on file.
    Regular waitlist: 12-hour claim window when spot opens.
    """
    logger.info(f"User {current_user.id} joining waitlist for class {data.class_id}")

    # Verify child belongs to user
    child_result = await db_session.execute(
        select(Child).where(Child.id == data.child_id, Child.user_id == current_user.id)
    )
    child = child_result.scalar_one_or_none()
    if not child:
        raise NotFoundException(message="Child not found")

    # Verify class exists
    class_result = await db_session.execute(select(Class).where(Class.id == data.class_id))
    class_ = class_result.scalar_one_or_none()
    if not class_:
        raise NotFoundException(message="Class not found")

    # Check if child already enrolled or waitlisted
    existing_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.child_id == data.child_id,
            Enrollment.class_id == data.class_id,
            Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.WAITLISTED, EnrollmentStatus.PENDING]),
        )
    )
    if existing_result.scalar_one_or_none():
        raise BadRequestException(message="Child is already enrolled or waitlisted for this class")

    # Validate priority level
    if data.priority not in ["priority", "regular"]:
        raise BadRequestException(message="Invalid priority level. Must be 'priority' or 'regular'")

    # Priority waitlist requires payment method
    if data.priority == "priority" and not data.payment_method_id:
        raise BadRequestException(message="Priority waitlist requires a payment method")

    # Create waitlist enrollment
    pricing_service = PricingService(db_session)
    order_data = await pricing_service.calculate_order(
        user_id=current_user.id,
        items=[{"class_id": data.class_id, "child_id": data.child_id}],
    )

    enrollment = Enrollment(
        child_id=data.child_id,
        class_id=data.class_id,
        user_id=current_user.id,
        status=EnrollmentStatus.WAITLISTED,
        waitlist_priority=data.priority,
        auto_promote=(data.priority == "priority"),
        base_price=class_.base_price,
        discount_amount=order_data["items"][0]["discount_amount"],
        final_price=order_data["items"][0]["final_price"],
        organization_id=current_user.organization_id,
    )

    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)

    return await enrollment_to_response(enrollment, db_session)


@router.post("/{enrollment_id}/waitlist/claim", response_model=EnrollmentResponse)
async def claim_waitlist_spot(
    enrollment_id: str,
    data: ClaimWaitlistRequest,
    current_user: User = Depends(get_current_parent_or_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Claim a regular waitlist spot within the 12-hour window.

    Requires payment method to complete the claim.
    """
    logger.info(f"User {current_user.id} claiming waitlist spot for enrollment {enrollment_id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.user_id != current_user.id:
        raise ForbiddenException(message="You don't have access to this enrollment")

    # Claim the spot (will validate status, priority, and window)
    try:
        await enrollment.claim_waitlist_spot(db_session)
    except ValueError as e:
        raise BadRequestException(message=str(e))

    # TODO: Process payment with data.payment_method_id
    # For now, we just mark it as claimed

    await db_session.refresh(enrollment)
    return await enrollment_to_response(enrollment, db_session)


@router.get("/waitlist/class/{class_id}", response_model=WaitlistListResponse)
async def get_class_waitlist(
    class_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> WaitlistListResponse:
    """
    Get waitlist for a class (admin only).

    Returns all waitlisted enrollments ordered by priority and creation time.
    """
    logger.info(f"Admin {current_user.id} viewing waitlist for class {class_id}")

    # Verify class exists
    class_result = await db_session.execute(select(Class).where(Class.id == class_id))
    class_ = class_result.scalar_one_or_none()
    if not class_:
        raise NotFoundException(message="Class not found")

    # Get waitlisted enrollments
    enrollments = await Enrollment.get_waitlisted_by_class(db_session, class_id)

    # Build response with position information
    entries = []
    priority_count = 0
    regular_count = 0

    for idx, enrollment in enumerate(enrollments, start=1):
        # Get child name
        child_result = await db_session.execute(
            select(Child).where(Child.id == enrollment.child_id)
        )
        child = child_result.scalar_one_or_none()

        if enrollment.waitlist_priority == "priority":
            priority_count += 1
        else:
            regular_count += 1

        entries.append(
            WaitlistEntryResponse(
                enrollment_id=enrollment.id,
                child_id=enrollment.child_id,
                child_name=child.full_name if child else "Unknown",
                class_id=enrollment.class_id,
                class_name=class_.name,
                waitlist_priority=enrollment.waitlist_priority,
                position=idx,
                auto_promote=enrollment.auto_promote,
                claim_window_expires_at=enrollment.claim_window_expires_at,
                created_at=enrollment.created_at,
            )
        )

    return WaitlistListResponse(
        class_id=class_id,
        class_name=class_.name,
        total_waitlisted=len(entries),
        priority_count=priority_count,
        regular_count=regular_count,
        entries=entries,
    )


@router.post("/{enrollment_id}/waitlist/promote", response_model=EnrollmentResponse)
async def promote_from_waitlist(
    enrollment_id: str,
    data: PromoteWaitlistRequest = None,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Manually promote an enrollment from waitlist to active (admin only).

    Can optionally skip payment requirement.
    """
    logger.info(f"Admin {current_user.id} promoting enrollment {enrollment_id} from waitlist")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Verify class has capacity
    class_result = await db_session.execute(
        select(Class).where(Class.id == enrollment.class_id)
    )
    class_ = class_result.scalar_one_or_none()

    if class_ and class_.current_enrollment >= class_.capacity:
        raise BadRequestException(message="Class is full")

    # Promote
    try:
        await enrollment.promote_from_waitlist(db_session)
    except ValueError as e:
        raise BadRequestException(message=str(e))

    # Update class enrollment count
    if class_:
        class_.current_enrollment += 1
        await db_session.commit()

    # TODO: Process payment if not skip_payment

    await db_session.refresh(enrollment)
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


@router.get("/class/{class_id}", response_model=EnrollmentListResponse)
async def list_enrollments_by_class(
    class_id: str,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_staff),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentListResponse:
    """List enrollments for a specific class (coach/admin/owner)."""
    logger.info(
        f"List enrollments for class {class_id} requested by user: {current_user.id}"
    )

    query = select(Enrollment).where(Enrollment.class_id == class_id)
    if status:
        query = query.where(Enrollment.status == EnrollmentStatus(status))

    query = query.order_by(Enrollment.created_at.desc())
    result = await db_session.execute(query)
    enrollments = result.scalars().all()

    items = [await enrollment_to_response(e, db_session) for e in enrollments]
    return EnrollmentListResponse(items=items, total=len(items))


@router.delete("/cleanup/pending")
async def cleanup_pending_enrollments(
    hours_old: int = 24,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Clean up stale PENDING enrollments from failed checkouts (admin only).

    Deletes PENDING enrollments older than the specified hours (default 24).
    This helps clean up orphan enrollments from failed checkout attempts.
    """
    from datetime import timedelta

    logger.info(f"Cleanup pending enrollments older than {hours_old} hours by admin: {current_user.id}")

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)

    # Find old pending enrollments
    result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.status == EnrollmentStatus.PENDING,
            Enrollment.created_at < cutoff_time,
        )
    )
    old_pending = result.scalars().all()

    deleted_count = 0
    for enrollment in old_pending:
        await db_session.delete(enrollment)
        deleted_count += 1

    await db_session.commit()

    logger.info(f"Deleted {deleted_count} stale pending enrollments")

    return {
        "message": f"Cleaned up {deleted_count} stale pending enrollments",
        "deleted_count": deleted_count,
    }


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
    await db_session.refresh(enrollment)

    return await enrollment_to_response(enrollment, db_session)


# ============== Admin CRUD Endpoints ==============


@router.post("/", response_model=EnrollmentResponse)
async def create_enrollment(
    data: AdminEnrollmentCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Create an enrollment directly (admin only).

    Allows admin to enroll a child in a class without going through checkout.
    """
    logger.info(f"Admin {current_user.id} creating enrollment for child {data.child_id} in class {data.class_id}")

    # Verify child exists
    child_result = await db_session.execute(
        select(Child).where(Child.id == data.child_id)
    )
    child = child_result.scalar_one_or_none()
    if not child:
        raise NotFoundException(message="Child not found")

    # Verify class exists
    class_result = await db_session.execute(
        select(Class).where(Class.id == data.class_id)
    )
    class_ = class_result.scalar_one_or_none()
    if not class_:
        raise NotFoundException(message="Class not found")

    # Check if child already enrolled in this class
    existing_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.child_id == data.child_id,
            Enrollment.class_id == data.class_id,
            Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING]),
        )
    )
    if existing_result.scalar_one_or_none():
        raise BadRequestException(message="Child is already enrolled in this class")

    # Check class capacity for active enrollments
    if data.status == "active" and class_.current_enrollment >= class_.capacity:
        raise BadRequestException(message="Class is full")

    # Calculate prices
    base_price = data.base_price if data.base_price is not None else class_.base_price
    discount_amount = data.discount_amount
    final_price = data.final_price if data.final_price is not None else (base_price - discount_amount)

    # Map status string to enum
    status_map = {
        "active": EnrollmentStatus.ACTIVE,
        "pending": EnrollmentStatus.PENDING,
        "waitlisted": EnrollmentStatus.WAITLISTED,
        "completed": EnrollmentStatus.COMPLETED,
        "cancelled": EnrollmentStatus.CANCELLED,
    }
    enrollment_status = status_map.get(data.status.lower(), EnrollmentStatus.ACTIVE)

    # Create enrollment
    enrollment = Enrollment(
        child_id=data.child_id,
        class_id=data.class_id,
        user_id=child.user_id,
        status=enrollment_status,
        base_price=base_price,
        discount_amount=discount_amount,
        final_price=final_price,
        organization_id=current_user.organization_id,
    )

    if enrollment_status == EnrollmentStatus.ACTIVE:
        enrollment.enrolled_at = datetime.now(timezone.utc)
        class_.current_enrollment += 1

    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)

    logger.info(f"Enrollment created successfully: {enrollment.id}")
    return await enrollment_to_response(enrollment, db_session)


@router.put("/{enrollment_id}", response_model=EnrollmentResponse)
async def update_enrollment(
    enrollment_id: str,
    data: AdminEnrollmentUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """
    Update an enrollment (admin only).

    Can update status, prices, and other enrollment details.
    """
    logger.info(f"Admin {current_user.id} updating enrollment {enrollment_id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Get class for enrollment count updates
    class_result = await db_session.execute(
        select(Class).where(Class.id == enrollment.class_id)
    )
    class_ = class_result.scalar_one_or_none()

    old_status = enrollment.status

    # Update fields
    if data.status is not None:
        status_map = {
            "active": EnrollmentStatus.ACTIVE,
            "pending": EnrollmentStatus.PENDING,
            "waitlisted": EnrollmentStatus.WAITLISTED,
            "completed": EnrollmentStatus.COMPLETED,
            "cancelled": EnrollmentStatus.CANCELLED,
        }
        new_status = status_map.get(data.status.lower())
        if not new_status:
            raise BadRequestException(message=f"Invalid status: {data.status}")

        # Handle class enrollment count changes
        if class_:
            # If changing TO active from non-active
            if new_status == EnrollmentStatus.ACTIVE and old_status != EnrollmentStatus.ACTIVE:
                if class_.current_enrollment >= class_.capacity:
                    raise BadRequestException(message="Class is full")
                class_.current_enrollment += 1
                enrollment.enrolled_at = datetime.now(timezone.utc)
            # If changing FROM active to non-active
            elif old_status == EnrollmentStatus.ACTIVE and new_status != EnrollmentStatus.ACTIVE:
                class_.current_enrollment = max(0, class_.current_enrollment - 1)

        # Handle cancellation
        if new_status == EnrollmentStatus.CANCELLED and old_status != EnrollmentStatus.CANCELLED:
            enrollment.cancelled_at = datetime.now(timezone.utc)

        enrollment.status = new_status

    if data.base_price is not None:
        enrollment.base_price = data.base_price

    if data.discount_amount is not None:
        enrollment.discount_amount = data.discount_amount

    if data.final_price is not None:
        enrollment.final_price = data.final_price

    if data.cancellation_reason is not None:
        enrollment.cancellation_reason = data.cancellation_reason

    await db_session.commit()
    await db_session.refresh(enrollment)

    logger.info(f"Enrollment updated successfully: {enrollment_id}")
    return await enrollment_to_response(enrollment, db_session)


@router.delete("/{enrollment_id}")
async def delete_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an enrollment (admin only).

    This permanently removes the enrollment record. Use cancel for normal cancellations.
    Related order line items will have their enrollment_id set to NULL to preserve order history.
    """
    logger.info(f"Admin {current_user.id} deleting enrollment {enrollment_id}")

    result = await db_session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Update class enrollment count if was active
    if enrollment.status == EnrollmentStatus.ACTIVE:
        class_result = await db_session.execute(
            select(Class).where(Class.id == enrollment.class_id)
        )
        class_ = class_result.scalar_one_or_none()
        if class_:
            class_.current_enrollment = max(0, class_.current_enrollment - 1)

    # Unlink related order line items (set enrollment_id to NULL to preserve order history)
    await db_session.execute(
        update(OrderLineItem)
        .where(OrderLineItem.enrollment_id == enrollment_id)
        .values(enrollment_id=None)
    )

    await db_session.delete(enrollment)
    await db_session.commit()

    logger.info(f"Enrollment deleted successfully: {enrollment_id}")
    return {"message": "Enrollment deleted successfully"}
