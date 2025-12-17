# CSF Backend - Project Guide

## Project Overview

CSF Software is a **web application** for managing youth sports/activity class registrations. It includes public registration flows, payment processing (one-time, subscription, installments), customizable waivers, and a comprehensive admin portal.

**Key Constraints:**
- Web Application Only (responsive design - NO native mobile app)
- English language only
- Basic reporting (essential metrics)
- 99.9% uptime requirement for payment processing

---

## Architecture Overview

```
CSF Backend Architecture
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer                │
├─────────────────────────────────────────────────────────────┤
│  API Routes │  Business Services │  Auth │  Webhooks        │
├─────────────────────────────────────────────────────────────┤
│      SQLAlchemy ORM │ Redis Cache │ Celery Tasks           │
├─────────────────────────────────────────────────────────────┤
│   PostgreSQL │ Stripe │ Mailchimp │ SendGrid │ Google OAuth │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack**: FastAPI + SQLAlchemy 2.0 + Pydantic V2 + Celery + Redis + Stripe
**Language**: Python 3.12 | **Package Manager**: uv | **Database**: PostgreSQL 15 / SQLite + Alembic

---

## Database Configuration

The application supports **both PostgreSQL and SQLite** databases, configured via the `DATABASE_URL` environment variable:

### PostgreSQL (Recommended for Local Development)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/csf_db
```
- Full-featured RDBMS with native ENUM support
- Connection pooling and advanced query optimization
- Best for production-scale deployments

### SQLite (For Testing & Simple Deployments)
```bash
DATABASE_URL=sqlite+aiosqlite:///./csf.db
```
- Single-file database, easy to deploy
- Suitable for PythonAnywhere and low-traffic deployments
- No separate database server required

**Note**: All models and migrations are database-agnostic. The application automatically adjusts connection settings based on the database type detected in the URL.

---

## Plan & Review Workflow

### Before Starting Work
1. **Always plan first** - Create a detailed implementation plan before coding
2. **Write the plan** to `.claude/tasks/TASK_NAME.md`
3. **Break down complex tasks** into smaller sub-tasks with separate files
4. **Research if needed** - Use Task tool for external knowledge or package research
5. **Think MVP** - Don't over-engineer, focus on minimum viable implementation
6. **Get approval** - Ask for review before proceeding with implementation

### While Implementing
1. **Update the plan** as you work with progress and changes
2. **Document obstacles** and how they were resolved
3. **Ask for clarification** if uncertain about any aspect
4. **Propose significant changes** and wait for approval
5. **Keep code simple** - Clean, maintainable, and focused

### After Completing
1. **Request review** before considering work done
2. **Update context files** so others can understand what was done
3. **Run tests** and ensure all pass before marking complete

---

## Clean Code Principles

### The Boy Scout Rule
**"Leave the codebase cleaner than you found it"**

### Naming Conventions
```python
# BAD
def calc(x, y, d):
    return x * y * (1 - d)

# GOOD
def calculate_discounted_price(base_price: Decimal, quantity: int, discount_rate: Decimal) -> Decimal:
    return base_price * quantity * (1 - discount_rate)
```

### Function Design
- **Single Responsibility**: Each function does one thing well
- **Small Functions**: Keep functions focused and concise (< 20 lines ideal)
- **Descriptive Names**: Function names describe exactly what they do
- **No Side Effects**: Functions should not have hidden behaviors
- **Minimal Arguments**: Prefer 0-3 arguments, use dataclasses for more

### Class Design (SOLID)
- **S**ingle Responsibility: Each class handles one business concern
- **O**pen/Closed: Extensible without modification
- **L**iskov Substitution: Subtypes must be substitutable
- **I**nterface Segregation: Many specific interfaces > one general
- **D**ependency Inversion: Depend on abstractions, not implementations

### Error Handling
```python
# BAD - Generic exception, no context
try:
    process_payment(order)
except Exception:
    return {"error": "failed"}

# GOOD - Specific exception with context
try:
    process_payment(order)
except StripeCardError as e:
    logger.error(f"Payment failed for order {order.id}: {e.message}")
    raise PaymentFailedError(
        message="Card was declined",
        order_id=order.id,
        stripe_error_code=e.code
    )
```

