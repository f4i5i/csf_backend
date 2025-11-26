from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService
from core.db import get_db
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(
    data: UserCreate,
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Register a new user.

    Returns user data and authentication tokens.
    """
    logger.info(f"Register request for email: {data.email}")
    service = AuthService(db_session)
    user, tokens = await service.register(data)
    logger.info(f"User registered successfully: {user.id}")
    return {
        "user": UserResponse.model_validate(user),
        "tokens": tokens,
    }


@router.post("/token", response_model=TokenResponse)
async def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    OAuth2 compatible token endpoint for Swagger UI.

    Use this endpoint with the "Authorize" button in Swagger.
    Username field expects email address.
    """
    logger.info(f"OAuth2 login attempt for email: {form_data.username}")
    service = AuthService(db_session)
    user, tokens = await service.login(form_data.username, form_data.password)
    logger.info(f"User logged in successfully: {user.id}")
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db_session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.

    Accepts JSON body with email and password fields.
    Use this for your frontend application.
    """
    logger.info(f"Login attempt for email: {data.email}")
    service = AuthService(db_session)
    user, tokens = await service.login(data.email, data.password)
    logger.info(f"User logged in successfully: {user.id}")
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db_session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    logger.info("Token refresh request")
    service = AuthService(db_session)
    tokens = await service.refresh_token(data.refresh_token)
    logger.info("Token refreshed successfully")
    return tokens


@router.post("/google")
async def google_auth(
    data: GoogleAuthRequest,
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate user with Google OAuth.

    - Verifies the Google ID token
    - Creates new user on first login
    - Links existing user by email
    - Returns user data and JWT tokens
    """
    logger.info("Google OAuth authentication request")
    service = GoogleAuthService(db_session)
    user, tokens = await service.authenticate(data.token)
    logger.info(f"Google auth successful for user: {user.id}")
    return {
        "user": UserResponse.model_validate(user),
        "tokens": tokens,
    }
