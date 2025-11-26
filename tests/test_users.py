import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestUserProfile:
    """Tests for user profile endpoints."""

    async def test_get_profile_success(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """Test getting current user's profile."""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name

    async def test_get_profile_unauthenticated(self, client: AsyncClient):
        """Test getting profile without authentication."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_update_profile_success(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """Test updating user's profile."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "first_name": "Updated",
                "last_name": "Name",
                "phone": "555-1234",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["phone"] == "555-1234"
        # Email should remain unchanged
        assert data["email"] == test_user.email

    async def test_update_profile_partial(
        self, client: AsyncClient, test_user, auth_headers
    ):
        """Test partial profile update."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"first_name": "OnlyFirst"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "OnlyFirst"
        assert data["last_name"] == test_user.last_name  # Unchanged
