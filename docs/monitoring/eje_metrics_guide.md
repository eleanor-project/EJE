# EJE-Specific Metrics Guide

Complete reference for EJE governance-specific Prometheus metrics.

## Overview

EJE exports custom metrics that capture governance-specific insights beyond generic system metrics. These metrics provide visibility into:
- Decision confidence and quality
- Precedent matching effectiveness
- Critic consensus patterns
- Compliance and governance posture
- Audit trail completeness
- Caching performance

## Metric Categories

### 1. Decision Confidence Metrics

#### eje_decision_confidence

**Type**: Histogram
**Description**: Distribution of decision confidence scores (0.0-1.0)
**Purpose**: Understand confidence patterns to identify when decisions need human review
**Labels**: None
**Buckets**: 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0

**Interpretation**:
- High values (>0.9): System confident in decisions
- Low values (<0.5): Many uncertain decisions, may need policy tuning
- Bimodal distribution: Clear confident/uncertain split (good)
- Uniform distribution: System lacks decisiveness (bad)

**Example Queries**:

```promql
# P50, P90, P95, P99 confidence percentiles
histogram_quantile(0.50, rate(eje_decision_confidence_bucket[5m]))
histogram_quantile(0.90, rate(eje_decision_confidence_bucket[5m]))
histogram_quantile(0.95, rate(eje_decision_confidence_bucket[5m]))
histogram_quantile(0.99, rate(eje_decision_confidence_bucket[5m]))

# Percentage of decisions with confidence > 0.8
sum(rate(eje_decision_confidence_bucket{le="1.0"}[5m])) - sum(rate(eje_decision_confidence_bucket{le="0.8"}[5m]))
/
sum(rate(eje_decision_confidence_bucket{le="+Inf"}[5m]))

# Average confidence over time
rate(eje_decision_confidence_sum[5m]) / rate(eje_decision_confidence_count[5m])

# Confidence distribution heatmap (for Grafana)
increase(eje_decision_confidence_bucket[1h])
```

#### eje_decision_confidence_avg

**Type**: Gauge
**Description**: Current average decision confidence
**Purpose**: Quick snapshot of overall system confidence
**Labels**: None

**Interpretation**:
- >0.8: System performing well
- 0.6-0.8: Acceptable performance, monitor trends
- <0.6: System struggling, investigate causes

**Example Queries**:

```promql
# Current average confidence
eje_decision_confidence_avg

# Confidence trend (24h)
eje_decision_confidence_avg[24h]

# Alert if confidence drops below threshold
eje_decision_confidence_avg < 0.6
```

---

### 2. Precedent Matching Metrics

#### eje_precedent_matches_total

**Type**: Counter
**Description**: Total number of precedent matches found
**Purpose**: Track effectiveness of precedent-based decision making
**Labels**:
- `match_quality`: excellent, good, fair, poor
- `precedent_type`: legal, policy, historical, similar_case

**Interpretation**:
- High match rate: Good precedent database coverage
- Low match rate: May need more precedents or better matching algorithm
- Quality distribution: Most matches should be "excellent" or "good"

**Example Queries**:

```promql
# Total precedent match rate
rate(eje_precedent_matches_total[5m])

# Match rate by quality
sum by (match_quality) (rate(eje_precedent_matches_total[5m]))

# Percentage of excellent matches
sum(rate(eje_precedent_matches_total{match_quality="excellent"}[5m]))
/
sum(rate(eje_precedent_matches_total[5m]))

# Precedent effectiveness score (excellent + good matches)
(
  sum(rate(eje_precedent_matches_total{match_quality="excellent"}[5m]))
  +
  sum(rate(eje_precedent_matches_total{match_quality="good"}[5m]))
)
/
sum(rate(eje_precedent_matches_total[5m]))
```

#### eje_precedent_lookups_total

**Type**: Counter
**Description**: Total number of precedent lookup operations
**Purpose**: Track precedent system usage
**Labels**:
- `lookup_type`: exact, semantic, hybrid, fuzzy

**Interpretation**:
- Compare with decisions_total to see precedent usage rate
- Monitor lookup type distribution to optimize search strategy

**Example Queries**:

```promql
# Precedent lookup rate
rate(eje_precedent_lookups_total[5m])

# Lookups per decision (precedent usage rate)
rate(eje_precedent_lookups_total[5m])
/
rate(eje_decisions_total[5m])

# Lookup type distribution
sum by (lookup_type) (rate(eje_precedent_lookups_total[5m]))

# Precedent system load
rate(eje_precedent_lookups_total[1m])
```

---

