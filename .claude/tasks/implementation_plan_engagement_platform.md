# Implementation Plan: Pivot to Class Engagement Platform

**Status**: Ready for Approval
**Estimated Effort**: ~45-50 hours (production-ready with tests)
**Created**: 2025-11-25
**Plan Type**: Complete feature implementation (6 major features)

---

## Executive Summary

### The Pivot
After comprehensive Figma analysis, we've identified a **critical misalignment**: the backend was built as a registration/payment platform, but the actual product is a **class engagement and management platform** with social features, gamification, and coach tools.

### What's Missing (8 Critical Features)
1. **Announcements/Posts System** - Coaches create posts with attachments
2. **Attendance Tracking** - Mark present/absent, track streaks, badges
3. **Badges/Achievements** - Gamification with 15+ badge types
4. **Photo Gallery** - Upload/view class photos by session/category
5. **Events/Calendar** - One-time events (tournaments, workshops)
6. **Check-In System** - Real-time student check-in at locations
7. **Text Messaging** - Send SMS to entire class (lower priority)
8. **File Attachments** - PDF/image uploads for announcements

### User Decisions
- **Scope**: Build features 1-6 together (defer SMS for later)
- **File Storage**: Local filesystem (simple, MVP-focused)
- **Existing Code**: Keep all current features (no removal)
- **Quality**: Production-ready with comprehensive tests

---

## Architecture Patterns (From Codebase Analysis)

### Model Layer Patterns
```python
# 1. All models inherit from Base + TimestampMixin
class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    # 2. UUID as string (36 chars) for all IDs
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # 3. Enums defined at module level
    # (see below)

    # 4. Foreign keys with index=True
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), index=True)

    # 5. Relationships use back_populates
    class_: Mapped["Class"] = relationship("Class", back_populates="announcements")
    attachments: Mapped[List["AnnouncementAttachment"]] = relationship(
        "AnnouncementAttachment",
        back_populates="announcement",
        cascade="all, delete-orphan"  # Cascade deletes
    )

    # 6. Class methods for data access (Repository pattern)
    @classmethod
    async def get_by_class(cls, db_session: AsyncSession, class_id: str):
        stmt = select(cls).where(cls.class_id == class_id).order_by(cls.created_at.desc())
        result = await db_session.execute(stmt)
        return result.scalars().all()

# Enum pattern (str, enum.Enum)
class AnnouncementType(str, enum.Enum):
    GENERAL = "general"
    IMPORTANT = "important"
    URGENT = "urgent"
```

### API Layer Patterns
```python
# 1. Router with prefix and tags
router = APIRouter(prefix="/announcements", tags=["Announcements"])

# 2. Dependency injection for auth and DB
@router.post("/", response_model=AnnouncementResponse)
async def create_announcement(
    data: AnnouncementCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Auth required
):
    # 3. Role-based access control
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create announcements")

    # 4. Use model class methods
    announcement = await Announcement.create(db_session, **data.model_dump(), author_id=current_user.id)

    # 5. Return response schema
    return AnnouncementResponse.model_validate(announcement)

# 6. Pagination pattern
@router.get("/", response_model=AnnouncementListResponse)
async def list_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    class_id: Optional[str] = Query(None),
    db_session: AsyncSession = Depends(get_db),
):
    announcements = await Announcement.get_filtered(db_session, class_id=class_id, skip=skip, limit=limit)
    total = await Announcement.count_filtered(db_session, class_id=class_id)
    return AnnouncementListResponse(items=announcements, total=total, skip=skip, limit=limit)
```

### Schema Layer Patterns
```python
# 1. Inherit from BaseSchema (from_attributes=True)
class AnnouncementCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=500)
    class_ids: List[str] = Field(..., min_items=1)  # Target classes
    type: AnnouncementType = Field(default=AnnouncementType.GENERAL)

class AnnouncementUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    # All fields optional

class AnnouncementResponse(BaseSchema):
    id: str
    title: str
    description: str
    type: AnnouncementType
    author_id: str
    created_at: datetime
    updated_at: datetime
    attachments: List[AnnouncementAttachmentResponse] = []
    # Include relationships

class AnnouncementListResponse(BaseSchema):
    items: List[AnnouncementResponse]
    total: int
    skip: int
    limit: int
```

---

## Feature Breakdown

### Feature 1: Announcements/Posts System (~8 hours)

#### Requirements (from Figma)
- **Dashboard view**: Feed of announcements with title, description, timestamp
- **Create Post modal**: Title, Description (200 char limit), Attachments (drag & drop or browse), Target Classes (multiple selection)
- **Attachment types**: PDFs, Images
- **Coach-only**: Only coaches/admins can create
- **Multi-class targeting**: One post can target multiple classes

#### Database Models

**1. Announcement Model** (`app/models/announcement.py`):
```python
class AnnouncementType(str, enum.Enum):
    GENERAL = "general"
    IMPORTANT = "important"
    URGENT = "urgent"

class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AnnouncementType] = mapped_column(
        Enum(AnnouncementType),
        default=AnnouncementType.GENERAL,
        nullable=False
    )
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    author: Mapped["User"] = relationship("User", back_populates="announcements")
    attachments: Mapped[List["AnnouncementAttachment"]] = relationship(
        "AnnouncementAttachment",
        back_populates="announcement",
        cascade="all, delete-orphan"
    )
    targets: Mapped[List["AnnouncementTarget"]] = relationship(
        "AnnouncementTarget",
        back_populates="announcement",
        cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_class(cls, db_session: AsyncSession, class_id: str, skip: int = 0, limit: int = 20):
        stmt = (
            select(cls)
            .join(AnnouncementTarget)
            .where(
                AnnouncementTarget.class_id == class_id,
                cls.is_active == True
            )
            .options(
                selectinload(cls.author),
                selectinload(cls.attachments)
            )
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def create_with_targets(cls, db_session: AsyncSession, class_ids: List[str], **kwargs):
        announcement = cls(**kwargs)
        db_session.add(announcement)
        await db_session.flush()

        # Create targets
        for class_id in class_ids:
            target = AnnouncementTarget(announcement_id=announcement.id, class_id=class_id)
            db_session.add(target)

        await db_session.commit()
        await db_session.refresh(announcement)
        return announcement
```

**2. AnnouncementAttachment Model**:
```python
class AttachmentType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"

class AnnouncementAttachment(Base, TimestampMixin):
    __tablename__ = "announcement_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    announcement_id: Mapped[str] = mapped_column(String(36), ForeignKey("announcements.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Relative path
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Bytes
    file_type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="attachments")
```

**3. AnnouncementTarget Model** (Many-to-Many):
```python
class AnnouncementTarget(Base, TimestampMixin):
    __tablename__ = "announcement_targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    announcement_id: Mapped[str] = mapped_column(String(36), ForeignKey("announcements.id"), nullable=False, index=True)
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), nullable=False, index=True)

    # Relationships
    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="targets")
    class_: Mapped["Class"] = relationship("Class")

    __table_args__ = (
        UniqueConstraint('announcement_id', 'class_id', name='unique_announcement_class'),
    )
```

