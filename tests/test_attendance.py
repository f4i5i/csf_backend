"""Tests for attendance API endpoints."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance, AttendanceStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User

pytestmark = pytest.mark.asyncio


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


class TestGetChildAttendanceStats:
    """Tests for GET /api/v1/attendance/stats/{child_id} endpoint."""

    async def test_get_attendance_stats_no_enrollments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_child: dict,
    ):
        """Test getting stats when child has no enrollments."""
        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["child_id"] == test_child["id"]
        assert data["total_sessions_attended"] == 0
        assert data["total_sessions_missed"] == 0
        assert data["total_sessions_excused"] == 0
        assert data["overall_attendance_rate"] == 0.0
        assert data["longest_streak"] == 0
        assert data["total_sessions"] == 0
        assert data["by_enrollment"] == []

    async def test_get_attendance_stats_with_attendance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_enrollment: Enrollment,
        test_user: User,
    ):
        """Test getting stats with attendance records."""
        # Create attendance records
        attendances = [
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date.today(),
                status=AttendanceStatus.PRESENT,
                marked_by=test_user.id,
            ),
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 2),
                status=AttendanceStatus.PRESENT,
                marked_by=test_user.id,
            ),
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 3),
                status=AttendanceStatus.ABSENT,
                marked_by=test_user.id,
            ),
        ]
        for att in attendances:
            db_session.add(att)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions_attended"] == 2
        assert data["total_sessions_missed"] == 1
        assert data["total_sessions"] == 3
        assert data["overall_attendance_rate"] == 66.67
        assert len(data["by_enrollment"]) == 1

    async def test_get_attendance_stats_multiple_enrollments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_user: User,
        test_class: dict,
    ):
        """Test getting stats across multiple enrollments."""
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
            status=EnrollmentStatus.COMPLETED,
        )
        db_session.add_all([enrollment1, enrollment2])
        await db_session.commit()
        await db_session.refresh(enrollment1)
        await db_session.refresh(enrollment2)

        # Add attendance to first enrollment
        att1 = Attendance(
            enrollment_id=enrollment1.id,
            class_id=test_class["id"],
            date=date.today(),
            status=AttendanceStatus.PRESENT,
            marked_by=test_user.id,
        )
        # Add attendance to second enrollment
        att2 = Attendance(
            enrollment_id=enrollment2.id,
            class_id=test_class["id"],
            date=date.today(),
            status=AttendanceStatus.PRESENT,
            marked_by=test_user.id,
        )
        db_session.add_all([att1, att2])
        await db_session.commit()

        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions_attended"] == 2
        assert len(data["by_enrollment"]) == 2

    async def test_get_attendance_stats_completed_enrollment_no_streak(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_user: User,
        test_class: dict,
    ):
        """Test that completed enrollments show 0 streak."""
        enrollment = Enrollment(
            child_id=test_child["id"],
            class_id=test_class["id"],
            user_id=test_user.id,
            status=EnrollmentStatus.COMPLETED,
        )
        db_session.add(enrollment)
        await db_session.commit()
        await db_session.refresh(enrollment)

        # Add attendance
        att = Attendance(
            enrollment_id=enrollment.id,
            class_id=test_class["id"],
            date=date.today(),
            status=AttendanceStatus.PRESENT,
            marked_by=test_user.id,
        )
        db_session.add(att)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["by_enrollment"][0]["current_streak"] == 0
        assert data["by_enrollment"][0]["status"] == "completed"

    async def test_get_attendance_stats_child_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting stats for non-existent child."""
        response = await client.get(
            "/api/v1/attendance/stats/nonexistent-id",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_get_attendance_stats_unauthorized(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        create_test_user,
        test_class: dict,
    ):
        """Test getting stats for another user's child."""
        from datetime import date, timedelta
        from app.models.child import Child, JerseySize
        from app.models.user import User

        # Create another user and their child
        other_user_data = await create_test_user("other@example.com", "Other User")
        other_user = await db_session.get(User, other_user_data["id"])

        other_child = await Child.create_child(
            db_session,
            user_id=other_user.id,
            first_name="OtherChild",
            last_name="User",
            date_of_birth=date.today() - timedelta(days=365 * 8),
            jersey_size=JerseySize.M,
        )

        response = await client.get(
            f"/api/v1/attendance/stats/{other_child.id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    async def test_get_attendance_stats_with_excused(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_enrollment: Enrollment,
        test_user: User,
    ):
        """Test stats with excused absences."""
        attendances = [
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 1),
                status=AttendanceStatus.PRESENT,
                marked_by=test_user.id,
            ),
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 2),
                status=AttendanceStatus.EXCUSED,
                marked_by=test_user.id,
            ),
        ]
        for att in attendances:
            db_session.add(att)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions_attended"] == 1
        assert data["total_sessions_excused"] == 1
        assert data["total_sessions"] == 2

    async def test_get_attendance_stats_per_enrollment_breakdown(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_child: dict,
        test_enrollment: Enrollment,
        test_user: User,
    ):
        """Test per-enrollment breakdown in response."""
        # Add attendance
        attendances = [
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 1),
                status=AttendanceStatus.PRESENT,
                marked_by=test_user.id,
            ),
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 2),
                status=AttendanceStatus.PRESENT,
                marked_by=test_user.id,
            ),
            Attendance(
                enrollment_id=test_enrollment.id,
                class_id=test_enrollment.class_id,
                date=date(2025, 1, 3),
                status=AttendanceStatus.ABSENT,
                marked_by=test_user.id,
            ),
        ]
        for att in attendances:
            db_session.add(att)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/attendance/stats/{test_child['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        enrollment_stats = data["by_enrollment"][0]
        assert enrollment_stats["enrollment_id"] == test_enrollment.id
        assert enrollment_stats["sessions_attended"] == 2
        assert enrollment_stats["sessions_missed"] == 1
        assert enrollment_stats["total_sessions"] == 3
        assert enrollment_stats["attendance_rate"] == 66.67
        assert enrollment_stats["status"] == "active"
