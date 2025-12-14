"""Tests for events API endpoints."""

from datetime import date, time
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventType
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_event(
    db_session: AsyncSession, test_class: dict, test_user
) -> Event:
    """Create a test event."""
    event = Event(
        class_id=test_class["id"],
        event_type=EventType.TRAINING,
        event_date=date.today(),
        title="Test Soccer Session",
        description="Regular practice session",
        created_by=test_user.id,
        is_active=True,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


class TestListAllEvents:
    """Tests for GET /api/v1/events/ endpoint."""

    async def test_list_events_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing events when none exist."""
        response = await client.get(
            "/api/v1/events/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_events_success(
        self, client: AsyncClient, auth_headers: dict, test_event: Event
    ):
        """Test listing all events."""
        response = await client.get(
            "/api/v1/events/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Test Soccer Session"

    async def test_list_events_filter_by_class(
        self, client: AsyncClient, auth_headers: dict, test_event: Event, test_class: dict
    ):
        """Test filtering events by class_id."""
        response = await client.get(
            f"/api/v1/events/?class_id={test_class['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["class_id"] == test_class["id"]

    async def test_list_events_filter_by_type(
        self, client: AsyncClient, auth_headers: dict, test_event: Event
    ):
        """Test filtering events by event_type."""
        response = await client.get(
            "/api/v1/events/?event_type=training",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == "training"

    async def test_list_events_filter_by_date_range(
        self, client: AsyncClient, auth_headers: dict, test_event: Event
    ):
        """Test filtering events by date range."""
        from datetime import timedelta
        start = (date.today() - timedelta(days=1)).isoformat()
        end = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/v1/events/?start_date={start}&end_date={end}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    async def test_list_events_pagination(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_class: dict, test_user
    ):
        """Test pagination for events."""
        # Create multiple events
        for i in range(5):
            event = Event(
                class_id=test_class["id"],
                event_type=EventType.TRAINING,
                event_date=date.today(),
                title=f"Session {i}",
                created_by=test_user.id,
                is_active=True,
            )
            db_session.add(event)
        await db_session.commit()

        # Test with limit
        response = await client.get(
            "/api/v1/events/?limit=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
