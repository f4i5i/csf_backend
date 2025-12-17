"""Area API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from app.models.program import Area
from app.models.user import User
from app.schemas.area import AreaCreate, AreaResponse, AreaUpdate
from core.db import get_db
from core.exceptions.base import NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/areas", tags=["Areas"])


@router.get("/", response_model=list[AreaResponse])
async def list_areas(
    is_active: bool = Query(None),
    db_session: AsyncSession = Depends(get_db),
) -> list[AreaResponse]:
    """
    List all geographic areas.

    Public endpoint - no authentication required.
    Optionally filter by active status.
    """
    query = select(Area)

    if is_active is not None:
        query = query.where(Area.is_active == is_active)

    query = query.order_by(Area.name)

    result = await db_session.execute(query)
    areas = result.scalars().all()

    return [
        AreaResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in areas
    ]


@router.get("/{area_id}", response_model=AreaResponse)
async def get_area(
    area_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Get area by ID."""
    area = await Area.get_by_id(db_session, area_id)

    if not area:
        raise NotFoundException(f"Area {area_id} not found")

    return AreaResponse(
        id=area.id,
        name=area.name,
        description=area.description,
        is_active=area.is_active,
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


@router.post("/", response_model=AreaResponse)
async def create_area(
    data: AreaCreate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Create a new area (Admin only)."""
    logger.info(f"Creating area: {data.name} (admin: {current_admin.id})")

    area = await Area.create_area(
        db_session,
        name=data.name,
        organization_id=current_admin.organization_id,
        description=data.description)

    return AreaResponse(
        id=area.id,
        name=area.name,
        description=area.description,
        is_active=area.is_active,
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


@router.put("/{area_id}", response_model=AreaResponse)
async def update_area(
    area_id: str,
    data: AreaUpdate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Update an area (Admin only)."""
    logger.info(f"Updating area {area_id} (admin: {current_admin.id})")

    area = await Area.get_by_id(db_session, area_id)
    if not area:
        raise NotFoundException(f"Area {area_id} not found")

    if data.name is not None:
        area.name = data.name
    if data.description is not None:
        area.description = data.description
    if data.is_active is not None:
        area.is_active = data.is_active

    await db_session.commit()
    await db_session.refresh(area)

    return AreaResponse(
        id=area.id,
        name=area.name,
        description=area.description,
        is_active=area.is_active,
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


@router.delete("/{area_id}")
async def delete_area(
    area_id: str,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an area (Admin only)."""
    logger.info(f"Deleting area {area_id} (admin: {current_admin.id})")

    area = await Area.get_by_id(db_session, area_id)
    if not area:
        raise NotFoundException(f"Area {area_id} not found")

    await db_session.delete(area)
    await db_session.commit()

    return {"status": "success", "message": f"Area {area_id} deleted"}