---

## Design Patterns

### Repository Pattern (Data Access)
```python
class EnrollmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, enrollment_id: UUID) -> Enrollment | None:
        return await self.db.get(Enrollment, enrollment_id)

    async def get_active_by_child(self, child_id: UUID) -> list[Enrollment]:
        stmt = select(Enrollment).where(
            Enrollment.child_id == child_id,
            Enrollment.status == EnrollmentStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
```

### Service Pattern (Business Logic)
```python
class EnrollmentService:
    def __init__(
        self,
        enrollment_repo: EnrollmentRepository,
        payment_service: PaymentService,
        email_service: EmailService
    ):
        self.enrollment_repo = enrollment_repo
        self.payment_service = payment_service
        self.email_service = email_service

    async def create_enrollment(self, data: EnrollmentCreate) -> Enrollment:
        # Business logic here
        pass
```

### Factory Pattern (Object Creation)
```python
class PaymentProcessorFactory:
    @staticmethod
    def create(payment_type: PaymentType) -> PaymentProcessor:
        match payment_type:
            case PaymentType.ONE_TIME:
                return OneTimePaymentProcessor()
            case PaymentType.SUBSCRIPTION:
                return SubscriptionPaymentProcessor()
            case PaymentType.INSTALLMENT:
                return InstallmentPaymentProcessor()
```

### Strategy Pattern (Payment Processing)
```python
class PaymentStrategy(Protocol):
    async def process(self, order: Order) -> PaymentResult: ...
    async def refund(self, payment: Payment, amount: Decimal) -> RefundResult: ...
```

---

## Directory Structure

```
csf_backend/
├── CLAUDE.md                    # This file - project guide
├── pyproject.toml               # Dependencies & project config
├── uv.lock                      # Lock file
├── alembic.ini                  # Migration config
├── .env.example                 # Environment template
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # DB connection & session
│   │
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── __init__.py          # Export all models
│   │   ├── base.py              # Base model with common fields
│   │   ├── user.py              # User, Role models
│   │   ├── child.py             # Child, EmergencyContact
│   │   ├── program.py           # Program, Area, School
│   │   ├── class_.py            # Class, ClassInstance
│   │   ├── waiver.py            # WaiverTemplate, WaiverAcceptance
│   │   ├── payment.py           # Payment, InstallmentPlan
│   │   ├── enrollment.py        # Enrollment, Order
│   │   └── discount.py          # DiscountCode, Scholarship
│   │
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── base.py              # Common schema mixins
│   │   ├── user.py
│   │   ├── child.py
│   │   ├── class_.py
│   │   ├── waiver.py
│   │   ├── payment.py
│   │   └── enrollment.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Dependency injection (auth, db, current_user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Main API router
│   │       ├── auth.py          # Authentication endpoints
│   │       ├── users.py         # User management
│   │       ├── classes.py       # Class browsing & management
│   │       ├── children.py      # Child management
│   │       ├── waivers.py       # Waiver templates & acceptance
│   │       ├── payments.py      # Payment processing
│   │       ├── enrollments.py   # Enrollment management
│   │       ├── admin.py         # Admin dashboard & management
│   │       └── webhooks.py      # Stripe webhooks
│   │
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication service
│   │   ├── stripe_service.py    # Stripe integration
│   │   ├── mailchimp_service.py # Mailchimp integration
│   │   ├── email_service.py     # Transactional emails
│   │   ├── enrollment_service.py
│   │   ├── pricing_service.py   # Pricing calculations
│   │   └── waiver_service.py
│   │
│   ├── repositories/            # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py              # Base repository
│   │   ├── user_repository.py
│   │   ├── class_repository.py
│   │   └── enrollment_repository.py
│   │
│   ├── tasks/                   # Celery background tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py        # Celery configuration
│   │   ├── email_tasks.py       # Email sending tasks
│   │   └── installment_tasks.py # Installment processing
│   │
│   └── utils/
│       ├── __init__.py
│       ├── security.py          # Password hashing, JWT
│       ├── encryption.py        # PII encryption (Fernet)
│       └── exceptions.py        # Custom exceptions
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── factories/               # Test data factories
│   │   ├── __init__.py
│   │   └── user_factory.py
│   ├── unit/                    # Unit tests
│   │   ├── test_services/
│   │   └── test_utils/
│   └── integration/             # Integration tests
│       ├── test_auth.py
│       ├── test_classes.py
│       ├── test_payments.py
│       └── test_enrollments.py
│
└── .claude/
    └── tasks/                   # Task planning files
        └── context_session_x.md
```

