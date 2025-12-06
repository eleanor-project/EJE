# OpenTelemetry Distributed Tracing Setup

Complete guide for setting up and using OpenTelemetry distributed tracing in EJE.

## Overview

EJE uses OpenTelemetry for distributed tracing, providing end-to-end visibility into decision pipelines across critics and services.

**Key Features**:
- Automatic span creation for decisions and critics
- Custom attributes for EJE-specific metadata
- Configurable sampling rates
- Jaeger backend integration
- Performance overhead < 5%
- Trace ID propagation across services

## Quick Start

### 1. Install Dependencies

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation
```

Already included in `requirements.txt`:
```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation>=0.41b0
opentelemetry-exporter-jaeger>=1.20.0
```

### 2. Start Jaeger (Docker)

```bash
# All-in-one Jaeger container
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 6831:6831/udp \
  jaegertracing/all-in-one:latest

# Open Jaeger UI
open http://localhost:16686
```

### 3. Initialize Tracing in Your Application

```python
from ejc.monitoring.opentelemetry_tracer import initialize_tracing

# Initialize with Jaeger export
tracer = initialize_tracing(
    service_name="eje-production",
    jaeger_endpoint="http://localhost:14268/api/traces",
    sampling_rate=1.0  # Sample all traces (adjust for production)
)
```

### 4. Use Decorators to Trace Functions

```python
from ejc.monitoring.opentelemetry_tracer import trace_decision, trace_critic

@trace_decision("aggregate_decision")
def aggregate_critics(critic_results):
    """Main decision aggregation - automatically traced"""
    # Your aggregation logic
    return {
        "overall_verdict": "APPROVE",
        "avg_confidence": 0.95,
        "details": critic_results
    }

@trace_critic("bias_critic")
def run_bias_critic(input_text):
    """Bias critic - automatically traced as child span"""
    # Your critic logic
    return {
        "verdict": "APPROVE",
        "confidence": 0.9,
        "weight": 1.0
    }
```

### 5. View Traces in Jaeger UI

1. Open http://localhost:16686
2. Select service: `eje-production`
3. Click "Find Traces"
4. Explore decision traces with nested critic spans

## Configuration

### Environment Variables

```bash
# Jaeger endpoint for trace export
export JAEGER_ENDPOINT="http://jaeger:14268/api/traces"

# Sampling rate (0.0 to 1.0)
export TRACE_SAMPLING_RATE="0.1"  # Sample 10% of traces
```

### Programmatic Configuration

```python
from ejc.monitoring.opentelemetry_tracer import initialize_tracing

tracer = initialize_tracing(
    service_name="eje-prod",
    jaeger_endpoint="http://jaeger:14268/api/traces",
    sampling_rate=0.1,  # 10% sampling for production
    console_export=False  # Set True for debugging
)
```

### Sampling Strategies

**Development**:
```python
sampling_rate=1.0  # Sample all traces
console_export=True  # See traces in console
```

**Production - High Traffic**:
```python
sampling_rate=0.01  # Sample 1% of traces
```

**Production - Standard**:
```python
sampling_rate=0.1  # Sample 10% of traces
```

**Critical Path Monitoring**:
```python
# Use parent-based sampling (already default)
# Child spans inherit parent sampling decision
sampling_rate=1.0
```

## Usage Patterns

### Pattern 1: Decorator-Based Tracing (Recommended)

```python
from ejc.monitoring.opentelemetry_tracer import trace_decision, trace_critic

@trace_decision("main_decision_pipeline")
def process_request(request_data):
    """Automatically creates root span for decision"""

    # Child spans automatically created for each critic
    bias_result = evaluate_bias(request_data)
    policy_result = check_policy(request_data)
    precedent_result = lookup_precedents(request_data)

    return aggregate_results([bias_result, policy_result, precedent_result])

@trace_critic("bias_critic")
def evaluate_bias(data):
    """Automatically creates child span"""
    return {"verdict": "APPROVE", "confidence": 0.95}

@trace_critic("policy_critic")
def check_policy(data):
    """Automatically creates child span"""
    return {"verdict": "APPROVE", "confidence": 0.90}

