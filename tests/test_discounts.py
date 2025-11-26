"""Tests for discount code and scholarship functionality."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient


class TestDiscountCodeValidation:
    """Tests for discount code validation."""

    async def test_validate_valid_code(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Test validating a valid discount code."""
        # Create a discount code first (admin)
        create_response = await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "SUMMER25",
                "discount_type": "percentage",
                "discount_value": "25.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=admin_auth_headers,
        )
        assert create_response.status_code == 200

        # Validate it (regular user)
        response = await client.post(
            "/api/v1/discounts/validate",
            json={
                "code": "SUMMER25",
                "order_amount": "100.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert Decimal(data["discount_amount"]) == Decimal("25.00")

    async def test_validate_invalid_code(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test validating a nonexistent discount code."""
        response = await client.post(
            "/api/v1/discounts/validate",
            json={
                "code": "INVALID123",
                "order_amount": "100.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "invalid" in data["error_message"].lower()


class TestDiscountCodeAdmin:
    """Tests for discount code admin operations."""

    async def test_create_discount_code(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """Test creating a discount code."""
        response = await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "NEWCODE10",
                "description": "10% off for new customers",
                "discount_type": "percentage",
                "discount_value": "10.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
                "max_uses": 100,
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "NEWCODE10"
        assert data["discount_type"] == "percentage"
        assert data["is_active"] is True

    async def test_create_discount_code_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that non-admin cannot create discount codes."""
        response = await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "TESTCODE",
                "discount_type": "percentage",
                "discount_value": "10.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_list_discount_codes(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """Test listing discount codes."""
        # Create a code first
        await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "LISTTEST",
                "discount_type": "fixed_amount",
                "discount_value": "20.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=admin_auth_headers,
        )

        response = await client.get(
            "/api/v1/discounts/codes",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_update_discount_code(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """Test updating a discount code."""
        # Create a code
        create_response = await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "UPDATEME",
                "discount_type": "percentage",
                "discount_value": "15.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=admin_auth_headers,
        )
        code_id = create_response.json()["id"]

        # Update it
        response = await client.put(
            f"/api/v1/discounts/codes/{code_id}",
            json={"description": "Updated description", "is_active": False},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["is_active"] is False

    async def test_delete_discount_code(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """Test deactivating a discount code."""
        # Create a code
        create_response = await client.post(
            "/api/v1/discounts/codes",
            json={
                "code": "DELETEME",
                "discount_type": "percentage",
                "discount_value": "5.00",
                "valid_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=admin_auth_headers,
        )
        code_id = create_response.json()["id"]

        # Delete (deactivate) it
        response = await client.delete(
            f"/api/v1/discounts/codes/{code_id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        # Verify it's inactive
        get_response = await client.get(
            f"/api/v1/discounts/codes/{code_id}",
            headers=admin_auth_headers,
        )
        assert get_response.json()["is_active"] is False


class TestScholarships:
    """Tests for scholarship functionality."""

    async def test_create_scholarship(
        self, client: AsyncClient, admin_auth_headers: dict, test_user
    ):
        """Test creating a scholarship."""
        response = await client.post(
            "/api/v1/discounts/scholarships",
            json={
                "user_id": test_user.id,
                "scholarship_type": "Financial Need",
                "discount_percentage": "50.00",
                "notes": "Approved for financial assistance",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scholarship_type"] == "Financial Need"
        assert Decimal(data["discount_percentage"]) == Decimal("50.00")
        assert data["is_active"] is True

    async def test_list_my_scholarships(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict, test_user
    ):
        """Test listing user's own scholarships."""
        # Create a scholarship
        await client.post(
            "/api/v1/discounts/scholarships",
            json={
                "user_id": test_user.id,
                "scholarship_type": "Merit",
                "discount_percentage": "25.00",
            },
            headers=admin_auth_headers,
        )

        # List my scholarships
        response = await client.get(
            "/api/v1/discounts/my-scholarships",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_deactivate_scholarship(
        self, client: AsyncClient, admin_auth_headers: dict, test_user
    ):
        """Test deactivating a scholarship."""
        # Create a scholarship
        create_response = await client.post(
            "/api/v1/discounts/scholarships",
            json={
                "user_id": test_user.id,
                "scholarship_type": "Temporary",
                "discount_percentage": "30.00",
            },
            headers=admin_auth_headers,
        )
        scholarship_id = create_response.json()["id"]

        # Deactivate it
        response = await client.delete(
            f"/api/v1/discounts/scholarships/{scholarship_id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
