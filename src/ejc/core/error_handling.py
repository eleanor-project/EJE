"""
Enhanced Error Handling Module for Eleanor Project's EJE

This module provides comprehensive error handling, recovery mechanisms, and
failure scenario management for the Ethical Jurisprudence Engine.

Key Features:
- Custom exception hierarchy for precise error identification
- Retry mechanisms with exponential backoff
- Circuit breaker pattern for external API calls
- Detailed error logging and tracing
- Graceful degradation strategies

Author: Eleanor Project Contributors
Date: 2025-11-25
Version: 1.0.0
"""

import logging
import time
import functools
from typing import Optional, Callable, Any, Dict, List
from enum import Enum
from datetime import datetime, timedelta


# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Exception Hierarchy
# ============================================================================

class EJEBaseException(Exception):
    """Base exception for all EJE-related errors.
    
    Attributes:
        message: Human-readable error description
        error_code: Unique error identifier for tracking
        context: Additional context about the error
        timestamp: When the error occurred
    """
    
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class CriticException(EJEBaseException):
    """Raised when a critic fails to execute or return valid results."""
    pass


class CriticTimeoutException(CriticException):
    """Raised when a critic exceeds its execution time limit."""
    pass


class CriticAPIException(CriticException):
    """Raised when external API (OpenAI, Anthropic, etc.) fails."""
    pass


class PrecedentException(EJEBaseException):
    """Raised when precedent retrieval or storage fails."""
    pass


class EmbeddingException(PrecedentException):
    """Raised when embedding generation fails."""
    pass


class AuditLogException(EJEBaseException):
    """Raised when audit log operations fail."""
    pass


class ConfigurationException(EJEBaseException):
    """Raised when configuration is invalid or missing."""
    pass


class GovernanceException(EJEBaseException):
    """Raised when governance rules are violated."""
    pass


class HumanEscalationRequired(EJEBaseException):
    """Raised when a case requires mandatory human review.
    
    This is not an error per se, but a signal that the system
    cannot proceed without human intervention.
    """
    pass


# ============================================================================
# Error Severity Levels
# ============================================================================

class ErrorSeverity(Enum):
    """Classification of error severity for handling strategies."""
    LOW = "low"           # Recoverable, can continue with degraded service
    MEDIUM = "medium"     # Requires attention, partial functionality lost
    HIGH = "high"         # Critical component failure, escalation needed
    CRITICAL = "critical" # System-level failure, immediate intervention required


# ============================================================================
# Retry Mechanism with Exponential Backoff
# ============================================================================

class RetryConfig:
    """Configuration for retry mechanism.
    
    Attributes:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to prevent thundering herd
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(
    exceptions: tuple = (Exception,),
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable] = None
):
    """Decorator for retrying functions with exponential backoff.
    
    Args:
        exceptions: Tuple of exception types to catch and retry
        config: RetryConfig instance (uses defaults if None)
        on_retry: Optional callback function called on each retry
    
    Example:
        @retry_with_backoff(
            exceptions=(CriticAPIException, ConnectionError),
            config=RetryConfig(max_attempts=5, base_delay=2.0)
        )
        def call_external_api():
            # API call logic here
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            extra={"error": str(e), "attempts": attempt}
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{config.max_attempts}). "
                        f"Retrying in {delay:.2f}s...",
                        extra={"error": str(e), "delay": delay}
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================

