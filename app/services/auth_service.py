from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.password_history import PasswordHistory
from app.models.password_reset_token import PasswordResetToken
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

    async def get_or_create_default_organization(self) -> str:
        """Get or create the default organization for new users."""
        # Check if default organization exists
        result = await self.db_session.execute(
            select(Organization).where(Organization.slug == "csf-default")
        )
        org = result.scalar_one_or_none()

        if not org:
            # Create default organization
            org = Organization(
                name="CSF School Academy",
                slug="csf-default",
                description="Default organization for CSF School Academy",
                is_active=True,
            )
            self.db_session.add(org)
            await self.db_session.commit()
            await self.db_session.refresh(org)

        return org.id

    async def register(self, data: UserCreate) -> Tuple[User, TokenResponse]:
        """Register a new user."""
        # Check if email exists
        existing_user = await User.get_by_email(self.db_session, data.email)
        if existing_user:
            raise BadRequestException(message="Email already registered")

        # Hash password
        hashed_password = hash_password(data.password)

        # Get or create default organization
        organization_id = await self.get_or_create_default_organization()

        # Create user
        user = await User.create_user(
            db_session=self.db_session,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            organization_id=organization_id,
            hashed_password=hashed_password,
            phone=data.phone,
        )

        # Add password to history
        await PasswordHistory.add_password(
            self.db_session, user.id, hashed_password
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

    async def logout(self, refresh_token: str | None = None) -> dict:
        """
        Logout user.

        Currently this is a stateless JWT implementation, so logout is handled
        client-side by deleting tokens. This endpoint validates the token (if provided)
        and returns success.

        TODO: Implement token blacklisting or refresh token tracking for enhanced security:
        - Store active refresh tokens in database
        - Invalidate refresh token on logout
        - Add token blacklist for access tokens (with TTL matching token expiry)
        - Enable "logout from all devices" functionality
        """
        if refresh_token:
            # Validate the refresh token before logout
            payload = decode_token(refresh_token)

            if payload.get("type") != "refresh":
                raise UnauthorizedException(message="Invalid token type")

            user_id = payload.get("sub")
            user = await User.get_by_id(self.db_session, user_id)

            if not user:
                raise UnauthorizedException(message="User not found")

            # TODO: If refresh tokens are tracked in DB, invalidate them here
            # await self._invalidate_refresh_token(user_id, refresh_token)

        return {"message": "Logged out successfully"}

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

        hashed_password = hash_password(password)

        # Get or create default organization
        organization_id = await self.get_or_create_default_organization()

        user = await User.create_user(
            db_session=self.db_session,
            email=email,
            first_name=first_name,
            last_name=last_name,
            organization_id=organization_id,
            hashed_password=hashed_password,
            role=Role.ADMIN,
        )
        user.is_verified = True
        await self.db_session.commit()
        await self.db_session.refresh(user)

        # Add password to history
        await PasswordHistory.add_password(
            self.db_session, user.id, hashed_password
        )

        return user

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> User:
        """
        Change user password with validation.

        Validates:
        - Old password is correct
        - New password not in last 5 passwords
        - User exists and is active

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            Updated user

        Raises:
            UnauthorizedException: If old password is incorrect
            BadRequestException: If new password was recently used
        """
        user = await User.get_by_id(self.db_session, user_id)

        if not user or not user.is_active:
            raise UnauthorizedException(message="User not found or inactive")

        # Verify old password
        if not user.hashed_password or not verify_password(
            old_password, user.hashed_password
        ):
            raise UnauthorizedException(message="Current password is incorrect")

        # Check if new password was used recently
        is_reused = await PasswordHistory.check_password_reuse(
            self.db_session, user_id, new_password
        )
        if is_reused:
            raise BadRequestException(
                message="Password was recently used. Please choose a different password."
            )

        # Update password
        hashed_password = hash_password(new_password)
        user.hashed_password = hashed_password
        await self.db_session.commit()
        await self.db_session.refresh(user)

        # Add new password to history
        await PasswordHistory.add_password(
            self.db_session, user_id, hashed_password
        )

        return user

    async def forgot_password(self, email: str) -> PasswordResetToken:
        """
        Initiate forgot password flow.

        Args:
            email: User email

        Returns:
            Password reset token

        Raises:
            NotFoundException: If user with email doesn't exist
        """
        # Get user by email
        user = await User.get_by_email(self.db_session, email)

        if not user:
            # Don't reveal if email exists or not for security
            raise BadRequestException(
                message="If an account exists with this email, you will receive a password reset link."
            )

        if not user.is_active:
            raise BadRequestException(message="Account is deactivated")

        # Invalidate any existing tokens for this user
        await PasswordResetToken.invalidate_user_tokens(self.db_session, user.id)

        # Create new reset token
        reset_token = await PasswordResetToken.create_token(
            self.db_session, user.id, user.organization_id
        )

        # TODO: Send email with reset link
        # The email should contain a link like:
        # https://yourapp.com/reset-password?token={reset_token.token}

        return reset_token

    async def reset_password(
        self, token: str, new_password: str
    ) -> User:
        """
        Reset password using reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            Updated user

        Raises:
            BadRequestException: If token is invalid or expired
        """
        # Get token from database
        reset_token = await PasswordResetToken.get_by_token(self.db_session, token)

        if not reset_token:
            raise BadRequestException(message="Invalid or expired reset token")

        if not reset_token.is_valid():
            raise BadRequestException(message="Invalid or expired reset token")

        # Get user
        user = await User.get_by_id(self.db_session, reset_token.user_id)

        if not user or not user.is_active:
            raise BadRequestException(message="User not found or inactive")

        # Check if new password was used recently
        is_reused = await PasswordHistory.check_password_reuse(
            self.db_session, user.id, new_password
        )
        if is_reused:
            raise BadRequestException(
                message="Password was recently used. Please choose a different password."
            )

        # Update password
        hashed_password = hash_password(new_password)
        user.hashed_password = hashed_password
        await self.db_session.commit()
        await self.db_session.refresh(user)

        # Mark token as used
        await reset_token.mark_as_used(self.db_session)

        # Add new password to history
        await PasswordHistory.add_password(
            self.db_session, user.id, hashed_password
        )

        return user
