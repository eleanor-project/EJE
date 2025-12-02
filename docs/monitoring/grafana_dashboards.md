# Grafana Dashboards Guide

Complete guide for EJE Grafana dashboards including setup, deployment, and customization.

## Overview

The EJE monitoring solution includes 4 pre-configured Grafana dashboards:

1. **EJE Overview** - System health and throughput
2. **Critic Performance** - Critic-specific metrics and latency
3. **Decision Analysis** - Verdict patterns and conflicts
4. **Alerting** - Active alerts and error trends

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start Grafana with Prometheus
docker-compose up -d grafana prometheus

# Wait for services to start
sleep 10

# Dashboards auto-load via provisioning
open http://localhost:3000
```

**Default Credentials**:
- Username: `admin`
- Password: `admin` (change on first login)

### Option 2: Manual Import

```bash
# Get your Grafana API key
# 1. Login to Grafana
# 2. Go to Configuration -> API Keys
# 3. Create new key with Editor role

# Import all dashboards
./scripts/monitoring/import_dashboards.sh \
    http://localhost:3000 \
    YOUR_API_KEY
```

### Option 3: Manual UI Import

1. Open Grafana: http://localhost:3000
2. Go to Dashboards -> Import
3. Click "Upload JSON file"
4. Select dashboard from `monitoring/grafana/dashboards/`
5. Choose Prometheus datasource
6. Click Import

## Dashboard Details

### 1. EJE Overview Dashboard

**Purpose**: High-level system health and performance monitoring

**Key Panels**:
- Decision Throughput (req/sec)
- Error Rate (%)
- Average Confidence
- Active Operations
- Decision Rate by Verdict (timeseries)
- Decision Latency Percentiles (P50, P95, P99)
- Verdict Distribution (pie chart)
- Top Critics by Activity (table)
- Memory Usage

**Use Cases**:
- Quick health check
- Capacity planning
- Performance trends
- Operational overview

**Refresh**: 10 seconds

---

### 2. Critic Performance Dashboard

**Purpose**: Detailed critic execution metrics and troubleshooting

**Key Panels**:
- Critic Execution Latency (P95) by critic
- Critic Execution Rate (success)
- Critic Failure Rate
- Critic Confidence Scores (table)
- Active Critic Executions
- Critic Verdict Distribution
- Critic Failures (last hour)

**Features**:
- Variable selector for filtering by critic
- Sortable tables
- Drill-down capabilities

**Use Cases**:
- Identifying slow critics
- Troubleshooting failures
- Confidence analysis
- Performance optimization

**Refresh**: 10 seconds

---

### 3. Decision Analysis Dashboard

**Purpose**: Understanding decision patterns and conflicts

**Key Panels**:
- Decision Verdicts (24h pie chart)
- Verdict Trends (percentage over time)
- Decision Confidence Over Time
- Conflicts by Type
- Conflicts (last hour) table
- Overrides by Type
- Human Review Required Rate
- Current Verdict Distribution

**Use Cases**:
- Policy effectiveness analysis
- Conflict detection
- Audit and compliance
- Decision pattern analysis

**Refresh**: 10 seconds

---

### 4. Alerting Dashboard

**Purpose**: Real-time alert monitoring and incident tracking

**Key Panels**:
- Error Rate by Type (with alert threshold)
- Critic Failure Rate (with alert threshold)
- Decision Latency P95 (with alert threshold)
- Memory Usage (with alert threshold)
- Conflict Rate (with alert threshold)
- Recent Error Summary (30m table)
- Fallback Activations
- Retry Attempts

**Alert Thresholds Visualized**:
- Error Rate > 0.1/sec (red line)
- Critic Failure > 5% (red line)
- P95 Latency > 5s (red line)
- Memory > 2GB (red line)
- Conflict Rate > 30% (red line)

**Use Cases**:
- Incident response
- Alert validation
- Root cause analysis
- Operational health

**Refresh**: 10 seconds

---

## Deployment

### Kubernetes

```yaml
# grafana-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        volumeMounts:
        - name: dashboards
          mountPath: /etc/grafana/provisioning/dashboards
          readOnly: true
        - name: dashboard-files
          mountPath: /var/lib/grafana/dashboards
          readOnly: true
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
          readOnly: true
      volumes:
      - name: dashboards
        configMap:
          name: grafana-dashboard-config
      - name: dashboard-files
        configMap:
          name: eje-dashboards
      - name: datasources
        configMap:
          name: grafana-datasources
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
  type: LoadBalancer