#### API Endpoints (`app/api/v1/announcements.py`)

```python
# 1. POST /api/v1/announcements - Create announcement (coach only)
@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create announcement. Coaches/admins only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create announcements")

    announcement = await Announcement.create_with_targets(
        db_session,
        class_ids=data.class_ids,
        title=data.title,
        description=data.description,
        type=data.type,
        author_id=current_user.id
    )
    return AnnouncementResponse.model_validate(announcement)

# 2. GET /api/v1/announcements - List announcements
@router.get("/", response_model=AnnouncementListResponse)
async def list_announcements(
    class_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List announcements for a class."""
    if class_id:
        announcements = await Announcement.get_by_class(db_session, class_id, skip, limit)
        total = await Announcement.count_by_class(db_session, class_id)
    else:
        announcements = await Announcement.get_all(db_session, skip, limit)
        total = await Announcement.count_all(db_session)

    return AnnouncementListResponse(
        items=[AnnouncementResponse.model_validate(a) for a in announcements],
        total=total,
        skip=skip,
        limit=limit
    )

# 3. GET /api/v1/announcements/{id} - Get announcement details
@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get announcement details."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")
    return AnnouncementResponse.model_validate(announcement)

# 4. PUT /api/v1/announcements/{id} - Update announcement
@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update announcement. Author or admin only."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if announcement.author_id != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized to update this announcement")

    await announcement.update(db_session, **data.model_dump(exclude_unset=True))
    return AnnouncementResponse.model_validate(announcement)

# 5. DELETE /api/v1/announcements/{id} - Soft delete
@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete announcement (soft delete). Author or admin only."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if announcement.author_id != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized to delete this announcement")

    announcement.is_active = False
    await db_session.commit()

# 6. POST /api/v1/announcements/{id}/attachments - Upload attachment
@router.post("/{announcement_id}/attachments", response_model=AnnouncementAttachmentResponse)
async def upload_attachment(
    announcement_id: str,
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    """Upload attachment to announcement."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if announcement.author_id != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized to add attachments")

    # Validate file
    if file.size > 10 * 1024 * 1024:  # 10MB limit
        raise ValidationException(message="File too large (max 10MB)")

    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise ValidationException(message="Invalid file type")

    # Save file
    file_path = await file_service.save_announcement_attachment(file)

    # Determine type
    attachment_type = AttachmentType.PDF if file.content_type == "application/pdf" else AttachmentType.IMAGE

    # Create record
    attachment = AnnouncementAttachment(
        announcement_id=announcement_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file.size,
        file_type=attachment_type,
        mime_type=file.content_type
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)

    return AnnouncementAttachmentResponse.model_validate(attachment)
```

#### Schemas (`app/schemas/announcement.py`)

```python
class AnnouncementCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    class_ids: List[str] = Field(..., min_items=1)
    type: AnnouncementType = Field(default=AnnouncementType.GENERAL)

class AnnouncementUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    type: Optional[AnnouncementType] = None

class AnnouncementAttachmentResponse(BaseSchema):
    id: str
    file_name: str
    file_path: str  # Will be converted to URL by frontend
    file_size: int
    file_type: AttachmentType
    mime_type: str
    created_at: datetime

class AnnouncementResponse(BaseSchema):
    id: str
    title: str
    description: str
    type: AnnouncementType
    author_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    attachments: List[AnnouncementAttachmentResponse] = []

class AnnouncementListResponse(BaseSchema):
    items: List[AnnouncementResponse]
    total: int
    skip: int
    limit: int
```

#### Migration
```bash
# Create migration
uv run alembic revision --autogenerate -m "Add announcements system"

# Tables created:
# - announcements
# - announcement_attachments
# - announcement_targets
```

#### Tests (`tests/integration/test_announcements.py`)
- Test create announcement (coach can, parent cannot)
- Test list announcements by class
- Test update announcement (author only)
- Test delete announcement (soft delete)
- Test upload attachment (PDF and image)
- Test file size validation
- Test multi-class targeting

---

### Feature 2: Attendance Tracking (~6 hours)

#### Requirements (from Figma)
- **Attendance view**: Badge carousel + attendance history list
- **Stats**: "50 Attendance Streak" prominently displayed
- **History**: Date, Class, Status (Present/Absent), Streak count
- **Coach tools**: Mark attendance for entire class session
- **Integration**: Attendance unlocks badges

#### Database Models

**Attendance Model** (`app/models/attendance.py`):
```python
class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"

class Attendance(Base, TimestampMixin):
    __tablename__ = "attendances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    enrollment_id: Mapped[str] = mapped_column(String(36), ForeignKey("enrollments.id"), nullable=False, index=True)
    class_instance_id: Mapped[str] = mapped_column(String(36), ForeignKey("class_instances.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    marked_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)  # Coach who marked
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="attendances")
    class_instance: Mapped["ClassInstance"] = relationship("ClassInstance")
    marker: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint('enrollment_id', 'class_instance_id', name='unique_enrollment_instance_attendance'),
        Index('idx_attendance_date_enrollment', 'enrollment_id', 'date'),
    )

    @classmethod
    async def get_streak(cls, db_session: AsyncSession, enrollment_id: str) -> int:
        """Calculate current attendance streak for an enrollment."""
        stmt = (
            select(cls.date, cls.status)
            .where(cls.enrollment_id == enrollment_id)
            .order_by(cls.date.desc())
        )
        result = await db_session.execute(stmt)
        records = result.all()

        if not records:
            return 0

        streak = 0
        for record in records:
            if record.status == AttendanceStatus.PRESENT:
                streak += 1
            else:
                break  # Streak broken

        return streak

    @classmethod
    async def get_by_enrollment(cls, db_session: AsyncSession, enrollment_id: str, skip: int = 0, limit: int = 50):
        """Get attendance history for an enrollment."""
        stmt = (
            select(cls)
            .where(cls.enrollment_id == enrollment_id)
            .options(selectinload(cls.class_instance))
            .order_by(cls.date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def mark_bulk(cls, db_session: AsyncSession, class_instance_id: str, attendance_data: List[dict], marked_by: str):
        """Bulk mark attendance for a class session."""
        for data in attendance_data:
            # Check if already marked
            stmt = select(cls).where(
                cls.enrollment_id == data['enrollment_id'],
                cls.class_instance_id == class_instance_id
            )
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                existing.status = data['status']
                existing.notes = data.get('notes')
            else:
                # Create new
                attendance = cls(
                    enrollment_id=data['enrollment_id'],
                    class_instance_id=class_instance_id,
                    date=data['date'],
                    status=data['status'],
                    marked_by=marked_by,
                    notes=data.get('notes')
                )
                db_session.add(attendance)

        await db_session.commit()
```

#### API Endpoints (`app/api/v1/attendance.py`)

