"""
SafetyCritic: Harm Prevention Framework

Evaluates cases for potential harm across three dimensions:
- Physical harm (injury, violence, health risks)
- Psychological harm (trauma, manipulation, emotional abuse)
- Social harm (reputation damage, ostracization, defamation)

Priority: 1 (High - safety is required per RBJA)
Severity: High (escalates to human review, doesn't auto-block)
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


class SafetyCritic(RuleBasedCritic):
    """
    Implements comprehensive harm prevention evaluation.

    Checks for three categories of harm:
    1. Physical Harm - Bodily injury, violence, health risks
    2. Psychological Harm - Trauma, manipulation, emotional damage
    3. Social Harm - Reputation damage, ostracization, defamation

    Unlike critical rights violations (dignity/autonomy/discrimination),
    safety concerns trigger REVIEW/escalation rather than automatic BLOCK.
    This allows for risk assessment and mitigation strategies.

    Priority: 1 (High)
    Weight: 1.5
    """

    def __init__(
        self,
        name: str = "SafetyCritic",
        weight: float = 1.5,
        priority: str = "high"
    ):
        """Initialize the Safety Critic."""
        super().__init__(name=name, weight=weight, priority=priority)
        self.pattern_matcher = PatternMatcher()

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply safety rules to evaluate potential harm.

        Args:
            case: Case dictionary with 'text' field

        Returns:
            Dict with verdict, confidence, justification
        """
        text = case.get("text", "")
        context = case.get("context", {})

        harm_detected = []

        # =====================================================================
        # 1. PHYSICAL HARM CHECK
        # =====================================================================
        physical_harm = self._check_physical_harm(text)
        if physical_harm.detected:
            harm_detected.append({
                "type": "physical",
                "severity": physical_harm.severity,
                "evidence": physical_harm.evidence,
                "confidence": physical_harm.confidence
            })

        # =====================================================================
        # 2. PSYCHOLOGICAL HARM CHECK
        # =====================================================================
        psychological_harm = self._check_psychological_harm(text)
        if psychological_harm.detected:
            harm_detected.append({
                "type": "psychological",
                "severity": psychological_harm.severity,
                "evidence": psychological_harm.evidence,
                "confidence": psychological_harm.confidence
            })

        # =====================================================================
        # 3. SOCIAL HARM CHECK
        # =====================================================================
        social_harm = self._check_social_harm(text)
        if social_harm.detected:
            harm_detected.append({
                "type": "social",
                "severity": social_harm.severity,
                "evidence": social_harm.evidence,
                "confidence": social_harm.confidence
            })

        # =====================================================================
        # 4. EVALUATE OVERALL SAFETY RISK
        # =====================================================================
        if not harm_detected:
            return {
                "verdict": "ALLOW",
                "confidence": 0.8,
                "justification": "No safety concerns detected (physical, psychological, or social harm)",
                "harm_detected": False,
                "escalate": False
            }

        # Calculate combined risk
        critical_harms = [h for h in harm_detected if h['severity'] == 'critical']
        high_harms = [h for h in harm_detected if h['severity'] == 'high']
        moderate_harms = [h for h in harm_detected if h['severity'] == 'moderate']

        # CRITICAL HARM: Immediate risk to life/safety
        if critical_harms:
            combined_confidence = ConfidenceCalculator.aggregate_multi_check([
                physical_harm, psychological_harm, social_harm
            ])

            harm_types = ", ".join([h['type'] for h in critical_harms])
            evidence = []
            for h in critical_harms:
                evidence.extend(h['evidence'])

            return {
                "verdict": "BLOCK",  # Critical harm warrants blocking
                "confidence": combined_confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="BLOCK",
                    primary_reason=f"Critical safety risk detected - {harm_types} harm",
                    evidence=evidence,
                    severity="critical",
                    confidence=combined_confidence
                ),
                "harm_detected": True,
                "harm_types": [h['type'] for h in critical_harms],
                "escalate": True
            }

        # HIGH HARM: Serious concern, requires review
        if high_harms:
            combined_confidence = ConfidenceCalculator.aggregate_multi_check([
                physical_harm, psychological_harm, social_harm
            ])

            harm_types = ", ".join([h['type'] for h in high_harms])
            evidence = []
            for h in high_harms:
                evidence.extend(h['evidence'])

            return {
                "verdict": "REVIEW",
                "confidence": combined_confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="REVIEW",
                    primary_reason=f"High safety concern - {harm_types} harm requires assessment",
                    evidence=evidence,
                    severity="high",
                    confidence=combined_confidence
                ),
                "harm_detected": True,
                "harm_types": [h['type'] for h in high_harms],
                "escalate": True
            }

        # MODERATE HARM: Lower-level concerns
        if moderate_harms:
            combined_confidence = ConfidenceCalculator.aggregate_multi_check([
                physical_harm, psychological_harm, social_harm
            ])

            harm_types = ", ".join([h['type'] for h in moderate_harms])

            return {
                "verdict": "REVIEW",
                "confidence": combined_confidence,
                "justification": f"Moderate safety concerns detected - {harm_types} harm (review recommended)",
                "harm_detected": True,
                "harm_types": [h['type'] for h in moderate_harms],
                "escalate": False  # Moderate doesn't auto-escalate
            }

        # Fallback (shouldn't reach here)
        return {
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "Low-level safety concerns detected, allowing with caution",
            "harm_detected": True,
            "escalate": False
        }

    def _check_physical_harm(self, text: str) -> DetectionResult:
        """
        Check for physical harm indicators.

        Includes:
        - Violence, assault, injury
        - Health risks, toxicity
        - Dangerous activities
        - Life-threatening situations

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        return self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.HARM_PHYSICAL
        )

    def _check_psychological_harm(self, text: str) -> DetectionResult:
        """
        Check for psychological harm indicators.

        Includes:
        - Emotional abuse, trauma
        - Manipulation, gaslighting
        - Anxiety, depression triggers
        - Psychological distress

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        return self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.HARM_PSYCHOLOGICAL
        )

    def _check_social_harm(self, text: str) -> DetectionResult:
        """
        Check for social harm indicators.

        Includes:
        - Reputation damage
        - Defamation, slander, libel
        - Social ostracization, exclusion
        - Privacy violations

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with detection status and evidence
        """
        return self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.HARM_SOCIAL
        )
