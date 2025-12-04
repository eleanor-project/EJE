# EJE Monitoring Troubleshooting Guide

Quick reference for diagnosing and resolving common monitoring issues.

## Quick Diagnosis

```bash
# Health check all services
make -f Makefile.monitoring local-ps  # Docker Compose
make -f Makefile.monitoring k8s-status  # Kubernetes

# Validate configurations
make -f Makefile.monitoring validate-config

# Test alerts
make -f Makefile.monitoring test-alerts
```

## Common Issues

### Services Not Starting

#### Docker Compose

**Symptoms**: `docker-compose ps` shows containers as "Exit 1" or "Restarting"

**Diagnosis**:
```bash
# Check logs
docker-compose -f docker-compose.monitoring.yml logs prometheus
docker-compose -f docker-compose.monitoring.yml logs grafana

# Check config syntax
docker run --rm -v $(pwd)/monitoring/prometheus:/prometheus \
  prom/prometheus:v2.47.0 \
  promtool check config /prometheus/prometheus.yml
```

**Common Causes**:
1. **Port conflict**: Another service using 3000, 9090, 9093, or 16686
   - Solution: Change ports in docker-compose.yml or stop conflicting service
2. **Config syntax error**: Invalid YAML
   - Solution: Run `promtool check config` or `amtool check-config`
3. **Permission issues**: Cannot write to volumes
   - Solution: `chmod 777 ./data` or fix volume permissions
4. **Out of memory**: System has < 8GB RAM
   - Solution: Reduce resource limits or add RAM

#### Kubernetes

**Symptoms**: Pods in `CrashLoopBackOff`, `Error`, or `Pending` state

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n eje-monitoring

# Describe pod (shows events)
kubectl describe pod POD_NAME -n eje-monitoring

# Check logs
kubectl logs POD_NAME -n eje-monitoring

# Check previous logs (if restarting)
kubectl logs POD_NAME -n eje-monitoring --previous
```

**Common Causes**:
1. **Pending**: No resources available
   ```bash
   # Check resource requests
   kubectl describe pod POD_NAME -n eje-monitoring | grep -A 5 "Requests"

   # Solution: Scale cluster or reduce resource requests
   ```

2. **ImagePullBackOff**: Cannot pull Docker image
   ```bash
   # Check image pull policy
   kubectl describe pod POD_NAME -n eje-monitoring | grep -A 3 "Image"

   # Solution: Check image name, pull secrets, or registry access
   ```

3. **CrashLoopBackOff**: Container starts then crashes
   ```bash
   # Check logs for error message
   kubectl logs POD_NAME -n eje-monitoring --previous

   # Common: Config error, missing dependencies
   ```

4. **PVC not bound**: Storage class not available
   ```bash
   # Check PVC status
   kubectl get pvc -n eje-monitoring

   # Check storage classes
   kubectl get storageclasses

   # Solution: Create storage class or use existing one
   ```

### Metrics Not Appearing

**Symptoms**: Grafana dashboards show "No Data"

**Diagnosis Chain**:

1. **Check EJE metrics endpoint**:
   ```bash
   curl http://localhost:8000/metrics
   # Should return Prometheus-formatted metrics
   ```

   If empty/404:
   - EJE not exporting metrics
   - Wrong port
   - PrometheusExporter not initialized

2. **Check Prometheus scraping**:
   ```bash
   # Check targets
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

   # Or open Prometheus UI
   open http://localhost:9090/targets
   ```

   If target DOWN:
   - Network connectivity issue
   - Firewall blocking
   - Wrong service discovery config

3. **Check Prometheus has data**:
   ```promql
   # Query a specific metric
   eje_decisions_total
   ```

   If empty:
   - Metric not being recorded
   - Scrape failing
   - Metric name mismatch

4. **Check Grafana datasource**:
   ```bash
   # Test datasource connection
   # Grafana UI -> Configuration -> Data Sources -> Prometheus -> Test
   ```

   If failing:
   - Wrong Prometheus URL
   - Network issue
   - Prometheus not running

**Solutions by Cause**:

| Cause | Solution |
|-------|----------|
| EJE not exporting | Initialize PrometheusExporter in application |
| Wrong port | Check EJE port configuration |
| Scrape failing | Verify service discovery config |
| Network issue | Check connectivity with `curl` or `telnet` |
| Metric name wrong | Check `/metrics` endpoint for actual names |
| Grafana connection | Verify Prometheus URL in datasource settings |

### Dashboards Not Loading

**Symptoms**: Grafana shows blank/loading dashboards

**Diagnosis**:
```bash
# Check Grafana logs
kubectl logs -l app=grafana -n eje-monitoring --tail=100

