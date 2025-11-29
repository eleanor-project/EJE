"""Dissent-aware context learning utilities."""
from __future__ import annotations

import math
from typing import Dict, Iterable, List


class DissentAwareContextModel:
    """Tracks dissent to recommend critic weight adjustments."""

    def __init__(self, *, floor_weight: float = 0.05, learning_rate: float = 0.2):
        self.floor_weight = floor_weight
        self.learning_rate = learning_rate
        self._critic_scores: Dict[str, float] = {}
        self._history: List[Dict[str, float]] = []

    def record_outcome(self, verdict: str, critic_reports: Iterable[Dict[str, float]]) -> None:
        """Update running scores based on agreement with the final verdict."""

        for report in critic_reports:
            critic = report.get("critic") or "unknown"
            critic_verdict = str(report.get("verdict", "")).upper()
            confidence = float(report.get("confidence", 0.0))
            delta = self.learning_rate * confidence
            if critic_verdict != verdict.upper():
                delta *= -1
            self._critic_scores[critic] = self._critic_scores.get(critic, 0.0) + delta
        self._history.append({k: v for k, v in self._critic_scores.items()})

    def suggest_weights(self) -> Dict[str, float]:
        """Return normalized critic weights informed by dissent history."""

        if not self._critic_scores:
            return {}

        # Stabilize scores using a softmax-like transform
        scores = self._critic_scores
        max_score = max(scores.values())
        exp_scores = {
            critic: math.exp(score - max_score) for critic, score in scores.items()
        }
        total = sum(exp_scores.values())
        if total == 0:
            return {critic: self.floor_weight for critic in scores}

        weights = {
            critic: max(exp_score / total, self.floor_weight)
            for critic, exp_score in exp_scores.items()
        }

        # Renormalize after applying floors
        total_weight = sum(weights.values())
        return {critic: weight / total_weight for critic, weight in weights.items()}

    @property
    def history(self) -> List[Dict[str, float]]:
        return list(self._history)
