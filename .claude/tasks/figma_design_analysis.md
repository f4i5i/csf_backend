# Figma Design Analysis - Complete Feature Breakdown

**Date:** 2025-11-25
**Source:** Carolina Soccer Factory Figma Designs
**Views Analyzed:** Student/Parent + Coach/Admin

---

## 🚨 CRITICAL FINDINGS

The actual application is **MUCH MORE** than just registration/payments. It's a **complete class management and engagement platform** with:

1. **Social Features** - Announcements, photos
2. **Gamification** - Badges/achievements system
3. **Operations** - Attendance tracking, check-in
4. **Communication** - Text messaging to class
5. **Multi-location** - Coach managing multiple locations

---

## Navigation Structure

### Student/Parent Navigation:
```
Dashboard | Calendar | Attendance | Photos | Badges
```

### Coach/Admin Navigation:
```
Dashboard | Calendar | Check-In | Attendance | Photos | Badges
```

### Settings Menu (Dropdown):
```
- Profile
- Payment & Billing
- Contact
- Password
- Log out
```

---

## Screen-by-Screen Analysis

### 1. LOGIN SCREEN ✅

**File:** `Login - Empty State.png`

**Elements:**
- Logo (Carolina Soccer Factory shield)
- "Welcome Back" heading
- Email Address field (required)
- Password field (required, with show/hide toggle)
- "Keep me login" checkbox
- "Forgot Password?" link
- "Login" button (yellow/gold)
- "Don't have an account? Register" link
- Footer: Privacy | Get Help

**Backend Status:** ✅ IMPLEMENTED
- We have: `/api/v1/auth/login`, `/api/v1/auth/register`
- Missing: "Keep me logged in" (remember me token)

---

### 2. STUDENT DASHBOARD ✅ (Partial)

**File:** `Dashboard.png`

**Top Bar:**
- "Welcome back, Anton! 👋"
- School info: "Davidson Elementary • Grade 4 • Wednesdays"
- **Stats:**
  - "50" - Attendance Streak
  - "15" - Badges Earned

**Left Panel - Announcements Feed:**
- Post 1: "Tournament This Saturday"
  - Posted by: Coach Martinez (Oct 27, 2025, 10:30 AM)
  - Attachment: "teamList.pdf"
  - Body text describing tournament

- Post 2: "New Team Jerseys"
  - Posted by: Coach Martinez
  - Attachment: "image-2.jpg"

- Post 3: Another announcement from Coach Martinez

**Right Panel Widgets:**
- **Mini Calendar** (October 2025)
  - Event markers on dates (orange dots)

- **Next Event Card:**
  - "02:00" - "Tournament Day" - "29 Oct 2025"
  - Description: "Annual soccer tournament..."
  - Attachment: "details.pdf"
  - "Write call" link

- **Program Photos Carousel:**
  - Photo with caption "Oct 26, 2024"
  - Navigation arrows

- **Earned Badges:**
  - "Perfect Attendance" badge shown
  - Badge counter: "1/5"
  - Navigation arrows

**Backend Status:**
- ✅ User info, school
- ❌ **MISSING: Announcements/Posts system** (CRITICAL)
- ❌ **MISSING: Attendance streak calculation**
- ❌ **MISSING: Badges system** (CRITICAL)
- ❌ **MISSING: Events system** (separate from classes)
- ❌ **MISSING: Photo gallery**
- ❌ **MISSING: File attachments for posts**

---

### 3. CALENDAR VIEW 📅

**File:** `Calendar.png`

**Elements:**
- Full calendar view (January 2025)
- Monthly navigation (< >)
- Mini calendar on left (October 2025) with highlighted dates

**Event Types (Color-coded):**
- **Dark Blue:** "Tournament" (10 AM - 11 AM)
- **Yellow/Gold:** "Match Day" (10 AM - 11 AM)
- **Yellow/Gold:** "Training sess..." (10 AM - 11 AM)
- **Dark Blue:** "Workshop" (10 AM - 11 AM)

**Event Detail (Left Panel):**
- Date: "October 8, 2025"
- Time: "02:00"
- Title: "Tournament Day"
- Description: "Annual soccer tournament. All teams will compete. Please arrive 30 minutes early for warm-up."
- Attachment: "details.pdf" (downloadable)

