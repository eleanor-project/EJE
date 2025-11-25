# Jurisprudence Repository Explainer

## Overview

The EJE Jurisprudence Repository provides consistency and traceability by storing and retrieving past decisions. It uses semantic similarity matching to find relevant historical cases and ensure consistent judgments.

## How It Works

### 1. Case Storage

When a decision is made, EJE stores:
- **Input Case**: Original case text and metadata
- **Decision Bundle**: Final verdict, confidence, critic outputs
- **Case Hash**: SHA-256 hash for exact match lookup
- **Embedding Vector**: Semantic representation for similarity search

```python
decision_bundle = {
    'request_id': 'uuid-123',
    'input': {'text': 'User wants to access medical records'},
    'final_decision': {'overall_verdict': 'REVIEW', 'avg_confidence': 0.8},
    'critic_outputs': [...]
}

precedent_manager.store_precedent(decision_bundle)
```

### 2. Similarity Search

When evaluating a new case, EJE:
1. Computes embedding vector for new case
2. Compares against all stored precedents using cosine similarity
3. Returns top-K most similar cases above similarity threshold

```python
new_case = {'text': 'User wants to view medical files'}
similar_precedents = precedent_manager.lookup(new_case)

# Returns:
[
    {
        'case_hash': 'abc123...',
        'similarity_score': 0.92,  # 0.0 to 1.0
        'final_verdict': 'REVIEW',
        'timestamp': '2025-01-15T10:30:00'
    }
]
```

### 3. Consistency Checking

The jurisprudence repository helps detect:
- **Drift**: Changes in decision patterns over time
- **Inconsistencies**: Similar cases with different verdicts
- **Pattern Recognition**: Emerging trends in decisions

## Architecture

### Storage Backends

EJE supports two storage backends:

#### JSON-Based (Simple)

```yaml
# File: precedent_store.json
{
    "precedents": [
        {
            "hash": "sha256-hash",
            "case": {...},
            "decision": {...},
            "embedding": [0.1, 0.2, ...]
        }
    ]
}
```

#### SQLite-Based (Recommended)

```sql
-- Four tables for structured storage
CREATE TABLE precedents (
    id INTEGER PRIMARY KEY,
    case_hash TEXT UNIQUE,
    case_text TEXT,
    final_verdict TEXT,
    timestamp TEXT
);

CREATE TABLE embeddings (
    precedent_id INTEGER,
    embedding_vector BLOB,
    FOREIGN KEY (precedent_id) REFERENCES precedents(id)
);

CREATE TABLE critic_outputs (
    id INTEGER PRIMARY KEY,
    precedent_id INTEGER,
    critic_name TEXT,
    verdict TEXT,
    confidence REAL,
    FOREIGN KEY (precedent_id) REFERENCES precedents(id)
);

CREATE TABLE references (
    id INTEGER PRIMARY KEY,
    source_precedent_id INTEGER,
    target_precedent_id INTEGER,
    similarity_score REAL,
    FOREIGN KEY (source_precedent_id) REFERENCES precedents(id),
    FOREIGN KEY (target_precedent_id) REFERENCES precedents(id)
);
```

### Embedding Model

**Default**: `sentence-transformers/all-MiniLM-L6-v2`

- **Size**: ~80MB
- **Dimensions**: 384
- **Performance**: Fast, suitable for real-time use
- **Quality**: Good semantic understanding

#### Custom Embeddings

```python
from sentence_transformers import SentenceTransformer

# Use custom model
custom_model = SentenceTransformer('your-model-name')
precedent_manager.model = custom_model
```

## Configuration

```yaml
# config/global.yaml

# Similarity threshold for precedent matching
precedent_similarity_threshold: 0.8  # 0.0 to 1.0

# Maximum precedents to return
max_precedent_results: 5

# Storage backend
precedent_backend: "sqlite"  # or "json"

# SQLite database path
db_uri: "sqlite:///eleanor_data/eleanor.db"

# Cache embeddings in memory
cache_embeddings: true
embedding_cache_size: 1000
```

## Usage Examples

### Basic Lookup

```python
from ejc.core.precedent_manager import JurisprudenceRepository

pm = JurisprudenceRepository(data_path="./eleanor_data")

# Find similar cases
case = {'text': 'User requests personal data deletion'}
precedents = pm.lookup(case)

for prec in precedents:
    print(f"Similarity: {prec['similarity_score']:.2f}")
    print(f"Verdict: {prec['final_verdict']}")
    print(f"When: {prec['timestamp']}")
```

### Drift Detection

```python
# Detect drift over time
from datetime import datetime, timedelta

def detect_drift(pm: JurisprudenceRepository, case_type: str, days: int = 30):
    """Check if decisions for similar cases have changed."""
    cutoff = datetime.now() - timedelta(days=days)

    # Get recent precedents
    recent = [p for p in pm.precedent_store if p['timestamp'] > cutoff]

    # Analyze verdict distribution
    verdicts = [p['final_verdict'] for p in recent]
    # Calculate distribution changes...
```

### Consistency Analysis

```python
def find_inconsistencies(pm: JurisprudenceRepository, threshold: float = 0.9):
    """Find highly similar cases with different verdicts."""
    inconsistencies = []

    for i, p1 in enumerate(pm.precedent_store):
        for p2 in pm.precedent_store[i+1:]:
            similarity = pm._compute_similarity(p1, p2)

            if similarity > threshold:
                if p1['final_verdict'] != p2['final_verdict']:
                    inconsistencies.append({
                        'case1': p1,
                        'case2': p2,
                        'similarity': similarity
                    })

    return inconsistencies
```

