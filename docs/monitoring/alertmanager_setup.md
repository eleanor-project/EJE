# AlertManager Setup Guide

Complete guide for setting up and configuring Prometheus AlertManager for EJE.

## Overview

AlertManager handles alerts sent by Prometheus, including:
- Alert deduplication and grouping
- Routing to appropriate channels (email, Slack, PagerDuty)
- Silencing and inhibition rules
- Alert status tracking

## Quick Start

### Option 1: Docker Compose (Recommended for Development)

```bash
# Start AlertManager with Prometheus
docker-compose up -d alertmanager prometheus

# Verify AlertManager is running
curl http://localhost:9093/-/healthy

# Open AlertManager UI
open http://localhost:9093
```

### Option 2: Kubernetes Deployment

```bash
# Apply AlertManager configuration
kubectl apply -f monitoring/kubernetes/alertmanager/

# Verify deployment
kubectl get pods -l app=alertmanager
kubectl logs -l app=alertmanager

# Access AlertManager UI
kubectl port-forward svc/alertmanager 9093:9093
open http://localhost:9093
```

### Option 3: Binary Installation

```bash
# Download AlertManager
ALERTMANAGER_VERSION="0.26.0"
wget https://github.com/prometheus/alertmanager/releases/download/v${ALERTMANAGER_VERSION}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz

# Extract
tar xvfz alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz
cd alertmanager-${ALERTMANAGER_VERSION}.linux-amd64

# Start AlertManager
./alertmanager --config.file=../../monitoring/alertmanager/alertmanager.yml
```

## Configuration

### Environment Variables

Set these before starting AlertManager:

```bash
# SMTP Configuration
export SMTP_PASSWORD="your-smtp-password"

# Slack Webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# PagerDuty Integration Key
export PAGERDUTY_SERVICE_KEY="your-pagerduty-service-key"
```

### Configuration File Structure

The main configuration file is `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  # Global settings (SMTP, Slack, PagerDuty)

templates:
  # Email/Slack notification templates

route:
  # Alert routing configuration

inhibit_rules:
  # Rules to suppress redundant alerts

receivers:
  # Notification channel definitions
```

### Alert Routing

Alerts are routed based on labels:

```yaml
routes:
  # Critical alerts -> PagerDuty + Slack
  - match:
      severity: critical
    receiver: 'eje-critical-pagerduty'

  # Warning alerts -> Slack
  - match:
      severity: warning
    receiver: 'eje-warning-slack'

  # Info alerts -> Email
  - match:
      severity: info
    receiver: 'eje-info-email'
```

## Notification Channels

### Email Setup

1. **Configure SMTP settings in `alertmanager.yml`**:
   ```yaml
   global:
     smtp_smarthost: 'smtp.gmail.com:587'
     smtp_from: 'eje-alerts@example.com'
     smtp_auth_username: 'eje-alerts@example.com'
     smtp_auth_password: '${SMTP_PASSWORD}'
     smtp_require_tls: true
   ```

2. **Add email receiver**:
   ```yaml
   receivers:
     - name: 'eje-ops-team'
       email_configs:
         - to: 'ops@example.com'
           headers:
             Subject: '[EJE] {{ .GroupLabels.severity | toUpper }}: {{ .GroupLabels.alertname }}'
           html: '{{ template "email.html" . }}'
   ```

3. **Test email**:
   ```bash
   # Send test alert
   curl -X POST http://alertmanager:9093/api/v1/alerts -d '[{
     "labels": {"alertname":"TestAlert","severity":"warning"},
     "annotations": {"summary":"Test email notification"}
   }]'
   ```

### Slack Setup

1. **Create Slack Incoming Webhook**:
   - Go to https://api.slack.com/apps
   - Create new app -> Incoming Webhooks
   - Activate and add to workspace
   - Copy webhook URL

2. **Configure Slack receiver**:
   ```yaml
   global:
     slack_api_url: '${SLACK_WEBHOOK_URL}'

   receivers:
     - name: 'eje-critical-slack'
       slack_configs:
         - channel: '#eje-critical'
           username: 'EJE AlertManager'
           icon_emoji: ':rotating_light:'
           title: ':rotating_light: CRITICAL: {{ .GroupLabels.alertname }}'
           text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
           color: 'danger'
           send_resolved: true
   ```

3. **Test Slack notification**:
   ```bash
   curl -X POST http://alertmanager:9093/api/v1/alerts -d '[{
     "labels": {"alertname":"TestAlert","severity":"critical"},
     "annotations": {"summary":"Test Slack notification"}
   }]'
   ```

### PagerDuty Setup

1. **Get PagerDuty Integration Key**:
   - Log into PagerDuty
   - Services -> Select service -> Integrations tab
   - Add integration -> Prometheus
   - Copy Integration Key

2. **Configure PagerDuty receiver**:
   ```yaml
   receivers:
     - name: 'eje-critical-pagerduty'
       pagerduty_configs:
         - service_key: '${PAGERDUTY_SERVICE_KEY}'
           description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
           details:
             severity: '{{ .GroupLabels.severity }}'
             summary: '{{ .CommonAnnotations.summary }}'
             runbook: '{{ .CommonAnnotations.runbook }}'
           client: 'EJE AlertManager'
   ```

