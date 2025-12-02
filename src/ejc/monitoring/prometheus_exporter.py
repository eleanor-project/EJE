"""
Prometheus Metrics Exporter for EJE

Provides comprehensive metrics collection for:
- Critic execution (latency, success rate, verdicts)
- Decision aggregation (throughput, verdict distribution)
- System health (memory, CPU, errors)
- Custom business metrics

Metrics follow Prometheus naming conventions:
- Counters: _total suffix
- Gauges: current values
- Histograms: _bucket, _sum, _count
- Summaries: percentiles
"""

import functools
import os
import platform
import psutil
import time
from typing import Any, Callable, Dict, List, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


class PrometheusExporter:
    """
    Central Prometheus metrics exporter for EJE.

    Provides:
    - Automatic metric registration
    - Decorator-based instrumentation
    - Health metrics collection
    - Custom metric creation
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None, namespace: str = "eje"):
        """
        Initialize Prometheus exporter.

        Args:
            registry: Optional custom Prometheus registry
            namespace: Metric namespace prefix (default: "eje")
        """
        self.registry = registry or CollectorRegistry()
        self.namespace = namespace

        # Initialize all metrics
        self._init_critic_metrics()
        self._init_decision_metrics()
        self._init_eje_specific_metrics()
        self._init_system_metrics()
        self._init_error_metrics()

    def _init_critic_metrics(self):
        """Initialize critic execution metrics"""
        # Critic execution counter
        self.critic_executions_total = Counter(
            f'{self.namespace}_critic_executions_total',
            'Total number of critic executions',
            ['critic_name', 'verdict', 'status'],
            registry=self.registry
        )

        # Critic execution latency histogram
        self.critic_execution_duration_seconds = Histogram(
            f'{self.namespace}_critic_execution_duration_seconds',
            'Critic execution duration in seconds',
            ['critic_name'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        # Critic confidence summary
        self.critic_confidence = Summary(
            f'{self.namespace}_critic_confidence',
            'Critic confidence scores',
            ['critic_name', 'verdict'],
            registry=self.registry
        )

        # Critic failures counter
        self.critic_failures_total = Counter(
            f'{self.namespace}_critic_failures_total',
            'Total number of critic failures',
            ['critic_name', 'error_type'],
            registry=self.registry
        )

        # Active critic executions gauge
        self.critic_executions_active = Gauge(
            f'{self.namespace}_critic_executions_active',
            'Number of currently executing critics',
            registry=self.registry
        )

    def _init_decision_metrics(self):
        """Initialize decision aggregation metrics"""
        # Decision counter
        self.decisions_total = Counter(
            f'{self.namespace}_decisions_total',
            'Total number of decisions made',
            ['final_verdict', 'requires_review'],
            registry=self.registry
        )

        # Decision latency histogram
        self.decision_duration_seconds = Histogram(
            f'{self.namespace}_decision_duration_seconds',
            'Decision aggregation duration in seconds',
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            registry=self.registry
        )

        # Verdict distribution gauge
        self.verdict_distribution = Gauge(
            f'{self.namespace}_verdict_distribution',
            'Current distribution of verdicts',
            ['verdict_type'],
            registry=self.registry
        )

        # Average confidence gauge
        self.decision_confidence_avg = Gauge(
            f'{self.namespace}_decision_confidence_avg',
            'Average decision confidence',
            registry=self.registry
        )

        # Conflicts counter
        self.conflicts_detected_total = Counter(
            f'{self.namespace}_conflicts_detected_total',
            'Total number of conflicts detected',
            ['conflict_type', 'severity'],
            registry=self.registry
        )

        # Override counter
        self.overrides_total = Counter(
            f'{self.namespace}_overrides_total',
            'Total number of override decisions',
            ['override_type'],
            registry=self.registry
        )

    def _init_eje_specific_metrics(self):
        """Initialize EJE-specific governance metrics"""
        # Decision confidence histogram (more detailed than average)
        self.decision_confidence_histogram = Histogram(
            f'{self.namespace}_decision_confidence',
            'Distribution of decision confidence scores',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
            registry=self.registry
        )

        # Precedent match rate counter
        self.precedent_matches_total = Counter(
            f'{self.namespace}_precedent_matches_total',
            'Total number of precedent matches found',
            ['match_quality', 'precedent_type'],
            registry=self.registry
        )

        # Precedent lookups counter
        self.precedent_lookups_total = Counter(
            f'{self.namespace}_precedent_lookups_total',
            'Total number of precedent lookup operations',
            ['lookup_type'],
            registry=self.registry
        )

        # Critic agreement gauge (percentage of critics in agreement)
        self.critic_agreement_ratio = Gauge(
            f'{self.namespace}_critic_agreement_ratio',
            'Ratio of critics in agreement (0.0-1.0)',
            ['decision_id'],
            registry=self.registry
        )

        # Critic unanimous verdicts counter
        self.critic_unanimous_verdicts_total = Counter(
            f'{self.namespace}_critic_unanimous_verdicts_total',
            'Total number of unanimous critic verdicts',
            ['verdict_type'],
            registry=self.registry
        )

        # Audit trail size gauge
        self.audit_trail_size_bytes = Gauge(
            f'{self.namespace}_audit_trail_size_bytes',
            'Current audit trail storage size in bytes',
            ['storage_type'],
            registry=self.registry
        )

        # Audit trail entries counter
        self.audit_trail_entries_total = Counter(
            f'{self.namespace}_audit_trail_entries_total',
            'Total number of audit trail entries',
            ['entry_type', 'severity'],
            registry=self.registry
        )

        # Cache hit rate counter
        self.cache_hits_total = Counter(
            f'{self.namespace}_cache_hits_total',
            'Total number of cache hits',
            ['cache_name', 'cache_type'],
            registry=self.registry
        )

        # Cache misses counter
        self.cache_misses_total = Counter(
            f'{self.namespace}_cache_misses_total',
            'Total number of cache misses',
            ['cache_name', 'cache_type'],
            registry=self.registry
        )

        # Cache evictions counter
        self.cache_evictions_total = Counter(
            f'{self.namespace}_cache_evictions_total',
            'Total number of cache evictions',
            ['cache_name', 'eviction_reason'],
            registry=self.registry
        )

        # Cache size gauge
        self.cache_size_bytes = Gauge(
            f'{self.namespace}_cache_size_bytes',
            'Current cache size in bytes',
            ['cache_name'],
            registry=self.registry
        )

        # Cache entry count gauge
        self.cache_entries = Gauge(
            f'{self.namespace}_cache_entries',
            'Current number of entries in cache',
            ['cache_name'],
            registry=self.registry
        )

        # Policy rule applications counter
        self.policy_rules_applied_total = Counter(
            f'{self.namespace}_policy_rules_applied_total',
            'Total number of policy rule applications',
            ['policy_name', 'rule_outcome'],
            registry=self.registry
        )

        # Governance compliance gauge
        self.governance_compliance_score = Gauge(
            f'{self.namespace}_governance_compliance_score',
            'Current governance compliance score (0.0-1.0)',
            ['compliance_domain'],
            registry=self.registry
        )

    def _init_system_metrics(self):
        """Initialize system health metrics"""
        # Memory usage gauge
        self.memory_usage_bytes = Gauge(
            f'{self.namespace}_memory_usage_bytes',
            'Current memory usage in bytes',
            ['memory_type'],
            registry=self.registry
        )

        # CPU usage gauge
        self.cpu_usage_percent = Gauge(
            f'{self.namespace}_cpu_usage_percent',
            'Current CPU usage percentage',
            registry=self.registry
        )

        # System info gauge (static)
        self.system_info = Gauge(
            f'{self.namespace}_system_info',
            'System information',
            ['python_version', 'platform', 'hostname'],
            registry=self.registry
        )

        # Set system info (static value)
        self.system_info.labels(
            python_version=platform.python_version(),
            platform=platform.system(),
            hostname=platform.node()
        ).set(1)

        # Active requests gauge
        self.active_requests = Gauge(
            f'{self.namespace}_active_requests',
            'Number of active requests',
            registry=self.registry
        )

    def _init_error_metrics(self):
        """Initialize error tracking metrics"""
        # Error counter
        self.errors_total = Counter(
            f'{self.namespace}_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )

        # Fallback counter
        self.fallbacks_total = Counter(
            f'{self.namespace}_fallbacks_total',
            'Total number of fallback activations',
            ['fallback_reason'],
            registry=self.registry
        )

        # Retry counter
        self.retries_total = Counter(
            f'{self.namespace}_retries_total',
            'Total number of retry attempts',
            ['operation_type'],
            registry=self.registry
        )

    def update_system_metrics(self):
        """Update system health metrics (call periodically)"""
        process = psutil.Process()

        # Memory metrics
        mem_info = process.memory_info()
        self.memory_usage_bytes.labels(memory_type='rss').set(mem_info.rss)
        self.memory_usage_bytes.labels(memory_type='vms').set(mem_info.vms)

        # CPU metrics
        cpu_percent = process.cpu_percent(interval=0.1)
        self.cpu_usage_percent.set(cpu_percent)

    def get_metrics(self) -> bytes:
        """
        Get current metrics in Prometheus exposition format.

        Returns:
            Bytes containing Prometheus-formatted metrics
        """
        # Update system metrics before export
        self.update_system_metrics()
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get Prometheus content type for HTTP response"""
        return CONTENT_TYPE_LATEST

    def create_custom_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Counter:
        """
        Create a custom counter metric.

        Args:
            name: Metric name (will be prefixed with namespace)
            description: Metric description
            labels: Optional label names

        Returns:
            Counter instance
        """
        return Counter(
            f'{self.namespace}_{name}',
            description,
            labels or [],
            registry=self.registry
        )

    def create_custom_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """
        Create a custom gauge metric.

        Args:
            name: Metric name (will be prefixed with namespace)
            description: Metric description
            labels: Optional label names

        Returns:
            Gauge instance
        """
        return Gauge(
            f'{self.namespace}_{name}',
            description,
            labels or [],
            registry=self.registry
        )

    def create_custom_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[tuple] = None
    ) -> Histogram:
        """
        Create a custom histogram metric.

        Args:
            name: Metric name (will be prefixed with namespace)
            description: Metric description
            labels: Optional label names
            buckets: Optional histogram buckets

        Returns:
            Histogram instance
        """
        return Histogram(
            f'{self.namespace}_{name}',
            description,
            labels or [],
            buckets=buckets,
            registry=self.registry
        )


