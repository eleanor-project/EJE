"""
Tests for Prometheus Metrics Exporter

Covers:
- Metric registration and initialization
- Decorator-based instrumentation
- Custom metric creation
- Metrics endpoint generation
- Error tracking
"""

import time
import pytest
from prometheus_client import CollectorRegistry

from ejc.monitoring.prometheus_exporter import (
    PrometheusExporter,
    track_critic_execution,
    track_decision_execution,
    get_exporter,
    record_error,
    record_fallback,
    record_retry,
    record_conflict,
    record_override,
    get_metrics_handler,
)


class TestPrometheusExporter:
    """Test suite for PrometheusExporter class"""

    def test_exporter_initialization(self):
        """Test that exporter initializes with all required metrics"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry, namespace="test")

        assert exporter.namespace == "test"
        assert exporter.registry == registry

        # Verify critic metrics exist
        assert exporter.critic_executions_total is not None
        assert exporter.critic_execution_duration_seconds is not None
        assert exporter.critic_confidence is not None
        assert exporter.critic_failures_total is not None

        # Verify decision metrics exist
        assert exporter.decisions_total is not None
        assert exporter.decision_duration_seconds is not None
        assert exporter.verdict_distribution is not None

        # Verify system metrics exist
        assert exporter.memory_usage_bytes is not None
        assert exporter.cpu_usage_percent is not None
        assert exporter.system_info is not None

    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns Prometheus-formatted bytes"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        metrics = exporter.get_metrics()

        assert isinstance(metrics, bytes)
        assert len(metrics) > 0
        # Should contain metric names
        assert b'eje_' in metrics

    def test_content_type(self):
        """Test that content type is correct for Prometheus"""
        exporter = PrometheusExporter()
        content_type = exporter.get_content_type()

        assert content_type.startswith('text/plain')

    def test_system_metrics_update(self):
        """Test that system metrics can be updated"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        # Should not raise exception
        exporter.update_system_metrics()

        # Metrics should be in output
        metrics = exporter.get_metrics()
        assert b'memory_usage_bytes' in metrics
        assert b'cpu_usage_percent' in metrics

    def test_custom_counter_creation(self):
        """Test creating custom counter metrics"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry, namespace="test")

        counter = exporter.create_custom_counter(
            name="custom_events_total",
            description="Custom event counter",
            labels=["event_type"]
        )

        assert counter is not None
        counter.labels(event_type="test").inc()

        metrics = exporter.get_metrics()
        assert b'test_custom_events_total' in metrics

    def test_custom_gauge_creation(self):
        """Test creating custom gauge metrics"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry, namespace="test")

        gauge = exporter.create_custom_gauge(
            name="custom_value",
            description="Custom gauge value",
            labels=["label"]
        )

        assert gauge is not None
        gauge.labels(label="test").set(42)

        metrics = exporter.get_metrics()
        assert b'test_custom_value' in metrics
        assert b'42' in metrics

    def test_custom_histogram_creation(self):
        """Test creating custom histogram metrics"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry, namespace="test")

        histogram = exporter.create_custom_histogram(
            name="custom_duration_seconds",
            description="Custom duration histogram",
            labels=["operation"],
            buckets=(0.1, 0.5, 1.0, 5.0)
        )

        assert histogram is not None
        histogram.labels(operation="test").observe(0.3)

        metrics = exporter.get_metrics()
        assert b'test_custom_duration_seconds' in metrics


class TestCriticExecutionDecorator:
    """Test suite for @track_critic_execution decorator"""

    def test_decorator_tracks_successful_execution(self):
        """Test that decorator tracks successful critic execution"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        # Replace global exporter for testing
        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_critic_execution("test_critic")
            def mock_critic():
                return {
                    'verdict': 'ALLOW',
                    'confidence': 0.9,
                    'justification': 'Test'
                }

            result = mock_critic()

            assert result['verdict'] == 'ALLOW'

            # Check metrics were recorded
            metrics = exporter.get_metrics()
            assert b'test_critic' in metrics
            assert b'ALLOW' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_decorator_tracks_execution_time(self):
        """Test that decorator measures execution time"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_critic_execution("slow_critic")
            def slow_critic():
                time.sleep(0.01)  # 10ms
                return {'verdict': 'DENY', 'confidence': 0.8}

            slow_critic()

            metrics = exporter.get_metrics()
            assert b'critic_execution_duration_seconds' in metrics
            assert b'slow_critic' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_decorator_tracks_failures(self):
        """Test that decorator tracks critic failures"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_critic_execution("failing_critic")
            def failing_critic():
                raise ValueError("Test error")

            with pytest.raises(ValueError):
                failing_critic()

            # Check failure was recorded
            metrics = exporter.get_metrics()
            assert b'critic_failures_total' in metrics
            assert b'failing_critic' in metrics
            assert b'ValueError' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_decorator_tracks_confidence(self):
        """Test that decorator records confidence scores"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_critic_execution("confident_critic")
            def confident_critic():
                return {'verdict': 'ALLOW', 'confidence': 0.95}

            confident_critic()

            metrics = exporter.get_metrics()
            assert b'critic_confidence' in metrics

        finally:
            prom_module._global_exporter = original_exporter


class TestDecisionExecutionDecorator:
    """Test suite for @track_decision_execution decorator"""

    def test_decorator_tracks_decisions(self):
        """Test that decorator tracks decision aggregation"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_decision_execution
            def mock_aggregator():
                return {
                    'overall_verdict': 'ALLOW',
                    'requires_review': False,
                    'avg_confidence': 0.88,
                    'verdict_scores': {
                        'ALLOW': 1.8,
                        'BLOCK': 0.2,
                        'REVIEW': 0.0
                    }
                }

            result = mock_aggregator()

            assert result['overall_verdict'] == 'ALLOW'

            # Check metrics
            metrics = exporter.get_metrics()
            assert b'decisions_total' in metrics
            assert b'decision_duration_seconds' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_decorator_updates_verdict_distribution(self):
        """Test that decorator updates verdict distribution gauge"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            @track_decision_execution
            def mock_aggregator():
                return {
                    'overall_verdict': 'BLOCK',
                    'verdict_scores': {
                        'ALLOW': 0.5,
                        'BLOCK': 2.0,
                        'REVIEW': 0.1
                    }
                }

            mock_aggregator()

            metrics = exporter.get_metrics()
            assert b'verdict_distribution' in metrics

        finally:
            prom_module._global_exporter = original_exporter


class TestConvenienceFunctions:
    """Test suite for convenience recording functions"""

    def test_record_error(self):
        """Test recording errors"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            record_error(error_type="ValueError", component="critic")

            metrics = exporter.get_metrics()
            assert b'errors_total' in metrics
            assert b'ValueError' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_record_fallback(self):
        """Test recording fallback activations"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            record_fallback(reason="all_critics_failed")

            metrics = exporter.get_metrics()
            assert b'fallbacks_total' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_record_retry(self):
        """Test recording retry attempts"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            record_retry(operation_type="llm_api_call")

            metrics = exporter.get_metrics()
            assert b'retries_total' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_record_conflict(self):
        """Test recording conflicts"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            record_conflict(conflict_type="opposing_verdicts", severity="high")

            metrics = exporter.get_metrics()
            assert b'conflicts_detected_total' in metrics

        finally:
            prom_module._global_exporter = original_exporter

    def test_record_override(self):
        """Test recording overrides"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            record_override(override_type="manual_review")

            metrics = exporter.get_metrics()
            assert b'overrides_total' in metrics

        finally:
            prom_module._global_exporter = original_exporter


