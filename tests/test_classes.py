from datetime import date, time
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class, ClassType
from app.models.program import Area, Program, School

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_program(db_session: AsyncSession) -> Program:
    """Create a test program."""
    program = Program(name="Basketball", description="Youth basketball program")
    db_session.add(program)
    await db_session.commit()
    await db_session.refresh(program)
    return program


@pytest.fixture
async def test_area(db_session: AsyncSession) -> Area:
    """Create a test area."""
    area = Area(name="North Region", description="Northern area")
    db_session.add(area)
    await db_session.commit()
    await db_session.refresh(area)
    return area


@pytest.fixture
async def test_school(db_session: AsyncSession, test_area: Area) -> School:
    """Create a test school."""
    school = School(
        name="Lincoln Elementary",
        address="123 Main St",
        city="Springfield",
        state="IL",
        zip_code="62701",
        area_id=test_area.id,
    )
    db_session.add(school)
    await db_session.commit()
    await db_session.refresh(school)
    return school


@pytest.fixture
async def test_class(
    db_session: AsyncSession, test_program: Program, test_school: School
) -> Class:
    """Create a test class."""
    class_obj = Class(
        name="Beginner Basketball",
        description="Basketball for beginners",
        program_id=test_program.id,
        school_id=test_school.id,
        class_type=ClassType.SHORT_TERM,
        weekdays=["monday", "wednesday"],
        start_time=time(16, 0),
        end_time=time(17, 0),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        capacity=20,
        price=Decimal("150.00"),
        min_age=6,
        max_age=10,
    )
    db_session.add(class_obj)
    await db_session.commit()
    await db_session.refresh(class_obj)
    return class_obj


class TestListClasses:
    """Tests for listing classes endpoint."""

    async def test_list_classes_empty(self, client: AsyncClient):
        """Test listing classes when none exist."""
        response = await client.get("/api/v1/classes/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_classes_success(self, client: AsyncClient, test_class):
        """Test listing classes."""
        response = await client.get("/api/v1/classes/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Beginner Basketball"


class TestGetClass:
    """Tests for getting class details endpoint."""

    async def test_get_class_success(self, client: AsyncClient, test_class):
        """Test getting class details."""
        response = await client.get(f"/api/v1/classes/{test_class.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Beginner Basketball"
        assert data["capacity"] == 20
        assert data["min_age"] == 6
        assert data["max_age"] == 10

    async def test_get_class_not_found(self, client: AsyncClient):
        """Test getting non-existent class."""
        response = await client.get("/api/v1/classes/nonexistent-id")
        assert response.status_code == 404


class TestCreateClass:
    """Tests for creating class endpoint."""

    async def test_create_class_admin_success(
        self,
        client: AsyncClient,
        admin_auth_headers,
        test_program,
        test_school,
    ):
        """Test creating class as admin."""
        response = await client.post(
            "/api/v1/classes/",
            headers=admin_auth_headers,
            json={
                "name": "Advanced Basketball",
                "description": "For advanced players",
                "program_id": test_program.id,
                "school_id": test_school.id,
                "class_type": "short_term",
                "weekdays": ["tuesday", "thursday"],
                "start_time": "17:00:00",
                "end_time": "18:30:00",
                "start_date": "2025-01-01",
                "end_date": "2025-03-31",
                "capacity": 15,
                "price": 200.00,
                "min_age": 10,
                "max_age": 14,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Advanced Basketball"
        assert data["capacity"] == 15

    async def test_create_class_unauthorized(
        self,
        client: AsyncClient,
        auth_headers,  # Regular user, not admin
        test_program,
        test_school,
    ):
        """Test creating class as non-admin."""
        response = await client.post(
            "/api/v1/classes/",
            headers=auth_headers,
            json={
                "name": "Unauthorized Class",
                "program_id": test_program.id,
                "school_id": test_school.id,
                "class_type": "short_term",
                "weekdays": ["monday"],
                "start_time": "16:00:00",
                "end_time": "17:00:00",
                "start_date": "2025-01-01",
                "end_date": "2025-03-31",
                "capacity": 10,
                "price": 100.00,
                "min_age": 5,
                "max_age": 8,
            },
        )
        assert response.status_code == 403


class TestDeleteClass:
    """Tests for deleting class endpoint."""

    async def test_delete_class_admin_success(
        self, client: AsyncClient, admin_auth_headers, test_class
    ):
        """Test soft deleting class as admin."""
        response = await client.delete(
            f"/api/v1/classes/{test_class.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        # Verify class is soft deleted (not visible in list)
        list_response = await client.get("/api/v1/classes/")
        assert list_response.json()["total"] == 0


class TestUpdateClass:
    """Tests for updating class validation rules."""

    async def test_update_class_invalid_end_date(
        self,
        client: AsyncClient,
        admin_auth_headers,
        test_class: Class,
    ):
        response = await client.put(
            f"/api/v1/classes/{test_class.id}",
            headers=admin_auth_headers,
            json={"end_date": "2024-01-01"},
        )
        assert response.status_code == 400

    async def test_update_class_invalid_end_time(
        self,
        client: AsyncClient,
        admin_auth_headers,
        test_class: Class,
    ):
        response = await client.put(
            f"/api/v1/classes/{test_class.id}",
            headers=admin_auth_headers,
            json={"end_time": "15:00:00"},
        )
        assert response.status_code == 400

    async def test_update_class_invalid_age_range(
        self,
        client: AsyncClient,
        admin_auth_headers,
        test_class: Class,
    ):
        response = await client.put(
            f"/api/v1/classes/{test_class.id}",
            headers=admin_auth_headers,
            json={"max_age": 5},
        )
        assert response.status_code == 400


class TestEnrollmentCounters:
    """Tests for enrollment counter helpers."""

    async def test_increment_enrollment_stops_at_capacity(
        self,
        db_session: AsyncSession,
        test_class: Class,
    ):
        # Store capacity value before async operations
        capacity = test_class.capacity

        for _ in range(capacity):
            assert await test_class.increment_enrollment(db_session)

        assert test_class.current_enrollment == capacity
        assert not await test_class.increment_enrollment(db_session)

        await test_class.decrement_enrollment(db_session)
        assert test_class.current_enrollment == capacity - 1

        # Decrement down to zero and ensure no negative values
        while test_class.current_enrollment > 0:
            await test_class.decrement_enrollment(db_session)

        assert test_class.current_enrollment == 0
