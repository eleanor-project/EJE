"""
pgvector backend implementation.

PostgreSQL extension for vector similarity search with native SQL support.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime

import asyncpg
from pgvector.asyncpg import register_vector

from .base import VectorStore, SearchResult, EmbeddingMetadata

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStore):
    """pgvector (PostgreSQL) vector database implementation."""

    DISTANCE_METRICS = {
        "cosine": "<=>",  # Cosine distance
        "euclidean": "<->",  # L2 distance
        "dot": "<#>",  # Negative inner product
    }

    def __init__(
        self,
        database_url: str,
        table_name: str = "precedent_embeddings",
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        """
        Initialize pgvector store.

        Args:
            database_url: PostgreSQL connection URL
            table_name: Name of the table for embeddings
            pool_size: Size of the connection pool
            max_overflow: Maximum overflow connections
        """
        super().__init__(table_name)
        self.database_url = database_url
        self.table_name = table_name
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool: Optional[asyncpg.Pool] = None
        self._dimension: Optional[int] = None
        self._distance_metric: str = "cosine"

    async def connect(self) -> None:
        """Establish connection to PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=self.pool_size,
            )

            # Register pgvector type
            async with self.pool.acquire() as conn:
                await register_vector(conn)

            logger.info(f"Connected to PostgreSQL with pgvector")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection to PostgreSQL."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL")

    async def health_check(self) -> bool:
        """Check if PostgreSQL is healthy."""
        try:
            if not self.pool:
                return False
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    async def create_collection(
        self,
        dimension: int,
        distance_metric: str = "cosine",
        **kwargs
    ) -> None:
        """Create a new table with pgvector extension."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        self._dimension = dimension
        self._distance_metric = distance_metric

        try:
            async with self.pool.acquire() as conn:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create table
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        precedent_id TEXT PRIMARY KEY,
                        embedding vector({dimension}),
                        decision_id TEXT NOT NULL,
                        embedding_model TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        context TEXT,
                        tags TEXT[],
                        similarity_threshold FLOAT,
                        metadata JSONB
                    )
                """)

                # Create indexes for efficient search
                # IVFFLAT index for approximate nearest neighbor search
                lists = kwargs.get("lists", 100)  # Number of clusters
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                    ON {self.table_name}
                    USING ivfflat (embedding {self.DISTANCE_METRICS[distance_metric]})
                    WITH (lists = {lists})
                """)

                # Additional indexes for filtering
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_decision_id_idx
                    ON {self.table_name} (decision_id)
                """)

                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_tags_idx
                    ON {self.table_name} USING GIN (tags)
                """)

                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_metadata_idx
                    ON {self.table_name} USING GIN (metadata)
                """)

            logger.info(
                f"Created pgvector table '{self.table_name}' "
                f"with dimension {dimension} and {distance_metric} distance"
            )
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise

    async def delete_collection(self) -> None:
        """Delete the table."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            self._dimension = None
            logger.info(f"Deleted table '{self.table_name}'")
        except Exception as e:
            logger.error(f"Failed to delete table: {e}")
            raise

    async def collection_exists(self) -> bool:
        """Check if table exists."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = $1
                    )
                    """,
                    self.table_name
                )
                return result
        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get table information."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                # Get row count
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {self.table_name}"
                )

                # Get table size
                size = await conn.fetchval(
                    """
                    SELECT pg_size_pretty(pg_total_relation_size($1))
                    """,
                    self.table_name
                )

                return {
                    "name": self.table_name,
                    "dimension": self._dimension,
                    "distance_metric": self._distance_metric,
                    "row_count": count,
                    "table_size": size,
                }
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            raise

    async def upsert(
        self,
        precedent_id: str,
        embedding: np.ndarray,
        metadata: EmbeddingMetadata,
    ) -> None:
        """Insert or update a vector."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        self.validate_embedding(embedding, self._dimension)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (precedent_id, embedding, decision_id, embedding_model,
                     created_at, context, tags, similarity_threshold, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (precedent_id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        decision_id = EXCLUDED.decision_id,
                        embedding_model = EXCLUDED.embedding_model,
                        created_at = EXCLUDED.created_at,
                        context = EXCLUDED.context,
                        tags = EXCLUDED.tags,
                        similarity_threshold = EXCLUDED.similarity_threshold,
                        metadata = EXCLUDED.metadata
                    """,
                    precedent_id,
                    embedding,
                    metadata.decision_id,
                    metadata.embedding_model,
                    metadata.created_at,
                    metadata.context,
                    metadata.tags,
                    metadata.similarity_threshold,
                    metadata.custom_fields,
                )
            logger.debug(f"Upserted embedding for precedent {precedent_id}")
        except Exception as e:
            logger.error(f"Failed to upsert embedding: {e}")
            raise

    async def upsert_batch(
        self,
        precedent_ids: List[str],
        embeddings: np.ndarray,
        metadatas: List[EmbeddingMetadata],
        batch_size: int = 100,
    ) -> None:
        """Insert or update multiple vectors in batches."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        if len(precedent_ids) != len(metadatas):
            raise ValueError("precedent_ids and metadatas must have same length")
        if embeddings.shape[0] != len(precedent_ids):
            raise ValueError("Number of embeddings must match precedent_ids")

        # Process in batches
        for i in range(0, len(precedent_ids), batch_size):
            batch_ids = precedent_ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            try:
                async with self.pool.acquire() as conn:
                    # Use executemany for batch insert
                    await conn.executemany(
                        f"""
                        INSERT INTO {self.table_name}
                        (precedent_id, embedding, decision_id, embedding_model,
                         created_at, context, tags, similarity_threshold, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (precedent_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            decision_id = EXCLUDED.decision_id,
                            embedding_model = EXCLUDED.embedding_model,
                            created_at = EXCLUDED.created_at,
                            context = EXCLUDED.context,
                            tags = EXCLUDED.tags,
                            similarity_threshold = EXCLUDED.similarity_threshold,
                            metadata = EXCLUDED.metadata
                        """,
                        [
                            (
                                pid,
                                emb,
                                meta.decision_id,
                                meta.embedding_model,
                                meta.created_at,
                                meta.context,
                                meta.tags,
                                meta.similarity_threshold,
                                meta.custom_fields,
                            )
                            for pid, emb, meta in zip(batch_ids, batch_embeddings, batch_metadatas)
                        ]
                    )
                logger.debug(f"Upserted batch of {len(batch_ids)} embeddings")
            except Exception as e:
                logger.error(f"Failed to upsert batch: {e}")
                raise

    async def get(
        self,
        precedent_id: str,
        include_embedding: bool = True,
    ) -> Optional[Tuple[np.ndarray, EmbeddingMetadata]]:
        """Retrieve a vector by ID."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                if include_embedding:
                    query = f"""
                        SELECT embedding, decision_id, embedding_model,
                               created_at, context, tags, similarity_threshold, metadata
                        FROM {self.table_name}
                        WHERE precedent_id = $1
                    """
                else:
                    query = f"""
                        SELECT decision_id, embedding_model,
                               created_at, context, tags, similarity_threshold, metadata
                        FROM {self.table_name}
                        WHERE precedent_id = $1
                    """

                row = await conn.fetchrow(query, precedent_id)

                if not row:
                    return None

                if include_embedding:
                    embedding = np.array(row["embedding"], dtype=np.float32)
                    offset = 1
                else:
                    embedding = np.array([], dtype=np.float32)
                    offset = 0

                metadata = EmbeddingMetadata(
                    precedent_id=precedent_id,
                    decision_id=row[offset],
                    embedding_model=row[offset + 1],
                    created_at=row[offset + 2],
                    context=row[offset + 3],
                    tags=row[offset + 4],
                    similarity_threshold=row[offset + 5],
                    custom_fields=row[offset + 6],
                )

                return (embedding, metadata)
        except Exception as e:
            logger.error(f"Failed to retrieve embedding: {e}")
            raise

    async def delete(self, precedent_id: str) -> bool:
        """Delete a vector."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE precedent_id = $1",
                    precedent_id
                )
                # Result is like "DELETE 1"
                return result.endswith("1")
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False

    async def delete_batch(self, precedent_ids: List[str]) -> int:
        """Delete multiple vectors."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE precedent_id = ANY($1)",
                    precedent_ids
                )
                # Extract count from "DELETE N"
                return int(result.split()[-1])
        except Exception as e:
            logger.error(f"Failed to delete batch: {e}")
            return 0

    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> Tuple[str, List[Any]]:
        """Build SQL WHERE clause from filters."""
        if not filters:
            return "", []

        conditions = []
        params = []
        param_idx = 1

        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(f"{key} = ANY(${param_idx})")
                params.append(value)
                param_idx += 1
            elif isinstance(value, dict):
                # Range filter
                if "gte" in value:
                    conditions.append(f"{key} >= ${param_idx}")
                    params.append(value["gte"])
                    param_idx += 1
                if "lte" in value:
                    conditions.append(f"{key} <= ${param_idx}")
                    params.append(value["lte"])
                    param_idx += 1
                if "gt" in value:
                    conditions.append(f"{key} > ${param_idx}")
                    params.append(value["gt"])
                    param_idx += 1
                if "lt" in value:
                    conditions.append(f"{key} < ${param_idx}")
                    params.append(value["lt"])
                    param_idx += 1
            else:
                conditions.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else ""
        return where_clause, params

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
        include_embeddings: bool = False,
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        self.validate_embedding(query_embedding, self._dimension)

        distance_op = self.DISTANCE_METRICS[self._distance_metric]
        where_clause, params = self._build_where_clause(filters)

        try:
            async with self.pool.acquire() as conn:
                if include_embeddings:
                    select_cols = "precedent_id, decision_id, embedding, embedding_model, created_at, context, tags, similarity_threshold, metadata"
                else:
                    select_cols = "precedent_id, decision_id, embedding_model, created_at, context, tags, similarity_threshold, metadata"

                if where_clause:
                    query = f"""
                        SELECT {select_cols},
                               embedding {distance_op} $1 AS distance
                        FROM {self.table_name}
                        WHERE {where_clause}
                        ORDER BY distance
                        LIMIT {top_k}
                    """
                    params.insert(0, query_embedding)
                else:
                    query = f"""
                        SELECT {select_cols},
                               embedding {distance_op} $1 AS distance
                        FROM {self.table_name}
                        ORDER BY distance
                        LIMIT {top_k}
                    """
                    params = [query_embedding]

                rows = await conn.fetch(query, *params)

                search_results = []
                for row in rows:
                    distance = row["distance"]
                    # Convert distance to similarity score (0-1, higher is better)
                    if self._distance_metric == "cosine":
                        score = 1.0 - distance
                    elif self._distance_metric == "dot":
                        score = -distance  # Negative inner product
                    else:  # euclidean
                        score = 1.0 / (1.0 + distance)

                    # Apply min_score filter
                    if min_score is not None and score < min_score:
                        continue

                    if include_embeddings:
                        embedding = np.array(row["embedding"], dtype=np.float32)
                        offset = 1
                    else:
                        embedding = None
                        offset = 0

                    metadata = EmbeddingMetadata(
                        precedent_id=row["precedent_id"],
                        decision_id=row["decision_id"],
                        embedding_model=row[offset + 1],
                        created_at=row[offset + 2],
                        context=row[offset + 3],
                        tags=row[offset + 4],
                        similarity_threshold=row[offset + 5],
                        custom_fields=row[offset + 6],
                    )

                    result = SearchResult(
                        precedent_id=row["precedent_id"],
                        decision_id=row["decision_id"],
                        score=score,
                        distance=distance,
                        metadata=metadata,
                        embedding=embedding,
                    )
                    search_results.append(result)

                return search_results
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            raise

    async def search_batch(
        self,
        query_embeddings: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> List[List[SearchResult]]:
        """Search for similar vectors in batch."""
        # PostgreSQL doesn't have native batch search, so we iterate
        results = []
        for query_embedding in query_embeddings:
            result = await self.search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
                min_score=min_score,
                include_embeddings=False,
            )
            results.append(result)

        return results

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count vectors in the collection."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        where_clause, params = self._build_where_clause(filters)

        try:
            async with self.pool.acquire() as conn:
                if where_clause:
                    query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
                    count = await conn.fetchval(query, *params)
                else:
                    query = f"SELECT COUNT(*) FROM {self.table_name}"
                    count = await conn.fetchval(query)

                return count
        except Exception as e:
            logger.error(f"Failed to count: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")

                size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_total_relation_size($1))",
                    self.table_name
                )

                index_size = await conn.fetchval(
                    """
                    SELECT pg_size_pretty(SUM(pg_relation_size(indexrelid)))
                    FROM pg_index
                    WHERE indrelid = $1::regclass
                    """,
                    self.table_name
                )

                return {
                    "backend": "pgvector",
                    "table": self.table_name,
                    "row_count": count,
                    "dimension": self._dimension,
                    "distance_metric": self._distance_metric,
                    "table_size": size,
                    "index_size": index_size,
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
