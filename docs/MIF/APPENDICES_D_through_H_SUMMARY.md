# Appendices D-H: Quick Reference

**Rights-Based Jurisprudence Architecture (RBJA) v3.0**  
**Document Status:** Production Reference  
**Last Updated:** November 2024

---

## Note to Reader

Due to the comprehensive nature of Appendices A-C (covering Critic Calibration, Testing, and Schemas), Appendices D-H are provided in summary form here. Full detailed versions can be generated on request or found in the project repository.

---

# Appendix D: Developer Integration Guide

## Quick Start Integration

### Python Integration

```python
from ejc.core.decision_engine import EthicalReasoningEngine

# Initialize engine
engine = EthicalReasoningEngine("config/global.yaml")

# Evaluate a decision
result = engine.evaluate({
    "text": "Should we approve this action?",
    "domain": "healthcare"
})

# Check verdict
if result['final_decision']['overall_verdict'] == 'ALLOW':
    # Proceed with action
    execute_action()
elif result['final_decision']['overall_verdict'] == 'DENY':
    # Block action
    log_denial(result['final_decision']['reason'])
else:  # REVIEW
    # Escalate to human
    escalate_for_review(result['request_id'])
```

### REST API Integration

```bash
curl -X POST https://eleanor.example.com/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "text": "Deploy facial recognition in retail store",
    "domain": "retail",
    "priority": "normal"
  }'
```

### Node.js/TypeScript Integration

```typescript
import { ELEANORClient } from '@eleanor/client';

const client = new ELEANORClient({
  apiKey: process.env.ELEANOR_API_KEY,
  baseURL: 'https://eleanor.example.com'
});

const result = await client.evaluate({
  text: 'Should we proceed with this decision?',
  domain: 'finance',
  priority: 'high'
});

if (result.finalDecision.overallVerdict === 'ALLOW') {
  await proceedWithAction();
}
```

### Java Integration

```java
import ai.eleanor.ELEANORClient;
import ai.eleanor.models.CaseInput;
import ai.eleanor.models.DecisionResponse;

ELEANORClient client = new ELEANORClient.Builder()
    .apiKey(System.getenv("ELEANOR_API_KEY"))
    .baseURL("https://eleanor.example.com")
    .build();

CaseInput case = new CaseInput.Builder()
    .text("Should we approve this transaction?")
    .domain("finance")
    .priority("normal")
    .build();

DecisionResponse response = client.evaluate(case);

if (response.getFinalDecision().getOverallVerdict() == Verdict.ALLOW) {
    processTransaction();
}
```

## Integration Patterns

### Pattern 1: Synchronous Blocking

```mermaid
sequenceDiagram
    participant App
    participant ELEANOR
    
    App->>ELEANOR: POST /evaluate
    ELEANOR->>App: Decision response
    alt ALLOW
        App->>App: Execute action
    else DENY
        App->>App: Block action
    else REVIEW
        App->>App: Queue for human
    end
```

**Use When:** Low-latency requirements, immediate decision needed

### Pattern 2: Asynchronous with Callback

```mermaid
sequenceDiagram
    participant App
    participant ELEANOR
    participant Webhook
    
    App->>ELEANOR: POST /evaluate?async=true
    ELEANOR->>App: {request_id}
    App->>App: Return to user
    
    ELEANOR->>ELEANOR: Process decision
    ELEANOR->>Webhook: POST /callback
    Webhook->>App: Update decision status
```

**Use When:** High-throughput scenarios, acceptable delay

### Pattern 3: Pre-Decision Check

```python
# Check decision before expensive operation
preliminary_check = engine.evaluate({
    "text": "preliminary check for expensive operation",
    "domain": "compute"
})

if preliminary_check['final_decision']['overall_verdict'] != 'DENY':
    # Only proceed with expensive operation if not denied
    result = perform_expensive_operation()
    
    # Final governance check
    final_check = engine.evaluate({
        "text": f"finalize operation with result: {result}",
        "domain": "compute"
    })
```

## Error Handling

```python
from ejc.exceptions import CriticException, ValidationException

try:
    result = engine.evaluate(case)
except ValidationException as e:
    # Invalid input
    log.error(f"Invalid case input: {e}")
    return {"error": "Invalid input", "details": str(e)}
    
except CriticException as e:
    # Critic failure
    log.error(f"Critic failed: {e}")
    # Decide: fail safe (deny) or escalate
    return {"verdict": "REVIEW", "reason": "System error, human review required"}
    
except Exception as e:
    # Unknown error
    log.critical(f"Unexpected error: {e}")
    # Fail safe - deny action
    return {"verdict": "DENY", "reason": "System error"}
```

## Best Practices

