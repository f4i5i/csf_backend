# Payment Options - Flexible Stripe Pricing Guide

## Overview

The **Payment Options** feature allows admins to configure flexible payment structures for classes. When creating or updating a class with `payment_options`, the system automatically:

1. Creates a Stripe Product (if needed)
2. Creates Stripe Prices for each payment option
3. Stores the Stripe IDs for future use

This eliminates the need for manual Stripe Product/Price creation and provides complete flexibility in pricing models.

---

## Features

✅ **Flexible Payment Types**
- One-time payments
- Recurring subscriptions (monthly, quarterly, annual, custom intervals)

✅ **Automatic Stripe Integration**
- Auto-creates Stripe Products
- Auto-creates Stripe Prices
- Stores Price IDs for enrollment processing

✅ **Multiple Payment Options Per Class**
- Offer multiple pricing tiers
- Mix one-time and recurring options
- Different billing intervals

✅ **Validation**
- Amount validation (positive, max 2 decimals)
- Recurring payment validation (requires interval)
- Type checking (one_time vs recurring)

---

## Schema

### PaymentOption

```python
{
    "name": str,              # Display name (required, 1-200 chars)
    "type": str,              # "one_time" or "recurring" (required)
    "amount": Decimal,        # Amount in dollars (required, > 0, max 2 decimals)
    "interval": str,          # "month" or "year" (required for recurring)
    "interval_count": int,    # Number of intervals (default: 1, range: 1-12)
    "description": str        # Optional description (max 500 chars)
}
```

### Validation Rules

1. **Amount**
   - Must be positive (> 0)
   - Maximum 2 decimal places
   - Example: `99.00`, `1000.50`

2. **Type**
   - Must be `"one_time"` or `"recurring"`

3. **Interval** (for recurring payments)
   - Required when `type = "recurring"`
   - Must be `"month"` or `"year"`
   - Not allowed when `type = "one_time"`

4. **Interval Count**
   - Range: 1-12
   - Default: 1
   - Examples:
     - `1` = Every interval
     - `3` with `interval="month"` = Every 3 months (quarterly)
     - `6` with `interval="month"` = Every 6 months (semi-annual)

---

## API Usage

### Create Class with Payment Options

**Endpoint:** `POST /api/v1/classes`

**Request Body:**

```json
{
  "name": "Elite Karate Program",
  "description": "Advanced karate training",
  "program_id": "550e8400-e29b-41d4-a716-446655440000",
  "school_id": "660e8400-e29b-41d4-a716-446655440001",
  "class_type": "membership",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "capacity": 20,
  "price": 99.00,
  "min_age": 8,
  "max_age": 16,

  "payment_options": [
    {
      "name": "Monthly Membership",
      "type": "recurring",
      "amount": 99.00,
      "interval": "month",
      "interval_count": 1,
      "description": "Pay monthly with flexibility to cancel anytime"
    },
    {
      "name": "Quarterly Membership",
      "type": "recurring",
      "amount": 270.00,
      "interval": "month",
      "interval_count": 3,
      "description": "Save 9% with quarterly billing"
    },
    {
      "name": "Annual Membership",
      "type": "recurring",
      "amount": 1000.00,
      "interval": "year",
      "interval_count": 1,
      "description": "Best value - save 16% with annual billing"
    },
    {
      "name": "One-time Enrollment Fee",
      "type": "one_time",
      "amount": 150.00,
      "description": "One-time registration fee"
    }
  ],
  "auto_create_stripe_prices": true
}
```

**What Happens:**

1. ✅ Class is created in database
2. ✅ Stripe Product is created: `"Elite Karate Program"`
3. ✅ 4 Stripe Prices are created:
   - Monthly: `$99.00/month`
   - Quarterly: `$270.00 every 3 months`
   - Annual: `$1000.00/year`
   - One-time: `$150.00`
4. ✅ Class is updated with `stripe_product_id`
5. ✅ Response includes the class with all data

**Response:**

```json
{
  "id": "class_uuid",
  "name": "Elite Karate Program",
  "stripe_product_id": "prod_xyz123",
  ...
}
```

---

### Update Class with Payment Options

**Endpoint:** `PUT /api/v1/classes/{class_id}`

**Request Body:**

```json
{
  "payment_options": [
    {
      "name": "Premium Monthly",
      "type": "recurring",
      "amount": 129.00,
      "interval": "month",
      "interval_count": 1,
      "description": "Premium tier with extra benefits"
    },
    {
      "name": "Standard Monthly",
      "type": "recurring",
      "amount": 99.00,
      "interval": "month",
      "interval_count": 1,
      "description": "Standard membership"
    }
  ]
}
```