# Check browser console (F12)
# Look for JavaScript errors or network failures

# Test Prometheus query directly
curl 'http://prometheus:9090/api/v1/query?query=up'
```

**Common Causes**:

1. **Slow queries**: Query timeout
   ```bash
   # Check query performance
   curl 'http://prometheus:9090/api/v1/query_range?query=...'

   # Solution: Optimize queries, add recording rules
   ```

2. **Too much data**: Loading 30 days of high-resolution data
   ```
   # Solution: Reduce time range, increase step interval
   ```

3. **Datasource misconfigured**:
   ```yaml
   # Check datasource URL
   url: http://prometheus:9090  # Not http://localhost:9090 in K8s
   ```

4. **Dashboard JSON invalid**:
   ```bash
   # Validate JSON
   cat dashboard.json | jq .
   ```

### Alerts Not Firing

**Symptoms**: Expected alerts not appearing in AlertManager

**Diagnosis Chain**:

1. **Check alert rule syntax**:
   ```bash
   promtool check rules monitoring/prometheus/alert_rules.yml
   ```

2. **Check Prometheus loaded rules**:
   ```bash
   # Open Prometheus UI
   open http://localhost:9090/rules

   # Or via API
   curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.type=="alerting")'
   ```

3. **Check alert state**:
   ```bash
   # View alerts in Prometheus
   curl http://localhost:9090/api/v1/alerts
   ```

   States:
   - `inactive`: Condition not met
   - `pending`: Condition met, waiting for `for` duration
   - `firing`: Alert active

4. **Check AlertManager received alert**:
   ```bash
   # View alerts in AlertManager
   curl http://localhost:9093/api/v2/alerts
   ```

**Common Causes**:

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Rule syntax error | `promtool check rules` fails | Fix YAML syntax |
| Condition never true | Check metric exists and has expected values | Adjust threshold or metric |
| `for` duration not met | Alert in `pending` state | Wait or reduce `for` duration |
| AlertManager not connected | Prometheus UI shows "AlertManager: 0/1 up" | Check AlertManager URL in prometheus.yml |
| Alert suppressed | Check inhibition rules | Review inhibit_rules in alertmanager.yml |
| Alert silenced | Check silences in AlertManager UI | Remove or wait for silence to expire |

### Notifications Not Received

**Symptoms**: Alerts firing but no emails/Slack/PagerDuty notifications

**Diagnosis**:

1. **Check AlertManager logs**:
   ```bash
   kubectl logs -l app=alertmanager -n eje-monitoring --tail=100 | grep -i error
   ```

2. **Check notification log**:
   ```bash
   # AlertManager UI -> Status
   open http://localhost:9093/#/status
   ```

3. **Test notification manually**:
   ```bash
   # Send test alert
   curl -X POST http://localhost:9093/api/v1/alerts -d '[{
     "labels": {"alertname":"TestAlert","severity":"warning"},
     "annotations": {"summary":"Test notification"}
   }]'
   ```

**Common Causes**:

1. **SMTP failure** (Email):
   ```bash
   # Check logs for SMTP errors
   kubectl logs alertmanager-0 | grep -i smtp

   # Common issues:
   # - Wrong SMTP server/port
   # - Invalid credentials
   # - TLS/SSL configuration
   # - Firewall blocking port 587/465
   ```

2. **Slack webhook failure**:
   ```bash
   # Test webhook directly
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_SLACK_WEBHOOK_URL

   # If fails: Invalid webhook URL or expired
   ```

3. **PagerDuty failure**:
   ```bash
   # Check service key
   # Common: Wrong integration key or service not configured
   ```

4. **Routing issue**:
   ```yaml
   # Alert doesn't match any route
   # Solution: Add catch-all route or fix label matching
   route:
     receiver: 'default'  # Catch-all
   ```

### High Memory Usage

**Symptoms**: Prometheus/Grafana OOMKilled or slow

**Diagnosis**:
```bash
# Check memory usage
kubectl top pods -n eje-monitoring

# Prometheus: Check active series
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.numSeries'

