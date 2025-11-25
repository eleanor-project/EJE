# EJC Architecture Documentation
**Ethical Jurisprudence Core - Technical Architecture for Pilot Demo**

---

## System Overview

ELEANOR (EJC) is a multi-critic, precedent-driven ethical oversight system that provides transparent, auditable decision-making for high-stakes AI applications.

---

## Current Architecture (Containerized)

```
┌─────────────────────────────────────────────────────────────────┐
│                          External Clients                        │
│                  (Web Browsers, API Consumers)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS (Port 443)
                             │ HTTP (Port 8000, 8049)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                            │
│                         (eje-network)                            │
│                                                                   │
│  ┌──────────────────┐   ┌──────────────────┐  ┌──────────────┐│
│  │   EJC Dashboard  │   │    EJC API       │  │   PostgreSQL ││
│  │    (Flask)       │   │   (FastAPI)      │  │   Database   ││
│  │   Port: 8049     │   │   Port: 8000     │  │   Port: 5432 ││
│  └────────┬─────────┘   └────────┬─────────┘  └──────┬───────┘│
│           │                       │                    │        │
│           │   ┌───────────────────┴────────────────────┘        │
│           │   │                                                 │
│           ▼   ▼                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │          Ethical Reasoning Engine (Core EJC Logic)              │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │  Critic Orchestration & Parallel Execution   │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │    │
│  │  │ OpenAI  │ │ Claude  │ │ Gemini  │ │ Custom  │   │    │
│  │  │ Critic  │ │ Critic  │ │ Critic  │ │ Critics │   │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │   Aggregator (Weighted Voting Logic)         │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │   Precedent Manager (Semantic Search)        │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │   Audit Logger (Complete Decision Trail)     │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌───────────────┐                                             │
│  │  Redis Cache  │  (Optional - for distributed caching)       │
│  │  Port: 6379   │                                             │
│  └───────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Flow Sequence

```
1. User/System                2. API Gateway              3. Ethical Reasoning Engine
   │                             │                           │
   │  POST /evaluate             │                           │
   ├────────────────────────────>│                           │
   │  {case: "..."}              │  Validate Input           │
   │                             ├──────────────────────────>│
   │                             │                           │ Check Cache
   │                             │                           ├──────────┐
   │                             │                           │<─────────┘
   │                             │                           │
   │                             │                           │ Load Critics
   │                             │                           ├──────────┐
   │                             │                           │<─────────┘
   │                             │                           │
   │                             │                           │ Parallel Execution
   │                             │                           │ ┌────────────┐
   │                             │                           ├>│OpenAI      │
   │                             │                           │ │Verdict: A  │
   │                             │                           │<┤Conf: 0.85  │
   │                             │                           │ └────────────┘
   │                             │                           │ ┌────────────┐
   │                             │                           ├>│Claude      │
   │                             │                           │ │Verdict: A  │
   │                             │                           │<┤Conf: 0.92  │
   │                             │                           │ └────────────┘
   │                             │                           │ ┌────────────┐
   │                             │                           ├>│Gemini      │
   │                             │                           │ │Verdict: R  │
   │                             │                           │<┤Conf: 0.75  │
   │                             │                           │ └────────────┘
   │                             │                           │
   │                             │                           │ Aggregate Results
   │                             │                           ├──────────┐
   │                             │                           │<─────────┘
   │                             │                           │
   │                             │                           │ Lookup Precedents
   │                             │                     ┌─────┤
   │                             │                     │  DB │
   │                             │                     └────>│
   │                             │                           │
   │                             │                           │ Store Precedent
   │                             │                     ┌─────┤
   │                             │                     │  DB │
   │                             │                     └────>│
   │                             │                           │
   │                             │                           │ Audit Log
   │                             │                     ┌─────┤
   │                             │                     │  DB │
   │                             │                     └────>│
   │                             │  Return Decision          │
   │  Response                   │<──────────────────────────┤
   │<────────────────────────────┤                           │
   │  {verdict, justification}   │                           │
   │                             │                           │