3. **Test PagerDuty integration**:
   ```bash
   curl -X POST http://alertmanager:9093/api/v1/alerts -d '[{
     "labels": {"alertname":"TestAlert","severity":"critical"},
     "annotations": {"summary":"Test PagerDuty notification"}
   }]'
   ```

## Alert Management

### Viewing Active Alerts

**Web UI**:
```bash
# Open AlertManager UI
open http://localhost:9093
```

**API**:
```bash
# Get all alerts
curl http://alertmanager:9093/api/v2/alerts

# Get alerts by severity
curl http://alertmanager:9093/api/v2/alerts?filter=severity=critical
```

**CLI (amtool)**:
```bash
# Install amtool
go install github.com/prometheus/alertmanager/cmd/amtool@latest

# List alerts
amtool --alertmanager.url=http://localhost:9093 alert query

# List critical alerts
amtool --alertmanager.url=http://localhost:9093 alert query severity=critical
```

### Silencing Alerts

**Web UI**:
1. Open http://localhost:9093
2. Click "Silences" tab
3. Click "New Silence"
4. Fill in matchers and duration
5. Click "Create"

**API**:
```bash
# Create silence
curl -X POST http://alertmanager:9093/api/v2/silences -d '{
  "matchers": [
    {"name": "alertname", "value": "HighCriticFailureRate", "isRegex": false},
    {"name": "critic_name", "value": "bias_critic", "isRegex": false}
  ],
  "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "endsAt": "'$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%SZ)'",
  "createdBy": "ops-team",
  "comment": "Maintenance window for critic upgrade"
}'
```

**CLI (amtool)**:
```bash
# Silence alert for 2 hours
amtool --alertmanager.url=http://localhost:9093 silence add \
  alertname=HighCriticFailureRate \
  critic_name=bias_critic \
  --duration=2h \
  --comment="Maintenance window"

# List silences
amtool --alertmanager.url=http://localhost:9093 silence query

# Expire silence
amtool --alertmanager.url=http://localhost:9093 silence expire SILENCE_ID
```

### Alert Inhibition

Inhibition rules automatically suppress alerts when related alerts are firing:

```yaml
inhibit_rules:
  # Suppress warning if critical is firing
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['component', 'instance']

  # Suppress all alerts if service is down
  - source_match:
      alertname: 'EJEServiceDown'
    target_match_re:
      alertname: '.*'
    equal: ['instance']
```

## Testing

### Test Alert Rules

```bash
# Check alert rule syntax
promtool check rules monitoring/prometheus/alert_rules.yml

# Test alert rule evaluation
promtool test rules monitoring/prometheus/alert_rules_test.yml
```

### Send Test Alerts

```bash
# Function to send test alert
send_test_alert() {
  local severity=$1
  local alertname=$2
  local summary=$3

  curl -X POST http://alertmanager:9093/api/v1/alerts -H "Content-Type: application/json" -d "[{
    \"labels\": {
      \"alertname\": \"${alertname}\",
      \"severity\": \"${severity}\",
      \"component\": \"test\",
      \"instance\": \"test-instance\"
    },
    \"annotations\": {
      \"summary\": \"${summary}\",
      \"description\": \"Test alert description\",
      \"impact\": \"Test impact\",
      \"action\": \"No action needed - this is a test\",
      \"runbook\": \"https://docs.eje.example.com/runbooks/test\",
      \"dashboard\": \"http://grafana:3000/d/test\"
    },
    \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"endsAt\": \"$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)\"
  }]"
}

# Test critical alert
send_test_alert "critical" "TestCriticalAlert" "Testing critical alert path"

# Test warning alert
send_test_alert "warning" "TestWarningAlert" "Testing warning alert path"

# Test info alert
send_test_alert "info" "TestInfoAlert" "Testing info alert path"
```

### Verify Alert Routing

1. **Check AlertManager logs**:
   ```bash
   # Docker
   docker logs alertmanager

   # Kubernetes
   kubectl logs -l app=alertmanager --tail=50

   # Binary
   tail -f /var/log/alertmanager.log
   ```

2. **Verify notifications received**:
   - Check email inbox
   - Check Slack channels
   - Check PagerDuty incidents

3. **Test alert deduplication**:
   ```bash
   # Send same alert multiple times
   for i in {1..5}; do
     send_test_alert "warning" "DuplicateTest" "Testing deduplication"
     sleep 2
   done

   # Should only see one notification
   ```

## Deployment

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  alertmanager:
    image: prom/alertmanager:v0.26.0
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - ./monitoring/alertmanager/templates:/etc/alertmanager/templates
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
    environment:
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
      - PAGERDUTY_SERVICE_KEY=${PAGERDUTY_SERVICE_KEY}
    networks:
      - eje-network

  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    depends_on:
      - alertmanager
    networks:
      - eje-network

volumes:
  alertmanager_data:
  prometheus_data:

networks:
  eje-network:
```

Start services:
```bash
docker-compose up -d alertmanager prometheus
```

### Kubernetes

Create AlertManager deployment:

```yaml
# monitoring/kubernetes/alertmanager/deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
data:
  alertmanager.yml: |
    # Include full alertmanager.yml content here
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-templates
data:
  email.tmpl: |
    # Include email.tmpl content here
---
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-secrets
type: Opaque
stringData:
  smtp-password: "your-smtp-password"
  slack-webhook-url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  pagerduty-service-key: "your-pagerduty-key"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alertmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alertmanager
  template:
    metadata:
      labels:
        app: alertmanager
    spec:
      containers:
      - name: alertmanager
        image: prom/alertmanager:v0.26.0
        ports:
        - containerPort: 9093
          name: web
        volumeMounts:
        - name: config
          mountPath: /etc/alertmanager
        - name: templates
          mountPath: /etc/alertmanager/templates
        - name: storage
          mountPath: /alertmanager
        env:
        - name: SMTP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: alertmanager-secrets
              key: smtp-password
        - name: SLACK_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: alertmanager-secrets
              key: slack-webhook-url
        - name: PAGERDUTY_SERVICE_KEY
          valueFrom:
            secretKeyRef:
              name: alertmanager-secrets
              key: pagerduty-service-key
        args:
          - '--config.file=/etc/alertmanager/alertmanager.yml'
          - '--storage.path=/alertmanager'
          - '--web.external-url=http://alertmanager:9093'
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
      volumes:
      - name: config
        configMap:
          name: alertmanager-config
      - name: templates
        configMap:
          name: alertmanager-templates
      - name: storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager
spec:
  selector:
    app: alertmanager
  ports:
  - port: 9093
    targetPort: 9093
    name: web
  type: ClusterIP
```

Deploy:
```bash
kubectl apply -f monitoring/kubernetes/alertmanager/deployment.yaml
```

## Monitoring AlertManager

### Key Metrics

```promql
# Alert delivery success rate
rate(alertmanager_notifications_total{integration="email"}[5m])
/
rate(alertmanager_notifications_total[5m])

# Alerts currently firing
sum(ALERTS{alertstate="firing"})

# AlertManager uptime
up{job="alertmanager"}

# Notification queue size
alertmanager_notification_queue_length
```

### Health Checks

```bash
# Check AlertManager health
curl http://alertmanager:9093/-/healthy

# Check AlertManager readiness
curl http://alertmanager:9093/-/ready

# Get AlertManager status
curl http://alertmanager:9093/api/v2/status
```

## Troubleshooting

### Alerts Not Firing

1. **Check Prometheus is evaluating rules**:
   ```bash
   curl http://prometheus:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.type=="alerting")'
   ```

2. **Verify AlertManager connection**:
   ```bash
   curl http://prometheus:9090/api/v1/alertmanagers
   ```

3. **Check alert rule syntax**:
   ```bash
   promtool check rules monitoring/prometheus/alert_rules.yml
   ```

### Notifications Not Received

1. **Check AlertManager logs**:
   ```bash
   kubectl logs -l app=alertmanager --tail=100
   ```

2. **Verify receiver configuration**:
   ```bash
   # Check AlertManager config
   curl http://alertmanager:9093/api/v2/status | jq '.config'
   ```

3. **Test notification channels**:
   ```bash
   # Send test alert
   send_test_alert "critical" "NotificationTest" "Test notification delivery"
   ```

4. **Common issues**:
   - SMTP authentication failed -> Check credentials
   - Slack webhook 404 -> Verify webhook URL
   - PagerDuty timeout -> Check integration key

### Duplicate Notifications

1. **Check grouping configuration**:
   ```yaml
   route:
     group_by: ['alertname', 'severity', 'instance']
     group_wait: 30s
   ```

2. **Verify repeat_interval**:
   ```yaml
   route:
     repeat_interval: 4h  # Don't repeat more frequently
   ```

3. **Check for multiple receivers**:
   - Ensure `continue: false` when not needed
   - Review route hierarchy

### Alerts Stuck in Pending

1. **Check `for` duration**:
   ```yaml
   # Alert must fire for this duration before sending
   for: 5m
   ```

2. **Verify metric exists**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=METRIC_NAME'
   ```

## Best Practices

### Alert Design
- Keep alert rules simple and focused
- Include actionable information in annotations
- Link to runbooks for every alert
- Set appropriate `for` durations to avoid flapping

### Routing
- Route by severity first, then by component
- Use `continue: true` sparingly
- Test routing with test alerts
- Document routing decisions

### Notification Channels
- Critical alerts -> PagerDuty
- Warnings -> Slack
- Info -> Email
- Use appropriate channels per team

### Silence Management
- Always add comments explaining why
- Use minimum necessary duration
- Review and clean up expired silences
- Document planned silences in advance

### Maintenance
- Review and update alerts monthly
- Test notification channels weekly
- Keep runbooks up to date
- Monitor AlertManager metrics

## Resources

- [Prometheus AlertManager Docs](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alert Rule Best Practices](https://prometheus.io/docs/practices/alerting/)
- [AlertManager API](https://prometheus.io/docs/alerting/latest/clients/)
- [EJE Runbooks](./runbooks.md)

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
**AlertManager Version**: 0.26.0+
