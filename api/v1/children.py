from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.child import Child, EmergencyContact
from app.models.user import User
from app.schemas.child import (
    ChildCreate,
    ChildListResponse,
    ChildResponse,
    ChildUpdate,
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
)
from app.utils.encryption import decrypt_pii, encrypt_pii
from core.db import get_db
from core.exceptions.base import ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/children", tags=["Children"])


def child_to_response(child: Child) -> ChildResponse:
    """Convert Child model to response with decrypted PII."""
    return ChildResponse(
        id=child.id,
        user_id=child.user_id,
        first_name=child.first_name,
        last_name=child.last_name,
        full_name=child.full_name,
        date_of_birth=child.date_of_birth,
        age=child.age,
        jersey_size=child.jersey_size,
        grade=child.grade,
        medical_conditions=decrypt_pii(child.medical_conditions_encrypted),
        has_no_medical_conditions=child.has_no_medical_conditions,
        after_school_attendance=child.after_school_attendance,
        after_school_program=child.after_school_program,
        health_insurance_number=decrypt_pii(child.health_insurance_number_encrypted),
        how_heard_about_us=child.how_heard_about_us,
        how_heard_other_text=child.how_heard_other_text,
        is_active=child.is_active,
        created_at=child.created_at,
        updated_at=child.updated_at,
        emergency_contacts=[
            EmergencyContactResponse.model_validate(ec)
            for ec in child.emergency_contacts
        ],
    )


async def verify_child_access(
    child: Child, user: User, require_owner: bool = False
) -> None:
    """Verify user has access to this child."""
    # Admin/Owner can access any child
    if user.role.value in ["owner", "admin"]:
        return

    # Parent can only access their own children
    if child.user_id != user.id:
        raise ForbiddenException(message="You don't have access to this child")


