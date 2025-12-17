# Current System Architecture - As Implemented

This document describes the **current implementation** based on the existing codebase. Compare this with client requirements to identify any gaps or needed changes.

---

## Current User Roles & Access

### Implemented Roles
```python
class Role(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    COACH = "coach"
    PARENT = "parent"
```

### Current Registration & Authentication

#### Public Endpoints (No Auth Required)
```
POST /api/v1/auth/register          # ✅ Parents can self-register
POST /api/v1/auth/token             # ✅ All users login here (Swagger OAuth2)
POST /api/v1/auth/login             # ✅ All users login here (JSON)
POST /api/v1/auth/google            # ✅ Google OAuth for all users
POST /api/v1/auth/refresh           # ✅ Refresh access token
POST /api/v1/auth/logout            # ✅ Logout
```

#### Current Registration Flow
```
Parent self-registration:
1. POST /api/v1/auth/register
   - Input: email, password, first_name, last_name, phone
   - Auto-assigned role: PARENT
   - Status: is_active=True, is_verified=False

2. User can login immediately (no email verification enforced yet)

3. Parent can add children and enroll in classes
```

#### Current Login Flow
```
All users (Owner, Admin, Coach, Parent):
1. POST /api/v1/auth/login
   - Input: email, password
   - Output: access_token, refresh_token

2. Same endpoint for all roles
3. Frontend redirects based on role (not enforced by backend)
```

### Current Admin User Creation

**NOT IMPLEMENTED YET** - There is no endpoint for admins to create users.

**Available:**
- `AuthService.create_admin_user()` method exists (line 134 in auth_service.py)
- But no API endpoint exposed

**Gap:** Need to create endpoints:
```
POST /api/v1/admin/users          # Create user (admin/owner only)
PUT  /api/v1/admin/users/{id}     # Update user
DELETE /api/v1/admin/users/{id}   # Delete user
```

---

## Current Data Relationships

### User → Child (One-to-Many)
```python
# app/models/user.py
children: Mapped[List["Child"]] = relationship(
    "Child", back_populates="user", cascade="all, delete-orphan"
)

# One parent can have multiple children
# One child belongs to ONE parent only (current limitation)
```

**Current Limitation:**
- ❌ Cannot have multiple parents per child (e.g., divorced parents)
- ✅ Can add multiple emergency contacts per child

### Child → EmergencyContact (One-to-Many)
```python
# app/models/child.py
emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(
    "EmergencyContact", back_populates="child", cascade="all, delete-orphan"
)
```

### Program → Class (One-to-Many)
```python
# app/models/program.py
classes: Mapped[List["Class"]] = relationship("Class", back_populates="program")
```

### School → Class (One-to-Many)
```python
# app/models/program.py (School model)
classes: Mapped[List["Class"]] = relationship("Class", back_populates="school")
```

### Area → School (One-to-Many)
```python
# app/models/program.py (Area model)
schools: Mapped[List["School"]] = relationship("School", back_populates="area")
```

### Current Hierarchy
```
Area
  └── School (Many schools per area)
       └── Class (Many classes per school)
            └── Enrollment (Many enrollments per class)

Program
  └── Class (Many classes per program)
       └── Enrollment
```

**Note:** One Class belongs to ONE Program and ONE School

---

## Current Enrollment Flow

### As Implemented
```
1. Parent registers                 → POST /api/v1/auth/register
2. Parent logs in                    → POST /api/v1/auth/login
3. Parent adds child                 → POST /api/v1/children
4. Parent adds emergency contacts    → Included in child creation
5. Parent browses classes            → GET /api/v1/classes
6. Parent creates order              → POST /api/v1/orders/calculate (preview)
                                     → POST /api/v1/orders (create)
7. Parent pays                       → POST /api/v1/payments/payment-intent
                                     → or POST /api/v1/payments/subscription
                                     → or POST /api/v1/installments (installment plan)
8. Payment webhook processes         → POST /api/v1/webhooks/stripe
9. Enrollment activated              → Automatic via webhook
```

