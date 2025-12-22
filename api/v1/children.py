from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.child import Child, EmergencyContact
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.program import School
from app.models.user import User
from app.schemas.child import (
    ChildCreate,
    ChildEnrollmentInfo,
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


async def child_to_response(child: Child, db_session: AsyncSession) -> ChildResponse:
    """Convert Child model to response with decrypted PII and enrollment info."""
    # Fetch active enrollments for this child
    enrollments_query = select(Enrollment).where(
        Enrollment.child_id == child.id,
        Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING])
    )
    result = await db_session.execute(enrollments_query)
    enrollments = result.scalars().all()

    # Build enrollment info with class and school names
    enrollment_info = []
    for enrollment in enrollments:
        # Get class details
        class_result = await db_session.execute(
            select(Class).where(Class.id == enrollment.class_id)
        )
        class_ = class_result.scalar_one_or_none()

        # Get school details if class has a school
        school_name = None
        school_id = None
        if class_ and class_.school_id:
            school_id = class_.school_id
            school_result = await db_session.execute(
                select(School).where(School.id == class_.school_id)
            )
            school = school_result.scalar_one_or_none()
            if school:
                school_name = school.name

        if class_:
            enrollment_info.append(
                ChildEnrollmentInfo(
                    enrollment_id=enrollment.id,
                    class_id=enrollment.class_id,
                    class_name=class_.name,
                    school_id=school_id,
                    school_name=school_name,
                    weekdays=class_.weekdays,
                    status=enrollment.status.value,
                    class_status=class_.status.value if hasattr(class_, 'status') else 'active',
                    enrolled_at=enrollment.enrolled_at,
                )
            )

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
        has_medical_alert=child.has_medical_alert,
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
        enrollments=enrollment_info,
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


async def verify_emergency_contact_access(child: Child, user: User) -> None:
    """
    Verify user can manage emergency contacts for this child.

    Emergency contacts can only be managed by:
    - Admin/Owner (any child)
    - Parent (their own children only)

    Staff/Coach role CANNOT manage emergency contacts.
    """
    # Block coach/staff role explicitly
    if user.role.value == "coach":
        raise ForbiddenException(
            message="Staff members cannot manage emergency contacts"
        )

    # Admin/Owner can manage any child's emergency contacts
    if user.role.value in ["owner", "admin"]:
        return

    # Parent can only manage their own children's emergency contacts
    if child.user_id != user.id:
        raise ForbiddenException(
            message="You can only manage emergency contacts for your own children"
        )


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

    # Build response with enrollment info
    items = []
    for child in children:
        item = await child_to_response(child, db_session)
        items.append(item)

    return ChildListResponse(
        items=items,
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

    # Validate emergency contacts (min 1, max 3)
    if not data.emergency_contacts or len(data.emergency_contacts) < 1:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(message="At least 1 emergency contact is required")

    if len(data.emergency_contacts) > 3:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(message="Maximum 3 emergency contacts allowed per child")

    # Determine if child has medical alert (for check-in dashboard)
    has_medical_alert = bool(
        data.medical_conditions and
        not data.has_no_medical_conditions
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
        has_medical_alert=has_medical_alert,
        after_school_attendance=data.after_school_attendance,
        after_school_program=data.after_school_program,
        health_insurance_number_encrypted=encrypt_pii(data.health_insurance_number),
        how_heard_about_us=data.how_heard_about_us,
        how_heard_other_text=data.how_heard_other_text,
        organization_id=current_user.organization_id,
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
                organization_id=current_user.organization_id,
            )
            db_session.add(contact)
        await db_session.commit()
        # Clear session cache and reload child with eager loading
        db_session.expire_all()
        child = await Child.get_by_id(db_session, child_id)

    logger.info(f"Child created successfully: {child.id}")
    return await child_to_response(child, db_session)


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
    return await child_to_response(child, db_session)


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
        # Update has_medical_alert based on medical conditions
        has_no_medical = update_data.get("has_no_medical_conditions", child.has_no_medical_conditions)
        update_data["has_medical_alert"] = bool(
            update_data.get("medical_conditions_encrypted") and not has_no_medical
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
    return await child_to_response(child, db_session)


@router.delete("/{child_id}")
async def delete_child(
    child_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft delete a child.

    Only admins and owners can delete children (not parents).
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
    """Add an emergency contact to a child (maximum 3 allowed)."""
    logger.info(f"Create emergency contact for child: {child_id}")
    child = await Child.get_by_id(db_session, child_id)
    if not child:
        raise NotFoundException(message="Child not found")

    await verify_emergency_contact_access(child, current_user)

    # Check if child already has 3 emergency contacts
    existing_contacts = await EmergencyContact.get_by_child_id(db_session, child_id)
    if len(existing_contacts) >= 3:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(message="Maximum 3 emergency contacts allowed per child")

    contact = await EmergencyContact.create_contact(
        db_session,
        child_id=child_id,
        name=data.name,
        relation=data.relation,
        phone=data.phone,
        email=data.email,
        is_primary=data.is_primary,
        organization_id=current_user.organization_id,
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
    await verify_emergency_contact_access(child, current_user)

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
    await verify_emergency_contact_access(child, current_user)

    await db_session.delete(contact)
    await db_session.commit()
    logger.info(f"Emergency contact deleted: {contact_id}")
    return {"message": "Emergency contact deleted successfully"}
