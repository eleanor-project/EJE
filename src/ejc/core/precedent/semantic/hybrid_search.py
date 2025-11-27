"""
Hybrid precedent search combining exact hash matching and semantic similarity.

Provides best of both worlds: fast exact matches prioritized, comprehensive
semantic search for similar cases.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .vector_store import VectorPrecedentStore, SimilarPrecedent

logger = logging.getLogger(__name__)


@dataclass
class SearchWeights:
    """Weights for combining exact and semantic matches."""

    exact_weight: float = 2.0  # Exact matches get 2x priority
    semantic_weight: float = 1.0
    decay_factor: float = 0.95  # Rank decay for lower positions


class HybridPrecedentSearch:
    """
    Hybrid search combining exact hash matching and semantic similarity.

    Strategy:
    1. Check for exact hash matches (fast, deterministic)
    2. Perform semantic search (comprehensive, approximate)
    3. Merge and rank results with weighted scoring
    4. Deduplicate and return top-k
    """

    def __init__(
        self,
        hash_store: Any,  # JurisprudenceRepository with hash-based lookup
        vector_store: VectorPrecedentStore,
        weights: Optional[SearchWeights] = None
    ):
        """
        Initialize hybrid search.

        Args:
            hash_store: Hash-based precedent store (exact matching)
            vector_store: Vector-based precedent store (semantic matching)
            weights: Search weights for combining results
        """
        self.hash_store = hash_store
        self.vector_store = vector_store
        self.weights = weights or SearchWeights()

    def search(
        self,
        case: Dict,
        top_k: int = 10,
        min_similarity: float = 0.7,
        exact_only: bool = False,
        semantic_only: bool = False
    ) -> List[SimilarPrecedent]:
        """
        Search for precedents using hybrid approach.

        Args:
            case: Case dictionary with 'prompt' and 'context'
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold for semantic matches
            exact_only: Only return exact hash matches
            semantic_only: Only return semantic matches (skip exact)

        Returns:
            List of similar precedents, ranked by combined score
        """
        exact_matches = []
        semantic_matches = []

        # 1. Exact hash matches (if not semantic_only)
        if not semantic_only:
            exact_matches = self._search_exact(case)
            logger.debug(f"Found {len(exact_matches)} exact matches")

        # If exact_only requested, return early
        if exact_only:
            return exact_matches[:top_k]

        # 2. Semantic matches (if not exact_only)
        if not exact_only:
            # Request more semantic results to account for deduplication
            semantic_k = top_k * 3
            semantic_matches = self.vector_store.search_similar(
                case,
                k=semantic_k,
                min_similarity=min_similarity
            )
            logger.debug(f"Found {len(semantic_matches)} semantic matches")

        # 3. Merge and rank
        merged = self._merge_and_rank(
            exact_matches,
            semantic_matches,
            top_k
        )

        return merged

    def _search_exact(self, case: Dict) -> List[SimilarPrecedent]:
        """
        Search for exact hash matches.

        Args:
            case: Case dictionary

        Returns:
            List of exact matches with similarity=1.0
        """
        try:
            # Use hash store's lookup method
            matches = self.hash_store.lookup(case)

            # Convert to SimilarPrecedent format
            similar = []
            for match in matches:
                similar.append(SimilarPrecedent(
                    precedent_id=match.get("id", match.get("hash", "unknown")),
                    precedent=match,
                    similarity_score=1.0,  # Exact match
                    match_type="exact",
                    metadata={"hash_match": True}
                ))

            return similar
        except Exception as e:
            logger.error(f"Exact search failed: {e}")
            return []

    def _merge_and_rank(
        self,
        exact_matches: List[SimilarPrecedent],
        semantic_matches: List[SimilarPrecedent],
        top_k: int
    ) -> List[SimilarPrecedent]:
        """
        Merge exact and semantic matches with weighted ranking.

        Args:
            exact_matches: List of exact hash matches
            semantic_matches: List of semantic similarity matches
            top_k: Number of results to return

        Returns:
            Merged and ranked list of precedents
        """
        # Build precedent ID set for deduplication
        seen_ids = set()
        merged = []

        # Add exact matches first (highest priority)
        for i, match in enumerate(exact_matches):
            if match.precedent_id not in seen_ids:
                # Apply exact weight and position decay
                position_decay = self.weights.decay_factor ** i
                score = match.similarity_score * self.weights.exact_weight * position_decay

                # Update match with weighted score
                weighted_match = SimilarPrecedent(
                    precedent_id=match.precedent_id,
                    precedent=match.precedent,
                    similarity_score=score,
                    match_type=match.match_type,
                    metadata={
                        **(match.metadata or {}),
                        "original_score": match.similarity_score,
                        "weighted_score": score,
                        "rank_source": "exact"
                    }
                )

                merged.append(weighted_match)
                seen_ids.add(match.precedent_id)

        # Add semantic matches (filter out duplicates)
        for i, match in enumerate(semantic_matches):
            if match.precedent_id not in seen_ids:
                # Apply semantic weight and position decay
                position_decay = self.weights.decay_factor ** i
                score = match.similarity_score * self.weights.semantic_weight * position_decay

                # Update match with weighted score
                weighted_match = SimilarPrecedent(
                    precedent_id=match.precedent_id,
                    precedent=match.precedent,
                    similarity_score=score,
                    match_type=match.match_type,
                    metadata={
                        **(match.metadata or {}),
                        "original_score": match.similarity_score,
                        "weighted_score": score,
                        "rank_source": "semantic"
                    }
                )

                merged.append(weighted_match)
                seen_ids.add(match.precedent_id)

        # Sort by weighted score (descending)
        merged.sort(key=lambda x: x.similarity_score, reverse=True)

        # Return top-k
        return merged[:top_k]

    def search_similar_to_precedent(
        self,
        precedent_id: str,
        top_k: int = 10,
        min_similarity: float = 0.75
    ) -> List[SimilarPrecedent]:
        """
        Find precedents similar to an existing precedent.

        Args:
            precedent_id: ID of reference precedent
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar precedents
        """
        # Get reference precedent
        precedent = self.vector_store.get_by_id(precedent_id)

        if not precedent:
            logger.warning(f"Precedent {precedent_id} not found")
            return []

        # Extract case from precedent
        case = precedent.get("input_data", {})

        # Search (exclude the reference precedent itself)
        results = self.search(
            case,
            top_k=top_k + 1,  # Get extra to account for self-match
            min_similarity=min_similarity,
            semantic_only=True  # Use semantic for "similar to" queries
        )

        # Filter out the reference precedent
        filtered = [r for r in results if r.precedent_id != precedent_id]

        return filtered[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about hybrid search."""
        return {
            "hash_store_type": type(self.hash_store).__name__,
            "vector_store_stats": self.vector_store.get_stats(),
            "weights": {
                "exact_weight": self.weights.exact_weight,
                "semantic_weight": self.weights.semantic_weight,
                "decay_factor": self.weights.decay_factor
            }
        }
