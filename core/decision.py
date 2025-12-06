"""
Final Decision Object with Compliance Flags

Task 4.3: Implement Compliance Flags

Integrates aggregation results with policy evaluation to produce a final
decision object that includes compliance flags and can be propagated to
audit logs.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from core.critic_aggregator import AggregationResult
from core.policy.rules import (
    PolicyEvaluationResult,
    ComplianceLevel,
    RuleViolation
)

logger = logging.getLogger("ejc.core.decision")


@dataclass
class FinalDecision:
    """
    Final decision object with compliance flags.

    Combines aggregation result and policy evaluation into a unified
    decision that can be propagated to audit logs.
    """

    decision_id: str
    timestamp: str
    query: str

    # Aggregation results
    final_verdict: str
    confidence: float
    contributing_critics: List[str]

    # Policy compliance flags
    compliance_level: ComplianceLevel
    passes_policy: bool  # True if PASSES, False if BORDERLINE or FAILS
    policy_violations: List[RuleViolation]

    # Additional context
    aggregation_result: AggregationResult
    policy_result: Optional[PolicyEvaluationResult]

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation
        """
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "query": self.query,
            "final_verdict": self.final_verdict,
            "confidence": self.confidence,
            "contributing_critics": self.contributing_critics,
            "compliance": {
                "level": self.compliance_level.value,
                "passes_policy": self.passes_policy,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "description": v.description,
                        "expected": str(v.expected),
                        "actual": str(v.actual),
                        "remediation": v.remediation,
                        "context": v.context
                    }
                    for v in self.policy_violations
                ]
            },
            "aggregation": {
                "weighted_scores": self.aggregation_result.weighted_scores,
                "total_weight": self.aggregation_result.total_weight,
                "conflicts": len(self.aggregation_result.conflicts_detected)
            },
            "policy_evaluation": {
                "policy_id": self.policy_result.policy_id if self.policy_result else None,
                "policy_name": self.policy_result.policy_name if self.policy_result else None,
                "passed_rules": self.policy_result.passed_rules if self.policy_result else 0,
                "total_rules": self.policy_result.total_rules if self.policy_result else 0
            } if self.policy_result else None,
            "metadata": self.metadata
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize to JSON.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_audit_log_entry(self) -> Dict[str, Any]:
        """
        Format for audit log.

        Returns:
            Audit log entry dict
        """
        return {
            "event_type": "decision",
            "event_id": self.decision_id,
            "timestamp": self.timestamp,
            "query": self.query,
            "verdict": self.final_verdict,
            "confidence": self.confidence,
            "compliance_level": self.compliance_level.value,
            "passes_policy": self.passes_policy,
            "violation_count": len(self.policy_violations),
            "critical_violations": sum(
                1 for v in self.policy_violations
                if v.severity.value == "critical"
            ),
            "critics": self.contributing_critics,
            "metadata": self.metadata
        }


class DecisionMaker:
    """
    Decision maker that combines aggregation and policy evaluation.

    Produces final decisions with compliance flags.
    """

    def __init__(self, audit_logger: Optional[logging.Logger] = None):
        """
        Initialize decision maker.

        Args:
            audit_logger: Optional logger for audit trails
        """
        self.audit_logger = audit_logger or logging.getLogger("ejc.audit")

    def make_decision(
        self,
        query: str,
        aggregation_result: AggregationResult,
        policy_result: Optional[PolicyEvaluationResult] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FinalDecision:
        """
        Create final decision from aggregation and policy results.

        Args:
            query: Original query
            aggregation_result: Critic aggregation result
            policy_result: Optional policy evaluation result
            metadata: Optional additional metadata

        Returns:
            FinalDecision object
        """
        # Generate decision ID
        decision_id = self._generate_decision_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Determine compliance level
        if policy_result:
            compliance_level = policy_result.overall_compliance
            passes_policy = compliance_level == ComplianceLevel.PASSES
            violations = policy_result.violations
        else:
            # No policy evaluation - assume passes
            compliance_level = ComplianceLevel.PASSES
            passes_policy = True
            violations = []

        # Create decision
        decision = FinalDecision(
            decision_id=decision_id,
            timestamp=timestamp,
            query=query,
            final_verdict=aggregation_result.final_verdict,
            confidence=aggregation_result.confidence,
            contributing_critics=aggregation_result.contributing_critics,
            compliance_level=compliance_level,
            passes_policy=passes_policy,
            policy_violations=violations,
            aggregation_result=aggregation_result,
            policy_result=policy_result,
            metadata=metadata or {}
        )

        # Log to audit trail
        self._log_decision(decision)

        logger.info(
            f"Decision {decision_id}: {decision.final_verdict} "
            f"(confidence={decision.confidence:.2f}, "
            f"compliance={compliance_level.value})"
        )

        return decision

    def _generate_decision_id(self) -> str:
        """Generate unique decision ID."""
        import uuid
        return f"dec-{uuid.uuid4().hex[:16]}"

    def _log_decision(self, decision: FinalDecision):
        """Log decision to audit trail."""
        audit_entry = decision.to_audit_log_entry()
        self.audit_logger.info(json.dumps(audit_entry))

        # Log violations separately if any
        if decision.policy_violations:
            for violation in decision.policy_violations:
                self.audit_logger.warning(
                    f"Policy violation in {decision.decision_id}: "
                    f"{violation.rule_id} - {violation.description}"
                )


class AuditLog:
    """
    Audit log for tracking all decisions and compliance outcomes.

    Stores decisions with compliance flags for compliance reporting
    and observability.
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize audit log.

        Args:
            log_file: Optional file path for persistent logging
        """
        self.log_file = log_file
        self.decisions: List[FinalDecision] = []

        # Configure audit logger
        self.logger = logging.getLogger("ejc.audit")
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_decision(self, decision: FinalDecision):
        """
        Log a decision to the audit trail.

        Args:
            decision: FinalDecision to log
        """
        self.decisions.append(decision)
        self.logger.info(json.dumps(decision.to_audit_log_entry()))

    def get_decisions(
        self,
        compliance_level: Optional[ComplianceLevel] = None,
        verdict: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FinalDecision]:
        """
        Query logged decisions.

        Args:
            compliance_level: Filter by compliance level
            verdict: Filter by verdict
            limit: Maximum number of results

        Returns:
            List of matching decisions
        """
        results = self.decisions

        if compliance_level:
            results = [d for d in results if d.compliance_level == compliance_level]

        if verdict:
            results = [d for d in results if d.final_verdict == verdict]

        if limit:
            results = results[:limit]

        return results

    def get_compliance_stats(self) -> Dict[str, Any]:
        """
        Get compliance statistics.

        Returns:
            Dict with compliance stats
        """
        total = len(self.decisions)
        if total == 0:
            return {
                "total_decisions": 0,
                "by_compliance_level": {},
                "violation_rate": 0.0
            }

        by_level = {}
        for level in ComplianceLevel:
            count = sum(1 for d in self.decisions if d.compliance_level == level)
            by_level[level.value] = {
                "count": count,
                "percentage": (count / total) * 100
            }

        violations = sum(1 for d in self.decisions if not d.passes_policy)

        return {
            "total_decisions": total,
            "by_compliance_level": by_level,
            "violation_rate": (violations / total) * 100,
            "total_violations": violations
        }

    def export_to_file(self, file_path: str):
        """
        Export audit log to JSON file.

        Args:
            file_path: Path to export file
        """
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_decisions": len(self.decisions),
            "decisions": [d.to_dict() for d in self.decisions],
            "compliance_stats": self.get_compliance_stats()
        }

        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.decisions)} decisions to {file_path}")
