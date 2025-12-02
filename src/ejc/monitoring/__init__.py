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

__all__ = [
    'PrometheusExporter',
    'metrics_middleware',
    'track_critic_execution',
    'track_decision_execution',
    'get_metrics_handler',
]
