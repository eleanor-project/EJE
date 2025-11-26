"""
FairnessCritic: Equity and Justice Evaluation

Evaluates cases for fairness concerns:
- Equitable treatment across groups
- Disparate impact on protected classes
- Access and opportunity equality
- Systemic bias detection

Priority: 2
Severity: Moderate (required unless overridden by critical rights)
"""

import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ejc.core.base_critic import RuleBasedCritic
from ejc.critics.rbja_utils import PatternMatcher, ConfidenceCalculator, EvidenceBuilder


class FairnessCritic(RuleBasedCritic):
    """
    Evaluates fairness and equity in decision-making.

    Checks for:
    - Unequal treatment
    - Disparate impact
    - Access/opportunity gaps
    - Systemic bias

    Priority: 2
    Weight: 1.2
    """

    def __init__(self, name: str = "FairnessCritic", weight: float = 1.2, priority: str = "moderate"):
        super().__init__(name=name, weight=weight, priority=priority)
        self.pattern_matcher = PatternMatcher()

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "")

        # Detect unfairness patterns
        unfairness = self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.UNFAIRNESS_PATTERNS
        )

        # Check for protected group + unfairness combination
        has_protected_groups, groups = self.pattern_matcher.detect_protected_group_mention(text)

        if unfairness.detected and unfairness.severity in ["high", "critical"]:
            if has_protected_groups:
                # Escalates to discrimination (handled by RightsCritic)
                return {
                    "verdict": "REVIEW",
                    "confidence": min(0.9, unfairness.confidence + 0.1),
                    "justification": f"Fairness concern with protected groups ({', '.join(list(groups)[:2])}) - escalating to rights review",
                    "fairness_penalty": True,
                    "escalate": True
                }
            else:
                return {
                    "verdict": "REVIEW",
                    "confidence": unfairness.confidence,
                    "justification": EvidenceBuilder.build_justification(
                        verdict="REVIEW",
                        primary_reason="Significant fairness concerns detected",
                        evidence=unfairness.evidence,
                        severity=unfairness.severity,
                        confidence=unfairness.confidence
                    ),
                    "fairness_penalty": True,
                    "escalate": False
                }

        if unfairness.detected:
            return {
                "verdict": "ALLOW",
                "confidence": 0.6,
                "justification": f"Minor fairness concerns noted: {unfairness.evidence[0] if unfairness.evidence else 'general inequity'}",
                "fairness_penalty": True,
                "escalate": False
            }

        return {
            "verdict": "ALLOW",
            "confidence": 0.85,
            "justification": "No significant fairness concerns detected",
            "fairness_penalty": False,
            "escalate": False
        }
