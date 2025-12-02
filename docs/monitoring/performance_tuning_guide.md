# EJE Monitoring Performance Tuning Guide

Optimization guidelines for EJE monitoring infrastructure.

## Quick Reference

| Component | Default | High Load | Notes |
|-----------|---------|-----------|-------|
| **Prometheus** |
| Scrape Interval | 15s | 30s | Reduce frequency for high-cardinality |
| Retention Time | 30d | 14d | Reduce to save storage |
| Memory | 2Gi | 8Gi | +2GB per 1M active series |
| CPU | 1 core | 4 cores | Scale with query load |
| **Grafana** |
| Memory | 512Mi | 2Gi | Increase for concurrent users |
| CPU | 250m | 1000m | Increase for complex queries |
| Query Cache | Disabled | 5m | Enable for frequently viewed dashboards |
| **AlertManager** |
| Memory | 256Mi | 512Mi | Rarely needs tuning |
| CPU | 100m | 200m | Lightweight component |
| **Jaeger** |
| Sampling Rate | 100% | 10% | Production: 1-10% |
| Collector Memory | 1Gi | 4Gi | Batch size dependent |
| ES Shards | 1 | 3-5 | Scale with trace volume |

## Prometheus Optimization

### 1. Scrape Configuration

**Reduce Scrape Frequency**:
```yaml
global:
  scrape_interval: 30s  # From 15s
  scrape_timeout: 10s
```

**Impact**: 50% less data ingestion, 50% less CPU usage

**Trade-off**: Lower resolution metrics

### 2. Storage Optimization

**Retention Settings**:
```yaml
# Prometheus command args
- '--storage.tsdb.retention.time=14d'  # Reduce from 30d
- '--storage.tsdb.retention.size=50GB'  # Set size limit
```

**Compression**:
```yaml
# Enable compression (default)
- '--storage.tsdb.wal-compression'
```

**Impact**: 60-70% storage savings

### 3. Query Optimization

**Recording Rules** (Pre-compute expensive queries):
```yaml
groups:
  - name: eje_aggregates
    interval: 1m
    rules:
      - record: eje:decision_success_rate:1m
        expr: |
          rate(eje_decisions_total{verdict="APPROVE"}[1m])
          /
          rate(eje_decisions_total[1m])
```

**Usage in Dashboards**:
```promql
# Instead of computing on every dashboard load
eje:decision_success_rate:1m
```

**Impact**: 10-100x faster dashboard loading

### 4. Cardinality Management

**Identify High Cardinality**:
```promql
# Top 10 metrics by series count
topk(10, count by (__name__) ({__name__=~".+"}))
```

**Limit Labels**:
```python
# Bad: Unbounded cardinality
metric.labels(user_id=str(user_id)).inc()

# Good: Bounded cardinality
metric.labels(user_type=user.type).inc()
```

**Drop High-Cardinality Metrics**:
```yaml
# In prometheus.yml
scrape_configs:
  - job_name: 'eje'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'eje_high_cardinality_.*'
        action: drop
```

### 5. Resource Sizing

**Memory Formula**:
```
Memory (GB) = (active_series × 2-3 bytes) + 2GB base
```

**Example**:
- 1M active series: ~2GB + 2GB = 4GB
- 5M active series: ~10GB + 2GB = 12GB

**Storage Formula**:
```
Storage (GB) = retention_days × ingestion_rate × sample_size × compression
```

**Example**:
- 30 days × 100k series × 15s intervals × 2 bytes × 0.3 = ~40GB

## Grafana Optimization

### 1. Query Caching

**Enable Query Caching**:
```yaml
# grafana.ini or env vars
[caching]
enabled = true

[query_caching]
enabled = true
ttl = 5m
```

**Impact**: 10x faster dashboard loading for cached queries

### 2. Dashboard Optimization

**Use Variables**:
```
# Instead of separate panels per critic
$critic_name variable with regex: .*

# Single panel with:
rate(eje_critic_executions_total{critic_name=~"$critic_name"}[5m])
```

**Limit Time Ranges**:
```
# Default to last 6 hours, not last 30 days
from: now-6h
to: now
```

**Impact**: 10-50x faster query execution

### 3. Connection Pooling

```yaml
[database]
max_open_conn = 300  # Increase from default 100
max_idle_conn = 100  # Increase from default 2
conn_max_lifetime = 14400  # 4 hours
```

### 4. Resource Sizing

**Concurrent Users Formula**:
```
Memory (Mi) = 128 + (concurrent_users × 50)
CPU (m) = 100 + (concurrent_users × 20)
```

**Example**:
- 20 users: 128 + 1000 = 1128Mi, 100 + 400 = 500m

## AlertManager Optimization

### 1. Grouping Configuration

**Reduce Notification Volume**:
```yaml
route:
  group_by: ['alertname', 'severity', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h  # Increase from default 3h
```

**Impact**: 50-90% fewer notifications

### 2. Inhibition Rules

**Smart Suppression**:
```yaml
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'component']
```

**Impact**: Reduce noise by 30-60%

## Jaeger Optimization

### 1. Sampling Configuration

**Adaptive Sampling**:
```yaml
# Production sampling rates
sampling:
  default_strategy:
    type: probabilistic
    param: 0.01  # 1% sampling

  per_operation_strategies:
    - operation: "critical_path"
      type: probabilistic
      param: 1.0  # 100% sampling
```

**Impact**: 99% less trace storage, minimal visibility loss

