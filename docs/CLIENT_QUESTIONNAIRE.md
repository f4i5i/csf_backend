# CSF Backend - Client Business Requirements Questionnaire

## Purpose
This questionnaire clarifies the business logic, user flows, and system behavior for the CSF Youth Sports Registration Platform. Please answer each question to ensure we build the system according to your exact requirements.

---

## Section 1: User Roles & Registration

### 1.1 User Registration - Public (Self-Registration)

**Q1.1.1:** Can parents register themselves through the public `/auth/register` endpoint?
- [ ] Yes - Parents can self-register
- [ ] No - Only admins can create parent accounts
- [ ] Other: _______________

**Q1.1.2:** What information is required for parent self-registration?
- [ ] Email (required)
- [ ] Password (required)
- [ ] First Name (required)
- [ ] Last Name (required)
- [ ] Phone Number (optional/required?)
- [ ] Other: _______________

**Q1.1.3:** After parent self-registration, what is their account status?
- [ ] Active immediately - can enroll children right away
- [ ] Pending verification - must verify email first
- [ ] Pending admin approval - admin must activate account
- [ ] Other: _______________

**Q1.1.4:** Can parents use Google OAuth to register?
- [ ] Yes - Google sign-in is available
- [ ] No - Only email/password registration
- [ ] Optional - Both methods available

**Q1.1.5:** When a parent registers with Google, what happens if their email already exists?
- [ ] Link to existing account automatically
- [ ] Show error - email already registered
- [ ] Create new account and merge later
- [ ] Other: _______________

### 1.2 User Creation - Admin Panel

**Q1.2.1:** Can ADMINS create user accounts through the admin panel?
- [ ] Yes
- [ ] No

**Q1.2.2:** If yes, what types of users can ADMINS create?
- [ ] Parents only
- [ ] Coaches only
- [ ] Other admins
- [ ] All user types except Owner
- [ ] All user types including Owner
- [ ] Other: _______________

**Q1.2.3:** Can OWNERS create user accounts through the admin panel?
- [ ] Yes
- [ ] No

**Q1.2.4:** If yes, what types of users can OWNERS create?
- [ ] Parents
- [ ] Coaches
- [ ] Admins
- [ ] Other owners
- [ ] All user types
- [ ] Other: _______________

**Q1.2.5:** When admin creates a parent account, how does the parent get their password?
- [ ] Admin sets password and shares with parent
- [ ] System sends password reset email to parent
- [ ] Parent receives invitation email with setup link
- [ ] Parent can only use Google OAuth
- [ ] Other: _______________

**Q1.2.6:** Can coaches register themselves or must they be created by admin?
- [ ] Coaches can self-register
- [ ] Only admins can create coach accounts
- [ ] Other: _______________

---

## Section 2: Authentication & Access Control

### 2.1 Login Endpoints

**Q2.1.1:** Do ALL user types (Owner, Admin, Coach, Parent) use the same login endpoint?
- [ ] Yes - All use `/auth/login` or `/auth/token`
- [ ] No - Different endpoints for different roles
- [ ] Other: _______________

**Q2.1.2:** If different endpoints, please specify:
- Owner login endpoint: _______________
- Admin login endpoint: _______________
- Coach login endpoint: _______________
- Parent login endpoint: _______________

**Q2.1.3:** After successful login, do different roles go to different pages/dashboards?
- [ ] Yes - Each role has different dashboard
- [ ] No - Same dashboard for all
- [ ] Depends: _______________

**Q2.1.4:** Where does each role land after login?
- Owner: _______________ (e.g., `/admin/dashboard`)
- Admin: _______________ (e.g., `/admin/dashboard`)
- Coach: _______________ (e.g., `/coach/classes`)
- Parent: _______________ (e.g., `/parent/children`)

### 2.2 Initial System Setup

**Q2.2.1:** How is the first OWNER account created?
- [ ] Database seed script
- [ ] Special setup endpoint (one-time use)
- [ ] Manual database insertion
- [ ] During deployment
- [ ] Other: _______________

**Q2.2.2:** How many OWNER accounts should the system support?
- [ ] Only 1 owner (organization owner)
- [ ] Multiple owners (e.g., business partners)
- [ ] Number: _____

**Q2.2.3:** Can the system have multiple ADMINs?
- [ ] Yes - unlimited admins
- [ ] Yes - limited to _____ admins
- [ ] No - only 1 admin
- [ ] Other: _______________

---

## Section 3: User Relationships & Data Ownership

### 3.1 Parent-Child Relationship

**Q3.1.1:** Can one PARENT have multiple CHILDREN?
- [ ] Yes
- [ ] No
- [ ] Limited to _____ children

**Q3.1.2:** Can one CHILD have multiple PARENTS (e.g., divorced parents, guardians)?
- [ ] Yes - multiple parents can manage the same child
- [ ] No - one child belongs to one parent only
- [ ] Other: _______________

