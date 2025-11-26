# Clarification Questions & Verification Checklist

Hey there! I have some questions to make sure everything is perfectly aligned with your requirements. Take your time going through these - they're designed to catch any edge cases or misunderstandings early.

---

## 1. Authentication & Authorization (RBAC)

### Role-Based Access Control

**Q1.1:** I see we have 4 roles defined: `PARENT`, `STAFF`, `ADMIN`, and `OWNER`. Can you confirm:
- **Parents** can only see/manage their own children, orders, and enrollments, right?
- **Staff** can view all data but can't modify financial records or create discount codes?
- **Admins** have full CRUD access to everything except maybe deleting users?
- **Owners** are the super-admins who can do absolutely everything?

**Q1.2:** For the payment endpoints - who should be able to issue refunds?
- Currently, only ADMIN and OWNER can create refunds via `/api/v1/payments/refund`
- Should STAFF also have this permission? Or is it intentionally restricted?

**Q1.3:** Class creation is admin-only. What about class updates and deletions?
- Should parents be able to see all classes (public catalog)?
- Should staff be able to edit class schedules/capacity?
- Who can cancel/close a class?

**Q1.4:** Scholarship management - I've made it admin-only. Is this correct?
- Should staff be able to view scholarship status?
- Should parents see if they have a scholarship applied (I think yes, but want to confirm)?

**Q1.5:** Emergency contacts - currently parents can add/edit emergency contacts for their children. Should staff also be able to update emergency contacts in case of changes?

---

## 2. Business Logic & Rules

### Discount & Pricing

**Q2.1:** Sibling discount calculation - I've implemented it as:
- 2nd child: 25% off
- 3rd child: 35% off
- 4th+ child: 45% off
- The **highest-priced** item gets no discount

Is this the exact business rule? Some organizations do it differently:
- Apply discount to **all** items except the first child
- Apply discount to **lowest-priced** items
- Apply discount **per family, not per order**

Which approach matches your business requirements?

**Q2.2:** Discount stacking order - currently it's:
1. First: Sibling discounts
2. Second: Scholarship discounts
3. Third: Promo code discounts

So if a family gets 25% sibling discount, then 50% scholarship, then uses a "SAVE20" promo code, the calculation is:
```
$200 → $150 (sibling) → $75 (scholarship) → $55 (promo)
```

Is this the correct order? Should promo codes apply to the original price instead?

**Q2.3:** Minimum order amounts for promo codes:
- If a code requires minimum $100 order, does that apply BEFORE or AFTER sibling/scholarship discounts?
- Example: Order is $150, after discounts it's $80. Does the "min $100" code still work?

**Q2.4:** Promo code usage limits:
- `max_uses_per_user` is set to 1 by default
- Does this mean 1 per order, or 1 per lifetime?
- Can a parent use "SUMMER25" for multiple children in the same order?

### Enrollment & Cancellation

**Q2.5:** The 15-day refund policy with $25 processing fee:
- Does the 15-day period start from:
  - Order payment date?
  - Enrollment date?
  - Class start date?
- Is it 15 calendar days or 15 business days?

**Q2.6:** If a parent enrolls 3 kids and wants to cancel just 1:
- Do they get a pro-rated refund?
- Does the sibling discount recalculate for the remaining kids?
- Does the $25 processing fee apply per child or per cancellation request?

**Q2.7:** Class transfers:
- If a child transfers from a $200 class to a $150 class, do they get $50 refund?
- If transferring to a $250 class, do they pay the $50 difference?
- Is there a limit on how many times a child can transfer?
- Are there any transfer fees?

**Q2.8:** Waitlist functionality:
- I see the `WAITLISTED` status in enrollments
- Is there automatic promotion from waitlist when spots open up?
- Do parents get notified when a spot opens?
- Is there a waitlist expiration (e.g., 48 hours to accept)?

### Payment & Installments

**Q2.9:** Installment plans:
- Who decides the installment frequency (weekly/biweekly/monthly)?
- Is there a minimum order amount for installments?
- Are there any fees for using installment plans?
- What happens if an installment payment fails? Immediate cancellation or grace period?

**Q2.10:** Partial refunds:
- Currently admins can issue partial refunds
- What's the business rule for partial refunds?
- Should there be a minimum refund amount?
- Can multiple partial refunds be issued for the same payment?

**Q2.11:** Failed payments:
- If a payment fails, how many retry attempts?
- Is there a grace period before enrollment is cancelled?
- Do parents get notified immediately?

---

## 3. API Payloads & Validation

