"""
OpenTelemetry Distributed Tracing for EJE

Provides distributed tracing capabilities for tracking requests across critics
and understanding end-to-end decision pipeline performance.

Features:
- Automatic span creation for decisions and critics
- Custom attributes for EJE-specific metadata
- Trace sampling configuration
- Jaeger export integration
- Performance overhead monitoring
"""

import functools
import os
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace import Status, StatusCode, Tracer


# Global tracer instance
_tracer: Optional[Tracer] = None
_tracer_provider: Optional[TracerProvider] = None


def initialize_tracing(
    service_name: str = "eje",
    jaeger_endpoint: Optional[str] = None,
    sampling_rate: float = 1.0,
    console_export: bool = False
) -> Tracer:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for trace identification
        jaeger_endpoint: Jaeger collector endpoint (e.g., "http://localhost:14268/api/traces")
        sampling_rate: Sampling rate (0.0 to 1.0). Default 1.0 = sample all traces
        console_export: Export traces to console for debugging

    Returns:
        Configured tracer instance

    Example:
        tracer = initialize_tracing(
            service_name="eje-prod",
            jaeger_endpoint="http://jaeger:14268/api/traces",
            sampling_rate=0.1  # Sample 10% of traces
        )
    """
    global _tracer, _tracer_provider

    # Create resource with service name
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    # Create sampler (parent-based with ratio)
    sampler = ParentBasedTraceIdRatio(sampling_rate)

    # Create tracer provider
    _tracer_provider = TracerProvider(
        resource=resource,
        sampler=sampler
    )

    # Configure exporters
    if jaeger_endpoint:
        jaeger_exporter = JaegerExporter(
            agent_host_name=_parse_jaeger_host(jaeger_endpoint),
            agent_port=_parse_jaeger_port(jaeger_endpoint),
        )
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )

    if console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Get tracer
    _tracer = trace.get_tracer(__name__)

    return _tracer


def _parse_jaeger_host(endpoint: str) -> str:
    """Extract hostname from Jaeger endpoint URL"""
    # Handle http://host:port/path format
    if "://" in endpoint:
        endpoint = endpoint.split("://")[1]
    if ":" in endpoint:
        endpoint = endpoint.split(":")[0]
    if "/" in endpoint:
        endpoint = endpoint.split("/")[0]
    return endpoint


def _parse_jaeger_port(endpoint: str) -> int:
    """Extract port from Jaeger endpoint URL"""
    # Default Jaeger agent port
    default_port = 6831

    if ":" in endpoint:
        try:
            port_part = endpoint.split(":")[1]
            if "/" in port_part:
                port_part = port_part.split("/")[0]
            return int(port_part)
        except (ValueError, IndexError):
            return default_port

    return default_port


def get_tracer() -> Tracer:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance

    Raises:
        RuntimeError: If tracing not initialized
    """
    global _tracer

    if _tracer is None:
        # Auto-initialize with defaults if not explicitly initialized
        jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
        sampling_rate = float(os.getenv("TRACE_SAMPLING_RATE", "1.0"))
        _tracer = initialize_tracing(
            jaeger_endpoint=jaeger_endpoint,
            sampling_rate=sampling_rate
        )

    return _tracer


def shutdown_tracing():
    """Shutdown tracing and flush remaining spans"""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()


