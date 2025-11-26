# Milestone 2: Child Registration & Customizable Waivers

## Overview
Enable parents to add children to their account and accept required waivers before enrollment.

---

## Tasks

### Phase 1: Child Model & Database

#### Task 1.1: Create Child Model
**File:** `app/models/child.py`

**Fields (from CSF Software.pdf §2.3):**
- `id` (UUID)
- `user_id` (FK to users - parent)
- `first_name`, `last_name` (String)
- `date_of_birth` (Date)
- `jersey_size` (Enum: XS, S, M, L, XL, XXL)
- `grade` (Enum: Pre-K, K, 1-12)
- `medical_conditions` (Text, encrypted) + `has_no_medical_conditions` (Bool)
- `after_school_attendance` (Bool) + `after_school_program` (Text, optional)
- `health_insurance_number` (String, encrypted, optional)
- `how_heard_about_us` (Enum + other_text)
- `is_active` (Bool)
- Timestamps

**Relationships:**
- `user` → User (parent)
- `emergency_contacts` → EmergencyContact[]

---

#### Task 1.2: Create EmergencyContact Model
**File:** `app/models/child.py` (same file)

**Fields:**
- `id` (UUID)
- `child_id` (FK to children)
- `name` (String)
- `relationship` (String - e.g., "Grandmother", "Uncle")
- `phone` (String)
- `email` (String, optional)
- `is_primary` (Bool)
- Timestamps

---

#### Task 1.3: Create PII Encryption Utility
**File:** `app/utils/encryption.py`

**Requirements:**
- Fernet symmetric encryption
- `encrypt_pii(plaintext) -> ciphertext`
- `decrypt_pii(ciphertext) -> plaintext`
- Use `ENCRYPTION_KEY` from config

**Encrypted fields:**
- `medical_conditions`
- `health_insurance_number`

---

#### Task 1.4: Create Alembic Migration for Child & EmergencyContact
- Add `children` table
- Add `emergency_contacts` table
- Add indexes

---

### Phase 2: Child Schemas & API

#### Task 2.1: Create Child Schemas
**File:** `app/schemas/child.py`

**Schemas:**
- `ChildCreate` - for adding a child
- `ChildUpdate` - for updating child info
- `ChildResponse` - for API responses (with computed `age`)
- `ChildListResponse` - paginated list

**Validation:**
- DOB must be in the past
- Age derived from DOB
- Jersey size enum validation
- Grade enum validation

---

#### Task 2.2: Create EmergencyContact Schemas
**File:** `app/schemas/child.py` (same file)

**Schemas:**
- `EmergencyContactCreate`
- `EmergencyContactUpdate`
- `EmergencyContactResponse`

---

#### Task 2.3: Create Children API Endpoints
**File:** `api/v1/children.py`

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me/children` | List parent's children |
| POST | `/users/me/children` | Add child |
| GET | `/children/{id}` | Get child details |
| PUT | `/children/{id}` | Update child |
| DELETE | `/children/{id}` | Soft delete child |

**Security:**
- Parent can only access their own children
- Admin/Owner can access any child

---

#### Task 2.4: Create EmergencyContact API Endpoints
**File:** `api/v1/children.py` (same file)

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/children/{id}/emergency-contacts` | List contacts |
| POST | `/children/{id}/emergency-contacts` | Add contact |
| PUT | `/emergency-contacts/{id}` | Update contact |
| DELETE | `/emergency-contacts/{id}` | Delete contact |

---

### Phase 3: Waiver Templates

#### Task 3.1: Create WaiverTemplate Model
**File:** `app/models/waiver.py`

**Fields:**
- `id` (UUID)
- `name` (String - e.g., "Medical Release")
- `waiver_type` (Enum: MEDICAL_RELEASE, LIABILITY, PHOTO_RELEASE, CANCELLATION_POLICY)
- `content` (Text - rich text HTML)
- `version` (Integer - auto-increment per type)
- `is_active` (Bool)
- `is_required` (Bool)
- `applies_to_program_id` (FK, optional - null = global)
- `applies_to_school_id` (FK, optional)
- Timestamps

**Class methods:**
- `get_active_waivers(program_id, school_id)` - Get required waivers for context
- `get_latest_version(waiver_type)` - Get latest version number

---

#### Task 3.2: Create WaiverAcceptance Model
**File:** `app/models/waiver.py` (same file)

**Fields:**
- `id` (UUID)
- `user_id` (FK to users - the signer)
- `waiver_template_id` (FK to waiver_templates)
- `waiver_version` (Integer - copy of template version at acceptance time)
- `signer_name` (String - full name entered)
- `signer_ip` (String - IP address)
- `signer_user_agent` (String - browser UA)
- `accepted_at` (DateTime with timezone)
- Timestamps

**Unique constraint:** One acceptance per user per waiver_type (can re-accept new versions)