### Current Order Structure
```python
Order
  └── OrderLineItem (one per class enrollment)
       └── Enrollment (linked to child + class)

# One order can have multiple line items
# Each line item = one child in one class
```

---

## Current Payment Types

### One-Time Payment
```
POST /api/v1/payments/payment-intent
- Full amount paid upfront
- Order status: "paid"
- Enrollment status: "active"
```

### Subscription (Recurring)
```
POST /api/v1/payments/subscription
- Recurring monthly billing
- Stripe subscription created
- Order status: "paid"
- Enrollment status: "active"
```

### Installment Plans
```
POST /api/v1/installments
- Split into 2-12 payments
- Frequencies: weekly, biweekly, monthly
- Stripe subscription with fixed count
- Order status: "partially_paid"
- Enrollment status: "active"
```

**Current Limitation:**
```python
# In installment_service.py line 79
if num_installments != 2:
    raise BadRequestException("Exactly 2 installments required (no more, no less)")
```
- ❌ Currently hardcoded to EXACTLY 2 installments
- Need to remove this restriction if client wants 3-12 installments

---

## Current Discount System

### Sibling Discounts
**NOT IMPLEMENTED YET** - The logic exists in comments but not active.

**Available in pricing_service.py:**
```python
SIBLING_DISCOUNTS = {
    2: Decimal("0.25"),  # 2nd child: 25% off
    3: Decimal("0.35"),  # 3rd child: 35% off
    4: Decimal("0.45"),  # 4th+ child: 45% off
}
```

**Gap:** Need to implement auto-application of sibling discounts in order creation.

### Promo Codes
```
GET  /api/v1/discounts              # List discount codes
POST /api/v1/discounts              # Create discount code (admin)
POST /api/v1/discounts/validate     # Validate code
```

**Current Fields:**
- code: string
- discount_type: PERCENTAGE | FIXED_AMOUNT
- discount_value: Decimal
- min_order_amount: Decimal
- max_uses: int
- current_uses: int
- valid_from / valid_until: dates
- applies_to_program_id: optional
- applies_to_class_id: optional

---

## Current Waiver System

### Waiver Types
```python
class WaiverType(str, enum.Enum):
    MEDICAL_RELEASE = "medical_release"
    LIABILITY = "liability"
    PHOTO_RELEASE = "photo_release"
    CANCELLATION_POLICY = "cancellation_policy"
```

### Waiver Acceptance Flow
```
1. GET /api/v1/waivers/templates      # Get all waiver templates
2. GET /api/v1/waivers/required/{class_id}  # Get required waivers for class
3. POST /api/v1/waivers/accept        # Accept waivers
```

**Current Implementation:**
- Waivers are global (apply to all) OR program-specific OR school-specific
- Parent accepts waivers (recorded with IP, user agent, timestamp)
- Version tracking for legal compliance
- Rich text content (HTML)

**Gap:** Waiver acceptance is optional - not enforced before enrollment.

---

## Current Role-Based Access Control

### Endpoint Protection Examples

#### Parent Endpoints
```python
@router.get("/children/{id}")
async def get_child(
    current_user: User = Depends(get_current_user)
):
    # Any authenticated user can access
    # No role check - relies on ownership check
```

#### Admin Endpoints
```python
@router.get("/admin/clients")
async def list_clients(
    current_admin: User = Depends(get_current_admin)
):
    # Requires ADMIN or OWNER role
```

#### Owner Endpoints
```python
@router.post("/admin/some-critical-action")
async def critical_action(
    current_owner: User = Depends(get_current_owner)
):
    # Requires OWNER role only
```

#### Coach/Staff Endpoints
```python
@router.get("/classes/{id}/roster")
async def get_roster(
    current_staff: User = Depends(get_current_staff)
):
    # Requires COACH, ADMIN, or OWNER role
```

#### Parent or Admin Endpoints (Financial)
```python
@router.get("/orders")
async def list_orders(
    current_user: User = Depends(get_current_parent_or_admin)
):
    # Only PARENT, ADMIN, or OWNER
    # Coaches excluded from financial data
```

---

## Current Cancellation & Refund