# Decorator for tracing decision execution
def trace_decision(operation_name: Optional[str] = None):
    """
    Decorator to trace decision execution with a span.

    Args:
        operation_name: Optional custom operation name (defaults to function name)

    Usage:
        @trace_decision("aggregate_decision")
        def aggregate(critic_results):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = operation_name or f"decision.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Execute function
                    result = func(*args, **kwargs)

                    # Add result attributes to span
                    if isinstance(result, dict):
                        _add_decision_attributes(span, result)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


def _add_decision_attributes(span, result: Dict[str, Any]):
    """Add decision-specific attributes to span"""
    if "overall_verdict" in result:
        span.set_attribute("eje.decision.verdict", result["overall_verdict"])

    if "avg_confidence" in result:
        span.set_attribute("eje.decision.confidence", result["avg_confidence"])

    if "ambiguity" in result:
        span.set_attribute("eje.decision.ambiguity", result["ambiguity"])

    if "requires_review" in result:
        span.set_attribute("eje.decision.requires_review", result["requires_review"])

    if "details" in result and isinstance(result["details"], list):
        span.set_attribute("eje.decision.critic_count", len(result["details"]))


# Decorator for tracing critic execution
def trace_critic(critic_name: str):
    """
    Decorator to trace critic execution with a child span.

    Args:
        critic_name: Name of the critic for span naming

    Usage:
        @trace_critic("bias_critic")
        def evaluate_bias(input_text):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = f"critic.{critic_name}"

            with tracer.start_as_current_span(span_name) as span:
                # Add critic metadata
                span.set_attribute("eje.critic.name", critic_name)

                try:
                    # Execute critic
                    result = func(*args, **kwargs)

                    # Add result attributes
                    if isinstance(result, dict):
                        _add_critic_attributes(span, result)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    span.set_attribute("eje.critic.error", type(e).__name__)
                    raise

        return wrapper
    return decorator


def _add_critic_attributes(span, result: Dict[str, Any]):
    """Add critic-specific attributes to span"""
    if "verdict" in result:
        span.set_attribute("eje.critic.verdict", result["verdict"])

    if "confidence" in result:
        span.set_attribute("eje.critic.confidence", result["confidence"])

    if "weight" in result:
        span.set_attribute("eje.critic.weight", result["weight"])

    if "priority" in result and result["priority"]:
        span.set_attribute("eje.critic.priority", result["priority"])


# Context manager for custom spans
class trace_span:
    """
    Context manager for creating custom spans.

    Usage:
        with trace_span("precedent_lookup", case_id="abc123"):
            results = lookup_precedents(case)
    """

    def __init__(self, name: str, **attributes):
        """
        Create a traced span context manager.

        Args:
            name: Span name
            **attributes: Custom attributes to add to span
        """
        self.name = name
        self.attributes = attributes
        self.span = None

    def __enter__(self):
        tracer = get_tracer()
        self.span = tracer.start_as_current_span(self.name).__enter__()

        # Add custom attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(f"eje.{key}", value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))

        self.span.__exit__(exc_type, exc_val, exc_tb)


# Manual span creation functions
def start_span(name: str, **attributes) -> trace.Span:
    """
    Manually start a new span.

    Args:
        name: Span name
        **attributes: Custom attributes

    Returns:
        Started span

    Usage:
        span = start_span("custom_operation", operation_id="123")
        try:
            # do work
            span.set_status(Status(StatusCode.OK))
        finally:
            span.end()
    """
    tracer = get_tracer()
    span = tracer.start_span(name)

    for key, value in attributes.items():
        span.set_attribute(f"eje.{key}", value)

    return span


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes

    Usage:
        add_span_event("precedent_match_found", {"match_score": 0.95})
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any):
    """
    Set an attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value

    Usage:
        set_span_attribute("case_id", case_id)
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(f"eje.{key}", value)


def get_trace_id() -> str:
    """
    Get the current trace ID.

    Returns:
        Trace ID as hex string, or empty string if no active span

    Usage:
        trace_id = get_trace_id()
        logger.info(f"Processing request {trace_id}")
    """
    span = trace.get_current_span()
    if span.is_recording():
        return format(span.get_span_context().trace_id, '032x')
    return ""


def get_span_id() -> str:
    """
    Get the current span ID.

    Returns:
        Span ID as hex string, or empty string if no active span
    """
    span = trace.get_current_span()
    if span.is_recording():
        return format(span.get_span_context().span_id, '016x')
    return ""


# Convenience functions for common tracing operations
def trace_precedent_lookup(precedent_count: int):
    """Record a precedent lookup event"""
    add_span_event("precedent_lookup", {"count": precedent_count})


def trace_policy_check(policy_name: str, passed: bool):
    """Record a policy check event"""
    add_span_event("policy_check", {
        "policy": policy_name,
        "passed": passed
    })


def trace_conflict_detected(conflict_type: str, severity: str):
    """Record a conflict detection event"""
    add_span_event("conflict_detected", {
        "type": conflict_type,
        "severity": severity
    })


def trace_override(override_type: str, actor: str):
    """Record an override event"""
    add_span_event("override", {
        "type": override_type,
        "actor": actor
    })
