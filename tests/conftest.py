import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure critical settings exist before the app/config modules import.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me-please")
os.environ.setdefault(
    "ENCRYPTION_KEY", "lvh82OR2Fn8OsoGJ3CCXohfgjYAsATdtnRiLV_3Y3d0="
)  # Valid Fernet key for testing

from app.models.user import Role, User
from app.utils.security import create_tokens, hash_password
from core.db import get_db
from core.db.base import Base
from main import app

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create and drop all tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for testing."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing."""

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=hash_password("TestPass123"),
        role=Role.PARENT,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        hashed_password=hash_password("AdminPass123"),
        role=Role.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    access_token, _ = create_tokens(test_user.id, test_user.role.value)
    return {"Authorization": f"Bearer {access_token}", "user_id": test_user.id}


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """Create authentication headers for admin user."""
    access_token, _ = create_tokens(admin_user.id, admin_user.role.value)
    return {"Authorization": f"Bearer {access_token}", "user_id": admin_user.id}


@pytest.fixture
def admin_auth_headers(admin_headers: dict) -> dict:
    """Alias for admin_headers for compatibility."""
    return admin_headers


@pytest.fixture
async def create_test_user(db_session: AsyncSession):
    """Factory fixture to create additional test users."""
    async def _create_user(email: str, name: str = "Test User", role: Role = Role.PARENT):
        user = User(
            email=email,
            first_name=name.split()[0],
            last_name=name.split()[-1] if len(name.split()) > 1 else "User",
            hashed_password=hash_password("TestPass123"),
            role=role,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        access_token, _ = create_tokens(user.id, user.role.value)
        return {
            "id": user.id,
            "email": user.email,
            "access_token": access_token,
        }
    return _create_user


@pytest.fixture
async def test_area(db_session: AsyncSession) -> "Area":
    """Create a test area."""
    from app.models.program import Area

    area = Area(
        name="Test Area",
        description="A test geographic area",
        is_active=True,
    )
    db_session.add(area)
    await db_session.commit()
    await db_session.refresh(area)
    return area


@pytest.fixture
async def test_program(db_session: AsyncSession) -> "Program":
    """Create a test program."""
    from app.models.program import Program

    program = Program(
        name="Test Soccer Program",
        description="A test soccer program",
        is_active=True,
    )
    db_session.add(program)
    await db_session.commit()
    await db_session.refresh(program)
    return program


@pytest.fixture
async def test_school(db_session: AsyncSession, test_area) -> "School":
    """Create a test school."""
    from app.models.program import School

    school = School(
        name="Test School",
        address="123 Test St",
        city="Test City",
        state="CA",
        zip_code="12345",
        area_id=test_area.id,
        is_active=True,
    )
    db_session.add(school)
    await db_session.commit()
    await db_session.refresh(school)
    return school


@pytest.fixture
async def test_class(db_session: AsyncSession, test_program, test_school) -> dict:
    """Create a test class for enrollment."""
    from datetime import date, time
    from decimal import Decimal
    from app.models.class_ import Class, ClassType

    class_ = Class(
        name="Test Soccer Class",
        description="A test soccer class",
        program_id=test_program.id,
        school_id=test_school.id,
        class_type=ClassType.SHORT_TERM,
        weekdays=["monday", "wednesday"],
        start_date=date.today(),
        end_date=date.today().replace(year=date.today().year + 1),
        start_time=time(16, 0),
        end_time=time(17, 0),
        capacity=20,
        price=Decimal("150.00"),
        min_age=6,
        max_age=12,
        is_active=True,
    )
    db_session.add(class_)
    await db_session.commit()
    await db_session.refresh(class_)
    return {
        "id": class_.id,
        "name": class_.name,
        "price": str(class_.price),
        "program_id": class_.program_id,
    }


@pytest.fixture
async def test_child(db_session: AsyncSession, test_user: User) -> dict:
    """Create a test child for the test user."""
    from datetime import date, timedelta
    from app.models.child import Child, JerseySize

    child = await Child.create_child(
        db_session,
        user_id=test_user.id,
        first_name="TestChild",
        last_name="User",
        date_of_birth=date.today() - timedelta(days=365 * 8),  # 8 years old
        jersey_size=JerseySize.M,
    )
    return {
        "id": child.id,
        "first_name": child.first_name,
        "last_name": child.last_name,
    }


@pytest.fixture
async def test_order(db_session: AsyncSession, test_user: User, test_child: dict, test_class: dict) -> dict:
    """Create a test order."""
    from decimal import Decimal
    from app.models.order import Order, OrderStatus

    order = await Order.create_order(
        db_session,
        user_id=test_user.id,
        status=OrderStatus.DRAFT,
        subtotal=Decimal(test_class["price"]),
        discount_total=Decimal("0.00"),
        total=Decimal(test_class["price"]),
    )
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status.value,
        "total": str(order.total),
    }


@pytest.fixture
async def test_payment_method(test_user: User) -> dict:
    """Create a mock payment method for testing."""
    # Return a mock Stripe payment method ID
    # In real tests, you might want to use Stripe test tokens
    return {
        "id": "pm_test_1234567890",
        "brand": "visa",
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2025,
    }


@pytest.fixture
async def test_installment_plan(
    db_session: AsyncSession,
    test_user: User,
    test_order: dict
) -> dict:
    """Create a test installment plan."""
    from datetime import date
    from decimal import Decimal
    from app.models.payment import (
        InstallmentPlan,
        InstallmentPlanStatus,
        InstallmentFrequency,
        InstallmentPayment,
        InstallmentPaymentStatus,
    )

    plan = await InstallmentPlan.create_plan(
        db_session,
        order_id=test_order["id"],
        user_id=test_user.id,
        total_amount=Decimal(test_order["total"]),
        num_installments=3,
        installment_amount=Decimal(test_order["total"]) / 3,
        frequency=InstallmentFrequency.MONTHLY,
        start_date=date.today(),
        stripe_subscription_id="sub_test_1234567890",
        status=InstallmentPlanStatus.ACTIVE,
    )

    # Create installment payment records
    for i in range(3):
        from datetime import timedelta
        installment = InstallmentPayment(
            installment_plan_id=plan.id,
            installment_number=i + 1,
            due_date=date.today() + timedelta(days=30 * i),
            amount=Decimal(test_order["total"]) / 3,
            status=InstallmentPaymentStatus.PENDING,
        )
        db_session.add(installment)

    await db_session.commit()
    await db_session.refresh(plan)

    return {
        "id": plan.id,
        "order_id": plan.order_id,
        "user_id": plan.user_id,
        "num_installments": plan.num_installments,
        "status": plan.status.value,
    }


@pytest.fixture
def mock_stripe_service():
    """Mock Stripe service methods for testing."""
    with patch("app.services.installment_service.StripeService") as mock_stripe:
        # Create a mock instance
        mock_instance = AsyncMock()

        # Mock get_or_create_customer
        mock_instance.get_or_create_customer = AsyncMock(return_value="cus_test_123")

        # Mock create_installment_subscription
        mock_instance.create_installment_subscription = AsyncMock(
            return_value={"id": "sub_test_123", "status": "active"}
        )

        # Mock cancel_subscription
        mock_instance.cancel_subscription = AsyncMock(return_value={"status": "canceled"})

        # Make the class constructor return our mock instance
        mock_stripe.return_value = mock_instance

        yield mock_instance
