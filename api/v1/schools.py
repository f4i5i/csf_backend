"""School API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from app.models.program import School
from app.models.user import User
from app.schemas.school import SchoolCreate, SchoolResponse, SchoolUpdate
from core.db import get_db
from core.exceptions.base import NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get("/", response_model=list[SchoolResponse])
async def list_schools(
    is_active: bool = Query(None),
    area_id: str = Query(None),
    db_session: AsyncSession = Depends(get_db),
) -> list[SchoolResponse]:
    """
    List all schools.

    Public endpoint - no authentication required.
    Optionally filter by active status or area_id.
    """
    query = select(School)

    if is_active is not None:
        query = query.where(School.is_active == is_active)

    if area_id:
        query = query.where(School.area_id == area_id)

    query = query.order_by(School.name)

    result = await db_session.execute(query)
    schools = result.scalars().all()

    return [
        SchoolResponse(
            id=s.id,
            name=s.name,
            code=s.code,
            address=s.address,
            city=s.city,
            state=s.state,
            zip_code=s.zip_code,
            area_id=s.area_id,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in schools
    ]


@router.get("/{school_id}", response_model=SchoolResponse)
async def get_school(
    school_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> SchoolResponse:
    """Get school by ID."""
    school = await School.get_by_id(db_session, school_id)

    if not school:
        raise NotFoundException(f"School {school_id} not found")

    return SchoolResponse(
        id=school.id,
        name=school.name,
        code=school.code,
        address=school.address,
        city=school.city,
        state=school.state,
        zip_code=school.zip_code,
        area_id=school.area_id,
        is_active=school.is_active,
        created_at=school.created_at,
        updated_at=school.updated_at,
    )


@router.post("/", response_model=SchoolResponse)
async def create_school(
    data: SchoolCreate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> SchoolResponse:
    """Create a new school (Admin only)."""
    logger.info(f"Creating school: {data.name} (admin: {current_admin.id})")

    school = await School.create_school(
        db_session,
        name=data.name,
        code=data.code,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        area_id=data.area_id,
    )

    if data.is_active is not None:
        school.is_active = data.is_active
        await db_session.commit()
        await db_session.refresh(school)

    return SchoolResponse(
        id=school.id,
        name=school.name,
        code=school.code,
        address=school.address,
        city=school.city,
        state=school.state,
        zip_code=school.zip_code,
        area_id=school.area_id,
        is_active=school.is_active,
        created_at=school.created_at,
        updated_at=school.updated_at,
    )


@router.put("/{school_id}", response_model=SchoolResponse)
async def update_school(
    school_id: str,
    data: SchoolUpdate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> SchoolResponse:
    """Update a school (Admin only)."""
    logger.info(f"Updating school {school_id} (admin: {current_admin.id})")

    school = await School.get_by_id(db_session, school_id)
    if not school:
        raise NotFoundException(f"School {school_id} not found")

    if data.name is not None:
        school.name = data.name
    if data.code is not None:
        school.code = data.code
    if data.address is not None:
        school.address = data.address
    if data.city is not None:
        school.city = data.city
    if data.state is not None:
        school.state = data.state
    if data.zip_code is not None:
        school.zip_code = data.zip_code
    if data.area_id is not None:
        school.area_id = data.area_id
    if data.is_active is not None:
        school.is_active = data.is_active

    await db_session.commit()
    await db_session.refresh(school)

    return SchoolResponse(
        id=school.id,
        name=school.name,
        code=school.code,
        address=school.address,
        city=school.city,
        state=school.state,
        zip_code=school.zip_code,
        area_id=school.area_id,
        is_active=school.is_active,
        created_at=school.created_at,
        updated_at=school.updated_at,
    )


@router.delete("/{school_id}")
async def delete_school(
    school_id: str,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a school (Admin only)."""
    logger.info(f"Deleting school {school_id} (admin: {current_admin.id})")

    school = await School.get_by_id(db_session, school_id)
    if not school:
        raise NotFoundException(f"School {school_id} not found")

    await db_session.delete(school)
    await db_session.commit()

    return {"status": "success", "message": f"School {school_id} deleted"}
