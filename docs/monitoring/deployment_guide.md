# EJE Monitoring Stack Deployment Guide

Complete guide for deploying the EJE monitoring infrastructure in local and production environments.

## Overview

The EJE monitoring stack includes:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notifications
- **Jaeger**: Distributed tracing
- **Node Exporter**: System metrics
- **Elasticsearch**: Trace storage (production)

## Prerequisites

### Local Development
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB free disk space

### Production (Kubernetes)
- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- StorageClass for persistent volumes
- cert-manager (optional, for TLS)
- 16GB RAM minimum per node
- 100GB+ storage

## Local Deployment (Docker Compose)

### Quick Start

```bash
# Clone repository
git clone https://github.com/eleanor-project/eje.git
cd eje

# Set environment variables (optional)
export SMTP_PASSWORD="your-smtp-password"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export PAGERDUTY_SERVICE_KEY="your-pagerduty-key"

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose -f docker-compose.monitoring.yml ps

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f
```

### Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | None |
| Grafana | http://localhost:3000 | admin / admin |
| AlertManager | http://localhost:9093 | None |
| Jaeger UI | http://localhost:16686 | None |
| Node Exporter | http://localhost:9100 | None |

### Configuration

#### Custom Prometheus Configuration

Edit `monitoring/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s  # Adjust scrape frequency
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

#### Custom Grafana Settings

Edit `docker-compose.monitoring.yml`:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=your-secure-password
    - GF_SERVER_ROOT_URL=http://grafana.yourdomain.com
```

Restart Grafana:
```bash
docker-compose -f docker-compose.monitoring.yml restart grafana
```

#### Alert Notification Setup

Edit `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'
```

Restart AlertManager:
```bash
docker-compose -f docker-compose.monitoring.yml restart alertmanager
```

### Stopping and Cleaning Up

```bash
# Stop all services
docker-compose -f docker-compose.monitoring.yml down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f docker-compose.monitoring.yml down -v

# View disk usage
docker system df
```

### Backup and Restore

#### Backup

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup Prometheus data
docker run --rm -v eje_prometheus_data:/data -v $(pwd)/backups/$(date +%Y%m%d):/backup alpine tar czf /backup/prometheus.tar.gz -C /data .

# Backup Grafana data
docker run --rm -v eje_grafana_data:/data -v $(pwd)/backups/$(date +%Y%m%d):/backup alpine tar czf /backup/grafana.tar.gz -C /data .

# Backup AlertManager data
docker run --rm -v eje_alertmanager_data:/data -v $(pwd)/backups/$(date +%Y%m%d):/backup alpine tar czf /backup/alertmanager.tar.gz -C /data .
```

#### Restore

```bash
# Stop services
docker-compose -f docker-compose.monitoring.yml down

# Restore Prometheus data
docker run --rm -v eje_prometheus_data:/data -v $(pwd)/backups/YYYYMMDD:/backup alpine tar xzf /backup/prometheus.tar.gz -C /data

# Restore Grafana data
docker run --rm -v eje_grafana_data:/data -v $(pwd)/backups/YYYYMMDD:/backup alpine tar xzf /backup/grafana.tar.gz -C /data

# Restore AlertManager data
docker run --rm -v eje_alertmanager_data:/data -v $(pwd)/backups/YYYYMMDD:/backup alpine tar xzf /backup/alertmanager.tar.gz -C /data

# Start services
docker-compose -f docker-compose.monitoring.yml up -d
```

## Production Deployment (Kubernetes)

### Prerequisites Check

```bash
# Verify kubectl access
kubectl cluster-info

# Check available storage classes
kubectl get storageclasses

# Verify cert-manager (if using TLS)
kubectl get pods -n cert-manager
```

### Step 1: Create Namespace

```bash
kubectl apply -f monitoring/kubernetes/namespace.yaml

# Verify namespace created
kubectl get namespace eje-monitoring
```

### Step 2: Create Secrets

```bash
# Create Grafana admin credentials
kubectl create secret generic grafana-credentials \
  --from-literal=admin-user=admin \
  --from-literal=admin-password='YOUR_SECURE_PASSWORD' \
  -n eje-monitoring