```

Create ConfigMaps:

```bash
# Provisioning config
kubectl create configmap grafana-dashboard-config \
    --from-file=monitoring/grafana/provisioning/dashboards.yml

# Datasource config
kubectl create configmap grafana-datasources \
    --from-file=monitoring/grafana/provisioning/datasources.yml

# Dashboard files
kubectl create configmap eje-dashboards \
    --from-file=monitoring/grafana/dashboards/
```

### Docker Compose

```yaml
version: '3.8'

services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
      - ./monitoring/grafana/provisioning/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

volumes:
  grafana_data:
  prometheus_data:
```

## Customization

### Modifying Dashboards

1. **Edit in Grafana UI**:
   - Make changes in the UI
   - Click "Save dashboard"
   - Export: Settings -> JSON Model -> Copy to clipboard
   - Save to `monitoring/grafana/dashboards/`

2. **Edit JSON directly**:
   ```bash
   vim monitoring/grafana/dashboards/eje_overview.json
   # Import using script or UI
   ```

### Adding Custom Panels

Example: Adding a custom metric panel

```json
{
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "your_custom_metric",
      "legendFormat": "{{label_name}}",
      "refId": "A"
    }
  ],
  "title": "My Custom Metric",
  "type": "timeseries"
}
```

### Creating Dashboard Variables

Variables allow filtering (e.g., by critic, environment):

```json
{
  "templating": {
    "list": [
      {
        "name": "environment",
        "type": "query",
        "datasource": "Prometheus",
        "query": "label_values(eje_decisions_total, environment)",
        "multi": true,
        "includeAll": true
      }
    ]
  }
}
```

Use in queries: `eje_decisions_total{environment=~"$environment"}`

## Export & Backup

### Export Current Dashboards

```bash
# Export all EJE dashboards
./scripts/monitoring/export_dashboards.sh \
    http://localhost:3000 \
    YOUR_API_KEY
```

### Backup to Git

```bash
# Dashboards are in git
git add monitoring/grafana/dashboards/
git commit -m "Update Grafana dashboards"
git push
```

### Version Control Best Practices

1. Keep dashboard JSON in git
2. Use semantic versioning in dashboard titles
3. Document breaking changes
4. Test imports before committing

## Troubleshooting

### Dashboard Not Loading

**Problem**: Dashboard shows "No data"

**Solutions**:
1. Check Prometheus is scraping EJE:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```
2. Verify EJE metrics endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```
3. Check datasource configuration in Grafana

### Metrics Not Appearing

**Problem**: Some panels show "N/A"

**Solutions**:
1. Check metric exists:
   ```bash
   curl http://localhost:8000/metrics | grep metric_name
   ```
2. Verify time range (metrics need data)
3. Check PromQL query syntax

### Import Failures

**Problem**: Dashboard import fails

**Solutions**:
1. Verify API key has Editor role
2. Check Grafana URL is correct
3. Validate JSON syntax:
   ```bash
   jq . dashboard.json
   ```
4. Check Grafana logs:
   ```bash
   docker logs grafana
   ```

### Performance Issues

**Problem**: Dashboards loading slowly

**Solutions**:
1. Reduce time range
2. Increase refresh interval
3. Optimize queries (use recording rules)
4. Check Prometheus performance
5. Add query result caching

## Alert Integration

Dashboards can link to AlertManager:

```yaml
# In dashboard JSON
"links": [
  {
    "title": "AlertManager",
    "url": "http://alertmanager:9093/#/alerts",
    "type": "link"
  }
]
```

## Best Practices

### Dashboard Design
- Keep panels focused (one metric per panel)
- Use consistent colors (green=good, red=bad)
- Include legends with units
- Add descriptions to panels
- Group related panels together

### Query Optimization
- Use rate() for counters
- Use irate() for spiky data
- Pre-aggregate with recording rules
- Limit cardinality
- Use appropriate time ranges

### Maintenance
- Review dashboards monthly
- Remove unused panels
- Update thresholds based on SLOs
- Test dashboard imports
- Document custom modifications

## Mobile Responsiveness

Dashboards are mobile-responsive:
- Panels auto-resize
- Touch-friendly controls
- Simplified layout on small screens
- Single-column view on mobile

## Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)
- [Panel Types](https://grafana.com/docs/grafana/latest/panels/)

## Support

For issues or questions:
- Check Grafana logs: `docker logs grafana`
- EJE Documentation: `docs/`
- GitHub Issues: https://github.com/eleanor-project/eje/issues

---

**Last Updated**: 2025-12-01
**Dashboard Version**: 1.0.0
**Grafana Version**: 9.0.0+