### Enrollment Cancellation
```
PUT /api/v1/enrollments/{id}/cancel
- Sets status to "cancelled"
- Cancels any related installment plans
- Cancels Stripe subscriptions
```

**Current Limitation:**
- No 15-day refund policy implemented
- No pro-rated refunds
- No automatic refund processing

**Gap:** Need to implement:
1. Calculate days since enrollment
2. Apply 15-day refund rule
3. Process refunds via Stripe
4. Issue pro-rated credits for future

---

## Current Admin Functions

### Implemented
```
GET  /api/v1/admin/dashboard/metrics     # Dashboard statistics
GET  /api/v1/admin/clients               # List all clients (parents)
GET  /api/v1/admin/clients/{id}          # Client profile
PUT  /api/v1/admin/clients/{id}          # Update client
GET  /api/v1/admin/finance/revenue       # Revenue reports
POST /api/v1/admin/export/csv            # Export data
POST /api/v1/admin/bulk/email            # Bulk email
```

### Not Yet Implemented
- ❌ Create user accounts
- ❌ Delete user accounts
- ❌ Reset user passwords
- ❌ Deactivate/activate users
- ❌ Manual enrollment creation (without payment)
- ❌ Refund processing
- ❌ Waitlist management

---

## Current Communication & Notifications

### Email Integration
- **SendGrid** - Transactional emails (configured but emails not sent yet)
- **Mailchimp** - Marketing emails (configured but not integrated)

### SMS Integration
- **Twilio** - Configured but not implemented

**Gap:** No automatic emails are sent currently. Need to implement:
- Welcome email after registration
- Enrollment confirmation
- Payment receipts
- Class reminders
- etc.

---

## Current Data Encryption

### Encrypted Fields
```python
# app/models/child.py
medical_info: Mapped[Optional[str]] = mapped_column(
    Text, nullable=True
)  # Encrypted via encrypt_pii()

insurance_info: Mapped[Optional[str]] = mapped_column(
    Text, nullable=True
)  # Encrypted via encrypt_pii()
```

**Encryption Method:** Fernet (symmetric encryption)
**Key Location:** `.env` - `ENCRYPTION_KEY`

---

## Gaps & Missing Features

Based on code review, here are features mentioned in CLAUDE.md but not fully implemented:

### High Priority Gaps
1. ❌ Admin user creation endpoints
2. ❌ Automatic sibling discount application
3. ❌ Waiver enforcement (before enrollment)
4. ❌ 15-day cancellation/refund policy
5. ❌ Email notifications (welcome, receipts, reminders)
6. ❌ Installment plans limited to 2 payments only

### Medium Priority Gaps
7. ❌ Waitlist auto-promotion
8. ❌ Class transfer functionality
9. ❌ Coach assignment to classes
10. ❌ Attendance tracking UI/API
11. ❌ Photo upload and management
12. ❌ Announcements and events

### Low Priority Gaps
13. ❌ Badges and achievements
14. ❌ Check-in system
15. ❌ SMS notifications
16. ❌ Advanced reporting/analytics
17. ❌ GDPR data export/deletion

---

## Database Schema Status

### Tables Created ✅
- users, children, emergency_contacts
- programs, areas, schools, classes
- enrollments, orders, order_line_items
- payments, installment_plans, installment_payments
- waiver_templates, waiver_acceptances
- discount_codes, scholarships
- password_history

### Tables Partially Implemented
- attendances (model exists, limited endpoints)
- checkins (model exists, limited endpoints)
- events (model exists, limited endpoints)
- photos, photo_categories (models exist, limited endpoints)
- badges, student_badges (models exist, limited endpoints)
- announcements, announcement_attachments, announcement_targets (models exist)

### Indexes Status
- ✅ 20 indexes just added on foreign keys
- ✅ Unique constraints on critical fields
- ✅ Composite indexes where needed

---

## Next Steps for Client

1. **Review this document** - Understand what's already built
2. **Fill out questionnaire** - Clarify business requirements
3. **Identify gaps** - What needs to change vs what's correct
4. **Prioritize features** - What's critical for launch

---

**Last Updated:** 2025-11-29
**Status:** Phase 3 (Payment Integration) - In Progress
