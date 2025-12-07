"""
Pinecone vector database backend implementation.

Managed vector database service with automatic scaling and serverless options.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime

from pinecone import Pinecone, ServerlessSpec, PodSpec
from pinecone.exceptions import PineconeException

from .base import VectorStore, SearchResult, EmbeddingMetadata

logger = logging.getLogger(__name__)


class PineconeStore(VectorStore):
    """Pinecone vector database implementation."""

    DISTANCE_METRICS = {
        "cosine": "cosine",
        "euclidean": "euclidean",
        "dot": "dotproduct",
    }

    def __init__(
        self,
        api_key: str,
        environment: Optional[str] = None,
        index_name: str = "precedent-embeddings",
        namespace: str = "",
        serverless: bool = True,
        cloud: str = "aws",
        region: str = "us-east-1",
    ):
        """
        Initialize Pinecone store.

        Args:
            api_key: Pinecone API key
            environment: Pinecone environment (deprecated, use serverless)
            index_name: Name of the index
            namespace: Namespace within the index (for multi-tenancy)
            serverless: Use serverless spec (True) or pod-based (False)
            cloud: Cloud provider (aws, gcp, azure) - for serverless
            region: Cloud region - for serverless
        """
        super().__init__(index_name)
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.namespace = namespace
        self.serverless = serverless
        self.cloud = cloud
        self.region = region
        self.client: Optional[Pinecone] = None
        self.index = None
        self._dimension: Optional[int] = None

    async def connect(self) -> None:
        """Establish connection to Pinecone."""
        try:
            self.client = Pinecone(api_key=self.api_key)
            logger.info("Connected to Pinecone")
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection to Pinecone."""
        # Pinecone client doesn't need explicit disconnect
        self.client = None
        self.index = None
        logger.info("Disconnected from Pinecone")

    async def health_check(self) -> bool:
        """Check if Pinecone is healthy."""
        try:
            if not self.client:
                return False
            # Try to list indexes as health check
            self.client.list_indexes()
            return True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return False

    async def create_collection(
        self,
        dimension: int,
        distance_metric: str = "cosine",
        **kwargs
    ) -> None:
        """Create a new index in Pinecone."""
        if not self.client:
            raise RuntimeError("Not connected to Pinecone")

        metric = self.DISTANCE_METRICS.get(distance_metric.lower(), "cosine")

        try:
            if self.serverless:
                spec = ServerlessSpec(cloud=self.cloud, region=self.region)
            else:
                # Pod-based (legacy)
                spec = PodSpec(
                    environment=self.environment or "us-east-1-aws",
                    pod_type=kwargs.get("pod_type", "p1.x1"),
                    pods=kwargs.get("pods", 1),
                )

            self.client.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=spec,
            )
            self._dimension = dimension
            logger.info(
                f"Created Pinecone index '{self.index_name}' "
                f"with dimension {dimension} and {distance_metric} distance"
            )
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    async def delete_collection(self) -> None:
        """Delete the index."""
        if not self.client:
            raise RuntimeError("Not connected to Pinecone")

        try:
            self.client.delete_index(name=self.index_name)
            self._dimension = None
            self.index = None
            logger.info(f"Deleted index '{self.index_name}'")
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            raise

    async def collection_exists(self) -> bool:
        """Check if index exists."""
        if not self.client:
            raise RuntimeError("Not connected to Pinecone")

        try:
            indexes = self.client.list_indexes()
            return any(idx.name == self.index_name for idx in indexes.indexes)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get index information."""
        if not self.client:
            raise RuntimeError("Not connected to Pinecone")

        try:
            index_desc = self.client.describe_index(name=self.index_name)
            index = self.client.Index(self.index_name)
            stats = index.describe_index_stats()

            return {
                "name": self.index_name,
                "dimension": index_desc.dimension,
                "distance_metric": index_desc.metric,
                "total_vector_count": stats.total_vector_count,
                "namespaces": stats.namespaces,
                "status": index_desc.status.state if index_desc.status else "unknown",
            }
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            raise

    def _ensure_index(self):
        """Ensure index is connected."""
        if not self.client:
            raise RuntimeError("Not connected to Pinecone")

        if not self.index:
            self.index = self.client.Index(self.index_name)

    async def upsert(
        self,
        precedent_id: str,
        embedding: np.ndarray,
        metadata: EmbeddingMetadata,
    ) -> None:
        """Insert or update a vector."""
        self._ensure_index()
        self.validate_embedding(embedding, self._dimension)

        # Pinecone metadata must be simple types
        payload = metadata.to_dict()
        # Convert datetime to ISO string
        if isinstance(payload.get("created_at"), datetime):
            payload["created_at"] = payload["created_at"].isoformat()

        try:
            self.index.upsert(
                vectors=[(precedent_id, embedding.tolist(), payload)],
                namespace=self.namespace,
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
        self._ensure_index()

        if len(precedent_ids) != len(metadatas):
            raise ValueError("precedent_ids and metadatas must have same length")
        if embeddings.shape[0] != len(precedent_ids):
            raise ValueError("Number of embeddings must match precedent_ids")

        # Process in batches
        for i in range(0, len(precedent_ids), batch_size):
            batch_ids = precedent_ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            vectors = []
            for pid, emb, meta in zip(batch_ids, batch_embeddings, batch_metadatas):
                payload = meta.to_dict()
                # Convert datetime to ISO string
                if isinstance(payload.get("created_at"), datetime):
                    payload["created_at"] = payload["created_at"].isoformat()
                vectors.append((pid, emb.tolist(), payload))

            try:
                self.index.upsert(
                    vectors=vectors,
                    namespace=self.namespace,
                )
                logger.debug(f"Upserted batch of {len(vectors)} embeddings")
            except Exception as e:
                logger.error(f"Failed to upsert batch: {e}")
                raise

    async def get(
        self,
        precedent_id: str,
        include_embedding: bool = True,
    ) -> Optional[Tuple[np.ndarray, EmbeddingMetadata]]:
        """Retrieve a vector by ID."""
        self._ensure_index()

        try:
            result = self.index.fetch(
                ids=[precedent_id],
                namespace=self.namespace,
            )

            if precedent_id not in result.vectors:
                return None

            vector_data = result.vectors[precedent_id]
            metadata_dict = vector_data.metadata

            # Convert ISO string back to datetime
            if "created_at" in metadata_dict:
                metadata_dict["created_at"] = datetime.fromisoformat(
                    metadata_dict["created_at"]
                )

            metadata = EmbeddingMetadata.from_dict(metadata_dict)

            if include_embedding:
                embedding = np.array(vector_data.values, dtype=np.float32)
            else:
                embedding = np.array([], dtype=np.float32)

            return (embedding, metadata)
        except Exception as e:
            logger.error(f"Failed to retrieve embedding: {e}")
            raise

    async def delete(self, precedent_id: str) -> bool:
        """Delete a vector."""
        self._ensure_index()

        try:
            self.index.delete(
                ids=[precedent_id],
                namespace=self.namespace,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False

    async def delete_batch(self, precedent_ids: List[str]) -> int:
        """Delete multiple vectors."""
        self._ensure_index()

        try:
            self.index.delete(
                ids=precedent_ids,
                namespace=self.namespace,
            )
            return len(precedent_ids)
        except Exception as e:
            logger.error(f"Failed to delete batch: {e}")
            return 0

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build Pinecone filter from dictionary."""
        if not filters:
            return None

        # Pinecone uses a specific filter format
        # See: https://docs.pinecone.io/docs/metadata-filtering
        pinecone_filter = {}

        for key, value in filters.items():
            if isinstance(value, list):
                pinecone_filter[key] = {"$in": value}
            elif isinstance(value, dict):
                # Range filter
                range_filter = {}
                if "gte" in value:
                    range_filter["$gte"] = value["gte"]
                if "lte" in value:
                    range_filter["$lte"] = value["lte"]
                if "gt" in value:
                    range_filter["$gt"] = value["gt"]
                if "lt" in value:
                    range_filter["$lt"] = value["lt"]
                pinecone_filter[key] = range_filter
            else:
                pinecone_filter[key] = {"$eq": value}

        return pinecone_filter if pinecone_filter else None

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
        include_embeddings: bool = False,
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        self._ensure_index()
        self.validate_embedding(query_embedding, self._dimension)

        pinecone_filter = self._build_filter(filters)

        try:
            results = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                filter=pinecone_filter,
                include_values=include_embeddings,
                include_metadata=True,
                namespace=self.namespace,
            )

            search_results = []
            for match in results.matches:
                # Convert ISO string back to datetime
                metadata_dict = match.metadata
                if "created_at" in metadata_dict:
                    metadata_dict["created_at"] = datetime.fromisoformat(
                        metadata_dict["created_at"]
                    )

                metadata = EmbeddingMetadata.from_dict(metadata_dict)

                # Apply min_score filter
                if min_score is not None and match.score < min_score:
                    continue

                # Pinecone returns score (higher is better)
                # For cosine: score is similarity in [0, 1]
                # For euclidean: score is -distance
                score = match.score
                distance = 1.0 - score if score <= 1.0 else 0.0

                result = SearchResult(
                    precedent_id=match.id,
                    decision_id=metadata.decision_id,
                    score=score,
                    distance=distance,
                    metadata=metadata,
                    embedding=np.array(match.values, dtype=np.float32) if include_embeddings and match.values else None,
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
        # Pinecone doesn't have native batch query, so we iterate
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
        self._ensure_index()

        try:
            stats = self.index.describe_index_stats()

            if filters:
                # Pinecone doesn't support counting with filters directly
                # We'd need to query and count results
                logger.warning("Pinecone count with filters is not efficient")
                return stats.total_vector_count  # Return total as approximation
            else:
                if self.namespace:
                    return stats.namespaces.get(self.namespace, {}).get("vector_count", 0)
                else:
                    return stats.total_vector_count
        except Exception as e:
            logger.error(f"Failed to count: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        self._ensure_index()

        try:
            index_desc = self.client.describe_index(name=self.index_name)
            stats = self.index.describe_index_stats()

            return {
                "backend": "pinecone",
                "index": self.index_name,
                "namespace": self.namespace,
                "dimension": index_desc.dimension,
                "distance_metric": index_desc.metric,
                "total_vector_count": stats.total_vector_count,
                "namespaces": {k: v.vector_count for k, v in stats.namespaces.items()},
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