---

## Tech Stack Details

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.115+ |
| Language | Python | 3.12 |
| ORM | SQLAlchemy | 2.0+ |
| Validation | Pydantic | 2.0+ |
| Database | PostgreSQL | 15+ |
| Migrations | Alembic | 1.13+ |
| Task Queue | Celery | 5.3+ |
| Cache/Broker | Redis | 7+ |
| Payment | Stripe SDK | Latest |
| Email Marketing | Mailchimp API | 3.0 |
| Transactional Email | SendGrid | Latest |
| Package Manager | uv | Latest |

### Frontend (Separate Repo)
- Next.js 14 (App Router), TypeScript 5, Tailwind CSS 3, shadcn/ui
- React Query, React Hook Form + Zod, Recharts, TipTap (rich text)

---

## Database Models

### Core Entities
```
Users              - Parent accounts (email/password + Google OAuth)
Roles              - RBAC (Owner, Admin, Staff, Parent)
Children           - Child profiles (encrypted PII: medical, insurance)
EmergencyContacts  - Per child emergency contacts
```

### Program Structure
```
Programs           - Top-level program types (Soccer, Basketball, etc.)
Areas              - Geographic areas/regions
Schools            - Locations/venues
Classes            - Specific class offerings with schedules
ClassInstances     - Individual class sessions (generated from schedule)
Waitlists          - Waitlist entries for full classes
```

### Waivers
```
WaiverTemplates    - Configurable waiver content (rich text, versioned)
WaiverAcceptances  - Acceptance records (IP, UA, timestamp, version)
```

### Payments & Enrollments
```
Orders             - Order records with line items
OrderLineItems     - Individual items in an order
Enrollments        - Child-to-class enrollment records
Payments           - Payment records (one-time, subscription, installment)
InstallmentPlans   - Installment configuration (num payments, frequency)
InstallmentPayments - Individual installment tracking
DiscountCodes      - Promo codes with validation rules
Scholarships       - Scholarship records
```

### Communication
```
CommunicationLogs  - Email/SMS history with status tracking
```

---

## API Structure

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Email/password registration |
| POST | `/login` | Email/password login |
| POST | `/google` | Google OAuth callback |
| POST | `/refresh` | Refresh JWT token |
| POST | `/logout` | Logout (invalidate token) |
| POST | `/forgot-password` | Request password reset |
| POST | `/reset-password` | Reset password with token |

### Users (`/api/v1/users`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Current user profile |
| PUT | `/me` | Update profile |
| GET | `/me/children` | List user's children |
| POST | `/me/children` | Add child |
| GET | `/me/enrollments` | List user's enrollments |
| GET | `/me/payments` | Payment history |

### Classes (`/api/v1/classes`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List classes (filters: school, weekday, time, age, capacity) |
| GET | `/{id}` | Class details |
| POST | `/` | Create class (admin) |
| PUT | `/{id}` | Update class (admin) |
| DELETE | `/{id}` | Delete class (admin) |
| POST | `/{id}/clone` | Clone class (admin) |
| GET | `/{id}/roster` | Get class roster (admin) |

### Children (`/api/v1/children`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{id}` | Child details |
| PUT | `/{id}` | Update child |
| DELETE | `/{id}` | Remove child |

