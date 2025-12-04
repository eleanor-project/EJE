# Prometheus Metrics Setup Guide

This guide explains how to use the EJE Prometheus metrics exporter for production monitoring.

## Overview

The EJE Prometheus exporter provides comprehensive metrics for:
- **Critic Execution**: Latency, success rate, verdicts, confidence
- **Decision Aggregation**: Throughput, verdict distribution, conflicts
- **System Health**: Memory, CPU, active requests
- **Error Tracking**: Failures, fallbacks, retries

## Quick Start

### 1. Install Dependencies

```bash
pip install prometheus-client psutil
```

### 2. Basic Usage

```python
from ejc.monitoring import PrometheusExporter, get_metrics_handler

# Initialize exporter (done automatically on first import)
# Metrics are tracked via decorators

# In your HTTP framework, add metrics endpoint:

# Flask example:
from flask import Flask, Response
app = Flask(__name__)

@app.route('/metrics')
def metrics():
    data, content_type = get_metrics_handler()
    return Response(data, mimetype=content_type)

# FastAPI example:
from fastapi import FastAPI, Response as FastAPIResponse
app = FastAPI()

@app.get('/metrics')
def metrics():
    data, content_type = get_metrics_handler()
    return FastAPIResponse(content=data, media_type=content_type)
3. Instrument Your Code
Tracking Critic Executionpythonfrom ejc.monitoring import track_critic_execution

@track_critic_execution("bias_critic")
def evaluate_bias(input_text: str) -> dict:
    # Your critic logic here
    return {
        'verdict': 'ALLOW',
        'confidence': 0.92,
        'justification': 'No bias detected'
    }
# Automatically tracks:
# - Execution count
# - Latency
# - Verdict distribution
# - Confidence scores
# - Failures
Tracking Decision Aggregationpythonfrom ejc.monitoring import track_decision_execution

@track_decision_execution
def aggregate_decision(critic_results: list) -> dict:
    # Your aggregation logic
    return {
        'overall_verdict': 'ALLOW',
        'requires_review': False,
        'avg_confidence': 0.88,
        'verdict_scores': {'ALLOW': 1.8, 'BLOCK': 0.2}
    }
# Automatically tracks:
# - Decision count
# - Latency
# - Verdict distribution
# - Average confidence
Manual Metric Recordingpythonfrom ejc.monitoring import (
    record_error,
    record_fallback,
    record_conflict,
    record_retry,
    record_override
)

# Record an error
try:
    risky_operation()
except ValueError as e:
    record_error(error_type="ValueError", component="api")
    raise

# Record a fallback
if all_critics_failed:
    record_fallback(reason="all_critics_failed")
    return default_decision

# Record a conflict
if opposing_verdicts_detected:
    record_conflict(conflict_type="opposing_verdicts", severity="high")

# Record a retry
if need_retry:
    record_retry(operation_type="llm_api_call")

# Record an override
if manual_override:
    record_override(override_type="human_review")
Available Metrics
Critic MetricsMetric NameTypeDescriptioneje_critic_executions_totalCounterTotal critic executionseje_critic_execution_duration_secondsHistogramCritic execution latencyeje_critic_confidenceSummaryCritic confidence scoreseje_critic_failures_totalCounterCritic failureseje_critic_executions_activeGaugeCurrently executing criticsDecision MetricsMetric NameTypeDescriptioneje_decisions_totalCounterTotal decisions madeeje_decision_duration_secondsHistogramDecision aggregation latencyeje_verdict_distributionGaugeCurrent verdict distributioneje_decision_confidence_avgGaugeAverage decision confidenceeje_conflicts_detected_totalCounterConflicts detectedeje_overrides_totalCounterOverride decisionsSystem MetricsMetric NameTypeDescriptioneje_memory_usage_bytesGaugeMemory usage (RSS, VMS)eje_cpu_usage_percentGaugeCPU usage percentageeje_system_infoGaugeSystem information (static)eje_active_requestsGaugeActive HTTP requestsError MetricsMetric NameTypeDescriptioneje_errors_totalCounterTotal errorseje_fallbacks_totalCounterFallback activationseje_retries_totalCounterRetry attemptsprometheus.yml Configurationyamlglobal:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'eje'
    static_configs:
      - targets: ['localhost:8000']  # Your EJE API server
    metrics_path: '/metrics'
    scrape_interval: 10s
Example QueriesTotal Decisions Per Minutepromqlrate(eje_decisions_total[1m])
P95 Critic Latencypromqlhistogram_quantile(0.95,
  rate(eje_critic_execution_duration_seconds_bucket[5m])
)
Critic Success Ratepromqlrate(eje_critic_executions_total{status="success"}[5m])
/
rate(eje_critic_executions_total[5m])
Verdict Distributionpromqleje_verdict_distribution
Error Ratepromqlrate(eje_errors_total[5m])
Active Requests/Executionspromqleje_active_requests
eje_critic_executions_active
Conflict Detection Ratepromqlrate(eje_conflicts_detected_total[5m])
/
rate(eje_decisions_total[5m])
Alerting Rules
Example alerts.yaml for AlertManager:
yamlgroups:
  - name: eje_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(eje_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      # High conflict rate
      - alert: HighConflictRate
        expr: |
          rate(eje_conflicts_detected_total[5m])
          /
          rate(eje_decisions_total[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High conflict rate detected"
          description: "{{ $value }}% of decisions have conflicts"

      # Critic failures
      - alert: CriticFailures
        expr: rate(eje_critic_failures_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critics are failing"
          description: "Critic failure rate: {{ $value }}/sec"

      # Slow decisions
      - alert: SlowDecisions
        expr: |
          histogram_quantile(0.95,
            rate(eje_decision_duration_seconds_bucket[5m])
          ) > 5.0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Slow decision aggregation"
          description: "P95 latency: {{ $value }}s"

      # High memory usage
      - alert: HighMemoryUsage
        expr: eje_memory_usage_bytes{memory_type="rss"} > 2e9  # 2GB
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "RSS memory: {{ $value | humanize }}B"
Custom Metrics
Creating custom metrics:
pythonfrom ejc.monitoring import get_exporter

# Get the global exporter
exporter = get_exporter()

# Create custom counter
custom_counter = exporter.create_custom_counter(
    name="custom_events_total",
    description="Custom event counter",
    labels=["event_type", "severity"]
)

# Use it
custom_counter.labels(event_type="precedent_match", severity="high").inc()

# Create custom gauge
custom_gauge = exporter.create_custom_gauge(
    name="queue_depth",
    description="Current queue depth",
    labels=["queue_name"]
)

# Use it
custom_gauge.labels(queue_name="decisions").set(42)

# Create custom histogram
custom_histogram = exporter.create_custom_histogram(
    name="custom_duration_seconds",
    description="Custom operation duration",
    labels=["operation"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

# Use it
custom_histogram.labels(operation="precedent_lookup").observe(0.23)
Testing
Test that metrics are being exported:
bashcurl http://localhost:8000/metrics
```

