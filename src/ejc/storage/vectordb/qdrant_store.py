"""
Qdrant vector database backend implementation.

High-performance vector similarity search engine with rich filtering capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
    SearchParams,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from .base import VectorStore, SearchResult, EmbeddingMetadata

logger = logging.getLogger(__name__)


class QdrantStore(VectorStore):
    """Qdrant vector database implementation."""

    DISTANCE_METRICS = {
        "cosine": Distance.COSINE,
        "euclidean": Distance.EUCLID,
        "dot": Distance.DOT,
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        collection_name: str = "precedent_embeddings",
        prefer_grpc: bool = False,
        timeout: float = 60.0,
    ):
        """
        Initialize Qdrant store.

        Args:
            host: Qdrant server host
            port: Qdrant server port (6333 for HTTP, 6334 for gRPC)
            api_key: API key for authentication (for Qdrant Cloud)
            collection_name: Name of the collection
            prefer_grpc: Use gRPC instead of HTTP
            timeout: Request timeout in seconds
        """
        super().__init__(collection_name)
        self.host = host
        self.port = port
        self.api_key = api_key
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout
        self.client: Optional[QdrantClient] = None
        self._dimension: Optional[int] = None

    async def connect(self) -> None:
        """Establish connection to Qdrant."""
        try:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                prefer_grpc=self.prefer_grpc,
                timeout=self.timeout,
            )
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection to Qdrant."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Disconnected from Qdrant")

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            if not self.client:
                return False
            # Try to list collections as a health check
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def create_collection(
        self,
        dimension: int,
        distance_metric: str = "cosine",
        **kwargs
    ) -> None:
        """Create a new collection in Qdrant."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        distance = self.DISTANCE_METRICS.get(distance_metric.lower(), Distance.COSINE)

        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=distance,
                ),
                **kwargs
            )
            self._dimension = dimension
            logger.info(
                f"Created Qdrant collection '{self.collection_name}' "
                f"with dimension {dimension} and {distance_metric} distance"
            )
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    async def delete_collection(self) -> None:
        """Delete the collection."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self._dimension = None
            logger.info(f"Deleted collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    async def collection_exists(self) -> bool:
        """Check if collection exists."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            collections = self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "name": self.collection_name,
                "dimension": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.name,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status.name,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    async def upsert(
        self,
        precedent_id: str,
        embedding: np.ndarray,
        metadata: EmbeddingMetadata,
    ) -> None:
        """Insert or update a vector."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        self.validate_embedding(embedding, self._dimension)

        point = PointStruct(
            id=precedent_id,
            vector=embedding.tolist(),
            payload=metadata.to_dict(),
        )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
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
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        if len(precedent_ids) != len(metadatas):
            raise ValueError("precedent_ids and metadatas must have same length")
        if embeddings.shape[0] != len(precedent_ids):
            raise ValueError("Number of embeddings must match precedent_ids")

        # Process in batches
        for i in range(0, len(precedent_ids), batch_size):
            batch_ids = precedent_ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            points = [
                PointStruct(
                    id=pid,
                    vector=emb.tolist(),
                    payload=meta.to_dict(),
                )
                for pid, emb, meta in zip(batch_ids, batch_embeddings, batch_metadatas)
            ]

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                logger.debug(f"Upserted batch of {len(points)} embeddings")
            except Exception as e:
                logger.error(f"Failed to upsert batch: {e}")
                raise

    async def get(
        self,
        precedent_id: str,
        include_embedding: bool = True,
    ) -> Optional[Tuple[np.ndarray, EmbeddingMetadata]]:
        """Retrieve a vector by ID."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[precedent_id],
                with_vectors=include_embedding,
                with_payload=True,
            )

            if not points:
                return None

            point = points[0]
            metadata = EmbeddingMetadata.from_dict(point.payload)

            if include_embedding and point.vector:
                embedding = np.array(point.vector, dtype=np.float32)
            else:
                embedding = np.array([], dtype=np.float32)

            return (embedding, metadata)
        except Exception as e:
            logger.error(f"Failed to retrieve embedding: {e}")
            raise

    async def delete(self, precedent_id: str) -> bool:
        """Delete a vector."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=[precedent_id],
            )
            return result.status.name == "COMPLETED"
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False

    async def delete_batch(self, precedent_ids: List[str]) -> int:
        """Delete multiple vectors."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=precedent_ids,
            )
            # Qdrant doesn't return count, so we assume success for all
            return len(precedent_ids) if result.status.name == "COMPLETED" else 0
        except Exception as e:
            logger.error(f"Failed to delete batch: {e}")
            return 0

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """Build Qdrant filter from dictionary."""
        if not filters:
            return None

        conditions = []

        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(
                    FieldCondition(key=key, match=MatchAny(any=value))
                )
            elif isinstance(value, dict):
                # Range filter
                if "gte" in value or "lte" in value or "gt" in value or "lt" in value:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            range=Range(
                                gte=value.get("gte"),
                                lte=value.get("lte"),
                                gt=value.get("gt"),
                                lt=value.get("lt"),
                            )
                        )
                    )
            else:
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )

        return Filter(must=conditions) if conditions else None

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
        include_embeddings: bool = False,
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        self.validate_embedding(query_embedding, self._dimension)

        qdrant_filter = self._build_filter(filters)

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                query_filter=qdrant_filter,
                with_vectors=include_embeddings,
                with_payload=True,
                score_threshold=min_score,
            )

            search_results = []
            for hit in results:
                metadata = EmbeddingMetadata.from_dict(hit.payload)

                # Qdrant returns score (higher is better)
                # For cosine: score is similarity in [-1, 1], distance = 1 - score
                # For euclidean: score is -distance, distance = -score
                score = hit.score
                distance = 1.0 - score if score <= 1.0 else 0.0

                result = SearchResult(
                    precedent_id=str(hit.id),
                    decision_id=metadata.decision_id,
                    score=score,
                    distance=distance,
                    metadata=metadata,
                    embedding=np.array(hit.vector, dtype=np.float32) if include_embeddings and hit.vector else None,
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
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        # Qdrant doesn't have native batch search, so we iterate
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
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            if filters:
                # Use scroll to count with filters
                qdrant_filter = self._build_filter(filters)
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=qdrant_filter,
                    limit=1,
                    with_payload=False,
                    with_vectors=False,
                )
                # This is approximate - full count would require pagination
                info = self.client.get_collection(self.collection_name)
                return info.points_count
            else:
                info = self.client.get_collection(self.collection_name)
                return info.points_count
        except Exception as e:
            logger.error(f"Failed to count: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if not self.client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "backend": "qdrant",
                "collection": self.collection_name,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "dimension": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.name,
                "status": info.status.name,
                "optimizer_status": info.optimizer_status.name if info.optimizer_status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