### 2. Batch Configuration

**Collector Optimization**:
```yaml
env:
  - name: COLLECTOR_QUEUE_SIZE
    value: "10000"
  - name: COLLECTOR_NUM_WORKERS
    value: "100"
```

### 3. Elasticsearch Optimization

**Index Lifecycle Management**:
```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_size": "50gb"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {"number_of_shards": 1}
        }
      },
      "cold": {
        "min_age": "30d"
      },
      "delete": {
        "min_age": "90d"
      }
    }
  }
}
```

## System-Level Tuning

### 1. Network Optimization

**TCP Tuning** (Linux):
```bash
# Increase buffer sizes
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864"
```

### 2. Disk I/O Optimization

**Mount Options**:
```bash
# /etc/fstab for Prometheus data directory
/dev/sdb1 /prometheus ext4 noatime,nodiratime 0 2
```

**File Descriptors**:
```bash
# Increase open file limit
ulimit -n 65536
```

### 3. Kubernetes Resource Limits

**Set Appropriate Limits**:
```yaml
resources:
  requests:
    memory: "2Gi"  # Guaranteed
    cpu: "1000m"
  limits:
    memory: "4Gi"  # Maximum (2x requests)
    cpu: "2000m"   # Maximum (2x requests)
```

**Why 2x**:
- Allows burst traffic
- Prevents OOM kills
- Better bin packing

## Monitoring Performance

### Key Metrics

**Prometheus**:
```promql
# Query duration (should be <1s)
rate(prometheus_engine_query_duration_seconds_sum[5m])
/
rate(prometheus_engine_query_duration_seconds_count[5m])

# Scrape duration (should be <5s)
prometheus_target_interval_length_seconds

# Active series (monitor growth)
prometheus_tsdb_symbol_table_size_bytes
```

**Grafana**:
```promql
# Query time (should be <5s)
grafana_datasource_request_duration_seconds

# Active users
grafana_stat_totals_users
```

**Jaeger**:
```promql
# Collector queue size (should be <1000)
jaeger_collector_queue_length

# Span throughput
rate(jaeger_collector_spans_received_total[5m])
```

## Scaling Thresholds

### When to Scale

| Metric | Threshold | Action |
|--------|-----------|--------|
| Prometheus memory | >80% | Add memory or reduce retention |
| Prometheus active series | >10M | Shard Prometheus or reduce cardinality |
| Grafana query time | >5s | Add query caching or recording rules |
| Jaeger collector queue | >5000 | Scale collector horizontally |
| Elasticsearch disk | >80% | Add storage or reduce retention |
| Alert rate | >100/min | Review alert thresholds |

### Horizontal Scaling

**Prometheus**:
```bash
# Add more Prometheus instances with sharding
# Each scrapes different set of targets
```

**Grafana**:
```bash
# Add more Grafana instances behind load balancer
kubectl scale deployment grafana -n eje-monitoring --replicas=5
```

**Jaeger Collector**:
```bash
# Scale collector deployment
kubectl scale deployment jaeger-collector -n eje-monitoring --replicas=10
```

## Cost Optimization

### 1. Storage Costs

**Reduce Retention**:
- Metrics: 30d → 14d (50% savings)
- Traces: 90d → 30d (67% savings)

**Tiered Storage**:
- Hot: SSD (last 7 days)
- Warm: HDD (7-30 days)
- Cold: Object storage (>30 days)

### 2. Compute Costs

**Right-Size Resources**:
```bash
# Analyze actual usage
kubectl top pods -n eje-monitoring

# Reduce if underutilized
kubectl set resources deployment/grafana \
  --limits=cpu=500m,memory=1Gi \
  -n eje-monitoring
```

### 3. Network Costs

**Reduce Scrape Frequency**:
```yaml
# 30s instead of 15s = 50% less network traffic
scrape_interval: 30s
```

**Enable Compression**:
```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'eje'
    honor_labels: true
    scheme: http
    # Metrics compressed by default
```

## Troubleshooting Performance Issues

### High Memory Usage

**Diagnosis**:
```promql
# Check series count
prometheus_tsdb_symbol_table_size_bytes

# Check ingestion rate
rate(prometheus_tsdb_head_samples_appended_total[5m])
```

**Solutions**:
1. Reduce cardinality
2. Reduce retention
3. Add more memory
4. Implement sharding

### Slow Queries

**Diagnosis**:
```promql
# Slowest queries
topk(10, prometheus_engine_query_duration_seconds)
```

**Solutions**:
1. Add recording rules
2. Optimize PromQL
3. Increase query timeout
4. Add query result caching

### High Disk I/O

**Diagnosis**:
```bash
# Check I/O wait
iostat -x 1

# Check Prometheus compaction
prometheus_tsdb_compactions_total
```

**Solutions**:
1. Use SSD storage
2. Tune compaction settings
3. Reduce ingestion rate
4. Increase disk throughput

## Best Practices Summary

1. **Start Small**: Begin with defaults, scale as needed
2. **Monitor the Monitors**: Watch Prometheus/Grafana metrics
3. **Recording Rules**: Pre-compute expensive queries
4. **Cardinality**: Keep labels bounded
5. **Retention**: Match to actual needs
6. **Sampling**: Use adaptive sampling for traces
7. **Caching**: Enable query caching in Grafana
8. **Resources**: Set requests = actual usage, limits = 2x requests
9. **Review Quarterly**: Audit metrics, alerts, dashboards
10. **Test**: Load test before production

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
