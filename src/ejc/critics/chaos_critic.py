"""ChaosCritic: intentionally erratic critic for stress testing."""

import random
from typing import Any, Dict

from ejc.core.base_critic import RuleBasedCritic


class ChaosCritic(RuleBasedCritic):
    """A noisy critic that introduces jitter into deliberations."""

    def __init__(self, name: str = "ChaosCritic", weight: float = 0.2, priority: str = "advisory"):
        super().__init__(name=name, weight=weight, priority=priority)

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        verdict = random.choice(["ALLOW", "DENY", "REVIEW", "BLOCK"])
        confidence = round(random.uniform(0.1, 0.7), 2)
        justification = "💥 Chaos mode activated — randomized stress evaluation"
        if case.get("text"):
            justification += f" on '{case.get('text')[:60]}...'"
        return {
            "verdict": verdict,
            "confidence": confidence,
            "justification": justification,
        }