# Global exporter instance
_global_exporter: Optional[PrometheusExporter] = None


def get_exporter() -> PrometheusExporter:
    """Get or create global Prometheus exporter instance"""
    global _global_exporter
    if _global_exporter is None:
        _global_exporter = PrometheusExporter()
    return _global_exporter


# Decorator for tracking critic execution
def track_critic_execution(critic_name: str):
    """
    Decorator to track critic execution metrics.

    Args:
        critic_name: Name of the critic

    Usage:
        @track_critic_execution("bias_critic")
        def evaluate_bias(input_text):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            exporter = get_exporter()

            # Increment active executions
            exporter.critic_executions_active.inc()

            start_time = time.time()
            status = 'success'
            verdict = 'UNKNOWN'
            error_type = None

            try:
                result = func(*args, **kwargs)

                # Extract verdict from result
                if isinstance(result, dict):
                    verdict = result.get('verdict', 'UNKNOWN')
                    confidence = result.get('confidence', 0.0)

                    # Record confidence
                    exporter.critic_confidence.labels(
                        critic_name=critic_name,
                        verdict=verdict
                    ).observe(confidence)

                return result

            except Exception as e:
                status = 'error'
                error_type = type(e).__name__
                exporter.critic_failures_total.labels(
                    critic_name=critic_name,
                    error_type=error_type
                ).inc()
                raise

            finally:
                # Record execution time
                duration = time.time() - start_time
                exporter.critic_execution_duration_seconds.labels(
                    critic_name=critic_name
                ).observe(duration)

                # Record execution
                exporter.critic_executions_total.labels(
                    critic_name=critic_name,
                    verdict=verdict,
                    status=status
                ).inc()

                # Decrement active executions
                exporter.critic_executions_active.dec()

        return wrapper
    return decorator


# Decorator for tracking decision execution
def track_decision_execution(func: Callable) -> Callable:
    """
    Decorator to track decision aggregation metrics.

    Usage:
        @track_decision_execution
        def aggregate_decision(critic_results):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        exporter = get_exporter()

        # Increment active requests
        exporter.active_requests.inc()

        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # Extract decision info
            if isinstance(result, dict):
                final_verdict = result.get('overall_verdict', 'UNKNOWN')
                requires_review = 'true' if result.get('requires_review', False) else 'false'
                avg_confidence = result.get('avg_confidence', 0.0)

                # Record decision
                exporter.decisions_total.labels(
                    final_verdict=final_verdict,
                    requires_review=requires_review
                ).inc()

                # Update confidence gauge
                exporter.decision_confidence_avg.set(avg_confidence)

                # Update verdict distribution
                if 'verdict_scores' in result:
                    for verdict, score in result['verdict_scores'].items():
                        exporter.verdict_distribution.labels(
                            verdict_type=verdict
                        ).set(score)

            return result

        finally:
            # Record execution time
            duration = time.time() - start_time
            exporter.decision_duration_seconds.observe(duration)

            # Decrement active requests
            exporter.active_requests.dec()

    return wrapper


