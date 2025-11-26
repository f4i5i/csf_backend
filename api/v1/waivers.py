from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.user import User
from app.models.waiver import WaiverAcceptance, WaiverTemplate
from app.schemas.waiver import (
    WaiverAcceptanceCreate,
    WaiverAcceptanceListResponse,
    WaiverAcceptanceResponse,
    WaiverStatusListResponse,
    WaiverStatusResponse,
    WaiverTemplateCreate,
    WaiverTemplateListResponse,
    WaiverTemplateResponse,
    WaiverTemplateUpdate,
)
from core.db import get_db
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/waivers", tags=["Waivers"])


# ============== Admin Endpoints for Managing Templates ==============


@router.post("/templates", response_model=WaiverTemplateResponse)
async def create_waiver_template(
    data: WaiverTemplateCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverTemplateResponse:
    """
    Create a new waiver template (admin only).

    Creates a new version if a template with the same type already exists.
    """
    logger.info(f"Create waiver template request by admin: {current_user.id}")

    template = await WaiverTemplate.create_template(
        db_session,
        name=data.name,
        waiver_type=data.waiver_type,
        content=data.content,
        is_active=data.is_active,
        is_required=data.is_required,
        applies_to_program_id=data.applies_to_program_id,
        applies_to_school_id=data.applies_to_school_id,
    )

    logger.info(f"Waiver template created: {template.id}, version: {template.version}")
    return WaiverTemplateResponse.model_validate(template)


@router.get("/templates", response_model=WaiverTemplateListResponse)
async def list_waiver_templates(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverTemplateListResponse:
    """
    List all waiver templates (admin only).
    """
    logger.info(f"List waiver templates by admin: {current_user.id}")
    templates = await WaiverTemplate.get_all(db_session, include_inactive=include_inactive)
    return WaiverTemplateListResponse(
        items=[WaiverTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.get("/templates/{template_id}", response_model=WaiverTemplateResponse)
async def get_waiver_template(
    template_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverTemplateResponse:
    """
    Get a specific waiver template (admin only).
    """
    template = await WaiverTemplate.get_by_id(db_session, template_id)
    if not template:
        raise NotFoundException(message="Waiver template not found")
    return WaiverTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=WaiverTemplateResponse)
async def update_waiver_template(
    template_id: str,
    data: WaiverTemplateUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverTemplateResponse:
    """
    Update a waiver template (admin only).

    Note: Updating content will create a new version.
    """
    logger.info(f"Update waiver template: {template_id} by admin: {current_user.id}")

    template = await WaiverTemplate.get_by_id(db_session, template_id)
    if not template:
        raise NotFoundException(message="Waiver template not found")

    update_data = data.model_dump(exclude_unset=True)

    # If content is changing, increment version
    if "content" in update_data and update_data["content"] != template.content:
        template.version += 1
        logger.info(f"Waiver template version incremented to: {template.version}")

    for field, value in update_data.items():
        setattr(template, field, value)

    await db_session.commit()
    await db_session.refresh(template)
    logger.info(f"Waiver template updated: {template_id}")
    return WaiverTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_waiver_template(
    template_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft delete a waiver template (admin only).

    Sets is_active to False rather than deleting the record.
    """
    logger.info(f"Delete waiver template: {template_id} by admin: {current_user.id}")

    template = await WaiverTemplate.get_by_id(db_session, template_id)
    if not template:
        raise NotFoundException(message="Waiver template not found")

    template.is_active = False
    await db_session.commit()
    logger.info(f"Waiver template soft deleted: {template_id}")
    return {"message": "Waiver template deleted successfully"}


# ============== User Endpoints for Viewing and Accepting Waivers ==============


@router.get("/required", response_model=WaiverStatusListResponse)
async def get_required_waivers(
    program_id: Optional[str] = None,
    school_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverStatusListResponse:
    """
    Get all required waivers for the current user with acceptance status.

    Returns waivers applicable to the given program/school context.
    """
    logger.info(f"Get required waivers for user: {current_user.id}")

    templates = await WaiverTemplate.get_active_waivers(
        db_session, program_id=program_id, school_id=school_id
    )

    items = []
    pending_count = 0

    for template in templates:
        acceptance = await WaiverAcceptance.get_user_acceptance_for_waiver(
            db_session, current_user.id, template.id
        )
        needs_reconsent = await WaiverAcceptance.needs_reconsent(
            db_session, current_user.id, template
        )

        if needs_reconsent:
            pending_count += 1

        status = WaiverStatusResponse(
            waiver_template=WaiverTemplateResponse.model_validate(template),
            is_accepted=acceptance is not None,
            acceptance=(
                WaiverAcceptanceResponse.model_validate(acceptance) if acceptance else None
            ),
            needs_reconsent=needs_reconsent,
        )
        items.append(status)

    return WaiverStatusListResponse(
        items=items,
        pending_count=pending_count,
        total=len(items),
    )


@router.post("/accept", response_model=WaiverAcceptanceResponse)
async def accept_waiver(
    data: WaiverAcceptanceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverAcceptanceResponse:
    """
    Accept a waiver.

    Records the acceptance with signer information for legal compliance.
    """
    logger.info(
        f"Accept waiver: {data.waiver_template_id} by user: {current_user.id}"
    )

    template = await WaiverTemplate.get_by_id(db_session, data.waiver_template_id)
    if not template:
        raise NotFoundException(message="Waiver template not found")

    if not template.is_active:
        raise BadRequestException(message="This waiver is no longer active")

    # Check if already accepted at current version
    existing = await WaiverAcceptance.get_user_acceptance_for_waiver(
        db_session, current_user.id, template.id
    )
    if existing and existing.waiver_version >= template.version:
        raise BadRequestException(message="You have already accepted this waiver")

    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:500]

    acceptance = await WaiverAcceptance.create_acceptance(
        db_session,
        user_id=current_user.id,
        waiver_template_id=template.id,
        waiver_version=template.version,
        signer_name=data.signer_name,
        signer_ip=client_ip,
        signer_user_agent=user_agent,
    )

    logger.info(f"Waiver accepted: {acceptance.id}")
    return WaiverAcceptanceResponse.model_validate(acceptance)


@router.get("/my-acceptances", response_model=WaiverAcceptanceListResponse)
async def get_my_acceptances(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverAcceptanceListResponse:
    """
    Get all waiver acceptances for the current user.
    """
    logger.info(f"Get waiver acceptances for user: {current_user.id}")
    acceptances = await WaiverAcceptance.get_user_acceptances(db_session, current_user.id)
    return WaiverAcceptanceListResponse(
        items=[WaiverAcceptanceResponse.model_validate(a) for a in acceptances],
        total=len(acceptances),
    )


@router.get("/acceptances/{acceptance_id}", response_model=WaiverAcceptanceResponse)
async def get_acceptance(
    acceptance_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> WaiverAcceptanceResponse:
    """
    Get a specific waiver acceptance.

    Users can only view their own acceptances. Admins can view any.
    """
    acceptance = await WaiverAcceptance.get_by_id(db_session, acceptance_id)
    if not acceptance:
        raise NotFoundException(message="Waiver acceptance not found")

    # Check access
    if current_user.role.value not in ["owner", "admin"]:
        if acceptance.user_id != current_user.id:
            raise NotFoundException(message="Waiver acceptance not found")

    return WaiverAcceptanceResponse.model_validate(acceptance)
