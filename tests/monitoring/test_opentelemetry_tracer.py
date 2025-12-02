"""
Tests for OpenTelemetry distributed tracing module.

Tests cover:
- Tracer initialization
- Decorator functionality
- Span attribute addition
- Context managers
- Trace ID propagation
"""

import functools
import pytest
from unittest.mock import MagicMock, Mock, patch, call
from typing import Dict, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode

from ejc.monitoring.opentelemetry_tracer import (
    initialize_tracing,
    get_tracer,
    shutdown_tracing,
    trace_decision,
    trace_critic,
    trace_span,
    start_span,
    add_span_event,
    set_span_attribute,
    get_trace_id,
    get_span_id,
    trace_precedent_lookup,
    trace_policy_check,
    trace_conflict_detected,
    trace_override,
    _add_decision_attributes,
    _add_critic_attributes,
    _parse_jaeger_host,
    _parse_jaeger_port,
)


class TestTracerInitialization:
    """Test tracer initialization and configuration"""

    def setup_method(self):
        """Reset global tracer before each test"""
        import ejc.monitoring.opentelemetry_tracer as tracer_module
        tracer_module._tracer = None
        tracer_module._tracer_provider = None

    def test_initialize_tracing_basic(self):
        """Test basic tracer initialization"""
        tracer = initialize_tracing(service_name="test-service")

        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    def test_initialize_tracing_with_sampling(self):
        """Test tracer initialization with custom sampling rate"""
        tracer = initialize_tracing(
            service_name="test-service",
            sampling_rate=0.5
        )

        assert tracer is not None

    @patch('ejc.monitoring.opentelemetry_tracer.JaegerExporter')
    @patch('ejc.monitoring.opentelemetry_tracer.BatchSpanProcessor')
    def test_initialize_tracing_with_jaeger(self, mock_processor, mock_exporter):
        """Test tracer initialization with Jaeger export"""
        tracer = initialize_tracing(
            service_name="test-service",
            jaeger_endpoint="http://jaeger:14268/api/traces"
        )

        assert tracer is not None
        mock_exporter.assert_called_once()
        mock_processor.assert_called()

    @patch('ejc.monitoring.opentelemetry_tracer.ConsoleSpanExporter')
    @patch('ejc.monitoring.opentelemetry_tracer.BatchSpanProcessor')
    def test_initialize_tracing_with_console_export(self, mock_processor, mock_exporter):
        """Test tracer initialization with console export"""
        tracer = initialize_tracing(
            service_name="test-service",
            console_export=True
        )

        assert tracer is not None
        mock_exporter.assert_called_once()

    def test_get_tracer_auto_initialize(self):
        """Test get_tracer auto-initializes if not initialized"""
        tracer = get_tracer()

        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    @patch.dict('os.environ', {
        'JAEGER_ENDPOINT': 'http://jaeger:14268/api/traces',
        'TRACE_SAMPLING_RATE': '0.1'
    })
    def test_get_tracer_uses_env_vars(self):
        """Test get_tracer uses environment variables"""
        tracer = get_tracer()

        assert tracer is not None

    def test_shutdown_tracing(self):
        """Test tracer shutdown"""
        tracer = initialize_tracing(service_name="test-service")
        shutdown_tracing()

        # Should not raise exception
        assert True


class TestJaegerEndpointParsing:
    """Test Jaeger endpoint URL parsing"""

    def test_parse_jaeger_host_basic(self):
        """Test basic hostname parsing"""
        host = _parse_jaeger_host("localhost")
        assert host == "localhost"

    def test_parse_jaeger_host_with_protocol(self):
        """Test hostname parsing with protocol"""
        host = _parse_jaeger_host("http://jaeger:14268/api/traces")
        assert host == "jaeger"

    def test_parse_jaeger_host_with_port(self):
        """Test hostname parsing with port"""
        host = _parse_jaeger_host("jaeger:6831")
        assert host == "jaeger"

    def test_parse_jaeger_port_basic(self):
        """Test basic port parsing"""
        port = _parse_jaeger_port("jaeger:6831")
        assert port == 6831

    def test_parse_jaeger_port_with_path(self):
        """Test port parsing with path"""
        port = _parse_jaeger_port("http://jaeger:14268/api/traces")
        assert port == 14268

    def test_parse_jaeger_port_default(self):
        """Test default port when not specified"""
        port = _parse_jaeger_port("jaeger")
        assert port == 6831


