# VectorDB Storage Layer

Production-ready vector database storage for precedent embeddings with multiple backend support.

## Overview

The VectorDB storage layer provides a unified interface for storing and querying vector embeddings across multiple backends:

- **Qdrant** - High-performance open-source vector search engine
- **Pinecone** - Managed vector database service (serverless or pod-based)
- **pgvector** - PostgreSQL extension for native vector support

All backends implement the same abstract `VectorStore` interface, making it easy to switch between providers or run different backends for development vs production.

## Quick Start

### 1. Choose Your Backend

Set the backend via environment variable:

```bash
export VECTORDB_BACKEND=qdrant  # or pinecone, pgvector
```

### 2. Configure Your Backend

#### Qdrant

```bash
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_API_KEY=your-api-key  # Optional, for cloud
export QDRANT_COLLECTION=precedent_embeddings
```

#### Pinecone

```bash
export PINECONE_API_KEY=your-api-key
export PINECONE_INDEX=precedent-embeddings
export PINECONE_NAMESPACE=production  # Optional
export PINECONE_SERVERLESS=true
export PINECONE_CLOUD=aws
export PINECONE_REGION=us-east-1
```

#### pgvector

```bash
export PGVECTOR_DATABASE_URL=postgresql://user:pass@localhost/dbname
# Or use the main DATABASE_URL as fallback
export DATABASE_URL=postgresql://user:pass@localhost/dbname
export PGVECTOR_TABLE=precedent_embeddings
```

### 3. Initialize and Use

```python
import numpy as np
from ejc.storage.vectordb import (
    init_vectordb,
    create_collection_if_not_exists,
    EmbeddingMetadata,
)

# Initialize vector store
store = init_vectordb()

# Connect to the database
await store.connect()

# Create collection if needed (one-time setup)
await create_collection_if_not_exists(
    store=store,
    dimension=1536,  # OpenAI ada-002 embedding size
    distance_metric="cosine",
)

# Create metadata
metadata = EmbeddingMetadata(
    precedent_id="prec-001",
    decision_id="dec-001",
    embedding_model="text-embedding-ada-002",
    created_at=datetime.utcnow(),
    tags=["critical", "security"],
    similarity_threshold=0.85,
)

# Store an embedding
embedding = np.random.rand(1536).astype(np.float32)
await store.upsert(
    precedent_id="prec-001",
    embedding=embedding,
    metadata=metadata,
)

# Search for similar embeddings
query_embedding = np.random.rand(1536).astype(np.float32)
results = await store.search(
    query_embedding=query_embedding,
    top_k=10,
    filters={"tags": ["critical"]},
    min_score=0.8,
)

for result in results:
    print(f"Found: {result.precedent_id} (score: {result.score:.3f})")

# Cleanup
await store.disconnect()
```

## Synchronization with PostgreSQL

The `EmbeddingSync` class keeps PostgreSQL and VectorDB in sync:

```python
from ejc.storage import init_database
from ejc.storage.vectordb import init_vectordb, EmbeddingSync

# Initialize both stores
db = init_database()
vector_store = init_vectordb()
await vector_store.connect()

# Create sync manager
sync = EmbeddingSync(
    db_manager=db,
    vector_store=vector_store,
)

# Sync a single embedding to both stores
await sync.sync_to_vectordb(
    precedent_id="prec-001",
    embedding_vector=embedding,
    decision_id="dec-001",
    embedding_model="text-embedding-ada-002",
    tags=["critical"],
)

# Sync a batch
await sync.sync_batch_to_vectordb(
    precedent_ids=["prec-001", "prec-002", "prec-003"],
    embedding_vectors=embeddings,  # numpy array (3, 1536)
    decision_ids=["dec-001", "dec-001", "dec-002"],
    embedding_model="text-embedding-ada-002",
)

# Delete from both stores
await sync.delete_from_both("prec-001")

# Sync all embeddings from PostgreSQL to VectorDB
synced_count = await sync.sync_from_postgres_to_vectordb(
    limit=1000,
    batch_size=100,
)

# Verify sync status
stats = await sync.verify_sync(sample_size=100)
print(f"Sync rate: {stats['sync_rate_percent']:.1f}%")
print(f"In sync: {stats['in_sync']}")
```

## Searching for Similar Precedents

