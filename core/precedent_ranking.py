"""
Precedent Ranking Function

Task 3.4: Implement Precedent Ranking Function

Ranks precedents based on multiple factors: similarity, recency, confidence,
and decision relevance. Provides stable, deterministic rankings with tunable weights.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import hashlib

from core.similarity_search import SimilarityResult

logger = logging.getLogger("ejc.core.precedent_ranking")


@dataclass
class RankingConfig:
    """Configuration for precedent ranking."""

    similarity_weight: float = 0.6  # Weight for similarity score
    recency_weight: float = 0.3  # Weight for recency score
    confidence_weight: float = 0.1  # Weight for confidence score
    decision_boost: Optional[Dict[str, float]] = None  # Boost for specific decisions
    recency_decay_days: float = 365.0  # Days for recency score to decay to 0


@dataclass
class RankedResult:
    """Ranked precedent result."""

    precedent_id: str
    query: str
    decision: str
    confidence: float
    similarity_score: float
    recency_score: float
    confidence_score: float
    final_score: float
    rank: int
    precedent: Dict[str, Any]


class PrecedentRanker:
    """
    Ranks precedents using multiple factors.

    Combines similarity, recency, and confidence into a final score
    with configurable weights. Ensures stable, deterministic rankings.
    """

    def __init__(self, config: Optional[RankingConfig] = None):
        """
        Initialize ranker.

        Args:
            config: Optional ranking configuration
        """
        self.config = config or RankingConfig()
        self._validate_config()

    def _validate_config(self):
        """Validate ranking configuration."""
        # Check that weights are non-negative
        if self.config.similarity_weight < 0:
            raise ValueError("similarity_weight must be non-negative")
        if self.config.recency_weight < 0:
            raise ValueError("recency_weight must be non-negative")
        if self.config.confidence_weight < 0:
            raise ValueError("confidence_weight must be non-negative")

        # Check that recency decay is positive
        if self.config.recency_decay_days <= 0:
            raise ValueError("recency_decay_days must be positive")

        # Log normalization info
        total_weight = (
            self.config.similarity_weight +
            self.config.recency_weight +
            self.config.confidence_weight
        )

        if total_weight == 0:
            raise ValueError("At least one weight must be non-zero")

        logger.debug(
            f"Ranking weights: similarity={self.config.similarity_weight:.2f}, "
            f"recency={self.config.recency_weight:.2f}, "
            f"confidence={self.config.confidence_weight:.2f} "
            f"(total={total_weight:.2f})"
        )

    def rank(
        self,
        similarity_results: List[SimilarityResult],
        current_time: Optional[datetime] = None
    ) -> List[RankedResult]:
        """
        Rank precedents by combining multiple factors.

        Args:
            similarity_results: Results from similarity search
            current_time: Current time for recency calculation (defaults to now)

        Returns:
            List of RankedResult objects, sorted by final score (descending)
        """
        if not similarity_results:
            return []

        if current_time is None:
            current_time = datetime.utcnow()

        # Calculate scores for each result
        ranked_results = []

        for sim_result in similarity_results:
            # Calculate component scores
            similarity_score = sim_result.similarity_score
            recency_score = self._calculate_recency_score(
                sim_result.precedent,
                current_time
            )
            confidence_score = sim_result.confidence

            # Calculate final score
            final_score = self._calculate_final_score(
                similarity_score,
                recency_score,
                confidence_score,
                sim_result.decision
            )

            ranked_results.append(
                RankedResult(
                    precedent_id=sim_result.precedent_id,
                    query=sim_result.query,
                    decision=sim_result.decision,
                    confidence=sim_result.confidence,
                    similarity_score=similarity_score,
                    recency_score=recency_score,
                    confidence_score=confidence_score,
                    final_score=final_score,
                    rank=0,  # Will be set after sorting
                    precedent=sim_result.precedent
                )
            )

        # Sort by final score (descending), with stable tiebreaker
        ranked_results.sort(
            key=lambda x: (x.final_score, x.precedent_id),
            reverse=True
        )

        # Assign ranks
        for i, result in enumerate(ranked_results, 1):
            result.rank = i

        logger.info(f"Ranked {len(ranked_results)} precedents")

        return ranked_results

    def _calculate_recency_score(
        self,
        precedent: Dict[str, Any],
        current_time: datetime
    ) -> float:
        """
        Calculate recency score (1.0 = most recent, 0.0 = oldest).

        Uses exponential decay: score = exp(-age_days / decay_days)

        Args:
            precedent: Precedent dict
            current_time: Current time

        Returns:
            Recency score (0.0-1.0)
        """
        # Parse precedent timestamp
        timestamp_str = precedent.get("timestamp")
        if not timestamp_str:
            logger.warning(f"Precedent {precedent['precedent_id']} missing timestamp")
            return 0.5  # Default to middle score

        try:
            # Parse ISO 8601 timestamp (make timezone-aware)
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'

            precedent_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Ensure current_time is timezone-aware (UTC)
            if current_time.tzinfo is None:
                from datetime import timezone
                current_time = current_time.replace(tzinfo=timezone.utc)

            # Calculate age in days
            age = current_time - precedent_time
            age_days = age.total_seconds() / 86400.0

            # Exponential decay
            import math
            recency_score = math.exp(-age_days / self.config.recency_decay_days)

            # Clamp to [0, 1]
            return max(0.0, min(1.0, recency_score))

        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return 0.5

    def _calculate_final_score(
        self,
        similarity_score: float,
        recency_score: float,
        confidence_score: float,
        decision: str
    ) -> float:
        """
        Calculate final ranking score.

        Args:
            similarity_score: Similarity score (0.0-1.0)
            recency_score: Recency score (0.0-1.0)
            confidence_score: Confidence score (0.0-1.0)
            decision: Decision type

        Returns:
            Final score
        """
        # Weighted sum
        score = (
            self.config.similarity_weight * similarity_score +
            self.config.recency_weight * recency_score +
            self.config.confidence_weight * confidence_score
        )

        # Apply decision boost if configured
        if self.config.decision_boost and decision in self.config.decision_boost:
            boost = self.config.decision_boost[decision]
            score *= (1.0 + boost)

        return score

    def rerank(
        self,
        ranked_results: List[RankedResult],
        custom_scorer: Callable[[RankedResult], float]
    ) -> List[RankedResult]:
        """
        Re-rank results using a custom scoring function.

        Args:
            ranked_results: Previously ranked results
            custom_scorer: Function that takes RankedResult and returns new score

        Returns:
            Re-ranked results
        """
        # Calculate new scores
        for result in ranked_results:
            result.final_score = custom_scorer(result)

        # Re-sort
        ranked_results.sort(
            key=lambda x: (x.final_score, x.precedent_id),
            reverse=True
        )

        # Reassign ranks
        for i, result in enumerate(ranked_results, 1):
            result.rank = i

        logger.info(f"Re-ranked {len(ranked_results)} precedents")

        return ranked_results

    def get_top_k(
        self,
        ranked_results: List[RankedResult],
        k: int,
        min_score: Optional[float] = None
    ) -> List[RankedResult]:
        """
        Get top-k ranked results.

        Args:
            ranked_results: Ranked results
            k: Number of results to return
            min_score: Optional minimum score threshold

        Returns:
            Top-k results
        """
        # Filter by minimum score if specified
        if min_score is not None:
            ranked_results = [r for r in ranked_results if r.final_score >= min_score]

        # Return top k
        return ranked_results[:k]

    def explain_ranking(self, result: RankedResult) -> str:
        """
        Generate human-readable explanation of ranking.

        Args:
            result: Ranked result

        Returns:
            Explanation string
        """
        parts = [
            f"Rank #{result.rank}: {result.query[:50]}...",
            f"Final Score: {result.final_score:.4f}",
            "",
            "Component Scores:",
            f"  - Similarity: {result.similarity_score:.4f} (weight: {self.config.similarity_weight})",
            f"  - Recency: {result.recency_score:.4f} (weight: {self.config.recency_weight})",
            f"  - Confidence: {result.confidence_score:.4f} (weight: {self.config.confidence_weight})",
            "",
            f"Decision: {result.decision}",
            f"Precedent ID: {result.precedent_id}"
        ]

        # Add decision boost info if applicable
        if self.config.decision_boost and result.decision in self.config.decision_boost:
            boost = self.config.decision_boost[result.decision]
            parts.insert(-2, f"Decision Boost: +{boost * 100:.1f}%")

        return "\n".join(parts)


def rank_precedents(
    similarity_results: List[SimilarityResult],
    similarity_weight: float = 0.6,
    recency_weight: float = 0.3,
    confidence_weight: float = 0.1
) -> List[RankedResult]:
    """
    Convenience function to rank precedents.

    Args:
        similarity_results: Results from similarity search
        similarity_weight: Weight for similarity score
        recency_weight: Weight for recency score
        confidence_weight: Weight for confidence score

    Returns:
        List of RankedResult objects
    """
    config = RankingConfig(
        similarity_weight=similarity_weight,
        recency_weight=recency_weight,
        confidence_weight=confidence_weight
    )

    ranker = PrecedentRanker(config)
    return ranker.rank(similarity_results)