```python
# 1. POST /api/v1/attendance/mark - Mark attendance (bulk)
@router.post("/mark", status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    data: AttendanceMarkBulk,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark attendance for multiple students. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can mark attendance")

    await Attendance.mark_bulk(
        db_session,
        class_instance_id=data.class_instance_id,
        attendance_data=[item.model_dump() for item in data.records],
        marked_by=current_user.id
    )

    return {"message": "Attendance marked successfully"}

# 2. GET /api/v1/attendance/enrollment/{enrollment_id}/history - Get history
@router.get("/enrollment/{enrollment_id}/history", response_model=AttendanceListResponse)
async def get_attendance_history(
    enrollment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance history for enrollment."""
    # Verify access (user owns enrollment or is coach/admin)
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.child.user_id != current_user.id and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    attendances = await Attendance.get_by_enrollment(db_session, enrollment_id, skip, limit)
    total = await Attendance.count_by_enrollment(db_session, enrollment_id)

    return AttendanceListResponse(
        items=[AttendanceResponse.model_validate(a) for a in attendances],
        total=total,
        skip=skip,
        limit=limit
    )

# 3. GET /api/v1/attendance/enrollment/{enrollment_id}/streak - Get streak
@router.get("/enrollment/{enrollment_id}/streak", response_model=AttendanceStreakResponse)
async def get_attendance_streak(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current attendance streak."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.child.user_id != current_user.id and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    streak = await Attendance.get_streak(db_session, enrollment_id)
    return AttendanceStreakResponse(enrollment_id=enrollment_id, streak=streak)

# 4. GET /api/v1/attendance/class-instance/{id} - Get class session attendance
@router.get("/class-instance/{class_instance_id}", response_model=ClassInstanceAttendanceResponse)
async def get_class_instance_attendance(
    class_instance_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance for a specific class session. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view class attendance")

    attendances = await Attendance.get_by_class_instance(db_session, class_instance_id)
    return ClassInstanceAttendanceResponse(
        class_instance_id=class_instance_id,
        records=[AttendanceResponse.model_validate(a) for a in attendances]
    )
```

#### Schemas (`app/schemas/attendance.py`)

```python
class AttendanceMarkRecord(BaseSchema):
    enrollment_id: str
    date: date
    status: AttendanceStatus
    notes: Optional[str] = None

class AttendanceMarkBulk(BaseSchema):
    class_instance_id: str
    records: List[AttendanceMarkRecord] = Field(..., min_items=1)

class AttendanceResponse(BaseSchema):
    id: str
    enrollment_id: str
    class_instance_id: str
    date: date
    status: AttendanceStatus
    notes: Optional[str]
    created_at: datetime

class AttendanceListResponse(BaseSchema):
    items: List[AttendanceResponse]
    total: int
    skip: int
    limit: int

class AttendanceStreakResponse(BaseSchema):
    enrollment_id: str
    streak: int

class ClassInstanceAttendanceResponse(BaseSchema):
    class_instance_id: str
    records: List[AttendanceResponse]
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add attendance tracking"
# Table: attendances
```

#### Tests
- Test mark attendance (bulk)
- Test get attendance history
- Test calculate streak (continuous, broken)
- Test coach-only access
- Test duplicate prevention

---

### Feature 3: Badges/Achievements System (~10 hours)

#### Requirements (from Figma)
- **15+ badge types**: First Goal, Hat Trick, Team Player, Perfect Attendance (5 weeks), Marathon Runner (10 weeks), Century (20 weeks), Punctuality King, Early Bird, Goal Machine, Assist Master, Defensive Wall, Speedster, Endurance, Skills Master, Leadership
- **Badge states**: Locked (gray) vs Unlocked (colored)
- **Progress tracking**: "3/5 weeks" for Perfect Attendance badge
- **Criteria system**: Each badge has unlock criteria
- **Auto-awarding**: System automatically awards badges when criteria met

#### Database Models

**1. Badge Model** (`app/models/badge.py`):
```python
class BadgeCategory(str, enum.Enum):
    ATTENDANCE = "attendance"
    ACHIEVEMENT = "achievement"
    SKILL = "skill"
    MILESTONE = "milestone"

class BadgeCriteria(str, enum.Enum):
    # Attendance-based
    PERFECT_ATTENDANCE_5 = "perfect_attendance_5"  # 5 weeks perfect
    PERFECT_ATTENDANCE_10 = "perfect_attendance_10"  # 10 weeks
    PERFECT_ATTENDANCE_20 = "perfect_attendance_20"  # 20 weeks
    EARLY_BIRD = "early_bird"  # Check in 10 times before class start
    PUNCTUALITY_KING = "punctuality_king"  # Never late

    # Milestone-based
    FIRST_CLASS = "first_class"  # Attend first class
    FIRST_MONTH = "first_month"  # Complete 1 month
    FIRST_SEASON = "first_season"  # Complete full season

    # Manual awards (coach-given)
    FIRST_GOAL = "first_goal"
    HAT_TRICK = "hat_trick"
    TEAM_PLAYER = "team_player"
    GOAL_MACHINE = "goal_machine"
    ASSIST_MASTER = "assist_master"
    DEFENSIVE_WALL = "defensive_wall"
    SPEEDSTER = "speedster"
    ENDURANCE = "endurance"
    SKILLS_MASTER = "skills_master"
    LEADERSHIP = "leadership"

class Badge(Base, TimestampMixin):
    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[BadgeCategory] = mapped_column(Enum(BadgeCategory), nullable=False)
    criteria: Mapped[BadgeCriteria] = mapped_column(Enum(BadgeCriteria), nullable=False, unique=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500))  # Path to badge icon
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    student_badges: Mapped[List["StudentBadge"]] = relationship("StudentBadge", back_populates="badge")

    @classmethod
    async def get_all_active(cls, db_session: AsyncSession):
        """Get all active badges."""
        stmt = select(cls).where(cls.is_active == True).order_by(cls.category, cls.name)
        result = await db_session.execute(stmt)
        return result.scalars().all()

class StudentBadge(Base, TimestampMixin):
    __tablename__ = "student_badges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    enrollment_id: Mapped[str] = mapped_column(String(36), ForeignKey("enrollments.id"), nullable=False, index=True)
    badge_id: Mapped[str] = mapped_column(String(36), ForeignKey("badges.id"), nullable=False, index=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    awarded_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))  # NULL for auto-awarded
    progress: Mapped[Optional[int]] = mapped_column(Integer)  # For progress tracking (e.g., 3/5 weeks)
    progress_max: Mapped[Optional[int]] = mapped_column(Integer)  # Max progress value

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="badges")
    badge: Mapped["Badge"] = relationship("Badge", back_populates="student_badges")
    awarder: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint('enrollment_id', 'badge_id', name='unique_student_badge'),
    )

    @classmethod
    async def get_by_enrollment(cls, db_session: AsyncSession, enrollment_id: str):
        """Get all badges for an enrollment."""
        stmt = (
            select(cls)
            .where(cls.enrollment_id == enrollment_id)
            .options(selectinload(cls.badge))
            .order_by(cls.awarded_at.desc())
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def check_and_award(cls, db_session: AsyncSession, enrollment_id: str):
        """Check criteria and auto-award badges."""
        # Get enrollment
        enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
        if not enrollment:
            return

        # Check attendance-based badges
        streak = await Attendance.get_streak(db_session, enrollment_id)

        # Perfect Attendance 5 weeks
        if streak >= 5:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_5)

        # Perfect Attendance 10 weeks
        if streak >= 10:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_10)

        # Perfect Attendance 20 weeks
        if streak >= 20:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.PERFECT_ATTENDANCE_20)

        # Check first class
        attendance_count = await Attendance.count_by_enrollment(db_session, enrollment_id)
        if attendance_count == 1:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.FIRST_CLASS)

        # Check first month (4+ weeks)
        if streak >= 4:
            await cls.try_award(db_session, enrollment_id, BadgeCriteria.FIRST_MONTH)

        await db_session.commit()

    @classmethod
    async def try_award(cls, db_session: AsyncSession, enrollment_id: str, criteria: BadgeCriteria):
        """Try to award badge if not already awarded."""
        # Get badge
        stmt = select(Badge).where(Badge.criteria == criteria, Badge.is_active == True)
        result = await db_session.execute(stmt)
        badge = result.scalar_one_or_none()

        if not badge:
            return

        # Check if already awarded
        stmt = select(cls).where(cls.enrollment_id == enrollment_id, cls.badge_id == badge.id)
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return  # Already awarded

        # Award badge
        student_badge = cls(
            enrollment_id=enrollment_id,
            badge_id=badge.id,
            awarded_by=None  # Auto-awarded
        )
        db_session.add(student_badge)
```

