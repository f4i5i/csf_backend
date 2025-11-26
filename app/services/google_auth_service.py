import asyncio
from functools import partial
from typing import Tuple

from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import TokenResponse
from app.utils.security import create_tokens
from core.config import config
from core.exceptions.base import UnauthorizedException


class GoogleAuthService:
    """Service for Google OAuth authentication."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def authenticate(self, token: str) -> Tuple[User, TokenResponse]:
        """
        Authenticate user with Google ID token.

        - Verifies the Google token
        - Creates new user on first login
        - Links existing user by email
        - Returns JWT tokens
        """
        verifier = partial(
            id_token.verify_oauth2_token,
            token,
            requests.Request(),
            config.GOOGLE_CLIENT_ID,
        )

        try:
            idinfo = await asyncio.to_thread(verifier)
        except ValueError:
            raise UnauthorizedException(message="Invalid Google token")

        google_id = idinfo["sub"]
        email = idinfo["email"]
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        # Check if user exists by google_id
        user = await User.get_by_google_id(self.db_session, google_id)

        if not user:
            # Check by email
            user = await User.get_by_email(self.db_session, email)
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                await self.db_session.commit()
            else:
                # Create new user
                user = await User.create_user(
                    db_session=self.db_session,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_id,
                )
                user.is_verified = True
                await self.db_session.commit()
                await self.db_session.refresh(user)

        if not user.is_active:
            raise UnauthorizedException(message="Account is deactivated")

        access_token, refresh_token = create_tokens(user.id, user.role.value)

        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
