"""
Custom rule-based critic implementation.
Uses the RuleBasedCritic ABC for proper separation of concerns.
"""
from typing import Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from ejc.core.base_critic import RuleBasedCritic


class CustomRuleCritic(RuleBasedCritic):
    """
    A simple example critic that evaluates text based on rule logic.
    Designed to be fully synchronous and compatible with EJE.

    Inherits from RuleBasedCritic ABC for proper interface compliance.
    """

    def __init__(self, name: str = "CustomRule", weight: float = 1.0, priority: str = None):
        """Initialize the custom rule critic."""
        super().__init__(name=name, weight=weight, priority=priority)

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply custom rule logic to the case.

        Args:
            case: Case dictionary containing at minimum a 'text' field

        Returns:
            Dict with verdict, confidence, and justification
        """
        text = case.get("text", "")

        # Simple rule: allow if contains 'transparency'
        if "transparency" in text.lower():
            verdict = "ALLOW"
            confidence = 1.0
            justification = "Text promotes transparency (rule-based approval)"
        else:
            verdict = "REVIEW"
            confidence = 0.5
            justification = "No transparency indicators found (requires review)"

        return {
            "verdict": verdict,
            "confidence": confidence,
            "justification": justification
        }