**Q3.1.3:** If multiple parents can manage one child, what is the data relationship?
- [ ] Child has primary_parent_id and secondary_parent_id fields
- [ ] Many-to-many relationship (parent_child junction table)
- [ ] Child belongs to one parent, others added as emergency contacts
- [ ] Other: _______________

**Q3.1.4:** Who can add/edit emergency contacts for a child?
- [ ] Only the parent who created the child
- [ ] Any parent linked to the child
- [ ] Admins only
- [ ] Both parent and admins
- [ ] Other: _______________

### 3.2 Class-Program-School Relationship

**Q3.2.1:** Current structure is:
```
Area → School → Class
Program → Class
```

Is this correct?
- [ ] Yes
- [ ] No - please describe: _______________

**Q3.2.2:** Can one CLASS belong to multiple PROGRAMS?
- [ ] Yes (e.g., "Soccer & Fitness" class)
- [ ] No - one class = one program
- [ ] Other: _______________

**Q3.2.3:** Can one CLASS be held at multiple SCHOOLS?
- [ ] Yes (e.g., rotating locations)
- [ ] No - one class = one school/location
- [ ] Other: _______________

**Q3.2.4:** Who can create/edit CLASSES?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Coaches can create their own classes
- [ ] Other: _______________

**Q3.2.5:** Who can create/edit PROGRAMS?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Other: _______________

---

## Section 4: Enrollment & Registration Flow

### 4.1 Enrollment Process

**Q4.1.1:** Current enrollment flow understanding:
```
Parent logs in → Adds child profile → Browses classes →
Selects class → Creates order → Pays → Enrollment active
```

Is this correct?
- [ ] Yes
- [ ] No - please describe correct flow: _______________

**Q4.1.2:** Can a parent enroll a child WITHOUT payment?
- [ ] Yes - enrollment pending until payment
- [ ] No - payment required for enrollment
- [ ] Depends on: _______________

**Q4.1.3:** Can parents enroll multiple children in multiple classes in one order?
- [ ] Yes - one order can have multiple children and classes
- [ ] No - separate order for each child
- [ ] No - separate order for each class
- [ ] Other: _______________

**Q4.1.4:** Who can manually create enrollments without payment (e.g., free enrollments)?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Coaches can enroll their own students
- [ ] No one - all enrollments require payment
- [ ] Other: _______________

**Q4.1.5:** Can coaches see their class rosters?
- [ ] Yes - coaches can view enrolled students
- [ ] No - only admins see rosters
- [ ] Yes - but limited information (no payment details)
- [ ] Other: _______________

### 4.2 Waitlist Management

**Q4.1.6:** What happens when a class is full?
- [ ] Show "Class Full" - no further action
- [ ] Allow joining waitlist
- [ ] Allow enrollment anyway (over-capacity)
- [ ] Other: _______________

**Q4.1.7:** Who manages the waitlist?
- [ ] Parents automatically moved to enrolled when spot opens
- [ ] Admin manually promotes from waitlist
- [ ] Both - auto-promote with admin override
- [ ] Other: _______________

---

## Section 5: Payment & Financial Management

### 5.1 Payment Methods

**Q5.1.1:** What payment types are required? (Check all that apply)
- [ ] One-time payment (pay full amount upfront)
- [ ] Subscription (recurring monthly billing)
- [ ] Installment plans (split payment into 2-12 installments)
- [ ] Other: _______________

**Q5.1.2:** For INSTALLMENT PLANS:
- Minimum number of installments: _____
- Maximum number of installments: _____
- Allowed frequencies:
  - [ ] Weekly
  - [ ] Bi-weekly
  - [ ] Monthly
  - [ ] Other: _____

**Q5.1.3:** Can parents change payment method after enrollment?
- [ ] Yes - any time
- [ ] Yes - only before first payment
- [ ] No - contact admin to change
- [ ] Other: _______________

**Q5.1.4:** Who can see payment information?
- [ ] Parent - own payments only
- [ ] Admin - all payments
- [ ] Owner - all payments
- [ ] Coach - cannot see payments
- [ ] Other: _______________

### 5.2 Discounts & Scholarships

**Q5.2.1:** SIBLING DISCOUNTS - Current logic:
```
2nd child: 25% off
3rd child: 35% off
4th+ child: 45% off
```

Is this correct?
- [ ] Yes
- [ ] No - please provide correct percentages:
  - 2nd child: _____% off
  - 3rd child: _____% off
  - 4th+ child: _____% off

**Q5.2.2:** Are sibling discounts applied automatically?
- [ ] Yes - automatic when multiple children enrolled
- [ ] No - parent must apply discount code
- [ ] No - admin must manually apply
- [ ] Other: _______________