1. **Always handle REVIEW verdicts** - Don't auto-approve
2. **Log all decisions** - Include request_id for tracing
3. **Implement timeouts** - Don't block indefinitely
4. **Cache when appropriate** - But be careful with sensitive decisions
5. **Monitor performance** - Track latency and error rates
6. **Fail safe** - When in doubt, DENY or REVIEW

---

# Appendix E: Precedent Governance Manual

## Precedent Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: Significant Decision
    Created --> Active: Passes Review
    Created --> Rejected: Failed Review
    Active --> Referenced: Used in Decision
    Referenced --> Active: Continue Use
    Active --> UnderReview: Periodic Review
    UnderReview --> Active: Still Valid
    UnderReview --> Deprecated: Policy Changed
    Deprecated --> Archived: No Longer Used
    Archived --> [*]
    Rejected --> [*]
```

## Creating Precedents

### Automatic Creation Triggers

1. **High Dissent** (dissent_index > 0.3)
2. **Human Override** (human modified decision)
3. **Novel Case** (no similar precedents found)
4. **Flagged Decision** (critical flags present)
5. **Configured Sampling** (random % for diversity)

### Precedent Quality Criteria

```python
def should_create_precedent(decision_bundle):
    """Determine if decision should become precedent"""
    
    # Always create for human overrides
    if decision_bundle.get('human_override'):
        return True
    
    # High dissent cases
    if decision_bundle['final_decision']['dissent_index'] > 0.3:
        return True
    
    # Novel cases (low similarity to existing)
    if not decision_bundle['precedent_refs'] or \
       max(p['similarity'] for p in decision_bundle['precedent_refs']) < 0.7:
        return True
    
    # DENY decisions in high-stakes domains
    if decision_bundle['input']['domain'] in ['healthcare', 'criminal_justice']:
        if decision_bundle['final_decision']['overall_verdict'] == 'DENY':
            return True
    
    # Random sampling (10%)
    if random.random() < 0.10:
        return True
    
    return False