### Waivers (`/api/v1/waivers`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/templates` | List waiver templates |
| POST | `/templates` | Create template (admin) |
| PUT | `/templates/{id}` | Update template (admin) |
| GET | `/required/{class_id}` | Get required waivers for class |
| POST | `/accept` | Accept waivers |

### Payments (`/api/v1/payments`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/setup-intent` | Create Stripe SetupIntent |
| POST | `/payment-intent` | Create Stripe PaymentIntent |
| POST | `/subscription` | Create subscription |
| POST | `/installment-plan` | Create installment plan |
| GET | `/methods` | List saved payment methods |
| DELETE | `/methods/{id}` | Remove payment method |

### Webhooks (`/api/v1/webhooks`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/stripe` | Stripe webhook handler |

### Orders (`/api/v1/orders`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calculate` | Calculate order total |
| POST | `/` | Create order |
| GET | `/{id}` | Order details |
| GET | `/` | Order history |

### Enrollments (`/api/v1/enrollments`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Create enrollment |
| PUT | `/{id}/transfer` | Transfer to different class |
| PUT | `/{id}/cancel` | Cancel enrollment |
| PUT | `/{id}/reactivate` | Reactivate enrollment |

### Admin (`/api/v1/admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/metrics` | Dashboard metrics |
| GET | `/clients` | Client list (pagination, filters) |
| GET | `/clients/{id}` | Client profile |
| PUT | `/clients/{id}` | Update client |
| GET | `/finance/revenue` | Revenue reports |
| POST | `/export/csv` | Export data |
| POST | `/bulk/email` | Bulk email trigger |

### Discounts (`/api/v1/discounts`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List discount codes |
| POST | `/` | Create discount code |
| POST | `/validate` | Validate code |
| DELETE | `/{id}` | Delete discount code |

---

## Key Business Logic

### Payment Types
| Type | Description | Use Case |
|------|-------------|----------|
| One-time | Single payment | Short-term classes |
| Subscription | Recurring monthly | Memberships |
| Installment | Split into 2 payments | Flexible payment option |

### Sibling Discounts (Auto-applied)
```python
SIBLING_DISCOUNTS = {
    2: Decimal("0.25"),  # 2nd child: 25% off
    3: Decimal("0.35"),  # 3rd child: 35% off
    4: Decimal("0.45"),  # 4th+ child: 45% off
}
```

### Proration Rules
- **Short-term classes**: Prorated based on remaining sessions
- **Memberships**: Prorated based on billing cycle position

### 15-Day Cancellation Policy
The 15-day period starts from the cancellation request date (not enrollment date or class start date).

```python
def calculate_cancellation(enrollment: Enrollment, cancel_date: date) -> CancellationResult:
    days_enrolled = (cancel_date - enrollment.start_date).days

    if days_enrolled < 15:
        # Full refund with no processing fee
        return CancellationResult(
            refund_amount=enrollment.amount_paid,
            effective_date=cancel_date
        )
    else:
        # No refund after 15 days
        return CancellationResult(
            refund_amount=Decimal("0.00"),
            effective_date=cancel_date
        )
```

### Waiver System
- 4 default waiver types included
- Custom waivers per location/program
- Version tracking for legal compliance
- Rich text content support (HTML)
- IP address and timestamp logging for acceptance

---

## Stripe Integration

### Webhook Events to Handle
```python
STRIPE_WEBHOOK_EVENTS = [
    "invoice.payment_succeeded",      # Subscription/installment payment success
    "invoice.payment_failed",         # Payment failure
    "customer.subscription.updated",  # Subscription status change
    "customer.subscription.deleted",  # Subscription cancelled
    "payment_intent.succeeded",       # One-time payment success
    "payment_intent.payment_failed",  # One-time payment failure
    "charge.refunded",                # Refund processed
    "invoice.upcoming",               # Upcoming payment reminder
]
```

### Webhook Handler Pattern
```python
@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_service: StripeService = Depends(get_stripe_service)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe_service.construct_event(payload, sig_header)
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Route to appropriate handler
    handler = WEBHOOK_HANDLERS.get(event.type)
    if handler:
        await handler(event.data.object)

    return {"status": "success"}
```