@trace_critic("precedent_critic")
def lookup_precedents(data):
    """Automatically creates child span"""
    return {"verdict": "APPROVE", "confidence": 0.85}
```

### Pattern 2: Context Manager for Custom Spans

```python
from ejc.monitoring.opentelemetry_tracer import trace_span

def process_with_custom_spans(case_data):
    """Use context managers for fine-grained control"""

    with trace_span("database_lookup", case_id=case_data["id"]):
        case_history = db.query(case_data["id"])

    with trace_span("ml_inference", model="bert-base"):
        embeddings = model.encode(case_data["text"])

    with trace_span("similarity_search", threshold=0.8):
        similar_cases = vector_db.search(embeddings)

    return similar_cases
```

### Pattern 3: Manual Span Management

```python
from ejc.monitoring.opentelemetry_tracer import start_span
from opentelemetry.trace import Status, StatusCode

def process_with_manual_spans(data):
    """Manual span management for complex workflows"""
    span = start_span("complex_operation", operation_id="12345")

    try:
        # Do work
        result = perform_operation(data)

        # Add custom attributes
        span.set_attribute("eje.result_count", len(result))
        span.set_attribute("eje.processing_time", 0.5)

        span.set_status(Status(StatusCode.OK))
        return result

    except Exception as e:
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.record_exception(e)
        raise

    finally:
        span.end()
```

### Pattern 4: Adding Events to Spans

```python
from ejc.monitoring.opentelemetry_tracer import (
    add_span_event,
    trace_precedent_lookup,
    trace_policy_check,
    trace_conflict_detected
)

@trace_decision("decision_with_events")
def make_decision(case_data):
    """Decision function with event recording"""

    # Record precedent lookup
    precedents = find_precedents(case_data)
    trace_precedent_lookup(len(precedents))

    # Record policy checks
    gdpr_compliant = check_gdpr(case_data)
    trace_policy_check("gdpr", gdpr_compliant)

    hipaa_compliant = check_hipaa(case_data)
    trace_policy_check("hipaa", hipaa_compliant)

    # Aggregate critics
    results = run_all_critics(case_data)

    # Detect conflicts
    if has_conflict(results):
        trace_conflict_detected("verdict_mismatch", "high")

    return aggregate(results)
```

### Pattern 5: Trace ID Logging

```python
from ejc.monitoring.opentelemetry_tracer import get_trace_id, get_span_id
import logging

logger = logging.getLogger(__name__)

@trace_decision("logged_decision")
def make_decision_with_logging(case_data):
    """Include trace IDs in logs for correlation"""
    trace_id = get_trace_id()
    span_id = get_span_id()

    logger.info(f"Processing decision [trace_id={trace_id}, span_id={span_id}]")

    result = process_decision(case_data)

    logger.info(f"Decision complete [trace_id={trace_id}, verdict={result['verdict']}]")

    return result
```

## Integration Examples

### Example 1: EJE Decision Pipeline

```python
from ejc.monitoring.opentelemetry_tracer import (
    initialize_tracing,
    trace_decision,
    trace_critic,
    trace_span
)

# Initialize once at application startup
initialize_tracing(
    service_name="eje-decision-engine",
    jaeger_endpoint="http://jaeger:14268/api/traces",
    sampling_rate=0.1
)

@trace_decision("eje_decision_pipeline")
def execute_decision_pipeline(input_data):
    """
    Main decision pipeline with automatic tracing.

    Creates a root span containing all critic executions.
    """
    # Load critics
    critics = load_critics()

    # Execute each critic (child spans automatically created)
    critic_results = []
    for critic in critics:
        result = execute_critic(critic, input_data)
        critic_results.append(result)

    # Aggregate results
    with trace_span("aggregate_results", critic_count=len(critic_results)):
        final_decision = aggregate(critic_results)

    return final_decision

@trace_critic("dynamic_critic")
def execute_critic(critic, input_data):
    """
    Execute a single critic with tracing.

    Critic name is set dynamically based on critic config.
    """
    return critic.evaluate(input_data)
```

### Example 2: Async Tracing

```python
import asyncio
from ejc.monitoring.opentelemetry_tracer import trace_decision, trace_critic