```

## Precedent Retrieval

### Semantic Search

```python
def retrieve_similar_precedents(case, limit=5):
    """Find similar precedents using semantic search"""
    
    # Generate embedding for current case
    embedding = generate_embedding(case['text'])
    
    # Cosine similarity search in database
    query = """
        SELECT 
            precedent_id,
            case_hash,
            decision,
            1 - (embedding <=> %s::vector) AS similarity
        FROM precedents
        WHERE domain = %s
          AND jurisdiction = %s
          AND migration_status != 'PARTIAL'
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    
    results = db.execute(query, (
        embedding,
        case['domain'],
        case.get('jurisdiction', 'US'),
        embedding,
        limit
    ))
    
    # Filter by similarity threshold
    return [r for r in results if r['similarity'] >= 0.8]
```

## Precedent Conflicts

### Detecting Conflicts

```python
def detect_precedent_conflicts(precedents):
    """Identify conflicting precedent recommendations"""
    
    if len(precedents) < 2:
        return None
    
    verdicts = [p['decision']['overall_verdict'] for p in precedents]
    
    # Check for contradictions
    if 'ALLOW' in verdicts and 'DENY' in verdicts:
        return {
            'type': 'VERDICT_CONFLICT',
            'conflicting_precedents': precedents,
            'action': 'ESCALATE',
            'reason': 'Conflicting precedents found - human judgment required'
        }
    
    return None
```

## Precedent Maintenance

### Monthly Review Process

1. **Usage Analysis** - Identify frequently-used precedents
2. **Accuracy Check** - Compare to recent human overrides
3. **Conflict Detection** - Find contradictory precedents
4. **Deprecation Review** - Mark outdated precedents
5. **Documentation Update** - Annotate precedents with learnings

---

# Appendix F: Precedent Migration Protocol

## Migration Process

```mermaid
flowchart TD
    A[Old Precedent v2.1] --> B[Load Migration Map]
    B --> C[Map Fields]
    C --> D{All Fields<br/>Mappable?}
    D -->|Yes| E[Generate Required<br/>New Fields]
    D -->|No| F[Mark as PARTIAL]
    E --> G{New Fields<br/>Generated?}
    G -->|Yes| H[Mark as MIGRATED<br/>Status: NATIVE]
    G -->|No| F
    F --> I[Mark as PARTIAL<br/>Limited Use]
    H --> J[Store Migrated]
    I --> J
```

## Migration Map Example

```yaml
# migration_map_v2.1_to_v3.0.yaml
source_version: "2.1.0"
target_version: "3.0.0"
created_by: "governance_team"
approved_by: "GCR-2024-045"

field_transformations:
  # Simple rename
  case_data:
    target: input_case
    transform: identity
  
  # Type conversion
  verdict:
    target: decision.overall_verdict
    transform: uppercase  # allow -> ALLOW
  
  # Computed field
  case_hash:
    target: case_hash
    transform: sha256_normalized
    required: true
  
  # Optional new field
  embedding:
    target: embedding
    transform: generate_embedding
    required: false
    fallback: mark_partial

critic_name_mappings:
  Eleanor: RightsCritic
  Equity: EquityAnalyzer
  Risk: RiskAssessor
  Transparency: TransparencyMonitor
  Pragmatic: PragmaticValidator
  Context: ContextCritic

verdict_mappings:
  allow: ALLOW
  deny: DENY
  escalate: REVIEW
  conditional: ALLOW  # With conditions extracted

migration_tests:
  - source_file: tests/migration/v2.1_samples.json
    expected_results: tests/migration/v3.0_expected.json
```

---

# Appendix G: Deployment Architecture Reference

## Docker Compose (Single Node)

```yaml
version: '3.8'

services:
  eje-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://eje:pass@postgres/eleanor
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config:ro
      - eje_data:/app/eleanor_data
    restart: unless-stopped
  
  eje-dashboard:
    build: .
    command: ["python", "-m", "flask", "--app", "eje.server.dashboard", "run", "--host", "0.0.0.0", "--port", "8049"]
    ports:
      - "8049:8049"
    environment:
      - DATABASE_URL=postgresql://eje:pass@postgres/eleanor
      - EJE_API_URL=http://eje-api:8000
    depends_on:
      - eje-api
    volumes:
      - ./config:/app/config:ro
    restart: unless-stopped
  
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=eleanor
      - POSTGRES_USER=eje
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  eje_data:
```

## Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eje-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eje-api
  template:
    metadata:
      labels:
        app: eje-api
    spec:
      containers:
      - name: eje-api
        image: eleanor/eje:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: eje-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: openai
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: eje-api-service
spec:
  selector:
    app: eje-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

# Appendix H: Operational Runbook

## Common Operations

### 1. Deployment

```bash
# Build new version
docker-compose build

# Deploy with zero downtime
docker-compose up -d --no-deps --build eje-api

# Verify health
curl http://localhost:8000/health

# Check logs
docker-compose logs -f eje-api
```

### 2. Scaling

```bash
# Scale API pods
docker-compose up -d --scale eje-api=5

# OR in Kubernetes
kubectl scale deployment/eje-api --replicas=5
```

### 3. Backup

```bash
# Backup database
pg_dump -h localhost -U eje_user eleanor > backup_$(date +%Y%m%d).sql

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# Backup precedents
pg_dump -h localhost -U eje_user -t precedents eleanor > precedents_backup.sql
```

### 4. Restore

```bash
# Restore database
psql -h localhost -U eje_user eleanor < backup_20241125.sql

# Verify
psql -h localhost -U eje_user eleanor -c "SELECT COUNT(*) FROM audit_log;"
```

### 5. Monitoring

```bash
# Check system metrics
curl http://localhost:8000/stats

# Check critic performance
curl http://localhost:8000/stats | jq '.security_stats'

# View recent decisions
psql -h localhost -U eje_user eleanor -c "
  SELECT request_id, timestamp, 
         final_decision->>'overall_verdict' as verdict
  FROM audit_log 
  ORDER BY timestamp DESC 
  LIMIT 10;
"
```

### 6. Troubleshooting

```bash
# API not responding
docker-compose logs eje-api --tail=100

# Database connection issues
docker-compose exec postgres psql -U eje_user -d eleanor -c "SELECT 1;"

# Critic failures
psql -h localhost -U eje_user eleanor -c "
  SELECT critic_name, total_errors, last_error 
  FROM critic_performance 
  WHERE total_errors > 0;
"

# High latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/evaluate
```

## Incident Response Procedures

### Database Outage

1. Check database status: `docker-compose ps postgres`
2. Check logs: `docker-compose logs postgres`
3. If crashed, restart: `docker-compose restart postgres`
4. Verify data integrity: Run test queries
5. If corrupt, restore from backup
6. Update incident log

### Critic API Failure

1. Check which critic is failing: `GET /stats`
2. Verify API keys valid: Check `.env` file
3. Test API directly: `curl` to LLM endpoint
4. If API down, configure critic as fallback or disable temporarily
5. Monitor escalation rate (should increase)
6. Notify stakeholders

### High Escalation Rate

1. Query escalation metrics
2. Identify common patterns in escalated cases
3. Review recent precedents
4. Check if critics need recalibration
5. Escalate to governance committee if systemic issue

---

## Full Documentation Available

Complete detailed versions of Appendices D-H with:
- Step-by-step integration examples
- Architecture diagrams
- Deployment templates
- Operational procedures
- Troubleshooting guides

**Available at:** `docs/appendices/` in the project repository

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-11-25 | William Parris | Summary version for v3.0 spec |

**Note:** This is a summary document. Full appendices available in repository.