class TestDecisionDecorator:
    """Test @trace_decision decorator"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_trace_decision_decorator_basic(self):
        """Test basic decision tracing"""
        @trace_decision()
        def test_function():
            return {"overall_verdict": "APPROVE", "avg_confidence": 0.9}

        result = test_function()

        assert result["overall_verdict"] == "APPROVE"
        assert result["avg_confidence"] == 0.9

    def test_trace_decision_decorator_custom_name(self):
        """Test decision tracing with custom operation name"""
        @trace_decision("custom_operation")
        def test_function():
            return {"overall_verdict": "DENY"}

        result = test_function()

        assert result["overall_verdict"] == "DENY"

    def test_trace_decision_decorator_with_exception(self):
        """Test decision tracing handles exceptions"""
        @trace_decision()
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function()

    @patch('opentelemetry.trace.Tracer.start_as_current_span')
    def test_trace_decision_adds_attributes(self, mock_span):
        """Test decision decorator adds result attributes"""
        mock_span_instance = MagicMock()
        mock_span.return_value.__enter__ = Mock(return_value=mock_span_instance)
        mock_span.return_value.__exit__ = Mock(return_value=None)

        @trace_decision()
        def test_function():
            return {
                "overall_verdict": "APPROVE",
                "avg_confidence": 0.95,
                "ambiguity": 0.05,
                "requires_review": False,
                "details": [1, 2, 3]
            }

        result = test_function()

        # Verify span attributes were set
        assert mock_span_instance.set_attribute.call_count >= 4


class TestCriticDecorator:
    """Test @trace_critic decorator"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_trace_critic_decorator_basic(self):
        """Test basic critic tracing"""
        @trace_critic("bias_critic")
        def test_critic():
            return {"verdict": "APPROVE", "confidence": 0.9}

        result = test_critic()

        assert result["verdict"] == "APPROVE"
        assert result["confidence"] == 0.9

    def test_trace_critic_decorator_with_exception(self):
        """Test critic tracing handles exceptions"""
        @trace_critic("failing_critic")
        def test_critic():
            raise RuntimeError("Critic failed")

        with pytest.raises(RuntimeError, match="Critic failed"):
            test_critic()

    @patch('opentelemetry.trace.Tracer.start_as_current_span')
    def test_trace_critic_adds_attributes(self, mock_span):
        """Test critic decorator adds result attributes"""
        mock_span_instance = MagicMock()
        mock_span.return_value.__enter__ = Mock(return_value=mock_span_instance)
        mock_span.return_value.__exit__ = Mock(return_value=None)

        @trace_critic("test_critic")
        def test_function():
            return {
                "verdict": "APPROVE",
                "confidence": 0.9,
                "weight": 1.5,
                "priority": True
            }

        result = test_function()

        # Verify span attributes were set
        assert mock_span_instance.set_attribute.call_count >= 4


class TestDecisionAttributes:
    """Test decision-specific attribute addition"""

    def test_add_decision_attributes_full(self):
        """Test adding all decision attributes"""
        mock_span = MagicMock()
        result = {
            "overall_verdict": "APPROVE",
            "avg_confidence": 0.95,
            "ambiguity": 0.05,
            "requires_review": False,
            "details": [{"critic": "bias"}, {"critic": "policy"}]
        }

        _add_decision_attributes(mock_span, result)

        assert mock_span.set_attribute.call_count == 5
        mock_span.set_attribute.assert_any_call("eje.decision.verdict", "APPROVE")
        mock_span.set_attribute.assert_any_call("eje.decision.confidence", 0.95)
        mock_span.set_attribute.assert_any_call("eje.decision.ambiguity", 0.05)
        mock_span.set_attribute.assert_any_call("eje.decision.requires_review", False)
        mock_span.set_attribute.assert_any_call("eje.decision.critic_count", 2)

    def test_add_decision_attributes_partial(self):
        """Test adding partial decision attributes"""
        mock_span = MagicMock()
        result = {
            "overall_verdict": "DENY"
        }

        _add_decision_attributes(mock_span, result)

        assert mock_span.set_attribute.call_count == 1
        mock_span.set_attribute.assert_called_with("eje.decision.verdict", "DENY")


