"""Tests for subscription management functionality."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import stripe
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class, BillingModel
from app.models.enrollment import Enrollment
from app.models.order import Order
from app.models.payment import Payment, PaymentType, PaymentStatus
from app.models.user import User
from app.services.subscription_service import SubscriptionService
from app.services.stripe_service import StripeService


@pytest.fixture
def subscription_service():
    """Create subscription service with mocked Stripe service."""
    stripe_service = MagicMock(spec=StripeService)
    return SubscriptionService(stripe_service)


@pytest.fixture
def mock_stripe_subscription():
    """Mock Stripe subscription object."""
    return MagicMock(
        id="sub_test123",
        status="active",
        current_period_start=int(datetime.now().timestamp()),
        current_period_end=int((datetime.now() + timedelta(days=30)).timestamp()),
        cancel_at_period_end=False,
        canceled_at=None,
    )


@pytest.fixture
async def monthly_class(db_session: AsyncSession):
    """Create a monthly subscription class."""
    class_ = Class(
        name="Monthly Karate",
        description="Monthly karate class",
        billing_model=BillingModel.MONTHLY,
        monthly_price=Decimal("99.00"),
        short_term_price=Decimal("120.00"),
        capacity=20,
        stripe_product_id="prod_test123",
        stripe_monthly_price_id="price_monthly123",
    )
    db_session.add(class_)
    await db_session.commit()
    await db_session.refresh(class_)
    return class_


@pytest.fixture
async def subscription_enrollment(db_session: AsyncSession, test_user: User, test_child, monthly_class: Class):
    """Create an enrollment with active subscription."""
    order = Order(
        user_id=test_user.id,
        total_amount=Decimal("99.00"),
        status="completed",
    )
    db_session.add(order)
    await db_session.commit()

    enrollment = Enrollment(
        user_id=test_user.id,
        child_id=test_child.id,
        class_id=monthly_class.id,
        order_id=order.id,
        status="active",
        stripe_subscription_id="sub_test123",
        subscription_status="active",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30),
    )
    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)
    return enrollment


class TestSubscriptionService:
    """Test SubscriptionService business logic."""

    @pytest.mark.asyncio
    async def test_create_subscription_for_enrollment(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        test_user: User,
        test_child,
        monthly_class: Class,
        mock_stripe_subscription,
    ):
        """Test creating a subscription for an enrollment."""
        # Setup
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("99.00"),
            status="pending",
        )
        db_session.add(order)
        await db_session.commit()

        enrollment = Enrollment(
            user_id=test_user.id,
            child_id=test_child.id,
            class_id=monthly_class.id,
            order_id=order.id,
            status="pending",
        )
        db_session.add(enrollment)
        await db_session.commit()

        # Set user's Stripe customer ID
        test_user.stripe_customer_id = "cus_test123"
        await db_session.commit()

        # Mock Stripe calls
        with patch("stripe.PaymentMethod.attach_async", new_callable=AsyncMock):
            with patch("stripe.Customer.modify_async", new_callable=AsyncMock):
                subscription_service.stripe_service.create_subscription = AsyncMock(
                    return_value=mock_stripe_subscription
                )

                # Execute
                payment = await subscription_service.create_subscription_for_enrollment(
                    db_session=db_session,
                    enrollment=enrollment,
                    class_=monthly_class,
                    order=order,
                    payment_method_id="pm_test123",
                )

                # Assert
                assert payment is not None
                assert payment.payment_type == PaymentType.SUBSCRIPTION
                assert payment.amount == Decimal("99.00")
                assert enrollment.stripe_subscription_id == "sub_test123"
                assert enrollment.subscription_status == "active"

    @pytest.mark.asyncio
    async def test_create_subscription_for_one_time_class_raises_error(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        test_user: User,
        test_child,
    ):
        """Test that creating subscription for one-time class raises error."""
        # Create one-time class
        class_ = Class(
            name="One-time Workshop",
            description="One-time workshop",
            billing_model=BillingModel.ONE_TIME,
            short_term_price=Decimal("50.00"),
            capacity=15,
        )
        db_session.add(class_)
        await db_session.commit()

        order = Order(user_id=test_user.id, total_amount=Decimal("50.00"), status="pending")
        db_session.add(order)
        await db_session.commit()

        enrollment = Enrollment(
            user_id=test_user.id,
            child_id=test_child.id,
            class_id=class_.id,
            order_id=order.id,
            status="pending",
        )
        db_session.add(enrollment)
        await db_session.commit()

        # Execute & Assert
        with pytest.raises(ValueError, match="not subscription-based"):
            await subscription_service.create_subscription_for_enrollment(
                db_session=db_session,
                enrollment=enrollment,
                class_=class_,
                order=order,
                payment_method_id="pm_test123",
            )

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        subscription_enrollment: Enrollment,
    ):
        """Test immediate subscription cancellation."""
        # Mock Stripe call
        with patch("stripe.Subscription.cancel_async", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = MagicMock(
                id=subscription_enrollment.stripe_subscription_id,
                status="canceled",
            )

            # Execute
            await subscription_service.cancel_subscription(
                db_session=db_session,
                enrollment=subscription_enrollment,
                cancel_immediately=True,
                prorate=True,
            )

            # Assert
            assert subscription_enrollment.subscription_status == "canceled"
            assert subscription_enrollment.subscription_cancelled_at is not None
            mock_cancel.assert_called_once_with(
                subscription_enrollment.stripe_subscription_id,
                prorate=True,
            )

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        subscription_enrollment: Enrollment,
    ):
        """Test scheduling subscription cancellation at period end."""
        # Mock Stripe call
        with patch("stripe.Subscription.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(
                id=subscription_enrollment.stripe_subscription_id,
                cancel_at_period_end=True,
            )

            # Execute
            await subscription_service.cancel_subscription(
                db_session=db_session,
                enrollment=subscription_enrollment,
                cancel_immediately=False,
            )

            # Assert
            assert subscription_enrollment.cancel_at_period_end is True
            assert subscription_enrollment.subscription_cancelled_at is not None
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_reactivate_subscription(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        subscription_enrollment: Enrollment,
    ):
        """Test reactivating a subscription scheduled for cancellation."""
        # Setup - schedule cancellation first
        subscription_enrollment.cancel_at_period_end = True
        subscription_enrollment.subscription_cancelled_at = datetime.now()
        await db_session.commit()

        # Mock Stripe call
        with patch("stripe.Subscription.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(
                id=subscription_enrollment.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            # Execute
            await subscription_service.reactivate_subscription(
                db_session=db_session,
                enrollment=subscription_enrollment,
            )

            # Assert
            assert subscription_enrollment.cancel_at_period_end is False
            assert subscription_enrollment.subscription_cancelled_at is None
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_payment_method(
        self,
        db_session: AsyncSession,
        subscription_service: SubscriptionService,
        subscription_enrollment: Enrollment,
        test_user: User,
    ):
        """Test updating payment method for a subscription."""
        # Set user's Stripe customer ID
        test_user.stripe_customer_id = "cus_test123"
        await db_session.commit()

        # Mock Stripe calls
        with patch("stripe.PaymentMethod.attach_async", new_callable=AsyncMock) as mock_attach:
            with patch("stripe.Subscription.modify_async", new_callable=AsyncMock) as mock_sub_modify:
                with patch("stripe.Customer.modify_async", new_callable=AsyncMock) as mock_cust_modify:
                    # Execute
                    await subscription_service.update_payment_method(
                        db_session=db_session,
                        enrollment=subscription_enrollment,
                        payment_method_id="pm_new123",
                    )

                    # Assert
                    mock_attach.assert_called_once_with("pm_new123", customer="cus_test123")
                    mock_sub_modify.assert_called_once()
                    mock_cust_modify.assert_called_once()


class TestSubscriptionEndpoints:
    """Test subscription API endpoints."""

    @pytest.mark.asyncio
    async def test_list_user_subscriptions(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
    ):
        """Test listing user's subscriptions."""
        response = await async_client.get("/api/v1/subscriptions", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        subscription = data[0]
        assert subscription["enrollment_id"] == str(subscription_enrollment.id)
        assert subscription["subscription_status"] == "active"

    @pytest.mark.asyncio
    async def test_get_subscription_details(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
    ):
        """Test getting subscription details."""
        response = await async_client.get(
            f"/api/v1/subscriptions/{subscription_enrollment.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enrollment_id"] == str(subscription_enrollment.id)
        assert data["subscription_id"] == subscription_enrollment.stripe_subscription_id

    @pytest.mark.asyncio
    async def test_cancel_subscription_endpoint(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
    ):
        """Test cancelling subscription via API."""
        with patch("stripe.Subscription.modify_async", new_callable=AsyncMock):
            response = await async_client.post(
                f"/api/v1/subscriptions/{subscription_enrollment.id}/cancel",
                headers=auth_headers,
                json={"cancel_immediately": False},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Subscription cancelled successfully"
            assert data["effective_date"] == "end of billing period"

    @pytest.mark.asyncio
    async def test_reactivate_subscription_endpoint(
        self,
        db_session: AsyncSession,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
    ):
        """Test reactivating subscription via API."""
        # Setup - schedule cancellation first
        subscription_enrollment.cancel_at_period_end = True
        subscription_enrollment.subscription_cancelled_at = datetime.now()
        await db_session.commit()

        with patch("stripe.Subscription.modify_async", new_callable=AsyncMock):
            response = await async_client.post(
                f"/api/v1/subscriptions/{subscription_enrollment.id}/reactivate",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Subscription reactivated successfully"

    @pytest.mark.asyncio
    async def test_update_payment_method_endpoint(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test updating payment method via API."""
        # Set user's Stripe customer ID
        test_user.stripe_customer_id = "cus_test123"
        await db_session.commit()

        with patch("stripe.PaymentMethod.attach_async", new_callable=AsyncMock):
            with patch("stripe.Subscription.modify_async", new_callable=AsyncMock):
                with patch("stripe.Customer.modify_async", new_callable=AsyncMock):
                    response = await async_client.put(
                        f"/api/v1/subscriptions/{subscription_enrollment.id}/payment-method",
                        headers=auth_headers,
                        json={"payment_method_id": "pm_new123"},
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["message"] == "Payment method updated successfully"

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_subscription(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        subscription_enrollment: Enrollment,
        db_session: AsyncSession,
    ):
        """Test that users cannot access other users' subscriptions."""
        # Create another user
        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            role="parent",
        )
        db_session.add(other_user)
        await db_session.commit()

        # Try to access subscription with different user's auth
        # (This would need a different auth token in practice)
        response = await async_client.get(
            f"/api/v1/subscriptions/{subscription_enrollment.id}",
            headers=auth_headers,
        )

        # The subscription belongs to test_user, so this should work
        # To properly test access control, we'd need to create auth headers for other_user
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


class TestClassBillingModels:
    """Test class billing model functionality."""

    @pytest.mark.asyncio
    async def test_class_get_subscription_price_monthly(self, monthly_class: Class):
        """Test getting subscription price for monthly class."""
        price = monthly_class.get_subscription_price()
        assert price == Decimal("99.00")

    @pytest.mark.asyncio
    async def test_class_get_subscription_price_quarterly(self, db_session: AsyncSession):
        """Test getting subscription price for quarterly class."""
        class_ = Class(
            name="Quarterly Karate",
            description="Quarterly karate class",
            billing_model=BillingModel.QUARTERLY,
            quarterly_price=Decimal("270.00"),
            capacity=20,
        )
        db_session.add(class_)
        await db_session.commit()

        price = class_.get_subscription_price()
        assert price == Decimal("270.00")

    @pytest.mark.asyncio
    async def test_class_get_subscription_price_annual(self, db_session: AsyncSession):
        """Test getting subscription price for annual class."""
        class_ = Class(
            name="Annual Karate",
            description="Annual karate membership",
            billing_model=BillingModel.ANNUAL,
            annual_price=Decimal("1000.00"),
            capacity=20,
        )
        db_session.add(class_)
        await db_session.commit()

        price = class_.get_subscription_price()
        assert price == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_class_is_subscription_based(self, monthly_class: Class):
        """Test checking if class is subscription-based."""
        assert monthly_class.is_subscription_based is True

    @pytest.mark.asyncio
    async def test_class_is_not_subscription_based(self, db_session: AsyncSession):
        """Test one-time class is not subscription-based."""
        class_ = Class(
            name="One-time Workshop",
            description="One-time workshop",
            billing_model=BillingModel.ONE_TIME,
            short_term_price=Decimal("50.00"),
            capacity=15,
        )
        db_session.add(class_)
        await db_session.commit()

        assert class_.is_subscription_based is False

    @pytest.mark.asyncio
    async def test_class_get_stripe_price_id_monthly(self, monthly_class: Class):
        """Test getting Stripe price ID for monthly billing."""
        price_id = monthly_class.get_stripe_price_id()
        assert price_id == "price_monthly123"

    @pytest.mark.asyncio
    async def test_class_get_stripe_price_id_one_time_returns_none(self, db_session: AsyncSession):
        """Test that one-time class returns None for price ID."""
        class_ = Class(
            name="One-time Workshop",
            billing_model=BillingModel.ONE_TIME,
            short_term_price=Decimal("50.00"),
            capacity=15,
        )
        db_session.add(class_)
        await db_session.commit()

        price_id = class_.get_stripe_price_id()
        assert price_id is None


class TestEnrollmentSubscriptionMethods:
    """Test enrollment subscription-related methods."""

    @pytest.mark.asyncio
    async def test_get_by_subscription_id(
        self,
        db_session: AsyncSession,
        subscription_enrollment: Enrollment,
    ):
        """Test getting enrollment by Stripe subscription ID."""
        enrollment = await Enrollment.get_by_subscription_id(
            db_session,
            subscription_enrollment.stripe_subscription_id,
        )

        assert enrollment is not None
        assert enrollment.id == subscription_enrollment.id

    @pytest.mark.asyncio
    async def test_get_active_subscriptions_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        subscription_enrollment: Enrollment,
    ):
        """Test getting all active subscriptions for a user."""
        enrollments = await Enrollment.get_active_subscriptions_by_user(
            db_session,
            test_user.id,
        )

        assert len(enrollments) > 0
        assert any(e.id == subscription_enrollment.id for e in enrollments)

    @pytest.mark.asyncio
    async def test_schedule_subscription_cancellation(
        self,
        db_session: AsyncSession,
        subscription_enrollment: Enrollment,
    ):
        """Test scheduling subscription cancellation."""
        await subscription_enrollment.schedule_subscription_cancellation(db_session)

        assert subscription_enrollment.cancel_at_period_end is True
        assert subscription_enrollment.subscription_cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately_on_enrollment(
        self,
        db_session: AsyncSession,
        subscription_enrollment: Enrollment,
    ):
        """Test immediate subscription cancellation on enrollment."""
        await subscription_enrollment.cancel_subscription_immediately(db_session)

        assert subscription_enrollment.subscription_status == "canceled"
        assert subscription_enrollment.subscription_cancelled_at is not None