**2. Update Enrollment Model** (`app/models/enrollment.py`):
```python
# Add to Enrollment model
class Enrollment(Base, TimestampMixin):
    # ... existing fields ...

    # Add relationship
    badges: Mapped[List["StudentBadge"]] = relationship("StudentBadge", back_populates="enrollment", cascade="all, delete-orphan")
```

#### API Endpoints (`app/api/v1/badges.py`)

```python
# 1. GET /api/v1/badges - List all badges
@router.get("/", response_model=BadgeListResponse)
async def list_badges(
    db_session: AsyncSession = Depends(get_db),
):
    """List all available badges (public)."""
    badges = await Badge.get_all_active(db_session)
    return BadgeListResponse(items=[BadgeResponse.model_validate(b) for b in badges])

# 2. GET /api/v1/badges/enrollment/{enrollment_id} - Get student badges
@router.get("/enrollment/{enrollment_id}", response_model=StudentBadgeListResponse)
async def get_student_badges(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get badges for an enrollment with locked/unlocked status."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.child.user_id != current_user.id and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    # Get all badges
    all_badges = await Badge.get_all_active(db_session)

    # Get student's earned badges
    earned = await StudentBadge.get_by_enrollment(db_session, enrollment_id)
    earned_badge_ids = {sb.badge_id for sb in earned}

    # Build response with locked/unlocked status
    items = []
    for badge in all_badges:
        is_unlocked = badge.id in earned_badge_ids
        student_badge = next((sb for sb in earned if sb.badge_id == badge.id), None)

        items.append(StudentBadgeStatusResponse(
            badge=BadgeResponse.model_validate(badge),
            is_unlocked=is_unlocked,
            awarded_at=student_badge.awarded_at if student_badge else None,
            progress=student_badge.progress if student_badge else None,
            progress_max=student_badge.progress_max if student_badge else None,
        ))

    return StudentBadgeListResponse(enrollment_id=enrollment_id, badges=items)

# 3. POST /api/v1/badges/award - Manually award badge (coach only)
@router.post("/award", response_model=StudentBadgeResponse, status_code=status.HTTP_201_CREATED)
async def award_badge(
    data: BadgeAward,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually award a badge to student. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can award badges")

    # Check enrollment exists
    enrollment = await Enrollment.get_by_id(db_session, data.enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check badge exists
    badge = await Badge.get_by_id(db_session, data.badge_id)
    if not badge:
        raise NotFoundException(message="Badge not found")

    # Check not already awarded
    stmt = select(StudentBadge).where(
        StudentBadge.enrollment_id == data.enrollment_id,
        StudentBadge.badge_id == data.badge_id
    )
    result = await db_session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise ValidationException(message="Badge already awarded")

    # Award badge
    student_badge = StudentBadge(
        enrollment_id=data.enrollment_id,
        badge_id=data.badge_id,
        awarded_by=current_user.id
    )
    db_session.add(student_badge)
    await db_session.commit()
    await db_session.refresh(student_badge)

    return StudentBadgeResponse.model_validate(student_badge)

# 4. GET /api/v1/badges/enrollment/{enrollment_id}/progress - Get badge progress
@router.get("/enrollment/{enrollment_id}/progress", response_model=BadgeProgressResponse)
async def get_badge_progress(
    enrollment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get progress towards unlocking badges."""
    enrollment = await Enrollment.get_by_id(db_session, enrollment_id)
    if not enrollment:
        raise NotFoundException(message="Enrollment not found")

    # Check access
    if enrollment.child.user_id != current_user.id and current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    # Calculate progress for attendance-based badges
    streak = await Attendance.get_streak(db_session, enrollment_id)

    progress_items = [
        {"criteria": "perfect_attendance_5", "current": min(streak, 5), "required": 5},
        {"criteria": "perfect_attendance_10", "current": min(streak, 10), "required": 10},
        {"criteria": "perfect_attendance_20", "current": min(streak, 20), "required": 20},
    ]

    return BadgeProgressResponse(enrollment_id=enrollment_id, progress=progress_items)
```

#### Schemas (`app/schemas/badge.py`)

```python
class BadgeResponse(BaseSchema):
    id: str
    name: str
    description: str
    category: BadgeCategory
    criteria: BadgeCriteria
    icon_url: Optional[str]

class BadgeListResponse(BaseSchema):
    items: List[BadgeResponse]

class StudentBadgeResponse(BaseSchema):
    id: str
    enrollment_id: str
    badge_id: str
    awarded_at: datetime
    awarded_by: Optional[str]
    progress: Optional[int]
    progress_max: Optional[int]

class StudentBadgeStatusResponse(BaseSchema):
    badge: BadgeResponse
    is_unlocked: bool
    awarded_at: Optional[datetime]
    progress: Optional[int]
    progress_max: Optional[int]

class StudentBadgeListResponse(BaseSchema):
    enrollment_id: str
    badges: List[StudentBadgeStatusResponse]

class BadgeAward(BaseSchema):
    enrollment_id: str
    badge_id: str

class BadgeProgressResponse(BaseSchema):
    enrollment_id: str
    progress: List[dict]
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add badges system"
# Tables: badges, student_badges
```

#### Seed Data (Create in migration or via script)
```python
# Create 15+ default badges
badges = [
    Badge(name="First Class", description="Attended your first class", category=BadgeCategory.MILESTONE, criteria=BadgeCriteria.FIRST_CLASS),
    Badge(name="Perfect Attendance (5 weeks)", description="5 weeks of perfect attendance", category=BadgeCategory.ATTENDANCE, criteria=BadgeCriteria.PERFECT_ATTENDANCE_5),
    # ... all 15+ badges
]
```

#### Tests
- Test list all badges
- Test get student badges (locked/unlocked states)
- Test manual badge award (coach only)
- Test auto-award on attendance (streak triggers)
- Test badge progress calculation
- Test duplicate prevention