### 3. Critic Agreement Metrics

#### eje_critic_agreement_ratio

**Type**: Gauge
**Description**: Ratio of critics in agreement (0.0-1.0) for specific decisions
**Purpose**: Measure consensus among critics
**Labels**:
- `decision_id`: Unique decision identifier

**Interpretation**:
- 1.0: Perfect consensus (all critics agree)
- 0.8-0.9: Strong consensus
- 0.5-0.7: Moderate agreement
- <0.5: High disagreement, may need human review

**Example Queries**:

```promql
# Average critic agreement
avg(eje_critic_agreement_ratio)

# Minimum agreement in recent decisions
min_over_time(eje_critic_agreement_ratio[1h])

# Decisions with low agreement (<0.7)
count(eje_critic_agreement_ratio < 0.7)

# Agreement distribution
histogram_quantile(0.5,
  rate(eje_critic_agreement_ratio[5m]))
```

#### eje_critic_unanimous_verdicts_total

**Type**: Counter
**Description**: Total number of unanimous critic verdicts
**Purpose**: Track perfect consensus rate
**Labels**:
- `verdict_type`: APPROVE, DENY, ESCALATE, UNCERTAIN

**Interpretation**:
- High unanimous rate: Critics well-calibrated
- Low unanimous rate: May indicate complex cases or critic disagreement

**Example Queries**:

```promql
# Unanimous verdict rate
rate(eje_critic_unanimous_verdicts_total[5m])

# Percentage of unanimous decisions
rate(eje_critic_unanimous_verdicts_total[5m])
/
rate(eje_decisions_total[5m])

# Unanimous verdicts by type
sum by (verdict_type) (rate(eje_critic_unanimous_verdicts_total[5m]))

# Unanimous APPROVE vs DENY ratio
rate(eje_critic_unanimous_verdicts_total{verdict_type="APPROVE"}[5m])
/
rate(eje_critic_unanimous_verdicts_total{verdict_type="DENY"}[5m])
```

---

### 4. Audit Trail Metrics

#### eje_audit_trail_size_bytes

**Type**: Gauge
**Description**: Current audit trail storage size in bytes
**Purpose**: Monitor audit trail growth for capacity planning
**Labels**:
- `storage_type`: database, filesystem, s3, archive

**Interpretation**:
- Monitor growth rate to predict storage needs
- Alert if approaching storage limits
- Track by storage type for tiered storage strategies

**Example Queries**:

```promql
# Current audit trail size
eje_audit_trail_size_bytes

# Total size across all storage types
sum(eje_audit_trail_size_bytes)

# Growth rate (bytes per hour)
rate(eje_audit_trail_size_bytes[1h]) * 3600

# Projected size in 30 days
eje_audit_trail_size_bytes +
(rate(eje_audit_trail_size_bytes[7d]) * 86400 * 30)

# Size by storage type
sum by (storage_type) (eje_audit_trail_size_bytes)
```

#### eje_audit_trail_entries_total

**Type**: Counter
**Description**: Total number of audit trail entries
**Purpose**: Track audit activity volume
**Labels**:
- `entry_type`: decision, override, policy_change, access, modification
- `severity`: info, warning, critical

**Interpretation**:
- Compare with decisions_total to ensure all decisions are audited
- Monitor severity distribution for compliance
- High critical severity may indicate issues

**Example Queries**:

```promql
# Audit entry creation rate
rate(eje_audit_trail_entries_total[5m])

# Audit entries per decision (should be ≥1)
rate(eje_audit_trail_entries_total{entry_type="decision"}[5m])
/
rate(eje_decisions_total[5m])

# Critical audit events
rate(eje_audit_trail_entries_total{severity="critical"}[5m])

# Audit entries by type
sum by (entry_type) (rate(eje_audit_trail_entries_total[5m]))

# Audit coverage (all decisions audited?)
rate(eje_audit_trail_entries_total{entry_type="decision"}[5m])
==
rate(eje_decisions_total[5m])
```

---

### 5. Cache Performance Metrics

#### eje_cache_hits_total

**Type**: Counter
**Description**: Total number of cache hits
**Purpose**: Measure cache effectiveness
**Labels**:
- `cache_name`: critic_results, precedents, policies, embeddings
- `cache_type`: memory, redis, disk

**Example Queries**:

```promql
# Cache hit rate
rate(eje_cache_hits_total[5m])

# Hit rate by cache
sum by (cache_name) (rate(eje_cache_hits_total[5m]))

# Cache efficiency (hit ratio)
sum(rate(eje_cache_hits_total[5m]))
/
(
  sum(rate(eje_cache_hits_total[5m]))
  +
  sum(rate(eje_cache_misses_total[5m]))
)

# Cache hit ratio per cache type
sum by (cache_name) (rate(eje_cache_hits_total[5m]))
/
(
  sum by (cache_name) (rate(eje_cache_hits_total[5m]))
  +
  sum by (cache_name) (rate(eje_cache_misses_total[5m]))
)
```

#### eje_cache_misses_total

**Type**: Counter
**Description**: Total number of cache misses
**Purpose**: Identify caching inefficiencies
**Labels**:
- `cache_name`: critic_results, precedents, policies, embeddings
- `cache_type`: memory, redis, disk

**Example Queries**:

```promql
# Cache miss rate
rate(eje_cache_misses_total[5m])

# Misses by cache
sum by (cache_name) (rate(eje_cache_misses_total[5m]))

# Caches with high miss rate (>50%)
(
  sum by (cache_name) (rate(eje_cache_misses_total[5m]))
  /
  (
    sum by (cache_name) (rate(eje_cache_hits_total[5m]))
    +
    sum by (cache_name) (rate(eje_cache_misses_total[5m]))
  )
) > 0.5
```

#### eje_cache_evictions_total

**Type**: Counter
**Description**: Total number of cache evictions
**Purpose**: Monitor cache pressure and effectiveness of eviction policies
**Labels**:
- `cache_name`: Name of the cache
- `eviction_reason`: size_limit, ttl, lru, manual

**Example Queries**:

```promql
# Cache eviction rate
rate(eje_cache_evictions_total[5m])

# Evictions by reason
sum by (eviction_reason) (rate(eje_cache_evictions_total[5m]))

# Caches under pressure (high eviction rate)
sum by (cache_name) (rate(eje_cache_evictions_total[5m])) > 0.1
```

#### eje_cache_size_bytes

**Type**: Gauge
**Description**: Current cache size in bytes
**Purpose**: Monitor memory usage by caches
**Labels**:
- `cache_name`: Name of the cache

**Example Queries**:

```promql
# Current cache sizes
eje_cache_size_bytes

# Total cache memory
sum(eje_cache_size_bytes)

# Largest caches
topk(5, eje_cache_size_bytes)

# Cache growth rate
rate(eje_cache_size_bytes[1h])
```

#### eje_cache_entries

**Type**: Gauge
**Description**: Current number of entries in cache
**Purpose**: Monitor cache entry count
**Labels**:
- `cache_name`: Name of the cache

**Example Queries**:

```promql
# Entry counts by cache
eje_cache_entries

# Total cached entries
sum(eje_cache_entries)

# Average entry size
eje_cache_size_bytes / eje_cache_entries
```

---

### 6. Policy and Compliance Metrics

#### eje_policy_rules_applied_total

**Type**: Counter
**Description**: Total number of policy rule applications
**Purpose**: Track policy enforcement activity
**Labels**:
- `policy_name`: Name of the policy
- `rule_outcome`: allow, deny, escalate, modify

**Example Queries**:

```promql
# Policy rule application rate
rate(eje_policy_rules_applied_total[5m])

# Rules applied per decision
rate(eje_policy_rules_applied_total[5m])
/
rate(eje_decisions_total[5m])

# Most active policies
topk(10, sum by (policy_name) (rate(eje_policy_rules_applied_total[5m])))

# Policy outcomes distribution
sum by (rule_outcome) (rate(eje_policy_rules_applied_total[5m]))

# Denial rate by policy
sum by (policy_name) (rate(eje_policy_rules_applied_total{rule_outcome="deny"}[5m]))
```

#### eje_governance_compliance_score

**Type**: Gauge
**Description**: Current governance compliance score (0.0-1.0)
**Purpose**: Monitor overall compliance posture
**Labels**:
- `compliance_domain`: gdpr, hipaa, sox, pci_dss, custom

**Interpretation**:
- 1.0: Perfect compliance
- 0.9-0.99: Good compliance
- 0.8-0.89: Acceptable, monitor closely
- <0.8: Compliance issues, immediate attention needed

**Example Queries**:

```promql
# Current compliance scores
eje_governance_compliance_score

# Average compliance across domains
avg(eje_governance_compliance_score)

# Minimum compliance (weakest domain)
min(eje_governance_compliance_score)

# Compliance by domain
eje_governance_compliance_score

# Domains below threshold
eje_governance_compliance_score < 0.9
```

---

## Common Query Patterns

### Decision Quality Assessment