class CircuitState(Enum):
    """States for the circuit breaker pattern."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failures detected, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.
    
    The circuit breaker prevents repeated calls to failing services,
    allowing them time to recover and preventing resource exhaustion.
    
    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Too many failures, requests are blocked
        - HALF_OPEN: After timeout, allows test requests through
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers the circuit
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitState.CLOSED
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, transitioning if necessary."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
        
        return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return False
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of func execution
        
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception raised by func
        """
        if self.state == CircuitState.OPEN:
            raise CriticException(
                "Circuit breaker is OPEN - service unavailable",
                error_code="CIRCUIT_BREAKER_OPEN",
                context={"failure_count": self._failure_count}
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker test successful - closing circuit")
            self._reset()
    
    def _on_failure(self):
        """Handle failed execution."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker opened after {self._failure_count} failures",
                extra={"recovery_timeout": self.recovery_timeout}
            )
    
    def _reset(self):
        """Reset circuit breaker to closed state."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED


# ============================================================================
# Error Recovery Strategies
# ============================================================================

class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def can_recover(self, exception: Exception) -> bool:
        """Determine if this strategy can recover from the given exception."""
        raise NotImplementedError
    
    def recover(self, exception: Exception, context: Dict[str, Any]) -> Any:
        """Attempt to recover from the exception."""
        raise NotImplementedError


class GracefulDegradationStrategy(ErrorRecoveryStrategy):
    """Strategy for graceful degradation when services fail.
    
    This strategy allows the system to continue operating with reduced
    functionality when non-critical components fail.
    """
    
    def __init__(self, fallback_value: Any = None):
        self.fallback_value = fallback_value
    
    def can_recover(self, exception: Exception) -> bool:
        """Can recover from non-critical failures."""
        return isinstance(exception, (CriticException, PrecedentException))
    
    def recover(self, exception: Exception, context: Dict[str, Any]) -> Any:
        """Return fallback value and log degradation."""
        logger.warning(
            f"Graceful degradation triggered: {exception}",
            extra=context
        )
        return self.fallback_value


class FallbackCriticStrategy(ErrorRecoveryStrategy):
    """Strategy to use alternative critics when primary ones fail."""
    
    def __init__(self, fallback_critics: List[str]):
        self.fallback_critics = fallback_critics
    
    def can_recover(self, exception: Exception) -> bool:
        """Can recover from critic failures."""
        return isinstance(exception, CriticException)
    
    def recover(self, exception: Exception, context: Dict[str, Any]) -> Any:
        """Attempt to use fallback critics."""
        logger.info(
            f"Primary critic failed, trying fallback critics: {self.fallback_critics}",
            extra=context
        )
        # Implementation would invoke fallback critics
        # This is a template - actual implementation depends on critic system
        return None


# ============================================================================
# Error Context Manager
# ============================================================================

class ErrorContext:
    """Context manager for enhanced error handling and logging.
    
    Automatically captures exception details, logs them, and can apply
    recovery strategies.
    
    Example:
        with ErrorContext(
            operation="critic_execution",
            severity=ErrorSeverity.HIGH,
            recovery_strategy=GracefulDegradationStrategy(fallback_value={})
        ) as ctx:
            result = execute_critic()
            ctx.set_result(result)
    """
    
    def __init__(
        self,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_strategy: Optional[ErrorRecoveryStrategy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.metadata = metadata or {}
        self.start_time = None
        self.result = None
        self.exception = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting operation: {self.operation}", extra=self.metadata)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # Success case
            logger.info(
                f"Operation '{self.operation}' completed successfully in {duration:.2f}s",
                extra={**self.metadata, "duration": duration}
            )
            return False
        
        # Exception occurred
        self.exception = exc_val
        
        # Log with appropriate severity
        log_data = {
            **self.metadata,
            "duration": duration,
            "exception_type": exc_type.__name__,
            "exception_message": str(exc_val)
        }
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL: Operation '{self.operation}' failed", extra=log_data)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"Operation '{self.operation}' failed", extra=log_data)
        else:
            logger.warning(f"Operation '{self.operation}' failed", extra=log_data)
        
        # Attempt recovery if strategy provided
        if self.recovery_strategy and self.recovery_strategy.can_recover(exc_val):
            try:
                self.result = self.recovery_strategy.recover(exc_val, log_data)
                logger.info(f"Recovery successful for operation '{self.operation}'")
                return True  # Suppress exception
            except Exception as recovery_error:
                logger.error(
                    f"Recovery failed for operation '{self.operation}'",
                    extra={"recovery_error": str(recovery_error)}
                )
        
        return False  # Propagate exception
    
    def set_result(self, result: Any):
        """Store result for access after context exits."""
        self.result = result


# ============================================================================
# Helper Functions
# ============================================================================

def classify_error_severity(exception: Exception) -> ErrorSeverity:
    """Classify exception severity based on type and context.
    
    Args:
        exception: The exception to classify
    
    Returns:
        ErrorSeverity level
    """
    if isinstance(exception, (ConfigurationException, AuditLogException)):
        return ErrorSeverity.CRITICAL
    elif isinstance(exception, GovernanceException):
        return ErrorSeverity.HIGH
    elif isinstance(exception, CriticAPIException):
        return ErrorSeverity.MEDIUM
    elif isinstance(exception, (EmbeddingException, PrecedentException)):
        return ErrorSeverity.LOW
    else:
        return ErrorSeverity.MEDIUM


def should_escalate_to_human(exception: Exception) -> bool:
    """Determine if an error requires human escalation.
    
    Args:
        exception: The exception to evaluate
    
    Returns:
        True if human intervention is required
    """
    # Always escalate these critical errors
    if isinstance(exception, (HumanEscalationRequired, GovernanceException)):
        return True
    
    # Escalate high-severity errors
    severity = classify_error_severity(exception)
    if severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH):
        return True
    
    return False


def create_error_report(exception: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a comprehensive error report for logging and escalation.
    
    Args:
        exception: The exception to report
        context: Additional context information
    
    Returns:
        Dictionary containing error details
    """
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "exception_type": type(exception).__name__,
        "message": str(exception),
        "severity": classify_error_severity(exception).value,
        "requires_escalation": should_escalate_to_human(exception)
    }
    
    # Add EJE-specific exception details
    if isinstance(exception, EJEBaseException):
        report.update(exception.to_dict())
    
    # Add context if provided
    if context:
        report["context"] = context
    
    return report


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Exceptions
    'EJEBaseException',
    'CriticException',
    'CriticTimeoutException',
    'CriticAPIException',
    'PrecedentException',
    'EmbeddingException',
    'AuditLogException',
    'ConfigurationException',
    'GovernanceException',
    'HumanEscalationRequired',
    # Severity
    'ErrorSeverity',
    # Retry mechanism
    'RetryConfig',
    'retry_with_backoff',
    # Circuit breaker
    'CircuitState',
    'CircuitBreaker',
    # Recovery strategies
    'ErrorRecoveryStrategy',
    'GracefulDegradationStrategy',
    'FallbackCriticStrategy',
    # Context manager
    'ErrorContext',
    # Helper functions
    'classify_error_severity',
    'should_escalate_to_human',
    'create_error_report',
]
