from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
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

    # Block disposable email addresses
    from app.utils.email_validator import is_disposable_email
    if is_disposable_email(data.email):
        from core.exceptions.base import BadRequestException
        raise BadRequestException(
            message="Disposable email addresses are not allowed. Please use a valid email address."
        )

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


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest | None = None,
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Logout user.

    Optionally accepts refresh token for validation.
    Client should delete access and refresh tokens from storage.

    For stateless JWT authentication, the actual logout happens client-side
    by deleting the tokens. This endpoint confirms the logout action.
    """
    logger.info("Logout request")
    service = AuthService(db_session)
    refresh_token = data.refresh_token if data else None
    result = await service.logout(refresh_token)
    logger.info("User logged out successfully")
    return result


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initiate forgot password flow.

    Sends a password reset email if the account exists.
    For security, always returns success message even if email doesn't exist.
    """
    logger.info(f"Forgot password request for email: {data.email}")
    service = AuthService(db_session)
    
    try:
        reset_token = await service.forgot_password(data.email)
        logger.info(f"Password reset token created for user")
        
        # TODO: Send email with reset link
        # For now, return the token in response (remove this in production!)
        # In production, send email and only return success message
        return {
            "message": "If an account exists with this email, you will receive a password reset link.",
            "token": reset_token.token  # REMOVE THIS IN PRODUCTION
        }
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        # Always return same message for security
        return {
            "message": "If an account exists with this email, you will receive a password reset link."
        }


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset password using reset token.

    Validates the token and updates the user's password.
    """
    logger.info(f"Reset password request with token")
    service = AuthService(db_session)
    user = await service.reset_password(data.token, data.new_password)
    logger.info(f"Password reset successfully for user: {user.id}")
    
    return {
        "message": "Password reset successfully. You can now login with your new password."
    }