# Create AlertManager secrets
kubectl create secret generic alertmanager-secrets \
  --from-literal=smtp-password='YOUR_SMTP_PASSWORD' \
  --from-literal=slack-webhook-url='YOUR_SLACK_WEBHOOK' \
  --from-literal=pagerduty-service-key='YOUR_PAGERDUTY_KEY' \
  -n eje-monitoring

# Verify secrets created
kubectl get secrets -n eje-monitoring
```

### Step 3: Create ConfigMaps

```bash
# Prometheus configuration
kubectl create configmap prometheus-config \
  --from-file=prometheus.yml=monitoring/prometheus/prometheus.yml \
  -n eje-monitoring

# Prometheus alert rules
kubectl create configmap prometheus-alert-rules \
  --from-file=alert_rules.yml=monitoring/prometheus/alert_rules.yml \
  -n eje-monitoring

# AlertManager configuration
kubectl create configmap alertmanager-config \
  --from-file=alertmanager.yml=monitoring/alertmanager/alertmanager.yml \
  -n eje-monitoring

# AlertManager templates
kubectl create configmap alertmanager-templates \
  --from-file=monitoring/alertmanager/templates/ \
  -n eje-monitoring

# Grafana datasources
kubectl create configmap grafana-datasources \
  --from-file=datasources.yml=monitoring/grafana/provisioning/datasources.yml \
  -n eje-monitoring

# Grafana dashboard provisioning
kubectl create configmap grafana-dashboards-config \
  --from-file=dashboards.yml=monitoring/grafana/provisioning/dashboards.yml \
  -n eje-monitoring

# Grafana dashboards
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/ \
  -n eje-monitoring

# Verify configmaps created
kubectl get configmaps -n eje-monitoring
```

### Step 4: Deploy Components

```bash
# Deploy in order (dependencies first)

# 1. Prometheus
kubectl apply -f monitoring/kubernetes/prometheus.yaml

# Wait for Prometheus to be ready
kubectl wait --for=condition=ready pod -l app=prometheus -n eje-monitoring --timeout=300s

# 2. Grafana
kubectl apply -f monitoring/kubernetes/grafana.yaml

# Wait for Grafana to be ready
kubectl wait --for=condition=ready pod -l app=grafana -n eje-monitoring --timeout=300s

# 3. AlertManager
kubectl apply -f monitoring/kubernetes/alertmanager.yaml

# Wait for AlertManager to be ready
kubectl wait --for=condition=ready pod -l app=alertmanager -n eje-monitoring --timeout=300s

# 4. Jaeger (with Elasticsearch)
kubectl apply -f monitoring/kubernetes/jaeger.yaml

# Wait for Jaeger to be ready
kubectl wait --for=condition=ready pod -l app=jaeger -n eje-monitoring --timeout=300s
```

### Step 5: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n eje-monitoring

# Check services
kubectl get services -n eje-monitoring

# Check persistent volumes
kubectl get pvc -n eje-monitoring

# Check logs
kubectl logs -l app=prometheus -n eje-monitoring --tail=50
kubectl logs -l app=grafana -n eje-monitoring --tail=50
kubectl logs -l app=alertmanager -n eje-monitoring --tail=50
kubectl logs -l app=jaeger -n eje-monitoring --tail=50
```

### Step 6: Access Services

#### Port Forwarding (Testing)

```bash
# Prometheus
kubectl port-forward -n eje-monitoring svc/prometheus 9090:9090

# Grafana
kubectl port-forward -n eje-monitoring svc/grafana 3000:3000

# AlertManager
kubectl port-forward -n eje-monitoring svc/alertmanager-lb 9093:9093

# Jaeger
kubectl port-forward -n eje-monitoring svc/jaeger 16686:16686
```

#### Ingress (Production)

Update hostnames in ingress manifests:
- `grafana.example.com` → `grafana.yourdomain.com`
- `alertmanager.example.com` → `alertmanager.yourdomain.com`
- `jaeger.example.com` → `jaeger.yourdomain.com`

Apply ingress:
```bash
# Ensure ingress controller is installed
kubectl get pods -n ingress-nginx

# Ingress resources are included in the YAML files
# Verify ingress created
kubectl get ingress -n eje-monitoring
```