# Grafana: Check query count
# Look for slow queries in logs
```

**Solutions**:

1. **Prometheus**:
   - Reduce retention: `--storage.tsdb.retention.time=14d`
   - Reduce cardinality: Drop high-cardinality metrics
   - Add memory: Increase resource limits
   - Shard: Use multiple Prometheus instances

2. **Grafana**:
   - Enable query caching
   - Limit concurrent queries
   - Optimize dashboard queries
   - Increase memory limits

### Trace Not Appearing in Jaeger

**Symptoms**: Traces not visible in Jaeger UI

**Diagnosis**:

1. **Check EJE tracing configured**:
   ```python
   # Verify tracing initialized
   from ejc.monitoring import initialize_tracing
   initialize_tracing(jaeger_endpoint="http://jaeger:14268/api/traces")
   ```

2. **Check Jaeger collector**:
   ```bash
   # Collector health
   curl http://localhost:14269/

   # Check logs
   kubectl logs -l app=jaeger -n eje-monitoring
   ```

3. **Check sampling**:
   ```python
   # Verify sampling rate
   initialize_tracing(sampling_rate=1.0)  # Sample all traces
   ```

4. **Check storage**:
   ```bash
   # Elasticsearch health (if used)
   curl http://elasticsearch:9200/_cluster/health
   ```

**Common Causes**:
- Sampling rate too low (traces dropped)
- Jaeger endpoint wrong
- Storage full
- Trace too old (outside retention window)

### Permission Denied Errors

**Symptoms**: Containers cannot write to volumes

**Docker Compose**:
```bash
# Fix volume permissions
chmod -R 777 ./data/prometheus
chmod -R 777 ./data/grafana
chmod -R 777 ./data/alertmanager
```

**Kubernetes**:
```yaml
# Add security context
securityContext:
  fsGroup: 65534
  runAsUser: 65534
```

## Performance Issues

### Slow Dashboard Loading

**Diagnosis**:
```promql
# Check query duration
rate(prometheus_engine_query_duration_seconds_sum[5m])
/
rate(prometheus_engine_query_duration_seconds_count[5m])
```

**Solutions**:
1. Add recording rules for complex queries
2. Reduce time range
3. Increase Prometheus resources
4. Enable query result caching in Grafana

### High Disk Usage

**Diagnosis**:
```bash
# Check Prometheus data size
du -sh /prometheus/data

# Check retention settings
curl http://localhost:9090/api/v1/status/runtimeinfo | jq .data.storageRetention
```

**Solutions**:
1. Reduce retention time
2. Add size-based retention
3. Clean up old data: `rm -rf /prometheus/data/01*`
4. Add more storage

## Tools and Commands

### Prometheus Tools

```bash
# Validate config
promtool check config prometheus.yml

# Validate rules
promtool check rules alert_rules.yml

# Query from CLI
promtool query instant http://localhost:9090 'up'

# Check metrics
promtool query instant http://localhost:9090 'eje_decisions_total'
```

### AlertManager Tools

```bash
# Validate config
amtool check-config alertmanager.yml

# List alerts
amtool --alertmanager.url=http://localhost:9093 alert query

# Add silence
amtool --alertmanager.url=http://localhost:9093 silence add \
  alertname=HighMemory --duration=2h

# List silences
amtool --alertmanager.url=http://localhost:9093 silence query
```

### Kubernetes Tools

```bash
# Get all monitoring resources
kubectl get all -n eje-monitoring

# Port forward for local access
kubectl port-forward -n eje-monitoring svc/prometheus 9090:9090

# Execute command in pod
kubectl exec -it prometheus-0 -n eje-monitoring -- /bin/sh

# Copy file from pod
kubectl cp eje-monitoring/prometheus-0:/prometheus/data ./backup

# View resource usage
kubectl top pods -n eje-monitoring

# View events
kubectl get events -n eje-monitoring --sort-by='.lastTimestamp'
```

## Getting Help

### 1. Check Logs

**Docker Compose**:
```bash
docker-compose -f docker-compose.monitoring.yml logs -f --tail=100 SERVICE_NAME
```

**Kubernetes**:
```bash
kubectl logs -f POD_NAME -n eje-monitoring --tail=100
```

### 2. Check Documentation

- [Prometheus Troubleshooting](https://prometheus.io/docs/prometheus/latest/troubleshooting/)
- [Grafana Troubleshooting](https://grafana.com/docs/grafana/latest/troubleshooting/)
- [Jaeger Troubleshooting](https://www.jaegertracing.io/docs/latest/troubleshooting/)
- [EJE Runbooks](./runbooks.md)

### 3. Contact Support

- GitHub Issues: https://github.com/eleanor-project/eje/issues
- On-call: Slack #eje-oncall
- Email: eje-ops@example.com

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
