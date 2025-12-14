"""Photos API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.photo import Photo, PhotoCategory
from app.models.user import Role, User
from app.schemas.photo import (
    PhotoCategoryCreate,
    PhotoCategoryListResponse,
    PhotoCategoryResponse,
    PhotoListResponse,
    PhotoResponse,
)
from app.services.file_service import FileService, get_file_service
from core.db import get_db
from core.exceptions.base import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/photos", tags=["Photos"])


@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    class_id: str = Form(...),
    category_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> PhotoResponse:
    """Upload photo to class gallery. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can upload photos")

    # Validate category if provided
    if category_id:
        category = await PhotoCategory.get_by_id(db_session, category_id)
        if not category or category.class_id != class_id:
            raise ValidationException(message="Invalid category")

    # Read file binary data
    file_data = await file.read()
    file_size = len(file_data)
    content_type = file.content_type or "image/jpeg"

    # Reset file pointer and save file (for backward compatibility)
    await file.seek(0)
    file_path, thumbnail_path, width, height, _ = await file_service.save_photo(
        file, class_id
    )

    # Read thumbnail binary if exists
    thumbnail_data = None
    if thumbnail_path:
        try:
            import aiofiles
            async with aiofiles.open(thumbnail_path, 'rb') as f:
                thumbnail_data = await f.read()
        except Exception as e:
            logger.warning(f"Could not read thumbnail data: {e}")

    # Create record with binary data
    photo = Photo(
        class_id=class_id,
        category_id=category_id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_data=file_data,
        content_type=content_type,
        thumbnail_path=thumbnail_path,
        thumbnail_data=thumbnail_data,
        width=width,
        height=height,
        organization_id=current_user.organization_id,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    return PhotoResponse.model_validate(photo)


@router.get("/", response_model=PhotoListResponse)
async def list_all_photos(
    class_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhotoListResponse:
    """List all photos with optional filters."""
    from sqlalchemy import select, and_, func
    from sqlalchemy.orm import selectinload

    conditions = [Photo.is_active == True]

    if class_id:
        conditions.append(Photo.class_id == class_id)
    if category_id:
        conditions.append(Photo.category_id == category_id)

    stmt = (
        select(Photo)
        .where(and_(*conditions))
        .options(selectinload(Photo.category))
        .order_by(Photo.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db_session.execute(stmt)
    photos = result.scalars().all()

    # Count total
    count_stmt = select(func.count(Photo.id)).where(and_(*conditions))
    count_result = await db_session.execute(count_stmt)
    total = count_result.scalar() or 0

    return PhotoListResponse(
        items=[PhotoResponse.model_validate(p) for p in photos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/class/{class_id}", response_model=PhotoListResponse)
async def list_photos(
    class_id: str,
    category_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhotoListResponse:
    """List photos for a class."""
    photos = await Photo.get_by_class(db_session, class_id, category_id, skip, limit)
    total = await Photo.count_by_class(db_session, class_id, category_id)

    return PhotoListResponse(
        items=[PhotoResponse.model_validate(p) for p in photos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> None:
    """Delete photo. Uploader or admin only."""
    photo = await Photo.get_by_id(db_session, photo_id)
    if not photo:
        raise NotFoundException(message="Photo not found")

    if (
        photo.uploaded_by != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    # Delete files
    await file_service.delete_photo(photo.file_path, photo.thumbnail_path)

    # Soft delete
    photo.is_active = False
    await db_session.commit()


@router.post(
    "/categories",
    response_model=PhotoCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_photo_category(
    data: PhotoCategoryCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhotoCategoryResponse:
    """Create photo category. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create categories")

    category = PhotoCategory(
        **data.model_dump(),
        organization_id=current_user.organization_id
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)

    return PhotoCategoryResponse.model_validate(category)


@router.get("/categories/class/{class_id}", response_model=PhotoCategoryListResponse)
async def list_photo_categories(
    class_id: str, db_session: AsyncSession = Depends(get_db)
) -> PhotoCategoryListResponse:
    """List photo categories for a class."""
    categories = await PhotoCategory.get_by_class(db_session, class_id)
    return PhotoCategoryListResponse(
        items=[PhotoCategoryResponse.model_validate(c) for c in categories]
    )


@router.get("/{photo_id}/image")
async def get_photo_image(
    photo_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> Response:
    """Get photo image binary data for display."""
    photo = await Photo.get_by_id(db_session, photo_id)
    if not photo:
        raise NotFoundException(message="Photo not found")

    if not photo.file_data:
        raise NotFoundException(message="Photo data not available")

    return Response(
        content=photo.file_data,
        media_type=photo.content_type or "image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="{photo.file_name}"',
            "Cache-Control": "public, max-age=31536000",
        },
    )


@router.get("/{photo_id}/thumbnail")
async def get_photo_thumbnail(
    photo_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> Response:
    """Get photo thumbnail binary data for display."""
    photo = await Photo.get_by_id(db_session, photo_id)
    if not photo:
        raise NotFoundException(message="Photo not found")

    if not photo.thumbnail_data:
        # Fallback to full image if no thumbnail
        if photo.file_data:
            return Response(
                content=photo.file_data,
                media_type=photo.content_type or "image/jpeg",
                headers={
                    "Content-Disposition": f'inline; filename="thumb_{photo.file_name}"',
                    "Cache-Control": "public, max-age=31536000",
                },
            )
        raise NotFoundException(message="Thumbnail not available")

    return Response(
        content=photo.thumbnail_data,
        media_type=photo.content_type or "image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="thumb_{photo.file_name}"',
            "Cache-Control": "public, max-age=31536000",
        },
    )
