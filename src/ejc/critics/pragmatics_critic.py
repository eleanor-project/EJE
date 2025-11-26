"""
PragmaticsCritic: Feasibility and Resource Assessment

Evaluates practical considerations:
- Real-world feasibility
- Resource constraints
- Implementation practicality
- Cost-benefit considerations

Priority: 4 (Lowest)
Severity: Advisory (can be overridden)
"""

import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ejc.core.base_critic import RuleBasedCritic


class PragmaticsCritic(RuleBasedCritic):
    """
    Evaluates practical feasibility and resource considerations.

    This critic provides advisory input on implementation practicality,
    but can be overridden by higher-priority rights concerns.

    Checks for:
    - Feasibility concerns
    - Resource limitations
    - Implementation challenges
    - Practical constraints

    Priority: 4 (Lowest)
    Weight: 0.8 (Lower weight)
    """

    def __init__(self, name: str = "PragmaticsCritic", weight: float = 0.8, priority: str = "advisory"):
        super().__init__(name=name, weight=weight, priority=priority)

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply pragmatic feasibility rules.

        This is a simplified implementation that checks for obvious
        feasibility keywords. A full implementation would include:
        - Resource estimation
        - Cost-benefit analysis
        - Technical feasibility assessment
        - Implementation complexity scoring
        """
        text = case.get("text", "")
        text_lower = text.lower()

        # Check for feasibility concerns
        feasibility_issues = []

        if any(word in text_lower for word in ["impossible", "unfeasible", "impractical"]):
            feasibility_issues.append("feasibility concerns mentioned")

        if any(word in text_lower for word in ["insufficient resources", "lack of funding", "too expensive"]):
            feasibility_issues.append("resource constraints mentioned")

        if any(word in text_lower for word in ["technically impossible", "cannot implement", "not achievable"]):
            feasibility_issues.append("technical limitations mentioned")

        if feasibility_issues:
            return {
                "verdict": "REVIEW",
                "confidence": 0.6,
                "justification": f"Pragmatic concerns: {', '.join(feasibility_issues)} - advisory review recommended",
                "escalate": False,  # Advisory only
                "concerns": feasibility_issues
            }

        # No obvious feasibility issues
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "No obvious feasibility or resource concerns (pragmatic assessment)",
            "escalate": False
        }
