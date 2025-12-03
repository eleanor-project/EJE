# EJE Grafana Dashboards

Pre-configured Grafana dashboards for comprehensive EJE monitoring and observability.

## 📊 Available Dashboards

### 1. EJE Overview Dashboard
**UID**: `eje-overview`
**Purpose**: High-level system health, throughput, and key metrics

**Panels**:
- Decision Requests/sec (real-time throughput)
- Decision Latency P95 (performance)
- Decision Throughput (success vs errors)
- Decision Latency Percentiles (P50, P95, P99)
- Verdict Distribution (pie chart)
- Success Rate (gauge)
- Memory Usage (gauge)

**Use Cases**:
- System health monitoring
- Quick performance overview
- Operational dashboards
- Status displays

### 2. Critic Performance Dashboard
**UID**: `eje-critic-performance`
**Purpose**: Per-critic execution metrics, latency distribution, error rates

**Panels**:
- Critic Execution Latency P95 by Critic
- Critic Execution Rate by Critic
- Critic Failures (1h) by Critic
- Critic Execution Distribution (donut chart)
- Average Critic Confidence by Critic
- Critic Failures by Type (table)

**Use Cases**:
- Identifying slow critics
- Debugging critic failures
- Optimizing critic performance
- Load balancing

**Variables**:
- `critic`: Filter by specific critic name(s)

### 3. Decision Analysis Dashboard
**UID**: `eje-decision-analysis`
**Purpose**: Verdict patterns, precedent usage, aggregation insights

**Panels**:
- Verdict Distribution Over Time (stacked bars)
- Average Decision Confidence (gauge)
- Precedent Matches (1h) (stat)
- Precedent Usage Rate
- Critic Conflict Detection Rate
- Policy Flags Distribution (pie chart)
- Critic Agreement Ratio
- Top Precedents Used (1h) (table)

**Use Cases**:
- Understanding decision patterns
- Analyzing precedent effectiveness
- Detecting anomalies in verdicts
- Governance reporting

### 4. Alerting Dashboard
**UID**: `eje-alerting`
**Purpose**: Active alerts, alert trends, system health warnings

**Panels**:
- Active Alerts (stat)
- Critical Alerts (stat)
- Warning Alerts (stat)
- Alerts (24h) (stat)
- Active Alerts (table)
- Alert Trend by Severity
- Top Alerts (24h) (donut chart)

**Use Cases**:
- Alert management
- Incident response
- System health monitoring
- SLA tracking

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start Grafana with pre-configured dashboards
cd monitoring
docker-compose up -d grafana

# Access Grafana
open http://localhost:3000
# Default credentials: admin / admin
```

### Option 2: Manual Import

```bash
# Set environment variables
export GRAFANA_URL=http://localhost:3000
export GRAFANA_API_KEY=your-api-key

# Import all dashboards
python3 monitoring/grafana/import_dashboards.py import

# Or import specific dashboard
python3 monitoring/grafana/import_dashboards.py import --dir monitoring/grafana/dashboards
```

### Option 3: Kubernetes Deployment

```bash
# Deploy with Helm (includes Grafana provisioning)
helm install eje ./deploy/helm/eje \
  --set grafana.enabled=true \
  --set grafana.adminPassword=admin

# Or use kubectl with ConfigMaps
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/ \
  -n monitoring

kubectl apply -f deploy/k8s/monitoring/
```

## 📦 Dashboard Structure

```
monitoring/grafana/
├── dashboards/               # Dashboard JSON files
│   ├── eje-overview.json
│   ├── critic-performance.json
│   ├── decision-analysis.json
│   └── alerting.json
├── provisioning/             # Grafana provisioning configs
│   ├── datasources/
│   │   └── prometheus.yml    # Prometheus datasource
│   └── dashboards/
│       └── eje-dashboards.yml # Dashboard provider
├── import_dashboards.py      # Import/export script
└── README.md                 # This file
```

## 🔧 Configuration

### Datasource Configuration

Edit `provisioning/datasources/prometheus.yml` to configure Prometheus:

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090  # Update for your environment
    isDefault: true
```

### Dashboard Provisioning

Dashboards are automatically loaded from `dashboards/` directory when Grafana starts with provisioning enabled.

To enable provisioning:

```bash
# Set Grafana environment variable
export GF_PATHS_PROVISIONING=/etc/grafana/provisioning

# Or in grafana.ini
[paths]
provisioning = /etc/grafana/provisioning
```

## 📥 Import/Export Dashboards

### Import Dashboards

```bash
# Import all dashboards
./monitoring/grafana/import_dashboards.py import

# Import with custom URL and API key
./monitoring/grafana/import_dashboards.py import \
  --url http://grafana.example.com \
  --api-key eyJrIjoiVGVzdCJ9

# Import from specific directory
./monitoring/grafana/import_dashboards.py import \
  --dir ./custom-dashboards/
```

### Export Dashboards

```bash
# Export all dashboards
./monitoring/grafana/import_dashboards.py export

# Export to custom directory
./monitoring/grafana/import_dashboards.py export \
  --dir ./backup-dashboards/
```

## 🎨 Customization

### Modifying Dashboards

1. Edit dashboard JSON files in `dashboards/` directory
2. Or use Grafana UI to modify dashboards
3. Export modified dashboards using the export script
4. Commit changes to version control

### Adding New Panels

Dashboard JSON structure:

```json
{
  "panels": [
    {
      "id": 1,
      "title": "My Panel",
      "type": "timeseries",
      "targets": [
        {
          "expr": "eje_my_metric",
          "legendFormat": "{{label}}"
        }
      ]
    }
  ]
}
```

### Variables and Templating

Add dashboard variables for filtering:

```json
{
  "templating": {
    "list": [
      {
        "name": "critic",
        "type": "query",
        "query": "label_values(eje_critic_executions_total, critic_name)",
        "includeAll": true,
        "multi": true
      }
    ]
  }
}
```

## 📱 Mobile Responsiveness

All dashboards are designed with mobile-responsive layouts:

- Panels adjust to screen size
- Touch-friendly interactions
- Optimized for tablets and mobile devices
- Drill-down capabilities work on mobile

## 🔍 Drill-Down Capabilities

### Panel Links

Dashboards support drill-down:

1. Click on panel title → "View"
2. Click on legend items to filter
3. Use time range selector for zoom
4. Click on table rows for details

### Dashboard Links

Navigate between dashboards:

- Overview → Critic Performance (click on critic metrics)
- Decision Analysis → Alerting (click on anomalies)
- Alerting → Overview (click on alert context)

## 🎯 Best Practices

### Dashboard Usage

1. **Start with Overview**: Get system health at a glance
2. **Drill into Critic Performance**: Identify bottlenecks
3. **Analyze Decisions**: Understand patterns and trends
4. **Monitor Alerts**: Stay on top of issues

### Performance Optimization

1. **Use appropriate time ranges**: Shorter ranges = faster queries
2. **Limit data points**: Use `$__interval` variable
3. **Cache queries**: Enable query result caching
4. **Use recording rules**: Pre-compute complex queries

### Alerting Integration

Configure Grafana alerts on panels:

```json
{
  "alert": {
    "name": "High Error Rate",
    "conditions": [
      {
        "type": "query",
        "query": {
          "params": ["A", "5m", "now"]
        },
        "reducer": {
          "type": "avg"
        },
        "evaluator": {
          "type": "gt",
          "params": [0.05]
        }
      }
    ]
  }
}
```

## 🐛 Troubleshooting

### Dashboards Not Loading

```bash
# Check Grafana logs
docker logs grafana

# Verify provisioning
ls -la /etc/grafana/provisioning/dashboards/

# Test API connection
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  $GRAFANA_URL/api/search
```

### Missing Metrics

```bash
# Verify Prometheus connection
curl $GRAFANA_URL/api/datasources/proxy/1/api/v1/label/__name__/values

# Check metric names
promtool query instant http://prometheus:9090 '{__name__=~"eje_.*"}'
```

### Dashboard JSON Errors

```bash
# Validate JSON
python3 -m json.tool dashboard.json

# Check dashboard schema
./import_dashboards.py import --validate-only
```

## 📚 Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [EJE Metrics Reference](../../docs/observability/metrics.md)

## 🤝 Contributing

To contribute new dashboards:

1. Create dashboard in Grafana UI
2. Export using export script
3. Add to `dashboards/` directory
4. Update this README
5. Submit pull request

## 📝 License

Part of the ELEANOR Judicial Engine (EJE) project.