You should see Prometheus-formatted output:
```
# HELP eje_critic_executions_total Total number of critic executions
# TYPE eje_critic_executions_total counter
eje_critic_executions_total{critic_name="bias_critic",status="success",verdict="ALLOW"} 142.0

# HELP eje_decision_duration_seconds Decision aggregation duration in seconds
# TYPE eje_decision_duration_seconds histogram
eje_decision_duration_seconds_bucket{le="0.01"} 45.0
eje_decision_duration_seconds_bucket{le="0.05"} 89.0
...
Production Deployment
Docker Composeyamlversion: '3.8'

services:
  eje:
    image: eje:latest
    ports:
      - "8000:8000"
    environment:
      - PROMETHEUS_ENABLED=true

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
Kubernetes Deploymentyamlapiversion: v1
kind: Service
metadata:
  name: eje-metrics
spec:
  selector:
    app: eje
  ports:
    - port: 8000
      targetPort: 8000
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
Best Practices
Use Labels Wisely: Keep cardinality low (avoid high-cardinality labels like user IDs)
Name Metrics Clearly: Follow Prometheus naming conventions (snake_case, units in name)
Set Appropriate Buckets: Histogram buckets should match your SLOs
Monitor the Monitors: Alert on Prometheus itself being down
Dashboard Design: Focus on key business and technical metrics
Troubleshooting
Metrics Not AppearingCheck /metrics endpoint is accessible
Verify decorators are applied to functions
Ensure Prometheus is scraping the right port/path
Check Prometheus logs for scrape errors

Missing LabelsMake sure all label values are provided
Labels must be consistent across metric uses
Check for typos in label names

High Memory UsageReduce metric cardinality
Consider sampling for high-frequency metrics
Use histogram/summary instead of many gauges

Resources
Prometheus Documentation
Prometheus Best Practices
Grafana Dashboards
OpenMetrics Specification

Support
For issues or questions, see:

EJE Documentation
GitHub Issues
Example Dashboards

---

**Last Updated**: 2025-12-01
**Version**: 1.0.0
