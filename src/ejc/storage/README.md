# EJC Storage Layer

Production-grade multi-tier storage architecture for the Ethical Jurisprudence Core.

## Overview

The EJC storage layer provides three complementary storage systems:

1. **PostgreSQL Storage** - Relational data with ACID transactions
2. **VectorDB Storage** - Vector similarity search for precedent embeddings
3. **S3-Compatible Storage** - Object storage for evidence bundles and attachments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │   VectorDB   │  │  S3-Compatible   │
│   (Relational)   │  │  (Similarity) │  │    (Objects)     │
├──────────────────┤  ├──────────────┤  ├──────────────────┤
│ • Decisions      │  │ • Embeddings │  │ • Evidence Files │
│ • Audit Records  │  │ • Search     │  │ • Attachments    │
│ • Precedents     │  │ • Filters    │  │ • Backups        │
│ • Metrics        │  │ • Top-K      │  │ • Exports        │
└──────────────────┘  └──────────────┘  └──────────────────┘
         │                    │
         └────────┬───────────┘
                  │
         ┌────────▼────────┐
         │  EmbeddingSync  │
         │  (Keeps in sync)│
         └─────────────────┘
```

## Quick Start

### PostgreSQL Storage

```python
from ejc.storage import init_database, DecisionRepository

# Initialize database
db = init_database()  # Uses DATABASE_URL env var

# Use repository pattern
with db.session() as session:
    decision_repo = DecisionRepository(session)

    # Create decision
    decision = decision_repo.create(
        decision_id="dec-123",
        input_data={"query": "test"},
        final_verdict="ALLOW",
        avg_confidence=0.95
    )

    # Query
    recent = decision_repo.get_recent(hours=24)
    stats = decision_repo.get_statistics()
```

### VectorDB Storage

```python
from ejc.storage.vectordb import init_vectordb, search_similar_precedents
import numpy as np

# Initialize vector store (uses VECTORDB_BACKEND env var)
store = init_vectordb()
await store.connect()

# Search for similar precedents
query_embedding = np.random.rand(1536).astype(np.float32)
results = await search_similar_precedents(
    vector_store=store,
    query_embedding=query_embedding,
    top_k=10,
    filters={"tags": ["critical"]},
    min_similarity=0.8,
)
```

### Synchronized Storage

```python
from ejc.storage import init_database
from ejc.storage.vectordb import init_vectordb, EmbeddingSync

# Initialize both
db = init_database()
vector_store = init_vectordb()
await vector_store.connect()

# Create sync manager
sync = EmbeddingSync(db_manager=db, vector_store=vector_store)

# Sync to both stores atomically
await sync.sync_to_vectordb(
    precedent_id="prec-001",
    embedding_vector=embedding,
    decision_id="dec-001",
    embedding_model="text-embedding-ada-002",
)
```

## PostgreSQL Storage

### Features

- **Connection Pooling**: QueuePool with configurable size and overflow
- **Session Management**: Context managers for safe session lifecycle
- **Transaction Support**: ACID transactions with savepoints
- **Auto-Retry**: Exponential backoff for transient failures
- **Health Checks**: Connection validation and monitoring
- **Migrations**: Alembic-based schema versioning
- **Repository Pattern**: Clean data access layer

### Environment Variables

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/eje"
export DB_POOL_SIZE=10
export DB_MAX_OVERFLOW=20
```

### Models

- **Decision** - Complete decision records
- **CriticOutput** - Individual critic evaluations
- **Precedent** - Historical decisions
- **PrecedentEmbedding** - Vector embeddings (syncs with VectorDB)
- **AuditRecord** - Audit trail
- **Override** - Human overrides
- **PolicyRule** - Governance rules
- **MetricsSnapshot** - System metrics

### Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Show current version
alembic current
```

See [database.py](database.py), [models.py](models.py), and [repositories.py](repositories.py) for full API.

## VectorDB Storage

### Features

- **Multiple Backends**: Qdrant, Pinecone, pgvector
- **Unified Interface**: Switch backends without code changes
- **Similarity Search**: Fast nearest-neighbor search
- **Metadata Filtering**: Filter by tags, model, threshold, etc.
- **Batch Operations**: Efficient bulk insert/update/delete
- **Sync with PostgreSQL**: Keep embeddings in sync
- **Production-Ready**: Connection pooling, health checks, monitoring

### Supported Backends

| Backend | Type | Best For |
|---------|------|----------|
| **Qdrant** | Self-hosted | Full control, high performance |
| **Pinecone** | Managed | Ease of use, serverless scaling |
| **pgvector** | PostgreSQL | Unified storage, SQL queries |

### Environment Variables

```bash
# Choose backend
export VECTORDB_BACKEND=qdrant  # or pinecone, pgvector

# Qdrant
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_COLLECTION=precedent_embeddings