# Middleware for HTTP frameworks
def metrics_middleware(request_handler: Callable) -> Callable:
    """
    Middleware to track HTTP request metrics.

    Args:
        request_handler: HTTP request handler function

    Returns:
        Wrapped handler with metrics tracking
    """
    @functools.wraps(request_handler)
    def wrapper(*args, **kwargs):
        exporter = get_exporter()
        exporter.active_requests.inc()

        start_time = time.time()

        try:
            return request_handler(*args, **kwargs)
        finally:
            exporter.active_requests.dec()

    return wrapper


# Metrics endpoint handler
def get_metrics_handler():
    """
    Get metrics handler for HTTP endpoint.

    Returns:
        Tuple of (metrics_data, content_type)

    Usage with Flask:
        @app.route('/metrics')
        def metrics():
            data, content_type = get_metrics_handler()
            return Response(data, mimetype=content_type)

    Usage with FastAPI:
        @app.get('/metrics')
        def metrics():
            data, content_type = get_metrics_handler()
            return Response(content=data, media_type=content_type)
    """
    exporter = get_exporter()
    return exporter.get_metrics(), exporter.get_content_type()


# Convenience functions for recording metrics
def record_error(error_type: str, component: str):
    """Record an error occurrence"""
    exporter = get_exporter()
    exporter.errors_total.labels(
        error_type=error_type,
        component=component
    ).inc()


def record_fallback(reason: str):
    """Record a fallback activation"""
    exporter = get_exporter()
    exporter.fallbacks_total.labels(fallback_reason=reason).inc()


def record_retry(operation_type: str):
    """Record a retry attempt"""
    exporter = get_exporter()
    exporter.retries_total.labels(operation_type=operation_type).inc()


def record_conflict(conflict_type: str, severity: str):
    """Record a detected conflict"""
    exporter = get_exporter()
    exporter.conflicts_detected_total.labels(
        conflict_type=conflict_type,
        severity=severity
    ).inc()


def record_override(override_type: str):
    """Record an override decision"""
    exporter = get_exporter()
    exporter.overrides_total.labels(override_type=override_type).inc()