@trace_decision("async_decision")
async def async_decision_pipeline(data):
    """Tracing works with async functions"""

    # Run critics concurrently
    results = await asyncio.gather(
        async_bias_critic(data),
        async_policy_critic(data),
        async_precedent_critic(data)
    )

    return aggregate_results(results)

@trace_critic("async_bias_critic")
async def async_bias_critic(data):
    """Async critic with automatic tracing"""
    await asyncio.sleep(0.1)  # Simulate async work
    return {"verdict": "APPROVE", "confidence": 0.9}
```

### Example 3: Multi-Service Tracing

```python
import requests
from opentelemetry.propagate import inject
from ejc.monitoring.opentelemetry_tracer import trace_span

@trace_span("call_external_service")
def call_external_critic_service(data):
    """
    Propagate trace context to external service.

    Trace IDs are automatically injected into HTTP headers.
    """
    headers = {}

    # Inject trace context into headers
    inject(headers)

    # Call external service with trace context
    response = requests.post(
        "http://critic-service:8000/evaluate",
        json=data,
        headers=headers
    )

    return response.json()
```

## Jaeger Deployment

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14268:14268"  # HTTP collector
      - "6831:6831/udp"  # Jaeger agent
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - SPAN_STORAGE_TYPE=memory
    networks:
      - eje-network

  eje:
    build: .
    environment:
      - JAEGER_ENDPOINT=http://jaeger:14268/api/traces
      - TRACE_SAMPLING_RATE=0.1
    depends_on:
      - jaeger
    networks:
      - eje-network

networks:
  eje-network:
```

Start services:
```bash
docker-compose up -d
```

### Kubernetes

```yaml
# jaeger-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        ports:
        - containerPort: 16686
          name: ui
        - containerPort: 14268
          name: collector
        - containerPort: 6831
          protocol: UDP
          name: agent
        env:
        - name: SPAN_STORAGE_TYPE
          value: elasticsearch
        - name: ES_SERVER_URLS
          value: http://elasticsearch:9200
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  selector:
    app: jaeger
  ports:
  - port: 16686
    targetPort: 16686
    name: ui
  - port: 14268
    targetPort: 14268
    name: collector
  - port: 6831
    protocol: UDP
    targetPort: 6831
    name: agent
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f jaeger-deployment.yaml
```

### Production with Elasticsearch Backend

```yaml
# jaeger with elasticsearch storage
jaeger:
  image: jaegertracing/all-in-one:latest
  environment:
    - SPAN_STORAGE_TYPE=elasticsearch
    - ES_SERVER_URLS=http://elasticsearch:9200
    - ES_INDEX_PREFIX=eje-traces
  depends_on:
    - elasticsearch

elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  volumes:
    - es_data:/usr/share/elasticsearch/data
```

## Performance Analysis

### Measuring Overhead

```python
import time
from ejc.monitoring.opentelemetry_tracer import initialize_tracing, trace_decision

# Initialize tracing
initialize_tracing(service_name="performance-test", sampling_rate=1.0)

def measure_overhead():
    """Measure tracing overhead"""

    # Baseline without tracing
    def untraced_function():
        return sum(range(10000))

    # Function with tracing
    @trace_decision()
    def traced_function():
        return sum(range(10000))

    # Warmup
    for _ in range(100):
        untraced_function()
        traced_function()

    # Measure untraced
    start = time.perf_counter()
    for _ in range(1000):
        untraced_function()
    untraced_time = time.perf_counter() - start

    # Measure traced
    start = time.perf_counter()
    for _ in range(1000):
        traced_function()
    traced_time = time.perf_counter() - start

    overhead = ((traced_time - untraced_time) / untraced_time) * 100
    print(f"Tracing overhead: {overhead:.2f}%")

if __name__ == "__main__":
    measure_overhead()
```

**Expected Results**:
- Simple operations: < 5% overhead
- Complex operations: < 1% overhead
- Production workloads: < 0.5% overhead

### Optimizing Performance

1. **Adjust Sampling Rate**:
```python
# High traffic: sample less
initialize_tracing(sampling_rate=0.01)  # 1%

# Critical path: sample more
initialize_tracing(sampling_rate=1.0)  # 100%
```

