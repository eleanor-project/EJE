"""
Plugin security and fault-tolerance module for EJE.
Handles timeouts, input validation, blacklisting, and error tracking.
"""
import signal
import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable, List, Set
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading


@dataclass
class PluginErrorStats:
    """Track error statistics for a plugin."""
    plugin_name: str
    total_calls: int = 0
    total_errors: int = 0
    total_timeouts: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def error_rate(self) -> float:
        """Calculate error rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.total_errors / self.total_calls) * 100

    @property
    def is_failing_consistently(self) -> bool:
        """Check if plugin is failing consistently."""
        return self.consecutive_failures >= 3 or self.error_rate > 50


class TimeoutException(Exception):
    """Raised when a plugin execution exceeds timeout."""
    pass


class PluginSecurityManager:
    """
    Manages security and fault-tolerance for critic plugins.

    Features:
    - Per-critic timeouts with thread-based enforcement
    - Input validation and sanitization
    - Plugin blacklisting based on failure rate
    - Error tracking and statistics
    - Automatic plugin disabling for consistent failures
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        max_consecutive_failures: int = 3,
        max_error_rate: float = 50.0,
        blacklist_duration: int = 300  # seconds
    ):
        """
        Initialize plugin security manager.

        Args:
            default_timeout: Default timeout for critic evaluation (seconds)
            max_consecutive_failures: Max failures before blacklisting
            max_error_rate: Max error rate (%) before blacklisting
            blacklist_duration: How long to blacklist failing plugins (seconds)
        """
        self.default_timeout = default_timeout
        self.max_consecutive_failures = max_consecutive_failures
        self.max_error_rate = max_error_rate
        self.blacklist_duration = blacklist_duration

        # Error tracking
        self.plugin_stats: Dict[str, PluginErrorStats] = {}

        # Blacklist tracking
        self.blacklisted_plugins: Dict[str, datetime] = {}

        # Thread-local storage for timeout handling
        self._local = threading.local()

    def validate_case_input(self, case: Dict[str, Any]) -> None:
        """
        Validate and sanitize case input before passing to plugins.

        Args:
            case: The case dictionary to validate

        Raises:
            ValueError: If case input is invalid or potentially malicious
        """
        # Type checking
        if not isinstance(case, dict):
            raise ValueError(f"Case must be a dictionary, got {type(case)}")

        # Required fields
        if 'text' not in case:
            raise ValueError("Case must contain 'text' field")

        # Sanitize text field
        text = case.get('text', '')
        if not isinstance(text, str):
            raise ValueError(f"Case 'text' must be string, got {type(text)}")

        # Check for code injection patterns (basic sanitization)
        dangerous_patterns = [
            '__import__', 'eval(', 'exec(',
            'compile(', 'open(', 'file(',
            'subprocess', 'os.system', 'commands.',
            '__builtins__', '__globals__', '__locals__'
        ]

        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in text_lower:
                raise ValueError(
                    f"Potentially malicious content detected: '{pattern}' "
                    f"found in input. This pattern is blocked for security."
                )

        # Length validation (prevent DoS)
        max_text_length = 100_000  # 100KB
        if len(text) > max_text_length:
            raise ValueError(
                f"Text too long: {len(text)} chars. Max: {max_text_length}"
            )

        # Validate optional fields
        if 'context' in case and case['context'] is not None:
            if not isinstance(case['context'], dict):
                raise ValueError("Case 'context' must be dict or None")

        if 'metadata' in case and case['metadata'] is not None:
            if not isinstance(case['metadata'], dict):
                raise ValueError("Case 'metadata' must be dict or None")

    def is_blacklisted(self, plugin_name: str) -> bool:
        """
        Check if a plugin is currently blacklisted.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is blacklisted, False otherwise
        """
        if plugin_name not in self.blacklisted_plugins:
            return False

        # Check if blacklist has expired
        blacklist_time = self.blacklisted_plugins[plugin_name]
        if datetime.now() - blacklist_time > timedelta(seconds=self.blacklist_duration):
            # Blacklist expired, remove it
            del self.blacklisted_plugins[plugin_name]
            # Reset consecutive failures
            if plugin_name in self.plugin_stats:
                self.plugin_stats[plugin_name].consecutive_failures = 0
            return False

        return True

    def blacklist_plugin(self, plugin_name: str, reason: str) -> None:
        """
        Add a plugin to the blacklist.

        Args:
            plugin_name: Name of the plugin to blacklist
            reason: Reason for blacklisting
        """
        self.blacklisted_plugins[plugin_name] = datetime.now()
        if plugin_name in self.plugin_stats:
            self.plugin_stats[plugin_name].last_error = f"Blacklisted: {reason}"
            self.plugin_stats[plugin_name].last_error_time = datetime.now()

    def record_call(self, plugin_name: str) -> None:
        """Record a plugin call attempt."""
        if plugin_name not in self.plugin_stats:
            self.plugin_stats[plugin_name] = PluginErrorStats(plugin_name=plugin_name)
        self.plugin_stats[plugin_name].total_calls += 1

    def record_success(self, plugin_name: str) -> None:
        """Record a successful plugin call."""
        if plugin_name in self.plugin_stats:
            self.plugin_stats[plugin_name].consecutive_failures = 0

    def record_error(
        self,
        plugin_name: str,
        error: Exception,
        is_timeout: bool = False
    ) -> None:
        """
        Record a plugin error and update statistics.

        Args:
            plugin_name: Name of the plugin that failed
            error: The exception that occurred
            is_timeout: Whether this was a timeout error
        """
        if plugin_name not in self.plugin_stats:
            self.plugin_stats[plugin_name] = PluginErrorStats(plugin_name=plugin_name)

        stats = self.plugin_stats[plugin_name]
        stats.total_errors += 1
        stats.consecutive_failures += 1
        stats.last_error = str(error)
        stats.last_error_time = datetime.now()

        if is_timeout:
            stats.total_timeouts += 1

        # Check if plugin should be blacklisted
        if stats.is_failing_consistently:
            self.blacklist_plugin(
                plugin_name,
                f"High failure rate: {stats.error_rate:.1f}% "
                f"({stats.consecutive_failures} consecutive failures)"
            )

    def get_plugin_stats(self, plugin_name: str) -> Optional[PluginErrorStats]:
        """Get error statistics for a plugin."""
        return self.plugin_stats.get(plugin_name)

    def get_all_stats(self) -> Dict[str, PluginErrorStats]:
        """Get error statistics for all plugins."""
        return self.plugin_stats.copy()

    def get_blacklisted_plugins(self) -> List[str]:
        """Get list of currently blacklisted plugins."""
        # Clean up expired blacklists first
        current_time = datetime.now()
        expired = [
            name for name, blacklist_time in self.blacklisted_plugins.items()
            if current_time - blacklist_time > timedelta(seconds=self.blacklist_duration)
        ]
        for name in expired:
            del self.blacklisted_plugins[name]

        return list(self.blacklisted_plugins.keys())

    @contextmanager
    def timeout_context(self, seconds: float, plugin_name: str):
        """
        Context manager for enforcing timeouts using threading.

        Args:
            seconds: Timeout duration in seconds
            plugin_name: Name of the plugin being executed

        Raises:
            TimeoutException: If execution exceeds timeout

        Example:
            with security_manager.timeout_context(30.0, "MyPlugin"):
                result = plugin.evaluate(case)
        """
        def timeout_handler():
            self._local.timed_out = True

        # Set up timer
        timer = threading.Timer(seconds, timeout_handler)
        self._local.timed_out = False

        try:
            timer.start()
            yield
            if self._local.timed_out:
                raise TimeoutException(
                    f"Plugin '{plugin_name}' exceeded timeout of {seconds}s"
                )
        finally:
            timer.cancel()

    def execute_with_timeout(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        timeout: Optional[float] = None,
        plugin_name: str = "Unknown"
    ) -> Any:
        """
        Execute a function with timeout protection.

        Args:
            func: Function to execute
            args: Positional arguments for function
            kwargs: Keyword arguments for function
            timeout: Timeout in seconds (uses default if None)
            plugin_name: Name of the plugin for tracking

        Returns:
            Result of function execution

        Raises:
            TimeoutException: If execution exceeds timeout
            Exception: Any exception raised by the function
        """
        if kwargs is None:
            kwargs = {}

        timeout_value = timeout or self.default_timeout

        # Check if plugin is blacklisted
        if self.is_blacklisted(plugin_name):
            raise RuntimeError(
                f"Plugin '{plugin_name}' is blacklisted due to "
                f"consistent failures. Will retry after "
                f"{self.blacklist_duration} seconds."
            )

        # Record the call attempt
        self.record_call(plugin_name)

        try:
            with self.timeout_context(timeout_value, plugin_name):
                result = func(*args, **kwargs)
                self.record_success(plugin_name)
                return result
        except TimeoutException as e:
            self.record_error(plugin_name, e, is_timeout=True)
            raise
        except Exception as e:
            self.record_error(plugin_name, e, is_timeout=False)
            raise


# Global singleton instance
_global_security_manager: Optional[PluginSecurityManager] = None


def get_security_manager(
    default_timeout: float = 30.0,
    max_consecutive_failures: int = 3,
    max_error_rate: float = 50.0,
    blacklist_duration: int = 300
) -> PluginSecurityManager:
    """
    Get or create global plugin security manager instance.

    Args:
        default_timeout: Default timeout for critic evaluation (seconds)
        max_consecutive_failures: Max failures before blacklisting
        max_error_rate: Max error rate (%) before blacklisting
        blacklist_duration: How long to blacklist failing plugins (seconds)

    Returns:
        PluginSecurityManager instance
    """
    global _global_security_manager
    if _global_security_manager is None:
        _global_security_manager = PluginSecurityManager(
            default_timeout=default_timeout,
            max_consecutive_failures=max_consecutive_failures,
            max_error_rate=max_error_rate,
            blacklist_duration=blacklist_duration
        )
    return _global_security_manager
