"""
PrecedentCritic: Case Law Consistency Evaluation

Evaluates cases against established precedents:
- Retrieves similar historical cases
- Checks for consistency with precedent
- Detects novel situations requiring review
- Identifies precedent conflicts

Priority: 2
Weight: 1.3
"""

import sys
import os
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ejc.core.base_critic import RuleBasedCritic


class PrecedentCritic(RuleBasedCritic):
    """
    Evaluates consistency with established precedents.

    Integrates with the precedent retrieval system to:
    1. Find similar historical cases
    2. Check for consistency
    3. Identify conflicts or novelty
    4. Escalate when precedent is unclear

    Priority: 2
    Weight: 1.3
    """

    def __init__(self, name: str = "PrecedentCritic", weight: float = 1.3, priority: str = "moderate"):
        super().__init__(name=name, weight=weight, priority=priority)

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply precedent consistency rules.

        Note: Full precedent retrieval integration happens in the main
        adjudication pipeline. This critic provides additional checks
        for precedent conflicts flagged by the governance system.
        """
        text = case.get("text", "")
        context = case.get("context", {})

        # Check if precedent system has flagged a conflict
        precedent_conflict = context.get("precedent_conflict", False)
        precedent_status = context.get("precedent_status", "unknown")

        if precedent_conflict:
            return {
                "verdict": "REVIEW",
                "confidence": 0.9,
                "justification": "Precedent conflict detected - case deviates from established decisions",
                "conflict": True,
                "escalate": True
            }

        if precedent_status == "novelty":
            return {
                "verdict": "REVIEW",
                "confidence": 0.7,
                "justification": "Novel case - no strong precedent match, requires assessment",
                "conflict": False,
                "escalate": True
            }

        if precedent_status == "inherited":
            return {
                "verdict": "ALLOW",
                "confidence": 0.95,
                "justification": "Strong precedent match - consistent with established case law",
                "conflict": False,
                "escalate": False
            }

        if precedent_status == "advisory":
            return {
                "verdict": "ALLOW",
                "confidence": 0.8,
                "justification": "Moderate precedent match - generally consistent",
                "conflict": False,
                "escalate": False
            }

        # No precedent information available
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "No precedent data available for comparison",
            "conflict": False,
            "escalate": False
        }