### Required Fields

**Q3.1:** Child registration - which fields are truly optional?
- `medical_conditions` - can be empty if `has_no_medical_conditions` is true
- `after_school_program` - only if `after_school_attendance` is true
- `health_insurance_number` - is this optional or required?
- `how_heard_other_text` - only if `how_heard_about_us` is "other"

Are these validation rules correct?

**Q3.2:** Emergency contacts - I require at least 1 contact, and exactly 1 must be marked as `is_primary`. Is this right?
- Should we allow 0 emergency contacts?
- Can there be multiple primary contacts?
- What's the maximum number of emergency contacts per child?

**Q3.3:** Order creation - currently requires:
- At least 1 item (child + class pair)
- Both `child_id` and `class_id` must exist
- Parent must own the child

Should staff/admin be able to create orders for any child, or only their own?

**Q3.4:** Class creation - these fields are required:
- `name`, `program_id`, `school_id`, `class_type`, `start_date`, `price`

Are `weekdays` and `start_time`/`end_time` truly required? What about membership classes that don't have fixed schedules?

### Field Validation

**Q3.5:** Phone number format:
- Currently accepting any string format ("555-0123", "(555) 012-3456", etc.)
- Should we enforce a specific format?
- Should we validate US phone numbers only or international too?

**Q3.6:** Email validation:
- Using standard email regex
- Should we verify email deliverability (DNS check)?
- Should we prevent disposable email addresses?

**Q3.7:** Date validations:
- Child's `date_of_birth` - should we have min/max age limits?
- Class `start_date` - can it be in the past (for existing classes)?
- Scholarship `valid_until` - can it be in the past (for expired scholarships)?

**Q3.8:** Price validations:
- Minimum class price?
- Maximum class price?
- Can prices be $0 (free classes)?
- How many decimal places? Currently using `Decimal` with 2 places.

---

## 4. Database & Data Integrity

### Schema Design

**Q4.1:** Soft deletes vs hard deletes:
- Currently no soft delete functionality
- Should we keep deleted records for audit trail?
- Which tables need soft deletes? (Users, Children, Classes, Orders?)

**Q4.2:** Cascading deletes:
- If a child is deleted, what happens to:
  - Their enrollments?
  - Their emergency contacts?
  - Order line items?
- If a class is deleted:
  - Active enrollments?
  - Pending orders?

**Q4.3:** Unique constraints:
- User email must be unique ✓
- Discount codes must be unique ✓
- Can a child be enrolled in the same class twice? (Currently allowed - is this right?)
- Can the same emergency contact be added twice for a child? (Currently allowed)

**Q4.4:** Indexes:
- I've added indexes on commonly queried fields
- Are there specific reports/queries you run frequently that need optimization?
- Expected data volume? (helps determine if more indexes are needed)

### Migrations

**Q4.5:** The Milestone 3 migration hasn't been run yet. Before running:
- Is the production database backed up?
- Should we run it in a maintenance window?
- Are there any existing orders/enrollments in production that need special handling?

---

## 5. Security Concerns

### Data Encryption

**Q5.1:** PII encryption - currently encrypting:
- `medical_conditions`
- `health_insurance_number`

Should we also encrypt:
- Emergency contact phone numbers?
- Emergency contact emails?
- Child's date of birth?
- Payment method details (Stripe handles this, but want to confirm)?

**Q5.2:** Encryption key rotation:
- Is there a plan for periodic key rotation?
- Should we implement versioned encryption (so we can decrypt old data during rotation)?

### Authentication & Tokens

**Q5.3:** JWT token expiration:
- Access token: 30 minutes
- Refresh token: 7 days

Are these durations appropriate for your use case? Some considerations:
- Shorter = more secure but more frequent re-auth
- Longer = better UX but higher security risk

**Q5.4:** Password requirements:
- Minimum 8 characters
- Must have: uppercase, lowercase, number

Should we also require:
- Special characters?
- Maximum length limit?
- Password history (prevent reuse)?
- Password expiration after X days?

**Q5.5:** Account security:
- Should we implement 2FA for payments?
- Should we implement 2FA for admin accounts?
- Should we lock accounts after X failed login attempts?
- Should we require email verification on signup?

### Payment Security

**Q5.6:** Stripe webhooks:
- Currently validating webhook signatures ✓
- Should we also validate the webhook source IP?
- Should we implement idempotency keys for payment operations?

**Q5.7:** Refund authorization:
- Should refunds above a certain amount require owner approval?
- Should we audit log all refund operations?
- Should we rate-limit refund endpoints?

