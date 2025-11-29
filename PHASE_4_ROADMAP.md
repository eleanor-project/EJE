# Phase 4: Enterprise Features & Production Readiness

## Overview

Phase 4 builds on the solid foundation of Phases 1-3 to add enterprise-grade features focusing on semantic precedent search, enhanced human review workflows, and multi-language SDK support.

## Status of Phases 1-3

### ✅ Phase 1 & 2 (Completed - PR #23 Merged)
- Governance & Constitutional Test Suite (Gap #8) ✓
- Cryptographic Signed Audit Logging (Gap #7) ✓
- Precedent System Foundation (Gap #1 - Phase 1) ✓
- GCR Automation & Enhanced Escalation (Gap #4 - Partial) ✓

### ✅ Phase 3 (Completed - Current Branch)
- Critic Calibration System (Gap #6) ✓
- Drift Detection System (Gap #6 enhanced) ✓
- Advanced Context System (Gap #9) ✓
- Performance Optimizations (caching, parallelization) ✓

## Phase 4 Goals

Complete remaining HIGH and MEDIUM priority gaps from the Feature Gap Analysis:

1. **Semantic Precedent Search** (Gap #1 - Phases 2 & 3)
2. **Enhanced Human Review Workflows** (Gap #5)
3. **Multi-Language SDK Support** (Gap #3 - Phase 1)
4. **Complete GCR Automation** (Gap #4 - Complete)

---

## Phase 4.1: Semantic Precedent Search (Production-Grade)

**Priority**: HIGH
**Effort**: 20-24 hours
**Gap Reference**: Gap #1 - Phases 2 & 3

### Objectives

Upgrade the precedent system from hash-based lookup to semantic similarity search using vector embeddings.

### Components

#### 4.1.1: Vector Database Integration

**New Module**: `src/ejc/core/precedent/vector_store.py`

Features:
- FAISS or Qdrant vector database integration
- Efficient nearest-neighbor search
- Batch embedding generation
- Index persistence and loading

```python
class VectorPrecedentStore:
    """Vector-based precedent storage and retrieval."""

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embedding_model)
        self.index = faiss.IndexFlatIP(384)  # Inner product for cosine sim
        self.precedents = []

    def add_precedent(self, precedent: Dict) -> str:
        """Add precedent with vector embedding."""
        embedding = self._generate_embedding(precedent)
        self.index.add(np.array([embedding]))
        self.precedents.append(precedent)
        return precedent["id"]

    def search_similar(
        self,
        case: Dict,
        k: int = 10,
        min_similarity: float = 0.75
    ) -> List[SimilarPrecedent]:
        """Search for similar precedents by semantic similarity."""
        query_embedding = self._generate_embedding(case)
        distances, indices = self.index.search(
            np.array([query_embedding]),
            k
        )

        results = []
        for idx, similarity in zip(indices[0], distances[0]):
            if similarity >= min_similarity:
                results.append(SimilarPrecedent(
                    precedent=self.precedents[idx],
                    similarity_score=float(similarity),
                    match_type="semantic"
                ))
        return results
```

#### 4.1.2: Hybrid Search (Hash + Semantic)

**Module**: `src/ejc/core/precedent/hybrid_search.py`

Features:
- Combine exact hash matching with semantic search
- Weighted ranking (exact matches prioritized)
- Deduplication of results
- Performance optimization

```python
class HybridPrecedentSearch:
    """Hybrid precedent search combining hash and semantic matching."""

    def search(
        self,
        case: Dict,
        exact_weight: float = 2.0,
        semantic_weight: float = 1.0,
        top_k: int = 10
    ) -> List[SimilarPrecedent]:
        """Search using both exact and semantic matching."""
        # Exact hash matches (fast)
        exact_matches = self.hash_store.lookup(case)

        # Semantic matches (comprehensive)
        semantic_matches = self.vector_store.search_similar(case, k=top_k*2)

        # Combine and rank
        return self._merge_and_rank(
            exact_matches,
            semantic_matches,
            exact_weight,
            semantic_weight
        )[:top_k]
```

#### 4.1.3: Privacy-Preserving Precedent Bundling

**Module**: `src/ejc/core/precedent/privacy.py`

Features:
- K-anonymity bundling (group similar cases)
- Differential privacy noise injection
- Sensitive field redaction
- Consent-based sharing controls

```python
class PrivacyPreservingPrecedents:
    """Privacy-preserving precedent sharing."""

    def create_anonymous_bundle(
        self,
        precedents: List[Dict],
        k: int = 5
    ) -> AnonymousBundle:
        """Create k-anonymous precedent bundle."""
        # Group similar precedents
        clusters = self._cluster_precedents(precedents, min_cluster_size=k)

        # Generalize sensitive attributes
        anonymized = []
        for cluster in clusters:
            generalized = self._generalize_attributes(cluster)
            anonymized.append(generalized)

        return AnonymousBundle(
            precedents=anonymized,
            k_value=k,
            privacy_guarantee="k-anonymity"
        )
```

#### 4.1.4: API Endpoints

**Update**: `src/ejc/server/api.py`

New endpoints:
- `POST /precedents/search/semantic` - Semantic similarity search
- `POST /precedents/search/hybrid` - Hybrid hash + semantic
- `GET /precedents/similar/{precedent_id}` - Find similar to existing
- `POST /precedents/bundle` - Create privacy-preserving bundle

### Testing

**New Test Suite**: `tests/test_semantic_precedents.py`

Tests (25+):
- Vector embedding generation accuracy
- Semantic similarity search correctness
- Hybrid search ranking
- Privacy bundling (k-anonymity verification)
- Performance benchmarks (sub-100ms search)
- Edge cases (empty corpus, identical cases)

### Dependencies

```python
# Add to requirements.txt
sentence-transformers>=2.2.0
faiss-cpu>=1.7.0  # or faiss-gpu for production
```

---

## Phase 4.2: Enhanced Human Review Workflows

**Priority**: MEDIUM
**Effort**: 12-16 hours
**Gap Reference**: Gap #5

### Objectives

Create rich escalation bundles and interactive human review workflows with templated feedback.

### Components

#### 4.2.1: Escalation Bundle Schema

**New Module**: `src/ejc/core/escalation/bundle.py`

Features:
- Enriched escalation metadata
- Dissent index calculation
- Risk/rights flag taxonomy
- Recommended review questions

```python
@dataclass
class EscalationBundle:
    """Complete escalation package for human review."""

    # Decision context
    case_id: str
    case_hash: str
    prompt: str
    context: Dict[str, Any]

    # Critic analysis
    critic_verdicts: List[CriticVerdict]
    aggregated_verdict: str
    dissent_index: float  # 0.0 (unanimous) to 1.0 (split)
    conflicting_critics: List[Tuple[str, str]]  # (critic1, critic2)

    # Risk assessment
    risk_level: str  # "low", "medium", "high", "critical"
    rights_at_stake: List[str]  # ["privacy", "safety", "autonomy"]
    risk_flags: List[str]  # ["novel_case", "high_stakes", "precedent_conflict"]

    # Human guidance
    explanation_summary: str
    recommended_questions: List[str]
    similar_precedents: List[Dict]
    escalation_reason: str  # "high_dissent" | "rights_concern" | "low_confidence"

    # Review tracking
    requires_authorization: bool
    priority: int  # 1 (highest) to 5 (lowest)
    escalated_at: datetime
    reviewed_by: Optional[str] = None
    review_decision: Optional[str] = None
    review_notes: Optional[str] = None
    review_completed_at: Optional[datetime] = None
```

#### 4.2.2: Dissent Index Calculator

**Module**: `src/ejc/core/escalation/dissent.py`

Features:
- Calculate disagreement among critics
- Identify contentious critic pairs
- Weight dissent by critic importance
- Normalize scores (0.0-1.0)

```python
class DissentCalculator:
    """Calculate critic disagreement metrics."""

    def calculate_dissent_index(
        self,
        critic_verdicts: List[CriticVerdict],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate dissent index (0.0 = unanimous, 1.0 = maximum disagreement).

        Uses normalized entropy: H = -Σ(p_i * log(p_i)) / log(n)
        where p_i is proportion voting for each verdict.
        """
        verdict_counts = defaultdict(int)
        total_weight = 0.0

        for cv in critic_verdicts:
            weight = weights.get(cv.critic_name, 1.0) if weights else 1.0
            verdict_counts[cv.verdict] += weight
            total_weight += weight

        # Calculate normalized entropy
        probabilities = [count / total_weight for count in verdict_counts.values()]
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        max_entropy = math.log2(len(verdict_counts)) if len(verdict_counts) > 1 else 1.0

        return entropy / max_entropy if max_entropy > 0 else 0.0

    def identify_conflicts(
        self,
        critic_verdicts: List[CriticVerdict]
    ) -> List[Tuple[str, str, str]]:
        """Identify pairs of critics with conflicting verdicts."""
        conflicts = []
        for i, cv1 in enumerate(critic_verdicts):
            for cv2 in critic_verdicts[i+1:]:
                if cv1.verdict != cv2.verdict:
                    conflicts.append((
                        cv1.critic_name,
                        cv2.critic_name,
                        f"{cv1.verdict} vs {cv2.verdict}"
                    ))
        return conflicts
```

#### 4.2.3: Human Review Dashboard

**Update**: `src/ejc/server/dashboard_enhanced.py`

New features:
- `/review/queue` - List pending escalations
- `/review/{case_id}` - Interactive review interface
- Templated feedback forms
- Side-by-side precedent comparison
- One-click decision approval/override

Templates:
- Privacy review template
- Safety review template
- Novel case review template
- Precedent conflict resolution template

#### 4.2.4: API Endpoints

**Update**: `src/ejc/server/api.py`

New endpoints:
- `GET /escalations/pending` - List pending human reviews
- `GET /escalations/{case_id}` - Get escalation bundle details
- `POST /escalations/{case_id}/review` - Submit review decision
- `POST /escalations/{case_id}/notes` - Add reviewer notes
- `GET /escalations/stats` - Escalation metrics (rate, resolution time)

### Testing

**New Test Suite**: `tests/test_escalation.py`

Tests (20+):
- Dissent index calculation accuracy
- Risk flag assignment logic
- Escalation priority scoring
- Review workflow state transitions
- Feedback template rendering
- Integration with calibration system

---

## Phase 4.3: Multi-Language SDK Support

**Priority**: MEDIUM
**Effort**: 16-20 hours
**Gap Reference**: Gap #3 - Phase 1 & 2

### Objectives

Expand EJC accessibility with JavaScript/TypeScript and Python client SDKs.

### Components

#### 4.3.1: JavaScript/TypeScript SDK

**New Package**: `sdks/javascript/`

Structure:
```
sdks/javascript/
├── package.json
├── tsconfig.json
├── src/
│   ├── client.ts          # Main EJC client
│   ├── types.ts           # TypeScript definitions
│   ├── errors.ts          # Error classes
│   └── utils.ts           # Helpers
├── examples/
│   ├── node-example.js    # Node.js usage
│   ├── browser-example.html  # Browser usage
│   └── typescript-example.ts
└── tests/
    └── client.test.ts
```

Features:
- Full TypeScript support
- Promise-based async API
- Browser and Node.js compatible
- Automatic retries and error handling
- WebSocket support for real-time updates

```typescript
// sdks/javascript/src/client.ts
export class EJCClient {
    constructor(
        private apiUrl: string,
        private apiToken?: string
    ) {}

    async evaluate(request: CaseRequest): Promise<DecisionResponse> {
        const response = await fetch(`${this.apiUrl}/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiToken && { 'Authorization': `Bearer ${this.apiToken}` })
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new EJCError(`Evaluation failed: ${response.statusText}`);
        }

        return await response.json();
    }

    async evaluateWithContext(
        request: ContextualEvaluationRequest
    ): Promise<DecisionResponse> {
        return await this._post('/evaluate/contextual', request);
    }

    async getDriftHealth(days: number = 30): Promise<DriftHealthResponse> {
        return await this._get(`/drift/health?days=${days}`);
    }

    async getCalibrationMetrics(criticName: string): Promise<CalibrationMetrics> {
        return await this._get(`/calibration/metrics/${criticName}`);
    }
}

// Type definitions
export interface CaseRequest {
    case_id?: string;
    prompt: string;
    context?: Record<string, any>;
    require_human_review?: boolean;
}

export interface DecisionResponse {
    case_id: string;
    status: 'approved' | 'rejected' | 'escalated';
    final_decision: string;
    confidence: number;
    critic_results: CriticResult[];
    requires_escalation: boolean;
    audit_log_id: string;
    timestamp: string;
    execution_time_ms: number;
}
```

Package config:
```json
{
  "name": "@eleanor-project/ejc-client",
  "version": "1.0.0",
  "description": "JavaScript/TypeScript client for Eleanor Judicial Engine (EJC)",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "jest",
    "prepublish": "npm run build"
  },
  "keywords": ["ejc", "eleanor", "ethical-ai", "governance"],
  "license": "MIT"
}
```

#### 4.3.2: Enhanced Python SDK

**Update**: `src/ejc/client.py`

Features:
- Synchronous and async clients
- Context manager support
- Automatic retries with exponential backoff
- Streaming responses for long-running evaluations
- Type hints throughout

```python
# src/ejc/client.py
class EJCClient:
    """Official Python client for EJC API."""

    def __init__(
        self,
        api_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

        if api_token:
            self.session.headers['Authorization'] = f'Bearer {api_token}'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def evaluate(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> DecisionResponse:
        """Evaluate a case through EJC."""
        request = {
            "prompt": prompt,
            "context": context or {},
            **kwargs
        }

        response = self._post('/evaluate', json=request)
        return DecisionResponse(**response)

    def evaluate_contextual(
        self,
        prompt: str,
        jurisdiction: Optional[str] = None,
        cultural_context: Optional[str] = None,
        domain: Optional[str] = None,
        **kwargs
    ) -> DecisionResponse:
        """Evaluate with jurisdiction/cultural/domain context."""
        request = {
            "prompt": prompt,
            "jurisdiction": jurisdiction,
            "cultural_context": cultural_context,
            "domain": domain,
            **kwargs
        }

        response = self._post('/evaluate/contextual', json=request)
        return DecisionResponse(**response)

class AsyncEJCClient:
    """Async Python client for EJC API."""

    async def evaluate(self, prompt: str, **kwargs) -> DecisionResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/evaluate",
                json={"prompt": prompt, **kwargs},
                headers=self._headers()
            ) as resp:
                data = await resp.json()
                return DecisionResponse(**data)
```

#### 4.3.3: Documentation & Examples

**New Directory**: `docs/sdk/`

Contents:
- `quickstart.md` - Getting started guide
- `api-reference.md` - Complete API documentation
- `examples/` - Code examples for common use cases
- `migration-guide.md` - Upgrading between versions

Example use cases:
```javascript
// Example 1: Simple evaluation
const client = new EJCClient('http://localhost:8000', process.env.EJC_TOKEN);
const result = await client.evaluate({
    prompt: "Share user data with third party",
    context: { user_consent: false }
});
console.log(`Decision: ${result.final_decision}`);

// Example 2: GDPR-aware evaluation
const result = await client.evaluateWithContext({
    prompt: "Store user email for marketing",
    jurisdiction: "EU",
    domain: "marketing",
    context: { has_consent: false }
});

// Example 3: Monitor system health
const health = await client.getDriftHealth(30);
if (health.health_score < 75) {
    console.warn(`System health degraded: ${health.overall_assessment}`);
}
```

### Testing

**New Test Suites**:
- `sdks/javascript/tests/` - Jest tests for JS/TS SDK
- `tests/test_python_client.py` - Pytest tests for Python client

Tests (30+ combined):
- API endpoint coverage
- Error handling
- Retry logic
- Authentication
- Type safety (TypeScript)
- Async/await correctness
- Browser compatibility (JS)

---

## Phase 4.4: Complete GCR Automation

**Priority**: HIGH
**Effort**: 8-12 hours
**Gap Reference**: Gap #4 - Complete

### Objectives

Fully automate the Governance Change Request (GCR) process with migration maps and CI enforcement.

### Components

#### 4.4.1: GCR Ledger

**New File**: `governance/gcr_ledger.json`

Features:
- Complete audit trail of governance changes
- Impact analysis for each GCR
- Migration map references
- Approval workflow tracking

```json
{
  "schema_version": "1.0",
  "gcr_ledger": [
    {
      "gcr_id": "GCR-2025-004",
      "title": "Add semantic precedent search (Phase 4.1)",
      "proposed_by": "engineering-team",
      "date_proposed": "2025-11-27",
      "date_approved": "2025-12-01",
      "status": "APPROVED",
      "priority": "HIGH",
      "impact_analysis": {
        "affected_components": [
          "JurisprudenceRepository",
          "PrecedentRetrieval",
          "API endpoints"
        ],
        "breaking_changes": false,
        "migration_required": true,
        "backward_compatible": true
      },
      "changes": {
        "added": ["VectorPrecedentStore", "HybridSearch", "PrivacyBundling"],
        "modified": ["precedent retrieval logic", "API /precedents/search"],
        "deprecated": [],
        "removed": []
      },
      "migration_map": "governance/migration_maps/precedent_v2_to_v3.py",
      "test_coverage": "tests/test_semantic_precedents.py",
      "documentation": "docs/semantic_precedents.md",
      "version": "1.4.0"
    }
  ]
}
```

#### 4.4.2: Migration Maps

**New Directory**: `governance/migration_maps/`

Features:
- Automated data migration scripts
- Version translation utilities
- Rollback procedures
- Validation checks

```python
# governance/migration_maps/precedent_v2_to_v3.py
"""
Migrate precedents from v2.0 (hash-based) to v3.0 (vector-based).

GCR Reference: GCR-2025-004
"""

def migrate_precedent(old_precedent: Dict) -> Dict:
    """Migrate single precedent from v2 to v3 schema."""
    return {
        "version": "3.0",
        "id": old_precedent["hash"],  # Preserve ID
        "hash": old_precedent["hash"],
        "case_input": old_precedent["case_input"],
        "outcome": old_precedent["outcome"],
        "critic_verdicts": old_precedent["critic_verdicts"],
        "timestamp": old_precedent["timestamp"],

        # New v3.0 fields
        "embedding": None,  # Will be computed on demand
        "migration_status": "MIGRATED",
        "original_version": "2.0",
        "semantic_searchable": False  # Requires embedding generation
    }

def migrate_all(repository_path: str) -> MigrationReport:
    """Migrate all precedents in repository."""
    repo = JurisprudenceRepository(repository_path)
    precedents = repo.load_all()

    migrated = []
    failures = []

    for prec in precedents:
        try:
            new_prec = migrate_precedent(prec)
            validate_precedent(new_prec)  # Ensure valid
            migrated.append(new_prec)
        except Exception as e:
            failures.append((prec["hash"], str(e)))

    return MigrationReport(
        total=len(precedents),
        migrated=len(migrated),
        failed=len(failures),
        failures=failures
    )
```

#### 4.4.3: CI/CD GCR Checks

**New File**: `.github/workflows/gcr-validation.yml`

Features:
- Validate GCR ledger on PR
- Check migration maps exist for schema changes
- Verify test coverage for changed components
- Block merge on missing GCR documentation

```yaml
name: GCR Validation

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  validate-gcr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for schema changes
        id: schema-check
        run: |
          # Check if any schema files changed
          if git diff --name-only origin/main | grep -E '(schema|models|types)'; then
            echo "schema_changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Validate GCR ledger updated
        if: steps.schema-check.outputs.schema_changed == 'true'
        run: |
          # Ensure GCR ledger was updated
          if ! git diff --name-only origin/main | grep 'governance/gcr_ledger.json'; then
            echo "ERROR: Schema changed but GCR ledger not updated"
            exit 1
          fi

      - name: Validate migration map exists
        if: steps.schema-check.outputs.schema_changed == 'true'
        run: |
          # Extract latest GCR from ledger
          LATEST_GCR=$(jq -r '.gcr_ledger[-1]' governance/gcr_ledger.json)
          MIGRATION_MAP=$(echo $LATEST_GCR | jq -r '.migration_map')

          # Check migration map file exists
          if [ ! -f "$MIGRATION_MAP" ]; then
            echo "ERROR: Migration map $MIGRATION_MAP not found"
            exit 1
          fi

      - name: Run migration tests
        if: steps.schema-check.outputs.schema_changed == 'true'
        run: |
          pytest tests/test_migrations.py -v
```

#### 4.4.4: GCR Templates

**New File**: `.github/ISSUE_TEMPLATE/governance-change-request.md`

```markdown
---
name: Governance Change Request (GCR)
about: Propose a change to EJC governance logic, schemas, or thresholds
title: 'GCR: [Brief description]'
labels: 'governance, gcr'
assignees: ''
---

## GCR Metadata

**GCR ID**: GCR-YYYY-NNN (assigned by maintainers)
**Proposed By**: @username
**Priority**: HIGH | MEDIUM | LOW
**Target Version**: vX.X.X

## Change Description

Brief summary of the proposed governance change.

## Rationale

Why is this change needed? What problem does it solve?

## Impact Analysis

### Affected Components
- [ ] Critic logic
- [ ] Aggregation rules
- [ ] Schema definitions
- [ ] API contracts
- [ ] Precedent system
- [ ] Other: ___

### Breaking Changes?
- [ ] Yes (requires major version bump)
- [ ] No (backward compatible)

### Migration Required?
- [ ] Yes - data migration needed
- [ ] No - configuration only

## Implementation Plan

1. Step 1
2. Step 2
3. Step 3

## Testing Strategy

How will this change be tested?

- [ ] Unit tests
- [ ] Integration tests
- [ ] Migration tests
- [ ] Manual validation

## Rollback Plan

If the change causes issues, how can it be reverted?

## Documentation

- [ ] Migration map created: `governance/migration_maps/xxx.py`
- [ ] Tests written: `tests/test_xxx.py`
- [ ] User documentation updated
- [ ] API documentation updated

## Checklist

- [ ] GCR ledger updated
- [ ] Migration map implemented
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Reviewed by governance team
```

### Testing

**New Test Suite**: `tests/test_migrations.py`

Tests (15+):
- GCR ledger schema validation
- Migration map execution
- Backward compatibility verification
- Rollback procedures
- Version parsing correctness

---

## Summary: Phase 4 Features

| Component | Priority | Effort | Impact |
|-----------|----------|--------|--------|
| **4.1 Semantic Precedent Search** | HIGH | 20-24h | Enables semantic case law reasoning |
| **4.2 Enhanced Human Review** | MEDIUM | 12-16h | Improves escalation workflows |
| **4.3 Multi-Language SDKs** | MEDIUM | 16-20h | Broadens adoption & integration |
| **4.4 Complete GCR Automation** | HIGH | 8-12h | Ensures governance compliance |

**Total Estimated Effort**: 56-72 hours (~2-3 weeks)

---

## Integration with Existing System

Phase 4 builds directly on Phase 3:

- **Semantic Search** uses Phase 3 Performance optimizations (caching, parallel)
- **Human Review** integrates with Phase 3 Calibration (feedback loops)
- **SDKs** expose all Phase 3 endpoints (drift, context, calibration, performance)
- **GCR Automation** tracks Phase 4 schema changes systematically

---

## Testing Strategy

### Unit Tests
- `tests/test_semantic_precedents.py` (25+ tests)
- `tests/test_escalation.py` (20+ tests)
- `tests/test_migrations.py` (15+ tests)
- `sdks/javascript/tests/client.test.ts` (20+ tests)

### Integration Tests
- End-to-end precedent search (hash→semantic→hybrid)
- Full escalation workflow (detection→bundle→review→feedback)
- SDK client integration with live API
- Migration pipeline validation

### Performance Benchmarks
- Semantic search < 100ms (p95)
- Hybrid search < 150ms (p95)
- SDK client overhead < 10ms
- Migration script < 1000 precedents/sec

---

## Deployment Sequence

1. **Week 1-2**: Implement Phase 4.1 (Semantic Precedent Search)
   - Core vector store
   - Hybrid search
   - API endpoints
   - Tests

2. **Week 2-3**: Implement Phase 4.2 & 4.4 (Human Review & GCR)
   - Escalation bundles
   - Dissent calculator
   - GCR ledger & migration maps
   - Dashboard updates

3. **Week 3-4**: Implement Phase 4.3 (SDKs)
   - JavaScript/TypeScript client
   - Enhanced Python client
   - Documentation & examples
   - Package publishing

4. **Week 4**: Integration & Testing
   - Full integration testing
   - Performance benchmarks
   - Documentation review
   - PR preparation

---

## Success Criteria

- [ ] Semantic precedent search achieves >0.85 similarity accuracy
- [ ] Dissent index correctly identifies conflicting critics
- [ ] JavaScript SDK works in Node.js and browser
- [ ] Python SDK supports both sync and async
- [ ] GCR CI checks block merges on missing documentation
- [ ] All 80+ tests passing
- [ ] API response times within targets
- [ ] Documentation complete

---

## Future Phases (5+)

After Phase 4, natural next steps include:

- **Phase 5: Federated Governance** - Multi-node precedent sharing
- **Phase 6: Advanced Analytics** - Precedent trend analysis, critic performance dashboards
- **Phase 7: Mobile SDKs** - iOS/Android native clients
- **Phase 8: Enterprise Features** - SSO, audit exports, compliance reports

---

**Phase 4 Status**: Ready to implement
**Dependencies**: Phase 3 must be merged
**Expected Completion**: 3-4 weeks from start

---

*This roadmap aligns with the ELEANOR v3.0 Master Document and addresses gaps #1, #3, #4, and #5 from the Feature Gap Analysis.*