---

### Feature 4: Photo Gallery (~6 hours)

#### Requirements (from Figma)
- **Gallery view**: Grid of photos
- **Categories**: Everyone, Morning Session, Afternoon Session, Evening Session, Weekend Warriors
- **Upload modal**: Drag & drop or browse, category selection
- **Coach-only uploads**: Only coaches can upload
- **Class-based**: Photos belong to specific classes

#### Database Models

**1. PhotoCategory Model** (`app/models/photo.py`):
```python
class PhotoCategory(Base, TimestampMixin):
    __tablename__ = "photo_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="photo_categories")
    photos: Mapped[List["Photo"]] = relationship("Photo", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('class_id', 'name', name='unique_class_category'),
    )

class Photo(Base, TimestampMixin):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), nullable=False, index=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("photo_categories.id"), index=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Relative path
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500))  # Compressed thumbnail
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="photos")
    category: Mapped[Optional["PhotoCategory"]] = relationship("PhotoCategory", back_populates="photos")
    uploader: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_class(cls, db_session: AsyncSession, class_id: str, category_id: Optional[str] = None, skip: int = 0, limit: int = 50):
        """Get photos for a class, optionally filtered by category."""
        stmt = (
            select(cls)
            .where(cls.class_id == class_id, cls.is_active == True)
            .options(selectinload(cls.category))
        )

        if category_id:
            stmt = stmt.where(cls.category_id == category_id)

        stmt = stmt.order_by(cls.created_at.desc()).offset(skip).limit(limit)

        result = await db_session.execute(stmt)
        return result.scalars().all()
```

**2. Update Class Model**:
```python
# Add to Class model
class Class(Base, TimestampMixin):
    # ... existing fields ...

    # Add relationships
    photo_categories: Mapped[List["PhotoCategory"]] = relationship("PhotoCategory", back_populates="class_", cascade="all, delete-orphan")
    photos: Mapped[List["Photo"]] = relationship("Photo", back_populates="class_", cascade="all, delete-orphan")
```

#### API Endpoints (`app/api/v1/photos.py`)

```python
# 1. POST /api/v1/photos/upload - Upload photo
@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    class_id: str = Form(...),
    category_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    """Upload photo to class gallery. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can upload photos")

    # Validate class exists
    class_obj = await Class.get_by_id(db_session, class_id)
    if not class_obj:
        raise NotFoundException(message="Class not found")

    # Validate category if provided
    if category_id:
        category = await PhotoCategory.get_by_id(db_session, category_id)
        if not category or category.class_id != class_id:
            raise ValidationException(message="Invalid category")

    # Validate file
    if file.size > 10 * 1024 * 1024:  # 10MB
        raise ValidationException(message="File too large (max 10MB)")

    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise ValidationException(message="Invalid file type (only JPEG/PNG)")

    # Save original and thumbnail
    file_path, thumbnail_path, width, height = await file_service.save_photo(file, class_id)

    # Create record
    photo = Photo(
        class_id=class_id,
        category_id=category_id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file.size,
        thumbnail_path=thumbnail_path,
        width=width,
        height=height
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    return PhotoResponse.model_validate(photo)

# 2. GET /api/v1/photos/class/{class_id} - List photos
@router.get("/class/{class_id}", response_model=PhotoListResponse)
async def list_photos(
    class_id: str,
    category_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List photos for a class."""
    photos = await Photo.get_by_class(db_session, class_id, category_id, skip, limit)
    total = await Photo.count_by_class(db_session, class_id, category_id)

    return PhotoListResponse(
        items=[PhotoResponse.model_validate(p) for p in photos],
        total=total,
        skip=skip,
        limit=limit
    )

# 3. DELETE /api/v1/photos/{id} - Delete photo
@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    """Delete photo. Uploader or admin only."""
    photo = await Photo.get_by_id(db_session, photo_id)
    if not photo:
        raise NotFoundException(message="Photo not found")

    # Check permissions
    if photo.uploaded_by != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    # Delete files
    await file_service.delete_photo(photo.file_path, photo.thumbnail_path)

    # Soft delete
    photo.is_active = False
    await db_session.commit()

# 4. POST /api/v1/photos/categories - Create category
@router.post("/categories", response_model=PhotoCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_photo_category(
    data: PhotoCategoryCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create photo category. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create categories")

    category = PhotoCategory(**data.model_dump())
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)

    return PhotoCategoryResponse.model_validate(category)

# 5. GET /api/v1/photos/categories/class/{class_id} - List categories
@router.get("/categories/class/{class_id}", response_model=PhotoCategoryListResponse)
async def list_photo_categories(
    class_id: str,
    db_session: AsyncSession = Depends(get_db),
):
    """List photo categories for a class."""
    categories = await PhotoCategory.get_by_class(db_session, class_id)
    return PhotoCategoryListResponse(items=[PhotoCategoryResponse.model_validate(c) for c in categories])
```

#### Schemas (`app/schemas/photo.py`)

```python
class PhotoResponse(BaseSchema):
    id: str
    class_id: str
    category_id: Optional[str]
    uploaded_by: str
    file_name: str
    file_path: str
    thumbnail_path: Optional[str]
    file_size: int
    width: Optional[int]
    height: Optional[int]
    created_at: datetime

class PhotoListResponse(BaseSchema):
    items: List[PhotoResponse]
    total: int
    skip: int
    limit: int

class PhotoCategoryCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    class_id: str

class PhotoCategoryResponse(BaseSchema):
    id: str
    name: str
    class_id: str
    created_at: datetime

class PhotoCategoryListResponse(BaseSchema):
    items: List[PhotoCategoryResponse]
```

#### File Service (`app/services/file_service.py`)

```python
from PIL import Image
import os
from pathlib import Path

class FileService:
    def __init__(self, upload_dir: str = "/uploads"):
        self.upload_dir = Path(upload_dir)
        self.photos_dir = self.upload_dir / "photos"
        self.thumbnails_dir = self.upload_dir / "thumbnails"

        # Create directories
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    async def save_photo(self, file: UploadFile, class_id: str) -> tuple[str, str, int, int]:
        """Save photo and create thumbnail. Returns (file_path, thumbnail_path, width, height)."""
        # Generate unique filename
        ext = Path(file.filename).suffix
        unique_name = f"{uuid4()}{ext}"

        # Save original
        file_path = self.photos_dir / class_id / unique_name
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create thumbnail
        with Image.open(file_path) as img:
            width, height = img.size

            # Create thumbnail (max 300x300)
            img.thumbnail((300, 300))
            thumbnail_path = self.thumbnails_dir / class_id / unique_name
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumbnail_path, optimize=True, quality=85)

        return (
            str(file_path.relative_to(self.upload_dir)),
            str(thumbnail_path.relative_to(self.upload_dir)),
            width,
            height
        )

    async def delete_photo(self, file_path: str, thumbnail_path: Optional[str]):
        """Delete photo and thumbnail files."""
        full_path = self.upload_dir / file_path
        if full_path.exists():
            full_path.unlink()

        if thumbnail_path:
            full_thumb_path = self.upload_dir / thumbnail_path
            if full_thumb_path.exists():
                full_thumb_path.unlink()
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add photo gallery"
# Tables: photos, photo_categories
```

