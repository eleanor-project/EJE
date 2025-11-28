"""
TruthCritic: Accuracy and Misinformation Detection

Evaluates cases for factual accuracy and truth:
- Misinformation/disinformation detection
- Unverified claims
- Fabricated evidence
- Misleading statements

Priority: 3
Severity: Moderate
"""

import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ejc.core.base_critic import RuleBasedCritic
from ejc.critics.rbja_utils import PatternMatcher, EvidenceBuilder


class TruthCritic(RuleBasedCritic):
    """
    Evaluates truthfulness and accuracy.

    Priority: 3
    Weight: 1.0
    """

    def __init__(self, name: str = "TruthCritic", weight: float = 1.0, priority: str = "normal"):
        super().__init__(name=name, weight=weight, priority=priority)
        self.pattern_matcher = PatternMatcher()

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "")

        misinformation = self.pattern_matcher.detect_patterns(
            text=text,
            patterns=self.pattern_matcher.MISINFORMATION_PATTERNS
        )

        if misinformation.detected and misinformation.severity in ["high", "critical"]:
            return {
                "verdict": "REVIEW",
                "confidence": misinformation.confidence,
                "justification": EvidenceBuilder.build_justification(
                    verdict="REVIEW",
                    primary_reason="Potential misinformation or false claims detected",
                    evidence=misinformation.evidence,
                    severity=misinformation.severity,
                    confidence=misinformation.confidence
                ),
                "escalate": True
            }

        if misinformation.detected:
            return {
                "verdict": "ALLOW",
                "confidence": 0.65,
                "justification": "Minor accuracy concerns, monitoring recommended",
                "escalate": False
            }

        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "No significant accuracy or misinformation concerns",
            "escalate": False
        }