```

---

## Component Descriptions

### 1. API Gateway (FastAPI)
**Purpose:** REST API interface for external systems
**Technology:** FastAPI + Uvicorn
**Responsibilities:**
- Request validation
- Authentication/authorization (future)
- Rate limiting (future)
- API documentation (OpenAPI/Swagger)
- Health checks

**Key Endpoints:**
- `POST /evaluate` - Submit case for evaluation
- `GET /health` - System health check
- `GET /stats` - Performance metrics
- `GET /precedents` - Search similar cases
- `GET /critics` - List available critics

### 2. Ethical Reasoning Engine
**Purpose:** Core orchestration and decision logic
**Technology:** Python 3.11
**Responsibilities:**
- Load and validate configuration
- Orchestrate critic execution
- Manage parallel processing
- Cache results
- Handle errors and retries
- Coordinate with all subsystems

**Key Classes:**
- `DecisionEngine` - Main orchestrator
- `CriticLoader` - Plugin management
- `Aggregator` - Result aggregation
- `PrecedentManager` - Historical lookup
- `AuditLogger` - Decision logging

### 3. Critic System
**Purpose:** Independent ethical evaluation perspectives
**Technology:** Python + LLM APIs
**Responsibilities:**
- Evaluate cases from specific ethical lens
- Return verdict + confidence + justification
- Handle API failures gracefully
- Respect timeouts

**Critic Types:**
- **Rights Critic** (OpenAI) - Focuses on rights protection
- **Equity Critic** (Gemini) - Focuses on fairness
- **Utilitarian Critic** (Claude) - Focuses on outcomes
- **Custom Critics** - Domain-specific rules

**Configuration:**
```yaml
critic_weights:
  Rights: 1.0
  Equity: 0.9
  Utilitarian: 1.2

critic_priorities:
  Security: "override"  # Can veto others
  Human: "override"
```

### 4. Aggregator
**Purpose:** Combine critic opinions into final decision
**Technology:** Weighted voting algorithm
**Responsibilities:**
- Apply critic weights
- Handle priority/override critics
- Calculate confidence scores
- Determine final verdict (ALLOW/DENY/REVIEW)
- Generate explanation

**Verdict Logic:**
```
If any OVERRIDE critic says DENY -> DENY
Else if weighted DENY votes > threshold -> DENY
Else if ambiguity > threshold -> REVIEW
Else -> ALLOW
```

### 5. Precedent Manager
**Purpose:** Store and retrieve similar past decisions
**Technology:** PostgreSQL + sentence-transformers
**Responsibilities:**
- Generate case embeddings
- Semantic similarity search
- Store decision history
- Retrieve similar precedents
- Provide consistency

**Similarity Algorithm:**
- Uses sentence-transformers to create embeddings
- Cosine similarity to find matches
- Configurable threshold (default: 0.8)
- Returns top N matches (default: 5)

### 6. Audit Logger
**Purpose:** Complete decision trail for compliance
**Technology:** PostgreSQL
**Responsibilities:**
- Log every decision
- Store complete context
- Enable forensic review
- Support compliance audits
- Generate reports

**Logged Data:**
- Request ID (UUID)
- Timestamp
- Input case (full text)
- All critic outputs
- Final decision
- Precedent references
- Cache hit/miss

### 7. Dashboard
**Purpose:** Human interface for monitoring and review
**Technology:** Flask + HTML/CSS/JavaScript
**Responsibilities:**
- Real-time decision visualization
- Historical review
- Critic deliberation display
- Precedent browser
- Export functionality

**Features:**
- Live decision feed
- Critic opinion comparison
- Confidence visualization
- Precedent similarity
- Filter by verdict/date
- Export to CSV/JSON

### 8. Database (PostgreSQL)
**Purpose:** Persistent storage for all data
**Technology:** PostgreSQL 15
**Responsibilities:**
- Audit log storage
- Precedent storage
- Critic performance metrics
- User feedback
- System configuration

**Key Tables:**
- `audit_log` - All decisions
- `precedents` - Historical cases
- `feedback` - Human corrections
- `critic_performance` - Metrics

---

## Data Flow Examples

### Example 1: Healthcare Decision
```
Input:
  "Should we approve experimental treatment for patient 
   with rare condition? Success rate 60%, high cost."

