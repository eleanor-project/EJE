"""Unit tests for Plugin Security Manager"""
import pytest
import time
from unittest.mock import Mock, patch
from src.eje.core.plugin_security import (
    PluginSecurityManager,
    TimeoutException,
    PluginErrorStats
)


class TestPluginSecurityManager:
    """Test suite for PluginSecurityManager"""

    def test_initialization(self):
        """Test security manager initialization"""
        manager = PluginSecurityManager(
            default_timeout=10.0,
            max_consecutive_failures=5,
            max_error_rate=60.0,
            blacklist_duration=600
        )
        assert manager.default_timeout == 10.0
        assert manager.max_consecutive_failures == 5
        assert manager.max_error_rate == 60.0
        assert manager.blacklist_duration == 600

    def test_validate_case_input_valid(self):
        """Test validation passes for valid case input"""
        manager = PluginSecurityManager()

        valid_case = {
            'text': 'This is a valid test case',
            'context': {'user_id': '123'},
            'metadata': {'source': 'test'}
        }

        # Should not raise exception
        manager.validate_case_input(valid_case)

    def test_validate_case_input_missing_text(self):
        """Test validation fails when text field is missing"""
        manager = PluginSecurityManager()

        invalid_case = {
            'context': {'user_id': '123'}
        }

        with pytest.raises(ValueError, match="must contain 'text' field"):
            manager.validate_case_input(invalid_case)

    def test_validate_case_input_malicious_patterns(self):
        """Test validation detects potentially malicious patterns"""
        manager = PluginSecurityManager()

        malicious_cases = [
            {'text': '__import__("os").system("rm -rf /")'},
            {'text': 'eval(malicious_code)'},
            {'text': 'exec(user_input)'},
            {'text': 'open("/etc/passwd").read()'},
            {'text': 'subprocess.call(["ls"])'},
        ]

        for case in malicious_cases:
            with pytest.raises(ValueError, match="Potentially malicious content"):
                manager.validate_case_input(case)

    def test_validate_case_input_text_too_long(self):
        """Test validation fails for excessively long text"""
        manager = PluginSecurityManager()

        # Create text longer than 100KB
        long_text = 'a' * 150000
        case = {'text': long_text}

        with pytest.raises(ValueError, match="Text too long"):
            manager.validate_case_input(case)

    def test_validate_case_input_invalid_type(self):
        """Test validation fails for non-dict input"""
        manager = PluginSecurityManager()

        with pytest.raises(ValueError, match="must be a dictionary"):
            manager.validate_case_input("not a dict")

    def test_validate_case_input_invalid_text_type(self):
        """Test validation fails when text is not string"""
        manager = PluginSecurityManager()

        case = {'text': 12345}

        with pytest.raises(ValueError, match="must be string"):
            manager.validate_case_input(case)

    def test_execute_with_timeout_success(self):
        """Test successful execution within timeout"""
        manager = PluginSecurityManager(default_timeout=2.0)

        def fast_function():
            return "success"

        result = manager.execute_with_timeout(
            func=fast_function,
            plugin_name="TestPlugin"
        )

        assert result == "success"
        stats = manager.get_plugin_stats("TestPlugin")
        assert stats.total_calls == 1
        assert stats.total_errors == 0
        assert stats.consecutive_failures == 0

    def test_execute_with_timeout_exceeds(self):
        """Test timeout exception when execution exceeds limit"""
        manager = PluginSecurityManager(default_timeout=0.5)

        def slow_function():
            time.sleep(2.0)
            return "should not reach"

        with pytest.raises(TimeoutException):
            manager.execute_with_timeout(
                func=slow_function,
                timeout=0.5,
                plugin_name="SlowPlugin"
            )

        stats = manager.get_plugin_stats("SlowPlugin")
        assert stats.total_calls == 1
        assert stats.total_errors == 1
        assert stats.total_timeouts == 1

    def test_execute_with_timeout_function_error(self):
        """Test error tracking when function raises exception"""
        manager = PluginSecurityManager()

        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            manager.execute_with_timeout(
                func=failing_function,
                plugin_name="FailingPlugin"
            )

        stats = manager.get_plugin_stats("FailingPlugin")
        assert stats.total_calls == 1
        assert stats.total_errors == 1
        assert stats.consecutive_failures == 1

    def test_blacklist_after_consecutive_failures(self):
        """Test plugin gets blacklisted after max consecutive failures"""
        manager = PluginSecurityManager(max_consecutive_failures=3)

        def failing_function():
            raise RuntimeError("Failure")

        # Execute 3 times to trigger blacklist
        for _ in range(3):
            try:
                manager.execute_with_timeout(
                    func=failing_function,
                    plugin_name="UnstablePlugin"
                )
            except RuntimeError:
                pass

        # Should be blacklisted now
        assert manager.is_blacklisted("UnstablePlugin")

        # Next call should fail immediately with blacklist error
        with pytest.raises(RuntimeError, match="blacklisted"):
            manager.execute_with_timeout(
                func=failing_function,
                plugin_name="UnstablePlugin"
            )

    def test_blacklist_expiration(self):
        """Test blacklist expires after duration"""
        manager = PluginSecurityManager(
            max_consecutive_failures=1,
            blacklist_duration=1  # 1 second
        )

        # Manually blacklist a plugin
        manager.blacklist_plugin("TestPlugin", "Test blacklist")
        assert manager.is_blacklisted("TestPlugin")

        # Wait for blacklist to expire
        time.sleep(1.5)

        # Should no longer be blacklisted
        assert not manager.is_blacklisted("TestPlugin")

    def test_error_rate_calculation(self):
        """Test error rate calculation"""
        stats = PluginErrorStats(plugin_name="TestPlugin")
        stats.total_calls = 10
        stats.total_errors = 3

        assert stats.error_rate == 30.0

    def test_error_rate_zero_calls(self):
        """Test error rate with zero calls"""
        stats = PluginErrorStats(plugin_name="TestPlugin")

        assert stats.error_rate == 0.0

    def test_is_failing_consistently(self):
        """Test detection of consistent failures"""
        stats = PluginErrorStats(plugin_name="TestPlugin")

        # Test consecutive failures threshold
        stats.consecutive_failures = 5
        assert stats.is_failing_consistently

        # Test error rate threshold
        stats.consecutive_failures = 0
        stats.total_calls = 10
        stats.total_errors = 6
        assert stats.is_failing_consistently

    def test_record_success_resets_consecutive_failures(self):
        """Test that recording success resets consecutive failures"""
        manager = PluginSecurityManager()

        # Record some failures
        for _ in range(2):
            manager.record_call("TestPlugin")
            manager.record_error("TestPlugin", RuntimeError("Fail"))

        stats = manager.get_plugin_stats("TestPlugin")
        assert stats.consecutive_failures == 2

        # Record success
        manager.record_call("TestPlugin")
        manager.record_success("TestPlugin")

        stats = manager.get_plugin_stats("TestPlugin")
        assert stats.consecutive_failures == 0

    def test_get_all_stats(self):
        """Test retrieving all plugin statistics"""
        manager = PluginSecurityManager()

        # Execute various plugins
        manager.record_call("Plugin1")
        manager.record_success("Plugin1")

        manager.record_call("Plugin2")
        manager.record_error("Plugin2", RuntimeError("Error"))

        all_stats = manager.get_all_stats()
        assert "Plugin1" in all_stats
        assert "Plugin2" in all_stats
        assert all_stats["Plugin1"].total_calls == 1
        assert all_stats["Plugin2"].total_errors == 1

    def test_get_blacklisted_plugins(self):
        """Test retrieving list of blacklisted plugins"""
        manager = PluginSecurityManager()

        manager.blacklist_plugin("Plugin1", "Too many failures")
        manager.blacklist_plugin("Plugin2", "High error rate")

        blacklisted = manager.get_blacklisted_plugins()
        assert "Plugin1" in blacklisted
        assert "Plugin2" in blacklisted
        assert len(blacklisted) == 2

    def test_timeout_context_manager(self):
        """Test timeout context manager"""
        manager = PluginSecurityManager()

        # Should complete within timeout
        with manager.timeout_context(1.0, "TestPlugin"):
            time.sleep(0.1)

        # Should raise TimeoutException
        with pytest.raises(TimeoutException):
            with manager.timeout_context(0.1, "TestPlugin"):
                time.sleep(0.5)

    def test_validate_context_field_type(self):
        """Test validation of context field type"""
        manager = PluginSecurityManager()

        # Valid context
        case = {'text': 'test', 'context': {'key': 'value'}}
        manager.validate_case_input(case)

        # Invalid context type
        case = {'text': 'test', 'context': 'not a dict'}
        with pytest.raises(ValueError, match="context.*must be dict"):
            manager.validate_case_input(case)

    def test_validate_metadata_field_type(self):
        """Test validation of metadata field type"""
        manager = PluginSecurityManager()

        # Valid metadata
        case = {'text': 'test', 'metadata': {'key': 'value'}}
        manager.validate_case_input(case)

        # Invalid metadata type
        case = {'text': 'test', 'metadata': 'not a dict'}
        with pytest.raises(ValueError, match="metadata.*must be dict"):
            manager.validate_case_input(case)

    def test_execute_with_kwargs(self):
        """Test execution with keyword arguments"""
        manager = PluginSecurityManager()

        def function_with_kwargs(a, b=10):
            return a + b

        result = manager.execute_with_timeout(
            func=function_with_kwargs,
            args=(5,),
            kwargs={'b': 20},
            plugin_name="TestPlugin"
        )

        assert result == 25

    def test_concurrent_executions(self):
        """Test handling of concurrent plugin executions"""
        import threading
        manager = PluginSecurityManager()

        def slow_function():
            time.sleep(0.1)
            return "done"

        # Execute multiple plugins concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(
                target=manager.execute_with_timeout,
                args=(slow_function,),
                kwargs={'plugin_name': f'Plugin{i}'}
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should have succeeded
        all_stats = manager.get_all_stats()
        assert len(all_stats) == 5
        for stats in all_stats.values():
            assert stats.total_calls == 1
            assert stats.total_errors == 0


class TestPluginErrorStats:
    """Test suite for PluginErrorStats dataclass"""

    def test_initial_state(self):
        """Test initial state of PluginErrorStats"""
        stats = PluginErrorStats(plugin_name="TestPlugin")

        assert stats.plugin_name == "TestPlugin"
        assert stats.total_calls == 0
        assert stats.total_errors == 0
        assert stats.total_timeouts == 0
        assert stats.last_error is None
        assert stats.last_error_time is None
        assert stats.consecutive_failures == 0

    def test_error_tracking(self):
        """Test error tracking functionality"""
        stats = PluginErrorStats(plugin_name="TestPlugin")

        stats.total_calls = 5
        stats.total_errors = 2
        stats.total_timeouts = 1
        stats.consecutive_failures = 1

        assert stats.error_rate == 40.0
        assert not stats.is_failing_consistently
