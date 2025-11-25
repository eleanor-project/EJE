"""
Unit Tests for Error Handling Module

Comprehensive test suite for the error_handling.py module, covering:
- Exception hierarchy and serialization
- Retry mechanisms with exponential backoff
- Circuit breaker pattern and state transitions
- Error recovery strategies
- Error context management
- Helper functions for severity classification and escalation

Author: Eleanor Project Contributors
Date: 2025-11-25
Version: 1.0.0
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the error handling module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ejc.core.error_handling import (
    # Exceptions
    EJEBaseException,
    CriticException,
    CriticTimeoutException,
    CriticAPIException,
    PrecedentException,
    EmbeddingException,
    AuditLogException,
    ConfigurationException,
    GovernanceException,
    HumanEscalationRequired,
    # Severity
    ErrorSeverity,
    # Retry mechanism
    RetryConfig,
    retry_with_backoff,
    # Circuit breaker
    CircuitState,
    CircuitBreaker,
    # Recovery strategies
    ErrorRecoveryStrategy,
    GracefulDegradationStrategy,
    FallbackCriticStrategy,
    # Context manager
    ErrorContext,
    # Helper functions
    classify_error_severity,
    should_escalate_to_human,
    create_error_report,
)


# ============================================================================
# Test Exception Hierarchy
# ============================================================================

class TestExceptionHierarchy:
    """Test custom exception classes and their behavior."""
    
    def test_base_exception_creation(self):
        """Test EJEBaseException instantiation and attributes."""
        exc = EJEBaseException(
            message="Test error",
            error_code="TEST_001",
            context={"key": "value"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_001"
        assert exc.context == {"key": "value"}
        assert isinstance(exc.timestamp, datetime)
    
    def test_base_exception_default_error_code(self):
        """Test that error_code defaults to class name."""
        exc = EJEBaseException("Test error")
        assert exc.error_code == "EJEBaseException"
    
    def test_base_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = EJEBaseException(
            message="Test error",
            error_code="TEST_001",
            context={"key": "value"}
        )
        
        exc_dict = exc.to_dict()
        
        assert exc_dict["error_type"] == "EJEBaseException"
        assert exc_dict["message"] == "Test error"
        assert exc_dict["error_code"] == "TEST_001"
        assert exc_dict["context"] == {"key": "value"}
        assert "timestamp" in exc_dict
    
    def test_critic_exception_inheritance(self):
        """Test that CriticException inherits from EJEBaseException."""
        exc = CriticException("Critic failed")
        assert isinstance(exc, EJEBaseException)
        assert isinstance(exc, CriticException)
    
    def test_specialized_exceptions(self):
        """Test all specialized exception types."""
        exceptions = [
            CriticTimeoutException("Timeout"),
            CriticAPIException("API failure"),
            PrecedentException("Precedent error"),
            EmbeddingException("Embedding failed"),
            AuditLogException("Log error"),
            ConfigurationException("Config invalid"),
            GovernanceException("Rule violated"),
            HumanEscalationRequired("Human needed")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, EJEBaseException)
            assert exc.error_code == exc.__class__.__name__


# ============================================================================
# Test Retry Mechanism
# ============================================================================

class TestRetryMechanism:
    """Test retry with exponential backoff."""
    
    def test_retry_config_defaults(self):
        """Test default RetryConfig values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_retry_config_custom(self):
        """Test custom RetryConfig values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
    
    def test_retry_success_on_first_attempt(self):
        """Test that successful function doesn't retry."""
        call_count = 0
        
        @retry_with_backoff()
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test retry mechanism with eventual success."""
        call_count = 0
        
        @retry_with_backoff(
            exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, base_delay=0.1)
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not ready yet")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_max_attempts_exceeded(self):
        """Test that function fails after max attempts."""
        call_count = 0
        
        @retry_with_backoff(
            exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, base_delay=0.1)
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count == 3
    
    def test_retry_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff."""
        call_times = []
        
        @retry_with_backoff(
            exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, base_delay=0.5, jitter=False)
        )
        def timed_function():
            call_times.append(time.time())
            raise ValueError("Fail")
        
        with pytest.raises(ValueError):
            timed_function()
        
        # Check that delays increase (approximately 0.5s, 1.0s)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        assert 0.4 < delay1 < 0.6  # ~0.5s
        assert 0.9 < delay2 < 1.1  # ~1.0s
    
    def test_retry_callback(self):
        """Test retry callback is invoked."""
        callback_calls = []
        
        def on_retry(attempt, exception, delay):
            callback_calls.append((attempt, str(exception), delay))
        
        @retry_with_backoff(
            exceptions=(ValueError,),
            config=RetryConfig(max_attempts=3, base_delay=0.1),
            on_retry=on_retry
        )
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
        
        assert len(callback_calls) == 2  # Called on retries, not final failure
        assert callback_calls[0][0] == 1
        assert callback_calls[1][0] == 2


