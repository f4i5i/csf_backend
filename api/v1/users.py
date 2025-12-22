from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin, get_current_user
from app.models.user import Role, User
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.utils.security import hash_password
from core.db import get_db
from core.exceptions.base import BadRequestException, ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user's profile.

    Requires authentication.
    """
    logger.info(f"Get profile request for user: {current_user.id}")
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user's profile.

    Requires authentication.
    Cannot change email or role through this endpoint.
    """
    logger.info(f"Update profile request for user: {current_user.id}")
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db_session.commit()
    await db_session.refresh(current_user)
    logger.info(f"Profile updated successfully for user: {current_user.id}")
    return UserResponse.model_validate(current_user)


# ============== Admin User Management Endpoints ==============


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[Role] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    List all users with optional filtering.

    Admin/Owner only. Returns paginated list of users.
    """
    logger.info(f"List users request by admin: {current_user.id}")

    # Build query
    query = select(User).where(User.organization_id == current_user.organization_id)

    # Apply filters
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(User.email).like(search_term),
                func.lower(User.first_name).like(search_term),
                func.lower(User.last_name).like(search_term),
            )
        )

    if role:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db_session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db_session.execute(query)
    users = result.scalars().all()

    logger.info(f"Found {len(users)} users (total: {total})")
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get user by ID.

    Admin/Owner only.
    """
    logger.info(f"Get user request by admin: {current_user.id}, user: {user_id}")

    user = await User.get_by_id(db_session, user_id)
    if not user:
        raise NotFoundException(message="User not found")

    # Check same organization
    if user.organization_id != current_user.organization_id:
        raise ForbiddenException(message="Access denied")

    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    data: AdminUserCreate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Create a new user.

    Admin/Owner only. If password is not provided, user will need to reset password.
    """
    logger.info(f"Create user request by admin: {current_user.id}, email: {data.email}")

    # Check if email already exists in the organization
    normalized_email = User.normalize_email(data.email)
    existing_query = select(User).where(
        User.email == normalized_email,
        User.organization_id == current_user.organization_id,
    )
    result = await db_session.execute(existing_query)
    if result.scalars().first():
        raise BadRequestException(message="Email already registered in this organization")

    # Only owner can create admin/owner users
    if data.role in [Role.ADMIN, Role.OWNER] and current_user.role != Role.OWNER:
        raise ForbiddenException(message="Only owners can create admin or owner users")

    # Hash password if provided
    hashed_password = None
    if data.password:
        hashed_password = hash_password(data.password)

    # Create user
    user = await User.create_user(
        db_session,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        hashed_password=hashed_password,
        role=data.role,
        phone=data.phone,
        organization_id=current_user.organization_id,
    )

    # Set is_active status
    if not data.is_active:
        user.is_active = False
        await db_session.commit()
        await db_session.refresh(user)

    logger.info(f"User created successfully: {user.id}")
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update a user.

    Admin/Owner only. Owners can update any user, admins cannot update owners.
    """
    logger.info(f"Update user request by admin: {current_user.id}, user: {user_id}")

    user = await User.get_by_id(db_session, user_id)
    if not user:
        raise NotFoundException(message="User not found")

    # Check same organization
    if user.organization_id != current_user.organization_id:
        raise ForbiddenException(message="Access denied")

    # Prevent admin from modifying owner
    if user.role == Role.OWNER and current_user.role != Role.OWNER:
        raise ForbiddenException(message="Only owners can modify owner accounts")

    # Only owner can change roles to admin/owner
    if data.role and data.role in [Role.ADMIN, Role.OWNER] and current_user.role != Role.OWNER:
        raise ForbiddenException(message="Only owners can assign admin or owner roles")

    # Prevent self-demotion for owners
    if user.id == current_user.id and data.role and data.role != Role.OWNER and current_user.role == Role.OWNER:
        raise BadRequestException(message="Cannot demote yourself from owner role")

    update_data = data.model_dump(exclude_unset=True)

    # Check email uniqueness if changing email
    if "email" in update_data and update_data["email"]:
        normalized_email = User.normalize_email(update_data["email"])
        if normalized_email != user.email:
            existing_query = select(User).where(
                User.email == normalized_email,
                User.organization_id == current_user.organization_id,
                User.id != user_id,
            )
            result = await db_session.execute(existing_query)
            if result.scalars().first():
                raise BadRequestException(message="Email already registered in this organization")
            update_data["email"] = normalized_email

    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]

    for field, value in update_data.items():
        setattr(user, field, value)

    await db_session.commit()
    await db_session.refresh(user)
    logger.info(f"User updated successfully: {user_id}")
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft delete a user.

    Admin/Owner only. Cannot delete self or owner accounts (unless you are owner).
    """
    logger.info(f"Delete user request by admin: {current_user.id}, user: {user_id}")

    user = await User.get_by_id(db_session, user_id)
    if not user:
        raise NotFoundException(message="User not found")

    # Check same organization
    if user.organization_id != current_user.organization_id:
        raise ForbiddenException(message="Access denied")

    # Cannot delete yourself
    if user.id == current_user.id:
        raise BadRequestException(message="Cannot delete your own account")

    # Only owner can delete owner/admin accounts
    if user.role in [Role.OWNER, Role.ADMIN] and current_user.role != Role.OWNER:
        raise ForbiddenException(message="Only owners can delete admin or owner accounts")

    # Soft delete
    user.is_active = False
    await db_session.commit()
    logger.info(f"User soft deleted: {user_id}")
    return {"message": "User deleted successfully"}
