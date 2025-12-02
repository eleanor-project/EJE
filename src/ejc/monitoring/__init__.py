"""
EJE Monitoring Module

Provides observability infrastructure including:
- Prometheus metrics export
- OpenTelemetry tracing
- Custom metric decorators
- Health checks
"""

from .prometheus_exporter import (
    PrometheusExporter,
    metrics_middleware,
    track_critic_execution,
    track_decision_execution,
    get_metrics_handler,
)

from .opentelemetry_tracer import (
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
)

__all__ = [
    # Prometheus metrics
    'PrometheusExporter',
    'metrics_middleware',
    'track_critic_execution',
    'track_decision_execution',
    'get_metrics_handler',
    # OpenTelemetry tracing
    'initialize_tracing',
    'get_tracer',
    'shutdown_tracing',
    'trace_decision',
    'trace_critic',
    'trace_span',
    'start_span',
    'add_span_event',
    'set_span_attribute',
    'get_trace_id',
    'get_span_id',
    'trace_precedent_lookup',
    'trace_policy_check',
    'trace_conflict_detected',
    'trace_override',
]
