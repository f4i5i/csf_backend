# Milestone 3: Payment Integration (Stripe) + Installments

## Overview
Implement complete payment processing with Stripe, including one-time payments, subscriptions, and installment plans. Build the enrollment flow that ties children to classes with payment.

---

## Phase 1: Core Payment Models

### 1.1 Enrollment Model (`app/models/enrollment.py`)
```python
class EnrollmentStatus(str, Enum):
    PENDING = "pending"          # Awaiting payment
    ACTIVE = "active"            # Paid and enrolled
    CANCELLED = "cancelled"      # Cancelled by user
    COMPLETED = "completed"      # Class finished
    WAITLISTED = "waitlisted"    # On waitlist

class Enrollment:
    id: str (UUID)
    child_id: str (FK -> children)
    class_id: str (FK -> classes)
    user_id: str (FK -> users)  # Parent who enrolled
    status: EnrollmentStatus
    enrolled_at: datetime
    cancelled_at: datetime (nullable)
    cancellation_reason: str (nullable)
    # Pricing snapshot at enrollment time
    base_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
```

### 1.2 Order Models (`app/models/order.py`)
```python
class OrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class Order:
    id: str (UUID)
    user_id: str (FK -> users)
    status: OrderStatus
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    # Stripe
    stripe_payment_intent_id: str (nullable)
    stripe_customer_id: str (nullable)
    # Timestamps
    created_at, updated_at, paid_at

class OrderLineItem:
    id: str (UUID)
    order_id: str (FK -> orders)
    enrollment_id: str (FK -> enrollments)
    description: str
    quantity: int (default 1)
    unit_price: Decimal
    discount_code_id: str (nullable, FK -> discount_codes)
    discount_amount: Decimal
    line_total: Decimal
```

### 1.3 Payment Models (`app/models/payment.py`)
```python
class PaymentType(str, Enum):
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    INSTALLMENT = "installment"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class Payment:
    id: str (UUID)
    order_id: str (FK -> orders)
    user_id: str (FK -> users)
    payment_type: PaymentType
    status: PaymentStatus
    amount: Decimal
    currency: str (default "usd")
    # Stripe references
    stripe_payment_intent_id: str (nullable)
    stripe_charge_id: str (nullable)
    stripe_subscription_id: str (nullable)
    # Metadata
    failure_reason: str (nullable)
    refund_amount: Decimal (default 0)
    paid_at: datetime (nullable)

class InstallmentPlan:
    id: str (UUID)
    order_id: str (FK -> orders)
    user_id: str (FK -> users)
    total_amount: Decimal
    num_installments: int (2-4)
    installment_amount: Decimal
    frequency: str ("weekly", "biweekly", "monthly")
    start_date: date
    stripe_subscription_id: str (nullable)
    status: str ("active", "completed", "cancelled", "defaulted")

class InstallmentPayment:
    id: str (UUID)
    installment_plan_id: str (FK -> installment_plans)
    payment_id: str (FK -> payments, nullable)
    due_date: date
    amount: Decimal
    status: str ("pending", "paid", "failed", "skipped")
    paid_at: datetime (nullable)
    attempt_count: int (default 0)
```

### 1.4 Discount Models (`app/models/discount.py`)
```python
class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"

class DiscountCode:
    id: str (UUID)
    code: str (unique, uppercase)
    description: str
    discount_type: DiscountType
    discount_value: Decimal  # % or fixed amount
    # Validity
    valid_from: datetime
    valid_until: datetime (nullable)
    max_uses: int (nullable)  # null = unlimited
    current_uses: int (default 0)
    # Restrictions
    min_order_amount: Decimal (nullable)
    applies_to_program_id: str (nullable)
    applies_to_class_id: str (nullable)
    is_active: bool
    created_by_id: str (FK -> users)

class Scholarship:
    id: str (UUID)
    user_id: str (FK -> users)
    child_id: str (FK -> children, nullable)
    scholarship_type: str
    discount_percentage: Decimal
    approved_by_id: str (FK -> users)
    valid_until: date (nullable)
    notes: str (nullable)
    is_active: bool
```

---

## Phase 2: Stripe Service Integration

### 2.1 Stripe Service (`app/services/stripe_service.py`)
```python
class StripeService:
    # Customer Management
    async def get_or_create_customer(user: User) -> str  # stripe_customer_id
    async def update_customer(user: User) -> None

    # Payment Methods
    async def create_setup_intent(customer_id: str) -> SetupIntent
    async def list_payment_methods(customer_id: str) -> list[PaymentMethod]
    async def detach_payment_method(payment_method_id: str) -> None

    # One-Time Payments
    async def create_payment_intent(
        amount: int,  # cents
        customer_id: str,
        payment_method_id: str = None,
        metadata: dict = None
    ) -> PaymentIntent

    # Subscriptions (for memberships)
    async def create_subscription(
        customer_id: str,
        price_id: str,
        payment_method_id: str
    ) -> Subscription
    async def cancel_subscription(subscription_id: str) -> Subscription

    # Installments (using subscription with fixed count)
    async def create_installment_subscription(
        customer_id: str,
        amount: int,  # per installment in cents
        num_installments: int,
        interval: str  # "week", "month"
    ) -> Subscription

    # Refunds
    async def create_refund(
        payment_intent_id: str,
        amount: int = None  # null = full refund
    ) -> Refund

    # Webhook
    def construct_event(payload: bytes, sig_header: str) -> Event
```

### 2.2 Environment Variables
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Phase 3: Pricing Service