**Backend Status:**
- ❌ **MISSING: Events system** (separate from Classes)
  - Events are NOT the same as recurring classes
  - Events are one-time occurrences (tournaments, matches, workshops)
  - Need: Event model, Event API, Event types enum

**Required API Endpoints:**
```
GET /api/v1/events/ - List events for student
GET /api/v1/events/{id} - Event details
POST /api/v1/events/ - Create event (coach only)
PUT /api/v1/events/{id} - Update event (coach only)
DELETE /api/v1/events/{id} - Delete event (coach only)
GET /api/v1/events/calendar?month=2025-01 - Calendar view data
```

---

### 4. ATTENDANCE TRACKING 📊

**File:** `Attendance.png`

**Top Section - Achievement Badges:**
- Horizontal scrollable badges carousel
- Badge types shown:
  - "Perfect Attendance" (trophy icon)
  - "Leadership" (thumbs up)
  - "Star Performer" (star)
  - "Quick Learner" (highlighted - with details)
  - "Team Player" (soccer ball)
  - "Team Player" (another one)

**Quick Learner Badge Detail:**
- "Mastered new techniques"
- "Achieved: Sep 28, 2024"

**Attendance History:**
- List of dates with status
- ✅ Green checkmark = Present
- ❌ Red X = Absent
- Dates shown:
  - Oct 24, 2024 - Present
  - Oct 21, 2024 - Present
  - Oct 17, 2024 - Present
  - Oct 14, 2024 - Present
  - Oct 13, 2024 - Absent
  - Oct 12, 2024 - Present

**Backend Status:**
- ❌ **MISSING: Attendance model**
- ❌ **MISSING: Attendance API endpoints**
- ❌ **MISSING: Badges/Achievements system** (CRITICAL)

**Required Models:**
```python
class Attendance(Base):
    id: UUID
    child_id: UUID  # FK to Child
    class_instance_id: UUID  # FK to ClassInstance (specific session)
    date: date
    status: AttendanceStatus  # present, absent, excused
    marked_by: UUID  # FK to User (coach)
    marked_at: datetime
    notes: str (optional)

class Badge(Base):
    id: UUID
    name: str  # "Perfect Attendance", "Leadership", etc.
    description: str
    icon: str  # icon identifier
    criteria: dict  # JSON - achievement criteria

class StudentBadge(Base):
    id: UUID
    student_id: UUID  # FK to Child
    badge_id: UUID  # FK to Badge
    achieved_at: datetime
    is_locked: bool
```

---

### 5. BADGES/ACHIEVEMENTS 🏆

**File:** `Badges.png`

**Achievements Section:**
- Same scrollable carousel as Attendance view
- Shows earned badges

**Locked Badges Section:**
- "Keep working to unlock these achievements"
- Badge cards showing:
  - "Perfect Attendance" - "Completed the sprint drill under 10 seconds"
  - "Sharpshooter" - "Score 5 goals in a single match"
  - "MVP" - "Nominate Most Valuable Player of the season"
  - "Early Bird" - "Arrive early to practice 20 times"

**Backend Status:**
- ❌ **MISSING: Complete badges system**
  - Badge definitions
  - Achievement criteria
  - Unlocking logic
  - Progress tracking

---

### 6. PHOTOS GALLERY 📸

**File:** `Photos.png` (Student view)

**Elements:**
- Grid of photos (masonry layout)
- Various soccer-related photos
- User menu dropdown visible:
  - Profile
  - Payment & Billing
  - Contact
  - Password
  - Log out

**File:** `Photos Coach view.png` (Coach upload)

**Modal:** "Upload Photos"
- Photo upload area: "Click to upload photos (PNG, JPG up to 10MB each)"
- **Categories (multi-select chips):**
  - Everyone
  - Morning Session
  - Afternoon Session
  - Evening Session
  - Weekend Warriors
- Cancel / Upload Photos buttons

**Backend Status:**
- ❌ **MISSING: Photo gallery system** (CRITICAL)

**Required Models:**
```python
class Photo(Base):
    id: UUID
    uploaded_by: UUID  # FK to User (coach)
    file_url: str  # S3/storage URL
    file_size: int
    mime_type: str
    caption: str (optional)
    uploaded_at: datetime

class PhotoCategory(Base):
    id: UUID
    photo_id: UUID  # FK to Photo
    category: str  # "Morning Session", "Everyone", etc.
```

