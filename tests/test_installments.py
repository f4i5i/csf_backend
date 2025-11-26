"""Tests for installment plan functionality."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient


class TestInstallmentPreview:
    """Tests for installment schedule preview."""

    async def test_preview_installment_schedule(
        self, client: AsyncClient, auth_headers: dict, test_order: dict
    ):
        """Test previewing installment payment schedule."""
        response = await client.post(
            f"/api/v1/installments/preview?order_id={test_order['id']}"
            "&num_installments=3&frequency=monthly",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify preview structure
        assert data["total_amount"] == test_order["total"]
        assert data["num_installments"] == 3
        assert data["frequency"] == "monthly"
        assert len(data["schedule"]) == 3

        # Verify schedule details
        for i, item in enumerate(data["schedule"], 1):
            assert item["installment_number"] == i
            assert "due_date" in item
            assert Decimal(item["amount"]) > 0

        # Verify total adds up
        total = sum(Decimal(item["amount"]) for item in data["schedule"])
        assert total == Decimal(test_order["total"])

    async def test_preview_with_custom_start_date(
        self, client: AsyncClient, auth_headers: dict, test_order: dict
    ):
        """Test preview with custom start date."""
        start_date = (date.today() + timedelta(days=7)).isoformat()

        response = await client.post(
            f"/api/v1/installments/preview?order_id={test_order['id']}"
            f"&num_installments=4&frequency=weekly&start_date={start_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # First installment should be on start date
        assert data["schedule"][0]["due_date"] == start_date

    async def test_preview_invalid_installment_count(
        self, client: AsyncClient, auth_headers: dict, test_order: dict
    ):
        """Test preview with invalid installment count."""
        # Too few
        response = await client.post(
            f"/api/v1/installments/preview?order_id={test_order['id']}"
            "&num_installments=1&frequency=monthly",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Too many
        response = await client.post(
            f"/api/v1/installments/preview?order_id={test_order['id']}"
            "&num_installments=13&frequency=monthly",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_preview_past_start_date(
        self, client: AsyncClient, auth_headers: dict, test_order: dict
    ):
        """Test preview with start date in the past."""
        past_date = (date.today() - timedelta(days=1)).isoformat()

        response = await client.post(
            f"/api/v1/installments/preview?order_id={test_order['id']}"
            f"&num_installments=3&frequency=monthly&start_date={past_date}",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "past" in response.json()["message"].lower()


class TestInstallmentPlanCRUD:
    """Tests for installment plan CRUD operations."""

    async def test_create_installment_plan(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: dict,
        test_payment_method: dict,
        mock_stripe_service,
    ):
        """Test creating an installment plan."""
        response = await client.post(
            "/api/v1/installments/",
            json={
                "order_id": test_order["id"],
                "num_installments": 3,
                "frequency": "monthly",
                "payment_method_id": test_payment_method["id"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify plan details
        assert data["order_id"] == test_order["id"]
        assert data["user_id"] == auth_headers["user_id"]
        assert data["num_installments"] == 3
        assert data["frequency"] == "monthly"
        assert data["status"] == "active"
        assert data["total_amount"] == test_order["total"]
        assert "stripe_subscription_id" in data

    async def test_create_installment_minimum_amount(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_child: dict,
        test_program,
        test_school,
        test_payment_method: dict,
        mock_stripe_service,
        db_session,
    ):
        """Test creating installment plan with amount below minimum."""
        # Create a low-priced class ($25)
        from datetime import date, time
        from decimal import Decimal
        from app.models.class_ import Class, ClassType

        low_price_class = Class(
            name="Low Price Class",
            description="A low-priced test class",
            program_id=test_program.id,
            school_id=test_school.id,
            class_type=ClassType.SHORT_TERM,
            weekdays=["monday"],
            start_date=date.today(),
            end_date=date.today().replace(year=date.today().year + 1),
            start_time=time(16, 0),
            end_time=time(17, 0),
            capacity=20,
            price=Decimal("25.00"),
            min_age=6,
            max_age=12,
            is_active=True,
        )
        db_session.add(low_price_class)
        await db_session.commit()
        await db_session.refresh(low_price_class)

        # Create a low-value order ($25)
        low_order = await client.post(
            "/api/v1/orders/",
            json={
                "items": [{"child_id": test_child["id"], "class_id": low_price_class.id}]
            },
            headers=auth_headers,
        )
        low_order_data = low_order.json()

        # Try to create 3 installments (would be ~$8.33 each, below $10 minimum)
        response = await client.post(
            "/api/v1/installments/",
            json={
                "order_id": low_order_data["id"],
                "num_installments": 3,
                "frequency": "monthly",
                "payment_method_id": test_payment_method["id"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "minimum" in response.json()["message"].lower()

    async def test_create_installment_for_paid_order(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: dict,
        test_payment_method: dict,
        db_session,
    ):
        """Test cannot create installment plan for already paid order."""
        from app.models.order import Order, OrderStatus

        # Mark order as paid
        order = await Order.get_by_id(db_session, test_order["id"])
        order.status = OrderStatus.PAID
        await db_session.commit()

        response = await client.post(
            "/api/v1/installments/",
            json={
                "order_id": test_order["id"],
                "num_installments": 3,
                "frequency": "monthly",
                "payment_method_id": test_payment_method["id"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "paid" in response.json()["message"].lower()

    async def test_get_my_installment_plans(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test getting user's installment plans."""
        response = await client.get(
            "/api/v1/installments/my",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0
        assert any(plan["id"] == test_installment_plan["id"] for plan in data)

    async def test_get_my_installment_plans_filtered(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test filtering installment plans by status."""
        response = await client.get(
            "/api/v1/installments/my?status=active",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # All returned plans should be active
        for plan in data:
            assert plan["status"] == "active"

    async def test_get_installment_plan_details(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test getting installment plan details."""
        response = await client.get(
            f"/api/v1/installments/{test_installment_plan['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_installment_plan["id"]
        assert data["order_id"] == test_installment_plan["order_id"]
        assert data["status"] == test_installment_plan["status"]

    async def test_get_installment_plan_unauthorized(
        self,
        client: AsyncClient,
        test_installment_plan: dict,
    ):
        """Test getting installment plan without authentication."""
        response = await client.get(
            f"/api/v1/installments/{test_installment_plan['id']}",
        )
        assert response.status_code == 401


class TestInstallmentSchedule:
    """Tests for installment payment schedule."""

    async def test_get_installment_schedule(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test getting payment schedule for installment plan."""
        response = await client.get(
            f"/api/v1/installments/{test_installment_plan['id']}/schedule",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == test_installment_plan["num_installments"]

        # Verify schedule is ordered by installment number
        for i, payment in enumerate(data, 1):
            assert payment["installment_number"] == i
            assert payment["installment_plan_id"] == test_installment_plan["id"]
            assert "due_date" in payment
            assert "amount" in payment
            assert "status" in payment

    async def test_get_upcoming_installments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test getting upcoming installments."""
        response = await client.get(
            "/api/v1/installments/upcoming/due?days_ahead=30",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should have at least one upcoming installment
        if data:
            for payment in data:
                assert "due_date" in payment
                assert "amount" in payment
                # Due date should be within 30 days
                due = date.fromisoformat(payment["due_date"])
                assert due <= date.today() + timedelta(days=30)

    async def test_get_upcoming_installments_custom_range(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting upcoming installments with custom day range."""
        response = await client.get(
            "/api/v1/installments/upcoming/due?days_ahead=7",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestInstallmentCancellation:
    """Tests for cancelling installment plans."""

    async def test_cancel_installment_plan(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
    ):
        """Test cancelling an installment plan."""
        response = await client.post(
            f"/api/v1/installments/{test_installment_plan['id']}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cancelled"
        assert data["id"] == test_installment_plan["id"]

    async def test_cancel_already_cancelled_plan(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
        db_session,
    ):
        """Test cannot cancel already cancelled plan."""
        from app.models.payment import InstallmentPlan, InstallmentPlanStatus

        # Cancel the plan
        plan = await InstallmentPlan.get_by_id(db_session, test_installment_plan["id"])
        plan.status = InstallmentPlanStatus.CANCELLED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/installments/{test_installment_plan['id']}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "cancel" in response.json()["message"].lower()

    async def test_cancel_unauthorized(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_installment_plan: dict,
        create_test_user,
    ):
        """Test cannot cancel another user's installment plan."""
        # Create another user
        other_user = await create_test_user("other@example.com", "Other User")

        response = await client.post(
            f"/api/v1/installments/{test_installment_plan['id']}/cancel",
            headers={"Authorization": f"Bearer {other_user['access_token']}"},
        )
        assert response.status_code == 403


class TestInstallmentAdminEndpoints:
    """Tests for admin installment endpoints."""

    async def test_admin_list_all_installments(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_installment_plan: dict,
    ):
        """Test admin can list all installment plans."""
        response = await client.get(
            "/api/v1/installments/",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should include the test plan
        assert any(plan["id"] == test_installment_plan["id"] for plan in data)

    async def test_admin_list_with_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test admin list with pagination."""
        response = await client.get(
            "/api/v1/installments/?limit=10&offset=0",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 10

    async def test_admin_list_filtered_by_status(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test admin can filter by status."""
        response = await client.get(
            "/api/v1/installments/?status=active",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # All plans should be active
        for plan in data:
            assert plan["status"] == "active"

    async def test_admin_cancel_installment_plan(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_installment_plan: dict,
    ):
        """Test admin can cancel any installment plan."""
        response = await client.post(
            f"/api/v1/installments/{test_installment_plan['id']}/cancel-admin",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cancelled"

    async def test_non_admin_cannot_access_admin_endpoints(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test non-admin cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/installments/",
            headers=auth_headers,
        )
        assert response.status_code == 403
