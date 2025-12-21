"""Check-in API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.checkin import CheckIn
from app.models.class_ import Class
from app.models.enrollment import Enrollment
from app.models.user import Role, User
from app.services.sms_service import get_sms_service
from app.schemas.checkin import (
    BulkCheckInRequest,
    CheckInCreate,
    CheckInListResponse,
    CheckInResponse,
    CheckInStatusListResponse,
    CheckInStatusResponse,
    TextClassRequest,
    TextClassResponse,
)
from core.db import get_db
from core.exceptions.base import ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/check-in", tags=["Check-In"])


@router.post("/", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def check_in_student(
    data: CheckInCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckInResponse:
    """Check in a single student. Parent can check in their child, coach can check in anyone."""
    # Verify enrollment exists
    enrollment = await Enrollment.get_by_id(db_session, data.enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Verify class exists
    class_ = await Class.get_by_id(db_session, data.class_id)
    if not class_:
        raise NotFoundException(message="Class not found")

    # Check permissions
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        # Parent can only check in their own children
        if enrollment.child.user_id != current_user.id:
            raise ForbiddenException(message="Not authorized")

    # Perform check-in
    checkin = await CheckIn.check_in_student(
        db_session,
        data.enrollment_id,
        data.class_id,
        data.check_in_date,
        data.is_late,
        organization_id=current_user.organization_id,
    )
    await db_session.commit()
    await db_session.refresh(checkin)

    return CheckInResponse.model_validate(checkin)


@router.post("/bulk", response_model=CheckInListResponse)
async def bulk_check_in(
    data: BulkCheckInRequest,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckInListResponse:
    """Bulk check in multiple students. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can perform bulk check-in")

    # Verify class exists
    class_ = await Class.get_by_id(db_session, data.class_id)
    if not class_:
        raise NotFoundException(message="Class not found")

    # Perform bulk check-in
    checkins = await CheckIn.bulk_check_in(
        db_session,
        data.class_id,
        data.enrollment_ids,
        data.check_in_date,
        organization_id=current_user.organization_id,
    )

    return CheckInListResponse(
        items=[CheckInResponse.model_validate(c) for c in checkins],
        total=len(checkins),
    )


@router.get(
    "/class/{class_id}", response_model=CheckInListResponse
)
async def get_class_check_ins(
    class_id: str,
    check_in_date: date = None,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckInListResponse:
    """Get all check-ins for a class, optionally filtered by date. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view check-ins")

    # Verify class exists
    class_ = await Class.get_by_id(db_session, class_id)
    if not class_:
        raise NotFoundException(message="Class not found")

    # Get check-ins
    checkins = await CheckIn.get_by_class(db_session, class_id, check_in_date)

    return CheckInListResponse(
        items=[CheckInResponse.model_validate(c) for c in checkins],
        total=len(checkins),
    )


@router.get(
    "/class/{class_id}/status",
    response_model=CheckInStatusListResponse,
)
async def get_check_in_status(
    class_id: str,
    check_in_date: date,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckInStatusListResponse:
    """Get check-in status for all enrolled students in a class on a specific date. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view check-in status")

    # Verify class exists
    class_ = await Class.get_by_id(db_session, class_id)
    if not class_:
        raise NotFoundException(message="Class not found")

    # Get all enrollments for this class
    from sqlalchemy import select

    stmt = select(Enrollment).where(
        Enrollment.class_id == class_id,
        Enrollment.status == "active",
    )
    result = await db_session.execute(stmt)
    enrollments = result.scalars().all()

    enrollment_ids = [e.id for e in enrollments]

    # Get check-in status
    status_map = await CheckIn.get_check_in_status(
        db_session, class_id, check_in_date, enrollment_ids
    )

    # Get check-in details for checked-in students
    checkins = await CheckIn.get_by_class(db_session, class_id, check_in_date)
    checkin_map = {c.enrollment_id: c for c in checkins}

    # Build response
    statuses = [
        CheckInStatusResponse(
            enrollment_id=enrollment_id,
            is_checked_in=status_map[enrollment_id],
            checked_in_at=checkin_map[enrollment_id].checked_in_at
            if enrollment_id in checkin_map
            else None,
        )
        for enrollment_id in enrollment_ids
    ]

    return CheckInStatusListResponse(
        class_id=class_id, check_in_date=check_in_date, statuses=statuses
    )


@router.post("/text-class", response_model=TextClassResponse)
async def text_class(
    data: TextClassRequest,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TextClassResponse:
    """Send SMS to all parents in a class. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can send class messages")

    # Verify class exists
    class_ = await Class.get_by_id(db_session, data.class_id)
    if not class_:
        raise NotFoundException(message="Class not found")

    # Get all active enrollments for this class
    from sqlalchemy import select

    stmt = select(Enrollment).where(
        Enrollment.class_id == data.class_id,
        Enrollment.status == "active",
    )
    result = await db_session.execute(stmt)
    enrollments = result.scalars().all()

    if not enrollments:
        raise NotFoundException(message="No active enrollments found for this class")

    # Extract parent phone numbers
    phone_numbers = []
    for enrollment in enrollments:
        # Load the child and user relationships
        await db_session.refresh(enrollment, ["child"])
        await db_session.refresh(enrollment.child, ["user"])

        parent = enrollment.child.user
        if parent.phone_number:
            phone_numbers.append(parent.phone_number)

    if not phone_numbers:
        return TextClassResponse(
            sent_count=0,
            failed_count=0,
            total=0,
            message="No parent phone numbers available"
        )

    # Send SMS via SMSService
    sms_service = get_sms_service()

    # Format message with class context
    coach_name = f"{current_user.first_name} {current_user.last_name}"
    result = sms_service.send_class_announcement(
        class_name=class_.name,
        coach_name=coach_name,
        phone_numbers=phone_numbers,
        message=data.message,
    )

    logger.info(
        f"Class message sent by {current_user.id} to class {data.class_id}: "
        f"{result['sent_count']}/{result['total']} successful"
    )

    return TextClassResponse(
        sent_count=result["sent_count"],
        failed_count=result["failed_count"],
        total=result["total"],
        message=f"Message sent to {result['sent_count']} out of {result['total']} parents"
    )
