"""Attendance API endpoints for tracking student attendance."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.user import Role, User
from app.schemas.attendance import (
    AttendanceListResponse,
    AttendanceMarkBulk,
    AttendanceResponse,
    AttendanceStreakResponse,
    ClassInstanceAttendanceResponse,
)
from core.db import get_db
from core.exceptions.base import ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/mark", status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    data: AttendanceMarkBulk,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark attendance for multiple students. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can mark attendance")

    logger.info(
        f"Marking attendance for {len(data.records)} students "
        f"in class {data.class_id}"
    )

    await Attendance.mark_bulk(
        db_session,
        class_id=data.class_id,
        attendance_data=[item.model_dump() for item in data.records],
        marked_by=current_user.id,
    )

    return {"message": "Attendance marked successfully"}


@router.get(
    "/enrollment/{enrollment_id}/history", response_model=AttendanceListResponse
)
async def get_attendance_history(
    enrollment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceListResponse:
    """Get attendance history for enrollment."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if (
        enrollment.child.user_id != current_user.id
        and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    attendances = await Attendance.get_by_enrollment(db_session, enrollment_id, skip, limit)
    total = await Attendance.count_by_enrollment(db_session, enrollment_id)

    return AttendanceListResponse(
        items=[AttendanceResponse.model_validate(a) for a in attendances],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/enrollment/{enrollment_id}/streak", response_model=AttendanceStreakResponse)
async def get_attendance_streak(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceStreakResponse:
    """Get current attendance streak."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if (
        enrollment.child.user_id != current_user.id
        and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    streak = await Attendance.get_streak(db_session, enrollment_id)
    return AttendanceStreakResponse(enrollment_id=enrollment_id, streak=streak)


@router.get(
    "/class/{class_id}",
    response_model=ClassInstanceAttendanceResponse,
)
async def get_class_attendance(
    class_id: str,
    date: str = Query(None),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClassInstanceAttendanceResponse:
    """Get attendance for a class, optionally filtered by date. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view class attendance")

    from datetime import date as date_type
    date_filter = date_type.fromisoformat(date) if date else None

    attendances = await Attendance.get_by_class(db_session, class_id, date_filter)
    return ClassInstanceAttendanceResponse(
        class_instance_id=class_id,  # Keeping field name for now, can update schema later
        records=[AttendanceResponse.model_validate(a) for a in attendances],
    )
