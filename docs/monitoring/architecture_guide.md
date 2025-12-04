# EJE Monitoring Architecture Guide

Detailed architecture and design principles for EJE observability infrastructure.

## Table of Contents
- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Design Patterns](#design-patterns)
- [Scalability](#scalability)
- [High Availability](#high-availability)
- [Security](#security)
- [Performance Considerations](#performance-considerations)

---

## System Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                           EJE Application Layer                         │
│                                                                          │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   │
│  │   Critic   │   │   Critic   │   │   Critic   │   │   Critic   │   │
│  │    #1      │   │    #2      │   │    #3      │   │    #N      │   │
│  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   │
│        │                │                │                │             │
│        └────────────────┴────────────────┴────────────────┘             │
│                               │                                          │
│                    ┌──────────┴──────────┐                              │
│                    │  Decision Aggregator │                              │
│                    └──────────┬──────────┘                              │
│                               │                                          │
│         ┌─────────────────────┼─────────────────────┐                   │
│         │                     │                      │                   │
│         ▼                     ▼                      ▼                   │
│  ┌────────────┐        ┌────────────┐        ┌────────────┐           │
│  │ Metrics    │        │  Traces    │        │   Logs     │           │
│  │ Exporter   │        │  Exporter  │        │  Exporter  │           │
│  └──────┬─────┘        └──────┬─────┘        └──────┬─────┘           │
└─────────┼────────────────────┼─────────────────────┼──────────────────┘
          │                     │                      │
          │ HTTP /metrics       │ OTLP                │ stdout/files
          │ (pull)              │ (push)              │
          │                     │                      │
┌─────────▼────────┐   ┌───────▼────────┐   ┌────────▼─────────┐
│   Prometheus     │   │     Jaeger     │   │  Log Aggregator  │
│   (Scraping)     │   │  (Collecting)  │   │   (Optional)     │
│                  │   │                │   │                  │
│  ┌────────────┐  │   │ ┌────────────┐ │   │                  │
│  │ TSDB       │  │   │ │Elasticsearch│ │   │                  │
│  │ Storage    │  │   │ │  /BadgerDB │ │   │                  │
│  └────────────┘  │   │ └────────────┘ │   │                  │
│                  │   │                │   │                  │
│  ┌────────────┐  │   │                │   │                  │
│  │Alert Rules │  │   │                │   │                  │
│  │Evaluation  │  │   │                │   │                  │
│  └──────┬─────┘  │   │                │   │                  │
└─────────┼────────┘   └────────────────┘   └──────────────────┘
          │
          │ Alerts
          │
┌─────────▼────────┐
│  AlertManager    │
│                  │
│  ┌────────────┐  │
│  │ Routing    │  │
│  │ Grouping   │  │
│  │ Silencing  │  │
│  │ Inhibition │  │
│  └──────┬─────┘  │
└─────────┼────────┘
          │
          ├──────────────┬──────────────┬──────────────┐
          │              │              │              │
┌─────────▼────┐  ┌──────▼─────┐  ┌───▼────────┐  ┌──▼────────┐
│    Email     │  │   Slack    │  │ PagerDuty  │  │  Webhook  │
└──────────────┘  └────────────┘  └────────────┘  └───────────┘

          ┌────────────────────────────────┐
          │                                │
          │        Query Layer             │
          │                                │
          │    ┌────────────────┐          │
          │    │    Grafana     │          │
          │    │  (Dashboard)   │          │
          │    │                │          │
          │    │ ┌────────────┐ │          │
          │    │ │Datasources:│ │          │
          │    │ │- Prometheus│ │          │
          │    │ │- Jaeger    │ │          │
          │    │ └────────────┘ │          │
          │    └────────────────┘          │
          └────────────────────────────────┘
```

### Component Layers

#### 1. Instrumentation Layer (EJE Application)
- **Responsibility**: Generate observability data
- **Components**:
  - PrometheusExporter: Metrics generation
  - OpenTelemetry SDK: Trace generation
  - Structured logging: Event logging
- **Pattern**: Push (traces, logs) and Pull (metrics)

#### 2. Collection Layer
- **Responsibility**: Collect and aggregate observability data
- **Components**:
  - Prometheus: Metrics scraping and storage
  - Jaeger Collector: Trace ingestion
  - Log aggregators: Log collection (optional)
- **Pattern**: Time-series DB (Prometheus), Document store (Elasticsearch)

#### 3. Processing Layer
- **Responsibility**: Analyze and route data
- **Components**:
  - Prometheus Alert Rules: Metric-based alerting
  - AlertManager: Alert routing and grouping
  - Jaeger Query: Trace querying
- **Pattern**: Rule evaluation, event-driven routing

#### 4. Notification Layer
- **Responsibility**: Deliver alerts to humans
- **Components**:
  - Email (SMTP)
  - Slack (Webhooks)
  - PagerDuty (API)
  - Custom webhooks
- **Pattern**: Fan-out with routing and grouping

#### 5. Visualization Layer
- **Responsibility**: Present data for human consumption
- **Components**:
  - Grafana: Dashboards and panels
  - Jaeger UI: Trace visualization
  - AlertManager UI: Alert management
- **Pattern**: Query-on-demand with caching

---

## Component Details

### Prometheus

**Role**: Time-series metrics storage and alerting engine

**Architecture**:
```
Prometheus Instance
├── Scraper
│   ├── Service Discovery (Kubernetes, Static)
│   ├── Target Management
│   └── HTTP Client (/metrics endpoint)
├── TSDB (Time-Series Database)
│   ├── In-Memory Buffer
│   ├── WAL (Write-Ahead Log)
│   ├── Compaction Engine
│   └── Block Storage
├── Query Engine
│   ├── PromQL Parser
│   ├── Query Executor
│   └── Query Cache
└── Alert Manager
    ├── Rule Evaluation
    ├── Alert State Tracking
    └── AlertManager Client
```

**Key Characteristics**:
- **Pull Model**: Scrapes metrics from targets
- **TSDB**: Optimized for time-series data
- **PromQL**: Powerful query language
- **Retention**: Configurable (default 30d)
- **Cardinality**: Monitor label cardinality carefully

**Resource Requirements**:
- Memory: ~2Gi base + (active series × 2-3 bytes)
- CPU: 1-2 cores for typical workload
- Storage: Depends on retention and cardinality
  - Formula: `retention_days × ingestion_rate × compression_ratio`
  - Example: 30d × 100k series × 15s × 1.5 bytes ≈ 400GB

### Grafana

**Role**: Visualization and dashboarding

**Architecture**:
```
Grafana Instance
├── Web Server (HTTP)
├── Dashboard Engine
│   ├── Panel Renderer
│   ├── Query Processor
│   └── Caching Layer
├── Datasource Plugins
│   ├── Prometheus Plugin
│   ├── Jaeger Plugin
│   └── Others...
├── User Management
│   ├── Authentication
│   ├── Authorization
│   └── Organizations
└── Database (SQLite/PostgreSQL)
    ├── Dashboard Definitions
    ├── User Preferences
    └── Alert Rules
```

**Key Characteristics**:
- **Multi-Datasource**: Query multiple backends
- **Templating**: Dynamic dashboards
- **Alerting**: Built-in alerting (optional)
- **Provisioning**: Auto-load dashboards and datasources
- **Plugins**: Extensible panel types

**Resource Requirements**:
- Memory: 512Mi-1Gi (depends on concurrent users)
- CPU: 250-500m (depends on query complexity)
- Storage: 10Gi (dashboard storage, minimal)

### AlertManager

**Role**: Alert routing, grouping, and notification

**Architecture**:
```
AlertManager Instance
├── API Server
│   ├── Alert Receiver (/api/v1/alerts)
│   ├── Silence Manager
│   └── Status Endpoint
├── Alert Processing
│   ├── Deduplication
│   ├── Grouping (by labels)
│   ├── Inhibition (suppress alerts)
│   └── Silencing (user-defined)
├── Routing Engine
│   ├── Route Tree
│   ├── Label Matching
│   └── Receiver Selection
├── Notification Pipeline
│   ├── Templating
│   ├── Rate Limiting
│   └── Retry Logic
└── Persistence
    ├── Silence Storage
    ├── Notification Log
    └── Alert State
```

**Key Characteristics**:
- **Clustering**: HA with gossip protocol
- **Grouping**: Reduce notification noise
- **Inhibition**: Smart alert suppression
- **Routing**: Label-based routing tree
- **Templating**: Customizable notifications

**Resource Requirements**:
- Memory: 256-512Mi per instance
- CPU: 100-200m per instance
- Storage: 2-5Gi (alert state, silences)

### Jaeger

**Role**: Distributed tracing and request tracking

**Architecture**:
```
Jaeger Deployment
├── Agent (per-host/sidecar)
│   ├── UDP Listener (Thrift)
│   ├── Batching
│   └── Collector Client
├── Collector
│   ├── gRPC/HTTP Receiver
│   ├── Span Processor
│   ├── Sampling Decisions
│   └── Storage Writer
├── Query Service
│   ├── Storage Reader
│   ├── Trace Aggregation
│   └── API Endpoint
├── UI (Web Interface)
│   ├── Trace Search
│   ├── Trace Visualization
│   └── Service Dependency Graph
└── Storage
    ├── Elasticsearch (production)
    ├── BadgerDB (dev/local)
    └── Cassandra (optional)
```

**Key Characteristics**:
- **Sampling**: Reduces storage overhead
- **Context Propagation**: Trace ID in headers
- **Span Relationships**: Parent-child hierarchy
- **Storage Options**: Pluggable backends
- **OpenTelemetry**: Native OTLP support

**Resource Requirements**:
- Agent: 64-128Mi memory, 50-100m CPU
- Collector: 512Mi-2Gi memory, 500m-1 CPU
- Query: 512Mi memory, 250-500m CPU
- Elasticsearch: 4-8Gi memory, 2-4 CPUs, 100Gi+ storage

---

## Data Flow

### Metrics Flow

```
EJE Application
    │
    │ 1. Record metric
    │    exporter.decisions_total.labels(verdict="APPROVE").inc()
    │
    ▼
PrometheusExporter
    │
    │ 2. Store in memory
    │    Counter/Histogram/Gauge objects
    │
    ▼
HTTP /metrics Endpoint
    │
    │ 3. Prometheus scrapes (every 15s)
    │    GET http://eje:8000/metrics
    │
    ▼
Prometheus TSDB
    │
    │ 4. Store as time-series
    │    eje_decisions_total{verdict="APPROVE"} 1234 @timestamp
    │
    ├──────────────────┬──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
Alert Rules      Grafana Query     External Query
    │                  │                  │
    ▼                  ▼                  ▼
AlertManager     Dashboard         API Client
```

### Trace Flow

```
EJE Application
    │
    │ 1. Create span
    │    with tracer.start_as_current_span("decision"):
    │
    ▼
OpenTelemetry SDK
    │
    │ 2. Add attributes
    │    span.set_attribute("eje.verdict", "APPROVE")
    │
    ▼
Batch Span Processor
    │
    │ 3. Batch spans (reduce network calls)
    │    Buffer up to 512 spans or 5s timeout
    │
    ▼
OTLP Exporter
    │
    │ 4. Send via gRPC/HTTP
    │    POST http://jaeger:4318/v1/traces
    │
    ▼
Jaeger Collector
    │
    │ 5. Process and validate
    │    Check sampling, apply processors
    │
    ▼
Storage Writer
    │
    │ 6. Write to Elasticsearch
    │    Index: eje-traces-YYYY-MM-DD
    │
    ▼
Query Service
    │
    │ 7. Read for UI/API
    │    Search by trace_id, service, operation
    │
    ▼
Jaeger UI / Grafana
```

### Alert Flow

```
Prometheus
    │
    │ 1. Evaluate rules (every 15s)
    │    FOR 5m: rate(eje_critic_failures) > 0.10
    │
    ▼
Alert State Machine
    │
    │ 2. State transitions
    │    Inactive → Pending → Firing → Resolved
    │
    ▼
AlertManager
    │
    │ 3. Receive alert
    │    POST /api/v1/alerts
    │
    ├── 4. Deduplication
    │    │ (merge identical alerts)
    │    │
    ├── 5. Grouping
    │    │ (by severity, component)
    │    │
    ├── 6. Inhibition
    │    │ (suppress if related alert firing)
    │    │
    ├── 7. Routing
    │    │ (match labels to receivers)
    │    │
    │    ├──────────┬──────────┬──────────┐
    │    │          │          │          │
    │    ▼          ▼          ▼          ▼
    │  Email     Slack    PagerDuty  Webhook
    │    │          │          │          │
    │    └──────────┴──────────┴──────────┘
    │                    │
    ▼                    ▼
Alert Log         Human Response
```

---

## Design Patterns

### 1. Instrumentation Patterns

#### Decorator Pattern (Metrics)
```python
@track_critic_execution(critic_name="bias_critic")
def evaluate_bias(input_text):
    # Automatically tracked:
    # - Execution count
    # - Latency
    # - Success/failure
    # - Result verdict
    return {"verdict": "APPROVE", "confidence": 0.9}
```

#### Decorator Pattern (Tracing)
```python
@trace_decision("main_pipeline")
def process_request(data):
    # Automatically creates span with:
    # - Operation name
    # - Start/end timestamps
    # - Child span relationships
    result1 = critic1(data)  # Child span
    result2 = critic2(data)  # Child span
    return aggregate([result1, result2])
```

#### Context Manager Pattern
```python
with trace_span("database_lookup", query_type="precedent"):
    # Custom span for specific operations
    results = db.query(...)
# Span automatically closed, timing recorded
```

### 2. Collection Patterns

#### Pull Model (Prometheus)
- **Pros**: Service discovery, health checks, simpler failure handling
- **Cons**: Need to expose HTTP endpoint, firewall rules
- **Used For**: Metrics

#### Push Model (Jaeger)
- **Pros**: Works with short-lived processes, simpler for client
- **Cons**: Need collector infrastructure, backpressure handling
- **Used For**: Traces, Logs

### 3. Storage Patterns

#### Time-Series Database (Prometheus TSDB)
- **Optimized For**: Append-only writes, time-range queries
- **Retention**: Time-based + size-based
- **Compaction**: Automatic background process
- **Indexing**: Label-based inverted index

#### Document Store (Elasticsearch)
- **Optimized For**: Full-text search, complex queries
- **Retention**: Index-based (daily/weekly indices)
- **Sharding**: Horizontal scaling
- **Indexing**: Inverted indices per field

### 4. Alerting Patterns

#### Threshold-Based Alerts
```yaml
expr: eje_critic_failures_total > 100
for: 5m
```
- Simple to understand
- Prone to false positives with spikes

#### Rate-Based Alerts
```yaml
expr: rate(eje_critic_failures_total[5m]) > 0.10
for: 5m
```
- Normalized for varying loads
- Better for scaling systems

#### SLO-Based Alerts
```yaml
expr: |
  (
    sum(rate(eje_decisions_total{status="success"}[30d]))
    /
    sum(rate(eje_decisions_total[30d]))
  ) < 0.999
```
- Aligned with business objectives
- Budget-based alerting (error budget)

### 5. Dashboard Patterns

#### Single Metric Per Panel
- Clear focus
- Easy to understand
- Recommended for most use cases

#### Golden Signals
- **Latency**: How long it takes
- **Traffic**: How many requests
- **Errors**: How many failures
- **Saturation**: How full the system is

#### RED Method
- **Rate**: Requests per second
- **Errors**: Error rate
- **Duration**: Latency distribution

#### USE Method (Resources)
- **Utilization**: % time busy
- **Saturation**: Queue depth
- **Errors**: Error count

---

## Scalability

### Horizontal Scaling

#### Prometheus
- **Federation**: Hierarchical Prometheus instances
- **Sharding**: Different Prometheus instances for different services
- **Remote Write**: Write to centralized storage (e.g., Thanos, Cortex)

```
       ┌──────────────┐
       │Global Prometheus│
       │  (Federation)   │
       └────────┬────────┘
                │
        ┌───────┴────────┐
        │                │
┌───────▼────┐    ┌──────▼──────┐
│Regional     │    │Regional     │
│Prometheus A │    │Prometheus B │
└───────┬─────┘    └──────┬──────┘
        │                 │
   ┌────┴────┐       ┌────┴────┐
   │         │       │         │
   EJE-A1  EJE-A2  EJE-B1  EJE-B2
```

#### Grafana
- **Load Balancer**: Multiple Grafana instances
- **Shared Database**: PostgreSQL for shared state
- **Session Affinity**: Not required (stateless queries)

#### AlertManager
- **Clustering**: Gossip protocol (Memberlist)
- **High Availability**: 3+ instances recommended
- **State Sharing**: Alerts, silences, notifications

#### Jaeger
- **Collector Scaling**: Horizontal (stateless)
- **Storage Scaling**: Elasticsearch sharding
- **Query Scaling**: Multiple query instances

### Vertical Scaling

**When to Scale Up**:
- Prometheus: High active series (>10M)
- Grafana: Complex queries timing out
- Elasticsearch: High query latency

**Resource Increase Guidelines**:
- Memory: 2x current usage if >80% utilization
- CPU: 2x current if >70% utilization consistently
- Storage: Increase before 80% full

---

## High Availability

### Prometheus HA

```
Load Balancer (Round-Robin)
        │
   ┌────┴─────┐
   │          │
Prom-1     Prom-2
   │          │
   └────┬─────┘
        │
   EJE Instances
```

**Configuration**:
- Identical scrape configs
- Identical alert rules
- Same external labels (except `replica`)
- AlertManager handles deduplication

**Trade-offs**:
- 2x storage required
- 2x scrape load on targets
- AlertManager deduplication needed

### AlertManager HA

```
Alert Manager Cluster (Gossip)
   ┌────────┬────────┬────────┐
   │        │        │        │
  AM-1     AM-2     AM-3
   │        │        │        │
   └────────┴────────┴────────┘
        (Share state)

Prometheus sends to all AMs
AMs deduplicate and send once
```

**Configuration**:
```yaml
--cluster.peer=am-1:9094
--cluster.peer=am-2:9094
--cluster.peer=am-3:9094
```

**Benefits**:
- No split-brain (gossip protocol)
- Automatic failover
- Shared silences and notifications

### Grafana HA

```
       Load Balancer
             │
      ┌──────┴──────┐
      │             │
  Grafana-1    Grafana-2
      │             │
      └──────┬──────┘
             │
    Shared PostgreSQL
```

**Configuration**:
- Shared database (PostgreSQL)
- Session store in database
- No sticky sessions needed

---

## Security

### Authentication

**Grafana**:
- Built-in users
- OAuth (Google, GitHub)
- LDAP integration
- Anonymous access (disabled by default)

**Prometheus/AlertManager**:
- No built-in auth
- Use reverse proxy (nginx) with basic auth
- Network policies in Kubernetes

### Authorization

**Grafana**:
- Organizations
- Role-based access (Admin, Editor, Viewer)
- Team-based permissions
- Dashboard permissions

### TLS/Encryption

**In-Transit**:
```yaml
# nginx ingress with cert-manager
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - grafana.example.com
      secretName: grafana-tls
```

**At-Rest**:
- Prometheus: No encryption (file system encryption)
- Elasticsearch: Optional (X-Pack Security)
- Grafana: Secrets encryption in database

### Network Security

**Network Policies** (Kubernetes):
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitoring-network-policy
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: eje
      ports:
        - protocol: TCP
          port: 9090
```

### Secrets Management

- Kubernetes Secrets for credentials
- Sealed Secrets for GitOps
- External Secrets Operator for cloud KMS
- Never commit secrets to git

---

## Performance Considerations

### Query Performance

**PromQL Optimization**:
```promql
# Bad: High cardinality
sum(rate(eje_requests_total{user_id=~".+"}[5m])) by (user_id)

# Good: Aggregate early
sum(rate(eje_requests_total[5m]))
```

**Recording Rules**:
```yaml
# Pre-compute expensive queries
- record: eje:decision_quality:ratio
  expr: |
    rate(eje_decisions_total{verdict="APPROVE"}[5m])
    /
    rate(eje_decisions_total[5m])
```

### Storage Performance

**Prometheus TSDB**:
- SSD highly recommended
- Avoid network filesystems (NFS)
- Monitor compaction metrics

**Elasticsearch**:
- Hot-warm-cold architecture
- SSD for hot tier
- HDD for warm/cold tiers

### Cardinality Management

**Label Cardinality**:
```python
# Bad: Unbounded labels
metric.labels(user_id=user_id, request_id=request_id).inc()

# Good: Bounded labels
metric.labels(user_type=user.type, api_version=version).inc()
```

**Monitor Cardinality**:
```promql
# Number of active series
prometheus_tsdb_symbol_table_size_bytes

# Cardinality by metric
count by (__name__) ({__name__=~".+"})
```

---

## Best Practices

### Instrumentation
1. Use consistent naming conventions
2. Keep label cardinality low
3. Instrument at boundaries (API, DB, external calls)
4. Use appropriate metric types
5. Add context to traces

### Alerting
1. Alert on symptoms, not causes
2. Include runbook links
3. Set appropriate `for` durations
4. Use inhibition to reduce noise
5. Review alerts quarterly

### Dashboards
1. One metric per panel
2. Use templates for reusability
3. Document panel purposes
4. Include links to runbooks
5. Test with real data

### Operations
1. Monitor the monitoring system
2. Regular backup of configurations
3. Test disaster recovery
4. Capacity planning (storage, resources)
5. Keep systems up to date

---

## Resources

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/reference/specification/)
- [SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