---

## 6. User Experience & Workflows

### Parent Workflow

**Q6.1:** Registration flow:
1. Parent registers account
2. Parent adds children
3. Parent browses classes
4. Parent adds to cart (order creation)
5. Parent pays
6. Enrollments activated

Is this the intended flow? Should we add:
- Email verification step?
- Waiver acceptance before checkout?
- Payment method saved before checkout?

**Q6.2:** Multi-child enrollment:
- Can parents add multiple children to multiple classes in one order? (Currently yes)
- Should there be a "cart" concept or is each order atomic?
- Can they mix different class types (short-term + membership)?

### Admin Workflow

**Q6.3:** Class management:
- How do admins typically create classes?
- Bulk import from spreadsheet?
- Manual one-by-one?
- Copy from previous season?

Should we add a "duplicate class" endpoint?

**Q6.4:** Reporting needs:
- What reports do you need?
- Revenue by program/school/date?
- Enrollment counts?
- Scholarship usage?
- Outstanding payments?

Should I create dedicated reporting endpoints?

**Q6.5:** Notification triggers:
- When should parents get emails?
  - Order confirmation?
  - Payment success/failure?
  - Enrollment activated?
  - Class reminder (X days before start)?
  - Cancellation confirmation?

Currently, email service is integrated but no auto-triggers are set up.

---

## 7. Documentation & API Design

### API Consistency

**Q7.1:** Response format:
- Success responses return the object directly
- Error responses use `ErrorResponse` schema with `error_code` and `message`

Is this consistent enough or should all responses have a wrapper like:
```json
{
  "success": true,
  "data": {...}
}
```

**Q7.2:** Pagination:
- List endpoints return all results (no pagination yet)
- Should we add pagination for:
  - `/api/v1/classes/` (could be hundreds)
  - `/api/v1/orders/` (admin view)
  - `/api/v1/enrollments/` (admin view)

**Q7.3:** Filtering & Sorting:
- Should list endpoints support filtering?
  - Classes by program, school, date range, age range?
  - Orders by status, date range, user?
  - Enrollments by status, class, child?

---

## 8. Edge Cases & Special Scenarios

### Unusual Situations

**Q8.1:** What if a class is cancelled by admin after enrollments?
- Automatic full refunds to all enrolled?
- Manual refund process?
- Transfer to alternative class?

**Q8.2:** What if Stripe payment succeeds but our webhook fails to activate enrollment?
- Manual reconciliation process?
- Automated retry mechanism?
- How do we detect and fix these?

**Q8.3:** What if a parent's child ages out during the season?
- Do age restrictions check current age or age at enrollment?
- Should we warn if child will age out mid-season?

**Q8.4:** What if a child has medical conditions that require special handling?
- Should staff be able to flag high-priority medical info?
- Should there be alerts for coaches?

**Q8.5:** Scholarship eligibility:
- How do families apply for scholarships?
- Is there an approval workflow?
- Can scholarships be revoked?

**Q8.6:** Installment plan defaults:
- What happens if 3 installments fail in a row?
- Automatic cancellation?
- Collection process?
- Grace period?

---


## 9. Future Features & Extensibility

### Phase 4+ Preview

**Q9.1:** Looking ahead, what features are coming next?
- Attendance tracking?
- Coach assignments?
- Equipment management?
- Communications (announcements, messages)?
- Event/tournament management?

Asking so I can ensure current architecture supports future needs.

**Q9.2:** Multi-tenant considerations:
- Will this system serve multiple organizations?
- Should we add `organization_id` to key tables now?
- Or is this single-tenant forever?

**Q9.3:** Mobile app plans:
- Will there be a mobile app consuming this API?
- Any mobile-specific requirements? (push notifications, offline mode?)

---

## Action Items After Review

Based on your answers, I'll:

1. ✅ Fix any misaligned business logic
2. ✅ Add missing validations
3. ✅ Implement additional security measures
4. ✅ Add required endpoints
5. ✅ Update documentation
6. ✅ Add tests for clarified edge cases

---

## How to Respond

You don't need to answer every single question if something is already correct as implemented. Just let me know:

1. **"Looks good"** - for anything that's already correct
2. **Specific changes** - for anything that needs adjustment
3. **"Not needed"** - for features you don't need
4. **Additional comments** - for any extra context or requirements

Take your time reviewing - it's better to catch issues now than after deployment! 🚀

---

**Created:** 2025-11-24
**Status:** Awaiting Your Response
**Priority:** High - Blocks production deployment