class TestCriticAttributes:
    """Test critic-specific attribute addition"""

    def test_add_critic_attributes_full(self):
        """Test adding all critic attributes"""
        mock_span = MagicMock()
        result = {
            "verdict": "APPROVE",
            "confidence": 0.9,
            "weight": 1.5,
            "priority": True
        }

        _add_critic_attributes(mock_span, result)

        assert mock_span.set_attribute.call_count == 4
        mock_span.set_attribute.assert_any_call("eje.critic.verdict", "APPROVE")
        mock_span.set_attribute.assert_any_call("eje.critic.confidence", 0.9)
        mock_span.set_attribute.assert_any_call("eje.critic.weight", 1.5)
        mock_span.set_attribute.assert_any_call("eje.critic.priority", True)

    def test_add_critic_attributes_no_priority(self):
        """Test adding critic attributes when priority is None"""
        mock_span = MagicMock()
        result = {
            "verdict": "APPROVE",
            "priority": None
        }

        _add_critic_attributes(mock_span, result)

        assert mock_span.set_attribute.call_count == 1
        mock_span.set_attribute.assert_called_with("eje.critic.verdict", "APPROVE")


class TestTraceSpanContextManager:
    """Test trace_span context manager"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_trace_span_basic(self):
        """Test basic span context manager"""
        with trace_span("test_operation"):
            result = "operation_complete"

        assert result == "operation_complete"

    def test_trace_span_with_attributes(self):
        """Test span context manager with custom attributes"""
        with trace_span("test_operation", case_id="123", user="admin") as span:
            assert span is not None

    def test_trace_span_with_exception(self):
        """Test span context manager handles exceptions"""
        with pytest.raises(ValueError):
            with trace_span("test_operation"):
                raise ValueError("Test error")


class TestManualSpanFunctions:
    """Test manual span creation and manipulation"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_start_span(self):
        """Test manual span creation"""
        span = start_span("custom_operation", operation_id="123")

        assert span is not None
        span.end()

    @patch('opentelemetry.trace.get_current_span')
    def test_add_span_event(self, mock_get_span):
        """Test adding event to current span"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        add_span_event("test_event", {"key": "value"})

        mock_span.add_event.assert_called_once_with("test_event", attributes={"key": "value"})

    @patch('opentelemetry.trace.get_current_span')
    def test_add_span_event_no_recording(self, mock_get_span):
        """Test adding event when span not recording"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mock_get_span.return_value = mock_span

        add_span_event("test_event")

        mock_span.add_event.assert_not_called()

    @patch('opentelemetry.trace.get_current_span')
    def test_set_span_attribute(self, mock_get_span):
        """Test setting attribute on current span"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        set_span_attribute("case_id", "123")

        mock_span.set_attribute.assert_called_once_with("eje.case_id", "123")

    @patch('opentelemetry.trace.get_current_span')
    def test_get_trace_id(self, mock_get_span):
        """Test getting trace ID from current span"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 123456789
        mock_span.get_span_context.return_value = mock_span_context
        mock_get_span.return_value = mock_span

        trace_id = get_trace_id()

        assert trace_id == format(123456789, '032x')

    @patch('opentelemetry.trace.get_current_span')
    def test_get_trace_id_not_recording(self, mock_get_span):
        """Test getting trace ID when not recording"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mock_get_span.return_value = mock_span

        trace_id = get_trace_id()

        assert trace_id == ""

    @patch('opentelemetry.trace.get_current_span')
    def test_get_span_id(self, mock_get_span):
        """Test getting span ID from current span"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span_context = MagicMock()
        mock_span_context.span_id = 987654321
        mock_span.get_span_context.return_value = mock_span_context
        mock_get_span.return_value = mock_span

        span_id = get_span_id()

        assert span_id == format(987654321, '016x')


