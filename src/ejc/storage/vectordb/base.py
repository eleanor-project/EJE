"""
Abstract base class for vector storage backends.

Defines the interface that all vector storage implementations must follow.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np


@dataclass
class EmbeddingMetadata:
    """Metadata associated with a vector embedding."""

    precedent_id: str
    decision_id: str
    embedding_model: str
    created_at: datetime
    context: Optional[str] = None
    tags: Optional[List[str]] = None
    similarity_threshold: Optional[float] = None
    custom_fields: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "precedent_id": self.precedent_id,
            "decision_id": self.decision_id,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat(),
            "context": self.context,
            "tags": self.tags or [],
            "similarity_threshold": self.similarity_threshold,
            **(self.custom_fields or {}),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingMetadata":
        """Create from dictionary."""
        custom_fields = {
            k: v for k, v in data.items()
            if k not in {
                "precedent_id", "decision_id", "embedding_model",
                "created_at", "context", "tags", "similarity_threshold"
            }
        }

        return cls(
            precedent_id=data["precedent_id"],
            decision_id=data["decision_id"],
            embedding_model=data["embedding_model"],
            created_at=datetime.fromisoformat(data["created_at"]),
            context=data.get("context"),
            tags=data.get("tags"),
            similarity_threshold=data.get("similarity_threshold"),
            custom_fields=custom_fields if custom_fields else None,
        )


@dataclass
class SearchResult:
    """Result from a similarity search."""

    precedent_id: str
    decision_id: str
    score: float  # Similarity score (higher is more similar)
    distance: float  # Distance metric (lower is more similar)
    metadata: EmbeddingMetadata
    embedding: Optional[np.ndarray] = None  # Include embedding if requested

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "precedent_id": self.precedent_id,
            "decision_id": self.decision_id,
            "score": self.score,
            "distance": self.distance,
            "metadata": self.metadata.to_dict(),
        }
        if include_embedding and self.embedding is not None:
            result["embedding"] = self.embedding.tolist()
        return result


class VectorStore(ABC):
    """
    Abstract base class for vector storage backends.

    All vector storage implementations (Qdrant, Pinecone, pgvector)
    must implement this interface.
    """

    def __init__(self, collection_name: str = "precedent_embeddings"):
        """
        Initialize vector store.

        Args:
            collection_name: Name of the collection/index to use
        """
        self.collection_name = collection_name

    # Connection and Health

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the vector database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the vector database."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector database is healthy and reachable.

        Returns:
            True if healthy, False otherwise
        """
        pass

    # Collection/Index Management

    @abstractmethod
    async def create_collection(
        self,
        dimension: int,
        distance_metric: str = "cosine",
        **kwargs
    ) -> None:
        """
        Create a new collection/index.

        Args:
            dimension: Dimensionality of the vectors
            distance_metric: Distance metric to use (cosine, euclidean, dot)
            **kwargs: Backend-specific parameters
        """
        pass

    @abstractmethod
    async def delete_collection(self) -> None:
        """Delete the collection/index."""
        pass

    @abstractmethod
    async def collection_exists(self) -> bool:
        """
        Check if the collection/index exists.

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection metadata (size, dimension, etc.)
        """
        pass

    # CRUD Operations

    @abstractmethod
    async def upsert(
        self,
        precedent_id: str,
        embedding: np.ndarray,
        metadata: EmbeddingMetadata,
    ) -> None:
        """
        Insert or update a vector embedding.

        Args:
            precedent_id: Unique ID for the precedent
            embedding: Vector embedding (numpy array)
            metadata: Metadata associated with the embedding
        """
        pass

    @abstractmethod
    async def upsert_batch(
        self,
        precedent_ids: List[str],
        embeddings: np.ndarray,
        metadatas: List[EmbeddingMetadata],
        batch_size: int = 100,
    ) -> None:
        """
        Insert or update multiple embeddings in batches.

        Args:
            precedent_ids: List of precedent IDs
            embeddings: Array of embeddings (shape: [n, dimension])
            metadatas: List of metadata objects
            batch_size: Number of embeddings per batch
        """
        pass

    @abstractmethod
    async def get(
        self,
        precedent_id: str,
        include_embedding: bool = True,
    ) -> Optional[Tuple[np.ndarray, EmbeddingMetadata]]:
        """
        Retrieve a vector embedding by ID.

        Args:
            precedent_id: ID of the precedent
            include_embedding: Whether to include the embedding vector

        Returns:
            Tuple of (embedding, metadata) or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, precedent_id: str) -> bool:
        """
        Delete a vector embedding.

        Args:
            precedent_id: ID of the precedent to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_batch(self, precedent_ids: List[str]) -> int:
        """
        Delete multiple embeddings.

        Args:
            precedent_ids: List of precedent IDs to delete

        Returns:
            Number of embeddings deleted
        """
        pass

    # Search Operations

    @abstractmethod
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
        include_embeddings: bool = False,
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"tags": ["critical"]})
            min_score: Minimum similarity score threshold
            include_embeddings: Whether to include embedding vectors in results

        Returns:
            List of search results, sorted by similarity (descending)
        """
        pass

    @abstractmethod
    async def search_batch(
        self,
        query_embeddings: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> List[List[SearchResult]]:
        """
        Search for similar vectors in batch.

        Args:
            query_embeddings: Array of query vectors (shape: [n, dimension])
            top_k: Number of results per query
            filters: Metadata filters
            min_score: Minimum similarity score threshold

        Returns:
            List of result lists, one per query
        """
        pass

    # Statistics and Monitoring

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in the collection.

        Args:
            filters: Optional metadata filters

        Returns:
            Number of vectors
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with stats (count, dimension, memory usage, etc.)
        """
        pass

    # Utility Methods

    def normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """Normalize a vector to unit length (for cosine similarity)."""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def validate_embedding(
        self,
        embedding: np.ndarray,
        expected_dim: Optional[int] = None,
    ) -> None:
        """
        Validate that an embedding is properly formatted.

        Args:
            embedding: The embedding to validate
            expected_dim: Expected dimensionality

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(embedding, np.ndarray):
            raise ValueError("Embedding must be a numpy array")

        if embedding.ndim != 1:
            raise ValueError(f"Embedding must be 1-dimensional, got shape {embedding.shape}")

        if expected_dim is not None and embedding.shape[0] != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim}, "
                f"got {embedding.shape[0]}"
            )

        if not np.isfinite(embedding).all():
            raise ValueError("Embedding contains non-finite values")