Critics Execute (Parallel):
  - Rights Critic → ALLOW (0.88)
    "Patient has right to try"
  - Equity Critic → REVIEW (0.72)
    "Cost may create access inequality"
  - Utilitarian Critic → ALLOW (0.85)
    "60% success justifies risk"
  - HIPAA Critic → ALLOW (0.95)
    "No privacy violations"

Aggregation:
  Weighted average: ALLOW
  Confidence: 0.85
  Ambiguity: Low
  
Precedent Lookup:
  Found 3 similar cases (similarity > 0.8)
  All resulted in ALLOW
  
Final Decision: ALLOW
Explanation: "Patient autonomy and reasonable success
  rate support approval. Monitor equity concerns."
```

### Example 2: Financial Decision with Conflict
```
Input:
  "Approve loan to customer with debt-to-income ratio 55%"

Critics Execute:
  - Regulation Critic → DENY (0.95) [OVERRIDE]
    "Exceeds regulatory limit of 50%"
  - Equity Critic → ALLOW (0.70)
    "Customer from underserved community"
  - Risk Critic → DENY (0.88)
    "High default probability"

Aggregation:
  OVERRIDE critic triggered: DENY
  
Final Decision: DENY
Explanation: "Regulatory compliance requires denial.
  Regulation Critic has override authority."
```

---

## Deployment Architecture

### Development Environment
```
├─ Local Machine
   ├─ Docker Desktop
   ├─ VSCode/IDE
   ├─ Git
   └─ docker-compose up