```promql
# Overall decision quality score
(
  # High confidence weight (40%)
  (histogram_quantile(0.9, rate(eje_decision_confidence_bucket[5m])) * 0.4)
  +
  # Low conflict rate weight (30%)
  ((1 - (rate(eje_conflicts_detected_total[5m]) / rate(eje_decisions_total[5m]))) * 0.3)
  +
  # High precedent match rate weight (30%)
  ((rate(eje_precedent_matches_total{match_quality=~"excellent|good"}[5m]) / rate(eje_precedent_lookups_total[5m])) * 0.3)
)
```

### System Effectiveness Score

```promql
# Composite effectiveness metric
(
  # Cache efficiency (25%)
  (
    sum(rate(eje_cache_hits_total[5m]))
    /
    (sum(rate(eje_cache_hits_total[5m])) + sum(rate(eje_cache_misses_total[5m])))
  ) * 0.25
  +
  # Critic consensus (25%)
  avg(eje_critic_agreement_ratio) * 0.25
  +
  # Decision confidence (25%)
  (rate(eje_decision_confidence_sum[5m]) / rate(eje_decision_confidence_count[5m])) * 0.25
  +
  # Audit coverage (25%)
  (rate(eje_audit_trail_entries_total{entry_type="decision"}[5m]) / rate(eje_decisions_total[5m])) * 0.25
)
```

### Governance Health Dashboard

```promql
# Panel 1: Compliance Score
avg(eje_governance_compliance_score)

# Panel 2: Decision Confidence P90
histogram_quantile(0.90, rate(eje_decision_confidence_bucket[5m]))

# Panel 3: Audit Coverage
(rate(eje_audit_trail_entries_total{entry_type="decision"}[5m]) / rate(eje_decisions_total[5m])) * 100

# Panel 4: Cache Hit Rate
(sum(rate(eje_cache_hits_total[5m])) / (sum(rate(eje_cache_hits_total[5m])) + sum(rate(eje_cache_misses_total[5m])))) * 100

# Panel 5: Critic Agreement
avg(eje_critic_agreement_ratio) * 100

# Panel 6: Precedent Effectiveness
(sum(rate(eje_precedent_matches_total{match_quality=~"excellent|good"}[5m])) / sum(rate(eje_precedent_matches_total[5m]))) * 100
```

---

## Integration Examples

### Update Metrics from Application Code

```python
from ejc.monitoring import PrometheusExporter

# Initialize exporter
exporter = PrometheusExporter()

# Record decision with confidence
confidence = 0.85
exporter.decision_confidence_histogram.observe(confidence)

# Record precedent match
exporter.precedent_matches_total.labels(
    match_quality="excellent",
    precedent_type="legal"
).inc()

# Record critic agreement
agreement_ratio = 0.9  # 9 out of 10 critics agree
exporter.critic_agreement_ratio.labels(
    decision_id="dec-12345"
).set(agreement_ratio)

# Record cache hit
exporter.cache_hits_total.labels(
    cache_name="critic_results",
    cache_type="redis"
).inc()

# Update audit trail size
audit_size = get_audit_trail_size()
exporter.audit_trail_size_bytes.labels(
    storage_type="database"
).set(audit_size)

# Record policy application
exporter.policy_rules_applied_total.labels(
    policy_name="gdpr_policy",
    rule_outcome="allow"
).inc()

# Update compliance score
compliance_score = calculate_compliance()
exporter.governance_compliance_score.labels(
    compliance_domain="gdpr"
).set(compliance_score)
```

---

## Best Practices

### Metric Recording
- Record confidence for every decision
- Update cache metrics on every cache operation
- Log audit entries synchronously
- Calculate compliance scores periodically (e.g., hourly)
- Record precedent matches immediately after lookup

### Label Usage
- Use consistent label values across metrics
- Avoid high-cardinality labels (e.g., user IDs, timestamps)
- Use decision_id sparingly, clean up old labels
- Standardize quality/severity levels

### Query Optimization
- Use rate() for counters over longer windows (5m+)
- Pre-aggregate with recording rules for complex queries
- Limit label cardinality to prevent memory issues
- Use histogram_quantile for percentiles, not averages

### Alerting
- Alert on compliance score drops
- Alert on low decision confidence (avg < 0.6)
- Alert on audit coverage gaps
- Alert on cache hit rate drops (< 50%)
- Alert on excessive critic disagreement

---

## Resources

- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Histogram Best Practices](https://prometheus.io/docs/practices/histograms/)
- [EJE Monitoring Setup](./prometheus_setup.md)
- [Grafana Dashboard Guide](./grafana_dashboards.md)

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
