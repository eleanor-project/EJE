---
name: Feature Gap Implementation
about: Track implementation of a feature gap from ELEANOR Spec v2.1
title: '[GAP #1] Precedent Vector Embeddings & Semantic Retrieval'
labels: ['enhancement', 'spec-alignment', 'eleanor-v2.1', 'high-priority', 'ml']
assignees: ''
---

## Feature Gap Reference

**Gap Number**: #1 (from FEATURE_GAP_ANALYSIS.md)
**Gap Title**: Precedent Vector Embeddings & Semantic Retrieval
**Specification Reference**: ELEANOR Spec v2.1, Precedent System Requirements

---

## Priority & Effort

**Priority**: **HIGH** 🔴
**Estimated Effort**: 16-24 hours (across 3 phases)
**Target Version**: v1.1.0 (Phase 1), v1.2.0 (Phase 2), v2.0.0 (Phase 3)

---

## Current Implementation Status

- [x] Phase 1 in progress
- [ ] Phase 1 complete
- [ ] Phase 2 in progress
- [ ] Phase 2 complete
- [ ] Phase 3 in progress
- [ ] Phase 3 complete

**What Exists**:
- ✅ Precedent storage with SHA-256 hashing
- ✅ Basic metadata indexing
- ✅ Precedent lookup by exact hash match
- ✅ JSON-based precedent storage

**What's Missing**:
- ❌ Vector embedding generation for precedents
- ❌ Semantic similarity search (cosine/nearest-neighbor)
- ❌ Privacy layers (k-anonymity, differential privacy)
- ❌ Federated sync protocols
- ❌ Migration map utilities
- ❌ Embedding-based drift detection

---

## Implementation Phases

### Phase 1: Basic Embeddings + Cosine Similarity (8-10 hours) - v1.1.0
**Description**: Add semantic search using sentence-transformers
**Deliverables**:
- [ ] Add `sentence-transformers` to requirements.txt
- [ ] Implement embedding generation in PrecedentManager
- [ ] Add `embedding` field to precedent storage schema
- [ ] Implement cosine similarity search
- [ ] Add configurable similarity threshold (default: 0.8)
- [ ] Create migration script for existing precedents
- [ ] Tests written and passing (similarity search, threshold tuning)
- [ ] Documentation updated

**Code Implementation**:
```python
# src/eje/core/precedent_manager.py
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class PrecedentManager:
    def __init__(self, data_path):
        self.data_path = data_path
        self.precedents = []
        self.embeddings = []
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim, fast
        self._load_precedents()

    def store(self, case, verdict, critics, references=None):
        """Store precedent with embedding"""
        case_hash = self._hash_case(case)

        # Generate embedding
        case_text = json.dumps(case, sort_keys=True)
        embedding = self.embedder.encode(case_text).tolist()

        precedent = {
            "hash": case_hash,
            "case": case,
            "verdict": verdict,
            "critics": critics,
            "embedding": embedding,
            "timestamp": datetime.utcnow().isoformat(),
            "references": references or [],
            "version": "2.0"
        }

        self.precedents.append(precedent)
        self.embeddings.append(embedding)
        self._save_precedents()

    def lookup_semantic(self, case, threshold=0.8, top_k=5):
        """Find similar precedents using semantic similarity"""
        if not self.precedents:
            return []

        # Generate embedding for query case
        case_text = json.dumps(case, sort_keys=True)
        query_embedding = self.embedder.encode(case_text)

        # Compute cosine similarity
        similarities = cosine_similarity(
            [query_embedding],
            self.embeddings
        )[0]

        # Find matches above threshold
        matches = [
            (idx, sim, self.precedents[idx])
            for idx, sim in enumerate(similarities)
            if sim >= threshold
        ]

        # Sort by similarity (descending) and return top-k
        matches.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "precedent": match[2],
                "similarity": float(match[1]),
                "match_type": "semantic"
            }
            for match in matches[:top_k]
        ]

    def lookup(self, case):
        """Hybrid lookup: exact hash + semantic similarity"""
        case_hash = self._hash_case(case)

        # Try exact match first
        exact_matches = [p for p in self.precedents if p["hash"] == case_hash]
        if exact_matches:
            return [{
                "precedent": exact_matches[0],
                "similarity": 1.0,
                "match_type": "exact"
            }]

        # Fall back to semantic search
        return self.lookup_semantic(case)
```

