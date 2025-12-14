"""Announcements API endpoints for coaches to create posts."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.announcement import (
    Announcement,
    AnnouncementAttachment,
    AttachmentType,
)
from app.models.user import Role, User
from app.schemas.announcement import (
    AnnouncementAttachmentResponse,
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.services.file_service import get_file_service, FileService
from core.db import get_db
from core.exceptions.base import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """
    Create announcement. Coaches/admins only.

    Coaches can create announcements that target one or more classes.
    Announcements can have attachments (PDFs, images) added separately.
    """
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create announcements")

    logger.info(
        f"Creating announcement '{data.title}' by user {current_user.id} "
        f"for {len(data.class_ids)} classes"
    )

    announcement = await Announcement.create_with_targets(
        db_session,
        class_ids=data.class_ids,
        title=data.title,
        description=data.description,
        type=data.type,
        author_id=current_user.id,
        organization_id=current_user.organization_id,
    )

    return AnnouncementResponse.model_validate(announcement)


@router.get("/", response_model=AnnouncementListResponse)
async def list_announcements(
    class_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementListResponse:
    """
    List announcements for a class or all announcements.

    If class_id is provided, returns announcements for that class.
    Otherwise returns all announcements (admin/coach only for all).
    """
    if class_id:
        announcements = await Announcement.get_by_class(db_session, class_id, skip, limit)
        total = await Announcement.count_by_class(db_session, class_id)
    else:
        # Only admins/coaches can see all announcements
        if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
            raise ForbiddenException(message="Only coaches can view all announcements")

        announcements = await Announcement.get_all(db_session, skip, limit)
        total = await Announcement.count_all(db_session)

    return AnnouncementListResponse(
        items=[AnnouncementResponse.model_validate(a) for a in announcements],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """Get announcement details."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    return AnnouncementResponse.model_validate(announcement)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """Update announcement. Author or admin only."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if (
        announcement.author_id != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized to update this announcement")

    logger.info(f"Updating announcement {announcement_id} by user {current_user.id}")

    updated = await announcement.update(db_session, **data.model_dump(exclude_unset=True))
    return AnnouncementResponse.model_validate(updated)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete announcement (soft delete). Author or admin only."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if (
        announcement.author_id != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized to delete this announcement")

    logger.info(f"Deleting announcement {announcement_id} by user {current_user.id}")

    announcement.is_active = False
    await db_session.commit()


@router.post(
    "/{announcement_id}/attachments",
    response_model=AnnouncementAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    announcement_id: str,
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> AnnouncementAttachmentResponse:
    """Upload attachment to announcement."""
    announcement = await Announcement.get_by_id(db_session, announcement_id)
    if not announcement:
        raise NotFoundException(message="Announcement not found")

    # Check permissions
    if (
        announcement.author_id != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized to add attachments")

    # Validate file
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise ValidationException(message="File too large (max 10MB)")

    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise ValidationException(message="Invalid file type (PDF or JPEG/PNG only)")

    logger.info(
        f"Uploading attachment '{file.filename}' to announcement {announcement_id}"
    )

    # Save file
    file_path = await file_service.save_announcement_attachment(file)

    # Determine type
    attachment_type = (
        AttachmentType.PDF
        if file.content_type == "application/pdf"
        else AttachmentType.IMAGE
    )

    # Create record
    attachment = AnnouncementAttachment(
        announcement_id=announcement_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file.size or 0,
        file_type=attachment_type,
        mime_type=file.content_type or "application/octet-stream",
        organization_id=current_user.organization_id,
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)

    return AnnouncementAttachmentResponse.model_validate(attachment)