```

### Pilot Demo Environment
```
├─ Cloud Provider (AWS/GCP/Azure)
   ├─ Container Service (ECS/Cloud Run/AKS)
   ├─ Managed PostgreSQL (RDS/Cloud SQL/Azure DB)
   ├─ Load Balancer (ALB/Cloud LB/Azure LB)
   ├─ SSL Certificate (ACM/Let's Encrypt)
   └─ Monitoring (CloudWatch/Operations/Monitor)
```

### Production Architecture (Future)
```
┌───────────────────────────────────────────────────┐
│              Load Balancer + WAF                  │
└────────────────────┬──────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌─────────┐             ┌─────────┐
   │ EJC API │             │ EJC API │  (Auto-scaling)
   │ Pod 1   │             │ Pod 2   │
   └────┬────┘             └────┬────┘
        │                       │
        └───────────┬───────────┘
                    ▼
         ┌────────────────────┐
         │  Redis Cluster     │  (Caching)
         └────────────────────┘
                    │
                    ▼
         ┌────────────────────┐
         │  PostgreSQL        │  (Primary/Replica)
         │  High Availability │
         └────────────────────┘
```

---

## Security Architecture

### Authentication & Authorization (Future Phase)
```
Client → API Gateway → JWT Validation → Route to Service
                    ↓
                Audit Log
```

### Data Security
- **At Rest:** PostgreSQL encryption
- **In Transit:** TLS 1.3
- **API Keys:** Environment variables only
- **Secrets:** Never logged or exposed

### Input Validation
```
User Input → Pydantic Validation → Sanitization → Processing
                ↓
          Reject Invalid
```

---

## Scalability Considerations

### Current Capacity (Single Node)
- **Requests/second:** ~10-20 (dependent on critic API latency)
- **Concurrent requests:** 5-10
- **Database:** 100K+ decisions

### Scaling Strategies

**Horizontal Scaling:**
```
Single Container → Multiple Containers → Load Balanced
     10 req/s          30 req/s            100+ req/s
```

**Vertical Scaling:**
```
Increase:
- CPU cores (for parallel critics)
- RAM (for caching)
- Database connections
```

**Caching Strategy:**
```
Request → Check Cache → Hit: Return (fast!)
                      → Miss: Process → Store → Return
```

### Performance Optimizations

1. **Critic Parallelization**
   - ThreadPoolExecutor for concurrent LLM calls
   - Configurable max_workers
   - Non-blocking I/O

2. **Result Caching**
   - In-memory LRU cache
   - Configurable size (default: 1000)
   - Hash-based lookup

3. **Database Optimization**
   - Connection pooling
   - Indexed queries
   - Batch inserts

4. **Async Processing** (Future)
   - Message queue for background tasks
   - Webhook callbacks for long operations
   - Priority queue for urgent decisions

---

## Monitoring & Observability

### Health Checks
```
GET /health → {
  "status": "healthy",
  "critics_loaded": 4,
  "database_connected": true,
  "cache_hit_rate": 0.45
}
```

### Metrics to Track
- API response time (p50, p95, p99)
- Critic execution time per model
- Cache hit rate
- Error rate by critic
- Database query performance
- Verdict distribution
- Confidence score distribution

### Logging Strategy
```
Level    | Use Case
---------|------------------------------------------
DEBUG    | Detailed critic execution
INFO     | Request/response logging
WARNING  | Degraded performance, retries
ERROR    | Critic failures, API errors
CRITICAL | System failures, data corruption
```

---

## Disaster Recovery

### Backup Strategy
```
Daily:
  - Full PostgreSQL backup
  - Configuration files
  - Custom critic code

Hourly:
  - Incremental database backup

Retention:
  - 30 days rolling
```

### Recovery Procedures
```
1. Identify failure point
2. Restore from last known good backup
3. Replay audit log if needed
4. Verify system health
5. Resume operations
```

---

## Integration Patterns

### REST API Integration
```python
import requests

response = requests.post(
    "https://eje.example.com/evaluate",
    json={
        "text": "Your case here",
        "domain": "healthcare"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

decision = response.json()
```

### SDK Integration (Future)
```python
from eje_client import EJEClient

client = EJEClient(api_key="YOUR_KEY")
decision = client.evaluate(
    case="Your case here",
    domain="healthcare"
)
```

### Webhook Integration (Future)
```python
# EJC calls your webhook when decision complete
@app.post("/eje-callback")
def handle_decision(decision: dict):
    # Process decision
    store_decision(decision)
    notify_stakeholders(decision)
```

---

## Configuration Management

### Environment-Based Config
```
config/
├── global.yaml         # Base configuration
├── development.yaml    # Dev overrides
├── pilot_demo.yaml     # Pilot-specific
└── production.yaml     # Production settings
```

### Priority Order
```
1. Environment variables (highest)
2. environment-specific YAML
3. global.yaml (lowest)
```

---

## Version History

- **v1.0.0:** Initial release with core critics
- **v1.1.0:** Added precedent system
- **v1.2.0:** Plugin architecture
- **v1.3.0:** Enhanced security and monitoring
- **v1.4.0:** (Current) Containerization and API

---

## Future Roadmap

### Phase 1 (Current): Pilot Demo
- ✅ Containerization
- ✅ REST API
- ✅ PostgreSQL migration
- 🔄 Dashboard enhancement

### Phase 2: Production Deployment
- Authentication/authorization
- Multi-tenancy support
- Advanced monitoring
- High availability setup

### Phase 3: Scale
- Distributed deployment
- Geographic redundancy
- Advanced caching
- Performance optimization

### Phase 4: Advanced Features
- Federated governance
- Cross-organization precedent sharing
- Advanced AI critics
- Self-improving system

---

## Questions or Issues?

**Documentation:** https://eje.readthedocs.io
**Repository:** https://github.com/eleanor-project/EJC
**Issues:** https://github.com/eleanor-project/EJC/issues
**Contact:** will@eleanorproject.org

---

*This architecture document reflects the containerized system design for the pilot demonstration. For production deployment, additional considerations around security, compliance, and scale will be addressed.*