```python
from ejc.storage.vectordb import search_similar_precedents

# Simple search
results = await search_similar_precedents(
    vector_store=store,
    query_embedding=query_embedding,
    top_k=5,
)

# With filters and minimum similarity
results = await search_similar_precedents(
    vector_store=store,
    query_embedding=query_embedding,
    top_k=10,
    filters={
        "tags": ["critical", "security"],  # Must have these tags
        "embedding_model": "text-embedding-ada-002",
        "similarity_threshold": {"gte": 0.8},  # Range filter
    },
    min_similarity=0.85,  # Minimum score
)

# Results are dictionaries
for result in results:
    print(f"""
    Precedent: {result['precedent_id']}
    Decision: {result['decision_id']}
    Score: {result['score']:.3f}
    Distance: {result['distance']:.3f}
    Model: {result['metadata']['embedding_model']}
    Tags: {result['metadata']['tags']}
    """)
```

## Backend-Specific Features

### Qdrant

```python
from ejc.storage.vectordb import QdrantStore

store = QdrantStore(
    host="qdrant.example.com",
    port=6333,
    api_key="your-api-key",
    prefer_grpc=True,  # Use gRPC instead of HTTP
    timeout=60.0,
)

# Create collection with custom parameters
await store.create_collection(
    dimension=1536,
    distance_metric="cosine",
    # Qdrant-specific
    on_disk_payload=True,
    optimizers_config={
        "indexing_threshold": 20000,
    },
)
```

### Pinecone

```python
from ejc.storage.vectordb import PineconeStore

# Serverless (recommended)
store = PineconeStore(
    api_key="your-api-key",
    index_name="precedents",
    namespace="production",  # For multi-tenancy
    serverless=True,
    cloud="aws",
    region="us-east-1",
)

# Pod-based (legacy)
store = PineconeStore(
    api_key="your-api-key",
    index_name="precedents",
    serverless=False,
    environment="us-east-1-aws",
)

# Create index
await store.create_collection(
    dimension=1536,
    distance_metric="cosine",
    # Pod-specific
    pod_type="p1.x1",
    pods=1,
)
```

### pgvector

```python
from ejc.storage.vectordb import PgVectorStore

store = PgVectorStore(
    database_url="postgresql://user:pass@localhost/db",
    table_name="precedent_embeddings",
    pool_size=10,
    max_overflow=20,
)

# Create table with custom index parameters
await store.create_collection(
    dimension=1536,
    distance_metric="cosine",
    # pgvector-specific
    lists=100,  # Number of clusters for IVFFLAT index
)
```

## Distance Metrics

All backends support three distance metrics:

- **cosine** - Cosine similarity (recommended for most use cases)
- **euclidean** - L2 distance
- **dot** - Dot product / inner product

```python
await store.create_collection(
    dimension=1536,
    distance_metric="cosine",  # or "euclidean", "dot"
)
```

## Batch Operations

Batch operations are more efficient for bulk inserts:

```python
# Prepare data
precedent_ids = ["prec-001", "prec-002", "prec-003"]
embeddings = np.random.rand(3, 1536).astype(np.float32)
metadatas = [
    EmbeddingMetadata(
        precedent_id=pid,
        decision_id="dec-001",
        embedding_model="text-embedding-ada-002",
        created_at=datetime.utcnow(),
    )
    for pid in precedent_ids
]

# Batch upsert
await store.upsert_batch(
    precedent_ids=precedent_ids,
    embeddings=embeddings,
    metadatas=metadatas,
    batch_size=100,  # Process 100 at a time
)

# Batch delete
deleted_count = await store.delete_batch(precedent_ids)

# Batch search
query_embeddings = np.random.rand(5, 1536).astype(np.float32)
results_list = await store.search_batch(
    query_embeddings=query_embeddings,
    top_k=10,
)
# results_list is a list of lists, one per query
```

## Filtering

All backends support metadata filtering:

```python
# Exact match
filters = {"embedding_model": "text-embedding-ada-002"}

# List match (OR)
filters = {"tags": ["critical", "security"]}

# Range queries
filters = {
    "similarity_threshold": {"gte": 0.8, "lte": 0.95},
    "created_at": {"gt": "2024-01-01T00:00:00"},
}

# Combine filters
filters = {
    "tags": ["critical"],
    "embedding_model": "text-embedding-ada-002",
    "similarity_threshold": {"gte": 0.85},
}

results = await store.search(
    query_embedding=query_embedding,
    top_k=10,
    filters=filters,
)
```

## Monitoring and Statistics

```python
# Get collection info
info = await store.get_collection_info()
print(f"Collection: {info['name']}")
print(f"Dimension: {info['dimension']}")
print(f"Vectors: {info.get('total_vector_count', 'N/A')}")

# Get detailed stats
stats = await store.get_stats()
print(f"Backend: {stats['backend']}")
print(f"Count: {stats.get('row_count', stats.get('points_count'))}")

# Count with filters
critical_count = await store.count(filters={"tags": ["critical"]})
print(f"Critical precedents: {critical_count}")

# Health check
is_healthy = await store.health_check()
if not is_healthy:
    print("Warning: Vector store is not healthy!")
```