### 3.1 Pricing Service (`app/services/pricing_service.py`)
```python
class PricingService:
    # Sibling discounts (auto-applied)
    SIBLING_DISCOUNTS = {
        2: Decimal("0.25"),  # 2nd child: 25% off
        3: Decimal("0.35"),  # 3rd child: 35% off
        4: Decimal("0.45"),  # 4th+ child: 45% off
    }

    async def calculate_order(
        user_id: str,
        items: list[OrderItemInput],  # child_id, class_id
        discount_code: str = None
    ) -> OrderCalculation:
        """
        Returns:
        - line_items with individual pricing
        - sibling_discount applied
        - promo_discount applied
        - subtotal, discount_total, total
        """

    async def validate_discount_code(
        code: str,
        order_amount: Decimal,
        program_id: str = None,
        class_id: str = None
    ) -> DiscountValidation

    async def calculate_installment_schedule(
        total: Decimal,
        num_installments: int,
        start_date: date,
        frequency: str
    ) -> list[InstallmentScheduleItem]
```

---

## Phase 4: API Endpoints

### 4.1 Payment Methods (`api/v1/payments.py`)
```
POST /api/v1/payments/setup-intent
  - Create Stripe SetupIntent to save card
  - Returns: client_secret for Stripe.js

GET /api/v1/payments/methods
  - List user's saved payment methods

DELETE /api/v1/payments/methods/{id}
  - Remove a saved payment method
```

### 4.2 Orders (`api/v1/orders.py`)
```
POST /api/v1/orders/calculate
  - Input: list of {child_id, class_id}, discount_code (optional)
  - Returns: order preview with pricing breakdown

POST /api/v1/orders
  - Create order and process payment
  - Input: items, payment_method_id, payment_type, discount_code
  - Handles: one-time, subscription, installment
  - Returns: order with enrollment IDs

GET /api/v1/orders/{id}
  - Get order details

GET /api/v1/orders
  - List user's orders (paginated)
```

### 4.3 Enrollments (`api/v1/enrollments.py`)
```
GET /api/v1/enrollments
  - List user's enrollments

GET /api/v1/enrollments/{id}
  - Get enrollment details

PUT /api/v1/enrollments/{id}/cancel
  - Cancel enrollment (applies 15-day policy)
  - Returns: refund amount if applicable

PUT /api/v1/enrollments/{id}/transfer
  - Transfer to different class
  - Input: new_class_id
```

### 4.4 Discounts (`api/v1/discounts.py`)
```
POST /api/v1/discounts/validate
  - Validate a discount code
  - Input: code, order_amount, program_id (optional)
  - Returns: discount details or error

# Admin endpoints
POST /api/v1/discounts (admin)
GET /api/v1/discounts (admin)
PUT /api/v1/discounts/{id} (admin)
DELETE /api/v1/discounts/{id} (admin)
```

### 4.5 Webhooks (`api/v1/webhooks.py`)
```
POST /api/v1/webhooks/stripe
  - Handle all Stripe webhook events
  - Events:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - invoice.payment_succeeded
    - invoice.payment_failed
    - customer.subscription.updated
    - customer.subscription.deleted
    - charge.refunded
```

---

## Phase 5: Database Migration

### Tables to Create
1. `enrollments`
2. `orders`
3. `order_line_items`
4. `payments`
5. `installment_plans`
6. `installment_payments`
7. `discount_codes`
8. `scholarships`

### Indexes
- `enrollments`: child_id, class_id, user_id, status
- `orders`: user_id, status, stripe_payment_intent_id
- `payments`: order_id, user_id, stripe_payment_intent_id
- `discount_codes`: code (unique), is_active

---

## Phase 6: Testing

### Unit Tests
- `test_pricing_service.py` - sibling discounts, promo codes
- `test_stripe_service.py` - mock Stripe API calls

### Integration Tests
- `test_orders.py` - order calculation, creation
- `test_payments.py` - payment processing flows
- `test_enrollments.py` - enrollment lifecycle
- `test_discounts.py` - discount validation
- `test_webhooks.py` - webhook event handling

### Test Scenarios
1. Single child enrollment (one-time payment)
2. Multiple children enrollment (sibling discount)
3. Enrollment with promo code
4. Installment plan creation and payments
5. Subscription creation
6. Cancellation with refund (within 15 days)
7. Cancellation without refund (after 15 days)
8. Payment failure handling
9. Webhook event processing

---

## Implementation Order

1. **Phase 1**: Models (enrollment, order, payment, discount)
2. **Phase 2**: Stripe service (basic integration)
3. **Phase 3**: Pricing service (calculations)
4. **Phase 4a**: Payment methods API
5. **Phase 4b**: Orders API (calculate + create)
6. **Phase 4c**: Enrollments API
7. **Phase 4d**: Discounts API
8. **Phase 4e**: Webhooks
9. **Phase 5**: Migration
10. **Phase 6**: Tests

---

## Success Criteria

- [ ] User can save payment methods
- [ ] User can calculate order with discounts
- [ ] User can complete one-time payment enrollment
- [ ] User can set up installment plan
- [ ] Sibling discounts auto-apply correctly
- [ ] Promo codes validate and apply
- [ ] Cancellation policy enforced (15-day rule)
- [ ] Stripe webhooks update payment status
- [ ] All tests passing

---

## Dependencies to Add

```bash
uv add stripe
```

---

**Estimated Effort**: 4-6 development sessions
**Priority**: High (core business functionality)
