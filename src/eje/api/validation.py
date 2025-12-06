"""Request validation utilities and custom exception handlers."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def format_validation_error(exc: RequestValidationError | ValidationError) -> Dict[str, Any]:
    """Format Pydantic validation errors into a clear, user-friendly structure."""
    
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return {
        "detail": "Request validation failed",
        "errors": errors,
    }


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Custom exception handler for request validation errors."""
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(format_validation_error(exc)),
    )


async def pydantic_exception_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Custom exception handler for Pydantic validation errors."""
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(format_validation_error(exc)),
    )


def validate_request_size(content_length: int, max_size: int = 10 * 1024 * 1024) -> None:
    """Validate that the request size does not exceed the maximum allowed.
    
    Args:
        content_length: Size of the request body in bytes
        max_size: Maximum allowed size in bytes (default 10MB)
        
    Raises:
        ValueError: If content length exceeds max_size
    """
    if content_length > max_size:
        raise ValueError(
            f"Request body too large: {content_length} bytes. Maximum allowed: {max_size} bytes"
        )