## Running Different Backends

### Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant:latest
```

### Pinecone

Sign up at https://www.pinecone.io/ and get an API key.

### pgvector (PostgreSQL)

```bash
# Install pgvector extension
CREATE EXTENSION vector;

# Or with Docker
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  ankane/pgvector
```

## Performance Tips

1. **Use batch operations** for bulk inserts/deletes
2. **Create indexes** after bulk loading (Qdrant, pgvector)
3. **Use appropriate pool sizes** (pgvector: 10-20 connections)
4. **Enable gRPC** for Qdrant for better performance
5. **Use serverless** for Pinecone unless you need dedicated pods
6. **Filter early** - apply filters in the query, not in application code
7. **Normalize embeddings** for cosine distance to improve performance

## Troubleshooting

### Connection Issues

```python
# Check if store is healthy
is_healthy = await store.health_check()
if not is_healthy:
    print("Store is not reachable")
    # Check environment variables
    # Check network connectivity
    # Check service status
```

### Dimension Mismatches

```python
# Ensure all embeddings have the same dimension
try:
    await store.upsert(precedent_id, embedding, metadata)
except ValueError as e:
    print(f"Dimension error: {e}")
    # Check embedding.shape[0] matches collection dimension
```

### Sync Issues

```python
# Verify sync status
stats = await sync.verify_sync(sample_size=100)
if not stats["in_sync"]:
    print(f"Sync issue: {stats['missing_in_vectordb']} missing")
    # Re-sync from PostgreSQL
    await sync.sync_from_postgres_to_vectordb()
```

### Performance Issues

```python
# For pgvector: Increase connection pool
store = PgVectorStore(
    database_url=url,
    pool_size=20,  # Increase for high concurrency
    max_overflow=40,
)

# For Qdrant: Use gRPC
store = QdrantStore(
    host=host,
    port=6334,  # gRPC port
    prefer_grpc=True,
)

# For Pinecone: Use batch operations
await store.upsert_batch(
    precedent_ids=ids,
    embeddings=embeddings,
    metadatas=metadatas,
    batch_size=200,  # Larger batches
)
```

## Environment Variables Reference

### Common

- `VECTORDB_BACKEND` - Backend to use (qdrant, pinecone, pgvector)

### Qdrant

- `QDRANT_HOST` - Qdrant server host (default: localhost)
- `QDRANT_PORT` - Qdrant server port (default: 6333)
- `QDRANT_API_KEY` - API key for authentication (optional)
- `QDRANT_COLLECTION` - Collection name (default: precedent_embeddings)
- `QDRANT_PREFER_GRPC` - Use gRPC (default: false)
- `QDRANT_TIMEOUT` - Request timeout in seconds (default: 60.0)

### Pinecone

- `PINECONE_API_KEY` - Pinecone API key (required)
- `PINECONE_INDEX` - Index name (default: precedent-embeddings)
- `PINECONE_NAMESPACE` - Namespace (default: "")
- `PINECONE_SERVERLESS` - Use serverless (default: true)
- `PINECONE_CLOUD` - Cloud provider (default: aws)
- `PINECONE_REGION` - Cloud region (default: us-east-1)

### pgvector

- `PGVECTOR_DATABASE_URL` - PostgreSQL connection URL (required, or use DATABASE_URL)
- `PGVECTOR_TABLE` - Table name (default: precedent_embeddings)
- `PGVECTOR_POOL_SIZE` - Connection pool size (default: 10)
- `PGVECTOR_MAX_OVERFLOW` - Max overflow connections (default: 20)

## Production Checklist

- [ ] Set `VECTORDB_BACKEND` environment variable
- [ ] Configure backend-specific environment variables
- [ ] Create collection with appropriate dimension
- [ ] Set up monitoring for vector store health
- [ ] Configure appropriate pool sizes (pgvector)
- [ ] Enable TLS/SSL for production connections
- [ ] Set up backups (Qdrant snapshots, Pinecone backups, PostgreSQL dumps)
- [ ] Monitor vector count and storage usage
- [ ] Test failover and recovery procedures
- [ ] Set up alerts for sync issues
- [ ] Document embedding model and dimension used
- [ ] Plan for re-indexing if model changes

## Next Steps

- See [Task 13.3 - S3-Compatible Storage](../s3/README.md) for evidence bundle storage
- See [Storage README](../README.md) for overall storage architecture
- See [PostgreSQL Storage](../README.md#postgresql-storage) for relational data storage
