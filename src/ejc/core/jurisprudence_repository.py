import os
import json
import hashlib
from typing import Dict, List, Any, Optional

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..utils.filepaths import ensure_dir
from ..utils.logging import get_logger
from ..constants import PRECEDENT_SIMILARITY_THRESHOLD


class JurisprudenceRepository:
    """
    Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF)

    Jurisprudence Repository implementing RBJA precedent requirements.
    Stores and retrieves precedent bundles with semantic similarity.
    Supports both exact hash matching and embedding-based semantic retrieval.
    """

    def __init__(self, data_path: str = "./eleanor_data", use_embeddings: bool = True) -> None:
        self.logger = get_logger("EJC.JurisprudenceRepository")
        self.data_path = data_path
        ensure_dir(data_path)

        self.store_path: str = os.path.join(data_path, "precedent_store.json")
        self.embeddings_path: str = os.path.join(data_path, "precedent_embeddings.npy")
        self.use_embeddings: bool = use_embeddings

        # Initialize embedding model with an offline-friendly deterministic encoder
        self.embedder = self._initialize_embedder()
        self.embeddings_cache: List[Any] = []

        if not os.path.exists(self.store_path):
            with open(self.store_path, "w") as f:
                json.dump([], f)

        # Load any existing precedents once and keep an in-memory view for tests
        with open(self.store_path, "r") as f:
            self.precedent_store: List[Dict[str, Any]] = json.load(f)

        if self.use_embeddings and self.embedder:
            self.embeddings_cache = self._load_embeddings()
            if not self.embeddings_cache and self.precedent_store:
                self._rebuild_embeddings_cache(self.precedent_store)

    def _load_embeddings(self) -> List[Any]:
        """Load cached embeddings from disk."""
        if os.path.exists(self.embeddings_path):
            try:
                return np.load(self.embeddings_path).tolist()
            except Exception as e:
                self.logger.warning(f"Failed to load embeddings cache: {e}")
        return []

    def _initialize_embedder(self) -> Optional[Any]:
        """Create an embedder that does not rely on network access."""

        class _HashingEmbedder:
            def __init__(self, text_dim: int = 256, context_dim: int = 128):
                self.text_vectorizer = HashingVectorizer(
                    n_features=text_dim,
                    alternate_sign=False,
                    norm=None,
                    ngram_range=(1, 1),
                    lowercase=True,
                )
                self.context_vectorizer = HashingVectorizer(
                    n_features=context_dim,
                    alternate_sign=False,
                    norm=None,
                    ngram_range=(1, 1),
                    lowercase=True,
                )

            def encode(self, text: str, convert_to_numpy: bool = True):
                if text is None:
                    text = ""

                text_part = text
                context_part = ""
                if "CONTEXT:" in text:
                    text_part, context_part = text.split("CONTEXT:", 1)
                elif "context" in text:
                    context_part = text

                text_vec = self.text_vectorizer.transform([text_part]).toarray()[0]
                context_vec = self.context_vectorizer.transform([context_part]).toarray()[0] * 3

                combined = np.concatenate([text_vec, context_vec])
                norm = np.linalg.norm(combined)
                return combined / norm if norm else combined

        if not self.use_embeddings:
            return None

        # Always start with deterministic offline embedder. If a real model is
        # explicitly requested, gate the potentially heavy import behind an env flag.
        embedder: Any = _HashingEmbedder()

        if os.environ.get("EJC_ENABLE_SENTENCE_TRANSFORMER") == "1":
            try:
                from sentence_transformers import SentenceTransformer

                self.logger.info("Loading sentence transformer model (local only)...")
                embedder = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
                self.logger.info("Semantic similarity enabled")
            except Exception as e:
                self.logger.warning(
                    f"Falling back to hashing embedder due to model load failure: {e}"
                )

        return embedder

    def _save_embeddings(self) -> None:
        """Save embeddings cache to disk."""
        try:
            np.save(self.embeddings_path, np.array(self.embeddings_cache))
        except Exception as e:
            self.logger.error(f"Failed to save embeddings cache: {e}")

    def _hash_case(self, case: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of case for exact matching."""
        return hashlib.sha256(
            json.dumps(case, sort_keys=True).encode()
        ).hexdigest()

    def _embed_case(self, case: Dict[str, Any]) -> Optional[Any]:
        """Generate embedding vector for semantic similarity."""
        if not self.use_embeddings or not self.embedder:
            return None

        try:
            # Create a text representation of the case
            text = case.get('text', '')
            if 'context' in case:
                text += f" CONTEXT: {json.dumps(case['context'], sort_keys=True)}"

            # Generate embedding
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None

    def lookup(
        self,
        case: Dict[str, Any],
        similarity_threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return precedents similar to the given case.

        Args:
            case: The case dictionary to find precedents for
            similarity_threshold: Minimum cosine similarity (0-1) for semantic matches
            max_results: Maximum number of results to return

        Returns:
            List of precedent bundles, sorted by similarity (most similar first)
        """
        database = self.precedent_store

        if self.use_embeddings and not self.embeddings_cache and database:
            self._rebuild_embeddings_cache(database)

        if len(database) == 0:
            return []

        # First, try exact hash matching (fastest)
        target_hash = self._hash_case(case)
        exact_matches = [p for p in database if p.get("case_hash") == target_hash]

        if exact_matches:
            self.logger.info(f"Found {len(exact_matches)} exact hash matches")
            scored = []
            for match in exact_matches[:max_results]:
                enriched = match.copy()
                enriched["similarity_score"] = 1.0
                scored.append(enriched)
            return scored

        # If no exact matches and embeddings enabled, use semantic similarity
        if self.use_embeddings and self.embedder:
            return self._semantic_lookup(case, database, similarity_threshold, max_results)

        # No matches
        return []

    def _semantic_lookup(
        self,
        case: Dict[str, Any],
        database: List[Dict[str, Any]],
        threshold: float,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Find similar precedents using semantic similarity.

        Args:
            case: The case to match
            database: List of all precedents
            threshold: Minimum similarity threshold
            max_results: Maximum results to return

        Returns:
            List of similar precedents with similarity scores
        """
        # Generate embedding for query case
        query_embedding = self._embed_case(case)
        if query_embedding is None:
            return []

        query_tokens = self._tokenize_case(case)

        # Ensure embeddings cache is synchronized with database
        if len(self.embeddings_cache) != len(database):
            self.logger.info("Rebuilding embeddings cache...")
            self._rebuild_embeddings_cache(database)

        if len(self.embeddings_cache) == 0:
            return []

        # Calculate cosine similarities
        try:
            similarities = cosine_similarity(
                [query_embedding],
                self.embeddings_cache
            )[0]

            # Find precedents above threshold
            similar_indices = np.where(similarities >= threshold)[0]

            if len(similar_indices) == 0:
                self.logger.info("No semantically similar precedents found")
                return []

            # Sort by similarity (descending)
            sorted_indices = similar_indices[np.argsort(-similarities[similar_indices])]

            # Build result list with similarity scores
            results = []
            for idx in sorted_indices[:max_results]:
                precedent = database[idx].copy()
                overlap = self._token_overlap(query_tokens, self._tokenize_case(precedent.get('input', {})))
                adjusted_similarity = min(0.99, float(similarities[idx]) + 0.3 * overlap)
                precedent['similarity_score'] = adjusted_similarity
                results.append(precedent)

            self.logger.info(f"Found {len(results)} semantically similar precedents")
            return results

        except Exception as e:
            self.logger.error(f"Semantic lookup failed: {e}")
            return []

    def _rebuild_embeddings_cache(self, database: List[Dict[str, Any]]) -> None:
        """Rebuild the entire embeddings cache from database."""
        self.embeddings_cache = []

        for precedent in database:
            case = precedent.get('input', {})
            embedding = self._embed_case(case)

            if embedding is not None:
                self.embeddings_cache.append(embedding)
            else:
                # Add zero vector as placeholder
                self.embeddings_cache.append(np.zeros(384))  # MiniLM dimension

        self._save_embeddings()

    @staticmethod
    def _tokenize_case(case: Dict[str, Any]) -> set:
        text = case.get('text', '')
        if 'context' in case:
            text += f" {json.dumps(case['context'], sort_keys=True)}"
        return set(text.lower().split())

    @staticmethod
    def _token_overlap(query_tokens: set, precedent_tokens: set) -> float:
        if not query_tokens or not precedent_tokens:
            return 0.0
        intersection = len(query_tokens & precedent_tokens)
        union = len(query_tokens | precedent_tokens)
        return intersection / union if union else 0.0

    def store_precedent(self, bundle: Dict[str, Any]) -> None:
        """
        Store a new precedent with its hash and embedding.

        Args:
            bundle: The decision bundle to store as precedent
        """
        database = self.precedent_store

        # Add hash
        bundle["case_hash"] = self._hash_case(bundle["input"])

        # Generate and cache embedding
        if self.use_embeddings and self.embedder:
            embedding = self._embed_case(bundle["input"])
            if embedding is not None:
                self.embeddings_cache.append(embedding)
                self._save_embeddings()

        database.append(bundle)

        with open(self.store_path, "w") as f:
            json.dump(database, f, indent=2)

        self.logger.debug(f"Stored precedent with hash {bundle['case_hash'][:8]}...")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the precedent database."""
        with open(self.store_path, "r") as f:
            database = json.load(f)

        return {
            "total_precedents": len(database),
            "embeddings_cached": len(self.embeddings_cache),
            "embeddings_enabled": self.use_embeddings,
            "storage_path": self.store_path
        }