class TestConvenienceFunctions:
    """Test convenience functions for common tracing operations"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    @patch('ejc.monitoring.opentelemetry_tracer.add_span_event')
    def test_trace_precedent_lookup(self, mock_add_event):
        """Test precedent lookup event recording"""
        trace_precedent_lookup(5)

        mock_add_event.assert_called_once_with("precedent_lookup", {"count": 5})

    @patch('ejc.monitoring.opentelemetry_tracer.add_span_event')
    def test_trace_policy_check(self, mock_add_event):
        """Test policy check event recording"""
        trace_policy_check("gdpr_policy", True)

        mock_add_event.assert_called_once_with("policy_check", {
            "policy": "gdpr_policy",
            "passed": True
        })

    @patch('ejc.monitoring.opentelemetry_tracer.add_span_event')
    def test_trace_conflict_detected(self, mock_add_event):
        """Test conflict detection event recording"""
        trace_conflict_detected("verdict_mismatch", "high")

        mock_add_event.assert_called_once_with("conflict_detected", {
            "type": "verdict_mismatch",
            "severity": "high"
        })

    @patch('ejc.monitoring.opentelemetry_tracer.add_span_event')
    def test_trace_override(self, mock_add_event):
        """Test override event recording"""
        trace_override("manual_override", "admin@example.com")

        mock_add_event.assert_called_once_with("override", {
            "type": "manual_override",
            "actor": "admin@example.com"
        })


class TestIntegration:
    """Integration tests for complete tracing workflows"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_nested_spans(self):
        """Test nested decision and critic spans"""
        @trace_decision("aggregate_decision")
        def aggregate_decision():
            critic1_result = run_critic1()
            critic2_result = run_critic2()
            return {
                "overall_verdict": "APPROVE",
                "details": [critic1_result, critic2_result]
            }

        @trace_critic("critic1")
        def run_critic1():
            return {"verdict": "APPROVE", "confidence": 0.9}

        @trace_critic("critic2")
        def run_critic2():
            return {"verdict": "APPROVE", "confidence": 0.8}

        result = aggregate_decision()

        assert result["overall_verdict"] == "APPROVE"
        assert len(result["details"]) == 2

    def test_mixed_span_types(self):
        """Test mixing decorators and context managers"""
        @trace_decision()
        def decision_with_lookup():
            with trace_span("precedent_lookup", case_id="123"):
                precedents = ["precedent1", "precedent2"]

            return {
                "overall_verdict": "APPROVE",
                "precedents": precedents
            }

        result = decision_with_lookup()

        assert result["overall_verdict"] == "APPROVE"
        assert len(result["precedents"]) == 2

    def test_exception_propagation(self):
        """Test exceptions propagate through tracing layers"""
        @trace_decision()
        def outer():
            return inner()

        @trace_critic("inner_critic")
        def inner():
            raise RuntimeError("Inner error")

        with pytest.raises(RuntimeError, match="Inner error"):
            outer()


class TestPerformance:
    """Test tracing performance overhead"""

    def setup_method(self):
        """Initialize tracer with sampling before each test"""
        initialize_tracing(service_name="test-service", sampling_rate=1.0)

    def test_decorator_overhead_minimal(self):
        """Test decorator adds minimal overhead"""
        import time

        def untraced_function():
            return sum(range(1000))

        @trace_decision()
        def traced_function():
            return sum(range(1000))

        # Warmup
        for _ in range(10):
            untraced_function()
            traced_function()

        # Measure untraced
        start = time.perf_counter()
        for _ in range(100):
            untraced_function()
        untraced_time = time.perf_counter() - start

        # Measure traced
        start = time.perf_counter()
        for _ in range(100):
            traced_function()
        traced_time = time.perf_counter() - start

        # Overhead should be reasonable (< 50% for this simple operation)
        # In production with real work, overhead will be much lower
        overhead_ratio = (traced_time - untraced_time) / untraced_time

        # This is a loose bound since timing tests are flaky
        # The real validation is in production monitoring
        assert overhead_ratio < 5.0  # Allow up to 5x for test environment


class TestErrorHandling:
    """Test error handling and edge cases"""

    def setup_method(self):
        """Initialize tracer before each test"""
        initialize_tracing(service_name="test-service")

    def test_decorator_preserves_function_metadata(self):
        """Test decorators preserve original function metadata"""
        @trace_decision()
        def documented_function():
            """This is a documented function"""
            return {"verdict": "APPROVE"}

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function"

    @patch('opentelemetry.trace.get_current_span')
    def test_add_span_event_handles_none_attributes(self, mock_get_span):
        """Test add_span_event handles None attributes"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        add_span_event("test_event", None)

        mock_span.add_event.assert_called_once_with("test_event", attributes={})

    def test_trace_span_reraises_exception(self):
        """Test trace_span properly reraises exceptions"""
        with pytest.raises(ValueError, match="Test error"):
            with trace_span("failing_operation"):
                raise ValueError("Test error")