### Phase 2: Production Vector Search (6-8 hours) - v1.2.0
**Description**: Migrate to FAISS or vector database for scale
**Deliverables**:
- [ ] Evaluate vector DB options (FAISS, Pinecone, Milvus, Qdrant)
- [ ] Implement FAISS-based indexing
- [ ] Add configurable similarity thresholds per deployment
- [ ] Implement k-anonymous precedent bundling
- [ ] Add privacy controls (opt-in sharing, anonymization)
- [ ] Performance benchmarks (1000+ precedents)
- [ ] Tests written and passing
- [ ] Documentation updated

**FAISS Integration**:
```python
import faiss

class PrecedentManager:
    def __init__(self, data_path):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384  # embedding dimension
        self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance index
        # Or use IndexHNSWFlat for faster approximate search
        self._load_precedents()

    def _build_index(self):
        """Build FAISS index from precedents"""
        if not self.embeddings:
            return
        embeddings_array = np.array(self.embeddings, dtype=np.float32)
        self.index.add(embeddings_array)

    def lookup_semantic(self, case, threshold=0.8, top_k=5):
        """Fast nearest-neighbor search with FAISS"""
        case_text = json.dumps(case, sort_keys=True)
        query_embedding = self.embedder.encode(case_text)

        # Search index
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32),
            top_k
        )

        # Convert L2 distance to cosine similarity
        similarities = 1 / (1 + distances[0])  # approximate conversion

        # Filter by threshold
        matches = [
            {
                "precedent": self.precedents[idx],
                "similarity": float(sim),
                "match_type": "semantic"
            }
            for idx, sim in zip(indices[0], similarities)
            if sim >= threshold
        ]

        return matches
```

### Phase 3: Federated Sync + Drift Detection (8-10 hours) - v2.0.0
**Description**: Enable cross-node precedent sharing with privacy
**Deliverables**:
- [ ] Add migration maps for precedent version translation
- [ ] Implement drift detection via embedding distance
- [ ] Add federated sync protocol (REST API)
- [ ] Implement consent controls for precedent sharing
- [ ] Add k-anonymity bundling (minimum 5 similar cases per bundle)
- [ ] Cross-node precedent reconciliation
- [ ] Tests written and passing
- [ ] Documentation updated

**Drift Detection**:
```python
def detect_drift(self, recent_cases, lookback_days=30):
    """Detect governance drift using embedding distance"""
    # Get precedents from lookback period
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    historical = [p for p in self.precedents if p["timestamp"] > cutoff.isoformat()]

    if len(historical) < 10:
        return {"drift_detected": False, "reason": "insufficient_data"}

    # Compute centroid of historical embeddings
    historical_embeddings = [p["embedding"] for p in historical]
    historical_centroid = np.mean(historical_embeddings, axis=0)

    # Compute centroid of recent cases
    recent_embeddings = [self.embedder.encode(json.dumps(c)) for c in recent_cases]
    recent_centroid = np.mean(recent_embeddings, axis=0)

    # Measure drift as cosine distance
    drift_distance = 1 - cosine_similarity(
        [historical_centroid],
        [recent_centroid]
    )[0][0]

    drift_threshold = 0.15  # configurable
    return {
        "drift_detected": drift_distance > drift_threshold,
        "drift_distance": float(drift_distance),
        "threshold": drift_threshold
    }
```

---

## Dependencies

**Requires**:
- [ ] Choose embedding model (sentence-transformers recommended)
- [ ] Decide on vector DB (FAISS for Phase 2, distributed DB for Phase 3)
- [ ] Gap #4: Migration maps (for precedent schema versioning)

**Blocks**:
- Gap #2: Federated Governance (needs semantic sync)
- Gap #6: Calibration (can use embeddings for drift)