# ============================================================================
# Test Circuit Breaker
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        
        def failing_function():
            raise ValueError("Fail")
        
        # Cause failures up to threshold
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_function)
        
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_breaker_blocks_when_open(self):
        """Test that circuit breaker blocks calls when OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        
        def failing_function():
            raise ValueError("Fail")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_function)
        
        # Next call should be blocked
        with pytest.raises(CriticException) as exc_info:
            cb.call(failing_function)
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
        
        def failing_function():
            raise ValueError("Fail")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_function)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.6)
        
        # Check state transitions to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_after_success(self):
        """Test circuit closes after successful call in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
        
        call_count = 0
        
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Fail")
            return "success"
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(sometimes_fails)
        
        # Wait for recovery
        time.sleep(0.6)
        
        # Successful call should close circuit
        result = cb.call(sometimes_fails)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED


# ============================================================================
# Test Error Recovery Strategies
# ============================================================================

class TestErrorRecoveryStrategies:
    """Test error recovery strategy implementations."""
    
    def test_graceful_degradation_can_recover(self):
        """Test graceful degradation strategy recovery capability."""
        strategy = GracefulDegradationStrategy(fallback_value="fallback")
        
        assert strategy.can_recover(CriticException("fail"))
        assert strategy.can_recover(PrecedentException("fail"))
        assert not strategy.can_recover(ValueError("fail"))
    
    def test_graceful_degradation_recovery(self):
        """Test graceful degradation returns fallback value."""
        strategy = GracefulDegradationStrategy(fallback_value="fallback")
        
        result = strategy.recover(
            CriticException("fail"),
            context={"test": "context"}
        )
        
        assert result == "fallback"
    
    def test_fallback_critic_strategy_can_recover(self):
        """Test fallback critic strategy recovery capability."""
        strategy = FallbackCriticStrategy(fallback_critics=["critic2", "critic3"])
        
        assert strategy.can_recover(CriticException("fail"))
        assert not strategy.can_recover(AuditLogException("fail"))


# ============================================================================
# Test Error Context Manager
# ============================================================================

