"""Neuro-moral replay logging utilities."""

from __future__ import annotations

import json
import os
from typing import Dict, List


class ReplayLogger:
    """Persist critic timelines for later replay/analysis."""

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def log(self, scenario_id: str, timeline: List[Dict[str, object]]) -> str:
        path = os.path.join(self.base_path, f"replay_{scenario_id}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(timeline, handle, indent=2)
        return path
