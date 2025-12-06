"""Request validation utilities and custom exception handlers (Task 10.2)."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def format_validation_error(exc: RequestValidationError | ValidationError) -> Dict[str, Any]:
    """Format Pydantic validation errors into a clear, user-friendly structure.
    
    Extracts field paths, messages, and error types from Pydantic validation
    errors and formats them for API responses.
    
    Args:
        exc: Request or Pydantic validation error
        
    Returns:
        Dictionary with 'detail' and 'errors' fields
    """
    
    errors = []
    for error in exc.errors():
        # Build field path from nested locations
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(f"Validation error: {len(errors)} field(s) failed validation")
    
    return {
        "detail": "Request validation failed",
        "errors": errors,
    }


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Custom exception handler for FastAPI request validation errors.
    
    Provides clear, structured error messages when request validation fails.
    
    Args:
        request: The FastAPI request object
        exc: The validation exception
        
    Returns:
        JSON response with structured error details
    """
    
    logger.warning(f"Request validation failed for {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(format_validation_error(exc)),
    )


async def pydantic_exception_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Custom exception handler for Pydantic validation errors.
    
    Handles validation errors that occur during response model validation
    or other Pydantic operations.
    
    Args:
        request: The FastAPI request object
        exc: The validation exception
        
    Returns:
        JSON response with structured error details
    """
    
    logger.error(f"Pydantic validation error for {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(format_validation_error(exc)),
    )


def validate_request_size(content_length: int, max_size: int = 10 * 1024 * 1024) -> None:
    """Validate that the request size does not exceed the maximum allowed.
    
    Prevents excessively large requests from consuming resources.
    
    Args:
        content_length: Size of the request body in bytes
        max_size: Maximum allowed size in bytes (default 10MB)
        
    Raises:
        ValueError: If content length exceeds max_size
    """
    if content_length > max_size:
        raise ValueError(
            f"Request body too large: {content_length} bytes. "
            f"Maximum allowed: {max_size} bytes ({max_size / (1024 * 1024):.1f}MB)"
        )
