"""Rate limiting middleware for the ELEANOR Moral Ops Center API.

Task 10.5: Implement per-IP rate limiting with exponential backoff.
Configurable via environment variables.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from eje.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Track rate limit state for a single IP address."""
    
    request_times: list[float] = field(default_factory=list)
    violation_count: int = 0
    last_violation: float = 0.0
    backoff_until: float = 0.0


class RateLimiter:
    """Per-IP rate limiter with exponential backoff.
    
    Features:
    - Sliding window rate limiting per IP
    - Exponential backoff on repeated violations
    - Thread-safe state management
    - Configurable via settings
    """
    
    def __init__(self, settings: Settings):
        """Initialize rate limiter with configuration.
        
        Args:
            settings: Application settings with rate limit configuration
        """
        self.settings = settings
        self.states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self.lock = Lock()
        
        logger.info(
            f"Rate limiter initialized: {settings.rate_limit_requests} requests per "
            f"{settings.rate_limit_window}s window, "
            f"backoff base {settings.rate_limit_backoff_base}s"
        )
    
    def _clean_old_requests(self, state: RateLimitState, current_time: float) -> None:
        """Remove requests outside the current time window."""
        cutoff = current_time - self.settings.rate_limit_window
        state.request_times = [t for t in state.request_times if t > cutoff]
    
    def _calculate_backoff(self, violation_count: int) -> float:
        """Calculate exponential backoff duration in seconds."""
        return self.settings.rate_limit_backoff_base * (2 ** (violation_count - 1))
    
    def check_rate_limit(self, ip: str) -> tuple[bool, dict]:
        """Check if request from IP should be allowed.
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (allowed: bool, info: dict with rate limit details)
        """
        with self.lock:
            current_time = time.time()
            state = self.states[ip]
            
            # Check if currently in backoff period
            if state.backoff_until > current_time:
                remaining = int(state.backoff_until - current_time)
                return False, {
                    "allowed": False,
                    "reason": "backoff",
                    "retry_after": remaining,
                    "violation_count": state.violation_count
                }
            
            # Clean old requests and check rate
            self._clean_old_requests(state, current_time)
            request_count = len(state.request_times)
            
            if request_count >= self.settings.rate_limit_requests:
                # Rate limit exceeded
                state.violation_count += 1
                state.last_violation = current_time
                
                # Calculate and apply exponential backoff
                backoff_duration = self._calculate_backoff(state.violation_count)
                state.backoff_until = current_time + backoff_duration
                
                logger.warning(
                    f"Rate limit exceeded for {ip}: "
                    f"violation #{state.violation_count}, "
                    f"backoff {backoff_duration:.1f}s"
                )
                
                return False, {
                    "allowed": False,
                    "reason": "rate_limit",
                    "retry_after": int(backoff_duration),
                    "violation_count": state.violation_count,
                    "limit": self.settings.rate_limit_requests,
                    "window": self.settings.rate_limit_window
                }
            
            # Allow request and record it
            state.request_times.append(current_time)
            
            # Reset violation count if enough time has passed since last violation
            if (state.last_violation > 0 and 
                current_time - state.last_violation > self.settings.rate_limit_window * 2):
                state.violation_count = 0
            
            return True, {
                "allowed": True,
                "remaining": self.settings.rate_limit_requests - request_count - 1,
                "limit": self.settings.rate_limit_requests,
                "window": self.settings.rate_limit_window
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        """Initialize middleware with rate limiter.
        
        Args:
            app: FastAPI application
            rate_limiter: Configured RateLimiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiter."""
        # Extract client IP (handles proxy headers)
        ip = request.client.host if request.client else "unknown"
        
        # Check forwarded headers for real IP behind proxies
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        
        # Check rate limit
        allowed, info = self.rate_limiter.check_rate_limit(ip)
        
        if not allowed:
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": (
                        f"Too many requests from {ip}. "
                        f"Please retry after {info['retry_after']} seconds."
                    ),
                    "retry_after": info["retry_after"],
                    "violation_count": info["violation_count"],
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info.get("limit", "N/A")),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Window"] = str(info["window"])
        
        return response


def create_rate_limit_middleware(settings: Settings) -> RateLimitMiddleware:
    """Factory function to create rate limit middleware.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured RateLimitMiddleware instance
    """
    rate_limiter = RateLimiter(settings)
    return lambda app: RateLimitMiddleware(app, rate_limiter)
