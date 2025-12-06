"""
Override Event Logger - Task 7.3

Logs override events to the signed audit trail with complete metadata.

Provides:
- Override event logging with reviewer identity
- Timestamp tracking
- Reasoning and justification capture
- Original vs overridden decision comparison
- Integration with signed audit log for immutability

All override events are cryptographically signed and tamper-evident.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .override_request import OverrideRequest
from ..decision import Decision
from .audit import write_signed_audit_log, get_audit_logger
from ...utils.logging import get_logger

logger = get_logger("ejc.governance.override_event_logger")


def create_override_event_bundle(
    decision: Decision,
    override_request: OverrideRequest,
    override_applied_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Create a structured event bundle for an override event.

    This bundle contains all information required for audit compliance:
    - Reviewer identity (ID, name, role, email)
    - Timestamp (when override was requested and applied)
    - Reasoning (justification and categorized reason)
    - Original vs overridden decision comparison
    - Supporting metadata for compliance review

    Args:
        decision: The decision that was overridden
        override_request: The override request with reviewer information
        override_applied_at: When the override was applied (defaults to now)

    Returns:
        Dictionary containing complete override event data
    """
    if override_applied_at is None:
        override_applied_at = datetime.utcnow()

    # Extract original outcome from decision
    original_outcome = decision.governance_outcome.get("verdict", "UNKNOWN")

    # Get override metadata if it exists (after override was applied)
    override_metadata = decision.governance_outcome.get("override", {})

    # Get current outcome (after override)
    current_outcome = decision.governance_outcome.get("verdict", "UNKNOWN")

    # Create event bundle with all required fields
    event_bundle = {
        # Event identification
        "event_type": "override_applied",
        "event_id": override_request.request_id,
        "request_id": decision.decision_id,  # Required by SignedAuditLogger
        "timestamp": override_applied_at.isoformat(),  # Required by SignedAuditLogger

        # Decision reference
        "decision_id": decision.decision_id,
        "decision_timestamp": decision.timestamp,

        # Reviewer identity (Task 7.3 requirement)
        "reviewer": {
            "reviewer_id": override_request.reviewer_id,
            "reviewer_name": override_request.reviewer_name,
            "reviewer_role": override_request.reviewer_role.value,
            "reviewer_email": override_request.reviewer_email
        },

        # Timestamps (Task 7.3 requirement)
        "override_request_timestamp": override_request.timestamp.isoformat(),
        "override_applied_timestamp": override_applied_at.isoformat(),

        # Reasoning (Task 7.3 requirement)
        "justification": override_request.justification,
        "reason_category": override_request.reason_category.value,

        # Original vs overridden decision (Task 7.3 requirement)
        "outcome_change": {
            "original_outcome": override_request.original_outcome or original_outcome,
            "proposed_outcome": override_request.proposed_outcome.value,
            "current_outcome": current_outcome
        },

        # Additional context for audit trail
        "metadata": {
            "is_urgent": override_request.is_urgent,
            "priority": override_request.priority,
            "supporting_documents": override_request.supporting_documents,
            "stakeholder_input": override_request.stakeholder_input,
            "additional_context": override_request.additional_context
        },

        # Escalation tracking
        "escalation_status": {
            "decision_escalated": decision.escalated,
            "override_to_escalate": override_request.proposed_outcome.value == "ESCALATE",
            "override_from_escalate": override_request.original_outcome == "ESCALATE"
        },

        # Decision snapshot (for forensic analysis)
        "decision_snapshot": {
            "aggregation_summary": decision.aggregation.get("verdict") if decision.aggregation else None,
            "critic_count": len(decision.critic_reports) if decision.critic_reports else 0,
            "precedent_count": len(decision.precedents) if decision.precedents else 0
        }
    }

    return event_bundle


