"""Identity and history ledger for critics.

Provides lightweight metadata for each critic along with a small in-memory
history of dissent counts. The ledger can optionally persist to disk so that
confidence calibration survives process restarts.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional


CRITIC_PROFILE: Dict[str, Dict[str, str]] = {
    "dignity": {"style": "empathetic", "core_value": "inherent worth"},
    "autonomy": {"style": "direct", "core_value": "agency"},
    "fairness": {"style": "analytic", "core_value": "equity"},
    "precaution": {"style": "cautious", "core_value": "risk aversion"},
}


class IdentityLedger:
    """Tracks critic dissent history for confidence self-calibration."""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self.persist_path = persist_path
        self.history: Dict[str, Dict[str, float]] = {}
        self._load()

    def set_persist_path(self, path: str) -> None:
        if self.persist_path:
            return
        self.persist_path = path
        self._load()

    def record_outcome(self, critic: str, verdict: str, final_verdict: Optional[str]) -> None:
        record = self.history.setdefault(critic, {"dissent_total": 0.0, "cases": 0.0})
        record["cases"] += 1
        if final_verdict and verdict and verdict.upper() != final_verdict.upper():
            record["dissent_total"] += 1
        self._persist()

    def dissent_rate(self, critic: str) -> float:
        record = self.history.get(critic, {"dissent_total": 0.0, "cases": 0.0})
        if record["cases"] == 0:
            return 0.0
        return min(1.0, record["dissent_total"] / record["cases"])

    def reliability(self, critic: str) -> float:
        """Return a reliability multiplier in the range [0.1, 1.0]."""

        return max(0.1, 1.0 - self.dissent_rate(critic))

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        return {k: dict(v) for k, v in self.history.items()}

    def _persist(self) -> None:
        if not self.persist_path:
            return
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as handle:
            json.dump(self.history, handle, indent=2)

    def _load(self) -> None:
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as handle:
                self.history = json.load(handle)
        except Exception:
            # If history is unreadable, start fresh but don't crash evaluation.
            self.history = {}


IDENTITY_LEDGER = IdentityLedger()

