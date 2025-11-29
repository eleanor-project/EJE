"""
RightsCritic: Rights-Based Jurisprudence Architecture (RBJA) Implementation

Implements the core constitutional framework for EJE/ELEANOR:
- Dignity (inviolable, cannot be overridden)
- Autonomy (freedom from coercion)
- Non-discrimination (equal treatment of protected groups)

These are CRITICAL rights that override all other considerations in
the lexicographic hierarchy.
"""

import sys
import os
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ejc.core.base_critic import RuleBasedCritic
from ejc.critics.rbja_utils import (
    PatternMatcher,
    ConfidenceCalculator,
    EvidenceBuilder,
    DetectionResult
)


class RightsCritic(RuleBasedCritic):
    """
    Implements Rights-Based Jurisprudence Architecture (RBJA).

    Evaluates cases against the three critical, inviolable rights:
    1. Human Dignity - Cannot treat people as mere means/objects
    2. Autonomy - Cannot coerce or remove legitimate choice
    3. Non-Discrimination - Cannot disfavor protected groups

    These rights are CRITICAL and cannot be overridden by any utilitarian
    or consequentialist reasoning. A single critical violation results
    in immediate BLOCK verdict.

    Priority: 1 (Highest)
    Weight: 2.0 (Higher weight than other critics)
    """

    def __init__(
        self,
        name: str = "RightsCritic",
        weight: float = 2.0,
        priority: str = "critical"
    ):
        """Initialize the Rights Critic."""
        super().__init__(name=name, weight=weight, priority=priority)
        self.pattern_matcher = PatternMatcher()

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rights-based rules to evaluate the case.

        Checks for violations of:
        1. Dignity (CRITICAL - immediate block)
        2. Autonomy (CRITICAL - immediate block)
        3. Non-Discrimination (CRITICAL - immediate block)

        Args:
            case: Case dictionary with 'text' field and optional 'context'

        Returns:
            Dict with verdict, confidence, justification, and metadata
        """
        text = case.get("text", "")
        context = case.get("context", {})

        violations = []

        # =====================================================================
        # 1. DIGNITY CHECK (CRITICAL - Cannot Override)
        # =====================================================================
        dignity_result = self._check_dignity_violation(text)
        if dignity_result.detected and dignity_result.severity in ["high", "critical"]:
            violations.append({
                "right": "dignity",
                "severity": "critical",
                "evidence": dignity_result.evidence,
                "confidence": dignity_result.confidence
            })
            # Immediate block - dignity is inviolable
            return {
                "verdict": "BLOCK",
                "confidence": dignity_result.confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="BLOCK",
                    primary_reason="Critical dignity violation - treats humans as mere objects/means",
                    evidence=dignity_result.evidence,
                    severity="critical",
                    confidence=dignity_result.confidence
                ),
                "right": "dignity",
                "violation": True,
                "escalate": True
            }

        # =====================================================================
        # 2. AUTONOMY CHECK (CRITICAL - Cannot Override)
        # =====================================================================
        autonomy_result = self._check_autonomy_violation(text)
        if autonomy_result.detected and autonomy_result.severity in ["high", "critical"]:
            violations.append({
                "right": "autonomy",
                "severity": "critical",
                "evidence": autonomy_result.evidence,
                "confidence": autonomy_result.confidence
            })
            # Immediate block - autonomy is inviolable
            return {
                "verdict": "BLOCK",
                "confidence": autonomy_result.confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="BLOCK",
                    primary_reason="Critical autonomy violation - coercion or removal of legitimate choice",
                    evidence=autonomy_result.evidence,
                    severity="critical",
                    confidence=autonomy_result.confidence
                ),
                "right": "autonomy",
                "violation": True,
                "escalate": True
            }

        # =====================================================================
        # 3. NON-DISCRIMINATION CHECK (CRITICAL - Cannot Override)
        # =====================================================================
        discrimination_result = self._check_discrimination(text)
        if discrimination_result.detected and discrimination_result.severity in ["high", "critical"]:
            violations.append({
                "right": "non_discrimination",
                "severity": "critical",
                "evidence": discrimination_result.evidence,
                "confidence": discrimination_result.confidence
            })
            # Immediate block - non-discrimination is inviolable
            return {
                "verdict": "BLOCK",
                "confidence": discrimination_result.confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="BLOCK",
                    primary_reason="Critical discrimination violation - disfavors protected group",
                    evidence=discrimination_result.evidence,
                    severity="critical",
                    confidence=discrimination_result.confidence
                ),
                "right": "non_discrimination",
                "violation": True,
                "escalate": True
            }

        # =====================================================================
        # 4. MODERATE CONCERNS (Require Review but not Block)
        # =====================================================================
        moderate_violations = []

        # Check for moderate dignity concerns
        if dignity_result.detected and dignity_result.severity == "moderate":
            moderate_violations.append({
                "right": "dignity",
                "severity": "moderate",
                "evidence": dignity_result.evidence
            })

        # Check for moderate autonomy concerns
        if autonomy_result.detected and autonomy_result.severity == "moderate":
            moderate_violations.append({
                "right": "autonomy",
                "severity": "moderate",
                "evidence": autonomy_result.evidence
            })

        # Check for moderate discrimination concerns
        if discrimination_result.detected and discrimination_result.severity == "moderate":
            moderate_violations.append({
                "right": "non_discrimination",
                "severity": "moderate",
                "evidence": discrimination_result.evidence
            })

        # If moderate violations detected, escalate for review
        if moderate_violations:
            combined_confidence = ConfidenceCalculator.aggregate_multi_check([
                dignity_result, autonomy_result, discrimination_result
            ])

            return {
                "verdict": "REVIEW",
                "confidence": combined_confidence,
                "justification": EvidenceBuilder.build_multi_violation_justification(
                    violations=moderate_violations,
                    verdict="REVIEW"
                ),
                "violation": True,
                "escalate": True,
                "concerns": moderate_violations
            }

        # =====================================================================
        # 5. NO VIOLATIONS DETECTED
        # =====================================================================
        return {
            "verdict": "ALLOW",
            "confidence": 0.85,  # High confidence in non-detection
            "justification": "No critical rights violations detected (dignity, autonomy, non-discrimination)",
            "violation": False,
            "escalate": False
        }

    def _check_dignity_violation(self, text: str) -> DetectionResult:
        """
        Check for human dignity violations.

        Dignity violations include:
        - Treating people as mere objects/instruments
        - Dehumanization
        - Exploitation without consent
        - Degradation or humiliation

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        return self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.DIGNITY_PATTERNS
        )

    def _check_autonomy_violation(self, text: str) -> DetectionResult:
        """
        Check for autonomy violations.

        Autonomy violations include:
        - Coercion or compulsion
        - Removal of legitimate choice
        - Deceptive manipulation
        - Paternalistic overrides of competent decisions

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        return self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.AUTONOMY_PATTERNS
        )

    def _check_discrimination(self, text: str) -> DetectionResult:
        """
        Check for discrimination violations.

        Discrimination violations include:
        - Unequal treatment based on protected characteristics
        - Bias against protected groups
        - Systemic or institutional discrimination
        - Stereotyping or stigmatization

        Protected groups include:
        - Race, ethnicity, national origin
        - Gender, sex, sexual orientation
        - Religion, creed
        - Age, disability
        - Pregnancy, familial status, veteran status

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        discrimination_result = self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.DISCRIMINATION_PATTERNS
        )

        # Also check for protected group mentions + negative context
        has_protected_groups, groups = self.pattern_matcher.detect_protected_group_mention(text)

        # If we have discrimination patterns AND protected group mentions, higher severity
        if discrimination_result.detected and has_protected_groups:
            discrimination_result.severity = "critical"
            discrimination_result.confidence = min(1.0, discrimination_result.confidence + 0.2)
            discrimination_result.evidence.append(f"Mentions protected groups: {', '.join(list(groups)[:3])}")

        return discrimination_result
