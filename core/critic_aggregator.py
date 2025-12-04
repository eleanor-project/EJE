"""
Critic Output Aggregator with Weighting Support

Aggregates multiple critic verdicts into a final decision using configurable
weights and conflict detection.

Task 2.1: Add Critic Weighting
Task 2.2: Implement Conflict Detection (partial)
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
import logging

logger = logging.getLogger("ejc.core.critic_aggregator")


@dataclass
class AggregationResult:
    """Result of critic aggregation."""

    final_verdict: str  # ALLOW, DENY, ESCALATE
    confidence: float  # 0.0 to 1.0
    weighted_scores: Dict[str, float]  # Verdict → weighted score
    contributing_critics: List[str]  # Critic names that contributed
    total_weight: float  # Sum of all critic weights
    conflicts_detected: List[Dict[str, Any]]  # List of detected conflicts


@dataclass
class CriticWeight:
    """Configuration for critic weighting."""

    critic_name: str
    weight: float  # Multiplier for this critic's influence (default: 1.0)
    enabled: bool = True  # Whether this critic is active


class CriticAggregator:
    """
    Aggregates multiple critic outputs into a final decision.

    Supports weighted voting where critics can have different levels of
    influence on the final verdict. Detects conflicts between critics.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize Critic Aggregator.

        Args:
            weights: Optional dict mapping critic_name → weight
                    Default weight is 1.0 if not specified
        """
        self.weights = weights or {}
        self.default_weight = 1.0

    def aggregate(
        self,
        evidence_bundles: List[Dict[str, Any]],
        escalate_on_conflict: bool = True
    ) -> AggregationResult:
        """
        Aggregate multiple evidence bundles into a final verdict.

        Args:
            evidence_bundles: List of evidence bundle dicts from critics
            escalate_on_conflict: Whether to escalate when critics conflict

        Returns:
            AggregationResult with final verdict and metadata

        Raises:
            ValueError: If no valid bundles provided
        """
        if not evidence_bundles:
            raise ValueError("Cannot aggregate empty list of evidence bundles")

        # Extract critic outputs with weights
        weighted_verdicts = []

        for bundle in evidence_bundles:
            critic_output = bundle.get("critic_output", {})
            critic_name = critic_output.get("critic_name")
            verdict = critic_output.get("verdict")
            confidence = critic_output.get("confidence", 0.5)

            if not critic_name or not verdict:
                logger.warning(f"Skipping bundle with missing critic_name or verdict")
                continue

            # Get weight for this critic
            weight = self.weights.get(critic_name, self.default_weight)

            weighted_verdicts.append({
                "critic_name": critic_name,
                "verdict": verdict,
                "confidence": confidence,
                "weight": weight
            })

        if not weighted_verdicts:
            raise ValueError("No valid critic outputs to aggregate")

        # Calculate weighted scores for each verdict
        verdict_scores = self._calculate_weighted_scores(weighted_verdicts)

        # Detect conflicts
        conflicts = self._detect_conflicts(weighted_verdicts)

        # Determine final verdict
        final_verdict, final_confidence = self._determine_final_verdict(
            verdict_scores,
            conflicts,
            escalate_on_conflict
        )

        # Build result
        total_weight = sum(v["weight"] for v in weighted_verdicts)
        contributing_critics = [v["critic_name"] for v in weighted_verdicts]

        return AggregationResult(
            final_verdict=final_verdict,
            confidence=final_confidence,
            weighted_scores=verdict_scores,
            contributing_critics=contributing_critics,
            total_weight=total_weight,
            conflicts_detected=conflicts
        )

    def _calculate_weighted_scores(
        self,
        weighted_verdicts: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate weighted scores for each verdict.

        Args:
            weighted_verdicts: List of verdict dicts with weights

        Returns:
            Dict mapping verdict → weighted score
        """
        scores: Dict[str, float] = {}

        for item in weighted_verdicts:
            verdict = item["verdict"]
            confidence = item["confidence"]
            weight = item["weight"]

            # Score = confidence × weight
            score = confidence * weight

            scores[verdict] = scores.get(verdict, 0.0) + score

        return scores

    def _detect_conflicts(
        self,
        weighted_verdicts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between critic verdicts.

        A conflict is when:
        - Critics give opposing verdicts (ALLOW vs DENY)
        - High confidence critics disagree
        - Weighted scores are very close

        Args:
            weighted_verdicts: List of verdict dicts

        Returns:
            List of conflict dicts
        """
        conflicts = []

        # Check for direct opposites (ALLOW vs DENY)
        verdicts = [v["verdict"] for v in weighted_verdicts]
        has_allow = "ALLOW" in verdicts
        has_deny = "DENY" in verdicts

        if has_allow and has_deny:
            # Find critics on each side
            allow_critics = [
                v["critic_name"] for v in weighted_verdicts
                if v["verdict"] == "ALLOW"
            ]
            deny_critics = [
                v["critic_name"] for v in weighted_verdicts
                if v["verdict"] == "DENY"
            ]

            conflicts.append({
                "type": "opposing_verdicts",
                "description": "Critics disagree on ALLOW vs DENY",
                "allow_critics": allow_critics,
                "deny_critics": deny_critics,
                "severity": "high"
            })

        # Check for high-confidence disagreements
        high_conf_verdicts = [
            v for v in weighted_verdicts
            if v["confidence"] >= 0.8
        ]

        if len(high_conf_verdicts) >= 2:
            unique_verdicts = set(v["verdict"] for v in high_conf_verdicts)
            if len(unique_verdicts) > 1:
                conflicts.append({
                    "type": "high_confidence_disagreement",
                    "description": "High-confidence critics disagree",
                    "critics": [v["critic_name"] for v in high_conf_verdicts],
                    "verdicts": list(unique_verdicts),
                    "severity": "medium"
                })

        return conflicts

    def _determine_final_verdict(
        self,
        verdict_scores: Dict[str, float],
        conflicts: List[Dict[str, Any]],
        escalate_on_conflict: bool
    ) -> Tuple[str, float]:
        """
        Determine final verdict from weighted scores and conflicts.

        Args:
            verdict_scores: Weighted scores per verdict
            conflicts: Detected conflicts
            escalate_on_conflict: Whether to escalate on conflicts

        Returns:
            (final_verdict, confidence)
        """
        # If conflicts and escalation enabled, escalate
        if conflicts and escalate_on_conflict:
            # Check for high severity conflicts
            high_severity = any(c.get("severity") == "high" for c in conflicts)
            if high_severity:
                logger.info("Escalating due to high-severity conflict")
                return "ESCALATE", 0.5

        # If any critic explicitly escalated, respect that
        if "ESCALATE" in verdict_scores and verdict_scores["ESCALATE"] > 0:
            # Calculate confidence based on escalation score
            total_score = sum(verdict_scores.values())
            confidence = verdict_scores["ESCALATE"] / total_score if total_score > 0 else 0.5
            return "ESCALATE", confidence

        # Otherwise, pick verdict with highest weighted score
        if not verdict_scores:
            return "ABSTAIN", 0.0

        # Get verdict with max score
        max_verdict = max(verdict_scores.items(), key=lambda x: x[1])
        verdict, score = max_verdict

        # Calculate confidence: score / total_score
        total_score = sum(verdict_scores.values())
        confidence = score / total_score if total_score > 0 else 0.0

        # If scores are very close, consider lowering confidence
        scores_list = sorted(verdict_scores.values(), reverse=True)
        if len(scores_list) >= 2:
            top_score = scores_list[0]
            second_score = scores_list[1]
            if top_score > 0 and (second_score / top_score) > 0.8:
                # Scores are within 80% of each other - lower confidence
                confidence *= 0.8

        return verdict, confidence

    def set_weight(self, critic_name: str, weight: float):
        """
        Set weight for a specific critic.

        Args:
            critic_name: Name of critic
            weight: Weight value (typically 0.0 to 2.0)
        """
        if weight < 0:
            raise ValueError(f"Weight must be non-negative, got {weight}")

        self.weights[critic_name] = weight
        logger.info(f"Set weight for {critic_name} to {weight}")

    def get_weight(self, critic_name: str) -> float:
        """
        Get weight for a specific critic.

        Args:
            critic_name: Name of critic

        Returns:
            Weight value (default: 1.0)
        """
        return self.weights.get(critic_name, self.default_weight)

    def remove_weight(self, critic_name: str):
        """
        Remove custom weight for critic (reverts to default).

        Args:
            critic_name: Name of critic
        """
        if critic_name in self.weights:
            del self.weights[critic_name]
            logger.info(f"Removed custom weight for {critic_name}")

    def get_all_weights(self) -> Dict[str, float]:
        """
        Get all configured weights.

        Returns:
            Dict of critic_name → weight
        """
        return self.weights.copy()

    def aggregate_with_justification(
        self,
        evidence_bundles: List[Dict[str, Any]],
        escalate_on_conflict: bool = True
    ) -> Tuple[AggregationResult, str]:
        """
        Aggregate with synthesized justification.

        Args:
            evidence_bundles: List of evidence bundles
            escalate_on_conflict: Whether to escalate on conflict

        Returns:
            (AggregationResult, synthesized_justification)
        """
        result = self.aggregate(evidence_bundles, escalate_on_conflict)

        # Synthesize justification
        justification_parts = []

        # Verdict summary
        justification_parts.append(
            f"Final verdict: {result.final_verdict} "
            f"(confidence: {result.confidence:.2f})"
        )

        # Weighted scores
        score_summary = ", ".join(
            f"{verdict}: {score:.2f}"
            for verdict, score in sorted(
                result.weighted_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
        )
        justification_parts.append(f"Weighted scores: {score_summary}")

        # Contributing critics
        justification_parts.append(
            f"Based on {len(result.contributing_critics)} critics: "
            f"{', '.join(result.contributing_critics)}"
        )

        # Conflicts
        if result.conflicts_detected:
            conflict_summary = ", ".join(
                c["description"] for c in result.conflicts_detected
            )
            justification_parts.append(f"Conflicts detected: {conflict_summary}")

        justification = ". ".join(justification_parts) + "."

        return result, justification


def aggregate_critics(
    evidence_bundles: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    escalate_on_conflict: bool = True
) -> AggregationResult:
    """
    Convenience function for aggregating critics.

    Args:
        evidence_bundles: List of evidence bundles
        weights: Optional weights dict
        escalate_on_conflict: Whether to escalate on conflict

    Returns:
        AggregationResult
    """
    aggregator = CriticAggregator(weights)
    return aggregator.aggregate(evidence_bundles, escalate_on_conflict)
