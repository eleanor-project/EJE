"""
Threshold-Based Policy Rules

Task 4.2: Add Threshold Rules

Common threshold-based rules for policy enforcement:
- Minimum confidence
- Critic agreement
- Conflict tolerance
- Minimum critics
- Verdict consistency
"""

import logging
from typing import Dict, Any, List, Optional

from core.policy.rules import (
    PolicyRule,
    RuleType,
    RuleSeverity,
    RuleEvaluationResult
)

logger = logging.getLogger("ejc.core.policy.threshold_rules")


class MinimumConfidenceRule(PolicyRule):
    """
    Requires final confidence to meet minimum threshold.

    Threshold-based rule that ensures the aggregated confidence score
    is above a configurable minimum.
    """

    def __init__(
        self,
        rule_id: str,
        min_confidence: float,
        severity: RuleSeverity = RuleSeverity.HIGH
    ):
        """
        Initialize rule.

        Args:
            rule_id: Unique rule identifier
            min_confidence: Minimum confidence threshold (0.0-1.0)
            severity: Rule severity level
        """
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be 0.0-1.0, got {min_confidence}")

        super().__init__(
            rule_id=rule_id,
            name="Minimum Confidence Threshold",
            rule_type=RuleType.THRESHOLD,
            severity=severity,
            description=f"Requires final confidence >= {min_confidence:.2f}"
        )
        self.min_confidence = min_confidence

    def evaluate(self, decision_context: Dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate confidence threshold."""
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            logger.warning(f"Rule {self.rule_id}: Missing aggregation_result")
            return self._create_result(False, 0.0, metadata={"error": "Missing aggregation_result"})

        confidence = aggregation_result.confidence

        if confidence >= self.min_confidence:
            logger.info(f"Rule {self.rule_id}: PASS (confidence={confidence:.2f} >= {self.min_confidence:.2f})")
            return self._create_result(
                True,
                1.0,
                metadata={
                    "confidence": confidence,
                    "threshold": self.min_confidence
                }
            )
        else:
            violation = self._create_violation(
                description=f"Confidence {confidence:.2f} below minimum threshold {self.min_confidence:.2f}",
                expected=f">= {self.min_confidence:.2f}",
                actual=f"{confidence:.2f}",
                remediation="Gather additional evidence, involve more critics, or escalate to human review",
                context={
                    "confidence": confidence,
                    "threshold": self.min_confidence,
                    "deficit": self.min_confidence - confidence
                }
            )

            # Score proportional to how close we are to threshold
            score = min(1.0, confidence / self.min_confidence)

            logger.warning(
                f"Rule {self.rule_id}: FAIL (confidence={confidence:.2f} < {self.min_confidence:.2f})"
            )

            return self._create_result(
                False,
                score,
                [violation],
                metadata={
                    "confidence": confidence,
                    "threshold": self.min_confidence,
                    "deficit": self.min_confidence - confidence
                }
            )


class CriticAgreementRule(PolicyRule):
    """
    Requires minimum level of critic agreement (no conflicts).

    Checks for conflicts in critic verdicts and ensures agreement
    is above threshold.
    """

    def __init__(
        self,
        rule_id: str,
        max_conflicts: int = 0,
        severity: RuleSeverity = RuleSeverity.MEDIUM
    ):
        """
        Initialize rule.

        Args:
            rule_id: Unique rule identifier
            max_conflicts: Maximum allowed conflicts
            severity: Rule severity level
        """
        super().__init__(
            rule_id=rule_id,
            name="Critic Agreement Requirement",
            rule_type=RuleType.THRESHOLD,
            severity=severity,
            description=f"Requires <= {max_conflicts} critic conflicts"
        )
        self.max_conflicts = max_conflicts

    def evaluate(self, decision_context: Dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate critic agreement."""
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            logger.warning(f"Rule {self.rule_id}: Missing aggregation_result")
            return self._create_result(False, 0.0, metadata={"error": "Missing aggregation_result"})

        num_conflicts = len(aggregation_result.conflicts_detected)

        if num_conflicts <= self.max_conflicts:
            logger.info(f"Rule {self.rule_id}: PASS ({num_conflicts} conflicts <= {self.max_conflicts})")
            return self._create_result(
                True,
                1.0,
                metadata={
                    "conflicts": num_conflicts,
                    "max_conflicts": self.max_conflicts
                }
            )
        else:
            # Build violation with conflict details
            conflict_descriptions = [
                c.get("description", "Unknown conflict")
                for c in aggregation_result.conflicts_detected
            ]

            violation = self._create_violation(
                description=f"Too many critic conflicts: {num_conflicts} (max: {self.max_conflicts})",
                expected=f"<= {self.max_conflicts} conflicts",
                actual=f"{num_conflicts} conflicts",
                remediation="Review conflicting critic outputs and escalate if necessary",
                context={
                    "conflicts": num_conflicts,
                    "max_conflicts": self.max_conflicts,
                    "conflict_details": conflict_descriptions
                }
            )

            # Score inversely proportional to excess conflicts
            if self.max_conflicts == 0:
                score = 1.0 / (1.0 + num_conflicts)
            else:
                score = self.max_conflicts / num_conflicts

            logger.warning(
                f"Rule {self.rule_id}: FAIL ({num_conflicts} conflicts > {self.max_conflicts})"
            )

            return self._create_result(
                False,
                score,
                [violation],
                metadata={
                    "conflicts": num_conflicts,
                    "max_conflicts": self.max_conflicts
                }
            )


class MinimumCriticsRule(PolicyRule):
    """
    Requires minimum number of critics to contribute.

    Ensures sufficient critics evaluated the case before making a decision.
    """

    def __init__(
        self,
        rule_id: str,
        min_critics: int,
        severity: RuleSeverity = RuleSeverity.HIGH
    ):
        """
        Initialize rule.

        Args:
            rule_id: Unique rule identifier
            min_critics: Minimum number of required critics
            severity: Rule severity level
        """
        if min_critics < 1:
            raise ValueError(f"min_critics must be >= 1, got {min_critics}")

        super().__init__(
            rule_id=rule_id,
            name="Minimum Critics Requirement",
            rule_type=RuleType.THRESHOLD,
            severity=severity,
            description=f"Requires >= {min_critics} contributing critics"
        )
        self.min_critics = min_critics

    def evaluate(self, decision_context: Dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate critic count."""
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            logger.warning(f"Rule {self.rule_id}: Missing aggregation_result")
            return self._create_result(False, 0.0, metadata={"error": "Missing aggregation_result"})

        num_critics = len(aggregation_result.contributing_critics)

        if num_critics >= self.min_critics:
            logger.info(f"Rule {self.rule_id}: PASS ({num_critics} critics >= {self.min_critics})")
            return self._create_result(
                True,
                1.0,
                metadata={
                    "num_critics": num_critics,
                    "min_critics": self.min_critics,
                    "critics": aggregation_result.contributing_critics
                }
            )
        else:
            violation = self._create_violation(
                description=f"Insufficient critics: {num_critics} (minimum: {self.min_critics})",
                expected=f">= {self.min_critics} critics",
                actual=f"{num_critics} critics",
                remediation=f"Include {self.min_critics - num_critics} more critic(s) in evaluation",
                context={
                    "num_critics": num_critics,
                    "min_critics": self.min_critics,
                    "deficit": self.min_critics - num_critics
                }
            )

            # Score proportional to critic count
            score = num_critics / self.min_critics

            logger.warning(
                f"Rule {self.rule_id}: FAIL ({num_critics} critics < {self.min_critics})"
            )

            return self._create_result(
                False,
                score,
                [violation],
                metadata={
                    "num_critics": num_critics,
                    "min_critics": self.min_critics
                }
            )


class VerdictConsistencyRule(PolicyRule):
    """
    Requires consistency between final verdict and weighted scores.

    Validates that the winning verdict has a significant margin over others.
    """

    def __init__(
        self,
        rule_id: str,
        min_margin: float = 0.2,
        severity: RuleSeverity = RuleSeverity.MEDIUM
    ):
        """
        Initialize rule.

        Args:
            rule_id: Unique rule identifier
            min_margin: Minimum score margin between winner and runner-up
            severity: Rule severity level
        """
        if not 0.0 <= min_margin <= 1.0:
            raise ValueError(f"min_margin must be 0.0-1.0, got {min_margin}")

        super().__init__(
            rule_id=rule_id,
            name="Verdict Consistency Check",
            rule_type=RuleType.THRESHOLD,
            severity=severity,
            description=f"Requires winning verdict margin >= {min_margin:.2f}"
        )
        self.min_margin = min_margin

    def evaluate(self, decision_context: Dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate verdict consistency."""
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            logger.warning(f"Rule {self.rule_id}: Missing aggregation_result")
            return self._create_result(False, 0.0, metadata={"error": "Missing aggregation_result"})

        weighted_scores = aggregation_result.weighted_scores

        if len(weighted_scores) < 2:
            # Only one verdict - automatically consistent
            logger.info(f"Rule {self.rule_id}: PASS (only one verdict)")
            return self._create_result(True, 1.0, metadata={"single_verdict": True})

        # Get top 2 scores
        sorted_scores = sorted(weighted_scores.values(), reverse=True)
        top_score = sorted_scores[0]
        second_score = sorted_scores[1]

        # Calculate margin
        margin = top_score - second_score

        if margin >= self.min_margin:
            logger.info(f"Rule {self.rule_id}: PASS (margin={margin:.2f} >= {self.min_margin:.2f})")
            return self._create_result(
                True,
                1.0,
                metadata={
                    "margin": margin,
                    "min_margin": self.min_margin,
                    "top_score": top_score,
                    "second_score": second_score
                }
            )
        else:
            # Find which verdicts are competing
            top_verdict = max(weighted_scores, key=weighted_scores.get)
            second_verdict = sorted(
                weighted_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[1][0]

            violation = self._create_violation(
                description=f"Verdict margin too small: {margin:.2f} (minimum: {self.min_margin:.2f})",
                expected=f">= {self.min_margin:.2f} margin",
                actual=f"{margin:.2f} margin",
                remediation="Decision is not decisive - consider escalation or gathering more evidence",
                context={
                    "margin": margin,
                    "min_margin": self.min_margin,
                    "top_verdict": top_verdict,
                    "second_verdict": second_verdict,
                    "top_score": top_score,
                    "second_score": second_score
                }
            )

            # Score proportional to margin
            score = min(1.0, margin / self.min_margin)

            logger.warning(
                f"Rule {self.rule_id}: FAIL (margin={margin:.2f} < {self.min_margin:.2f})"
            )

            return self._create_result(
                False,
                score,
                [violation],
                metadata={
                    "margin": margin,
                    "min_margin": self.min_margin
                }
            )
