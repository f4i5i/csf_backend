from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User
from app.schemas.user import TokenResponse, UserCreate
from app.utils.security import (
    create_tokens,
    decode_token,
    hash_password,
    verify_password,
)
from core.exceptions.base import BadRequestException, UnauthorizedException


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def register(self, data: UserCreate) -> Tuple[User, TokenResponse]:
        """Register a new user."""
        # Check if email exists
        existing_user = await User.get_by_email(self.db_session, data.email)
        if existing_user:
            raise BadRequestException(message="Email already registered")

        # Create user
        user = await User.create_user(
            db_session=self.db_session,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            hashed_password=hash_password(data.password),
            phone=data.phone,
        )

        # Generate tokens
        access_token, refresh_token = create_tokens(user.id, user.role.value)

        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def login(self, email: str, password: str) -> Tuple[User, TokenResponse]:
        """Authenticate user with email and password."""
        user = await User.get_by_email(self.db_session, email)

        if not user or not user.hashed_password:
            raise UnauthorizedException(message="Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException(message="Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException(message="Account is deactivated")

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self.db_session.commit()

        # Generate tokens
        access_token, refresh_token = create_tokens(user.id, user.role.value)

        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise UnauthorizedException(message="Invalid token type")

        user_id = payload.get("sub")
        user = await User.get_by_id(self.db_session, user_id)

        if not user or not user.is_active:
            raise UnauthorizedException(message="User not found or inactive")

        access_token, new_refresh_token = create_tokens(user.id, user.role.value)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def create_admin_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Create an admin user (for initial setup)."""
        existing_user = await User.get_by_email(self.db_session, email)
        if existing_user:
            raise BadRequestException(message="Email already registered")

        user = await User.create_user(
            db_session=self.db_session,
            email=email,
            first_name=first_name,
            last_name=last_name,
            hashed_password=hash_password(password),
            role=Role.ADMIN,
        )
        user.is_verified = True
        await self.db_session.commit()
        await self.db_session.refresh(user)

        return user