**What Happens:**

1. ✅ Class is updated with new data
2. ✅ Stripe Product is created/reused
3. ✅ New Stripe Prices are created
4. ✅ Old prices remain active (not deleted)

---

## Example Use Cases

### Use Case 1: Simple Monthly Membership

```json
{
  "payment_options": [
    {
      "name": "Monthly Membership",
      "type": "recurring",
      "amount": 99.00,
      "interval": "month"
    }
  ]
}
```

### Use Case 2: Tiered Pricing (Save More Long-Term)

```json
{
  "payment_options": [
    {
      "name": "Pay Monthly",
      "type": "recurring",
      "amount": 99.00,
      "interval": "month",
      "description": "Cancel anytime"
    },
    {
      "name": "Pay Quarterly",
      "type": "recurring",
      "amount": 270.00,
      "interval": "month",
      "interval_count": 3,
      "description": "Save $27 per quarter"
    },
    {
      "name": "Pay Annually",
      "type": "recurring",
      "amount": 990.00,
      "interval": "year",
      "description": "Save $198 per year!"
    }
  ]
}
```

### Use Case 3: One-Time Workshop

```json
{
  "payment_options": [
    {
      "name": "Workshop Registration",
      "type": "one_time",
      "amount": 250.00,
      "description": "Full weekend workshop"
    }
  ]
}
```

### Use Case 4: Mixed Payment Options

```json
{
  "payment_options": [
    {
      "name": "Registration Fee",
      "type": "one_time",
      "amount": 50.00,
      "description": "One-time registration"
    },
    {
      "name": "Monthly Tuition",
      "type": "recurring",
      "amount": 150.00,
      "interval": "month",
      "description": "Recurring monthly payment"
    }
  ]
}
```

### Use Case 5: Seasonal Memberships

```json
{
  "payment_options": [
    {
      "name": "Summer Season",
      "type": "one_time",
      "amount": 450.00,
      "description": "Full summer season (3 months)"
    },
    {
      "name": "Monthly Payment Plan",
      "type": "recurring",
      "amount": 160.00,
      "interval": "month",
      "interval_count": 1,
      "description": "Pay monthly during season"
    }
  ]
}
```

---

## Backend Flow

### 1. Class Creation with Payment Options

```python
# User creates class with payment_options
POST /api/v1/classes

# Backend processes:
1. Create Class in database
2. if payment_options provided and auto_create_stripe_prices:
   a. Call StripeProductService.process_payment_options()
   b. Create/Get Stripe Product
   c. For each payment_option:
      - Create Stripe Price (recurring or one-time)
      - Store metadata (class_id, payment_option_name, type)
   d. Update class.stripe_product_id
3. Return ClassResponse
```

### 2. Stripe Product/Price Creation

```python
# process_payment_options() method:

for each payment_option:
    if type == "recurring":
        stripe.Price.create(
            product=stripe_product_id,
            unit_amount=amount * 100,  # Convert to cents
            currency="usd",
            recurring={
                "interval": interval,         # "month" or "year"
                "interval_count": interval_count
            },
            metadata={
                "class_id": class_id,
                "payment_option_name": name,
                "payment_option_type": "recurring"
            }
        )
    else:  # one_time
        stripe.Price.create(
            product=stripe_product_id,
            unit_amount=amount * 100,
            currency="usd",
            metadata={
                "class_id": class_id,
                "payment_option_name": name,
                "payment_option_type": "one_time"
            }
        )
```

### 3. Enrollment with Payment Option

When a user enrolls, they select which payment option to use. The frontend passes the Stripe Price ID:

```python
POST /api/v1/enrollments
{
    "child_id": "child_uuid",
    "class_id": "class_uuid",
    "stripe_price_id": "price_monthly123",  # Selected payment option
    "payment_method_id": "pm_card_visa"
}
```

---

## Stripe Dashboard

After creating a class with payment options, you'll see in Stripe:

**Product:**
```
Name: Elite Karate Program
ID: prod_xyz123
Metadata:
  - class_id: class_uuid
  - class_name: Elite Karate Program
  - program_id: program_uuid
```

**Prices:**
```
1. Monthly Membership
   ID: price_abc123
   Amount: $99.00/month
   Metadata:
     - class_id: class_uuid
     - payment_option_name: Monthly Membership
     - payment_option_type: recurring

2. Quarterly Membership
   ID: price_def456
   Amount: $270.00 every 3 months
   Metadata:
     - class_id: class_uuid
     - payment_option_name: Quarterly Membership
     - payment_option_type: recurring

3. Annual Membership
   ID: price_ghi789
   Amount: $1000.00/year
   Metadata:
     - class_id: class_uuid
     - payment_option_name: Annual Membership
     - payment_option_type: recurring

4. One-time Enrollment Fee
   ID: price_jkl012
   Amount: $150.00
   Metadata:
     - class_id: class_uuid
     - payment_option_name: One-time Enrollment Fee
     - payment_option_type: one_time
```

