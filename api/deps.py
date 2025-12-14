from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User
from app.utils.security import decode_token
from core.db import get_db
from core.exceptions.base import ForbiddenException, UnauthorizedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    if not token:
        raise UnauthorizedException(message="Not authenticated")

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type")

    user_id = payload.get("sub")
    user = await User.get_by_id(db_session, user_id)

    if not user:
        raise UnauthorizedException(message="User not found")

    if not user.is_active:
        raise UnauthorizedException(message="User is inactive")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise UnauthorizedException(message="User is inactive")
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user if they have admin or owner role."""
    if current_user.role not in [Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Admin access required")
    return current_user


async def get_current_owner(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user if they have owner role."""
    if current_user.role != Role.OWNER:
        raise ForbiddenException(message="Owner access required")
    return current_user


async def get_current_staff(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user if they have coach, admin, or owner role."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Coach/staff access required")
    return current_user


async def get_current_parent_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user if they have parent, admin, or owner role.

    This dependency is used for financial endpoints to exclude coach/staff access.
    Staff should not have access to financial data (payments, orders, etc.).
    """
    if current_user.role not in [Role.PARENT, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(
            message="Access denied. Financial data is restricted to parents and administrators."
        )
    return current_user
