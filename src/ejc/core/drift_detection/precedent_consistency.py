"""
Precedent consistency checker - detects similar cases with different outcomes.

Identifies when the system makes inconsistent decisions for similar scenarios,
which could indicate drift or degraded reasoning.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import hashlib


@dataclass
class InconsistencyReport:
    """Report of precedent inconsistency."""

    case_1_id: str
    case_2_id: str
    similarity_score: float  # 0.0 to 1.0
    verdict_1: str
    verdict_2: str
    confidence_1: float
    confidence_2: float
    timestamp_1: str
    timestamp_2: str
    inconsistency_score: float  # Higher = more problematic
    explanation: str


class PrecedentConsistencyChecker:
    """
    Checks for inconsistencies in precedent application.

    Identifies cases where similar inputs produce different outputs,
    which may indicate:
    1. Critic drift
    2. Configuration changes
    3. Genuine edge cases requiring human review
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        inconsistency_threshold: float = 0.7
    ):
        """
        Initialize consistency checker.

        Args:
            similarity_threshold: How similar cases must be to compare (0-1)
            inconsistency_threshold: Threshold for flagging inconsistency
        """
        self.similarity_threshold = similarity_threshold
        self.inconsistency_threshold = inconsistency_threshold

    def check_consistency(
        self,
        decisions: List[Dict],
        max_pairs: int = 100
    ) -> List[InconsistencyReport]:
        """
        Check for inconsistent decisions among similar cases.

        Args:
            decisions: List of decision dicts
            max_pairs: Maximum pairs to check (for performance)

        Returns:
            List of inconsistency reports
        """
        if len(decisions) < 2:
            return []

        inconsistencies = []

        # Compare pairs of decisions
        compared = 0
        for i in range(len(decisions)):
            if compared >= max_pairs:
                break

            for j in range(i + 1, len(decisions)):
                if compared >= max_pairs:
                    break

                dec1 = decisions[i]
                dec2 = decisions[j]

                # Calculate similarity
                similarity = self._calculate_similarity(dec1, dec2)

                if similarity >= self.similarity_threshold:
                    # Check for inconsistency
                    inconsistency = self._check_pair_inconsistency(dec1, dec2, similarity)

                    if inconsistency and inconsistency.inconsistency_score >= self.inconsistency_threshold:
                        inconsistencies.append(inconsistency)

                compared += 1

        return inconsistencies

    def _calculate_similarity(self, dec1: Dict, dec2: Dict) -> float:
        """
        Calculate similarity between two decisions.

        Uses simple hash-based similarity for now.
        Could be enhanced with vector embeddings.

        Args:
            dec1, dec2: Decision dicts

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Extract input data
        input1 = dec1.get("input_data", {})
        input2 = dec2.get("input_data", {})

        # Simple approach: compare prompts
        prompt1 = input1.get("prompt", "")
        prompt2 = input2.get("prompt", "")

        if not prompt1 or not prompt2:
            return 0.0

        # Normalize
        prompt1_norm = prompt1.lower().strip()
        prompt2_norm = prompt2.lower().strip()

        # Exact match
        if prompt1_norm == prompt2_norm:
            return 1.0

        # Word overlap similarity (Jaccard)
        words1 = set(prompt1_norm.split())
        words2 = set(prompt2_norm.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _check_pair_inconsistency(
        self,
        dec1: Dict,
        dec2: Dict,
        similarity: float
    ) -> Optional[InconsistencyReport]:
        """
        Check if a pair of similar decisions is inconsistent.

        Args:
            dec1, dec2: Decision dicts
            similarity: Similarity score

        Returns:
            InconsistencyReport or None
        """
        # Extract verdicts
        verdict1 = dec1.get("governance_outcome", {}).get("verdict", "UNKNOWN")
        verdict2 = dec2.get("governance_outcome", {}).get("verdict", "UNKNOWN")

        # If verdicts match, no inconsistency
        if verdict1 == verdict2:
            return None

        # Extract confidence (from aggregation)
        agg1 = dec1.get("aggregation", {})
        agg2 = dec2.get("aggregation", {})

        confidence1 = agg1.get("confidence", 0.5)
        confidence2 = agg2.get("confidence", 0.5)

        # Calculate inconsistency score
        # Higher when: high similarity, different verdicts, high confidence
        verdict_distance = 1.0 if verdict1 != verdict2 else 0.0
        confidence_factor = (confidence1 + confidence2) / 2.0

        inconsistency_score = similarity * verdict_distance * confidence_factor

        # Generate explanation
        explanation = (
            f"Similar cases ({similarity:.0%} similar) received different verdicts: "
            f"{verdict1} vs {verdict2}"
        )

        if confidence1 > 0.8 and confidence2 > 0.8:
            explanation += " (both high confidence)"

        return InconsistencyReport(
            case_1_id=dec1.get("decision_id", "unknown"),
            case_2_id=dec2.get("decision_id", "unknown"),
            similarity_score=similarity,
            verdict_1=verdict1,
            verdict_2=verdict2,
            confidence_1=confidence1,
            confidence_2=confidence2,
            timestamp_1=dec1.get("timestamp", ""),
            timestamp_2=dec2.get("timestamp", ""),
            inconsistency_score=inconsistency_score,
            explanation=explanation,
        )

    def generate_consistency_report(
        self,
        decisions: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive precedent consistency report.

        Args:
            decisions: List of decision dicts

        Returns:
            Report dict with metrics and inconsistencies
        """
        inconsistencies = self.check_consistency(decisions)

        # Group by severity
        critical = [i for i in inconsistencies if i.inconsistency_score > 0.9]
        high = [i for i in inconsistencies if 0.8 <= i.inconsistency_score <= 0.9]
        medium = [i for i in inconsistencies if 0.7 <= i.inconsistency_score < 0.8]

        # Calculate verdict consistency rates
        verdict_pairs = {}
        for inc in inconsistencies:
            pair = tuple(sorted([inc.verdict_1, inc.verdict_2]))
            verdict_pairs[pair] = verdict_pairs.get(pair, 0) + 1

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_decisions_analyzed": len(decisions),
                "inconsistencies_found": len(inconsistencies),
                "critical_inconsistencies": len(critical),
                "high_inconsistencies": len(high),
                "medium_inconsistencies": len(medium),
            },
            "verdict_pairs": verdict_pairs,
            "inconsistencies": [
                {
                    "case_1_id": inc.case_1_id,
                    "case_2_id": inc.case_2_id,
                    "similarity": inc.similarity_score,
                    "verdicts": f"{inc.verdict_1} vs {inc.verdict_2}",
                    "inconsistency_score": inc.inconsistency_score,
                    "explanation": inc.explanation,
                }
                for inc in sorted(inconsistencies, key=lambda x: x.inconsistency_score, reverse=True)[:10]
            ],
            "recommendations": self._generate_recommendations(inconsistencies),
        }

    def _generate_recommendations(
        self,
        inconsistencies: List[InconsistencyReport]
    ) -> List[str]:
        """Generate recommendations based on inconsistencies."""
        recommendations = []

        if not inconsistencies:
            recommendations.append("✅ No significant precedent inconsistencies detected")
            return recommendations

        critical_count = sum(1 for i in inconsistencies if i.inconsistency_score > 0.9)

        if critical_count > 0:
            recommendations.append(
                f"🚨 {critical_count} critical inconsistencies require immediate review"
            )

        if len(inconsistencies) > 10:
            recommendations.append(
                "⚠️ High number of inconsistencies - consider recalibrating critics"
            )

        # Check for patterns
        verdict_patterns = {}
        for inc in inconsistencies:
            pattern = f"{inc.verdict_1}↔{inc.verdict_2}"
            verdict_patterns[pattern] = verdict_patterns.get(pattern, 0) + 1

        most_common = max(verdict_patterns.items(), key=lambda x: x[1]) if verdict_patterns else None
        if most_common and most_common[1] >= 3:
            recommendations.append(
                f"📊 Pattern detected: {most_common[0]} inconsistency appears {most_common[1]} times"
            )

        return recommendations
