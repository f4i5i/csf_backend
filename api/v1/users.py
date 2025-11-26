from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from core.db import get_db
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