# Pinecone
export PINECONE_API_KEY=your-api-key
export PINECONE_INDEX=precedent-embeddings

# pgvector
export PGVECTOR_DATABASE_URL=postgresql://user:pass@localhost/db
export PGVECTOR_TABLE=precedent_embeddings
```

### Usage

```python
from ejc.storage.vectordb import (
    init_vectordb,
    create_collection_if_not_exists,
    EmbeddingMetadata,
)

# Initialize
store = init_vectordb()
await store.connect()

# Create collection (one-time)
await create_collection_if_not_exists(
    store=store,
    dimension=1536,
    distance_metric="cosine",
)

# Store embedding
metadata = EmbeddingMetadata(
    precedent_id="prec-001",
    decision_id="dec-001",
    embedding_model="text-embedding-ada-002",
    created_at=datetime.utcnow(),
    tags=["critical"],
)

await store.upsert("prec-001", embedding, metadata)

# Search
results = await store.search(
    query_embedding=query,
    top_k=10,
    filters={"tags": ["critical"]},
    min_score=0.8,
)
```

See [vectordb/README.md](vectordb/README.md) for complete documentation.

## Synchronization

### Keeping PostgreSQL and VectorDB in Sync

The `EmbeddingSync` class ensures embeddings are consistent across both stores:

```python
from ejc.storage.vectordb import EmbeddingSync

sync = EmbeddingSync(db_manager=db, vector_store=vector_store)

# Sync single embedding
await sync.sync_to_vectordb(
    precedent_id="prec-001",
    embedding_vector=embedding,
    decision_id="dec-001",
    embedding_model="text-embedding-ada-002",
)

# Sync batch
await sync.sync_batch_to_vectordb(
    precedent_ids=ids,
    embedding_vectors=embeddings,
    decision_ids=decision_ids,
    embedding_model="text-embedding-ada-002",
)

# Delete from both
await sync.delete_from_both("prec-001")

# Verify sync status
stats = await sync.verify_sync(sample_size=100)
print(f"Sync rate: {stats['sync_rate_percent']:.1f}%")
```

### Recovery from Desync

```python
# Re-sync all embeddings from PostgreSQL to VectorDB
synced_count = await sync.sync_from_postgres_to_vectordb(
    limit=None,  # All records
    batch_size=100,
)
print(f"Synced {synced_count} embeddings")
```

## S3-Compatible Storage

Production-ready object storage for evidence bundles and attachments.

### Features

- **AWS S3 Support** - Native integration with Amazon S3
- **MinIO Support** - Works with MinIO and other S3-compatible services
- **Retry Logic** - Automatic retry with exponential backoff
- **Multipart Upload** - Efficient upload of large files (> 5MB)
- **Presigned URLs** - Temporary access URLs for secure sharing
- **Evidence Bundles** - Structured storage with metadata and checksums
- **Attachments** - Binary file storage for images, PDFs, etc.

### Environment Variables

```bash
export S3_BUCKET_NAME=eje-evidence
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1

# For MinIO
export S3_ENDPOINT_URL=http://localhost:9000
```

### Usage

```python
from ejc.storage.s3 import (
    init_objectstore,
    EvidenceBundle,
    store_evidence_bundle,
    retrieve_evidence_bundle,
)
from datetime import datetime

# Initialize object store
store = init_objectstore()
store.connect()

# Store evidence bundle
bundle = EvidenceBundle(
    decision_id="dec-123",
    evidence_data={
        "verdict": "ALLOW",
        "confidence": 0.95,
        "critics": [...],
    },
    created_at=datetime.utcnow(),
)

key = store_evidence_bundle(store, bundle)

# Retrieve evidence
retrieved = retrieve_evidence_bundle(store, decision_id="dec-123")

# Store attachment
from ejc.storage.s3 import store_attachment

key = store_attachment(
    store=store,
    decision_id="dec-123",
    attachment_name="screenshot.png",
    data=image_bytes,
    content_type="image/png",
)

# Generate presigned URL (1 hour expiration)
from ejc.storage.s3 import generate_presigned_url_for_evidence

url = generate_presigned_url_for_evidence(
    store=store,
    decision_id="dec-123",
    expiration=3600,
)
```

See [s3/README.md](s3/README.md) for complete documentation.

## Production Deployment

### Initial Setup

```bash
# 1. Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/eje"
export VECTORDB_BACKEND=qdrant
export QDRANT_HOST=qdrant.example.com
export QDRANT_PORT=6333
export QDRANT_API_KEY=your-api-key

# 2. Run PostgreSQL migrations
alembic upgrade head

# 3. Create VectorDB collection
python -c "
import asyncio
from ejc.storage.vectordb import init_vectordb, create_collection_if_not_exists