@router.get("/my", response_model=ChildListResponse)
async def list_my_children(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> ChildListResponse:
    """
    List all children for the current user.

    Returns children associated with the authenticated user.
    """
    logger.info(f"List children request by user: {current_user.id}")
    children = await Child.get_by_user_id(db_session, current_user.id)
    logger.info(f"Found {len(children)} children for user: {current_user.id}")
    return ChildListResponse(
        items=[child_to_response(c) for c in children],
        total=len(children),
    )


@router.post("/", response_model=ChildResponse)
async def create_child(
    data: ChildCreate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """
    Add a new child to the current user's account.

    PII fields (medical_conditions, health_insurance_number) are encrypted at rest.
    """
    logger.info(
        f"Create child request by user: {current_user.id}, name: {data.first_name}"
    )

    # Create child with encrypted PII
    child = await Child.create_child(
        db_session,
        user_id=current_user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        jersey_size=data.jersey_size,
        grade=data.grade,
        medical_conditions_encrypted=encrypt_pii(data.medical_conditions),
        has_no_medical_conditions=data.has_no_medical_conditions,
        after_school_attendance=data.after_school_attendance,
        after_school_program=data.after_school_program,
        health_insurance_number_encrypted=encrypt_pii(data.health_insurance_number),
        how_heard_about_us=data.how_heard_about_us,
        how_heard_other_text=data.how_heard_other_text,
    )

    # Create emergency contacts if provided
    if data.emergency_contacts:
        from app.models.child import EmergencyContact as EC

        child_id = child.id  # Save id before any potential expiry
        for ec_data in data.emergency_contacts:
            contact = EC(
                child_id=child_id,
                name=ec_data.name,
                relation=ec_data.relation,
                phone=ec_data.phone,
                email=ec_data.email,
                is_primary=ec_data.is_primary,
            )
            db_session.add(contact)
        await db_session.commit()
        # Clear session cache and reload child with eager loading
        db_session.expire_all()
        child = await Child.get_by_id(db_session, child_id)

    logger.info(f"Child created successfully: {child.id}")
    return child_to_response(child)


@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(
    child_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """
    Get child details by ID.

    Parents can only access their own children. Admins can access any child.
    """
    logger.info(f"Get child request by user: {current_user.id}, child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        logger.warning(f"Child not found: {child_id}")
        raise NotFoundException(message="Child not found")

    await verify_child_access(child, current_user)
    return child_to_response(child)


@router.put("/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: str,
    data: ChildUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> ChildResponse:
    """
    Update child information.

    Parents can only update their own children. Admins can update any child.
    """
    logger.info(f"Update child request by user: {current_user.id}, child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        logger.warning(f"Child not found: {child_id}")
        raise NotFoundException(message="Child not found")

    await verify_child_access(child, current_user)

    update_data = data.model_dump(exclude_unset=True)

    # Handle encrypted fields
    if "medical_conditions" in update_data:
        update_data["medical_conditions_encrypted"] = encrypt_pii(
            update_data.pop("medical_conditions")
        )
    if "health_insurance_number" in update_data:
        update_data["health_insurance_number_encrypted"] = encrypt_pii(
            update_data.pop("health_insurance_number")
        )

    for field, value in update_data.items():
        setattr(child, field, value)

    await db_session.commit()
    await db_session.refresh(child)
    logger.info(f"Child updated successfully: {child_id}")
    return child_to_response(child)


@router.delete("/{child_id}")
async def delete_child(
    child_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft delete a child.

    Parents can only delete their own children. Admins can delete any child.
    """
    logger.info(f"Delete child request by user: {current_user.id}, child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        logger.warning(f"Child not found: {child_id}")
        raise NotFoundException(message="Child not found")

    await verify_child_access(child, current_user)

    child.is_active = False
    await db_session.commit()
    logger.info(f"Child soft deleted: {child_id}")
    return {"message": "Child deleted successfully"}


# Emergency Contact endpoints


@router.get("/{child_id}/emergency-contacts", response_model=list[EmergencyContactResponse])
async def list_emergency_contacts(
    child_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> list[EmergencyContactResponse]:
    """List emergency contacts for a child."""
    logger.info(f"List emergency contacts for child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        raise NotFoundException(message="Child not found")

    await verify_child_access(child, current_user)

    contacts = await EmergencyContact.get_by_child_id(db_session, child_id)
    return [EmergencyContactResponse.model_validate(c) for c in contacts]


@router.post("/{child_id}/emergency-contacts", response_model=EmergencyContactResponse)
async def create_emergency_contact(
    child_id: str,
    data: EmergencyContactCreate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> EmergencyContactResponse:
    """Add an emergency contact to a child."""
    logger.info(f"Create emergency contact for child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        raise NotFoundException(message="Child not found")

    await verify_child_access(child, current_user)

    contact = await EmergencyContact.create_contact(
        db_session,
        child_id=child_id,
        name=data.name,
        relation=data.relation,
        phone=data.phone,
        email=data.email,
        is_primary=data.is_primary,
    )
    logger.info(f"Emergency contact created: {contact.id}")
    return EmergencyContactResponse.model_validate(contact)


@router.put("/emergency-contacts/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    contact_id: str,
    data: EmergencyContactUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> EmergencyContactResponse:
    """Update an emergency contact."""
    logger.info(f"Update emergency contact: {contact_id}")
    contact = await EmergencyContact.get_by_id(db_session, contact_id)
    if not contact:
        raise NotFoundException(message="Emergency contact not found")

    # Get parent child to verify access
    child = await Child.get_by_id(db_session, contact.child_id)
    await verify_child_access(child, current_user)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await db_session.commit()
    await db_session.refresh(contact)
    logger.info(f"Emergency contact updated: {contact_id}")
    return EmergencyContactResponse.model_validate(contact)


@router.delete("/emergency-contacts/{contact_id}")
async def delete_emergency_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an emergency contact."""
    logger.info(f"Delete emergency contact: {contact_id}")
    contact = await EmergencyContact.get_by_id(db_session, contact_id)
    if not contact:
        raise NotFoundException(message="Emergency contact not found")

    # Get parent child to verify access
    child = await Child.get_by_id(db_session, contact.child_id)
    await verify_child_access(child, current_user)

    await db_session.delete(contact)
    await db_session.commit()
    logger.info(f"Emergency contact deleted: {contact_id}")
    return {"message": "Emergency contact deleted successfully"}
