"""Tests for Stripe product and price management."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class, BillingModel
from app.models.user import User
from app.services.stripe_product_service import StripeProductService


@pytest.fixture
def mock_stripe_product():
    """Mock Stripe product object."""
    return {
        "id": "prod_test123",
        "object": "product",
        "active": True,
        "name": "Test Product",
        "description": "Test product description",
        "metadata": {},
        "created": 1234567890,
    }


@pytest.fixture
def mock_stripe_price():
    """Mock Stripe price object."""
    return {
        "id": "price_test123",
        "object": "price",
        "active": True,
        "currency": "usd",
        "unit_amount": 9900,
        "recurring": {
            "interval": "month",
            "interval_count": 1,
        },
        "product": "prod_test123",
        "metadata": {},
    }


@pytest.fixture
def mock_stripe_one_time_price():
    """Mock Stripe one-time price object."""
    return {
        "id": "price_onetime123",
        "object": "price",
        "active": True,
        "currency": "usd",
        "unit_amount": 5000,
        "recurring": None,
        "product": "prod_test123",
        "metadata": {},
    }


class TestStripeProductService:
    """Test StripeProductService functionality."""

    @pytest.mark.asyncio
    async def test_create_product(self, mock_stripe_product):
        """Test creating a Stripe product."""
        with patch("stripe.Product.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_product)

            product = await StripeProductService.create_product(
                name="Test Product",
                description="Test description",
                metadata={"key": "value"},
            )

            assert product["id"] == "prod_test123"
            assert product["name"] == "Test Product"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product(self, mock_stripe_product):
        """Test retrieving a Stripe product."""
        with patch("stripe.Product.retrieve_async", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = MagicMock(**mock_stripe_product)

            product = await StripeProductService.get_product("prod_test123")

            assert product["id"] == "prod_test123"
            mock_retrieve.assert_called_once_with("prod_test123")

    @pytest.mark.asyncio
    async def test_update_product(self, mock_stripe_product):
        """Test updating a Stripe product."""
        updated_product = mock_stripe_product.copy()
        updated_product["name"] = "Updated Product"

        with patch("stripe.Product.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(**updated_product)

            product = await StripeProductService.update_product(
                product_id="prod_test123",
                name="Updated Product",
            )

            assert product["name"] == "Updated Product"
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product(self):
        """Test archiving a Stripe product."""
        with patch("stripe.Product.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(active=False)

            result = await StripeProductService.delete_product("prod_test123")

            assert result is True
            mock_modify.assert_called_once_with("prod_test123", active=False)

    @pytest.mark.asyncio
    async def test_list_products(self, mock_stripe_product):
        """Test listing Stripe products."""
        with patch("stripe.Product.list_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = MagicMock(data=[MagicMock(**mock_stripe_product)])

            products = await StripeProductService.list_products(limit=10, active=True)

            assert len(products) > 0
            assert products[0]["id"] == "prod_test123"
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_recurring_price(self, mock_stripe_price):
        """Test creating a recurring Stripe price."""
        with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_price)

            price = await StripeProductService.create_price(
                product_id="prod_test123",
                amount=Decimal("99.00"),
                currency="usd",
                interval="month",
                interval_count=1,
            )

            assert price["id"] == "price_test123"
            assert price["unit_amount"] == 9900
            assert price["recurring"]["interval"] == "month"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_one_time_price(self, mock_stripe_one_time_price):
        """Test creating a one-time Stripe price."""
        with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_one_time_price)

            price = await StripeProductService.create_one_time_price(
                product_id="prod_test123",
                amount=Decimal("50.00"),
                currency="usd",
            )

            assert price["id"] == "price_onetime123"
            assert price["unit_amount"] == 5000
            assert price["recurring"] is None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_price(self, mock_stripe_price):
        """Test updating a Stripe price."""
        with patch("stripe.Price.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(**mock_stripe_price)

            price = await StripeProductService.update_price(
                price_id="price_test123",
                metadata={"updated": "true"},
                active=True,
            )

            assert price["id"] == "price_test123"
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_price(self):
        """Test deactivating a Stripe price."""
        with patch("stripe.Price.modify_async", new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = MagicMock(active=False)

            result = await StripeProductService.deactivate_price("price_test123")

            assert result is True
            mock_modify.assert_called_once_with("price_test123", active=False)

    @pytest.mark.asyncio
    async def test_list_prices(self, mock_stripe_price):
        """Test listing Stripe prices."""
        with patch("stripe.Price.list_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = MagicMock(data=[MagicMock(**mock_stripe_price)])

            prices = await StripeProductService.list_prices(
                product_id="prod_test123",
                limit=10,
                active=True,
            )

            assert len(prices) > 0
            assert prices[0]["id"] == "price_test123"
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_for_class(
        self,
        db_session: AsyncSession,
        mock_stripe_product,
    ):
        """Test creating a Stripe product for a class."""
        # Create class
        class_ = Class(
            name="Karate Class",
            description="Learn karate",
            billing_model=BillingModel.MONTHLY,
            monthly_price=Decimal("99.00"),
            capacity=20,
        )
        db_session.add(class_)
        await db_session.commit()
        await db_session.refresh(class_)

        with patch("stripe.Product.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_product)

            product = await StripeProductService.create_product_for_class(
                db_session=db_session,
                class_id=str(class_.id),
            )

            assert product["id"] == "prod_test123"
            # Check that class was updated with product ID
            await db_session.refresh(class_)
            assert class_.stripe_product_id == "prod_test123"

    @pytest.mark.asyncio
    async def test_create_prices_for_class(
        self,
        db_session: AsyncSession,
        mock_stripe_price,
    ):
        """Test creating Stripe prices for a class."""
        # Create class with product ID
        class_ = Class(
            name="Karate Class",
            description="Learn karate",
            billing_model=BillingModel.MONTHLY,
            monthly_price=Decimal("99.00"),
            quarterly_price=Decimal("270.00"),
            annual_price=Decimal("1000.00"),
            capacity=20,
            stripe_product_id="prod_test123",
        )
        db_session.add(class_)
        await db_session.commit()
        await db_session.refresh(class_)

        with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_price)

            prices = await StripeProductService.create_prices_for_class(
                db_session=db_session,
                class_id=str(class_.id),
                create_monthly=True,
                create_quarterly=True,
                create_annual=True,
            )

            assert "monthly" in prices
            assert "quarterly" in prices
            assert "annual" in prices
            # Verify 3 price creation calls
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_sync_class_with_stripe(
        self,
        db_session: AsyncSession,
        mock_stripe_product,
        mock_stripe_price,
    ):
        """Test syncing a class with Stripe (create product and prices)."""
        # Create class without Stripe IDs
        class_ = Class(
            name="Karate Class",
            description="Learn karate",
            billing_model=BillingModel.MONTHLY,
            monthly_price=Decimal("99.00"),
            capacity=20,
        )
        db_session.add(class_)
        await db_session.commit()
        await db_session.refresh(class_)

        with patch("stripe.Product.create_async", new_callable=AsyncMock) as mock_product:
            mock_product.return_value = MagicMock(**mock_stripe_product)
            with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_price:
                mock_price.return_value = MagicMock(**mock_stripe_price)

                result = await StripeProductService.sync_class_with_stripe(
                    db_session=db_session,
                    class_id=str(class_.id),
                )

                assert result["product"]["id"] == "prod_test123"
                assert "prices" in result
                # Check that class was updated
                await db_session.refresh(class_)
                assert class_.stripe_product_id == "prod_test123"


class TestStripeProductEndpoints:
    """Test Stripe product admin API endpoints."""

    @pytest.mark.asyncio
    async def test_create_product_endpoint(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        mock_stripe_product,
    ):
        """Test creating product via API."""
        with patch("stripe.Product.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_product)

            response = await async_client.post(
                "/api/v1/admin/stripe/products",
                headers=admin_headers,
                json={
                    "name": "Test Product",
                    "description": "Test description",
                    "metadata": {},
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == "prod_test123"

    @pytest.mark.asyncio
    async def test_list_products_endpoint(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        mock_stripe_product,
    ):
        """Test listing products via API."""
        with patch("stripe.Product.list_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = MagicMock(data=[MagicMock(**mock_stripe_product)])

            response = await async_client.get(
                "/api/v1/admin/stripe/products",
                headers=admin_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_create_price_endpoint(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        mock_stripe_price,
    ):
        """Test creating price via API."""
        with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_price)

            response = await async_client.post(
                "/api/v1/admin/stripe/prices",
                headers=admin_headers,
                json={
                    "product_id": "prod_test123",
                    "amount": 99.00,
                    "currency": "usd",
                    "interval": "month",
                    "interval_count": 1,
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == "price_test123"

    @pytest.mark.asyncio
    async def test_create_one_time_price_endpoint(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        mock_stripe_one_time_price,
    ):
        """Test creating one-time price via API."""
        with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(**mock_stripe_one_time_price)

            response = await async_client.post(
                "/api/v1/admin/stripe/prices/one-time",
                headers=admin_headers,
                json={
                    "product_id": "prod_test123",
                    "amount": 50.00,
                    "currency": "usd",
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == "price_onetime123"

    @pytest.mark.asyncio
    async def test_sync_class_endpoint(
        self,
        db_session: AsyncSession,
        async_client: AsyncClient,
        admin_headers: dict,
        mock_stripe_product,
        mock_stripe_price,
    ):
        """Test syncing class with Stripe via API."""
        # Create class
        class_ = Class(
            name="Karate Class",
            description="Learn karate",
            billing_model=BillingModel.MONTHLY,
            monthly_price=Decimal("99.00"),
            capacity=20,
        )
        db_session.add(class_)
        await db_session.commit()
        await db_session.refresh(class_)

        with patch("stripe.Product.create_async", new_callable=AsyncMock) as mock_product:
            mock_product.return_value = MagicMock(**mock_stripe_product)
            with patch("stripe.Price.create_async", new_callable=AsyncMock) as mock_price:
                mock_price.return_value = MagicMock(**mock_stripe_price)

                response = await async_client.post(
                    "/api/v1/admin/stripe/classes/sync",
                    headers=admin_headers,
                    json={"class_id": str(class_.id)},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "product" in data
                assert "prices" in data

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_stripe_endpoints(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that non-admin users cannot access Stripe product endpoints."""
        response = await async_client.get(
            "/api/v1/admin/stripe/products",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPriceValidation:
    """Test price validation in schemas."""

    def test_amount_validation_positive(self):
        """Test that amount must be positive."""
        from app.schemas.stripe_product import PriceCreate

        # Valid amount
        price = PriceCreate(
            product_id="prod_test",
            amount=Decimal("99.99"),
            interval="month",
        )
        assert price.amount == Decimal("99.99")

    def test_amount_validation_negative_raises_error(self):
        """Test that negative amount raises error."""
        from app.schemas.stripe_product import PriceCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PriceCreate(
                product_id="prod_test",
                amount=Decimal("-10.00"),
                interval="month",
            )

    def test_amount_validation_zero_raises_error(self):
        """Test that zero amount raises error."""
        from app.schemas.stripe_product import PriceCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PriceCreate(
                product_id="prod_test",
                amount=Decimal("0.00"),
                interval="month",
            )

    def test_currency_validation(self):
        """Test currency code validation."""
        from app.schemas.stripe_product import PriceCreate

        # Valid 3-letter lowercase currency
        price = PriceCreate(
            product_id="prod_test",
            amount=Decimal("99.99"),
            currency="usd",
            interval="month",
        )
        assert price.currency == "usd"

    def test_interval_validation(self):
        """Test interval validation."""
        from app.schemas.stripe_product import PriceCreate

        # Valid intervals
        for interval in ["month", "year"]:
            price = PriceCreate(
                product_id="prod_test",
                amount=Decimal("99.99"),
                interval=interval,
            )
            assert price.interval == interval

    def test_interval_count_validation(self):
        """Test interval count validation."""
        from app.schemas.stripe_product import PriceCreate

        # Valid interval count (1-12)
        price = PriceCreate(
            product_id="prod_test",
            amount=Decimal("99.99"),
            interval="month",
            interval_count=3,
        )
        assert price.interval_count == 3
