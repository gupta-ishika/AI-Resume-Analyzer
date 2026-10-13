from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    category: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Base class for all domain and HTTP application errors."""

    def __init__(
        self,
        code: str,
        category: str,
        message: str,
        status_code: int = 400,
        details: Any = None,
    ):
        super().__init__(message)
        self.code = code
        self.category = category
        self.message = message
        self.status_code = status_code
        self.details = details


# Specific typed errors
class NotFoundError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, category="system", message=message, status_code=404)


class ConflictError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, category="validation", message=message, status_code=409)


class ValidationError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, category="validation", message=message, status_code=400)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Standardized error response handler for AppError."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "category": exc.category,
                "message": exc.message,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safe fallback error handler: never exposes internal traces or secrets."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "category": "system",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )
