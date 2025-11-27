"""
Vector-based precedent storage and semantic retrieval.

Uses sentence transformers for embedding generation and FAISS for efficient
nearest-neighbor search. Supports persistence and incremental updates.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

# Conditional imports for optional dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, vector search disabled")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not available, using fallback similarity search")


@dataclass
class SimilarPrecedent:
    """A precedent with similarity score."""

    precedent_id: str
    precedent: Dict[str, Any]
    similarity_score: float
    match_type: str  # "exact", "semantic", "hybrid"
    metadata: Optional[Dict[str, Any]] = None


class VectorPrecedentStore:
    """
    Vector-based precedent storage using embeddings for semantic search.

    Features:
    - Sentence transformer embeddings (384-dim)
    - FAISS index for fast nearest-neighbor search
    - Incremental index updates
    - Persistence to disk
    - Fallback to cosine similarity if FAISS unavailable
    """

    def __init__(
        self,
        data_path: str,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
        use_gpu: bool = False
    ):
        """
        Initialize vector precedent store.

        Args:
            data_path: Directory for storing precedents and index
            embedding_model: SentenceTransformer model name
            embedding_dim: Embedding dimension (must match model)
            use_gpu: Use GPU for embeddings if available
        """
        self.data_path = data_path
        self.embedding_model_name = embedding_model
        self.embedding_dim = embedding_dim
        self.use_gpu = use_gpu

        # Storage
        self.precedents: List[Dict] = []
        self.precedent_index: Dict[str, int] = {}  # precedent_id -> index
        self.embeddings: Optional[np.ndarray] = None

        # Components
        self.embedder = None
        self.index = None

        # Initialize if dependencies available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self._initialize_embedder()

        if FAISS_AVAILABLE:
            self._initialize_index()

        # Load existing data
        self._load_if_exists()

    def _initialize_embedder(self):
        """Initialize sentence transformer model."""
        try:
            device = "cuda" if self.use_gpu else "cpu"
            self.embedder = SentenceTransformer(
                self.embedding_model_name,
                device=device
            )
            logger.info(f"Initialized embedder: {self.embedding_model_name} on {device}")
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            self.embedder = None

    def _initialize_index(self):
        """Initialize FAISS index for vector search."""
        try:
            # Use inner product for cosine similarity (normalize vectors)
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info(f"Initialized FAISS index (dimension={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}")
            self.index = None

    def _generate_embedding(self, precedent: Dict) -> Optional[np.ndarray]:
        """
        Generate embedding for a precedent.

        Args:
            precedent: Precedent dictionary with 'input_data' field

        Returns:
            Normalized embedding vector, or None if not available
        """
        if not self.embedder:
            return None

        try:
            # Extract text for embedding
            input_data = precedent.get("input_data", {})
            prompt = input_data.get("prompt", "")
            context_str = json.dumps(input_data.get("context", {}))

            # Combine prompt and context for richer representation
            text = f"{prompt} {context_str}"

            # Generate embedding
            embedding = self.embedder.encode(text, convert_to_numpy=True)

            # Normalize for cosine similarity via inner product
            embedding = embedding / np.linalg.norm(embedding)

            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def add_precedent(self, precedent: Dict) -> str:
        """
        Add precedent with vector embedding.

        Args:
            precedent: Precedent dictionary

        Returns:
            Precedent ID
        """
        precedent_id = precedent.get("id", f"prec_{len(self.precedents)}")

        # Check if already exists
        if precedent_id in self.precedent_index:
            logger.warning(f"Precedent {precedent_id} already exists, skipping")
            return precedent_id

        # Generate embedding
        embedding = self._generate_embedding(precedent)

        # Add to storage
        idx = len(self.precedents)
        self.precedents.append(precedent)
        self.precedent_index[precedent_id] = idx

        # Add to index
        if embedding is not None:
            if self.embeddings is None:
                self.embeddings = np.array([embedding], dtype=np.float32)
            else:
                self.embeddings = np.vstack([self.embeddings, embedding])

            if self.index is not None:
                self.index.add(np.array([embedding], dtype=np.float32))

        logger.debug(f"Added precedent {precedent_id} (total: {len(self.precedents)})")
        return precedent_id

    def add_precedents_batch(self, precedents: List[Dict]) -> List[str]:
        """
        Add multiple precedents efficiently.

        Args:
            precedents: List of precedent dictionaries

        Returns:
            List of precedent IDs
        """
        ids = []
        embeddings = []

        for prec in precedents:
            prec_id = prec.get("id", f"prec_{len(self.precedents) + len(ids)}")

            if prec_id in self.precedent_index:
                logger.warning(f"Precedent {prec_id} already exists, skipping")
                continue

            # Generate embedding
            embedding = self._generate_embedding(prec)

            # Add to storage
            idx = len(self.precedents) + len(ids)
            self.precedents.append(prec)
            self.precedent_index[prec_id] = idx
            ids.append(prec_id)

            if embedding is not None:
                embeddings.append(embedding)

        # Batch add to index
        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)

            if self.embeddings is None:
                self.embeddings = embeddings_array
            else:
                self.embeddings = np.vstack([self.embeddings, embeddings_array])

            if self.index is not None:
                self.index.add(embeddings_array)

        logger.info(f"Added {len(ids)} precedents (total: {len(self.precedents)})")
        return ids

    def search_similar(
        self,
        case: Dict,
        k: int = 10,
        min_similarity: float = 0.75
    ) -> List[SimilarPrecedent]:
        """
        Search for semantically similar precedents.

        Args:
            case: Case dictionary with 'prompt' and 'context'
            k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of similar precedents with scores
        """
        if not self.precedents:
            return []

        # Generate query embedding
        query_precedent = {"input_data": case}
        query_embedding = self._generate_embedding(query_precedent)

        if query_embedding is None:
            logger.warning("Could not generate query embedding, returning empty results")
            return []

        # Search using FAISS if available
        if self.index is not None and self.index.ntotal > 0:
            return self._search_faiss(query_embedding, k, min_similarity)

        # Fallback to manual cosine similarity
        return self._search_fallback(query_embedding, k, min_similarity)

    def _search_faiss(
        self,
        query_embedding: np.ndarray,
        k: int,
        min_similarity: float
    ) -> List[SimilarPrecedent]:
        """Search using FAISS index."""
        try:
            # Query embedding as 2D array
            query = np.array([query_embedding], dtype=np.float32)

            # Search
            similarities, indices = self.index.search(query, min(k, self.index.ntotal))

            # Build results
            results = []
            for similarity, idx in zip(similarities[0], indices[0]):
                if similarity >= min_similarity and idx < len(self.precedents):
                    precedent = self.precedents[idx]
                    results.append(SimilarPrecedent(
                        precedent_id=precedent.get("id", f"prec_{idx}"),
                        precedent=precedent,
                        similarity_score=float(similarity),
                        match_type="semantic",
                        metadata={"index": int(idx)}
                    ))

            return results
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return self._search_fallback(query_embedding, k, min_similarity)

    def _search_fallback(
        self,
        query_embedding: np.ndarray,
        k: int,
        min_similarity: float
    ) -> List[SimilarPrecedent]:
        """Fallback search using manual cosine similarity."""
        if self.embeddings is None or len(self.embeddings) == 0:
            return []

        try:
            # Compute cosine similarities
            similarities = np.dot(self.embeddings, query_embedding)

            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:k]

            # Build results
            results = []
            for idx in top_indices:
                similarity = similarities[idx]
                if similarity >= min_similarity:
                    precedent = self.precedents[idx]
                    results.append(SimilarPrecedent(
                        precedent_id=precedent.get("id", f"prec_{idx}"),
                        precedent=precedent,
                        similarity_score=float(similarity),
                        match_type="semantic",
                        metadata={"index": int(idx)}
                    ))

            return results
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    def get_by_id(self, precedent_id: str) -> Optional[Dict]:
        """Get precedent by ID."""
        idx = self.precedent_index.get(precedent_id)
        if idx is not None and idx < len(self.precedents):
            return self.precedents[idx]
        return None

    def save(self, force: bool = False):
        """
        Save precedents and index to disk.

        Args:
            force: Force save even if no changes
        """
        if not self.precedents and not force:
            logger.debug("No precedents to save")
            return

        try:
            os.makedirs(self.data_path, exist_ok=True)

            # Save precedents
            precedents_path = os.path.join(self.data_path, "precedents.json")
            with open(precedents_path, 'w') as f:
                json.dump(self.precedents, f, indent=2, default=str)

            # Save embeddings
            if self.embeddings is not None:
                embeddings_path = os.path.join(self.data_path, "embeddings.npy")
                np.save(embeddings_path, self.embeddings)

            # Save FAISS index
            if self.index is not None and FAISS_AVAILABLE:
                index_path = os.path.join(self.data_path, "faiss.index")
                faiss.write_index(self.index, index_path)

            logger.info(f"Saved {len(self.precedents)} precedents to {self.data_path}")
        except Exception as e:
            logger.error(f"Failed to save precedents: {e}")

    def _load_if_exists(self):
        """Load precedents and index from disk if they exist."""
        precedents_path = os.path.join(self.data_path, "precedents.json")

        if not os.path.exists(precedents_path):
            logger.debug(f"No existing precedents found at {precedents_path}")
            return

        try:
            # Load precedents
            with open(precedents_path, 'r') as f:
                self.precedents = json.load(f)

            # Rebuild index
            self.precedent_index = {
                prec.get("id", f"prec_{i}"): i
                for i, prec in enumerate(self.precedents)
            }

            # Load embeddings
            embeddings_path = os.path.join(self.data_path, "embeddings.npy")
            if os.path.exists(embeddings_path):
                self.embeddings = np.load(embeddings_path)

            # Load FAISS index
            index_path = os.path.join(self.data_path, "faiss.index")
            if os.path.exists(index_path) and FAISS_AVAILABLE:
                self.index = faiss.read_index(index_path)

            logger.info(f"Loaded {len(self.precedents)} precedents from {self.data_path}")
        except Exception as e:
            logger.error(f"Failed to load precedents: {e}")
            self.precedents = []
            self.precedent_index = {}
            self.embeddings = None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_precedents": len(self.precedents),
            "has_embeddings": self.embeddings is not None,
            "embedding_dimension": self.embedding_dim,
            "embedder_available": self.embedder is not None,
            "faiss_available": self.index is not None,
            "index_size": self.index.ntotal if self.index else 0,
            "model": self.embedding_model_name,
            "data_path": self.data_path
        }