### High Availability Configuration

#### Prometheus HA

The default configuration deploys 2 Prometheus replicas. To scale:

```bash
# Scale Prometheus
kubectl scale statefulset prometheus -n eje-monitoring --replicas=3

# Verify scaling
kubectl get pods -l app=prometheus -n eje-monitoring
```

#### AlertManager HA

AlertManager is deployed as a 3-replica StatefulSet with clustering:

```bash
# Verify clustering
kubectl exec -it alertmanager-0 -n eje-monitoring -- amtool cluster show

# Scale if needed
kubectl scale statefulset alertmanager -n eje-monitoring --replicas=5
```

#### Grafana HA

Grafana is deployed with 2 replicas behind a LoadBalancer:

```bash
# Scale Grafana
kubectl scale deployment grafana -n eje-monitoring --replicas=3
```

### Resource Management

#### View Resource Usage

```bash
# Check resource usage
kubectl top pods -n eje-monitoring

# Check resource limits
kubectl describe pod -n eje-monitoring | grep -A 5 "Limits:"
```

#### Adjust Resources

Edit the YAML files and update resource requests/limits:

```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

Apply changes:
```bash
kubectl apply -f monitoring/kubernetes/prometheus.yaml
```

### Backup and Restore (Kubernetes)

#### Backup

```bash
# Backup Prometheus data
kubectl exec -it prometheus-0 -n eje-monitoring -- tar czf - /prometheus > prometheus-backup-$(date +%Y%m%d).tar.gz

# Backup Grafana data
kubectl exec -it $(kubectl get pod -l app=grafana -n eje-monitoring -o jsonpath='{.items[0].metadata.name}') -n eje-monitoring -- tar czf - /var/lib/grafana > grafana-backup-$(date +%Y%m%d).tar.gz

# Backup AlertManager data
kubectl exec -it alertmanager-0 -n eje-monitoring -- tar czf - /alertmanager > alertmanager-backup-$(date +%Y%m%d).tar.gz

# Backup configurations
kubectl get configmaps -n eje-monitoring -o yaml > configmaps-backup-$(date +%Y%m%d).yaml
kubectl get secrets -n eje-monitoring -o yaml > secrets-backup-$(date +%Y%m%d).yaml
```

#### Restore

```bash
# Scale down to prevent writes during restore
kubectl scale statefulset prometheus -n eje-monitoring --replicas=0
kubectl scale deployment grafana -n eje-monitoring --replicas=0
kubectl scale statefulset alertmanager -n eje-monitoring --replicas=0

# Restore Prometheus data
kubectl exec -it prometheus-0 -n eje-monitoring -- tar xzf - -C / < prometheus-backup-YYYYMMDD.tar.gz

# Restore Grafana data
kubectl exec -it $(kubectl get pod -l app=grafana -n eje-monitoring -o jsonpath='{.items[0].metadata.name}') -n eje-monitoring -- tar xzf - -C / < grafana-backup-YYYYMMDD.tar.gz

# Restore AlertManager data
kubectl exec -it alertmanager-0 -n eje-monitoring -- tar xzf - -C / < alertmanager-backup-YYYYMMDD.tar.gz

# Scale back up
kubectl scale statefulset prometheus -n eje-monitoring --replicas=2
kubectl scale deployment grafana -n eje-monitoring --replicas=2
kubectl scale statefulset alertmanager -n eje-monitoring --replicas=3
```

### Automated Backups with CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: monitoring-backup
  namespace: eje-monitoring
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: alpine:latest
            command:
            - /bin/sh
            - -c
            - |
              apk add --no-cache curl tar
              kubectl exec prometheus-0 -- tar czf - /prometheus > /backup/prometheus-$(date +%Y%m%d).tar.gz
              # Upload to S3 or backup storage
          restartPolicy: OnFailure
```

### Monitoring the Monitoring Stack

#### Prometheus Self-Monitoring

Access Prometheus metrics:
```bash
curl http://prometheus:9090/metrics
```

Key metrics:
- `prometheus_tsdb_head_samples_appended_total`
- `prometheus_tsdb_storage_blocks_bytes`
- `prometheus_rule_evaluation_duration_seconds`

#### Grafana Self-Monitoring