#### Tests
- Test upload photo (coach only)
- Test image compression and thumbnail generation
- Test list photos by class
- Test list photos by category
- Test delete photo (permissions)
- Test file size validation

---

### Feature 5: Events/Calendar System (~8 hours)

#### Requirements (from Figma)
- **Calendar view**: Monthly calendar with events
- **Event types**: Tournament, Match Day, Training, Workshop (with different colors)
- **Event details**: Title, Date, Time, Location, Description
- **Coach management**: Create, edit, delete events
- **Class-based**: Events belong to specific classes

#### Database Models

**Event Model** (`app/models/event.py`):
```python
class EventType(str, enum.Enum):
    TOURNAMENT = "tournament"
    MATCH = "match"
    TRAINING = "training"
    WORKSHOP = "workshop"
    OTHER = "other"

class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(10))  # "14:00"
    end_time: Mapped[Optional[str]] = mapped_column(String(10))  # "16:00"
    location: Mapped[Optional[str]] = mapped_column(String(255))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="events")
    creator: Mapped["User"] = relationship("User")

    @classmethod
    async def get_by_class_and_date_range(
        cls,
        db_session: AsyncSession,
        class_id: str,
        start_date: date,
        end_date: date
    ):
        """Get events for a class within a date range."""
        stmt = (
            select(cls)
            .where(
                cls.class_id == class_id,
                cls.is_active == True,
                cls.event_date >= start_date,
                cls.event_date <= end_date
            )
            .order_by(cls.event_date, cls.start_time)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_calendar_view(
        cls,
        db_session: AsyncSession,
        class_id: str,
        year: int,
        month: int
    ):
        """Get events for calendar view (month)."""
        import calendar
        _, num_days = calendar.monthrange(year, month)

        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        return await cls.get_by_class_and_date_range(db_session, class_id, start_date, end_date)
```

#### API Endpoints (`app/api/v1/events.py`)

```python
# 1. POST /api/v1/events - Create event
@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create event. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create events")

    # Validate class exists
    class_obj = await Class.get_by_id(db_session, data.class_id)
    if not class_obj:
        raise NotFoundException(message="Class not found")

    event = Event(**data.model_dump(), created_by=current_user.id)
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    return EventResponse.model_validate(event)

# 2. GET /api/v1/events/class/{class_id} - List events
@router.get("/class/{class_id}", response_model=EventListResponse)
async def list_events(
    class_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List events for a class, optionally filtered by date range."""
    if start_date and end_date:
        events = await Event.get_by_class_and_date_range(db_session, class_id, start_date, end_date)
    else:
        events = await Event.get_by_class(db_session, class_id)

    return EventListResponse(items=[EventResponse.model_validate(e) for e in events])

# 3. GET /api/v1/events/calendar - Calendar view
@router.get("/calendar", response_model=CalendarViewResponse)
async def get_calendar_view(
    class_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get calendar view for a specific month."""
    events = await Event.get_calendar_view(db_session, class_id, year, month)

    # Group by date
    calendar_data = {}
    for event in events:
        date_str = event.event_date.isoformat()
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        calendar_data[date_str].append(EventResponse.model_validate(event))

    return CalendarViewResponse(year=year, month=month, events=calendar_data)

# 4. GET /api/v1/events/{id} - Get event details
@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get event details."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")
    return EventResponse.model_validate(event)

# 5. PUT /api/v1/events/{id} - Update event
@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update event. Creator or admin only."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")

    # Check permissions
    if event.created_by != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    await event.update(db_session, **data.model_dump(exclude_unset=True))
    return EventResponse.model_validate(event)

# 6. DELETE /api/v1/events/{id} - Delete event
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete event. Creator or admin only."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")

    # Check permissions
    if event.created_by != current_user.id and current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Not authorized")

    event.is_active = False
    await db_session.commit()
```

#### Schemas (`app/schemas/event.py`)

```python
class EventCreate(BaseSchema):
    class_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: EventType
    event_date: date
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # HH:MM
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = None

class EventUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    event_date: Optional[date] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = None

class EventResponse(BaseSchema):
    id: str
    class_id: str
    title: str
    description: Optional[str]
    event_type: EventType
    event_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    location: Optional[str]
    created_by: str
    created_at: datetime

class EventListResponse(BaseSchema):
    items: List[EventResponse]

class CalendarViewResponse(BaseSchema):
    year: int
    month: int
    events: dict  # date -> List[EventResponse]
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add events system"
# Table: events
```

#### Tests
- Test create event (coach only)
- Test list events by class
- Test list events by date range
- Test calendar view (month)
- Test update event (permissions)
- Test delete event (soft delete)

---

### Feature 6: Check-In System (~5 hours)

#### Requirements (from Figma)
- **Check-in list**: Students with checkboxes
- **Coach view**: "3/5 checked in" status
- **Student details**: Name, Grade, Medical info visible
- **Real-time**: Check-in affects attendance
- **Class instance based**: Check-ins are per session

#### Database Models

**CheckIn Model** (`app/models/checkin.py`):
```python
class CheckIn(Base, TimestampMixin):
    __tablename__ = "checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    enrollment_id: Mapped[str] = mapped_column(String(36), ForeignKey("enrollments.id"), nullable=False, index=True)
    class_instance_id: Mapped[str] = mapped_column(String(36), ForeignKey("class_instances.id"), nullable=False, index=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    checked_in_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)  # Coach

    # Relationships
    enrollment: Mapped["Enrollment"] = relationship("Enrollment")
    class_instance: Mapped["ClassInstance"] = relationship("ClassInstance")
    checker: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint('enrollment_id', 'class_instance_id', name='unique_enrollment_checkin'),
    )

    @classmethod
    async def check_in_bulk(cls, db_session: AsyncSession, class_instance_id: str, enrollment_ids: List[str], checked_in_by: str):
        """Bulk check-in students."""
        check_in_time = datetime.now(timezone.utc)

        for enrollment_id in enrollment_ids:
            # Check if already checked in
            stmt = select(cls).where(
                cls.enrollment_id == enrollment_id,
                cls.class_instance_id == class_instance_id
            )
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                checkin = cls(
                    enrollment_id=enrollment_id,
                    class_instance_id=class_instance_id,
                    checked_in_at=check_in_time,
                    checked_in_by=checked_in_by
                )
                db_session.add(checkin)

        await db_session.commit()

    @classmethod
    async def get_by_class_instance(cls, db_session: AsyncSession, class_instance_id: str):
        """Get all check-ins for a class session."""
        stmt = (
            select(cls)
            .where(cls.class_instance_id == class_instance_id)
            .options(
                selectinload(cls.enrollment).selectinload(Enrollment.child)
            )
            .order_by(cls.checked_in_at)
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_checkin_status(cls, db_session: AsyncSession, class_instance_id: str):
        """Get check-in status (count checked in vs total)."""
        # Get all enrollments for this class
        class_instance = await ClassInstance.get_by_id(db_session, class_instance_id)
        total_enrollments = await Enrollment.count_by_class(db_session, class_instance.class_id)

        # Get checked-in count
        stmt = select(func.count(cls.id)).where(cls.class_instance_id == class_instance_id)
        result = await db_session.execute(stmt)
        checked_in = result.scalar()

        return {"checked_in": checked_in, "total": total_enrollments}
```