class TestErrorContext:
    """Test error context manager functionality."""
    
    def test_error_context_success(self):
        """Test context manager with successful operation."""
        with ErrorContext(operation="test_op") as ctx:
            ctx.set_result("success")
        
        assert ctx.result == "success"
        assert ctx.exception is None
    
    def test_error_context_captures_exception(self):
        """Test context manager captures exceptions."""
        with pytest.raises(ValueError):
            with ErrorContext(operation="test_op") as ctx:
                raise ValueError("Test error")
        
        assert ctx.exception is not None
        assert isinstance(ctx.exception, ValueError)
    
    def test_error_context_with_recovery(self):
        """Test context manager with recovery strategy."""
        strategy = GracefulDegradationStrategy(fallback_value="recovered")
        
        with ErrorContext(
            operation="test_op",
            recovery_strategy=strategy
        ) as ctx:
            raise CriticException("Recoverable error")
        
        assert ctx.result == "recovered"
    
    def test_error_context_tracks_duration(self):
        """Test that context manager tracks operation duration."""
        with ErrorContext(operation="test_op") as ctx:
            time.sleep(0.1)
            ctx.set_result("done")
        
        # Duration should be tracked (approximate)
        assert ctx.start_time is not None


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Test utility functions for error handling."""
    
    def test_classify_error_severity_critical(self):
        """Test severity classification for critical errors."""
        exc = ConfigurationException("Config error")
        assert classify_error_severity(exc) == ErrorSeverity.CRITICAL
        
        exc = AuditLogException("Audit error")
        assert classify_error_severity(exc) == ErrorSeverity.CRITICAL
    
    def test_classify_error_severity_high(self):
        """Test severity classification for high severity errors."""
        exc = GovernanceException("Rule violation")
        assert classify_error_severity(exc) == ErrorSeverity.HIGH
    
    def test_classify_error_severity_medium(self):
        """Test severity classification for medium severity errors."""
        exc = CriticAPIException("API failure")
        assert classify_error_severity(exc) == ErrorSeverity.MEDIUM
    
    def test_classify_error_severity_low(self):
        """Test severity classification for low severity errors."""
        exc = EmbeddingException("Embedding error")
        assert classify_error_severity(exc) == ErrorSeverity.LOW
        
        exc = PrecedentException("Precedent error")
        assert classify_error_severity(exc) == ErrorSeverity.LOW
    
    def test_should_escalate_to_human_true(self):
        """Test escalation logic for errors requiring human review."""
        assert should_escalate_to_human(HumanEscalationRequired("Manual review"))
        assert should_escalate_to_human(GovernanceException("Rule violated"))
        assert should_escalate_to_human(ConfigurationException("Config error"))
    
    def test_should_escalate_to_human_false(self):
        """Test escalation logic for errors not requiring human review."""
        assert not should_escalate_to_human(EmbeddingException("Embedding fail"))
        assert not should_escalate_to_human(CriticAPIException("API fail"))
    
    def test_create_error_report_basic(self):
        """Test error report creation with basic exception."""
        exc = ValueError("Test error")
        report = create_error_report(exc)
        
        assert "timestamp" in report
        assert report["exception_type"] == "ValueError"
        assert report["message"] == "Test error"
        assert "severity" in report
        assert "requires_escalation" in report
    
    def test_create_error_report_with_eje_exception(self):
        """Test error report with EJE custom exception."""
        exc = CriticException(
            message="Critic failed",
            error_code="CRIT_001",
            context={"key": "value"}
        )
        report = create_error_report(exc, context={"extra": "info"})
        
        assert report["exception_type"] == "CriticException"
        assert report["error_code"] == "CRIT_001"
        assert "context" in report
        assert report["context"]["extra"] == "info"
    
    def test_create_error_report_severity(self):
        """Test error report includes correct severity."""
        exc = GovernanceException("Rule violated")
        report = create_error_report(exc)
        
        assert report["severity"] == "high"
        assert report["requires_escalation"] is True


# ============================================================================
# Integration Tests
# ============================================================================

class TestErrorHandlingIntegration:
    """Integration tests combining multiple error handling components."""
    
    def test_retry_with_circuit_breaker(self):
        """Test combining retry mechanism with circuit breaker."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        call_count = 0
        
        @retry_with_backoff(
            exceptions=(CriticAPIException,),
            config=RetryConfig(max_attempts=2, base_delay=0.1)
        )
        def api_call():
            nonlocal call_count
            call_count += 1
            def inner():
                raise CriticAPIException("API failed")
            return cb.call(inner)
        
        # Should attempt retries and eventually open circuit
        with pytest.raises(CriticAPIException):
            api_call()
        
        assert call_count == 2  # Retried
    
    def test_error_context_with_severity_classification(self):
        """Test error context integrates with severity classification."""
        with pytest.raises(GovernanceException) as exc_info:
            with ErrorContext(
                operation="governance_check",
                severity=ErrorSeverity.HIGH
            ):
                raise GovernanceException("Rule violation")
        
        exc = exc_info.value
        severity = classify_error_severity(exc)
        assert severity == ErrorSeverity.HIGH
        assert should_escalate_to_human(exc)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