---

#### Task 3.3: Create Alembic Migration for Waivers
- Add `waiver_templates` table
- Add `waiver_acceptances` table
- Seed 4 default waiver templates (Medical, Liability, Photo, Cancellation)

---

### Phase 4: Waiver Schemas & API

#### Task 4.1: Create Waiver Schemas
**File:** `app/schemas/waiver.py`

**Schemas:**
- `WaiverTemplateCreate` (admin)
- `WaiverTemplateUpdate` (admin)
- `WaiverTemplateResponse`
- `WaiverAcceptanceCreate` (includes signer_name)
- `WaiverAcceptanceResponse`
- `RequiredWaiversResponse` (list of waivers user needs to accept)

---

#### Task 4.2: Create Waiver API Endpoints
**File:** `api/v1/waivers.py`

**Public Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/waivers/required` | Get required waivers for current user |
| GET | `/waivers/required/{class_id}` | Get required waivers for specific class |
| POST | `/waivers/accept` | Accept waivers (batch) |
| GET | `/waivers/my-acceptances` | List user's waiver acceptances |

**Admin Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/waivers/templates` | List all templates |
| POST | `/waivers/templates` | Create template (creates new version) |
| PUT | `/waivers/templates/{id}` | Update template (creates new version) |
| GET | `/waivers/templates/{id}` | Get template details |

---

#### Task 4.3: Implement Re-consent Logic
**Service:** `app/services/waiver_service.py`

**Logic:**
- When new waiver version published, mark previous acceptances as "outdated"
- `needs_reconsent(user_id)` - Check if user needs to re-accept any waivers
- Block checkout if required waivers not accepted (handled in enrollment service later)

---

### Phase 5: Testing

#### Task 5.1: Child & EmergencyContact Tests
**File:** `tests/test_children.py`

**Test cases:**
- Add child success
- Add child with emergency contact
- Update child
- Delete child
- List children (only own)
- Admin can access any child
- Age calculation from DOB
- PII encryption/decryption

---

#### Task 5.2: Waiver Tests
**File:** `tests/test_waivers.py`

**Test cases:**
- Get required waivers
- Accept waiver (captures IP, UA, timestamp)
- Accept multiple waivers at once
- Re-consent required after version update
- Admin create/update waiver template
- New version auto-increments

---

## Enums to Create

```python
# app/models/child.py
class JerseySize(str, Enum):
    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"
    XXL = "xxl"

class Grade(str, Enum):
    PRE_K = "pre_k"
    KINDERGARTEN = "k"
    GRADE_1 = "1"
    GRADE_2 = "2"
    # ... through 12
    GRADE_12 = "12"

class HowHeardAboutUs(str, Enum):
    FRIEND = "friend"
    SOCIAL_MEDIA = "social_media"
    SCHOOL = "school"
    FLYER = "flyer"
    GOOGLE = "google"
    OTHER = "other"

# app/models/waiver.py
class WaiverType(str, Enum):
    MEDICAL_RELEASE = "medical_release"
    LIABILITY = "liability"
    PHOTO_RELEASE = "photo_release"
    CANCELLATION_POLICY = "cancellation_policy"
```

---

## Database Schema

```
children
├── id (PK)
├── user_id (FK → users)
├── first_name
├── last_name
├── date_of_birth
├── jersey_size
├── grade
├── medical_conditions_encrypted
├── has_no_medical_conditions
├── after_school_attendance
├── after_school_program
├── health_insurance_number_encrypted
├── how_heard_about_us
├── how_heard_other_text
├── is_active
├── created_at
└── updated_at

emergency_contacts
├── id (PK)
├── child_id (FK → children)
├── name
├── relationship
├── phone
├── email
├── is_primary
├── created_at
└── updated_at

waiver_templates
├── id (PK)
├── name
├── waiver_type
├── content (HTML)
├── version
├── is_active
├── is_required
├── applies_to_program_id (FK, nullable)
├── applies_to_school_id (FK, nullable)
├── created_at
└── updated_at

waiver_acceptances
├── id (PK)
├── user_id (FK → users)
├── waiver_template_id (FK → waiver_templates)
├── waiver_version
├── signer_name
├── signer_ip
├── signer_user_agent
├── accepted_at
├── created_at
└── updated_at
```

---

## Success Criteria

- [ ] Parent can add/edit/delete children
- [ ] Emergency contacts can be managed per child
- [ ] PII fields are encrypted at rest
- [ ] 4 default waiver templates seeded
- [ ] User can view and accept required waivers
- [ ] Waiver acceptance captures: name, IP, UA, timestamp, version
- [ ] Admin can create/update waiver templates
- [ ] New template version triggers re-consent requirement
- [ ] All tests passing

---

## Estimated Tasks: 15
## Priority: High (blocks enrollment flow)

---

**Created:** 2025-11-24
**Status:** Planning