**Required API Endpoints:**
```
POST /api/v1/photos/ - Upload photo (coach)
GET /api/v1/photos/ - List photos (filtered by category)
DELETE /api/v1/photos/{id} - Delete photo (coach)
GET /api/v1/photos/categories - List available categories
```

---

### 7. SETTINGS - ACCOUNT ⚙️

**File:** `Settings - Plan.png`

**Tabs:**
- My Account (active)
- Payment & Billing
- Password
- Badges
- Contact

**Account Settings Form:**
- Full Name: "Robert Johnson"
- Email Address: "robertjohnson@gmail.com"
- Phone Number (optional): "+1 (212) 555 4567"

**Buttons:**
- Cancel
- Save Changes

**Backend Status:**
- ✅ User model has these fields
- ✅ Update profile endpoint exists

---

### 8. SETTINGS - PAYMENT & BILLING 💳

**File:** `Settings - Plan (1).png`

**Payment Section:**
- Saved card: "•••• •••• •••• 1212" (Visa/Mastercard logos)
- Expiry: "10/23"
- More options menu (...)

**Billing Section:**
- "Review and update your billing information to ensure accurate and timely payments"
- **Billing Period:** "Next billing on Oct 18, 2025"
- **Membership:**
  - "$79 /month"
  - "Your active subscription plan"
- **Cancel Plan** (red link)

**Invoice History Table:**
| Invoice # | Date | Plan | Amount |
|-----------|------|------|--------|
| #018298 | Jan 20, 2025 | Pro Plan | $79 | ⬇️ |

**Backend Status:**
- ✅ Payment methods - IMPLEMENTED
- ✅ Subscription billing - IMPLEMENTED
- ✅ Invoice tracking - PARTIALLY (need invoice history endpoint)
- ❌ **MISSING: Invoice download/export**
- ❌ **MISSING: Pro Plan / plan types**

---

### 9. COACH DASHBOARD 👨‍🏫

**File:** `Dashboard Coach view.png`

**Top Bar:**
- "Welcome back, Coach! 👋"
- "Managing 3 locations • 45 active students"
- **Stats:**
  - "50" - Checked In Today
  - "15" - Announcements

**Left Panel - Announcements:**
- "+ New Post" button (prominent)
- Same announcement feed as student view
- Coach can create/edit posts

**Right Panel:**
- Same widgets as student view
- Calendar
- Next Event
- Program Photos

**Backend Status:**
- ❌ **MISSING: Coach/location relationship**
  - Coach can manage multiple locations
  - Need: location assignment

- ❌ **MISSING: Active students count**
  - Need: endpoint to get coach's total students across all classes

---

### 10. CREATE NEW POST ✍️

**File:** `New post.png`

**Form Fields:**
- **Title** (required)
- **Description** (required) - Rich text area with character counter "0/200"
- **Attachments** (required) - Drag & drop or Browse
  - Shows: "teamList.pdf" with remove (×)
- **Classes** (required) - Multi-select chips:
  - Everyone
  - Morning Session
  - Afternoon Session
  - Evening Session
  - Weekend Warriors

**Buttons:**
- Cancel
- Submit

**Backend Status:**
- ❌ **MISSING: Announcements system** (CRITICAL)

**Required Models:**
```python
class Announcement(Base):
    id: UUID
    title: str
    description: str  # max 200 chars based on UI
    author_id: UUID  # FK to User (coach)
    created_at: datetime
    updated_at: datetime

class AnnouncementAttachment(Base):
    id: UUID
    announcement_id: UUID
    file_url: str
    file_name: str
    file_size: int

class AnnouncementTarget(Base):
    id: UUID
    announcement_id: UUID
    target_type: str  # "everyone", "class"
    class_id: UUID (optional)  # FK to Class
```

**Required API Endpoints:**
```
POST /api/v1/announcements/ - Create announcement (coach)
GET /api/v1/announcements/ - List announcements (filtered by student's classes)
PUT /api/v1/announcements/{id} - Update announcement (coach)
DELETE /api/v1/announcements/{id} - Delete announcement (coach)
POST /api/v1/announcements/{id}/attachments - Upload attachment
```

---

### 11. STUDENT CHECK-IN (Coach View) ✅

**File:** `Details.png`

**Context:** This is when coach clicks on a student from the check-in list

**Modal Content:**
- Student name: "Anton G."
- Edit button