2. **Use Batch Export**:
```python
# Spans are batched automatically
# Configure batch size if needed
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    max_export_batch_size=512
)
```

3. **Disable Console Export in Production**:
```python
initialize_tracing(
    console_export=False  # Significant performance impact
)
```

## Troubleshooting

### Traces Not Appearing in Jaeger

**Problem**: No traces visible in Jaeger UI

**Solutions**:
1. Check Jaeger is running:
   ```bash
   curl http://localhost:16686
   ```

2. Verify EJE is sending spans:
   ```bash
   # Enable console export to see spans
   TRACE_SAMPLING_RATE=1.0 python -c "
   from ejc.monitoring.opentelemetry_tracer import initialize_tracing, trace_decision
   initialize_tracing(console_export=True, sampling_rate=1.0)

   @trace_decision()
   def test():
       return {'verdict': 'APPROVE'}

   test()
   "
   ```

3. Check Jaeger endpoint is correct:
   ```python
   # Should be collector endpoint, not UI
   jaeger_endpoint="http://localhost:14268/api/traces"  # ✓
   jaeger_endpoint="http://localhost:16686"  # ✗
   ```

4. Verify sampling rate:
   ```python
   # Make sure sampling is enabled
   initialize_tracing(sampling_rate=1.0)  # Sample all traces
   ```

### Span Relationships Not Correct

**Problem**: Spans appear flat instead of nested

**Solution**: Ensure using `start_as_current_span`:
```python
# Correct - creates parent-child relationship
with tracer.start_as_current_span("parent"):
    with tracer.start_as_current_span("child"):
        pass

# Incorrect - creates sibling spans
span1 = tracer.start_span("span1")
span2 = tracer.start_span("span2")
```

### High Performance Overhead

**Problem**: Tracing adds significant latency

**Solutions**:
1. Reduce sampling rate:
   ```python
   initialize_tracing(sampling_rate=0.1)  # 10%
   ```

2. Disable console export:
   ```python
   initialize_tracing(console_export=False)
   ```

3. Use batch processing (default):
   ```python
   # Already enabled by default
   BatchSpanProcessor(exporter)
   ```

4. Profile and optimize traced code:
   ```python
   # Don't trace hot loops
   def process_batch(items):
       for item in items:  # Don't trace each iteration
           process_item(item)
   ```

### Trace Context Not Propagating

**Problem**: Distributed traces appear disconnected

**Solution**: Propagate context explicitly for non-HTTP:
```python
from opentelemetry import context
from opentelemetry.propagate import inject, extract

# Sender
def send_message(data):
    headers = {}
    inject(headers)  # Inject trace context
    queue.send(data, headers=headers)

# Receiver
def receive_message(message):
    ctx = extract(message.headers)  # Extract trace context
    with tracer.start_as_current_span("process_message", context=ctx):
        process(message.data)
```

## Best Practices

### DO ✓

- **Use decorators for functions**: Simplest and most maintainable
- **Trace at appropriate granularity**: Decision and critic level
- **Add meaningful attributes**: Verdict, confidence, case IDs
- **Propagate trace context**: Across service boundaries
- **Use sampling in production**: Reduce overhead and storage
- **Include trace IDs in logs**: For correlation
- **Test tracing overhead**: Validate < 5% impact

### DON'T ✗

- **Trace hot loops**: Don't create spans for every iteration
- **Add sensitive data to spans**: PII, credentials, etc.
- **Sample at 100% in production**: Use 1-10% sampling
- **Create too many spans**: Keep hierarchy manageable (< 50 spans)
- **Forget error handling**: Always set span status
- **Block on span export**: Use async/batch export
- **Hardcode endpoints**: Use environment variables

## Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/observability-primer/)
- [EJE Monitoring Guide](./prometheus_setup.md)

## Support

For issues or questions:
- Check Jaeger logs: `docker logs jaeger`
- EJE Documentation: `docs/`
- GitHub Issues: https://github.com/eleanor-project/eje/issues

---

**Last Updated**: 2025-12-02
**OpenTelemetry Version**: 1.20.0+
**Jaeger Version**: 1.50.0+