def log_override_event(
    decision: Decision,
    override_request: OverrideRequest,
    override_applied_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Log an override event to the signed audit trail.

    Task 7.3 Requirements:
    - Log override events including:
      * Reviewer identity
      * Timestamp
      * Reasoning
      * Original vs overridden decision

    This function creates a complete override event bundle and logs it
    to the signed audit trail, ensuring immutability and tamper-evidence.

    Args:
        decision: The decision that was overridden
        override_request: The override request to log
        override_applied_at: When the override was applied (defaults to now)

    Returns:
        The event bundle that was logged

    Raises:
        Exception: If audit logging fails

    Example:
        >>> from ejc.core.governance import log_override_event, OverrideRequest
        >>> request = OverrideRequest(
        ...     reviewer_id="reviewer_123",
        ...     justification="Detailed reasoning here...",
        ...     proposed_outcome=OverrideOutcome.ALLOW,
        ...     decision_id=decision.decision_id,
        ...     reviewer_role=ReviewerRole.ETHICS_OFFICER
        ... )
        >>> event = log_override_event(decision, request)
        >>> print(f"Override event logged: {event['event_id']}")
    """
    logger.info(
        f"Logging override event {override_request.request_id[:8]} for decision "
        f"{decision.decision_id[:8]} by {override_request.reviewer_id}"
    )

    # Create structured event bundle
    event_bundle = create_override_event_bundle(
        decision,
        override_request,
        override_applied_at
    )

    # Log to signed audit trail
    try:
        # Create a Decision-like object from the event bundle for audit logging
        # The audit system expects a Decision object with to_dict() method
        class OverrideEventWrapper:
            """Wrapper to make event bundle compatible with audit logging."""
            def __init__(self, bundle):
                self._bundle = bundle
                self.decision_id = bundle["decision_id"]

            def to_dict(self):
                return self._bundle

        event_wrapper = OverrideEventWrapper(event_bundle)
        write_signed_audit_log(event_wrapper)

        logger.info(
            f"✅ Override event logged: {override_request.original_outcome or 'N/A'} → "
            f"{override_request.proposed_outcome.value} by "
            f"{override_request.reviewer_name or override_request.reviewer_id}"
        )

    except Exception as e:
        logger.error(f"Failed to log override event: {str(e)}")
        raise

    return event_bundle


def log_override_event_simple(
    decision_id: str,
    reviewer_id: str,
    reviewer_name: Optional[str],
    reviewer_role: str,
    original_outcome: str,
    new_outcome: str,
    justification: str,
    reason_category: str = "other"
) -> Dict[str, Any]:
    """
    Simplified override event logging for basic use cases.

    This is a convenience function that creates a minimal override event
    without requiring full OverrideRequest and Decision objects.

    Args:
        decision_id: ID of the decision being overridden
        reviewer_id: ID of the reviewer
        reviewer_name: Name of the reviewer
        reviewer_role: Role of the reviewer
        original_outcome: Original decision outcome
        new_outcome: New decision outcome after override
        justification: Reason for override
        reason_category: Categorized reason

    Returns:
        The event bundle that was logged
    """
    logger.info(
        f"Logging simple override event for decision {decision_id[:8]} by {reviewer_id}"
    )

    # Create minimal event bundle
    event_bundle = {
        "event_type": "override_applied",
        "event_id": f"override_{decision_id}_{datetime.utcnow().timestamp()}",
        "request_id": decision_id,
        "timestamp": datetime.utcnow().isoformat(),

        "decision_id": decision_id,

        "reviewer": {
            "reviewer_id": reviewer_id,
            "reviewer_name": reviewer_name,
            "reviewer_role": reviewer_role,
            "reviewer_email": None
        },

        "justification": justification,
        "reason_category": reason_category,

        "outcome_change": {
            "original_outcome": original_outcome,
            "proposed_outcome": new_outcome,
            "current_outcome": new_outcome
        },

        "metadata": {},
        "escalation_status": {},
        "decision_snapshot": {}
    }

    # Log to audit trail
    try:
        class OverrideEventWrapper:
            def __init__(self, bundle):
                self._bundle = bundle
                self.decision_id = bundle["decision_id"]

            def to_dict(self):
                return self._bundle

        event_wrapper = OverrideEventWrapper(event_bundle)
        write_signed_audit_log(event_wrapper)

        logger.info(f"✅ Simple override event logged: {original_outcome} → {new_outcome}")

    except Exception as e:
        logger.error(f"Failed to log simple override event: {str(e)}")
        raise

    return event_bundle


def get_override_events_for_decision(decision_id: str) -> list:
    """
    Retrieve all override events for a specific decision.

    Args:
        decision_id: The decision ID to look up

    Returns:
        List of override event bundles

    Note:
        This is a placeholder for future implementation.
        Full implementation would query the audit log database.
    """
    # TODO: Implement audit log query functionality
    # This would use the SignedAuditLogger to query the database
    # for all events with event_type="override_applied" and matching decision_id
    logger.warning("get_override_events_for_decision not yet fully implemented")
    return []


# Export public interface
__all__ = [
    'log_override_event',
    'log_override_event_simple',
    'create_override_event_bundle',
    'get_override_events_for_decision'
]