**Contact Information:**
- Parent/Guardian: Maria Garcia
- Phone: (555) 123-4567
- Email: maria.garcia@email.com

**Medical Information:**
- Allergies: None
- Conditions: None

**After School:**
- Yes

**Additional Notes:**
- "Advanced skills, consider moving to competitive team"

**Backend Status:**
- ✅ Child model exists
- ❌ **MISSING Fields on Child model:**
  - `grade` (shown in Student list as "Grade 4")
  - `after_school` (boolean)
  - `additional_notes` (text field)

**Required Updates:**
```python
class Child(Base):
    # ... existing fields ...
    grade: str  # "Grade 4", "Grade 5", etc.
    after_school: bool = False
    additional_notes: str (optional)
```

---

### 12. CHECK-IN SCREEN (Coach) 📋

**File:** `Student Check-In.png`

**Top Bar:**
- Search field
- Location dropdown: "Davidson Elementary"
- "Text Class" button (blue)

**Student List:**
- "Students (3/5)" - Shows 3 out of 5 checked in
- Sort: "Alphabetical" dropdown

**Students:**
1. ✅ Alex T. - Grade 6 - (checked in, green checkmark)
2. ⭕ Olivia C. - Grade 7 - (not checked in, empty circle)
3. ✅ James L. - Grade 3 - (checked in, green checkmark)
4. ⭕ Emma R. - Grade 5 - (not checked in)
5. ✅ Michael K. - Grade 4 - (checked in, green checkmark)

**Each row has:**
- Student photo
- Name
- Grade
- Document icon (view details)

**Backend Status:**
- ❌ **MISSING: Check-in system** (CRITICAL for coaches)

**Required Models:**
```python
class CheckIn(Base):
    id: UUID
    child_id: UUID  # FK to Child
    class_instance_id: UUID  # FK to ClassInstance
    checked_in_at: datetime
    checked_in_by: UUID  # FK to User (coach)
    location_id: UUID  # FK to School
```

**Required API Endpoints:**
```
POST /api/v1/check-ins/ - Check in student
GET /api/v1/check-ins/class/{class_instance_id} - Get check-ins for session
GET /api/v1/check-ins/student/{child_id} - Get student check-in history
POST /api/v1/check-ins/text-class - Send text to all students in class
```

---

### 13. ATTENDANCE HISTORY (Coach) 📊

**File:** `Attendance.png` (Coach view)

**Same as student view but coach can:**
- Mark attendance
- View all students' attendance
- Award badges

---

### 14. GET IN TOUCH 📧

**File:** `get in touch.png`

**Form Fields:**
- First Name
- Last Name
- "Enter your e-mail"
- "Enter your message" (text area)
- "Send Message" button

**Contact Info:**
- Phone: 00 445 000 2234
- Email: company@gmail.com
- Location: 6391 Elgin St. Celina, USA

**Backend Status:**
- ❌ **MISSING: Contact form endpoint**

**Required:**
```
POST /api/v1/contact - Send contact message
```

---

## MASSIVE FEATURE GAPS 🚨

### What We Built (But They Don't Need):
1. ❌ **Programs & Areas API** - NOT shown in UI at all
2. ❌ **Waivers system** - NOT shown in any screen
3. ❌ **Complex discount codes** - Not visible in UI
4. ❌ **Installment payments** - Only subscription shown ($79/month)

### What They Actually Need (But We Don't Have):

#### CRITICAL (Must Have):
1. ❌ **Announcements/Posts System**
   - Create, edit, delete posts
   - File attachments
   - Target specific classes
   - Rich text descriptions

2. ❌ **Attendance Tracking**
   - Mark present/absent
   - Attendance history
   - Attendance streak calculation

3. ❌ **Badges/Achievements**
   - Badge definitions
   - Badge criteria
   - Award badges
   - Track progress
   - Locked/unlocked states

4. ❌ **Photo Gallery**
   - Upload photos
   - Categorize by session
   - View/browse photos

5. ❌ **Events System** (NOT classes)
   - One-time events (tournaments, matches)
   - Event types
   - Event details with attachments
   - Calendar integration

6. ❌ **Check-In System**
   - Check students in/out
   - Location-based check-in
   - Check-in history
   - Real-time status

#### IMPORTANT (Should Have):
7. ❌ **Text Messaging to Class**
   - Send SMS to all students in a class
   - Twilio integration

