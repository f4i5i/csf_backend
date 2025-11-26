from typing import Any, Dict, Optional


class CustomException(Exception):
    """Base exception class for all custom exceptions."""

    code: int = 500
    error_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred"
    data: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        message: str = None,
        code: int = None,
        error_code: str = None,
        data: Dict[str, Any] = None
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.error_code = error_code or self.error_code
        self.data = data or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code}, error_code={self.error_code}, message={self.message})"


class BadRequestException(CustomException):
    """Exception for bad request errors (400)."""

    code = 400
    error_code = "BAD_REQUEST"
    message = "Bad request"


class UnauthorizedException(CustomException):
    """Exception for unauthorized access (401)."""

    code = 401
    error_code = "UNAUTHORIZED"
    message = "Unauthorized"


class ForbiddenException(CustomException):
    """Exception for forbidden access (403)."""

    code = 403
    error_code = "FORBIDDEN"
    message = "Access forbidden"


class NotFoundException(CustomException):
    """Exception for resource not found (404)."""

    code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictException(CustomException):
    """Exception for resource conflicts (409)."""

    code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"


class ValidationException(CustomException):
    """Exception for validation errors (422)."""

    code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation error"