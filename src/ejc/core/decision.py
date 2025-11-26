"""Decision data structure for EJE adjudication results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Decision:
    """
    Represents the final decision output from the EJE adjudication pipeline.

    Attributes:
        decision_id: Unique identifier for this decision
        input_data: The original input case data
        critic_reports: List of individual critic evaluation reports
        aggregation: Aggregated results from all critics
        governance_outcome: Results after applying governance rules
        precedents: Similar precedent cases retrieved
        escalated: Whether this decision was escalated for human review
        timestamp: ISO format timestamp of decision
    """
    decision_id: str
    input_data: Dict[str, Any]
    critic_reports: List[Dict[str, Any]]
    aggregation: Dict[str, Any]
    governance_outcome: Dict[str, Any]
    precedents: List[Dict[str, Any]] = field(default_factory=list)
    escalated: bool = False
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert Decision to dictionary format."""
        return {
            "decision_id": self.decision_id,
            "input_data": self.input_data,
            "critic_reports": self.critic_reports,
            "aggregation": self.aggregation,
            "governance_outcome": self.governance_outcome,
            "precedents": self.precedents,
            "escalated": self.escalated,
            "timestamp": self.timestamp
        }
