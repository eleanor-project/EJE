"""
Factory for creating vector store instances.

Provides easy initialization based on environment variables or configuration.
"""

import os
import logging
from typing import Optional, Dict, Any

from .base import VectorStore
from .qdrant_store import QdrantStore
from .pinecone_store import PineconeStore
from .pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)


def get_vectordb_backend() -> str:
    """
    Get the configured vector database backend from environment.

    Returns:
        Backend name (qdrant, pinecone, or pgvector)

    Raises:
        ValueError: If no backend is configured
    """
    backend = os.getenv("VECTORDB_BACKEND", "").lower()

    if not backend:
        raise ValueError(
            "VECTORDB_BACKEND environment variable not set. "
            "Must be one of: qdrant, pinecone, pgvector"
        )

    if backend not in ["qdrant", "pinecone", "pgvector"]:
        raise ValueError(
            f"Invalid VECTORDB_BACKEND: {backend}. "
            "Must be one of: qdrant, pinecone, pgvector"
        )

    return backend


def init_vectordb(
    backend: Optional[str] = None,
    **kwargs
) -> VectorStore:
    """
    Initialize a vector store based on configuration.

    Args:
        backend: Backend to use (qdrant, pinecone, pgvector).
                 If None, uses VECTORDB_BACKEND env var
        **kwargs: Backend-specific parameters (override env vars)

    Returns:
        Initialized VectorStore instance

    Raises:
        ValueError: If backend is invalid or required config is missing

    Environment Variables:
        VECTORDB_BACKEND: Backend to use (qdrant, pinecone, pgvector)

        For Qdrant:
            QDRANT_HOST: Qdrant server host (default: localhost)
            QDRANT_PORT: Qdrant server port (default: 6333)
            QDRANT_API_KEY: API key for authentication (optional)
            QDRANT_COLLECTION: Collection name (default: precedent_embeddings)
            QDRANT_PREFER_GRPC: Use gRPC (default: false)

        For Pinecone:
            PINECONE_API_KEY: Pinecone API key (required)
            PINECONE_INDEX: Index name (default: precedent-embeddings)
            PINECONE_NAMESPACE: Namespace (default: "")
            PINECONE_ENVIRONMENT: Environment (deprecated)
            PINECONE_SERVERLESS: Use serverless (default: true)
            PINECONE_CLOUD: Cloud provider (default: aws)
            PINECONE_REGION: Cloud region (default: us-east-1)

        For pgvector:
            PGVECTOR_DATABASE_URL: PostgreSQL connection URL (required)
            PGVECTOR_TABLE: Table name (default: precedent_embeddings)
            PGVECTOR_POOL_SIZE: Connection pool size (default: 10)
            PGVECTOR_MAX_OVERFLOW: Max overflow connections (default: 20)

    Examples:
        # Using environment variables
        store = init_vectordb()

        # Explicit backend selection
        store = init_vectordb(backend="qdrant")

        # With custom parameters
        store = init_vectordb(
            backend="qdrant",
            host="qdrant.example.com",
            port=6333,
            api_key="my-secret-key"
        )
    """
    if backend is None:
        backend = get_vectordb_backend()

    backend = backend.lower()
    logger.info(f"Initializing vector store with backend: {backend}")

    if backend == "qdrant":
        return _init_qdrant(**kwargs)
    elif backend == "pinecone":
        return _init_pinecone(**kwargs)
    elif backend == "pgvector":
        return _init_pgvector(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {backend}. "
            "Must be one of: qdrant, pinecone, pgvector"
        )


def _init_qdrant(**kwargs) -> QdrantStore:
    """Initialize Qdrant vector store."""
    config = {
        "host": os.getenv("QDRANT_HOST", "localhost"),
        "port": int(os.getenv("QDRANT_PORT", "6333")),
        "api_key": os.getenv("QDRANT_API_KEY"),
        "collection_name": os.getenv("QDRANT_COLLECTION", "precedent_embeddings"),
        "prefer_grpc": os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true",
        "timeout": float(os.getenv("QDRANT_TIMEOUT", "60.0")),
    }

    # Override with kwargs
    config.update(kwargs)

    logger.info(
        f"Initializing Qdrant at {config['host']}:{config['port']} "
        f"with collection '{config['collection_name']}'"
    )

    return QdrantStore(**config)


def _init_pinecone(**kwargs) -> PineconeStore:
    """Initialize Pinecone vector store."""
    api_key = kwargs.get("api_key") or os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError(
            "Pinecone API key not found. "
            "Set PINECONE_API_KEY environment variable or pass api_key parameter"
        )

    config = {
        "api_key": api_key,
        "environment": os.getenv("PINECONE_ENVIRONMENT"),
        "index_name": os.getenv("PINECONE_INDEX", "precedent-embeddings"),
        "namespace": os.getenv("PINECONE_NAMESPACE", ""),
        "serverless": os.getenv("PINECONE_SERVERLESS", "true").lower() == "true",
        "cloud": os.getenv("PINECONE_CLOUD", "aws"),
        "region": os.getenv("PINECONE_REGION", "us-east-1"),
    }

    # Override with kwargs
    config.update(kwargs)

    logger.info(
        f"Initializing Pinecone with index '{config['index_name']}' "
        f"(namespace: '{config['namespace']}')"
    )

    return PineconeStore(**config)


def _init_pgvector(**kwargs) -> PgVectorStore:
    """Initialize pgvector store."""
    database_url = kwargs.get("database_url") or os.getenv("PGVECTOR_DATABASE_URL")
    if not database_url:
        # Fallback to main DATABASE_URL if PGVECTOR_DATABASE_URL not set
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "PostgreSQL database URL not found. "
            "Set PGVECTOR_DATABASE_URL or DATABASE_URL environment variable "
            "or pass database_url parameter"
        )

    config = {
        "database_url": database_url,
        "table_name": os.getenv("PGVECTOR_TABLE", "precedent_embeddings"),
        "pool_size": int(os.getenv("PGVECTOR_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("PGVECTOR_MAX_OVERFLOW", "20")),
    }

    # Override with kwargs
    config.update(kwargs)

    logger.info(
        f"Initializing pgvector with table '{config['table_name']}'"
    )

    return PgVectorStore(**config)


async def create_collection_if_not_exists(
    store: VectorStore,
    dimension: int,
    distance_metric: str = "cosine",
    **kwargs
) -> None:
    """
    Create vector collection/index if it doesn't exist.

    Args:
        store: VectorStore instance
        dimension: Embedding dimension
        distance_metric: Distance metric to use
        **kwargs: Backend-specific parameters

    Example:
        store = init_vectordb()
        await store.connect()
        await create_collection_if_not_exists(store, dimension=1536)
    """
    try:
        exists = await store.collection_exists()
        if not exists:
            logger.info(
                f"Creating collection with dimension {dimension} "
                f"and {distance_metric} metric"
            )
            await store.create_collection(
                dimension=dimension,
                distance_metric=distance_metric,
                **kwargs
            )
        else:
            logger.info("Collection already exists")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise
