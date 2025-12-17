# Client Requirements Analysis & Action Plan

## Summary of Client Responses
**Date:** 2025-11-29
**Status:** Requirements Confirmed
**Total Changes Required:** 47 items (18 critical, 15 high priority, 14 medium)

---

## 🔴 CRITICAL CHANGES (Must Do Before Launch)

### 1. Sibling Discount Per Family (Not Per Order)
**Current:** Discount applies only within same order
**Required:** Track sibling discount across family, even if registered at different times

**Impact:** Database schema + business logic changes
**Code Changes:**
- Add `family_id` or use `user_id` to track family
- Calculate sibling discount by counting ALL enrolled children for that family
- Recalculate if child cancels
- Migration needed to retroactively apply discounts

**Files Affected:**
- `app/services/pricing_service.py`
- `app/models/enrollment.py`
- `app/services/order_service.py`

**Priority:** 🔴 CRITICAL

---

### 2. Remove $25 Processing Fee
**Current:** Code assumes $25 processing fee on refunds
**Required:** No processing fee

**Code Changes:**
```python
# app/services/payment_service.py
# Remove processing fee deduction
refund_amount = enrollment.amount_paid  # No minus $25
```

**Priority:** 🔴 CRITICAL

---

### 3. Multi-Tenant Architecture (Add organization_id)
**Current:** Single-tenant
**Required:** Add `organization_id` to all tables NOW

**Impact:** MASSIVE - affects ALL tables
**Code Changes:**
- Add `organization_id` column to all models
- Update all queries to filter by organization
- Add organization management endpoints
- Update seed data

**Files Affected:** ALL model files

**Priority:** 🔴 CRITICAL (must do now before data grows)

---

### 4. Soft Deletes for All Tables
**Current:** Hard deletes
**Required:** Soft delete with separate deleted accounts list

**Code Changes:**
- Add `deleted_at` and `is_deleted` fields to all models
- Override delete methods to soft delete
- Create `/admin/deleted` endpoints to view deleted records
- Filter all queries to exclude deleted by default

**Files Affected:** All models, create `SoftDeleteMixin`

**Priority:** 🔴 CRITICAL

---

### 5. Prevent Duplicate Enrollments (Same Child + Class)
**Current:** Allowed
**Required:** Unique constraint

**Code Changes:**
```python
# app/models/enrollment.py
__table_args__ = (
    UniqueConstraint('child_id', 'class_id', 'organization_id',
                    name='unique_child_class_enrollment'),
)
```

**Priority:** 🔴 CRITICAL

---

### 6. Emergency Contact Limits
**Current:** Unlimited
**Required:** Min 1, Max 3, allow multiple primary

**Code Changes:**
- Validation in child creation endpoint
- Allow `is_primary=True` for multiple contacts

**Files Affected:**
- `api/v1/children.py`
- `app/schemas/child.py`

**Priority:** 🔴 CRITICAL

---

### 7. Waiver Acceptance Before Checkout
**Current:** Optional
**Required:** Block checkout if waivers not accepted

**Code Changes:**
```python
# In order creation
if not all_waivers_accepted(user_id, class_ids):
    raise BadRequestException("Please accept all required waivers first")
```

**Files Affected:**
- `app/services/order_service.py`
- `app/models/waiver.py`

**Priority:** 🔴 CRITICAL

---

### 8. Priority Waitlist System
**Current:** Simple waitlist
**Required:** Two-tier system
- Priority: Auto-promote with CC on file
- Regular: 12-hour window to claim spot

**Code Changes:**
- Add `waitlist_priority` field to enrollments
- Add `cc_on_file` requirement for priority
- Add auto-promotion job
- Add 12-hour expiration for regular waitlist

**Files Affected:**
- `app/models/enrollment.py`
- New: `app/services/waitlist_service.py`
- New: `app/tasks/waitlist_tasks.py`

**Priority:** 🔴 CRITICAL

---

### 9. Scholarship Expires with Class End Date
**Current:** Has `valid_until` field
**Required:** Auto-calculate from class end date

**Code Changes:**
```python
# app/models/discount.py
@property
def valid_until(self):
    if self.class_id:
        return Class.get(self.class_id).end_date
    return self._valid_until
```

**Priority:** 🔴 CRITICAL

---

### 10. Refund Approval Workflow
**Current:** Instant refunds
**Required:** All refunds need admin/owner approval

**Code Changes:**
- Add `refund_status` (pending, approved, rejected)
- Add `/admin/refunds/pending` endpoint
- Add `/admin/refunds/{id}/approve` endpoint
- Add refund search/filter

**Files Affected:**
- `app/models/payment.py`
- `api/v1/admin.py`

**Priority:** 🔴 CRITICAL

---

### 11. Remove Installment Restriction (2 only)
**Current:** Hardcoded to exactly 2 installments
**Required:** Allow 2 installments (but remove "exactly" check)

**Code Changes:**
```python
# app/services/installment_service.py line 79
# Remove this:
if num_installments != 2:
    raise BadRequestException("Exactly 2 installments required")

# Replace with:
if num_installments > 2:
    raise BadRequestException("Maximum 2 installments allowed")
```

**Priority:** 🔴 CRITICAL

---

### 12. Class Transfer = Account Credit (Not Refund)
**Current:** May refund difference
**Required:**
- Downgrade: Credit to account
- Upgrade: Charge CC on file

**Code Changes:**
- Add `account_credit` field to users
- Add `/users/{id}/credits` endpoint
- Modify transfer logic

**Files Affected:**
- `app/models/user.py`
- `app/services/enrollment_service.py`

**Priority:** 🔴 CRITICAL

---

### 13. school_id Not Required for Classes
**Current:** Required
**Required:** Optional (some classes not at schools)

**Code Changes:**
```python
# app/models/class_.py
school_id: Mapped[Optional[str]] = mapped_column(
    String(36), ForeignKey("schools.id"), nullable=True, index=True
)
```

**Priority:** 🔴 CRITICAL

---

### 14. Prevent Disposable Emails
**Current:** Any email accepted
**Required:** Block disposable email services

**Code Changes:**
```python
# app/utils/validators.py
DISPOSABLE_DOMAINS = ['tempmail.com', 'guerrillamail.com', ...]

def validate_email(email: str):
    domain = email.split('@')[1]
    if domain in DISPOSABLE_DOMAINS:
        raise BadRequestException("Disposable email addresses not allowed")
```

**Priority:** 🔴 CRITICAL

---

### 15. Password History Enforcement
**Current:** Optional
**Required:** Prevent reusing last X passwords

**Code Changes:**
- Already have `PasswordHistory` model
- Enforce in `change_password` method (already exists!)
- Just ensure it's active

**Status:** ✅ Already implemented! (line 204-211 in auth_service.py)

---

### 16. Age Check at Enrollment (Not Current)
**Current:** Unclear
**Required:** Age restrictions check age at enrollment date, not current age

**Code Changes:**
```python
# app/services/enrollment_service.py
def check_age_eligibility(child, class_):
    age_at_enrollment = calculate_age(child.date_of_birth, class_.start_date)
    if not (class_.min_age <= age_at_enrollment <= class_.max_age):
        raise BadRequestException(f"Child must be {class_.min_age}-{class_.max_age} at class start")
```

**Priority:** 🔴 CRITICAL

---

### 17. Medical Alert on Check-in Dashboard
**Current:** Medical info encrypted, no alerts
**Required:** Show visual indicator for children with medical conditions

**Code Changes:**
- Add `has_medical_alert` boolean field to Child
- Show icon/badge on check-in dashboard
- Don't show actual medical info (privacy)

**Files Affected:**
- `app/models/child.py`
- `api/v1/checkin.py`

**Priority:** 🔴 CRITICAL

---

### 18. 15-Day Refund Starts from Cancellation Request Date
**Current:** Unclear
**Required:** Calculate from cancellation request date (calendar days)

**Code Changes:**
```python
# app/services/enrollment_service.py
def calculate_refund(enrollment, cancellation_date):
    days_since_enrollment = (cancellation_date - enrollment.enrolled_at).days
    if days_since_enrollment <= 15:
        return enrollment.amount_paid  # Full refund, NO processing fee
    else:
        return calculate_prorated_credit(enrollment)
```

**Priority:** 🔴 CRITICAL

---

## 🟠 HIGH PRIORITY (Phase 4)

### 19. Staff Role = Coaches Only (Rename to COACH)
**Current:** STAFF role exists
**Required:** Rename to COACH throughout codebase

**Status:** ✅ Already done! Role enum has COACH, not STAFF

---

### 20. Admin Financial Viewing Limitations
**Current:** Admins see all financial data
**Required:** Limit what admins can see

**Need Clarification:** What specifically can't admins view?
- Revenue reports?
- Individual payment amounts?
- Refund history?

**Action:** Ask client for specifics

---

### 21. Promo Code: One Per Class
**Current:** One per user lifetime
**Required:** One per class per user

**Code Changes:**
```python
# app/models/discount.py
# Change unique constraint from user_id to user_id + class_id
# Track usage per class, not globally
```

**Priority:** 🟠 HIGH

---

### 22. Bulk Class Import
**Current:** Manual one-by-one
**Required:** CSV/Excel import

**Code Changes:**
- Create `/admin/classes/import` endpoint
- Accept CSV file
- Validate and create classes in batch

**Priority:** 🟠 HIGH

---

### 23. Duplicate Class Endpoint
**Current:** None
**Required:** Clone existing class

**Code Changes:**
```python
@router.post("/classes/{id}/duplicate")
async def duplicate_class(
    id: str,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    original = await Class.get_by_id(db, id)
    new_class = Class(**original.__dict__)
    new_class.id = str(uuid4())
    new_class.name = f"{original.name} (Copy)"
    # ... create
```

**Priority:** 🟠 HIGH

---

### 24. Bulk Refund Option
**Current:** One refund at a time
**Required:** Bulk refund when class cancelled

**Code Changes:**
- Add `/admin/classes/{id}/cancel-and-refund` endpoint
- Select all enrollments
- Create refund requests in batch

**Priority:** 🟠 HIGH

---

### 25. Email Notification 5 Days Before Class
**Current:** No auto-emails
**Required:** Reminder email 5 days before class start

**Code Changes:**
- Create Celery periodic task
- Query classes starting in 5 days
- Send reminder emails to all enrolled parents

**Files:**
- `app/tasks/email_tasks.py`

**Priority:** 🟠 HIGH

---

### 26. Revenue by Class (Not Just Program/School)
**Current:** Basic reporting
**Required:** Detailed revenue breakdown per class

**Code Changes:**
- Add `/admin/reports/revenue-by-class` endpoint
- Group payments by class
- Show revenue, enrollments, refunds per class

**Priority:** 🟠 HIGH

---

### 27. Class Categorization for Reports
**Current:** Only program/school
**Required:** Custom categories

**Code Changes:**
- Add `category` or `tags` field to Class
- Filter reports by category
- Examples: "Summer Camp", "After School", "Weekend"

**Priority:** 🟠 HIGH

---

### 28. New Registration Counts (7d, 30d, 90d)
**Current:** None
**Required:** Dashboard metrics

**Code Changes:**
```python
@router.get("/admin/metrics/registrations")
async def get_registration_metrics():
    return {
        "last_7_days": count_enrollments(days=7),
        "last_30_days": count_enrollments(days=30),
        "last_90_days": count_enrollments(days=90)
    }
```

**Priority:** 🟠 HIGH

---

### 29. Cancellation Counts (7d, 30d, 90d)
**Current:** None
**Required:** Dashboard metrics

**Priority:** 🟠 HIGH

---

### 30. Membership vs Short-term Counts
**Current:** All counted together
**Required:** Separate metrics

**Code Changes:**
- Filter by `class_type` in metrics
- Show "Memberships: X, Short-term: Y"

**Priority:** 🟠 HIGH

---

### 31. Outstanding Payments Report
**Current:** None
**Required:** Show all unpaid/failed payments

**Code Changes:**
```python
@router.get("/admin/reports/outstanding-payments")
async def get_outstanding_payments():
    return {
        "pending": payments with status=pending,
        "failed": payments with status=failed,
        "total_owed": sum of amounts
    }
```

**Priority:** 🟠 HIGH

---

### 32. Failed Payment: 3 Retries with Email Reminders
**Current:** No retry
**Required:** 3 automatic retries + email notifications

**Code Changes:**
- Celery task to retry failed payments
- Send email on each retry
- After 3 failures, notify admin

**Priority:** 🟠 HIGH

---

### 33. No Automatic Cancellation for Failed Installments
**Current:** May auto-cancel
**Required:** Grace period, admin decides

