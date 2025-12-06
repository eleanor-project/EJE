# EJE Observability Documentation

Complete guide to monitoring, observability, and operational excellence for ELEANOR/EJE.

## 📚 Table of Contents

### Getting Started
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [5-Minute Setup](#5-minute-setup)

### Core Components
- [Prometheus Metrics](./prometheus_setup.md) - Metrics collection and storage
- [Grafana Dashboards](./grafana_dashboards.md) - Visualization and dashboards
- [OpenTelemetry Tracing](./opentelemetry_setup.md) - Distributed tracing
- [AlertManager](./alertmanager_setup.md) - Alert routing and notifications

### Operations
- [Deployment Guide](./deployment_guide.md) - Local and production deployment
- [Runbooks](./runbooks.md) - Alert response procedures
- [Troubleshooting](./troubleshooting_guide.md) - Common issues and solutions
- [Performance Tuning](./performance_tuning_guide.md) - Optimization guide

### Reference
- [EJE Metrics Guide](./eje_metrics_guide.md) - Complete metrics reference
- [Architecture Guide](./architecture_guide.md) - System design and patterns

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        EJE Application                           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Critics    │  │  Aggregator  │  │Policy Engine │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│         ┌──────────────────┴──────────────────┐                  │
│         │                                      │                  │
│         ▼                                      ▼                  │
│  ┌─────────────┐                      ┌──────────────┐          │
│  │  Metrics    │                      │    Traces    │          │
│  │  Exporter   │                      │   Exporter   │          │
│  └──────┬──────┘                      └──────┬───────┘          │
└─────────┼─────────────────────────────────────┼─────────────────┘
          │                                      │
          ▼                                      ▼
┌──────────────────┐                   ┌─────────────────┐
│   Prometheus     │                   │     Jaeger      │
│  (Port 9090)     │                   │  (Port 16686)   │
│                  │                   │                 │
│ ┌──────────────┐ │                   │ ┌─────────────┐ │
│ │Alert Rules   │ │                   │ │ Trace Store │ │
│ │Evaluation    │ │                   │ └─────────────┘ │
│ └──────┬───────┘ │                   └─────────────────┘
└────────┼─────────┘
         │
         ▼
┌──────────────────┐
│  AlertManager    │
│  (Port 9093)     │
│                  │
│ ┌──────────────┐ │
│ │  Routing &   │ │
│ │  Grouping    │ │
│ └──────┬───────┘ │
└────────┼─────────┘
         │
         ├─────────────┬──────────────┬───────────────┐
         ▼             ▼              ▼               ▼
    ┌────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐
    │ Email  │   │  Slack  │   │PagerDuty │   │  ...     │
    └────────┘   └─────────┘   └──────────┘   └──────────┘

                         │
                         ▼
                 ┌──────────────┐
                 │   Grafana    │
                 │ (Port 3000)  │
                 │              │
                 │ ┌──────────┐ │
                 │ │Dashboards│ │
                 │ └──────────┘ │
                 └──────────────┘
```

### Data Flow

1. **Metrics Collection**: EJE exports Prometheus metrics at `/metrics` endpoint
2. **Scraping**: Prometheus scrapes metrics every 15s
3. **Alert Evaluation**: Prometheus evaluates alert rules every 15s
4. **Alert Routing**: Alerts sent to AlertManager for routing
5. **Notifications**: AlertManager routes to appropriate channels (Email/Slack/PagerDuty)
6. **Visualization**: Grafana queries Prometheus for dashboard data
7. **Tracing**: EJE sends traces to Jaeger collector via OpenTelemetry
8. **Trace Storage**: Jaeger stores traces in Elasticsearch (production) or BadgerDB (dev)

### Key Features

- **Comprehensive Metrics**: 50+ metrics covering critics, decisions, system health
- **Pre-built Dashboards**: 4 Grafana dashboards for different audiences
- **Intelligent Alerting**: 35+ alert rules with severity-based routing
- **Distributed Tracing**: End-to-end request visibility across critics
- **High Availability**: Multi-replica deployments for production
- **Auto-provisioning**: Dashboards and datasources auto-configured

---

## Quick Start

### Local Development (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/eleanor-project/eje.git
cd eje

# 2. Start monitoring stack
make -f Makefile.monitoring local-up

# 3. Access services
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# AlertManager: http://localhost:9093
# Jaeger: http://localhost:16686

# 4. View dashboards
make -f Makefile.monitoring open-dashboards
```

### Production (Kubernetes)

```bash
# 1. Create namespace and secrets
make -f Makefile.monitoring k8s-namespace
make -f Makefile.monitoring k8s-secrets

# 2. Deploy monitoring stack
make -f Makefile.monitoring k8s-deploy

# 3. Access services (port forwarding)
make -f Makefile.monitoring k8s-port-forward
```

---

## 5-Minute Setup

### Prerequisites
- Docker and Docker Compose
- 8GB RAM, 20GB disk space
- Ports 3000, 9090, 9093, 16686 available

### Steps

1. **Start Stack**
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

2. **Verify Services**
   ```bash
   docker-compose -f docker-compose.monitoring.yml ps
   ```

3. **View Dashboards**
   - Open http://localhost:3000
   - Login: admin / admin
   - Browse dashboards in "EJE" folder

4. **Test Alerts** (optional)
   ```bash
   ./scripts/monitoring/test_alerts.sh
   ```

---

## Component Guides

### 📊 Prometheus Metrics

**Purpose**: Collect and store time-series metrics from EJE

**Key Metrics**:
- `eje_critic_executions_total` - Critic execution counter
- `eje_decision_latency_seconds` - Decision latency histogram
- `eje_decision_confidence` - Decision confidence distribution
- [Full Metrics Reference →](./eje_metrics_guide.md)

**Setup**: [Prometheus Setup Guide →](./prometheus_setup.md)

### 📈 Grafana Dashboards

**Purpose**: Visualize metrics and monitor system health

**Dashboards**:
1. **EJE Overview** - System health and throughput
2. **Critic Performance** - Critic-specific metrics
3. **Decision Analysis** - Verdict patterns and conflicts
4. **Alerting** - Real-time alert monitoring

**Setup**: [Grafana Dashboard Guide →](./grafana_dashboards.md)

### 🔍 OpenTelemetry Tracing

**Purpose**: Track requests through the decision pipeline

**Features**:
- Automatic span creation for decisions and critics
- Trace ID propagation across services
- Performance bottleneck identification
- Error tracking and debugging

**Setup**: [OpenTelemetry Setup Guide →](./opentelemetry_setup.md)

### 🚨 AlertManager

**Purpose**: Route alerts to appropriate notification channels

**Alert Groups**:
- Critic alerts (failure rate, latency)
- Performance alerts (latency spikes)
- Resource alerts (memory, CPU)
- Decision alerts (conflicts, confidence)
- Availability alerts (service down, errors)

**Setup**: [AlertManager Setup Guide →](./alertmanager_setup.md)

---

## Operational Guides

### 🚀 Deployment

Complete guide for deploying monitoring infrastructure:

- **Local Development**: Docker Compose setup
- **Production**: Kubernetes manifests
- **High Availability**: Multi-replica configuration
- **Backup & Restore**: Automated procedures

[Deployment Guide →](./deployment_guide.md)

### 📖 Runbooks

Detailed procedures for responding to alerts:

- Investigation steps for each alert
- Resolution procedures with timelines
- Impact assessment and prioritization
- Escalation procedures

[Alert Runbooks →](./runbooks.md)

### 🔧 Troubleshooting

Solutions for common issues:

- Services not starting
- Metrics not appearing
- Alerts not firing
- Dashboard loading issues
- Performance problems

[Troubleshooting Guide →](./troubleshooting_guide.md)

### ⚡ Performance Tuning

Optimization guidelines:

- Resource sizing (CPU, memory, storage)
- Scrape interval tuning
- Alert rule optimization
- Dashboard query optimization
- Retention and storage management

[Performance Tuning Guide →](./performance_tuning_guide.md)

---

## Monitoring Philosophy

### Observability Pillars

EJE monitoring is built on three pillars:

1. **Metrics** (Prometheus)
   - What is happening? (quantitative)
   - System-wide aggregates
   - Alert thresholds

2. **Traces** (Jaeger)
   - Why is it happening? (qualitative)
   - Request-level details
   - Performance bottlenecks

3. **Logs** (Application Logs)
   - Detailed context
   - Error messages
   - Audit trail

### Design Principles

- **Proactive over Reactive**: Alert before impact
- **Actionable Alerts**: Every alert has a runbook
- **Layered Monitoring**: System → Component → Request level
- **SLO-Driven**: Alerts based on Service Level Objectives
- **Low Noise**: Intelligent grouping and inhibition
- **Self-Monitoring**: Monitor the monitoring stack

### Best Practices

1. **Metric Naming**: Follow Prometheus conventions
2. **Label Cardinality**: Keep labels low-cardinality
3. **Alert Fatigue**: Use appropriate thresholds and `for` durations
4. **Dashboard Design**: One metric per panel, clear titles
5. **Runbook Quality**: Always include "what", "why", "how"
6. **Regular Review**: Review metrics and alerts quarterly

---

## Metrics Overview

### Critic Metrics
- **Executions**: Total count by verdict and status
- **Latency**: Histogram with P50/P90/P95/P99
- **Confidence**: Summary of confidence scores
- **Failures**: Count by error type
- **Active**: Current executing critics

### Decision Metrics
- **Throughput**: Total decisions by verdict
- **Latency**: Histogram of aggregation time
- **Confidence**: Average and distribution
- **Conflicts**: Count by type and severity
- **Overrides**: Count by override type

### EJE-Specific Metrics
- **Precedent Matching**: Match rate and quality
- **Critic Agreement**: Consensus ratios
- **Audit Trail**: Size and entry count
- **Cache Performance**: Hit/miss rates
- **Compliance**: Governance scores

### System Metrics
- **Memory**: RSS and VMS usage
- **CPU**: Process CPU percentage
- **Active Requests**: Current load
- **Errors**: Count by type and component
- **Fallbacks**: Activation count

[Complete Metrics Reference →](./eje_metrics_guide.md)

---

## Alert Categories

### Critical (PagerDuty + Slack)
- High critic failure rate (>10%)
- Critic completely failing
- Decision latency extreme (P99 >10s)
- Service down
- High memory usage (>2GB)
- API quota at limit (>90%)

### Warning (Slack)
- Elevated critic failure rate (>5%)
- Decision latency spike (P95 >5s)
- High conflict rate (>30%)
- Anomalous verdict distribution
- High CPU usage (>90%)

### Info (Email)
- High review requirement rate
- High retry rate
- Compliance score changes
- Capacity planning alerts

[Alert Runbooks →](./runbooks.md)

---

## Dashboard Guide

### EJE Overview Dashboard
**Audience**: Operations team, management
**Purpose**: System health at a glance

**Key Panels**:
- Decision throughput (req/sec)
- Error rate (%)
- Average confidence
- P95 latency
- Verdict distribution

**Use Cases**:
- Daily health check
- Capacity planning
- Performance trending
- Executive reporting

### Critic Performance Dashboard
**Audience**: ML engineers, developers
**Purpose**: Critic-specific troubleshooting

**Key Panels**:
- Critic latency by critic
- Success/failure rates
- Confidence scores
- Active executions

**Use Cases**:
- Identifying slow critics
- Debugging failures
- Optimizing performance
- Capacity planning per critic

### Decision Analysis Dashboard
**Audience**: Policy team, compliance
**Purpose**: Decision pattern analysis

**Key Panels**:
- Verdict distribution (24h)
- Confidence trends
- Conflict patterns
- Override tracking

**Use Cases**:
- Policy effectiveness
- Audit and compliance
- Pattern detection
- Conflict analysis

### Alerting Dashboard
**Audience**: On-call engineers
**Purpose**: Incident response

**Key Panels**:
- Error rates (with thresholds)
- Active alerts
- Recent errors
- System health

**Use Cases**:
- Incident triage
- Alert validation
- Root cause analysis
- On-call monitoring

[Dashboard Guide →](./grafana_dashboards.md)

---

## Common Queries

### System Health
```promql
# Overall decision throughput
rate(eje_decisions_total[5m])

# Error rate
rate(eje_errors_total[5m]) / rate(eje_decisions_total[5m])

# Average confidence
eje_decision_confidence_avg

# P95 latency
histogram_quantile(0.95, rate(eje_decision_latency_seconds_bucket[5m]))
```

### Critic Analysis
```promql
# Critic failure rate
rate(eje_critic_failures_total[5m]) / rate(eje_critic_executions_total[5m])

# Slowest critics (P95)
topk(5, histogram_quantile(0.95, rate(eje_critic_execution_seconds_bucket[5m])))

# Critic agreement
avg(eje_critic_agreement_ratio)
```

### Decision Quality
```promql
# High confidence decisions (>0.8)
sum(rate(eje_decision_confidence_bucket{le="+Inf"}[5m])) - sum(rate(eje_decision_confidence_bucket{le="0.8"}[5m]))

# Conflict rate
rate(eje_conflicts_detected_total[5m]) / rate(eje_decisions_total[5m])

# Unanimous verdict rate
rate(eje_critic_unanimous_verdicts_total[5m]) / rate(eje_decisions_total[5m])
```

[More Examples →](./eje_metrics_guide.md)

---

## Support and Resources

### Documentation
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)

### Tools
- **promtool**: Validate Prometheus configs
- **amtool**: Manage AlertManager
- **kubectl**: Kubernetes management
- **docker-compose**: Local development

### Getting Help
1. Check [Troubleshooting Guide](./troubleshooting_guide.md)
2. Review [Runbooks](./runbooks.md) for alerts
3. Search GitHub issues
4. Contact on-call team

---

## Changelog

### Version 1.0.0 (2025-12-02)
- Initial release
- Complete monitoring stack
- 4 Grafana dashboards
- 35+ alert rules
- 50+ metrics
- Comprehensive documentation

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
**Maintained By**: EJE Operations Team