class TestMetricsHandler:
    """Test suite for HTTP metrics handler"""

    def test_metrics_handler_returns_data(self):
        """Test that metrics handler returns data and content type"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        import ejc.monitoring.prometheus_exporter as prom_module
        original_exporter = prom_module._global_exporter
        prom_module._global_exporter = exporter

        try:
            data, content_type = get_metrics_handler()

            assert isinstance(data, bytes)
            assert len(data) > 0
            assert 'text/plain' in content_type

        finally:
            prom_module._global_exporter = original_exporter


class TestMetricsNaming:
    """Test that metrics follow Prometheus naming conventions"""

    def test_counter_names_have_total_suffix(self):
        """Test that counters have _total suffix"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        metrics = exporter.get_metrics().decode('utf-8')

        # Counters should have _total suffix
        assert 'critic_executions_total' in metrics
        assert 'decisions_total' in metrics
        assert 'errors_total' in metrics
        assert 'fallbacks_total' in metrics

    def test_histogram_names_have_proper_suffixes(self):
        """Test that histograms have _bucket, _sum, _count"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        # Record a measurement to generate histogram output
        exporter.critic_execution_duration_seconds.labels(critic_name="test").observe(0.5)

        metrics = exporter.get_metrics().decode('utf-8')

        # Histograms should have these suffixes
        assert '_duration_seconds_bucket' in metrics
        assert '_duration_seconds_sum' in metrics
        assert '_duration_seconds_count' in metrics

    def test_metric_names_use_snake_case(self):
        """Test that all metric names use snake_case"""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)

        metrics = exporter.get_metrics().decode('utf-8')

        # All metrics should use snake_case (no camelCase)
        lines = metrics.split('\n')
        for line in lines:
            if line.startswith('eje_'):
                # Extract metric name
                metric_name = line.split('{')[0].split(' ')[0]
                # Should not contain uppercase letters
                assert metric_name == metric_name.lower()
