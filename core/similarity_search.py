"""
Similarity Search for Precedent Retrieval

Task 3.3: Implement Similarity Search Wrapper

Provides embedding-based similarity search for retrieving relevant precedents
using cosine similarity.
"""

import logging
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from core.precedent_storage import PrecedentStorage

logger = logging.getLogger("ejc.core.similarity_search")


@dataclass
class SimilarityResult:
    """Result from similarity search."""

    precedent_id: str
    query: str
    decision: str
    confidence: float
    similarity_score: float
    precedent: Dict[str, Any]


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector (numpy array)
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get embedding dimensionality."""
        pass


class SimpleHashEmbedding(EmbeddingModel):
    """
    Simple hash-based embedding for testing.

    Not suitable for production - use sentence-transformers or similar.
    Creates deterministic embeddings from text hashes.
    """

    def __init__(self, dim: int = 128):
        """
        Initialize hash embedding.

        Args:
            dim: Embedding dimensionality
        """
        self._dim = dim

    def embed(self, text: str) -> np.ndarray:
        """Generate hash-based embedding."""
        # Create deterministic embedding from hash
        hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()

        # Convert to float vector
        embedding = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)

        # Pad or truncate to desired dimension
        if len(embedding) < self._dim:
            embedding = np.pad(embedding, (0, self._dim - len(embedding)))
        else:
            embedding = embedding[:self._dim]

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for batch."""
        return [self.embed(text) for text in texts]

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimensionality."""
        return self._dim


class SimilaritySearchEngine:
    """
    Similarity search engine for precedent retrieval.

    Uses embeddings and cosine similarity to find relevant precedents.
    """

    def __init__(
        self,
        storage: PrecedentStorage,
        embedding_model: EmbeddingModel,
        cache_embeddings: bool = True
    ):
        """
        Initialize similarity search engine.

        Args:
            storage: Precedent storage backend
            embedding_model: Embedding model to use
            cache_embeddings: Whether to cache embeddings
        """
        self.storage = storage
        self.embedding_model = embedding_model
        self.cache_embeddings = cache_embeddings
        self._embedding_cache: Dict[str, np.ndarray] = {}

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.0,
        filter_decision: Optional[str] = None
    ) -> List[SimilarityResult]:
        """
        Search for similar precedents.

        Args:
            query: Query text
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            filter_decision: Optional decision filter (ALLOW, DENY, etc.)

        Returns:
            List of SimilarityResult objects, sorted by similarity
        """
        # Generate query embedding
        query_embedding = self.embedding_model.embed(query)

        # Get all precedents (or filtered by decision)
        if filter_decision:
            precedents = self.storage.find_by_decision(filter_decision, limit=1000)
        else:
            precedents = self.storage.find_recent(limit=1000)

        if not precedents:
            logger.warning("No precedents found in storage")
            return []

        # Calculate similarities
        results = []
        for precedent in precedents:
            precedent_query = precedent["query"]
            precedent_id = precedent["precedent_id"]

            # Get or compute embedding
            precedent_embedding = self._get_embedding(precedent_id, precedent_query)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, precedent_embedding)

            # Apply threshold
            if similarity >= min_similarity:
                results.append(
                    SimilarityResult(
                        precedent_id=precedent_id,
                        query=precedent_query,
                        decision=precedent["decision"],
                        confidence=precedent["confidence"],
                        similarity_score=float(similarity),
                        precedent=precedent
                    )
                )

        # Sort by similarity (descending)
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Return top-k
        return results[:top_k]

    def search_by_id(
        self,
        precedent_id: str,
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[SimilarityResult]:
        """
        Find similar precedents to a given precedent.

        Args:
            precedent_id: ID of precedent to find similar cases for
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of SimilarityResult objects
        """
        # Get source precedent
        source_precedent = self.storage.get_precedent(precedent_id)
        if not source_precedent:
            raise ValueError(f"Precedent {precedent_id} not found")

        # Use its query for search
        query = source_precedent["query"]

        # Search (excluding the source itself)
        results = self.search(query, top_k + 1, min_similarity)

        # Filter out source precedent
        results = [r for r in results if r.precedent_id != precedent_id]

        return results[:top_k]

    def _get_embedding(self, precedent_id: str, query: str) -> np.ndarray:
        """
        Get embedding for precedent (with caching).

        Args:
            precedent_id: Precedent ID
            query: Query text

        Returns:
            Embedding vector
        """
        if self.cache_embeddings and precedent_id in self._embedding_cache:
            return self._embedding_cache[precedent_id]

        # Compute embedding
        embedding = self.embedding_model.embed(query)

        # Cache if enabled
        if self.cache_embeddings:
            self._embedding_cache[precedent_id] = embedding

        return embedding

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (-1.0 to 1.0)
        """
        # Compute dot product
        dot_product = np.dot(vec1, vec2)

        # Compute norms
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (norm1 * norm2)

        # Clamp to [-1, 1] (numerical stability)
        return float(np.clip(similarity, -1.0, 1.0))

    def precompute_embeddings(self, precedent_ids: Optional[List[str]] = None):
        """
        Precompute embeddings for precedents.

        Args:
            precedent_ids: Optional list of IDs (computes all if None)
        """
        if precedent_ids is None:
            # Get all precedents
            precedents = self.storage.find_recent(limit=10000)
            precedent_ids = [p["precedent_id"] for p in precedents]
        else:
            precedents = [self.storage.get_precedent(id) for id in precedent_ids]
            precedents = [p for p in precedents if p is not None]

        logger.info(f"Precomputing embeddings for {len(precedents)} precedents")

        for precedent in precedents:
            precedent_id = precedent["precedent_id"]
            query = precedent["query"]

            if precedent_id not in self._embedding_cache:
                embedding = self.embedding_model.embed(query)
                self._embedding_cache[precedent_id] = embedding

        logger.info(f"Precomputed {len(self._embedding_cache)} embeddings")

    def clear_cache(self):
        """Clear embedding cache."""
        self._embedding_cache.clear()
        logger.info("Cleared embedding cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        return {
            "cache_enabled": self.cache_embeddings,
            "cached_embeddings": len(self._embedding_cache),
            "embedding_dim": self.embedding_model.embedding_dim
        }


def create_search_engine(
    storage: Optional[PrecedentStorage] = None,
    embedding_model: Optional[EmbeddingModel] = None
) -> SimilaritySearchEngine:
    """
    Convenience function to create search engine.

    Args:
        storage: Optional storage backend (creates default if None)
        embedding_model: Optional embedding model (uses SimpleHashEmbedding if None)

    Returns:
        SimilaritySearchEngine instance
    """
    if storage is None:
        storage = PrecedentStorage()

    if embedding_model is None:
        embedding_model = SimpleHashEmbedding()

    return SimilaritySearchEngine(storage, embedding_model)