#### API Endpoints (`app/api/v1/checkin.py`)

```python
# 1. POST /api/v1/checkin - Check in students
@router.post("/", status_code=status.HTTP_201_CREATED)
async def check_in_students(
    data: CheckInBulk,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check in students for a class session. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can check in students")

    # Validate class instance exists
    class_instance = await ClassInstance.get_by_id(db_session, data.class_instance_id)
    if not class_instance:
        raise NotFoundException(message="Class session not found")

    await CheckIn.check_in_bulk(
        db_session,
        class_instance_id=data.class_instance_id,
        enrollment_ids=data.enrollment_ids,
        checked_in_by=current_user.id
    )

    return {"message": f"Checked in {len(data.enrollment_ids)} students"}

# 2. GET /api/v1/checkin/class-instance/{id} - Get check-ins
@router.get("/class-instance/{class_instance_id}", response_model=CheckInListResponse)
async def get_class_instance_checkins(
    class_instance_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get check-in list for a class session."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view check-ins")

    checkins = await CheckIn.get_by_class_instance(db_session, class_instance_id)
    return CheckInListResponse(
        class_instance_id=class_instance_id,
        checkins=[CheckInResponse.model_validate(c) for c in checkins]
    )

# 3. GET /api/v1/checkin/class-instance/{id}/status - Get status
@router.get("/class-instance/{class_instance_id}/status", response_model=CheckInStatusResponse)
async def get_checkin_status(
    class_instance_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get check-in status (X/Y checked in)."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can view check-in status")

    status = await CheckIn.get_checkin_status(db_session, class_instance_id)
    return CheckInStatusResponse(
        class_instance_id=class_instance_id,
        checked_in=status["checked_in"],
        total=status["total"]
    )
```

#### Schemas (`app/schemas/checkin.py`)

```python
class CheckInBulk(BaseSchema):
    class_instance_id: str
    enrollment_ids: List[str] = Field(..., min_items=1)

class CheckInResponse(BaseSchema):
    id: str
    enrollment_id: str
    class_instance_id: str
    checked_in_at: datetime
    checked_in_by: str

class CheckInListResponse(BaseSchema):
    class_instance_id: str
    checkins: List[CheckInResponse]

class CheckInStatusResponse(BaseSchema):
    class_instance_id: str
    checked_in: int
    total: int
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add check-in system"
# Table: checkins
```

#### Tests
- Test check in students (bulk)
- Test get check-ins by class session
- Test get check-in status (count)
- Test coach-only access
- Test duplicate prevention

---

### Feature 7: Child Model Updates (~2 hours)

#### Requirements (from Figma - Details.png)
Missing fields in Child model:
- `grade` - "Grade 4", "Grade 5", etc.
- `after_school` - Boolean flag
- `additional_notes` - Text field for coach notes

#### Model Changes

**Update Child Model** (`app/models/child.py`):
```python
class Child(Base, TimestampMixin):
    # ... existing fields ...

    # NEW FIELDS
    grade: Mapped[Optional[str]] = mapped_column(String(50))  # "Grade 4", "Grade 5", etc.
    after_school: Mapped[bool] = mapped_column(Boolean, default=False)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text)  # Coach notes
```

#### Schema Changes

**Update Child Schemas** (`app/schemas/child.py`):
```python
class ChildCreate(BaseSchema):
    # ... existing fields ...
    grade: Optional[str] = Field(None, max_length=50)
    after_school: bool = False
    additional_notes: Optional[str] = None

class ChildUpdate(BaseSchema):
    # ... existing fields ...
    grade: Optional[str] = Field(None, max_length=50)
    after_school: Optional[bool] = None
    additional_notes: Optional[str] = None

class ChildResponse(BaseSchema):
    # ... existing fields ...
    grade: Optional[str]
    after_school: bool
    additional_notes: Optional[str]
```

#### Migration
```bash
uv run alembic revision --autogenerate -m "Add grade, after_school, additional_notes to child"
```

---

### Feature 8: File Upload Infrastructure (~4-6 hours)

#### Setup

**1. Add Dependencies** (`pyproject.toml`):
```toml
dependencies = [
    # ... existing ...
    "pillow>=11.1.0",  # Image processing
    "python-magic>=0.4.27",  # File type detection
]
```

**2. Update Config** (`app/core/config.py`):
```python
class Settings(BaseSettings):
    # ... existing ...

    # File Upload
    UPLOAD_DIR: str = "/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/jpg"]
    ALLOWED_DOCUMENT_TYPES: List[str] = ["application/pdf"]
```

**3. File Service** (`app/services/file_service.py`):
```python
from pathlib import Path
from uuid import uuid4
from PIL import Image
import magic
from fastapi import UploadFile
from app.core.config import settings

class FileService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.photos_dir = self.upload_dir / "photos"
        self.announcements_dir = self.upload_dir / "announcements"
        self.thumbnails_dir = self.upload_dir / "thumbnails"

        # Create directories
        for dir_path in [self.photos_dir, self.announcements_dir, self.thumbnails_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def validate_file(self, file: UploadFile, allowed_types: List[str]):
        """Validate file type and size."""
        # Check size
        if file.size > settings.MAX_FILE_SIZE:
            raise ValidationException(message=f"File too large (max {settings.MAX_FILE_SIZE / 1024 / 1024}MB)")

        # Check MIME type
        if file.content_type not in allowed_types:
            raise ValidationException(message=f"Invalid file type. Allowed: {', '.join(allowed_types)}")

    async def save_photo(self, file: UploadFile, class_id: str) -> tuple[str, str, int, int]:
        """Save photo and create thumbnail."""
        self.validate_file(file, settings.ALLOWED_IMAGE_TYPES)

        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        unique_name = f"{uuid4()}{ext}"

        # Class-specific subdirectory
        class_dir = self.photos_dir / class_id
        class_dir.mkdir(parents=True, exist_ok=True)

        # Save original
        file_path = class_dir / unique_name
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create thumbnail
        with Image.open(file_path) as img:
            width, height = img.size

            # Create thumbnail (300x300 max)
            img.thumbnail((300, 300))
            thumbnail_dir = self.thumbnails_dir / class_id
            thumbnail_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = thumbnail_dir / unique_name
            img.save(thumbnail_path, optimize=True, quality=85)

        # Return relative paths
        return (
            str(file_path.relative_to(self.upload_dir)),
            str(thumbnail_path.relative_to(self.upload_dir)),
            width,
            height
        )

    async def save_announcement_attachment(self, file: UploadFile) -> str:
        """Save announcement attachment (PDF or image)."""
        allowed = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOCUMENT_TYPES
        self.validate_file(file, allowed)

        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        unique_name = f"{uuid4()}{ext}"

        # Save file
        file_path = self.announcements_dir / unique_name
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return str(file_path.relative_to(self.upload_dir))

    async def delete_file(self, relative_path: str):
        """Delete a file."""
        full_path = self.upload_dir / relative_path
        if full_path.exists():
            full_path.unlink()

    async def delete_photo(self, file_path: str, thumbnail_path: Optional[str]):
        """Delete photo and thumbnail."""
        await self.delete_file(file_path)
        if thumbnail_path:
            await self.delete_file(thumbnail_path)

# Dependency
def get_file_service() -> FileService:
    return FileService()
```