8. ❌ **File Attachments**
   - PDF uploads for announcements
   - Image uploads for posts
   - S3/storage integration

9. ❌ **Child Model Updates**
   - Grade field
   - After School boolean
   - Additional notes field

10. ❌ **Location Management**
    - Coach assigned to multiple locations
    - Location dropdown in check-in

11. ❌ **Invoice History**
    - List past invoices
    - Download invoices

#### NICE TO HAVE:
12. ❌ **Attendance Streak**
    - Calculate consecutive attendance
    - Display on dashboard

13. ❌ **Badge Counter**
    - "15 Badges Earned" stat
    - Badge progress tracking

---

## What We Over-Built 🔧

These features exist in backend but NOT in UI:

1. **Programs API** (`api/v1/programs.py`) - 5 endpoints
   - Not shown anywhere in UI
   - Seems unnecessary

2. **Areas API** (`api/v1/areas.py`) - 5 endpoints
   - Not shown anywhere in UI
   - Seems unnecessary

3. **Installment Plans** (`api/v1/installments.py`) - 9 endpoints
   - UI only shows "$79/month subscription"
   - No installment UI visible
   - Might not be needed

4. **Complex Waiver System**
   - Rich text waivers
   - Versioning
   - NOT shown in any registration flow

5. **Discount Codes**
   - Not visible in payment UI
   - Maybe admin-only feature?

---

## Corrected Data Model Requirements

### Child Model - NEEDS UPDATES:

**Current:**
```python
class Child(Base):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    medical_info_encrypted: str
    insurance_info_encrypted: str
```

**Required (from Figma):**
```python
class Child(Base):
    # ... existing fields ...
    grade: str  # "Grade 4", "Grade 5", etc. (MISSING)
    after_school: bool = False  # (MISSING)
    additional_notes: str = None  # Coach notes (MISSING)
    allergies: str = None  # Visible in check-in modal
    conditions: str = None  # Visible in check-in modal
```

---

## API Endpoints - What's Missing

### CRITICAL Endpoints to Build:

#### 1. Announcements
```
POST   /api/v1/announcements/           Create announcement (coach)
GET    /api/v1/announcements/           List announcements (student sees filtered)
GET    /api/v1/announcements/{id}       Get announcement details
PUT    /api/v1/announcements/{id}       Update announcement (coach)
DELETE /api/v1/announcements/{id}       Delete announcement (coach)
POST   /api/v1/announcements/{id}/files Upload attachment
```

#### 2. Events (Calendar)
```
POST   /api/v1/events/                  Create event (coach)
GET    /api/v1/events/                  List events
GET    /api/v1/events/{id}              Get event details
PUT    /api/v1/events/{id}              Update event (coach)
DELETE /api/v1/events/{id}              Delete event (coach)
GET    /api/v1/events/calendar          Calendar view data
```

#### 3. Attendance
```
POST   /api/v1/attendance/              Mark attendance (coach)
GET    /api/v1/attendance/student/{id}  Student attendance history
GET    /api/v1/attendance/class/{id}    Class attendance for session
GET    /api/v1/attendance/streak/{id}   Get student's current streak
```

#### 4. Badges
```
GET    /api/v1/badges/                  List all badges
GET    /api/v1/badges/student/{id}      Student's badges (earned + locked)
POST   /api/v1/badges/award             Award badge to student (auto or manual)
GET    /api/v1/badges/progress/{id}     Badge progress for student
```

#### 5. Photos
```
POST   /api/v1/photos/                  Upload photo (coach)
GET    /api/v1/photos/                  List photos (with category filter)
DELETE /api/v1/photos/{id}              Delete photo (coach)
```

#### 6. Check-In
```
POST   /api/v1/check-ins/               Check in student (coach)
GET    /api/v1/check-ins/class/{id}     Get check-ins for class session
POST   /api/v1/check-ins/text-class     Send SMS to class
```

---

## Payment Model - Simplified

**What UI Shows:**
- Only "$79/month subscription"
- Simple payment method management
- Invoice history

**What We Built:**
- Complex installment system (2-12 payments)
- Multiple payment types
- Preview schedules
- Cancellation logic

**Recommendation:**
- Keep subscription system ✅
- Keep one-time payments ✅
- **Maybe remove installment complexity** if not in UI

---

## Key Observations