---

## Environment Variables

```bash
# Application
APP_NAME=csf-backend
APP_ENV=development  # development | staging | production
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/csf_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Auth
SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email - SendGrid
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@csf.com

# Email Marketing - Mailchimp
MAILCHIMP_API_KEY=
MAILCHIMP_SERVER_PREFIX=us1
MAILCHIMP_AUDIENCE_ID=

# Redis
REDIS_URL=redis://localhost:6379/0

# Encryption
ENCRYPTION_KEY=your-fernet-key

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Development Commands

```bash
# Setup
uv sync                              # Install dependencies
uv add <package>                     # Add dependency
uv add --dev <package>               # Add dev dependency

# Database
uv run alembic revision --autogenerate -m "description"  # Create migration
uv run alembic upgrade head          # Apply migrations
uv run alembic downgrade -1          # Rollback one migration

# Development Server
uv run uvicorn app.main:app --reload --port 8000

# Testing
uv run pytest                        # Run all tests
uv run pytest -v                     # Verbose output
uv run pytest --cov=app              # With coverage
uv run pytest --cov=app --cov-report=html  # HTML coverage report
uv run pytest -k "test_auth"         # Run specific tests

# Celery
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat --loglevel=info
uv run celery -A app.tasks.celery_app flower  # Monitoring UI

# Code Quality
uv run ruff check .                  # Linting
uv run ruff format .                 # Formatting
uv run mypy app                      # Type checking

# Stripe CLI (for webhook testing)
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

---

## Security Requirements

### Data Protection
- **PII Encryption**: Medical, insurance data encrypted at rest (Fernet)
- **Password Hashing**: bcrypt with salt rounds >= 12
- **JWT Security**: Short-lived access tokens, secure refresh token rotation

### Access Control
- **RBAC**: Role-based access control (Owner > Admin > Staff > Parent)
- **Resource Ownership**: Users can only access their own data
- **Admin Verification**: Admin endpoints require role verification

### API Security
- **Rate Limiting**: 100 req/min for auth, 1000 req/min general
- **CORS**: Whitelist allowed origins
- **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options
- **Input Validation**: Pydantic validation on all inputs
- **SQL Injection**: Prevented via SQLAlchemy ORM

### Payment Security
- **PCI DSS**: Stripe handles all card data (no card numbers stored)
- **Webhook Verification**: Signature validation on all Stripe webhooks
- **Idempotency**: Prevent duplicate payment processing

---

## Performance Targets

| Metric | Target |
|--------|--------|
| API Response Time (p95) | < 200ms |
| Payment Processing | < 3s |
| Database Query Time | < 100ms |
| Background Task Processing | < 30s |
| System Uptime | 99.9% |
| Test Coverage | 75%+ |

### Optimization Strategies
- **Database**: Proper indexing, query optimization, connection pooling
- **Caching**: Redis for frequently accessed data
- **Async**: Async SQLAlchemy, async HTTP clients
- **Background Jobs**: Offload heavy operations to Celery

---

## Testing Strategy

### Test Types
```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_services/       # Business logic tests
│   └── test_utils/          # Utility function tests
├── integration/             # Tests with database
│   ├── test_auth.py
│   ├── test_payments.py
│   └── test_enrollments.py
└── e2e/                     # Full flow tests
    └── test_registration_flow.py
```

### Test Fixtures (conftest.py)
```python
@pytest.fixture
async def db_session():
    """Async database session for tests"""
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_user(db_session):
    """Create test user"""
    user = User(email="test@example.com", ...)
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def auth_client(test_user):
    """Authenticated test client"""
    token = create_access_token(test_user.id)
    return AsyncClient(headers={"Authorization": f"Bearer {token}"})
```

### Critical Test Flows
1. **Registration → Payment → Enrollment** (all payment types)
2. **Subscription lifecycle** (create, update, cancel)
3. **Installment plan lifecycle** (creation → payments → completion)
4. **Cancellation with 15-day policy**
5. **Waiver acceptance flow**
6. **Admin client management**