**4. Static File Serving** (`app/main.py`):
```python
from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
```

---

## Implementation Order

### Phase 1: Foundation (Hours 1-5)
1. **File Upload Infrastructure** (2h)
   - Add dependencies (Pillow, python-magic)
   - Create FileService
   - Update config
   - Static file serving

2. **Child Model Updates** (1h)
   - Add fields (grade, after_school, additional_notes)
   - Update schemas
   - Create migration

3. **Database Migrations** (2h)
   - Create all 6 feature migrations
   - Seed badge data
   - Test migrations (up/down)

### Phase 2: Core Features (Hours 6-30)
4. **Announcements System** (8h)
   - Models (Announcement, AnnouncementAttachment, AnnouncementTarget)
   - API endpoints (6 endpoints)
   - File upload for attachments
   - Tests

5. **Attendance Tracking** (6h)
   - Model (Attendance)
   - API endpoints (4 endpoints)
   - Streak calculation logic
   - Tests

6. **Events/Calendar** (8h)
   - Model (Event)
   - API endpoints (6 endpoints)
   - Calendar view logic
   - Tests

7. **Photo Gallery** (8h)
   - Models (Photo, PhotoCategory)
   - API endpoints (5 endpoints)
   - Image compression and thumbnails
   - Tests

### Phase 3: Advanced Features (Hours 31-45)
8. **Badges System** (10h)
   - Models (Badge, StudentBadge)
   - API endpoints (4 endpoints)
   - Auto-award logic
   - Seed data
   - Tests

9. **Check-In System** (5h)
   - Model (CheckIn)
   - API endpoints (3 endpoints)
   - Status tracking
   - Tests

### Phase 4: Integration & Testing (Hours 46-50)
10. **Integration Testing** (3h)
    - Cross-feature tests (attendance → badges)
    - Full workflow tests
    - Performance testing

11. **Documentation** (2h)
    - Update API documentation
    - Update CLAUDE.md
    - Create frontend integration guide

---

## Testing Strategy

### Unit Tests
- All model class methods
- Business logic (streak calculation, badge criteria)
- File validation and processing

### Integration Tests
- All API endpoints (CRUD)
- Authentication/authorization
- File uploads
- Multi-class operations

### Test Coverage Target
- **75%+ overall coverage**
- **90%+ for business logic**
- **100% for critical paths** (payments, enrollment)

### Key Test Scenarios
1. **Announcements**: Create → Upload attachment → List by class → Delete
2. **Attendance**: Mark bulk → Get history → Calculate streak → Award badge
3. **Badges**: Auto-award on attendance → Manual award → Progress tracking
4. **Photos**: Upload → Thumbnail generation → List by category → Delete
5. **Events**: Create → Calendar view → Update → Delete
6. **Check-in**: Bulk check-in → Get status → Link to attendance

---

## Risks & Mitigations

### Risk 1: File Storage Scalability
**Risk**: Local filesystem may not scale
**Mitigation**: Design with abstraction layer, easy to swap to S3 later
**Priority**: Low (MVP focused)

### Risk 2: Badge Auto-Award Performance
**Risk**: Checking criteria on every attendance mark could be slow
**Mitigation**: Use Celery background tasks for badge checks
**Priority**: Medium

### Risk 3: Large Photo Uploads
**Risk**: Multiple large photo uploads could overwhelm server
**Mitigation**: 10MB limit, image compression, thumbnail generation
**Priority**: Medium

### Risk 4: Attendance Streak Edge Cases
**Risk**: Streak calculation could be incorrect with gaps/excused absences
**Mitigation**: Comprehensive unit tests for streak logic
**Priority**: High

---

## Success Criteria

### Feature Completeness
- [ ] All 6 features implemented
- [ ] All API endpoints functional
- [ ] File upload working (photos, PDFs)
- [ ] Auto-badge awarding working
- [ ] All migrations applied successfully

### Code Quality
- [ ] Follows existing patterns (Base, TimestampMixin, etc.)
- [ ] All models have class methods
- [ ] All endpoints have proper auth
- [ ] Consistent error handling

### Testing
- [ ] 75%+ test coverage
- [ ] All critical paths tested
- [ ] Integration tests passing
- [ ] No regressions in existing tests

### Documentation
- [ ] API endpoints documented
- [ ] CLAUDE.md updated
- [ ] Frontend integration guide created

---

## Post-Implementation Tasks

1. **Defer to Later**:
   - SMS/Text Messaging (requires Twilio setup)
   - Advanced reporting/analytics
   - Push notifications

2. **Frontend Work** (separate):
   - Implement all UI screens from Figma
   - File upload components
   - Calendar component
   - Badge display with locked/unlocked states
   - Photo gallery grid
   - Announcement feed

3. **Future Enhancements**:
   - S3 file storage migration
   - Image moderation
   - Batch photo uploads
   - Export attendance reports
   - Badge sharing on social media

---

## Estimated Timeline

| Phase | Hours | Description |
|-------|-------|-------------|
| Foundation | 5 | File service, Child updates, Migrations |
| Announcements | 8 | Full system with attachments |
| Attendance | 6 | Tracking and streak calculation |
| Events/Calendar | 8 | Full calendar system |
| Photo Gallery | 8 | Upload, thumbnails, categories |
| Badges | 10 | Auto-award system, seed data |
| Check-In | 5 | Bulk check-in, status |
| Integration & Testing | 5 | Cross-feature tests, docs |
| **Total** | **55** | **Production-ready with tests** |

**Note**: This is ~10 hours over the 45-hour target. Can optimize by:
- Parallelizing badge seed data creation
- Reducing announcement endpoint count (defer delete)
- Simplifying photo categories (hardcode common ones)
- Focusing tests on critical paths only

---

## Questions for User (If Any)

1. **Badge Icons**: Do you have icon files for the 15+ badges, or should we use placeholder icons initially?

2. **SMS Feature**: Confirm deferring SMS/text messaging to later milestone?

3. **Photo Privacy**: Should photos be visible only to enrolled students, or public to entire class?

4. **Attendance Auto-Mark**: Should check-in automatically mark attendance, or are they separate actions?

---

## Next Steps

1. **User Reviews Plan** → Approves or requests changes
2. **Confirm Timeline** → Adjust scope if needed to hit 45 hours
3. **Start Implementation** → Begin with Phase 1 (Foundation)
4. **Regular Updates** → Update this plan with progress

---

**Plan Status**: ✅ Complete - Ready for Review
**Last Updated**: 2025-11-25
