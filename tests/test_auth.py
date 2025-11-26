import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuthRegister:
    """Tests for user registration endpoint."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewPass123",
                "confirm_password": "NewPass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "password": "NewPass123",
                "confirm_password": "NewPass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["message"]

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weak",  # Too short, no uppercase, no digit
                "confirm_password": "weak",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 422  # Validation error

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "NewPass123",
                "confirm_password": "NewPass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 422

    async def test_register_passwords_mismatch(self, client: AsyncClient):
        """Test registration with mismatched passwords."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewPass123",
                "confirm_password": "DifferentPass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 422

    async def test_register_normalizes_email(self, client: AsyncClient):
        """Emails should be stored in lowercase form."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "CaseUser@Example.com",
                "password": "NewPass123",
                "confirm_password": "NewPass123",
                "first_name": "Case",
                "last_name": "User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "caseuser@example.com"


class TestAuthLogin:
    """Tests for user login endpoint."""

    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPass123",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123",
            },
        )
        assert response.status_code == 401

    async def test_login_case_insensitive_email(
        self, client: AsyncClient, test_user
    ):
        """Login should succeed regardless of email casing."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "TEST@EXAMPLE.COM",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 200


class TestAuthRefresh:
    """Tests for token refresh endpoint."""

    async def test_refresh_success(self, client: AsyncClient, test_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123",
            },
        )
        tokens = login_response.json()

        # Then refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
