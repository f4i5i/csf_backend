"""Tests for badges API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, BadgeCategory, BadgeCriteria, StudentBadge
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_badge(db_session: AsyncSession) -> Badge:
    """Create a test badge."""
    badge = Badge(
        name="Perfect Attendance 5",
        description="Attended 5 sessions in a row",
        category=BadgeCategory.ATTENDANCE,
        criteria=BadgeCriteria.PERFECT_ATTENDANCE_5,
        icon_url="/badges/attendance_5.png",
        is_active=True,
    )
    db_session.add(badge)
    await db_session.commit()
    await db_session.refresh(badge)
    return badge


@pytest.fixture
async def test_enrollment(
    db_session: AsyncSession, test_user: User, test_child: dict, test_class: dict
) -> Enrollment:
    """Create a test enrollment."""
    enrollment = Enrollment(
        child_id=test_child["id"],
        class_id=test_class["id"],
        user_id=test_user.id,
        status=EnrollmentStatus.ACTIVE,
    )
    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)
    return enrollment


class TestGetChildBadges:
    """Tests for GET /api/v1/badges/child/{child_id} endpoint."""

    async def test_get_child_badges_no_enrollments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_child: dict,
        test_badge: Badge,
    ):
        """Test getting badges when child has no enrollments."""
        response = await client.get(
            f"/api/v1/badges/child/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["child_id"] == test_child["id"]
        assert data["total_unlocked"] == 0
        assert data["total_badges"] == 1
        assert len(data["badges"]) == 1
        assert data["badges"][0]["is_unlocked"] is False

    async def test_get_child_badges_with_earned_badge(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_badge: Badge,
        test_enrollment: Enrollment,
    ):
        """Test getting badges when child has earned a badge."""
        # Award badge to enrollment
        student_badge = StudentBadge(
            enrollment_id=test_enrollment.id,
            badge_id=test_badge.id,
            awarded_by=test_enrollment.user_id,
        )
        db_session.add(student_badge)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/badges/child/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_unlocked"] == 1
        assert data["total_badges"] == 1
        assert data["badges"][0]["is_unlocked"] is True
        assert data["badges"][0]["total_count"] == 1
        assert data["badges"][0]["enrollment_count"] == 1

    async def test_get_child_badges_multiple_enrollments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_badge: Badge,
        test_user: User,
        test_class: dict,
    ):
        """Test getting badges when child has multiple enrollments."""
        # Create two enrollments
        enrollment1 = Enrollment(
            child_id=test_child["id"],
            class_id=test_class["id"],
            user_id=test_user.id,
            status=EnrollmentStatus.ACTIVE,
        )
        enrollment2 = Enrollment(
            child_id=test_child["id"],
            class_id=test_class["id"],
            user_id=test_user.id,
            status=EnrollmentStatus.ACTIVE,
        )
        db_session.add_all([enrollment1, enrollment2])
        await db_session.commit()
        await db_session.refresh(enrollment1)
        await db_session.refresh(enrollment2)

        # Award same badge in both enrollments
        student_badge1 = StudentBadge(
            enrollment_id=enrollment1.id,
            badge_id=test_badge.id,
            awarded_by=test_user.id,
        )
        student_badge2 = StudentBadge(
            enrollment_id=enrollment2.id,
            badge_id=test_badge.id,
            awarded_by=test_user.id,
        )
        db_session.add_all([student_badge1, student_badge2])
        await db_session.commit()

        response = await client.get(
            f"/api/v1/badges/child/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_unlocked"] == 1  # Same badge, but unlocked
        assert data["badges"][0]["total_count"] == 2  # Earned twice
        assert data["badges"][0]["enrollment_count"] == 2  # In 2 enrollments

    async def test_get_child_badges_child_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting badges for non-existent child."""
        response = await client.get(
            "/api/v1/badges/child/nonexistent-id",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_get_child_badges_unauthorized(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        create_test_user,
        test_class: dict,
    ):
        """Test getting badges for another user's child."""
        from datetime import date, timedelta
        from app.models.child import Child, JerseySize

        # Create another user and their child
        other_user_data = await create_test_user("other@example.com", "Other User")
        from app.models.user import User
        other_user = await db_session.get(User, other_user_data["id"])

        other_child = await Child.create_child(
            db_session,
            user_id=other_user.id,
            first_name="OtherChild",
            last_name="User",
            date_of_birth=date.today() - timedelta(days=365 * 8),
            jersey_size=JerseySize.M,
            organization_id=other_user.organization_id,
        )

        response = await client.get(
            f"/api/v1/badges/child/{other_child.id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    async def test_get_child_badges_most_recent_award_date(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_badge: Badge,
        test_user: User,
        test_class: dict,
    ):
        """Test that most recent award date is returned."""
        from datetime import datetime, timedelta

        # Create two enrollments with time gap
        enrollment1 = Enrollment(
            child_id=test_child["id"],
            class_id=test_class["id"],
            user_id=test_user.id,
            status=EnrollmentStatus.ACTIVE,
        )
        enrollment2 = Enrollment(
            child_id=test_child["id"],
            class_id=test_class["id"],
            user_id=test_user.id,
            status=EnrollmentStatus.ACTIVE,
        )
        db_session.add_all([enrollment1, enrollment2])
        await db_session.commit()
        await db_session.refresh(enrollment1)
        await db_session.refresh(enrollment2)

        # Award badge at different times
        older_date = datetime.now() - timedelta(days=30)
        newer_date = datetime.now()

        student_badge1 = StudentBadge(
            enrollment_id=enrollment1.id,
            badge_id=test_badge.id,
            awarded_by=test_user.id,
        )
        # Manually set created_at to older date
        db_session.add(student_badge1)
        await db_session.flush()

        student_badge2 = StudentBadge(
            enrollment_id=enrollment2.id,
            badge_id=test_badge.id,
            awarded_by=test_user.id,
        )
        db_session.add(student_badge2)
        await db_session.commit()
        await db_session.refresh(student_badge2)

        response = await client.get(
            f"/api/v1/badges/child/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return the more recent date
        assert data["badges"][0]["awarded_at"] is not None

    async def test_get_child_badges_mixed_unlocked_locked(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_enrollment: Enrollment,
        test_user: User,
    ):
        """Test badges with mix of unlocked and locked."""
        # Create multiple badges
        badge1 = Badge(
            name="Badge 1",
            description="First badge",
            category=BadgeCategory.ATTENDANCE,
            criteria=BadgeCriteria.PERFECT_ATTENDANCE_5,
            is_active=True,
        )
        badge2 = Badge(
            name="Badge 2",
            description="Second badge",
            category=BadgeCategory.ACHIEVEMENT,
            criteria=BadgeCriteria.FIRST_CLASS,
            is_active=True,
        )
        db_session.add_all([badge1, badge2])
        await db_session.commit()
        await db_session.refresh(badge1)
        await db_session.refresh(badge2)

        # Award only badge1
        student_badge = StudentBadge(
            enrollment_id=test_enrollment.id,
            badge_id=badge1.id,
            awarded_by=test_user.id,
        )
        db_session.add(student_badge)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/badges/child/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_unlocked"] == 1
        assert data["total_badges"] == 2
        unlocked = [b for b in data["badges"] if b["is_unlocked"]]
        locked = [b for b in data["badges"] if not b["is_unlocked"]]
        assert len(unlocked) == 1
        assert len(locked) == 1