---

## Acceptance Criteria

### Phase 1 (v1.1.0)
- [ ] sentence-transformers integrated and working
- [ ] Semantic similarity search returns relevant precedents
- [ ] Hybrid lookup (exact + semantic) implemented
- [ ] Similarity threshold configurable
- [ ] Tests show >80% recall on similar cases
- [ ] Performance: <100ms for lookup on 1000 precedents
- [ ] Migration script for existing precedents
- [ ] Documentation with usage examples

### Phase 2 (v1.2.0)
- [ ] FAISS or vector DB integrated
- [ ] Sub-linear search time (O(log n) or better)
- [ ] Handles 10,000+ precedents efficiently
- [ ] K-anonymous bundling implemented
- [ ] Privacy controls in place
- [ ] Benchmark results documented

### Phase 3 (v2.0.0)
- [ ] Federated sync protocol working
- [ ] Drift detection alerts on significant changes
- [ ] Migration maps handle cross-version precedents
- [ ] Privacy-preserving sync (no PII leaked)
- [ ] Multi-node test deployment successful

---

## Technical Notes

**Model Selection**:
- **Recommended**: `all-MiniLM-L6-v2`
  - Dimensions: 384
  - Speed: Fast (CPU-friendly)
  - Quality: Good for semantic similarity
  - Size: 80MB

- **Alternatives**:
  - `all-mpnet-base-v2` (768-dim, higher quality, slower)
  - OpenAI `text-embedding-3-small` (API-based, costs money)
  - Vertex AI embeddings (GCP-based)

**Storage Considerations**:
- Each embedding: ~1.5KB (384 floats × 4 bytes)
- 1000 precedents: ~1.5MB
- 100,000 precedents: ~150MB (fits in memory)
- For >1M precedents, use vector DB

**Similarity Threshold Tuning**:
```python
# Recommended thresholds
EXACT_MATCH = 1.0           # Identical cases
HIGH_SIMILARITY = 0.9-0.95  # Very similar
MODERATE = 0.8-0.9          # Moderately similar
LOW = 0.7-0.8               # Somewhat related
UNRELATED = <0.7            # Ignore
```

---

## References

- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Section 1
- **Related Enhancements**: FUTURE_ENHANCEMENTS.md, Item #6
- **Specification**: ELEANOR Spec v2.1, Precedent Retrieval Requirements
- **Libraries**:
  - [sentence-transformers](https://www.sbert.net/)
  - [FAISS](https://github.com/facebookresearch/faiss)
  - [Pinecone](https://www.pinecone.io/)

---

## Questions & Discussion

### Q: Should we cache embeddings or compute on-the-fly?
**A**: Cache in precedent storage. Embedding generation is expensive (50-200ms per case).

### Q: What if the embedding model changes?
**A**: Store model version with each embedding. Provide re-embedding script when model updates.

### Q: How do we handle multilingual cases?
**A**: Use multilingual embedding model like `paraphrase-multilingual-MiniLM-L12-v2`.

---

## Implementation Checklist

**Tonight (Quick Wins)** 🚀:
- [ ] Add `sentence-transformers` to requirements.txt
- [ ] Test embedding generation locally:
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('all-MiniLM-L6-v2')
  embedding = model.encode("test case")
  print(f"Embedding shape: {embedding.shape}")  # Should be (384,)
  ```
- [ ] Create `tests/test_precedent_embeddings.py` skeleton
- [ ] Implement basic similarity test with two similar cases

**Week 1-2** (Phase 1):
- [ ] Modify PrecedentManager to generate embeddings
- [ ] Implement `lookup_semantic()` method
- [ ] Add hybrid lookup (exact + semantic)
- [ ] Write 10+ test cases for semantic similarity
- [ ] Benchmark performance on 100, 1000 precedents
- [ ] Migrate existing precedents (add embeddings)
- [ ] Document semantic search in docs/precedent_system.md

**Month 2-3** (Phase 2):
- [ ] Evaluate vector DB options
- [ ] Implement FAISS indexing
- [ ] Add privacy-preserving bundling
- [ ] Performance testing with 10,000+ precedents
- [ ] Production deployment guide

**Month 6-12** (Phase 3):
- [ ] Federated sync protocol design
- [ ] Drift detection implementation
- [ ] Migration map support
- [ ] Multi-node testing

---

## Example Usage

### Before (Exact Match Only)
```python
manager = PrecedentManager("data/precedents.json")

# Only finds EXACT matches
case1 = {"text": "User requests to delete their account"}
matches = manager.lookup(case1)  # Returns [] if no exact match
```

### After Phase 1 (Semantic Search)
```python
manager = PrecedentManager("data/precedents.json")

# Finds similar cases
case1 = {"text": "User requests to delete their account"}
case2 = {"text": "User wants to remove their profile"}  # Semantically similar!

matches = manager.lookup(case1)
# Returns:
# [
#   {
#     "precedent": {...},  # Previous "delete account" case
#     "similarity": 0.92,
#     "match_type": "semantic"
#   },
#   {
#     "precedent": {...},  # "Remove profile" case
#     "similarity": 0.87,
#     "match_type": "semantic"
#   }
# ]
```

This enables **true jurisprudence-style reasoning** - finding analogous cases, not just identical ones!

---

## Performance Benchmarks

Target performance metrics:

| Precedent Count | Exact Match | Semantic (NumPy) | Semantic (FAISS) |
|-----------------|-------------|------------------|------------------|
| 100             | <1ms        | <10ms            | <5ms             |
| 1,000           | <1ms        | <50ms            | <10ms            |
| 10,000          | <1ms        | ~500ms           | <20ms            |
| 100,000         | <1ms        | ~5000ms          | <50ms            |

**Phase 1 Target**: Handle 1,000 precedents efficiently (<50ms)
**Phase 2 Target**: Handle 100,000+ precedents (<50ms with FAISS)

---

## Dependencies

**Requires**:
- [ ] Python 3.8+ (for typing support)
- [ ] sentence-transformers library (~200MB download for models)
- [ ] NumPy and scikit-learn (already in dependencies)
- [ ] FAISS (Phase 2 only): `pip install faiss-cpu` or `faiss-gpu`

**Blocks**:
- Gap #2: Federated Governance (needs embedding sync)
- Gap #6: Calibration & Drift (can use embedding distance)

---

## Acceptance Criteria

### Phase 1 (v1.1.0)
- [ ] Embeddings generated for all new precedents
- [ ] Semantic search returns relevant results (>80% accuracy on test set)
- [ ] Similarity threshold configurable in config
- [ ] Hybrid lookup (try exact, fall back to semantic)
- [ ] Existing precedents migrated (embeddings added)
- [ ] Tests cover: similarity calculation, threshold filtering, edge cases
- [ ] Performance: <50ms for 1,000 precedents
- [ ] Documentation includes usage examples
- [ ] Model version stored with embeddings

### Phase 2 (v1.2.0)
- [ ] FAISS integration complete
- [ ] Sub-linear search performance
- [ ] Privacy bundling implemented (k≥5 anonymity)
- [ ] Configurable embedding model
- [ ] Benchmark: <50ms for 100,000 precedents
- [ ] Migration path from Phase 1

### Phase 3 (v2.0.0)
- [ ] Federated sync protocol working
- [ ] Drift detection alerts
- [ ] Cross-version migration support
- [ ] Privacy-preserving sync validated

---

## Technical Notes

**Embedding Storage**:
```json
{
  "hash": "abc123...",
  "case": {"text": "..."},
  "verdict": "ALLOW",
  "embedding": [0.12, 0.45, -0.32, ...],  // 384 floats
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_version": "1.0",
  "version": "2.0"
}
```

**Model Caching**:
- Models downloaded to `~/.cache/torch/sentence_transformers/`
- First run: ~200MB download
- Subsequent runs: Load from cache (fast)

**CPU vs GPU**:
- Phase 1: CPU is fine (all-MiniLM-L6-v2 is optimized for CPU)
- Phase 2+: Consider GPU for large-scale deployments

**Similarity Interpretation**:
- 1.0: Identical (exact match)
- 0.95-0.99: Extremely similar (near-duplicates)
- 0.85-0.95: Very similar (analogous cases)
- 0.75-0.85: Moderately similar (related concepts)
- 0.65-0.75: Somewhat similar (loose connection)
- <0.65: Unrelated

---

## Privacy & K-Anonymity (Phase 2)

For federated sharing, bundle precedents to ensure privacy:

```python
def create_k_anonymous_bundle(precedents, k=5):
    """
    Bundle at least k similar precedents to prevent re-identification

    Args:
        precedents: List of precedents to bundle
        k: Minimum bundle size (default: 5)

    Returns:
        Anonymized bundle safe for sharing
    """
    if len(precedents) < k:
        raise ValueError(f"Need at least {k} precedents for k-anonymity")

    # Cluster similar precedents
    embeddings = [p["embedding"] for p in precedents]
    # Use KMeans or DBSCAN clustering...

    bundle = {
        "bundle_id": generate_bundle_id(),
        "precedent_count": len(precedents),
        "anonymized_cases": [
            {
                "verdict_distribution": {"ALLOW": 3, "DENY": 2},
                "common_themes": ["privacy", "data_deletion"],
                "avg_confidence": 0.87
            }
        ],
        "k_anonymity_level": k,
        "created_at": datetime.utcnow().isoformat()
    }
    return bundle
```

---

## Migration Script

```python
# scripts/migrate_precedent_embeddings.py
"""Add embeddings to existing precedents"""

from eje.core.precedent_manager import PrecedentManager
from sentence_transformers import SentenceTransformer
import json

def migrate():
    """Add embeddings to all precedents missing them"""
    manager = PrecedentManager("data/precedents.json")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    migrated = 0
    for precedent in manager.precedents:
        if "embedding" not in precedent or precedent["embedding"] is None:
            case_text = json.dumps(precedent["case"], sort_keys=True)
            precedent["embedding"] = embedder.encode(case_text).tolist()
            precedent["embedding_model"] = "all-MiniLM-L6-v2"
            precedent["embedding_version"] = "1.0"
            precedent["version"] = "2.0"
            migrated += 1

    manager._save_precedents()
    print(f"Migrated {migrated} precedents with embeddings")

if __name__ == "__main__":
    migrate()
```

---

## References

- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Section 1
- **Related Enhancements**: FUTURE_ENHANCEMENTS.md, Item #6
- **Specification**: ELEANOR Spec v2.1, Precedent System & Semantic Retrieval
- **Related Gaps**:
  - Gap #2: Federated Governance (needs embedding sync)
  - Gap #6: Calibration (can use drift detection)

---

## Questions & Discussion

### Q: Which embedding model should we use?
**A**: Start with `all-MiniLM-L6-v2` (fast, good quality, CPU-friendly). Upgrade to larger models if quality is insufficient.

### Q: How do we handle model updates?
**A**: Store model version with embeddings. Provide re-embedding script when upgrading models. Support multiple model versions during transition.

### Q: What similarity threshold should we use?
**A**: Start with 0.8 (moderately similar). Make it configurable per deployment. Lower for exploratory recall (0.7), higher for precision (0.9).

---

## Implementation Checklist

**TONIGHT (Phase 1 Start)** 🚀:
- [ ] Install sentence-transformers: `pip install sentence-transformers`
- [ ] Test model download and basic embedding:
  ```bash
  python -c "from sentence_transformers import SentenceTransformer; \
             m = SentenceTransformer('all-MiniLM-L6-v2'); \
             print(m.encode('test').shape)"
  ```
- [ ] Create `tests/test_precedent_embeddings.py`
- [ ] Write test cases for semantic similarity
- [ ] Modify PrecedentManager to add embedding support

**This is the HIGHEST VALUE gap** - semantic precedent retrieval is core to ELEANOR's jurisprudence vision! 🎯
