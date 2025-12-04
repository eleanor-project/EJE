# EJE Alert Runbooks

Operational runbooks for responding to EJE alerts.

## Table of Contents

### Critic Alerts
- [High Critic Failure Rate](#high-critic-failure-rate)
- [Critic Completely Failing](#critic-completely-failing)
- [Elevated Critic Failure Rate](#elevated-critic-failure-rate)

### Performance Alerts
- [Decision Latency Spike](#decision-latency-spike)
- [Decision Latency Extreme](#decision-latency-extreme)
- [Critic Latency High](#critic-latency-high)
- [High Active Operations](#high-active-operations)

### Resource Alerts
- [High Memory Usage](#high-memory-usage)
- [Elevated Memory Usage](#elevated-memory-usage)
- [High CPU Usage](#high-cpu-usage)

### Decision Alerts
- [High Conflict Rate](#high-conflict-rate)
- [Anomalous Verdict Distribution](#anomalous-verdict-distribution)
- [Low Confidence Decisions](#low-confidence-decisions)
- [High Review Requirement Rate](#high-review-requirement-rate)

### Quota Alerts
- [API Quota Approaching Limit](#api-quota-approaching-limit)
- [API Quota Elevated](#api-quota-elevated)

### Availability Alerts
- [Service Down](#service-down)
- [High Error Rate](#high-error-rate)
- [Elevated Error Rate](#elevated-error-rate)

### Fallback Alerts
- [Fallback Mode Activated](#fallback-mode-activated)
- [High Retry Rate](#high-retry-rate)

---

## Critic Alerts

### High Critic Failure Rate

**Severity**: Critical
**Alert**: `HighCriticFailureRate`
**Threshold**: Failure rate > 10% for 5 minutes

#### Description
A critic is failing more than 10% of the time, indicating a serious problem with critic execution.

#### Impact
- Decision quality degraded
- Increased latency due to retries
- Potential bias in decision-making if critic is critical

#### Investigation Steps

1. **Identify the failing critic**:
   ```bash
   # Check Prometheus for failing critic
   curl 'http://prometheus:9090/api/v1/query?query=topk(5,rate(eje_critic_failures_total[5m]))'
   ```

2. **Check critic logs**:
   ```bash
   # Get recent logs for critic
   kubectl logs -l app=eje --tail=100 | grep "critic_name=CRITIC_NAME"
   ```

3. **Verify input data quality**:
   ```bash
   # Check for malformed inputs
   kubectl logs -l app=eje --tail=100 | grep "validation_error"
   ```

4. **Check external dependencies**:
   - API endpoints the critic calls
   - Database connections
   - ML model availability

5. **Review recent deployments**:
   ```bash
   # Check deployment history
   kubectl rollout history deployment/eje
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- If critic is non-critical, disable it temporarily:
  ```yaml
  # Update critic config
  critics:
    - name: failing_critic
      enabled: false
  ```
- If critic is critical, rollback recent changes:
  ```bash
  kubectl rollout undo deployment/eje
  ```

**Short-term (within 1 hour)**:
- Fix the root cause based on investigation
- Re-enable critic with fix deployed
- Monitor failure rate

**Long-term**:
- Add input validation to prevent similar failures
- Improve error messages for faster diagnosis
- Consider circuit breaker pattern for critic

#### Related Metrics
- `eje_critic_failures_total`
- `eje_critic_executions_total`
- `eje_critic_execution_seconds`

#### Related Dashboards
- [Critic Performance Dashboard](http://grafana:3000/d/critic-performance)

---

### Critic Completely Failing

**Severity**: Critical
**Alert**: `CriticCompletelyFailing`
**Threshold**: 100% failure rate for 2 minutes

#### Description
All executions of a critic are failing. The critic is completely non-functional.

#### Impact
- Critical decision functionality unavailable
- Decision pipeline may be blocked
- Immediate user impact

#### Investigation Steps

1. **Check if service is running**:
   ```bash
   kubectl get pods -l app=eje
   kubectl logs -l app=eje --tail=50
   ```

2. **Verify critic configuration**:
   ```bash
   # Check critic config
   kubectl get configmap eje-config -o yaml
   ```

3. **Test critic endpoint directly**:
   ```bash
   curl -X POST http://eje:8000/critics/CRITIC_NAME/evaluate \
     -H "Content-Type: application/json" \
     -d '{"text": "test input"}'
   ```

4. **Check for dependency failures**:
   - Database connectivity
   - External API availability
   - Model file accessibility

#### Resolution

**Immediate (within 2 minutes)**:
- Enable circuit breaker:
  ```python
  # Circuit breaker should auto-activate
  # Verify in logs:
  kubectl logs -l app=eje | grep "circuit_breaker"
  ```
- If circuit breaker not working, disable critic:
  ```bash
  kubectl patch configmap eje-config --patch '{"data":{"critic_CRITIC_NAME_enabled":"false"}}'
  kubectl rollout restart deployment/eje
  ```

**Short-term (within 30 minutes)**:
- Identify and fix root cause
- Test critic in isolation before re-enabling
- Monitor closely after re-enabling

#### Related Metrics
- `eje_critic_executions_total`
- `eje_critic_failures_total`
- `eje_circuit_breaker_state`

---

### Elevated Critic Failure Rate

**Severity**: Warning
**Alert**: `ElevatedCriticFailureRate`
**Threshold**: Failure rate > 5% for 10 minutes

#### Description
A critic is failing more than 5% but less than 10% of the time.

#### Impact
- Slight degradation in decision quality
- May escalate to critical if not addressed

#### Investigation Steps

1. **Monitor trend**:
   ```bash
   # Check failure rate trend
   curl 'http://prometheus:9090/api/v1/query?query=rate(eje_critic_failures_total{critic_name="CRITIC_NAME"}[30m])'
   ```

2. **Review error patterns**:
   ```bash
   # Get error types
   kubectl logs -l app=eje --tail=200 | grep "critic_error" | cut -d' ' -f5 | sort | uniq -c
   ```

3. **Check for transient issues**:
   - Network timeouts
   - Temporary API issues
   - Resource contention

#### Resolution

**Immediate**:
- Monitor closely
- Prepare for escalation if rate increases

**Short-term (within 2 hours)**:
- Investigate error patterns
- Fix if root cause identified
- Adjust timeouts or retry logic if transient

**Long-term**:
- Improve error handling
- Add more specific error messages
- Consider increasing timeout thresholds

---

## Performance Alerts

### Decision Latency Spike

**Severity**: Critical
**Alert**: `DecisionLatencySpike`
**Threshold**: P95 latency > 5 seconds for 5 minutes

#### Description
95th percentile decision latency exceeds 5 seconds, indicating serious performance degradation.

#### Impact
- Users experiencing slow response times
- SLA breach risk
- Potential timeout errors

#### Investigation Steps

1. **Identify slow critics**:
   ```bash
   # Check critic latencies
   curl 'http://prometheus:9090/api/v1/query?query=topk(10,histogram_quantile(0.95,rate(eje_critic_execution_seconds_bucket[5m])))'
   ```

2. **Check database performance**:
   ```bash
   # Check slow queries
   psql -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

3. **Review resource utilization**:
   ```bash
   # Check CPU and memory
   kubectl top pods -l app=eje
   ```

4. **Check for external API slowness**:
   ```bash
   # Review external API response times
   kubectl logs -l app=eje | grep "external_api_latency"
   ```

5. **Look for deadlocks or contention**:
   ```bash
   # Check for goroutine buildup
   curl http://eje:8000/debug/pprof/goroutine?debug=1
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- Scale up if resource-constrained:
  ```bash
  kubectl scale deployment/eje --replicas=5
  ```
- Enable aggressive caching:
  ```bash
  kubectl set env deployment/eje CACHE_AGGRESSIVE=true
  ```
- Disable non-critical critics:
  ```bash
  kubectl patch configmap eje-config --patch '{"data":{"critics_priority_only":"true"}}'
  ```

**Short-term (within 1 hour)**:
- Optimize slow critics
- Add database indexes
- Increase timeout limits for external APIs
- Add circuit breakers

**Long-term**:
- Performance profiling and optimization
- Implement result caching
- Consider async critic execution
- Database query optimization

#### Related Metrics
- `eje_decision_latency_seconds`
- `eje_critic_execution_seconds`
- `eje_active_operations`

#### Related Dashboards
- [EJE Overview Dashboard](http://grafana:3000/d/eje-overview)

---

### Decision Latency Extreme

**Severity**: Critical
**Alert**: `DecisionLatencyExtreme`
**Threshold**: P99 latency > 10 seconds for 2 minutes

#### Description
99th percentile latency is extremely high (>10s), indicating severe performance issues.

#### Impact
- Severe user experience degradation
- Timeout errors likely
- Service may appear unresponsive

#### Investigation Steps

1. **Check for hung operations**:
   ```bash
   # Check active operations age
   curl http://eje:8000/metrics | grep eje_active_operations
   ```

2. **Look for database locks**:
   ```bash
   psql -c "SELECT * FROM pg_locks WHERE NOT granted;"
   ```

3. **Check for memory issues**:
   ```bash
   kubectl top pods -l app=eje
   dmesg | grep -i "out of memory"
   ```

4. **Review goroutine dumps**:
   ```bash
   curl http://eje:8000/debug/pprof/goroutine?debug=2 > goroutines.txt
   # Look for stuck goroutines
   ```

#### Resolution

**Immediate (within 2 minutes)**:
- Restart affected pods:
  ```bash
  kubectl rollout restart deployment/eje
  ```
- Kill long-running operations:
  ```bash
  curl -X POST http://eje:8000/admin/kill-long-operations
  ```

**Short-term (within 30 minutes)**:
- Identify and fix hung operations
- Add operation timeouts
- Implement request cancellation

**Long-term**:
- Add distributed tracing for visibility
- Implement request timeout policies
- Add operation deadline propagation

---

### Critic Latency High

**Severity**: Warning
**Alert**: `CriticLatencyHigh`
**Threshold**: P95 critic latency > 3 seconds for 10 minutes

#### Description
A specific critic is running slower than expected.

#### Impact
- Overall decision latency increases
- May cascade to other critics
- User experience degradation

#### Investigation Steps

1. **Profile the critic**:
   ```bash
   # Enable profiling for specific critic
   curl http://eje:8000/admin/profile/critic/CRITIC_NAME
   ```

2. **Check external dependencies**:
   - API response times
   - Model inference time
   - Database query performance

3. **Review recent changes**:
   ```bash
   git log --oneline --since="1 week ago" -- src/critics/CRITIC_NAME/
   ```

#### Resolution

**Immediate**:
- Monitor for escalation
- Consider increasing timeout threshold

**Short-term (within 4 hours)**:
- Optimize critic implementation
- Cache expensive computations
- Parallelize independent operations

**Long-term**:
- Rewrite critic with better algorithm
- Move to async execution model
- Consider pre-computation strategies

---

### High Active Operations

**Severity**: Warning
**Alert**: `HighActiveOperations`
**Threshold**: >100 active operations for 5 minutes

#### Description
Unusually high number of concurrent operations.

#### Impact
- System under high load
- Risk of resource exhaustion
- Increased latency

#### Investigation Steps

1. **Check request rate**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=rate(eje_decisions_total[5m])'
   ```

2. **Look for leaked operations**:
   ```bash
   # Check operation ages
   curl http://eje:8000/admin/active-operations
   ```

3. **Review goroutine count**:
   ```bash
   curl http://eje:8000/debug/pprof/goroutine?debug=1 | head -1
   ```

#### Resolution

**Immediate**:
- Implement rate limiting:
  ```bash
  kubectl set env deployment/eje RATE_LIMIT=100
  ```
- Scale horizontally:
  ```bash
  kubectl scale deployment/eje --replicas=10
  ```

**Short-term**:
- Fix operation leaks if found
- Optimize operation lifecycle

**Long-term**:
- Implement backpressure
- Add request queue with limits
- Improve capacity planning

---

## Resource Alerts

### High Memory Usage

**Severity**: Critical
**Alert**: `HighMemoryUsage`
**Threshold**: Memory usage > 2GB for 5 minutes

#### Description
Memory usage is critically high and approaching limits.

#### Impact
- Risk of OOM kill
- System instability
- Potential data loss

#### Investigation Steps

1. **Get memory breakdown**:
   ```bash
   curl http://eje:8000/debug/pprof/heap > heap.prof
   go tool pprof -http=:8080 heap.prof
   ```

2. **Check for memory leaks**:
   ```bash
   # Compare heap profiles over time
   curl http://eje:8000/debug/pprof/heap > heap1.prof
   sleep 300
   curl http://eje:8000/debug/pprof/heap > heap2.prof
   go tool pprof -base=heap1.prof heap2.prof
   ```

3. **Review caching strategy**:
   ```bash
   # Check cache sizes
   curl http://eje:8000/admin/cache-stats
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- Clear caches:
  ```bash
  curl -X POST http://eje:8000/admin/clear-caches
  ```
- Restart pods with memory leak:
  ```bash
  kubectl delete pod -l app=eje --field-selector=status.phase=Running
  ```
- Increase memory limits temporarily:
  ```bash
  kubectl set resources deployment/eje --limits=memory=4Gi
  ```

**Short-term (within 2 hours)**:
- Fix memory leaks
- Implement cache eviction policies
- Reduce cache sizes

**Long-term**:
- Memory profiling and optimization
- Implement memory limits per operation
- Add memory usage monitoring per component

---

### Elevated Memory Usage

**Severity**: Warning
**Alert**: `ElevatedMemoryUsage`
**Threshold**: Memory usage > 1.5GB for 10 minutes

#### Description
Memory usage is elevated and trending upward.

#### Impact
- Approaching memory limits
- May escalate to critical

#### Investigation Steps

1. **Monitor trend**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=eje_memory_usage_bytes[1h]'
   ```

2. **Check for gradual leaks**:
   ```bash
   # Profile memory over time
   curl http://eje:8000/debug/pprof/heap > heap.prof
   ```

#### Resolution

**Immediate**:
- Monitor closely
- Prepare to clear caches

**Short-term**:
- Review caching policies
- Implement cache size limits
- Schedule periodic cache clears

---

### High CPU Usage

**Severity**: Critical
**Alert**: `HighCPUUsage`
**Threshold**: CPU usage > 90% for 10 minutes

#### Description
CPU usage is critically high.

#### Impact
- System CPU-bound
- Severe performance degradation
- Request queuing

#### Investigation Steps

1. **Get CPU profile**:
   ```bash
   curl http://eje:8000/debug/pprof/profile?seconds=30 > cpu.prof
   go tool pprof -http=:8080 cpu.prof
   ```

2. **Check for CPU-intensive critics**:
   ```bash
   # Profile critic execution times
   curl 'http://prometheus:9090/api/v1/query?query=topk(10,rate(eje_critic_execution_seconds_sum[5m]))'
   ```

3. **Look for busy loops**:
   ```bash
   # Check goroutine states
   curl http://eje:8000/debug/pprof/goroutine?debug=2
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- Scale horizontally:
  ```bash
  kubectl scale deployment/eje --replicas=10
  ```
- Rate limit incoming requests:
  ```bash
  kubectl set env deployment/eje RATE_LIMIT=50
  ```

**Short-term (within 2 hours)**:
- Optimize CPU-intensive operations
- Implement caching for repeated computations
- Parallelize where possible

**Long-term**:
- Algorithm optimization
- Move CPU-intensive work to background jobs
- Consider GPU acceleration for ML models

---

## Decision Alerts

### High Conflict Rate

**Severity**: Critical
**Alert**: `HighConflictRate`
**Threshold**: Conflict rate > 30% for 10 minutes

#### Description
A high percentage of decisions have conflicts between critics.

#### Impact
- Many decisions require human review
- Review queue growing
- Decision throughput reduced

#### Investigation Steps

1. **Identify conflict types**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=sum by (conflict_type) (rate(eje_decision_conflicts_total[5m]))'
   ```

2. **Check critic verdicts**:
   ```bash
   # Review verdict distribution by critic
   curl http://eje:8000/admin/critic-verdicts-distribution
   ```

3. **Review recent policy changes**:
   ```bash
   git log --oneline --since="1 week ago" -- config/policies/
   ```

4. **Check for model drift**:
   ```bash
   # Compare current vs. baseline metrics
   python scripts/check_model_drift.py
   ```

#### Resolution

**Immediate (within 10 minutes)**:
- Review conflict resolution policies:
  ```bash
  kubectl get configmap eje-conflict-policies -o yaml
  ```
- Temporarily adjust conflict thresholds:
  ```bash
  kubectl patch configmap eje-config --patch '{"data":{"conflict_threshold":"0.4"}}'
  ```

**Short-term (within 4 hours)**:
- Review critic weights
- Validate critic configurations
- Check for input data quality issues
- Retrain models if drift detected

**Long-term**:
- Implement automated model retraining
- Add model drift detection
- Improve conflict resolution logic
- Consider critic ensemble methods

---

### Anomalous Verdict Distribution

**Severity**: Warning
**Alert**: `AnomalousVerdictDistribution`
**Threshold**: DENY > 80% or APPROVE > 95% for 30 minutes

#### Description
Verdict distribution differs significantly from baseline.

#### Impact
- May indicate data quality issues
- Possible model drift
- Policy misconfiguration

#### Investigation Steps

1. **Compare to baseline**:
   ```bash
   # Get historical distribution
   curl 'http://prometheus:9090/api/v1/query_range?query=rate(eje_decisions_total[1h])&start=-7d&end=now&step=1h'
   ```

2. **Review recent inputs**:
   ```bash
   # Sample recent decision inputs
   kubectl logs -l app=eje --tail=100 | grep "decision_input"
   ```

3. **Check policy changes**:
   ```bash
   git diff HEAD~10 config/policies/
   ```

#### Resolution

**Immediate**:
- Validate policy configuration
- Check for input data anomalies

**Short-term (within 4 hours)**:
- Review and adjust policies if needed
- Investigate data pipeline for issues
- Check for upstream system changes

**Long-term**:
- Implement baseline tracking
- Add anomaly detection
- Set up A/B testing for policy changes

---

### Low Confidence Decisions

**Severity**: Warning
**Alert**: `LowConfidenceDecisions`
**Threshold**: Average confidence < 50% for 15 minutes

#### Description
Decision confidence is consistently low.

#### Impact
- Decision quality questionable
- More human reviews needed
- Reduced automation benefit

#### Investigation Steps

1. **Check confidence by critic**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=avg by (critic_name) (eje_critic_confidence)'
   ```

2. **Review input quality**:
   ```bash
   # Check input validation errors
   kubectl logs -l app=eje | grep "input_validation"
   ```

3. **Check critic models**:
   ```bash
   # Validate model versions
   kubectl exec -it eje-pod -- ls -la /models/
   ```

#### Resolution

**Immediate**:
- Monitor for critical threshold breach

**Short-term (within 4 hours)**:
- Review critic weights
- Validate input data quality
- Check model versions
- Test critics in isolation

**Long-term**:
- Retrain models with more data
- Improve input validation
- Add confidence calibration

---

### High Review Requirement Rate

**Severity**: Info
**Alert**: `HighReviewRequirementRate`
**Threshold**: Review rate > 50% for 20 minutes

#### Description
Over half of decisions require human review.

#### Impact
- Review queue growing
- Manual review capacity exceeded
- Reduced automation benefit

#### Investigation Steps

1. **Check review queue size**:
   ```bash
   curl http://eje:8000/admin/review-queue-size
   ```

2. **Review confidence thresholds**:
   ```bash
   kubectl get configmap eje-config -o yaml | grep confidence
   ```

#### Resolution

**Immediate**:
- Monitor queue growth

**Short-term (within 8 hours)**:
- Adjust confidence thresholds if appropriate
- Add review capacity
- Prioritize critical reviews

**Long-term**:
- Improve decision confidence
- Implement reviewer assistance tools
- Add review batch processing

---

## Quota Alerts

### API Quota Approaching Limit

**Severity**: Critical
**Alert**: `APIQuotaApproachingLimit`
**Threshold**: API usage > 90% of quota for 5 minutes

#### Description
API quota is nearly exhausted.

#### Impact
- Risk of API throttling
- Service interruption imminent
- Request failures

#### Investigation Steps

1. **Check quota usage**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=eje_api_requests_total/eje_api_quota_limit'
   ```

2. **Identify high-usage source**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=topk(10,rate(eje_api_requests_total[5m]))'
   ```

3. **Check for retry storms**:
   ```bash
   kubectl logs -l app=eje | grep "api_retry"
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- Request emergency quota increase:
  ```bash
  # Contact API provider
  ./scripts/request-quota-increase.sh URGENT
  ```
- Enable aggressive caching:
  ```bash
  kubectl set env deployment/eje API_CACHE_TTL=3600
  ```
- Implement circuit breaker:
  ```bash
  kubectl set env deployment/eje API_CIRCUIT_BREAKER=true
  ```

**Short-term (within 1 hour)**:
- Implement rate limiting
- Add request deduplication
- Optimize API usage patterns

**Long-term**:
- Permanent quota increase
- Implement request batching
- Add intelligent caching
- Consider alternative API providers

---

### API Quota Elevated

**Severity**: Warning
**Alert**: `APIQuotaElevated`
**Threshold**: API usage > 75% of quota for 10 minutes

#### Description
API quota usage is elevated.

#### Impact
- Approaching API limits
- Risk of throttling

#### Investigation Steps

1. **Monitor trend**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=rate(eje_api_requests_total[1h])'
   ```

2. **Project quota exhaustion time**:
   ```bash
   python scripts/project-quota-exhaustion.py
   ```

#### Resolution

**Immediate**:
- Monitor usage closely

**Short-term (within 4 hours)**:
- Plan quota increase
- Review usage optimization opportunities

**Long-term**:
- Implement usage forecasting
- Add quota usage alerts
- Optimize API usage

---

## Availability Alerts

### Service Down

**Severity**: Critical
**Alert**: `EJEServiceDown`
**Threshold**: Service unreachable for 1 minute

#### Description
EJE service is completely down.

#### Impact
- Complete service outage
- No decisions can be processed
- Customer-facing impact

#### Investigation Steps

1. **Check pod status**:
   ```bash
   kubectl get pods -l app=eje
   kubectl describe pods -l app=eje
   ```

2. **Check recent deployments**:
   ```bash
   kubectl rollout history deployment/eje
   ```

3. **Review logs**:
   ```bash
   kubectl logs -l app=eje --tail=100
   ```

4. **Check infrastructure**:
   ```bash
   kubectl get nodes
   kubectl describe node NODE_NAME
   ```

#### Resolution

**Immediate (within 1 minute)**:
- Restart deployment:
  ```bash
  kubectl rollout restart deployment/eje
  ```
- If persists, rollback:
  ```bash
  kubectl rollout undo deployment/eje
  ```
- Check for node issues:
  ```bash
  kubectl cordon NODE_NAME  # If node faulty
  kubectl drain NODE_NAME --ignore-daemonsets
  ```

**Short-term (within 30 minutes)**:
- Fix root cause
- Re-deploy with fix
- Add health checks if missing

**Long-term**:
- Improve deployment testing
- Add canary deployments
- Implement blue-green deployment

---

### High Error Rate

**Severity**: Critical
**Alert**: `HighErrorRate`
**Threshold**: Error rate > 0.1 errors/sec for 5 minutes

#### Description
High rate of errors across the system.

#### Impact
- Many requests failing
- Service degradation
- User impact

#### Investigation Steps

1. **Check error types**:
   ```bash
   kubectl logs -l app=eje --tail=500 | grep ERROR | cut -d' ' -f5 | sort | uniq -c | sort -rn
   ```

2. **Identify error sources**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=topk(10,rate(eje_errors_total[5m]))'
   ```

3. **Check dependencies**:
   ```bash
   # Test database
   psql -c "SELECT 1;"
   # Test external APIs
   curl http://external-api:8000/health
   ```

#### Resolution

**Immediate (within 5 minutes)**:
- Enable fallback mode:
  ```bash
  kubectl set env deployment/eje FALLBACK_MODE=true
  ```
- Check and fix dependency issues
- Rollback if caused by deployment:
  ```bash
  kubectl rollout undo deployment/eje
  ```

**Short-term (within 1 hour)**:
- Fix error causes
- Add error handling
- Improve input validation

**Long-term**:
- Implement circuit breakers
- Add graceful degradation
- Improve error recovery

---

### Elevated Error Rate

**Severity**: Warning
**Alert**: `ElevatedErrorRate`
**Threshold**: Error rate > 0.01 errors/sec for 10 minutes

#### Description
Moderate increase in error rate.

#### Impact
- Some requests failing
- May escalate

#### Investigation Steps

1. **Monitor trend**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=rate(eje_errors_total[30m])'
   ```

2. **Review error patterns**:
   ```bash
   kubectl logs -l app=eje --tail=200 | grep ERROR
   ```

#### Resolution

**Immediate**:
- Monitor for escalation

**Short-term (within 4 hours)**:
- Investigate error causes
- Fix if root cause identified

---

## Fallback Alerts

### Fallback Mode Activated

**Severity**: Warning
**Alert**: `FallbackModeActivated`
**Threshold**: >5 fallback activations in 5 minutes

#### Description
System has activated fallback mode multiple times.

#### Impact
- Operating in degraded mode
- Some critics unavailable
- Reduced decision quality

#### Investigation Steps

1. **Check which critics are in fallback**:
   ```bash
   curl http://eje:8000/admin/circuit-breaker-status
   ```

2. **Review primary service failures**:
   ```bash
   kubectl logs -l app=eje | grep "primary_service_failure"
   ```

3. **Check circuit breaker state**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=eje_circuit_breaker_state'
   ```

#### Resolution

**Immediate**:
- Verify fallback is working correctly
- Monitor decision quality

**Short-term (within 2 hours)**:
- Fix primary service issues
- Test and reset circuit breakers:
  ```bash
  curl -X POST http://eje:8000/admin/reset-circuit-breaker/CRITIC_NAME
  ```

**Long-term**:
- Improve primary service reliability
- Enhance fallback capabilities
- Add circuit breaker tuning

---

### High Retry Rate

**Severity**: Info
**Alert**: `HighRetryRate`
**Threshold**: Retry rate > 0.5 retries/sec for 10 minutes

#### Description
High rate of operation retries.

#### Impact
- Increased latency
- Resource usage increase
- May indicate instability

#### Investigation Steps

1. **Check retry reasons**:
   ```bash
   kubectl logs -l app=eje --tail=200 | grep "retry_reason"
   ```

2. **Identify retry sources**:
   ```bash
   curl 'http://prometheus:9090/api/v1/query?query=rate(eje_retries_total[5m])'
   ```

#### Resolution

**Immediate**:
- Monitor for escalation to failures

**Short-term (within 4 hours)**:
- Investigate transient failures
- Adjust retry configuration if needed

**Long-term**:
- Fix underlying instability
- Implement exponential backoff
- Add jitter to retries

---

## General Troubleshooting

### Getting Support

1. **Check logs**:
   ```bash
   kubectl logs -l app=eje --tail=500 > eje-logs.txt
   ```

2. **Export metrics**:
   ```bash
   curl http://prometheus:9090/api/v1/query?query={__name__=~"eje_.*"} > metrics.json
   ```

3. **Get system state**:
   ```bash
   kubectl get all -l app=eje > system-state.txt
   ```

4. **Contact on-call**:
   - Slack: #eje-oncall
   - PagerDuty: Escalate to L2
   - Email: eje-oncall@example.com

---

## Appendix

### Useful Commands

```bash
# Check all EJE metrics
curl http://localhost:8000/metrics

# Query Prometheus
curl 'http://prometheus:9090/api/v1/query?query=METRIC_NAME'

# View Grafana dashboards
open http://grafana:3000/d/eje-overview

# View AlertManager
open http://alertmanager:9093

# Get pod logs
kubectl logs -l app=eje --tail=100 --follow

# Scale deployment
kubectl scale deployment/eje --replicas=N

# Restart deployment
kubectl rollout restart deployment/eje

# Rollback deployment
kubectl rollout undo deployment/eje
```

### Escalation Path

1. **L1 (0-15 minutes)**: On-call engineer investigates
2. **L2 (15-30 minutes)**: Senior engineer joins
3. **L3 (30+ minutes)**: Engineering lead and product involved
4. **Incident Commander**: Coordinates response for P0 incidents

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
**Maintained By**: EJE Operations Team
