"""Tests for order and pricing functionality."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient


class TestOrderCalculation:
    """Tests for order price calculation."""

    async def test_calculate_single_item_order(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, test_child: dict
    ):
        """Test calculating order with single item."""
        response = await client.post(
            "/api/v1/orders/calculate",
            json={
                "items": [
                    {"child_id": test_child["id"], "class_id": test_class["id"]}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subtotal"] == str(test_class["price"])
        assert data["total"] == str(test_class["price"])
        assert data["sibling_discount_total"] == "0.00"

    async def test_calculate_sibling_discount(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, db_session, test_user
    ):
        """Test sibling discount calculation for multiple children."""
        from app.models.child import Child, JerseySize

        # Create two children
        child1 = await Child.create_child(
            db_session,
            user_id=auth_headers["user_id"],
            first_name="Child1",
            last_name="Test",
            date_of_birth=date.today() - timedelta(days=365 * 8),
            jersey_size=JerseySize.M,
            organization_id=test_user.organization_id,
        )
        child2 = await Child.create_child(
            db_session,
            user_id=auth_headers["user_id"],
            first_name="Child2",
            last_name="Test",
            date_of_birth=date.today() - timedelta(days=365 * 6),
            jersey_size=JerseySize.S,
            organization_id=test_user.organization_id,
        )

        response = await client.post(
            "/api/v1/orders/calculate",
            json={
                "items": [
                    {"child_id": child1.id, "class_id": test_class["id"]},
                    {"child_id": child2.id, "class_id": test_class["id"]},
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Second child should get 25% sibling discount
        price = Decimal(test_class["price"])
        expected_sibling_discount = (price * Decimal("0.25")).quantize(Decimal("0.01"))
        assert Decimal(data["sibling_discount_total"]) == expected_sibling_discount

    async def test_calculate_empty_order(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test calculating empty order."""
        response = await client.post(
            "/api/v1/orders/calculate",
            json={"items": []},
            headers=auth_headers,
        )
        # Should fail validation - min 1 item required
        assert response.status_code == 422


class TestOrderCRUD:
    """Tests for order CRUD operations."""

    async def test_create_order(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, test_child: dict
    ):
        """Test creating a new order."""
        response = await client.post(
            "/api/v1/orders/",
            json={
                "items": [
                    {"child_id": test_child["id"], "class_id": test_class["id"]}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert data["user_id"] == auth_headers["user_id"]
        assert len(data["line_items"]) == 1

    async def test_list_my_orders(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, test_child: dict
    ):
        """Test listing user's orders."""
        # Create an order first
        await client.post(
            "/api/v1/orders/",
            json={
                "items": [
                    {"child_id": test_child["id"], "class_id": test_class["id"]}
                ]
            },
            headers=auth_headers,
        )

        response = await client.get("/api/v1/orders/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_order(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, test_child: dict
    ):
        """Test getting order by ID."""
        # Create an order first
        create_response = await client.post(
            "/api/v1/orders/",
            json={
                "items": [
                    {"child_id": test_child["id"], "class_id": test_class["id"]}
                ]
            },
            headers=auth_headers,
        )
        order_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == order_id

    async def test_cancel_draft_order(
        self, client: AsyncClient, auth_headers: dict, test_class: dict, test_child: dict
    ):
        """Test cancelling a draft order."""
        # Create an order
        create_response = await client.post(
            "/api/v1/orders/",
            json={
                "items": [
                    {"child_id": test_child["id"], "class_id": test_class["id"]}
                ]
            },
            headers=auth_headers,
        )
        order_id = create_response.json()["id"]

        # Cancel it
        response = await client.post(
            f"/api/v1/orders/{order_id}/cancel", headers=auth_headers
        )
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()


class TestPricingService:
    """Tests for pricing service calculations."""

    async def test_installment_schedule(self, db_session):
        """Test installment schedule generation (max 2 payments)."""
        from app.services.pricing_service import PricingService

        schedule = PricingService.calculate_installment_schedule(
            total=Decimal("300.00"),
            num_installments=2,  # Max 2 installments
            start_date=date.today(),
            frequency="monthly",
        )

        assert len(schedule) == 2
        assert schedule[0].installment_number == 1
        assert schedule[0].amount == Decimal("150.00")

        # Verify total equals original amount
        total = sum(item.amount for item in schedule)
        assert total == Decimal("300.00")

    async def test_cancellation_refund_within_15_days(self, db_session):
        """Test refund calculation within 15-day window."""
        from app.services.pricing_service import PricingService

        enrolled_at = date.today() - timedelta(days=5)
        refund, policy = PricingService.calculate_cancellation_refund(
            enrollment_amount=Decimal("200.00"),
            enrolled_at=enrolled_at,
        )

        # Within 15 days: full refund with no processing fee
        assert refund == Decimal("200.00")
        assert "15 days" in policy.lower()

    async def test_cancellation_refund_after_15_days(self, db_session):
        """Test refund calculation after 15-day window."""
        from app.services.pricing_service import PricingService

        enrolled_at = date.today() - timedelta(days=20)
        refund, policy = PricingService.calculate_cancellation_refund(
            enrollment_amount=Decimal("200.00"),
            enrolled_at=enrolled_at,
        )

        # After 15 days: no refund
        assert refund == Decimal("0.00")
        assert "no refund" in policy.lower()