### 1. Role Structure
- **Student/Parent** - Limited view, see announcements/photos/attendance
- **Coach** - Create content, manage attendance, check-in, upload photos

### 2. Multi-Location Support
- Coaches manage multiple locations
- Check-in is location-specific
- Need School/Location assignment to coaches

### 3. Class Sessions vs Events
- **Classes** - Recurring (Morning Session, Afternoon Session, etc.)
- **Events** - One-time (Tournament Day, Match Day, Workshop)
- These are DIFFERENT entities

### 4. Gamification Focus
- Badges are prominent (shown in 3+ screens)
- Attendance tracking is core
- Achievement system is important

### 5. Communication Features
- Announcements (one-to-many)
- Text messaging to class (SMS)
- Contact form
- Photo sharing

---

## Revised Priority List

### Must Build NOW (Critical Gaps):

1. **Announcements System** (highest priority)
   - Models: Announcement, AnnouncementAttachment, AnnouncementTarget
   - API: 6 endpoints
   - File upload support
   - Estimated: 8 hours

2. **Attendance Tracking**
   - Models: Attendance
   - API: 4 endpoints
   - Estimated: 6 hours

3. **Badges/Achievements**
   - Models: Badge, StudentBadge
   - API: 4 endpoints
   - Badge criteria logic
   - Estimated: 10 hours

4. **Photo Gallery**
   - Models: Photo, PhotoCategory
   - API: 3 endpoints
   - S3/file storage integration
   - Estimated: 6 hours

5. **Events/Calendar**
   - Models: Event, EventType
   - API: 6 endpoints
   - Calendar view logic
   - Estimated: 8 hours

6. **Check-In System**
   - Models: CheckIn
   - API: 3 endpoints
   - Real-time updates
   - Estimated: 5 hours

7. **Child Model Updates**
   - Add: grade, after_school, additional_notes
   - Migration
   - Update schemas
   - Estimated: 2 hours

### Total Estimated: 45 hours

---

## What We Can Remove/Simplify

### Over-Built Features:

1. **Programs API** - Remove (not in UI)
2. **Areas API** - Remove (not in UI)
3. **Installment Plans** - Simplify or remove (only subscription in UI)
4. **Complex waiver system** - Simplify (not shown in registration)
5. **Email automation** - Might be premature (not shown in UI)

---

## Correct Architecture

```
Carolina Soccer Factory Backend
┌─────────────────────────────────────────────────────────┐
│                   Core Features                         │
├─────────────────────────────────────────────────────────┤
│  Authentication │ User/Child Management │ Classes       │
├─────────────────────────────────────────────────────────┤
│              Engagement Features                        │
├─────────────────────────────────────────────────────────┤
│  Announcements │ Photos │ Badges │ Calendar/Events     │
├─────────────────────────────────────────────────────────┤
│              Operations Features                        │
├─────────────────────────────────────────────────────────┤
│  Check-In │ Attendance Tracking │ Text Messaging       │
├─────────────────────────────────────────────────────────┤
│              Payment (Simple)                           │
├─────────────────────────────────────────────────────────┤
│  Subscription ($79/month) │ Payment Methods │ Invoices  │
└─────────────────────────────────────────────────────────┘
```

---

## Immediate Action Items

1. **Stop Building:**
   - No more payment complexity
   - No more email templates (we have enough)
   - No admin dashboard metrics (not shown in UI)

2. **Start Building:**
   - Announcements system (CRITICAL)
   - Attendance tracking (CRITICAL)
   - Badges system (CRITICAL)
   - Check-in system (CRITICAL)

3. **Update Existing:**
   - Child model (add grade, after_school, additional_notes)
   - User profile (verify phone field exists)

4. **Consider Removing:**
   - Programs API (not in UI)
   - Areas API (not in UI)
   - Installment system (if not needed)

---

## Conclusion

**Reality Check:** We've been building a **registration/payment platform** when the actual product is a **class engagement and management platform**.

**Payment is secondary** - it's just "$79/month subscription" in settings.

**Core value is:**
- Coaches managing students
- Attendance and check-in
- Announcements and communication
- Photo sharing
- Gamification (badges)
- Events and calendar

**We need to pivot focus immediately.**

---

**Analysis Date:** 2025-11-25
**Status:** ⚠️ MAJOR GAPS IDENTIFIED
**Action Required:** Discuss priorities with product owner
