# How to Authenticate in Swagger UI

## Issue Fixed ✅
The "unprocessable entity" error when using Swagger's Authorize button has been fixed.

## Changes Made
1. Added new `/api/v1/auth/token` endpoint that accepts OAuth2 form data
2. Updated `OAuth2PasswordBearer` to point to the new endpoint
3. Kept `/api/v1/auth/login` for JSON-based authentication (for frontend)

---

## How to Use Swagger Authentication

### Step 1: Start the server
```bash
uv run uvicorn main:app --reload
```

### Step 2: Open Swagger UI
Navigate to: http://localhost:8000/docs

### Step 3: Create a test user (if needed)
1. Find the **POST /api/v1/auth/register** endpoint
2. Click "Try it out"
3. Enter test user details:
```json
{
  "email": "test@example.com",
  "password": "Test123456",
  "confirm_password": "Test123456",
  "first_name": "Test",
  "last_name": "User"
}
```
4. Click "Execute"

### Step 4: Authorize in Swagger
1. Click the **"Authorize"** button (lock icon) at the top right
2. In the authorization dialog:
   - **username**: Enter your email (e.g., `test@example.com`)
   - **password**: Enter your password (e.g., `Test123456`)
   - Leave `client_id` and `client_secret` empty
3. Click **"Authorize"**
4. Click **"Close"**

### Step 5: Test Protected Endpoints
Now you can test any protected endpoint:
- Try **GET /api/v1/users/me** - Should return your user profile
- Try **GET /api/v1/children/my** - Should return your children list
- Try **GET /api/v1/orders/my** - Should return your orders

---

## Two Login Endpoints Explained

### `/api/v1/auth/token` (OAuth2 - for Swagger)
- Accepts **form data** (username/password)
- Used by Swagger UI's "Authorize" button
- Username field expects email address

### `/api/v1/auth/login` (JSON - for Frontend)
- Accepts **JSON** (email/password)
- Used by your frontend application
- Standard REST API endpoint

Both endpoints return the same token format and work identically.

---

## Troubleshooting

### "Unauthorized" after authenticating
- Make sure you clicked "Authorize" and then "Close"
- The lock icons next to endpoints should be locked (dark)

### "Invalid credentials"
- Check email is correct
- Password must meet requirements (8+ chars, uppercase, lowercase, number)
- Remember: username field in Swagger expects your **email**

### Token expired
- Click "Authorize" again and re-enter credentials
- Access tokens expire after 30 minutes by default

---

## Example Test Flow

1. **Register**: POST /api/v1/auth/register
2. **Authorize**: Click Authorize button, use email/password
3. **Get Profile**: GET /api/v1/users/me
4. **Add Child**: POST /api/v1/children/
5. **Create Order**: POST /api/v1/orders/calculate
6. **Make Payment**: POST /api/v1/orders/{order_id}/pay

All protected endpoints will now include your authentication token automatically!

