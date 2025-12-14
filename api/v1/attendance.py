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
    AttendanceStatsResponse,
    AttendanceStreakResponse,
    ClassInstanceAttendanceResponse,
    EnrollmentAttendanceStats,
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


@router.get("/stats/{child_id}", response_model=AttendanceStatsResponse)
async def get_child_attendance_stats(
    child_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceStatsResponse:
    """Get aggregated attendance statistics for a child across all enrollments."""
    from sqlalchemy import select, func, and_
    from sqlalchemy.orm import selectinload
    from app.models.child import Child
    from app.models.enrollment import EnrollmentStatus
    from app.models.attendance import AttendanceStatus

    # Verify child exists
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        raise NotFoundException(message="Child not found")

    # Permission check
    if (
        child.user_id != current_user.id
        and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    # Get all enrollments for child (active + completed)
    stmt = (
        select(Enrollment)
        .where(
            Enrollment.child_id == child_id,
            Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED])
        )
        .options(selectinload(Enrollment.class_))
    )
    result = await db_session.execute(stmt)
    enrollments = result.scalars().all()

    if not enrollments:
        # No enrollments - return empty stats
        return AttendanceStatsResponse(
            child_id=child_id,
            total_sessions_attended=0,
            total_sessions_missed=0,
            total_sessions_excused=0,
            overall_attendance_rate=0.0,
            longest_streak=0,
            total_sessions=0,
            by_enrollment=[],
        )

    # Aggregate stats across all enrollments
    total_attended = 0
    total_missed = 0
    total_excused = 0
    longest_streak = 0
    by_enrollment_list = []

    for enrollment in enrollments:
        # Count attendance by status for this enrollment
        count_stmt = (
            select(
                Attendance.status,
                func.count(Attendance.id)
            )
            .where(Attendance.enrollment_id == enrollment.id)
            .group_by(Attendance.status)
        )
        count_result = await db_session.execute(count_stmt)
        status_counts = dict(count_result.all())

        sessions_attended = status_counts.get(AttendanceStatus.PRESENT, 0)
        sessions_missed = status_counts.get(AttendanceStatus.ABSENT, 0)
        sessions_excused = status_counts.get(AttendanceStatus.EXCUSED, 0)
        total_sessions_for_enrollment = sessions_attended + sessions_missed + sessions_excused

        # Calculate attendance rate for this enrollment
        if total_sessions_for_enrollment > 0:
            attendance_rate = (sessions_attended / total_sessions_for_enrollment) * 100
        else:
            attendance_rate = 0.0

        # Get streak - only for active enrollments, 0 for completed
        if enrollment.status == EnrollmentStatus.ACTIVE:
            current_streak = await Attendance.get_streak(db_session, enrollment.id)
        else:
            current_streak = 0

        # Update longest streak
        if current_streak > longest_streak:
            longest_streak = current_streak

        # Add to aggregates
        total_attended += sessions_attended
        total_missed += sessions_missed
        total_excused += sessions_excused

        # Build enrollment stats
        by_enrollment_list.append(
            EnrollmentAttendanceStats(
                enrollment_id=enrollment.id,
                class_name=enrollment.class_.name,
                sessions_attended=sessions_attended,
                sessions_missed=sessions_missed,
                sessions_excused=sessions_excused,
                total_sessions=total_sessions_for_enrollment,
                attendance_rate=round(attendance_rate, 2),
                current_streak=current_streak,
                status=enrollment.status.value,
            )
        )

    # Calculate overall attendance rate
    total_sessions_overall = total_attended + total_missed + total_excused
    if total_sessions_overall > 0:
        overall_attendance_rate = (total_attended / total_sessions_overall) * 100
    else:
        overall_attendance_rate = 0.0

    return AttendanceStatsResponse(
        child_id=child_id,
        total_sessions_attended=total_attended,
        total_sessions_missed=total_missed,
        total_sessions_excused=total_excused,
        overall_attendance_rate=round(overall_attendance_rate, 2),
        longest_streak=longest_streak,
        total_sessions=total_sessions_overall,
        by_enrollment=by_enrollment_list,
    )