async def setup():
    store = init_vectordb()
    await store.connect()
    await create_collection_if_not_exists(store, dimension=1536)
    await store.disconnect()

asyncio.run(setup())
"
```

### Monitoring

```python
from ejc.storage import get_database
from ejc.storage.vectordb import init_vectordb

# PostgreSQL health
db = get_database()
health = db.health_check()
pool_status = db.get_pool_status()

# VectorDB health
store = init_vectordb()
await store.connect()
is_healthy = await store.health_check()
stats = await store.get_stats()

print(f"PostgreSQL: {health}")
print(f"Pool: {pool_status}")
print(f"VectorDB: {is_healthy}")
print(f"Vectors: {stats.get('points_count', stats.get('row_count'))}")
```

### Backup Strategy

**PostgreSQL**:
```bash
# Backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

**Qdrant**:
```bash
# Create snapshot
curl -X POST http://qdrant:6333/collections/{collection}/snapshots

# Download snapshot
curl http://qdrant:6333/collections/{collection}/snapshots/{snapshot_name}
```

**Pinecone**:
```python
# Pinecone handles backups automatically
# Export to backup location if needed
```

**pgvector**:
```bash
# Included in PostgreSQL backup
pg_dump $DATABASE_URL > backup.sql
```

## Performance Optimization

### PostgreSQL

1. **Use connection pooling** - Configure appropriate pool sizes
2. **Batch operations** - Use bulk insert/update when possible
3. **Indexes** - All models have appropriate indexes
4. **Pagination** - Always use limit/offset for large queries
5. **Query optimization** - Select only needed columns

### VectorDB

1. **Batch operations** - Use `upsert_batch` for bulk inserts
2. **Appropriate backend** - Choose based on scale and requirements
3. **Distance metric** - Cosine for most use cases
4. **Filtering** - Filter in query, not in application
5. **Pool sizes** - Configure for concurrency (pgvector)

### Synchronization

1. **Batch sync** - Use `sync_batch_to_vectordb` for multiple embeddings
2. **Async operations** - VectorDB operations are async
3. **Verify periodically** - Run `verify_sync` on schedule
4. **Monitor lag** - Alert if sync falls behind

## Troubleshooting

### Connection Issues

```python
# PostgreSQL
db = get_database()
if not db.health_check():
    print("PostgreSQL unhealthy")
    # Check DATABASE_URL
    # Check PostgreSQL service
    # Check network connectivity

# VectorDB
store = init_vectordb()
await store.connect()
if not await store.health_check():
    print("VectorDB unhealthy")
    # Check VECTORDB_BACKEND
    # Check backend-specific env vars
    # Check service status
```

### Sync Issues

```python
from ejc.storage.vectordb import EmbeddingSync

sync = EmbeddingSync(db, vector_store)

# Check sync status
stats = await sync.verify_sync(sample_size=100)
if not stats["in_sync"]:
    print(f"Out of sync: {stats}")
    # Re-sync from PostgreSQL
    await sync.sync_from_postgres_to_vectordb()
```

### Performance Issues

```python
# Check pool status
pool_status = db.get_pool_status()
if pool_status["checked_out"] > pool_status["size"] * 0.8:
    print("Pool nearly exhausted - increase pool_size")

# Check VectorDB stats
stats = await store.get_stats()
print(f"Vector count: {stats}")
# Monitor query latency
# Consider scaling VectorDB
```

## Testing

```python
import pytest
from ejc.storage import init_database, DatabaseConfig
from ejc.storage.vectordb import init_vectordb

# PostgreSQL - use in-memory SQLite
config = DatabaseConfig(database_url="sqlite:///:memory:")
db = init_database(config)
db.create_all_tables()

# VectorDB - use mocks or test instance
@pytest.fixture
async def vector_store():
    # Use mock or test instance
    store = init_vectordb(backend="qdrant", host="localhost")
    await store.connect()
    yield store
    await store.disconnect()
```

## Security

1. **Connection strings** - Never commit to version control
2. **SSL/TLS** - Use encrypted connections in production
3. **Least privilege** - Database users should have minimal permissions
4. **API keys** - Rotate regularly, use secrets management
5. **Audit logs** - Enable PostgreSQL query logging
6. **Network security** - Use VPCs, security groups, firewalls

## Documentation

- [PostgreSQL Storage](database.py) - Database manager and configuration
- [Models](models.py) - SQLAlchemy models
- [Repositories](repositories.py) - Data access layer
- [VectorDB Storage](vectordb/README.md) - Vector database documentation
- [Migrations](../../../alembic/) - Database migrations

## Support

For issues or questions:
1. Check the troubleshooting sections above
2. Review environment variables
3. Check service health and logs
4. Verify network connectivity
5. Consult backend-specific documentation

## License

CC BY 4.0 - See [LICENSE](../../../LICENSE) for details.