## Migration from JSON to SQLite

```bash
# Run migration script
python scripts/migrate_precedents.py

# Options:
# --source: Path to JSON file (default: eleanor_data/precedent_store.json)
# --db-uri: SQLite database URI (default: sqlite:///eleanor_data/eleanor.db)
# --backup: Create backup before migration (default: True)
```

## Performance Optimization

### 1. Embedding Cache

Cache computed embeddings in memory:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return model.encode(text)
```

### 2. Batch Processing

Process multiple cases at once:

```python
# Compute embeddings in batch
texts = [case['text'] for case in cases]
embeddings = model.encode(texts, batch_size=32)
```

### 3. Index Optimization

For large precedent stores, use approximate nearest neighbor search:

```python
from annoy import AnnoyIndex

# Build index
index = AnnoyIndex(384, 'angular')
for i, embedding in enumerate(embeddings):
    index.add_item(i, embedding)
index.build(10)

# Fast similarity search
similar_indices = index.get_nns_by_vector(query_embedding, 5)
```

## Monitoring and Maintenance

### Key Metrics

1. **Precedent Store Size**: Number of stored precedents
2. **Hit Rate**: Percentage of lookups finding similar precedents
3. **Similarity Distribution**: Average similarity scores
4. **Storage Size**: Disk space used
5. **Query Time**: Average lookup latency

### Maintenance Tasks

#### Pruning Old Precedents

```python
from datetime import datetime, timedelta

def prune_old_precedents(pm: JurisprudenceRepository, days: int = 365):
    """Remove precedents older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)

    pm.precedent_store = [
        p for p in pm.precedent_store
        if datetime.fromisoformat(p['timestamp']) > cutoff
    ]

    pm._save()
```

#### Deduplication

```python
def deduplicate_precedents(pm: JurisprudenceRepository, threshold: float = 0.99):
    """Remove near-duplicate precedents."""
    seen_hashes = set()
    unique_precedents = []

    for precedent in pm.precedent_store:
        hash_val = precedent['case_hash']
        if hash_val not in seen_hashes:
            seen_hashes.add(hash_val)
            unique_precedents.append(precedent)

    pm.precedent_store = unique_precedents
    pm._save()
```

## Advanced Features

### Custom Similarity Functions

```python
def custom_similarity(embedding1, embedding2, case1, case2):
    """Custom similarity combining embeddings and metadata."""
    # Cosine similarity
    cos_sim = cosine_similarity(embedding1, embedding2)

    # Metadata similarity (e.g., same user type)
    meta_sim = 1.0 if case1.get('user_type') == case2.get('user_type') else 0.5

    # Weighted combination
    return 0.8 * cos_sim + 0.2 * meta_sim
```

### Weighted Precedent Lookup

```python
def weighted_lookup(pm: JurisprudenceRepository, case: dict, weights: dict):
    """Lookup with time-based weighting."""
    precedents = pm.lookup(case)

    # Apply time decay
    now = datetime.now()
    for prec in precedents:
        age_days = (now - datetime.fromisoformat(prec['timestamp'])).days
        decay_factor = weights.get('time_decay', 0.99) ** age_days
        prec['weighted_score'] = prec['similarity_score'] * decay_factor

    # Re-sort by weighted score
    return sorted(precedents, key=lambda p: p['weighted_score'], reverse=True)
```

## Troubleshooting

### Issue: Slow Lookup Performance

**Solutions:**
1. Enable embedding caching
2. Use SQLite backend with indexes
3. Implement approximate nearest neighbor search
4. Prune old precedents

### Issue: Low Similarity Scores

**Solutions:**
1. Check embedding model quality
2. Preprocess text (lowercase, remove stopwords)
3. Use domain-specific embedding model
4. Lower similarity threshold

### Issue: High Memory Usage

**Solutions:**
1. Disable embedding caching or reduce cache size
2. Use SQLite backend instead of JSON
3. Prune old precedents regularly
4. Store embeddings on disk only

## Best Practices

1. **Regular Pruning**: Remove precedents older than 1-2 years
2. **Deduplication**: Run monthly to remove near-duplicates
3. **Monitoring**: Track similarity distributions and query times
4. **Backup**: Regular backups of precedent store
5. **Versioning**: Version precedent data with model updates
6. **Testing**: Test precedent lookups with real cases
7. **Documentation**: Document major precedent patterns

## API Reference

### JurisprudenceRepository

```python
class JurisprudenceRepository:
    def __init__(self, data_path: str):
        """Initialize precedent manager."""

    def store_precedent(self, bundle: dict) -> None:
        """Store a decision as precedent."""

    def lookup(self, case: dict) -> List[dict]:
        """Find similar precedents."""

    def get_by_hash(self, case_hash: str) -> Optional[dict]:
        """Retrieve precedent by exact hash."""

    def get_all(self) -> List[dict]:
        """Get all stored precedents."""

    def clear(self) -> None:
        """Clear all precedents (use with caution!)."""
```

## Further Reading

- [Semantic Similarity in NLP](https://example.com)
- [Sentence Transformers Documentation](https://www.sbert.net)
- [EJE Architecture Overview](./architecture.md)
- [Decision Engine Guide](./ethical_reasoning_engine.md)