**Q5.2.3:** Can PROMO CODES and SIBLING DISCOUNTS be combined?
- [ ] Yes - both apply (stackable)
- [ ] No - only one discount type per order
- [ ] Other: _______________

**Q5.2.4:** Who can create DISCOUNT CODES?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Coaches can create for their classes
- [ ] Other: _______________

**Q5.2.5:** Who can approve SCHOLARSHIPS?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Must be approved by: _______________
- [ ] Other: _______________

---

## Section 6: Waivers & Legal Compliance

### 6.1 Waiver Requirements

**Q6.1.1:** Current system has 4 waiver types:
1. Medical Release
2. Liability
3. Photo Release
4. Cancellation Policy

Is this correct?
- [ ] Yes
- [ ] No - please list required waiver types: _______________

**Q6.1.2:** When must parents accept waivers?
- [ ] Before enrollment (during class selection)
- [ ] After payment (before class starts)
- [ ] At first class check-in
- [ ] Other: _______________

**Q6.1.3:** Are waivers required for EACH child or ONCE per parent?
- [ ] Per child - parent accepts for each child separately
- [ ] Per parent - one acceptance covers all children
- [ ] Per enrollment - accept for each class enrollment
- [ ] Other: _______________

**Q6.1.4:** Can waivers be customized per PROGRAM or SCHOOL?
- [ ] Yes - different waivers for different programs
- [ ] Yes - different waivers for different schools
- [ ] No - same waivers for all
- [ ] Other: _______________

**Q6.1.5:** Who can create/edit waiver templates?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Other: _______________

---

## Section 7: Class Management

### 7.1 Class Scheduling

**Q7.1.1:** How are class schedules defined?
- [ ] Recurring schedule (e.g., "Every Monday 3pm-4pm")
- [ ] Individual session dates (e.g., "Jan 5, Jan 12, Jan 19")
- [ ] Both options available
- [ ] Other: _______________

**Q7.1.2:** Who can mark attendance?
- [ ] Coaches only
- [ ] Admins and Coaches
- [ ] Admins, Coaches, and check-in staff
- [ ] Other: _______________

**Q7.1.3:** Can parents see their child's attendance history?
- [ ] Yes - full history
- [ ] Yes - but only after class ends
- [ ] No - attendance is internal only
- [ ] Other: _______________

### 7.2 Coach Assignment

**Q7.2.1:** How many coaches can be assigned to one class?
- [ ] One primary coach only
- [ ] Multiple coaches (primary + assistants)
- [ ] Unlimited coaches
- [ ] Other: _______________

**Q7.2.2:** Can a coach teach multiple classes?
- [ ] Yes - unlimited
- [ ] Yes - limited to _____ classes
- [ ] No
- [ ] Other: _______________

**Q7.2.3:** Who assigns coaches to classes?
- [ ] Owner only
- [ ] Admins and Owner
- [ ] Coaches can self-assign
- [ ] Other: _______________

---

## Section 8: Administrative Functions

### 8.1 User Management

**Q8.1.1:** Can ADMINS deactivate user accounts?
- [ ] Yes - all user types
- [ ] Yes - only parents and coaches
- [ ] No - only Owner can deactivate
- [ ] Other: _______________

**Q8.1.2:** Can ADMINS delete user accounts permanently?
- [ ] Yes - all users
- [ ] Yes - only if no enrollments/payments exist
- [ ] No - can only deactivate, not delete
- [ ] Other: _______________

**Q8.1.3:** Can ADMINS reset user passwords?
- [ ] Yes - admins can reset any password
- [ ] Yes - but only send reset email, not set password
- [ ] No - users must use "Forgot Password" flow
- [ ] Other: _______________

### 8.2 Reporting & Analytics

**Q8.2.1:** What reports do admins need? (Check all that apply)
- [ ] Revenue reports (by date, program, school)
- [ ] Enrollment reports (active, pending, cancelled)
- [ ] Attendance reports (by class, student, date)
- [ ] Payment reports (paid, pending, failed)
- [ ] User growth reports
- [ ] Class capacity reports
- [ ] Other: _______________

**Q8.2.2:** Can admins export data to CSV/Excel?
- [ ] Yes - all reports exportable
- [ ] Yes - some reports only: _______________
- [ ] No - view only
- [ ] Other: _______________

**Q8.2.3:** Can coaches see financial data?
- [ ] Yes - for their classes only
- [ ] No - coaches see enrollment counts only
- [ ] Other: _______________

---

## Section 9: Cancellation & Refund Policy

### 9.1 Cancellation Rules

**Q9.1.1:** Current 15-day cancellation policy:
```
Within 15 days: Full refund minus processing fee
After 15 days: No refund, but pro-rated credit for future
```

Is this correct?
- [ ] Yes
- [ ] No - please describe policy: _______________