Enable Grafana metrics:
```yaml
env:
  - name: GF_METRICS_ENABLED
    value: "true"
```

#### AlertManager Self-Monitoring

Check AlertManager cluster status:
```bash
kubectl exec -it alertmanager-0 -n eje-monitoring -- amtool cluster show
```

### Troubleshooting

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod POD_NAME -n eje-monitoring

# Check logs
kubectl logs POD_NAME -n eje-monitoring

# Common issues:
# - Insufficient resources: Increase resource limits
# - Storage not available: Check PVC status
# - Config errors: Validate ConfigMaps
```

#### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n eje-monitoring

# Check PV status
kubectl get pv

# Expand PVC (if storage class supports it)
kubectl patch pvc CLAIM_NAME -n eje-monitoring -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
```

#### Network Issues

```bash
# Test service connectivity
kubectl run -it --rm debug --image=alpine --restart=Never -n eje-monitoring -- /bin/sh
# Inside pod:
apk add curl
curl http://prometheus:9090/-/healthy
curl http://grafana:3000/api/health
curl http://alertmanager:9093/-/healthy
```

#### Configuration Errors

```bash
# Validate Prometheus config
kubectl exec -it prometheus-0 -n eje-monitoring -- promtool check config /etc/prometheus/prometheus.yml

# Validate AlertManager config
kubectl exec -it alertmanager-0 -n eje-monitoring -- amtool check-config /etc/alertmanager/alertmanager.yml
```

### Upgrade Procedures

#### Rolling Update

```bash
# Update image version in YAML
sed -i 's/prometheus:v2.47.0/prometheus:v2.48.0/g' monitoring/kubernetes/prometheus.yaml

# Apply update
kubectl apply -f monitoring/kubernetes/prometheus.yaml

# Watch rollout
kubectl rollout status statefulset/prometheus -n eje-monitoring
```

#### Rollback

```bash
# Rollback to previous version
kubectl rollout undo statefulset/prometheus -n eje-monitoring

# Check rollout history
kubectl rollout history statefulset/prometheus -n eje-monitoring
```

### Scaling Guidelines

#### When to Scale

- **Prometheus**: > 10M active series or > 80% memory usage
- **Grafana**: > 100 concurrent users
- **AlertManager**: > 1000 alerts/second
- **Elasticsearch**: > 100GB trace data

#### How to Scale

```bash
# Horizontal scaling
kubectl scale statefulset prometheus -n eje-monitoring --replicas=N

# Vertical scaling (edit resources in YAML and reapply)
kubectl apply -f monitoring/kubernetes/prometheus.yaml
```

## Performance Tuning

### Prometheus

```yaml
# Increase retention
args:
  - '--storage.tsdb.retention.time=90d'
  - '--storage.tsdb.retention.size=200GB'

# Adjust scrape settings
global:
  scrape_interval: 30s  # Reduce frequency
  scrape_timeout: 10s
```

### Grafana

```yaml
env:
  - name: GF_DATABASE_MAX_OPEN_CONN
    value: "300"
  - name: GF_DATABASE_MAX_IDLE_CONN
    value: "100"
```

### Jaeger/Elasticsearch

```yaml
env:
  - name: ES_JAVA_OPTS
    value: "-Xms4g -Xmx4g"  # Adjust heap size
```

## Security Considerations

### TLS/HTTPS

1. Install cert-manager
2. Create ClusterIssuer
3. Ingress annotations handle TLS automatically

### Authentication

#### Grafana

```yaml
env:
  - name: GF_AUTH_BASIC_ENABLED
    value: "true"
  - name: GF_AUTH_ANONYMOUS_ENABLED
    value: "false"
```

#### Prometheus

Use nginx-ingress basic auth:
```bash
htpasswd -c auth admin
kubectl create secret generic prometheus-basic-auth --from-file=auth -n eje-monitoring
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitoring-network-policy
  namespace: eje-monitoring
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: eje-production
```

## Resources

- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
- [Grafana Helm Chart](https://github.com/grafana/helm-charts)
- [Jaeger Operator](https://github.com/jaegertracing/jaeger-operator)
- [EJE Monitoring Documentation](../README.md)

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
**Kubernetes Version**: 1.24+
