"""Program API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from app.models.program import Program
from app.models.user import User
from app.schemas.program import ProgramCreate, ProgramResponse, ProgramUpdate
from core.db import get_db
from core.exceptions.base import NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("/", response_model=list[ProgramResponse])
async def list_programs(
    is_active: bool = Query(None),
    db_session: AsyncSession = Depends(get_db),
) -> list[ProgramResponse]:
    """
    List all programs.

    Public endpoint - no authentication required.
    Optionally filter by active status.
    """
    query = select(Program)

    if is_active is not None:
        query = query.where(Program.is_active == is_active)

    query = query.order_by(Program.name)

    result = await db_session.execute(query)
    programs = result.scalars().all()

    return [
        ProgramResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in programs
    ]


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """Get program by ID."""
    program = await Program.get_by_id(db_session, program_id)

    if not program:
        raise NotFoundException(f"Program {program_id} not found")

    return ProgramResponse(
        id=program.id,
        name=program.name,
        description=program.description,
        is_active=program.is_active,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


@router.post("/", response_model=ProgramResponse)
async def create_program(
    data: ProgramCreate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """Create a new program (Admin only)."""
    logger.info(f"Creating program: {data.name} (admin: {current_admin.id})")

    program = await Program.create_program(
        db_session,
        name=data.name,
        description=data.description,
        is_active=data.is_active if data.is_active is not None else True,
    )

    return ProgramResponse(
        id=program.id,
        name=program.name,
        description=program.description,
        is_active=program.is_active,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


@router.put("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: str,
    data: ProgramUpdate,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    """Update a program (Admin only)."""
    logger.info(f"Updating program {program_id} (admin: {current_admin.id})")

    program = await Program.get_by_id(db_session, program_id)
    if not program:
        raise NotFoundException(f"Program {program_id} not found")

    if data.name is not None:
        program.name = data.name
    if data.description is not None:
        program.description = data.description
    if data.is_active is not None:
        program.is_active = data.is_active

    await db_session.commit()
    await db_session.refresh(program)

    return ProgramResponse(
        id=program.id,
        name=program.name,
        description=program.description,
        is_active=program.is_active,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


@router.delete("/{program_id}")
async def delete_program(
    program_id: str,
    current_admin: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a program (Admin only)."""
    logger.info(f"Deleting program {program_id} (admin: {current_admin.id})")

    program = await Program.get_by_id(db_session, program_id)
    if not program:
        raise NotFoundException(f"Program {program_id} not found")

    await db_session.delete(program)
    await db_session.commit()

    return {"status": "success", "message": f"Program {program_id} deleted"}