**Q9.1.2:** Who can cancel an enrollment?
- [ ] Parent can self-cancel
- [ ] Must request cancellation from admin
- [ ] Owner/Admin only
- [ ] Other: _______________

**Q9.1.3:** For SUBSCRIPTION enrollments, when does cancellation take effect?
- [ ] Immediately - access revoked right away
- [ ] End of current billing period
- [ ] Other: _______________

**Q9.1.4:** Can parents transfer a child to a different class instead of cancelling?
- [ ] Yes - free transfer within same program
- [ ] Yes - with transfer fee
- [ ] No - must cancel and re-enroll
- [ ] Other: _______________

### 9.2 Refund Processing

**Q9.2.1:** Who approves refunds?
- [ ] Automatic based on policy
- [ ] Admin must approve all refunds
- [ ] Owner must approve refunds > $___
- [ ] Other: _______________

**Q9.2.2:** How are refunds processed?
- [ ] Automatic via Stripe to original payment method
- [ ] Manual - admin initiates refund
- [ ] Store credit only - no cash refunds
- [ ] Other: _______________

---

## Section 10: Communication & Notifications

### 10.1 Email Notifications

**Q10.1.1:** What emails should be sent automatically? (Check all that apply)

**Account Related:**
- [ ] Welcome email after registration
- [ ] Email verification link
- [ ] Password reset link
- [ ] Account activation notification

**Enrollment Related:**
- [ ] Enrollment confirmation
- [ ] Payment receipt
- [ ] Upcoming class reminder (X days before)
- [ ] Class cancellation notice

**Payment Related:**
- [ ] Payment success confirmation
- [ ] Payment failure notice
- [ ] Upcoming installment reminder
- [ ] Installment payment receipt

**Administrative:**
- [ ] New enrollment notification to admin
- [ ] Failed payment alert to admin
- [ ] Waitlist promotion notice to parent

**Q10.2:** Should emails be customizable by program/school?
- [ ] Yes - each program can have custom email templates
- [ ] Yes - each school can have custom email templates
- [ ] No - standard templates for all
- [ ] Other: _______________

### 10.2 SMS Notifications

**Q10.3:** Should the system send SMS notifications?
- [ ] Yes - for critical events only
- [ ] Yes - parents can opt-in for SMS
- [ ] No - email only
- [ ] Future phase
- [ ] Other: _______________

---

## Section 11: Data Privacy & Security

### 11.1 PII Encryption

**Q11.1:** What data should be encrypted in the database? (Currently encrypted: medical info, insurance)
- [ ] Medical information
- [ ] Insurance information
- [ ] Social Security Numbers (if collected)
- [ ] Credit card info (handled by Stripe - not stored)
- [ ] Other: _______________

**Q11.2:** Can parents delete their account and all data (GDPR right to erasure)?
- [ ] Yes - self-service account deletion
- [ ] Yes - must request from admin
- [ ] No - data retention for X years required
- [ ] Other: _______________

**Q11.3:** Can parents export all their data (GDPR right to data portability)?
- [ ] Yes - download all data in JSON/CSV
- [ ] Yes - must request from admin
- [ ] Not required
- [ ] Other: _______________

---

## Section 12: Integration Requirements

### 12.1 Third-Party Services

**Q12.1:** Current integrations:
- Stripe (payments)
- SendGrid (transactional emails)
- Mailchimp (marketing emails)
- Google OAuth

Are any other integrations needed?
- [ ] Accounting software (QuickBooks, Xero): _______________
- [ ] Calendar integration (Google Calendar, Outlook): _______________
- [ ] SMS provider (Twilio): _______________
- [ ] Video conferencing (Zoom, Teams): _______________
- [ ] Other: _______________

---

## Section 13: Open Questions & Clarifications

**Q13.1:** List any specific business rules or scenarios not covered above:

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________
4. _______________________________________________
5. _______________________________________________

**Q13.2:** What are the top 3 most critical features for launch?

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Q13.3:** What features can be deferred to Phase 2?

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

---

## Submission Instructions

Please fill out this questionnaire and return it to the development team. Your answers will help us:

1. Finalize database schema and relationships
2. Implement correct access control and permissions
3. Build the right user workflows
4. Avoid costly rework and assumptions

**Contact:** _______________
**Date Completed:** _______________
**Reviewed By:** _______________

---

## Next Steps After Submission

Once we receive your answers, we will:

1. **Review & Clarify** - Schedule a call to discuss any unclear points
2. **Update Database Schema** - Adjust models to match your requirements
3. **Create API Specifications** - Define exact endpoints and behaviors
4. **Build User Flows** - Implement frontend workflows based on roles
5. **Deliver Prototype** - Show you a working version for feedback

**Estimated Time to Implement:** Based on complexity, 2-4 weeks after approval.

---

Thank you for taking the time to provide these details. Clear requirements lead to a better product! 🚀
