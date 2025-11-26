# Stripe Test Environment Setup Guide

## Complete Guide for CSF Backend Payment Testing

**Created:** 2025-11-25
**Purpose:** Configure Stripe for local development and testing
**Estimated Time:** 15-20 minutes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Stripe Account Setup](#stripe-account-setup)
3. [Get API Keys](#get-api-keys)
4. [Configure Backend](#configure-backend)
5. [Setup Webhooks](#setup-webhooks)
6. [Test Payment Flow](#test-payment-flow)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- ✅ Stripe account (free - no credit card needed for test mode)
- ✅ Stripe CLI installed (for webhook testing)
- ✅ Backend running locally (`uv run uvicorn main:app --reload`)
- ✅ PostgreSQL database running

### Install Stripe CLI

#### macOS
```bash
brew install stripe/stripe-cli/stripe
```

#### Linux
```bash
wget https://github.com/stripe/stripe-cli/releases/latest/download/stripe_linux_amd64.tar.gz
tar -xvf stripe_linux_amd64.tar.gz
sudo mv stripe /usr/local/bin/
```

#### Windows
```bash
scoop bucket add stripe https://github.com/stripe/scoop-stripe-cli.git
scoop install stripe
```

#### Verify Installation
```bash
stripe --version
# Should output: stripe version X.X.X
```

---

## Stripe Account Setup

### Step 1: Create Stripe Account

1. Go to [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Sign up with your email
3. Verify your email address
4. **Skip** business details (not needed for test mode)

### Step 2: Activate Test Mode

1. In Stripe Dashboard, look for the toggle in the top-right
2. Ensure **"Test mode"** is **ON** (should see orange indicator)
3. All API keys you copy will be test keys (starting with `pk_test_` and `sk_test_`)

---

## Get API Keys

### Step 1: Get Publishable and Secret Keys

1. Go to **Developers** → **API keys** in Stripe Dashboard
2. You'll see two keys in test mode:

```
Publishable key:  pk_test_xxxxxxxxxxxxxxxxxxxxx
Secret key:       sk_test_xxxxxxxxxxxxxxxxxxxxx (click "Reveal test key")
```

3. **Copy both keys** - you'll need them for configuration

### Step 2: Create Webhook Signing Secret

You'll get this in the webhook setup section below.

---

## Configure Backend

### Step 1: Update `.env` File

Open `.env` in your project root and update:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE  # We'll get this next

# Database (make sure this is set)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/csf_db

# Other required settings
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
ENCRYPTION_KEY=lcUKk96sknbfFlmZ5N_jyOau-s-sm-NyWDdFwjECWAo=
```

### Step 2: Verify Configuration

```bash
# Check environment variables are loaded
uv run python -c "from core.config import config; print(f'Stripe Key: {config.STRIPE_SECRET_KEY[:15]}...')"

# Should output: Stripe Key: sk_test_...
```

---

## Setup Webhooks

Webhooks allow Stripe to notify your backend when events occur (payment succeeded, subscription cancelled, etc.).

### Option A: Local Development with Stripe CLI (Recommended)

#### Step 1: Login to Stripe CLI

```bash
stripe login
```

This will open your browser to authorize the CLI.

#### Step 2: Forward Webhooks to Local Server

Open a **new terminal** window and run:

```bash
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe
```

You'll see output like:

```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxxxxxxxxxx
> Listening for webhooks...
```

#### Step 3: Copy the Webhook Secret

Copy the `whsec_xxxxxxxxxxxxxxxxxxxxx` value and add it to your `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
```

#### Step 4: Restart Your Backend

```bash
# Stop the server (Ctrl+C) and restart
uv run uvicorn main:app --reload
```

**Keep the `stripe listen` terminal running** - it must stay open to forward webhooks.

---

### Option B: Production Webhooks (After Deployment)

#### Step 1: Create Webhook Endpoint

1. Go to **Developers** → **Webhooks** in Stripe Dashboard
2. Click **"Add endpoint"**
3. Enter your endpoint URL: `https://your-domain.com/api/v1/webhooks/stripe`

#### Step 2: Select Events

Select these events to listen to:

```
✅ payment_intent.succeeded
✅ payment_intent.payment_failed
✅ invoice.paid
✅ invoice.payment_failed
✅ customer.subscription.deleted
✅ customer.subscription.updated
✅ charge.refunded
✅ invoice.upcoming
```

#### Step 3: Get Signing Secret

1. Click on the newly created webhook
2. Click **"Reveal"** under **Signing secret**
3. Copy the secret (starts with `whsec_`)
4. Add to production `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_YOUR_PRODUCTION_SECRET
```

---

## Test Payment Flow

### Step 1: Start All Services

```bash
# Terminal 1: Backend server
uv run uvicorn main:app --reload

# Terminal 2: Stripe webhook listener
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe
```

### Step 2: Test Card Numbers

Stripe provides test cards for different scenarios:

| Card Number | Scenario |
|-------------|----------|
| `4242424242424242` | ✅ Successful payment |
| `4000000000000002` | ❌ Card declined |
| `4000002500003155` | 🔐 Requires authentication (3D Secure) |
| `4000000000009995` | ❌ Insufficient funds |

**Expiry:** Any future date (e.g., `12/25`)
**CVC:** Any 3 digits (e.g., `123`)
**ZIP:** Any 5 digits (e.g., `12345`)

### Step 3: Test Complete Flow

#### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click **"Authorize"** button
3. Login with test user credentials
4. Test this flow:

```
1. POST /api/v1/orders/calculate
   - Calculate order total

2. POST /api/v1/orders/
   - Create order

3. POST /api/v1/payments/setup-intent
   - Save payment method (use test card: 4242424242424242)

4. POST /api/v1/installments/preview
   - Preview installment schedule

5. POST /api/v1/installments/
   - Create installment plan

6. Check Terminal 2 (Stripe CLI)
   - You should see webhook events being received
```

#### Example: Create Installment Plan

```bash
curl -X POST "http://localhost:8000/api/v1/installments/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order_123",
    "num_installments": 3,
    "frequency": "monthly",
    "payment_method_id": "pm_test_card_123"
  }'
```

### Step 4: Verify Webhooks

In Terminal 2 (Stripe CLI), you should see:

```
2025-11-25 14:30:15  --> invoice.paid [evt_abc123]
2025-11-25 14:30:15  <-- [200] POST http://localhost:8000/api/v1/webhooks/stripe
```

✅ **Success!** Your webhook is working.

---

## Testing Scenarios

### Scenario 1: One-Time Payment

```bash
1. Create order
2. Create payment method (4242424242424242)
3. Create payment intent
4. Verify payment succeeded
5. Check enrollment activated
```

### Scenario 2: Installment Plan

```bash
1. Create order
2. Preview installment schedule (3 monthly payments)
3. Create payment method
4. Create installment plan
5. Verify first payment processed
6. Trigger test webhook for next payment:
   stripe trigger invoice.paid
```

### Scenario 3: Failed Payment

```bash
1. Create order
2. Use declined card (4000000000000002)
3. Attempt payment
4. Verify payment_intent.payment_failed webhook
5. Check payment status = failed
```

### Scenario 4: Refund

```bash
1. Complete successful payment
2. POST /api/v1/payments/refund (admin only)
3. Verify charge.refunded webhook
4. Check enrollment cancelled
```

---

## Verify Database

### Check Payment Records

```sql
-- Connect to database
psql postgresql://postgres:postgres@localhost:5432/csf_db

-- View payments
SELECT id, user_id, payment_type, status, amount, stripe_payment_intent_id
FROM payments
ORDER BY created_at DESC
LIMIT 5;

-- View installment plans
SELECT id, user_id, num_installments, status, stripe_subscription_id
FROM installment_plans
ORDER BY created_at DESC;

-- View installment payments
SELECT ip.id, ip.installment_number, ip.status, ip.due_date, ip.amount
FROM installment_payments ip
JOIN installment_plans i ON ip.installment_plan_id = i.id
ORDER BY ip.due_date;
```

---

## Troubleshooting

### Issue 1: "Invalid API Key"

**Symptom:** `stripe.error.AuthenticationError: Invalid API Key provided`

**Solution:**
1. Verify `.env` has correct key: `STRIPE_SECRET_KEY=sk_test_...`
2. Ensure key starts with `sk_test_` (not `sk_live_`)
3. Restart backend server after changing `.env`
4. Check for extra spaces in the key

```bash
# Verify key in environment
uv run python -c "import os; print(os.getenv('STRIPE_SECRET_KEY'))"
```

---

### Issue 2: "Invalid webhook signature"

**Symptom:** Webhook returns 400 error "Invalid signature"

**Solution:**
1. Verify `STRIPE_WEBHOOK_SECRET` in `.env` starts with `whsec_`
2. Ensure Stripe CLI is running: `stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe`
3. Use the **exact** secret from Stripe CLI output
4. Restart backend after updating secret

---

### Issue 3: Webhooks not received

**Symptom:** No webhook events in Stripe CLI terminal

**Solution:**
1. Check Stripe CLI is running in separate terminal
2. Verify endpoint URL is correct: `http://localhost:8000/api/v1/webhooks/stripe`
3. Check backend server is running on port 8000
4. Try triggering test event:

```bash
stripe trigger payment_intent.succeeded
```

---

### Issue 4: Database connection error

**Symptom:** `could not connect to server: Connection refused`

**Solution:**
1. Start PostgreSQL:
```bash
sudo service postgresql start
# or
brew services start postgresql
```

2. Verify database exists:
```bash
psql -U postgres -l | grep csf_db
```

3. Create database if needed:
```bash
psql -U postgres -c "CREATE DATABASE csf_db;"
```

4. Run migrations:
```bash
uv run alembic upgrade head
```

---

### Issue 5: "Payment method not found"

**Symptom:** `No such payment_method: pm_xyz`

**Solution:**
1. Create payment method first using `/payments/setup-intent`
2. Use test card: `4242424242424242`
3. Save the returned `payment_method_id`
4. Use that ID in installment/subscription creation

---

## Test with Stripe Dashboard

### View Events

1. Go to **Developers** → **Events** in Stripe Dashboard
2. Filter by:
   - `payment_intent.succeeded`
   - `invoice.paid`
   - `customer.subscription.updated`
3. Click on any event to see full payload
4. Check "Request & response" to see webhook delivery

### View Customers

1. Go to **Customers** in Stripe Dashboard
2. You should see test customers created by your backend
3. Click on a customer to see:
   - Payment methods
   - Subscriptions
   - Invoices
   - Payment history

### View Subscriptions

1. Go to **Subscriptions** in Stripe Dashboard
2. See all active installment plans and memberships
3. Click to view:
   - Billing schedule
   - Payment history
   - Metadata (order_id, user_id, etc.)

---

## Testing Checklist

Before moving to production, test:

### ✅ Basic Payments
- [ ] Create payment method
- [ ] One-time payment succeeds
- [ ] Failed payment handled correctly
- [ ] Enrollment activated on success

### ✅ Installments
- [ ] Preview installment schedule
- [ ] Create 3-payment plan
- [ ] First payment processes
- [ ] Subsequent payments trigger webhooks
- [ ] Plan completes after all payments
- [ ] Cancel installment plan works

### ✅ Webhooks
- [ ] `payment_intent.succeeded` received
- [ ] `invoice.paid` received
- [ ] `invoice.payment_failed` handled
- [ ] `customer.subscription.deleted` handled
- [ ] `customer.subscription.updated` handled
- [ ] `charge.refunded` handled
- [ ] `invoice.upcoming` logged

### ✅ Edge Cases
- [ ] Declined card handled
- [ ] Insufficient funds handled
- [ ] Network error handled gracefully
- [ ] Duplicate payment prevented
- [ ] Refund processed correctly

---

## Next Steps

After testing locally:

1. **Deploy to Staging**
   - Update Stripe keys for staging environment
   - Configure production webhook endpoint
   - Test complete flow in staging

2. **Move to Production**
   - **Switch to Live Mode** in Stripe Dashboard
   - Get **live API keys** (`sk_live_` and `pk_live_`)
   - Update production `.env` with live keys
   - Configure production webhooks
   - **Test with real $0.50 transaction**
   - Monitor for first week

3. **Enable Monitoring**
   - Set up Stripe Dashboard alerts
   - Configure logging for failed payments
   - Monitor webhook delivery success rate
   - Track payment success rate

---

## Useful Commands

```bash
# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger invoice.paid
stripe trigger customer.subscription.deleted

# View webhook events
stripe logs tail

# Test webhook endpoint manually
stripe trigger payment_intent.succeeded --override customer=cus_test123

# Verify webhook signature locally
stripe webhooks verify <payload> <signature> <secret>
```

---

## Resources

- **Stripe API Docs:** https://stripe.com/docs/api
- **Test Cards:** https://stripe.com/docs/testing
- **Webhook Testing:** https://stripe.com/docs/webhooks/test
- **Stripe CLI Docs:** https://stripe.com/docs/stripe-cli

---

## Summary

✅ **You're Ready When:**
- Stripe CLI forwards webhooks successfully
- Test payments complete end-to-end
- Database shows correct payment records
- All 8 webhook events are handled
- Failed payments log correctly

**Estimated Setup Time:** 15-20 minutes
**Status:** Ready for local testing ✨

---

**Last Updated:** 2025-11-25
**Version:** 1.0
**For:** CSF Backend Development Team