---

## Milestones Overview

| Milestone | Focus | Status |
|-----------|-------|--------|
| 1 | Foundation, Auth & Class Browsing | ✅ Complete |
| 2 | Child Registration & Customizable Waivers | ✅ Complete |
| 3 | Payment Integration (Stripe) + Installments | ✅ Complete |
| 4 | Email Automation & Admin Portal Core | Current |
| 5 | Client Management & Advanced Admin | Pending |
| 6 | Testing, Security, Polish & Documentation | Pending |

### Completed: Milestone 1 - Foundation, Auth & Class Browsing

**Backend Tasks:**
- [x] FastAPI project setup with PostgreSQL
- [x] Database schema design
- [x] SQLAlchemy models (User, Role, Program, Area, School, Class)
- [x] Alembic migrations (2 migrations)
- [x] User authentication APIs (email/password + Google OAuth)
- [x] JWT token system (access + refresh tokens)
- [x] Class CRUD APIs with filtering & sorting
- [x] Waitlist/enrollment tracking logic
- [x] Basic unit tests (pytest) - 27 tests passing

**Success Criteria:** ✅ All Met
- User can register/login (email + Google)
- Public can browse classes with filters
- Database migrations working
- Tests passing with good coverage

### Completed: Milestone 2 - Child Registration & Customizable Waivers

**Backend Tasks:**
- [x] Child model and CRUD APIs
- [x] Emergency contact management
- [x] Waiver templates (rich text, versioning)
- [x] Waiver acceptance flow
- [x] PII encryption for sensitive data

**Success Criteria:** ✅ All Met
- Child CRUD with encrypted PII (medical, insurance)
- Emergency contacts per child
- 4 waiver types with versioning
- Waiver acceptance with legal compliance fields
- 55 tests passing

### Completed: Milestone 3 - Payment Integration (Stripe) + Installments

**Backend Tasks:**
- [x] Stripe SDK integration
- [x] Payment models (Payment, InstallmentPlan)
- [x] Order/OrderLineItem models
- [x] Enrollment model and flow
- [x] One-time payment processing
- [x] Subscription billing
- [x] Installment plan setup
- [x] Stripe webhook handlers
- [x] Coupon/discount code system

**Success Criteria:** ✅ All Met
- Users can enroll children in classes
- One-time payment processing works end-to-end
- Installment plans can be created and managed
- Subscription billing infrastructure in place
- Discount codes can be applied
- All webhook events handled properly
- 97 tests passing (100% pass rate)

### Current: Milestone 4 - Email Automation & Admin Portal Core

**Backend Tasks:**
- [ ] Email templates and automation
- [ ] Admin dashboard with metrics
- [ ] Client management interface
- [ ] Revenue reporting
- [ ] Bulk email functionality

---

## Quick Reference

### Common Imports
```python
# FastAPI
from fastapi import APIRouter, Depends, HTTPException, status

# SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

# Pydantic
from pydantic import BaseModel, Field, EmailStr, validator

# App
from app.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.models import User, Class, Enrollment
from app.schemas import UserCreate, UserResponse
from app.services import AuthService, EnrollmentService
```

### Dependency Injection Pattern
```python
# deps.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_token(token)
    user = await db.get(User, payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Usage in endpoint
@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

### Error Response Pattern
```python
from app.utils.exceptions import NotFoundError, ValidationError

@router.get("/classes/{class_id}")
async def get_class(class_id: UUID, db: AsyncSession = Depends(get_db)):
    class_ = await db.get(Class, class_id)
    if not class_:
        raise NotFoundError(f"Class {class_id} not found")
    return class_
```

---

## Context Session Rules

1. **Before work**: Check `.claude/tasks/context_session_x.md` for context
2. **During work**: Update context file with progress
3. **After work**: Document changes for handover

---

## Security Reminder

**CRITICAL**: Always validate user permissions before data access. Never expose internal system details in error messages. All PII must be encrypted at rest.

---

**Last Updated**: 2025-11-26 | **Milestone**: 4 - Email Automation & Admin Portal Core