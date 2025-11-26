# PII Encryption Setup Guide

## Issue Fixed ✅
The `ValueError: ENCRYPTION_KEY not configured` error has been resolved.

---

## What is PII Encryption?

The CSF Backend encrypts **Personally Identifiable Information (PII)** before storing it in the database to protect sensitive data like:
- Medical conditions
- Health insurance numbers
- Any other sensitive personal information

This uses **Fernet symmetric encryption** from the `cryptography` library.

---

## The Error

When you try to create a child with medical conditions, the API calls `encrypt_pii()` which requires an `ENCRYPTION_KEY` environment variable:

```python
# In api/v1/children.py
medical_conditions_encrypted=encrypt_pii(data.medical_conditions)
```

If `ENCRYPTION_KEY` is not set, you get:
```
ValueError: ENCRYPTION_KEY not configured
```

---

## Fix Applied ✅

### 1. Generated Encryption Key
A secure Fernet key has been generated and added to your `.env` file:

```bash
ENCRYPTION_KEY=lcUKk96sknbfFlmZ5N_jyOau-s-sm-NyWDdFwjECWAo=
```

### 2. Updated .env.example
Added encryption key placeholder with generation instructions.

---

## How to Generate Your Own Key

If you need to generate a new encryption key (e.g., for production):

### Method 1: Using Python directly
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))"
```

### Method 2: Using the utility function
```python
from app.utils.encryption import generate_encryption_key

key = generate_encryption_key()
print(key)
```

### Method 3: Using uv run
```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))"
```

---

## Environment Configuration

Your `.env` file should now have:

```bash
# Encryption (Fernet key for PII encryption)
ENCRYPTION_KEY=lcUKk96sknbfFlmZ5N_jyOau-s-sm-NyWDdFwjECWAo=
```

---

## Encryption Functions

The encryption utility provides three functions:

### 1. `encrypt_pii(plaintext: str) -> str`
Encrypts sensitive data before storing in database.

```python
from app.utils.encryption import encrypt_pii

encrypted = encrypt_pii("Asthma - requires inhaler")
# Returns: base64-encoded encrypted string
```

### 2. `decrypt_pii(ciphertext: str) -> str`
Decrypts data when reading from database.

```python
from app.utils.encryption import decrypt_pii

decrypted = decrypt_pii(encrypted_data)
# Returns: original plaintext
```

### 3. `generate_encryption_key() -> str`
Generates a new Fernet encryption key.

```python
from app.utils.encryption import generate_encryption_key

new_key = generate_encryption_key()
```

---

## What Data is Encrypted?

Currently, these fields are encrypted:

### Child Model
- `medical_conditions` - Encrypted in database, decrypted on read
- `health_insurance_number` - Encrypted in database, decrypted on read

These fields are automatically encrypted when saving and decrypted when reading:

```python
# In api/v1/children.py
child = Child(
    ...,
    medical_conditions_encrypted=encrypt_pii(data.medical_conditions),
    health_insurance_number_encrypted=encrypt_pii(data.health_insurance_number)
)
```

---

## Security Best Practices

### ✅ DO:
- **Generate unique keys per environment** (dev, staging, production)
- **Store keys in secure secret management** (AWS Secrets Manager, Vault, etc.)
- **Never commit keys to version control** (`.env` is in `.gitignore`)
- **Rotate keys periodically** (with migration plan)
- **Use strong keys** (Fernet generates 256-bit keys automatically)

### ❌ DON'T:
- Don't use the same key across environments
- Don't share keys via email or chat
- Don't hardcode keys in source code
- Don't lose the key (encrypted data becomes unrecoverable!)

---

## Key Rotation (Advanced)

If you need to rotate the encryption key:

1. Generate a new key
2. Keep the old key temporarily
3. Decrypt all data with old key
4. Re-encrypt with new key
5. Update `ENCRYPTION_KEY` in environment
6. Remove old key

**Example migration script:**

```python
# migrations/scripts/rotate_encryption_key.py
from app.models.child import Child
from app.utils.encryption import decrypt_pii, encrypt_pii
from cryptography.fernet import Fernet

OLD_KEY = "old-key-here"
NEW_KEY = "new-key-here"

async def rotate_keys(db_session):
    # Get all children
    children = await Child.get_all(db_session)

    for child in children:
        if child.medical_conditions_encrypted:
            # Decrypt with old key
            old_fernet = Fernet(OLD_KEY.encode())
            decrypted = old_fernet.decrypt(
                child.medical_conditions_encrypted.encode()
            ).decode()

            # Re-encrypt with new key
            new_fernet = Fernet(NEW_KEY.encode())
            child.medical_conditions_encrypted = new_fernet.encrypt(
                decrypted.encode()
            ).decode()

    await db_session.commit()
```

---

## Testing the Fix

After setting the encryption key, restart the server:

```bash
# The server should start without errors
uv run uvicorn main:app --reload
```

Test creating a child with medical conditions:

```bash
curl -X POST "http://localhost:8000/api/v1/children/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Emma",
    "last_name": "Smith",
    "date_of_birth": "2015-06-15",
    "jersey_size": "m",
    "medical_conditions": "Asthma - requires inhaler",
    "emergency_contacts": [
      {
        "name": "John Smith",
        "relation": "father",
        "phone": "555-0123",
        "email": "john@example.com",
        "is_primary": true
      }
    ]
  }'
```

Should return success with child data (medical conditions will be encrypted in DB).

---

## Verifying Encryption in Database

The data is encrypted at rest in PostgreSQL:

```sql
-- Check the encrypted value in database
SELECT
    first_name,
    last_name,
    medical_conditions_encrypted
FROM children
WHERE first_name = 'Emma';

-- Result shows encrypted string:
-- "gAAAAABl..." (base64-encoded Fernet token)
```

When you fetch via API, it's automatically decrypted:

```bash
curl http://localhost:8000/api/v1/children/my \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response shows decrypted value:
# "medical_conditions": "Asthma - requires inhaler"
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Generate unique encryption key for production
- [ ] Store key in secure secret manager (AWS Secrets Manager, etc.)
- [ ] Set `ENCRYPTION_KEY` environment variable in production
- [ ] Test encryption/decryption works
- [ ] Never log decrypted PII data
- [ ] Ensure backups are also encrypted
- [ ] Document key recovery process

---

## Troubleshooting

### Error: "Failed to decrypt data - invalid token or key mismatch"
**Cause**: The encryption key changed after data was encrypted.

**Solution**:
- Restore the original encryption key, OR
- Run key rotation script to re-encrypt all data

### Error: "ENCRYPTION_KEY not configured"
**Cause**: Environment variable not set or empty.

**Solution**:
```bash
# Generate key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('utf-8'))"

# Add to .env file
echo "ENCRYPTION_KEY=YOUR_GENERATED_KEY_HERE" >> .env

# Restart server
uv run uvicorn main:app --reload
```

### Error: Server not picking up new .env value
**Cause**: Server needs restart to reload environment variables.

**Solution**:
```bash
# Kill server
pkill -f uvicorn

# Restart
uv run uvicorn main:app --reload
```

---

## Additional Resources

- [Cryptography Documentation](https://cryptography.io/en/latest/fernet/)
- [Fernet Specification](https://github.com/fernet/spec/)
- [OWASP Data Encryption Guide](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

---

**Last Updated:** 2025-11-24
**Status:** ✅ CONFIGURED AND WORKING