**Code Changes:**
- Remove auto-cancellation
- Notify admin after 3 failed attempts
- Add `/admin/enrollments/{id}/cancel-for-non-payment` endpoint

**Priority:** 🟠 HIGH

---

## 🟡 MEDIUM PRIORITY (Phase 5)

### 34. Filtering on All List Endpoints
**Current:** Limited filtering
**Required:** Comprehensive filters

**Examples:**
- Classes: by program, school, date range, age range, price range
- Orders: by status, date range, user, amount
- Enrollments: by status, class, child, date

**Priority:** 🟡 MEDIUM

---

### 35. Child Deletion by Admin/Owner Only
**Current:** Parents can delete
**Required:** Only admin/owner

**Code Changes:**
```python
@router.delete("/children/{id}")
async def delete_child(
    current_admin: User = Depends(get_current_admin)  # Changed from get_current_user
):
    # Apply billing rules on deletion
```

**Priority:** 🟡 MEDIUM

---

### 36-47: Additional Medium Priority Items
- Email verification removed (already no verification)
- US phone number validation
- Scholarship usage reports
- Automated retry for webhook failures
- Push notification infrastructure
- Attendance tracking
- Coach assignments
- Announcements
- Event management
- Equipment (not planned - skip)

---

## 📋 Implementation Roadmap

### Week 1: Critical Database Changes
- [ ] Add `organization_id` to all tables
- [ ] Implement soft deletes
- [ ] Add family-based sibling discount tracking
- [ ] Add unique constraint for child-class enrollments
- [ ] Make school_id optional for classes
- [ ] Run migrations

### Week 2: Core Business Logic Fixes
- [ ] Remove $25 processing fee
- [ ] Fix sibling discount calculation (per family)
- [ ] Implement refund approval workflow
- [ ] Add account credit system
- [ ] Fix promo code (one per class)
- [ ] Implement waiver enforcement

### Week 3: Waitlist & Payments
- [ ] Build priority waitlist system
- [ ] Add 12-hour claim window
- [ ] Fix installment restrictions
- [ ] Add payment retry logic
- [ ] Scholarship auto-expiration

### Week 4: Admin Features & Reporting
- [ ] Bulk class import
- [ ] Duplicate class endpoint
- [ ] Revenue reports by class
- [ ] Registration/cancellation metrics
- [ ] Outstanding payments report
- [ ] Refund search

### Week 5: Email Notifications
- [ ] Class reminder (5 days before)
- [ ] Payment receipts
- [ ] Enrollment confirmations
- [ ] Failed payment notices
- [ ] Waitlist notifications

### Week 6: Polish & Testing
- [ ] Emergency contact limits
- [ ] Medical alert indicators
- [ ] Age at enrollment check
- [ ] Disposable email blocking
- [ ] Comprehensive testing

---

## 🚨 Blocking Issues (Need Client Clarification)

### 1. Admin Financial Viewing Limitations
**Question:** What specifically can admins NOT view?
**Impact:** Affects permission design

### 2. Sibling Discount When First Child Cancels
**Question:** "Can the discount be taken away if they cancel the first child?"
**Answer Given:** Recalculate sibling discount
**Clarification Needed:** Does this mean:
- Child 2's price increases immediately?
- Or discount removed on next billing cycle?
- Or parent must pay difference?

### 3. Multiple Primary Emergency Contacts
**Question:** Client said "Yes" to multiple primary contacts
**Clarification:** Is there a use case for this? Usually only one primary.

---

## 💰 Estimated Effort

**Total Development Time:** 6-8 weeks (1 developer)

**Breakdown:**
- Critical Changes: 3 weeks
- High Priority: 2 weeks
- Medium Priority: 2 weeks
- Testing & Bug Fixes: 1 week

**Cost Estimate:** $15,000 - $25,000 (based on hourly rate)

---

## Next Steps

1. **Review this document with client** - Confirm all interpretations are correct
2. **Clarify blocking issues** - Get answers to open questions
3. **Prioritize roadmap** - Adjust timeline based on client needs
4. **Create detailed tickets** - Break down each item into tasks
5. **Start development** - Begin with Week 1 critical changes

---

**Last Updated:** 2025-11-29
**Prepared By:** Development Team
**Status:** Awaiting Client Final Approval
