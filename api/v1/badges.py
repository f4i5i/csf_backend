"""Badges API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.attendance import Attendance
from app.models.badge import Badge, StudentBadge
from app.models.enrollment import Enrollment
from app.models.user import Role, User
from app.schemas.badge import (
    BadgeAward,
    BadgeListResponse,
    BadgeProgressResponse,
    BadgeResponse,
    StudentBadgeListResponse,
    StudentBadgeResponse,
    StudentBadgeStatusResponse,
)
from core.db import get_db
from core.exceptions.base import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/badges", tags=["Badges"])


@router.get("/", response_model=BadgeListResponse)
async def list_badges(db_session: AsyncSession = Depends(get_db)) -> BadgeListResponse:
    """List all available badges (public)."""
    badges = await Badge.get_all_active(db_session)
    return BadgeListResponse(items=[BadgeResponse.model_validate(b) for b in badges])


@router.get("/enrollment/{enrollment_id}", response_model=StudentBadgeListResponse)
async def get_student_badges(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentBadgeListResponse:
    """Get badges for an enrollment with locked/unlocked status."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if (
        enrollment.child.user_id != current_user.id
        and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    # Get all badges
    all_badges = await Badge.get_all_active(db_session)

    # Get student's earned badges
    earned = await StudentBadge.get_by_enrollment(db_session, enrollment_id)
    earned_badge_ids = {sb.badge_id for sb in earned}

    # Build response with locked/unlocked status
    items = []
    for badge in all_badges:
        is_unlocked = badge.id in earned_badge_ids
        student_badge = next((sb for sb in earned if sb.badge_id == badge.id), None)

        items.append(
            StudentBadgeStatusResponse(
                badge=BadgeResponse.model_validate(badge),
                is_unlocked=is_unlocked,
                awarded_at=student_badge.awarded_at if student_badge else None,
                progress=student_badge.progress if student_badge else None,
                progress_max=student_badge.progress_max if student_badge else None,
            )
        )

    return StudentBadgeListResponse(enrollment_id=enrollment_id, badges=items)


@router.post(
    "/award", response_model=StudentBadgeResponse, status_code=status.HTTP_201_CREATED
)
async def award_badge(
    data: BadgeAward,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentBadgeResponse:
    """Manually award a badge to student. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can award badges")

    # Check enrollment exists
    enrollment = await Enrollment.get_by_id(db_session, data.enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check badge exists
    badge = await Badge.get_by_id(db_session, data.badge_id)
    if not badge:
        raise NotFoundException(message="Badge not found")

    # Check not already awarded
    from sqlalchemy import select

    stmt = select(StudentBadge).where(
        StudentBadge.enrollment_id == data.enrollment_id,
        StudentBadge.badge_id == data.badge_id,
    )
    result = await db_session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise ValidationException(message="Badge already awarded")

    # Award badge
    student_badge = StudentBadge(
        enrollment_id=data.enrollment_id,
        badge_id=data.badge_id,
        awarded_by=current_user.id,
    )
    db_session.add(student_badge)
    await db_session.commit()
    await db_session.refresh(student_badge)

    return StudentBadgeResponse.model_validate(student_badge)


@router.get("/enrollment/{enrollment_id}/progress", response_model=BadgeProgressResponse)
async def get_badge_progress(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BadgeProgressResponse:
    """Get progress towards unlocking badges."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if (
        enrollment.child.user_id != current_user.id
        and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    # Calculate progress for attendance-based badges
    streak = await Attendance.get_streak(db_session, enrollment_id)

    progress_items = [
        {
            "criteria": "perfect_attendance_5",
            "current": min(streak, 5),
            "required": 5,
        },
        {
            "criteria": "perfect_attendance_10",
            "current": min(streak, 10),
            "required": 10,
        },
        {
            "criteria": "perfect_attendance_20",
            "current": min(streak, 20),
            "required": 20,
        },
    ]

    return BadgeProgressResponse(enrollment_id=enrollment_id, progress=progress_items)
