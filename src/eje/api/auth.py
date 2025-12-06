"""API authentication and audit trail logging (Task 10.4)."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from eje.config.settings import Settings

logger = logging.getLogger(__name__)

# HTTPBearer scheme for extracting Authorization header
security = HTTPBearer(auto_error=False)


class AuthAuditLogger:
    """Centralized authentication audit trail logger.
    
    Logs all authentication attempts (success and failure) with:
    - Timestamp
    - Client IP
    - Endpoint accessed
    - Authentication result
    - Token hash (for tracking without exposing token)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.audit")
    
    def log_auth_attempt(
        self,
        client_ip: str,
        endpoint: str,
        method: str,
        token_provided: bool,
        token_valid: bool,
        token_hash: Optional[str] = None,
    ) -> None:
        """Log an authentication attempt to the audit trail.
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint being accessed
            method: HTTP method
            token_provided: Whether a token was provided
            token_valid: Whether the token was valid
            token_hash: SHA256 hash of token (first 8 chars) for tracking
        """
        timestamp = datetime.utcnow().isoformat()
        result = "SUCCESS" if token_valid else "FAILURE"
        
        log_message = (
            f"[AUTH AUDIT] {timestamp} | {result} | "
            f"{client_ip} | {method} {endpoint} | "
            f"token_provided={token_provided} | "
            f"token_valid={token_valid}"
        )
        
        if token_hash:
            log_message += f" | token_hash={token_hash}"
        
        if token_valid:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)
    
    def log_auth_success(
        self,
        client_ip: str,
        endpoint: str,
        method: str,
        token_hash: str,
    ) -> None:
        """Log a successful authentication."""
        self.log_auth_attempt(
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            token_provided=True,
            token_valid=True,
            token_hash=token_hash,
        )
    
    def log_auth_failure(
        self,
        client_ip: str,
        endpoint: str,
        method: str,
        reason: str,
        token_hash: Optional[str] = None,
    ) -> None:
        """Log a failed authentication attempt."""
        self.log_auth_attempt(
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            token_provided=(token_hash is not None),
            token_valid=False,
            token_hash=token_hash,
        )
        self.logger.warning(f"Authentication failure reason: {reason}")


# Global audit logger instance
audit_logger = AuthAuditLogger()


def hash_token(token: str) -> str:
    """Create a SHA256 hash of the token for audit logging.
    
    Only logs the first 8 characters of the hash to balance
    traceability with security.
    
    Args:
        token: The authentication token
        
    Returns:
        First 8 characters of SHA256 hash
    """
    return hashlib.sha256(token.encode()).hexdigest()[:8]


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies.
    
    Checks X-Forwarded-For header first (for proxied requests),
    falls back to direct client connection.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first (client)
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def verify_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
    settings: Settings,
) -> Optional[HTTPAuthorizationCredentials]:
    """Verify bearer token authentication with audit logging.
    
    Implements OAuth2 Bearer token authentication scheme with:
    - Token validation against configured secret
    - Comprehensive audit trail logging
    - Client IP tracking
    - Graceful handling of missing/invalid tokens
    
    Args:
        credentials: HTTP Authorization credentials from security scheme
        request: FastAPI request object
        settings: Application settings with auth config
        
    Returns:
        Validated credentials if successful
        
    Raises:
        HTTPException: If authentication fails
    """
    client_ip = get_client_ip(request)
    endpoint = request.url.path
    method = request.method
    
    # Check if authentication is required
    if not settings.require_api_token:
        logger.debug("API token authentication is disabled")
        return None
    
    # Check if token is configured
    if not settings.api_token:
        logger.error("API token is required but not configured")
        audit_logger.log_auth_failure(
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            reason="API token not configured on server",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API token not configured",
        )
    
    # Check if credentials were provided
    if not credentials:
        audit_logger.log_auth_failure(
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            reason="No authorization header provided",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    provided_token = credentials.credentials
    token_hash = hash_token(provided_token)
    
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_token, settings.api_token):
        audit_logger.log_auth_failure(
            client_ip=client_ip,
            endpoint=endpoint,
            method=method,
            reason="Invalid token",
            token_hash=token_hash,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Authentication successful
    audit_logger.log_auth_success(
        client_ip=client_ip,
        endpoint=endpoint,
        method=method,
        token_hash=token_hash,
    )
    
    return credentials


def create_auth_dependency(settings: Settings):
    """Create a FastAPI dependency for authentication.
    
    This factory function creates a dependency that can be used
    with FastAPI's Depends() to protect routes.
    
    Args:
        settings: Application settings
        
    Returns:
        Dependency function for route protection
    """
    
    async def auth_dependency(
        credentials: Optional[HTTPAuthorizationCredentials],
        request: Request,
    ) -> Optional[HTTPAuthorizationCredentials]:
        """Verify authentication for the request."""
        return verify_bearer_token(credentials, request, settings)
    
    return auth_dependency


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Useful for generating API keys or session tokens.
    
    Args:
        length: Number of bytes for the token (default 32)
        
    Returns:
        Hex-encoded secure random token
    """
    return secrets.token_hex(length)