---

## Error Handling

### Validation Errors

**Example 1: Missing interval for recurring**
```json
{
  "name": "Monthly",
  "type": "recurring",
  "amount": 99.00
  // Missing interval - ERROR
}
```

**Error:**
```json
{
  "detail": "interval is required for recurring payment options"
}
```

**Example 2: Invalid amount**
```json
{
  "name": "Monthly",
  "type": "recurring",
  "amount": -50.00,  // Negative - ERROR
  "interval": "month"
}
```

**Error:**
```json
{
  "detail": "Amount must be positive"
}
```

**Example 3: Too many decimals**
```json
{
  "name": "Monthly",
  "type": "recurring",
  "amount": 99.999,  // 3 decimals - ERROR
  "interval": "month"
}
```

**Error:**
```json
{
  "detail": "Amount can have at most 2 decimal places"
}
```

### Stripe Errors

If Stripe Price creation fails, the class is still created but an error is returned:

```json
{
  "detail": "Class created but failed to create Stripe prices: <stripe_error>"
}
```

You can retry by updating the class with the same payment_options.

---

## Disabling Auto-Creation

To create a class WITHOUT automatically creating Stripe Prices:

```json
{
  "name": "My Class",
  ...
  "payment_options": [...],
  "auto_create_stripe_prices": false
}
```

This allows you to:
- Create the class first
- Manually create Stripe Prices later
- Use the `/admin/stripe/classes/sync` endpoint

---

## Migration from Legacy Pricing

### Old System (Still Supported)

```json
{
  "price": 99.00,
  "membership_price": 89.00,
  "installments_enabled": true
}
```

### New System (Recommended)

```json
{
  "price": 99.00,  // Keep for backward compatibility
  "payment_options": [
    {
      "name": "Standard Price",
      "type": "one_time",
      "amount": 99.00
    },
    {
      "name": "Member Price",
      "type": "one_time",
      "amount": 89.00
    },
    {
      "name": "Monthly Plan",
      "type": "recurring",
      "amount": 35.00,
      "interval": "month",
      "interval_count": 1,
      "description": "Pay in 3 monthly installments"
    }
  ]
}
```

---

## Best Practices

1. **Clear Naming**
   - Use descriptive payment option names
   - Include billing frequency in name
   - Example: "Monthly Membership", "Annual Membership", "One-time Registration"

2. **Descriptions**
   - Explain what the user gets
   - Highlight savings for long-term plans
   - Example: "Save 20% with annual billing"

3. **Pricing Strategy**
   - Offer 3-4 options (not too many)
   - Make annual plans attractive (10-20% discount)
   - Consider one-time options for flexibility

4. **Metadata**
   - Automatically stored in Stripe metadata
   - Used for filtering and reporting
   - Helps identify prices in Stripe Dashboard

5. **Testing**
   - Test with Stripe test mode
   - Verify prices created correctly
   - Check enrollment flow works

---

## Querying Payment Options

### Get Class with Stripe Product Info

```http
GET /api/v1/classes/{class_id}
```

**Response:**
```json
{
  "id": "class_uuid",
  "name": "Elite Karate Program",
  "stripe_product_id": "prod_xyz123",
  ...
}
```

### List Stripe Prices for a Product

```http
GET /api/v1/admin/stripe/prices?product_id=prod_xyz123
```

**Response:**
```json
[
  {
    "id": "price_monthly123",
    "amount": 9900,
    "recurring": {
      "interval": "month",
      "interval_count": 1
    },
    "metadata": {
      "payment_option_name": "Monthly Membership"
    }
  },
  ...
]
```

---

## Summary

✅ **What You Get:**
- Flexible payment configuration
- Automatic Stripe Product/Price creation
- Multiple pricing tiers per class
- Mix one-time and recurring payments
- Comprehensive validation
- Full Stripe metadata

✅ **What It Replaces:**
- Manual Stripe Product creation
- Manual Stripe Price creation
- Manual Price ID linking
- Fixed pricing models

✅ **Ready to Use:**
The payment options feature is production-ready and fully integrated with the enrollment system!

---

**Last Updated:** 2025-12-12
**Version:** 1.0
**Status:** Production Ready ✅
