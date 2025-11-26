# API Request Payload Examples

Complete examples for all CREATE endpoints in the CSF Backend API.

---

## Table of Contents
1. [Authentication](#authentication)
2. [Users](#users)
3. [Children & Emergency Contacts](#children--emergency-contacts)
4. [Classes](#classes)
5. [Waivers](#waivers)
6. [Orders](#orders)
7. [Payments](#payments)
8. [Enrollments](#enrollments)
9. [Discounts](#discounts)

---

## Authentication

### Register New User
**POST** `/api/v1/auth/register`

```json
{
  "email": "parent@example.com",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "first_name": "John",
  "last_name": "Smith",
  "phone": "555-0123"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "parent@example.com",
    "first_name": "John",
    "last_name": "Smith",
    "role": "parent",
    "is_active": true
  },
  "tokens": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer"
  }
}
```

### Login (JSON)
**POST** `/api/v1/auth/login`

```json
{
  "email": "parent@example.com",
  "password": "SecurePass123"
}
```

### Login (OAuth2 for Swagger)
**POST** `/api/v1/auth/token`

**Form Data:**
- username: `parent@example.com`
- password: `SecurePass123`

### Refresh Token
**POST** `/api/v1/auth/refresh`

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Users

### Update Profile
**PUT** `/api/v1/users/me`

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "555-0123"
}
```

---

## Children & Emergency Contacts

### Create Child
**POST** `/api/v1/children/`

```json
{
  "first_name": "Emma",
  "last_name": "Smith",
  "date_of_birth": "2015-06-15",
  "jersey_size": "m",
  "grade": "3",
  "medical_conditions": "Asthma - requires inhaler",
  "has_no_medical_conditions": false,
  "after_school_attendance": true,
  "after_school_program": "YMCA After School",
  "health_insurance_number": "ABC123456789",
  "how_heard_about_us": "social_media",
  "how_heard_other_text": null,
  "emergency_contacts": [
    {
      "name": "John Smith",
      "relation": "father",
      "phone": "555-0123",
      "email": "john@example.com",
      "is_primary": true
    },
    {
      "name": "Jane Smith",
      "relation": "mother",
      "phone": "555-0124",
      "email": "jane@example.com",
      "is_primary": false
    }
  ]
}
```

**Jersey Sizes:** `xs`, `s`, `m`, `l`, `xl`, `xxl`

**Grades:** `pre_k`, `k`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`, `12`

**How Heard:** `website`, `social_media`, `friend`, `flyer`, `school`, `other`

### Add Emergency Contact
**POST** `/api/v1/children/{child_id}/emergency-contacts`

```json
{
  "name": "Grandma Mary",
  "relation": "grandmother",
  "phone": "555-0125",
  "email": "mary@example.com",
  "is_primary": false
}
```

---

## Classes

### Create Class (Admin)
**POST** `/api/v1/classes/`

```json
{
  "name": "Youth Soccer - Beginners",
  "description": "Introduction to soccer for ages 6-8",
  "program_id": "program-uuid",
  "school_id": "school-uuid",
  "class_type": "short_term",
  "weekdays": ["monday", "wednesday"],
  "start_time": "16:00:00",
  "end_time": "17:30:00",
  "start_date": "2025-01-15",
  "end_date": "2025-05-30",
  "capacity": 20,
  "price": 150.00,
  "min_age": 6,
  "max_age": 8,
  "ledger_code": "SOC-BEG-001",
  "image_url": "https://example.com/soccer-kids.jpg",
  "installments_enabled": true
}
```

**Class Types:** `short_term`, `membership`

**Weekdays:** `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

---

## Waivers

### Create Waiver Template (Admin)
**POST** `/api/v1/waivers/templates`

```json
{
  "name": "General Liability Waiver 2025",
  "waiver_type": "liability",
  "content": "I hereby release CSF Sports from all liability for injuries...",
  "version": 1,
  "is_active": true,
  "requires_reconsent_on_update": true
}
```

**Waiver Types:** `liability`, `medical`, `photo_release`, `code_of_conduct`, `other`

### Accept Waiver
**POST** `/api/v1/waivers/accept`

```json
{
  "waiver_template_id": "waiver-uuid",
  "accepted": true,
  "signature": "John Smith",
  "accepted_for_child_id": "child-uuid"
}
```

---

## Orders

### Calculate Order (Preview)
**POST** `/api/v1/orders/calculate`

```json
{
  "items": [
    {
      "child_id": "child1-uuid",
      "class_id": "class1-uuid"
    },
    {
      "child_id": "child2-uuid",
      "class_id": "class1-uuid"
    }
  ],
  "discount_code": "SUMMER25"
}
```

**Response shows:**
- Subtotal
- Sibling discounts (25%/35%/45%)
- Scholarship discounts
- Promo code discount
- Final total

### Create Order
**POST** `/api/v1/orders/`

```json
{
  "items": [
    {
      "child_id": "child1-uuid",
      "class_id": "class1-uuid"
    },
    {
      "child_id": "child2-uuid",
      "class_id": "class1-uuid"
    }
  ],
  "discount_code": "SUMMER25",
  "notes": "Please confirm enrollment dates"
}
```

### Pay for Order
**POST** `/api/v1/orders/{order_id}/pay`

**Query Parameters:**
- `payment_method_id` (optional): If provided, attempts immediate charge

```json
{}
```

**Response:**
```json
{
  "id": "pi_xxx",
  "client_secret": "pi_xxx_secret_yyy",
  "status": "requires_payment_method",
  "amount": 25000
}
```

### Cancel Order
**POST** `/api/v1/orders/{order_id}/cancel`

```json
{}
```

---

## Payments

### Create Setup Intent (Save Card)
**POST** `/api/v1/payments/setup-intent`

```json
{}
```

**Response:**
```json
{
  "id": "seti_xxx",
  "client_secret": "seti_xxx_secret_yyy"
}
```

**Usage:** Use `client_secret` with Stripe.js to collect card details

### Create Refund (Admin)
**POST** `/api/v1/payments/refund`

```json
{
  "payment_id": "payment-uuid",
  "amount": 50.00,
  "reason": "Customer requested cancellation within 15 days"
}
```

**Note:** Omit `amount` for full refund

---

## Enrollments

### Cancel Enrollment
**POST** `/api/v1/enrollments/{enrollment_id}/cancel`

```json
{
  "reason": "Child has scheduling conflict"
}
```

### Transfer Enrollment
**POST** `/api/v1/enrollments/{enrollment_id}/transfer`

```json
{
  "new_class_id": "new-class-uuid"
}
```

### Activate Enrollment (Admin)
**POST** `/api/v1/enrollments/{enrollment_id}/activate`

```json
{}
```

---

## Discounts

### Validate Discount Code
**POST** `/api/v1/discounts/validate`

```json
{
  "code": "SUMMER25",
  "order_amount": 300.00,
  "program_id": "program-uuid",
  "class_id": "class-uuid"
}
```

**Response:**
```json
{
  "is_valid": true,
  "error_message": null,
  "discount_type": "percentage",
  "discount_value": 25.00,
  "discount_amount": 75.00
}
```

### Create Discount Code (Admin)
**POST** `/api/v1/discounts/codes`

```json
{
  "code": "SUMMER25",
  "description": "25% off for summer enrollment",
  "discount_type": "percentage",
  "discount_value": 25.00,
  "valid_from": "2025-06-01T00:00:00Z",
  "valid_until": "2025-08-31T23:59:59Z",
  "max_uses": 100,
  "max_uses_per_user": 1,
  "min_order_amount": 100.00,
  "applies_to_program_id": null,
  "applies_to_class_id": null
}
```

**Discount Types:** `percentage`, `fixed_amount`

**Tips:**
- Use `percentage` for percent off (value: 25 = 25% off)
- Use `fixed_amount` for dollars off (value: 20 = $20 off)
- Leave `applies_to_program_id` and `applies_to_class_id` null for site-wide codes

### Create Fixed Amount Discount
**POST** `/api/v1/discounts/codes`

```json
{
  "code": "SAVE20",
  "description": "$20 off any order",
  "discount_type": "fixed_amount",
  "discount_value": 20.00,
  "valid_from": "2025-01-01T00:00:00Z",
  "valid_until": "2025-12-31T23:59:59Z",
  "max_uses": 50,
  "min_order_amount": 50.00
}
```

### Create Scholarship (Admin)
**POST** `/api/v1/discounts/scholarships`

```json
{
  "user_id": "user-uuid",
  "child_id": null,
  "scholarship_type": "Financial Need",
  "discount_percentage": 50.00,
  "valid_until": "2025-12-31",
  "notes": "Approved by director on 2025-01-15. Family qualifies for 50% assistance."
}
```

**Tips:**
- Set `child_id` to null for family-wide scholarship
- Set `child_id` to specific child UUID for per-child scholarship
- `discount_percentage` is applied after sibling discounts

---

## Complete Example Flow

### 1. Register User
```json
POST /api/v1/auth/register
{
  "email": "parent@example.com",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "first_name": "John",
  "last_name": "Smith"
}
```

### 2. Add Children
```json
POST /api/v1/children/
{
  "first_name": "Emma",
  "last_name": "Smith",
  "date_of_birth": "2015-06-15",
  "jersey_size": "m",
  "emergency_contacts": [
    {
      "name": "John Smith",
      "relation": "father",
      "phone": "555-0123",
      "email": "parent@example.com",
      "is_primary": true
    }
  ]
}
```

### 3. Calculate Order
```json
POST /api/v1/orders/calculate
{
  "items": [
    {
      "child_id": "{child_id_from_step_2}",
      "class_id": "{class_id}"
    }
  ],
  "discount_code": "SUMMER25"
}
```

### 4. Create Order
```json
POST /api/v1/orders/
{
  "items": [
    {
      "child_id": "{child_id_from_step_2}",
      "class_id": "{class_id}"
    }
  ],
  "discount_code": "SUMMER25"
}
```

### 5. Save Payment Method
```json
POST /api/v1/payments/setup-intent
{}
```
**Then use client_secret with Stripe.js to collect card**

### 6. Pay for Order
```json
POST /api/v1/orders/{order_id}/pay?payment_method_id={stripe_pm_id}
{}
```

### 7. Check Enrollment
```json
GET /api/v1/enrollments/my
```

---

## Common Field Values Reference

### Jersey Sizes
- `xs` - Extra Small
- `s` - Small
- `m` - Medium
- `l` - Large
- `xl` - Extra Large
- `xxl` - 2X Large

### Grade Levels
- `pre_k` - Pre-Kindergarten
- `k` - Kindergarten
- `1` through `12` - Grades 1-12

### Enrollment Status
- `pending` - Awaiting payment
- `active` - Enrolled and paid
- `cancelled` - User cancelled
- `completed` - Class completed
- `waitlisted` - On waitlist

### Order Status
- `draft` - Created, not paid
- `pending_payment` - Payment in progress
- `paid` - Payment successful
- `partially_paid` - Partial payment (installments)
- `refunded` - Full refund issued
- `cancelled` - Order cancelled

### Payment Status
- `pending` - Awaiting processing
- `processing` - Being processed
- `succeeded` - Payment successful
- `failed` - Payment failed
- `refunded` - Refund issued
- `partially_refunded` - Partial refund

### Installment Frequency
- `weekly` - Every 7 days
- `biweekly` - Every 14 days
- `monthly` - Every 30 days

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid email format",
  "data": {
    "field": "email",
    "value": "invalid-email"
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR` - Invalid input
- `UNAUTHORIZED` - Not authenticated
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `CONFLICT` - Duplicate resource

---

**Last Updated:** 2025-11-24
**API Version:** v1
