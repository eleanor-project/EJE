"""Confidence self-awareness utilities for critics."""

from __future__ import annotations

from typing import Dict

from ejc.critics.identity import IdentityLedger


class SelfAwarenessScorer:
    """Calibrates critic confidence using historical dissent and context size."""

    def __init__(self, ledger: IdentityLedger, *, context_penalty: float = 0.05) -> None:
        self.ledger = ledger
        self.context_penalty = context_penalty

    def adjusted_confidence(self, critic: str, base_confidence: float, context: Dict[str, object]) -> float:
        reliability = self.ledger.reliability(critic)
        familiarity_penalty = 1 - (min(len(context), 10) * self.context_penalty)
        familiarity_penalty = max(0.5, familiarity_penalty)

        score = base_confidence * reliability * familiarity_penalty
        return max(0.0, min(1.0, score))
