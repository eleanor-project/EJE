"""
Override Workflow Integration

High-level workflow utilities for integrating the override system
with the main decision pipeline.

Provides:
- Complete override workflow (apply + log + audit)
- Integration with precedent storage
- Batch override processing
- Helper functions for common override scenarios

This module connects Tasks 7.1-7.4 with the main adjudication pipeline.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..decision import Decision
from .override_request import OverrideRequest, OverrideRequestBatch
from .override_handler import OverrideHandler, OverrideValidationError
from .override_event_logger import log_override_event
from .audit import write_signed_audit_log
from ..precedent.store import store_precedent_case
from ...utils.logging import get_logger

logger = get_logger("ejc.governance.override_workflow")


def apply_decision_override(
    decision: Decision,
    override_request: OverrideRequest,
    store_as_precedent: bool = True,
    precedent_config: Optional[Dict[str, Any]] = None,
    preserve_original: bool = True
) -> Decision:
    """
    Complete override workflow: Apply override, log event, update audit.

    This is the main integration function that connects the override system
    with the decision pipeline. It performs a complete override workflow:

    1. Validates and applies the override to the decision
    2. Logs the override event to the audit trail
    3. Optionally stores the overridden decision as a new precedent
    4. Re-writes the audit log with the updated decision

    Args:
        decision: The decision to override
        override_request: The override request with reviewer information
        store_as_precedent: Whether to store overridden decision as precedent
        precedent_config: Configuration for precedent storage
        preserve_original: If True, returns a copy; if False, modifies in-place

    Returns:
        The overridden Decision object

    Raises:
        OverrideValidationError: If override validation fails

    Example:
        >>> from ejc.core.governance import (
        ...     apply_decision_override,
        ...     OverrideRequest,
        ...     OverrideOutcome,
        ...     ReviewerRole
        ... )
        >>> request = OverrideRequest(
        ...     reviewer_id="ethics_officer_001",
        ...     reviewer_role=ReviewerRole.ETHICS_OFFICER,
        ...     decision_id=decision.decision_id,
        ...     original_outcome="DENY",
        ...     proposed_outcome=OverrideOutcome.ALLOW,
        ...     justification="After ethical review, approval is warranted..."
        ... )
        >>> updated_decision = apply_decision_override(decision, request)
    """
    logger.info(
        f"Starting override workflow for decision {decision.decision_id[:8]} "
        f"by {override_request.reviewer_id}"
    )

    # Step 1: Apply override using handler
    handler = OverrideHandler(preserve_original=preserve_original)

    try:
        overridden_decision = handler.apply_override(decision, override_request)
        logger.info(
            f"Override applied: {override_request.original_outcome or 'N/A'} → "
            f"{override_request.proposed_outcome.value}"
        )
    except OverrideValidationError as e:
        logger.error(f"Override validation failed: {str(e)}")
        raise

    # Step 2: Log override event to audit trail
    try:
        log_override_event(overridden_decision, override_request)
        logger.info("Override event logged to audit trail")
    except Exception as e:
        logger.error(f"Failed to log override event: {str(e)}")
        # Continue despite logging failure - override was already applied
        # In production, you might want to handle this differently

    # Step 3: Re-write audit log with overridden decision
    try:
        write_signed_audit_log(overridden_decision)
        logger.info("Updated decision logged to audit trail")
    except Exception as e:
        logger.error(f"Failed to update audit log: {str(e)}")
        # Continue despite audit failure

    # Step 4: Store as precedent if requested
    if store_as_precedent and precedent_config:
        try:
            if precedent_config.get("enabled", True):
                # Only store if not escalated (unless override resolved the escalation)
                if not overridden_decision.escalated or \
                   override_request.proposed_outcome.value != "ESCALATE":
                    store_precedent_case(overridden_decision, precedent_config)
                    logger.info("Overridden decision stored as precedent")
                else:
                    logger.debug("Skipping precedent storage for escalated decision")
        except Exception as e:
            logger.error(f"Failed to store precedent: {str(e)}")
            # Continue despite storage failure

    logger.info(f"Override workflow complete for decision {decision.decision_id[:8]}")
    return overridden_decision


def apply_batch_overrides(
    decisions: List[Decision],
    override_batch: OverrideRequestBatch,
    store_as_precedent: bool = True,
    precedent_config: Optional[Dict[str, Any]] = None,
    preserve_original: bool = True,
    continue_on_error: bool = True
) -> Dict[str, Any]:
    """
    Apply a batch of override requests to multiple decisions.

    Processes multiple override requests efficiently, with error handling
    for individual failures.

    Args:
        decisions: List of decisions to override
        override_batch: Batch of override requests
        store_as_precedent: Whether to store overridden decisions as precedents
        precedent_config: Configuration for precedent storage
        preserve_original: If True, returns copies; if False, modifies in-place
        continue_on_error: If True, continues processing if one override fails

    Returns:
        Dictionary with results:
        {
            "successful": [Decision, ...],
            "failed": [{"decision_id": str, "error": str}, ...],
            "total_processed": int,
            "success_count": int,
            "failure_count": int
        }

    Example:
        >>> batch = OverrideRequestBatch(
        ...     requests=[request1, request2, request3],
        ...     batch_submitted_by="batch_reviewer"
        ... )
        >>> results = apply_batch_overrides(decisions, batch)
        >>> print(f"Processed {results['total_processed']}, "
        ...       f"{results['success_count']} successful")
    """
    logger.info(
        f"Starting batch override workflow: {override_batch.get_request_count()} requests"
    )

    results = {
        "successful": [],
        "failed": [],
        "total_processed": 0,
        "success_count": 0,
        "failure_count": 0
    }

    # Create a mapping of decision_id to decision for quick lookup
    decision_map = {dec.decision_id: dec for dec in decisions}

    for request in override_batch.requests:
        results["total_processed"] += 1

        # Find corresponding decision
        decision = decision_map.get(request.decision_id)
        if not decision:
            error_msg = f"Decision {request.decision_id} not found in provided decisions"
            logger.warning(error_msg)
            results["failed"].append({
                "decision_id": request.decision_id,
                "error": error_msg
            })
            results["failure_count"] += 1
            continue

        # Apply override
        try:
            overridden = apply_decision_override(
                decision,
                request,
                store_as_precedent=store_as_precedent,
                precedent_config=precedent_config,
                preserve_original=preserve_original
            )
            results["successful"].append(overridden)
            results["success_count"] += 1

        except Exception as e:
            error_msg = f"Override failed: {str(e)}"
            logger.error(f"Failed to process override for {request.decision_id}: {error_msg}")
            results["failed"].append({
                "decision_id": request.decision_id,
                "error": error_msg
            })
            results["failure_count"] += 1

            if not continue_on_error:
                raise

    logger.info(
        f"Batch override complete: {results['success_count']} successful, "
        f"{results['failure_count']} failed out of {results['total_processed']} total"
    )

    return results


def get_escalated_decisions(
    decisions: List[Decision],
    include_overridden: bool = False
) -> List[Decision]:
    """
    Filter decisions that are escalated and potentially need human override.

    Args:
        decisions: List of decisions to filter
        include_overridden: If True, includes decisions already overridden

    Returns:
        List of escalated decisions

    Example:
        >>> escalated = get_escalated_decisions(all_decisions)
        >>> for decision in escalated:
        ...     print(f"Decision {decision.decision_id} needs review")
    """
    handler = OverrideHandler()

    filtered = []
    for decision in decisions:
        # Check if escalated
        if not decision.escalated:
            continue

        # Check if already overridden (unless we want to include those)
        if not include_overridden and handler.has_been_overridden(decision):
            continue

        filtered.append(decision)

    logger.info(f"Found {len(filtered)} escalated decisions needing review")
    return filtered


def create_override_from_review(
    decision: Decision,
    reviewer_id: str,
    reviewer_role: str,
    new_outcome: str,
    justification: str,
    **kwargs
) -> OverrideRequest:
    """
    Convenience function to create an override request from review parameters.

    Simplifies the process of creating an OverrideRequest for common scenarios.

    Args:
        decision: The decision being reviewed
        reviewer_id: ID of the reviewer
        reviewer_role: Role of the reviewer (must be a valid ReviewerRole value)
        new_outcome: Desired outcome (ALLOW, DENY, REVIEW, or ESCALATE)
        justification: Reason for the override
        **kwargs: Additional override request parameters (e.g., reviewer_name,
                 reviewer_email, reason_category, is_urgent, priority)

    Returns:
        OverrideRequest ready to be applied

    Example:
        >>> request = create_override_from_review(
        ...     decision,
        ...     reviewer_id="ethics_officer_jane",
        ...     reviewer_role="ethics_officer",
        ...     new_outcome="ALLOW",
        ...     justification="Ethical review complete, approval granted",
        ...     reviewer_name="Dr. Jane Smith",
        ...     is_urgent=True
        ... )
        >>> updated = apply_decision_override(decision, request)
    """
    from .override_request import OverrideOutcome, ReviewerRole

    # Convert string outcome to enum
    outcome_map = {
        "ALLOW": OverrideOutcome.ALLOW,
        "DENY": OverrideOutcome.DENY,
        "REVIEW": OverrideOutcome.REVIEW,
        "ESCALATE": OverrideOutcome.ESCALATE
    }
    proposed_outcome = outcome_map.get(new_outcome.upper())
    if not proposed_outcome:
        raise ValueError(
            f"Invalid outcome '{new_outcome}'. Must be one of: ALLOW, DENY, REVIEW, ESCALATE"
        )

    # Convert string role to enum
    try:
        role_enum = ReviewerRole(reviewer_role.lower())
    except ValueError:
        raise ValueError(
            f"Invalid reviewer role '{reviewer_role}'. Must be a valid ReviewerRole value."
        )

    # Get current outcome
    original_outcome = decision.governance_outcome.get("verdict")

    # Create request
    request = OverrideRequest(
        reviewer_id=reviewer_id,
        reviewer_role=role_enum,
        decision_id=decision.decision_id,
        original_outcome=original_outcome,
        proposed_outcome=proposed_outcome,
        justification=justification,
        **kwargs
    )

    logger.debug(
        f"Created override request: {original_outcome} → {new_outcome} "
        f"by {reviewer_id}"
    )

    return request


def get_override_summary_for_decision(decision: Decision) -> Optional[Dict[str, Any]]:
    """
    Get a summary of override information for a decision.

    Args:
        decision: The decision to summarize

    Returns:
        Dictionary with override summary, or None if not overridden

    Example:
        >>> summary = get_override_summary_for_decision(decision)
        >>> if summary:
        ...     print(f"Overridden by {summary['reviewer_name']} "
        ...           f"on {summary['timestamp']}")
    """
    handler = OverrideHandler()

    if not handler.has_been_overridden(decision):
        return None

    metadata = handler.get_override_metadata(decision)
    if not metadata:
        return None

    summary = {
        "is_overridden": True,
        "override_id": metadata.get("override_id"),
        "override_timestamp": metadata.get("override_timestamp"),
        "reviewer_id": metadata["override_by"]["reviewer_id"],
        "reviewer_name": metadata["override_by"].get("reviewer_name"),
        "reviewer_role": metadata["override_by"]["reviewer_role"],
        "reviewer_email": metadata["override_by"].get("reviewer_email"),
        "original_outcome": metadata.get("original_outcome"),
        "proposed_outcome": metadata.get("proposed_outcome"),
        "current_outcome": decision.governance_outcome.get("verdict"),
        "justification": metadata.get("override_justification"),
        "reason_category": metadata.get("override_reason_category"),
        "is_urgent": metadata.get("is_urgent", False),
        "priority": metadata.get("priority", 0),
        "human_readable_summary": handler.get_override_summary(decision)
    }

    return summary


# Export public API
__all__ = [
    'apply_decision_override',
    'apply_batch_overrides',
    'get_escalated_decisions',
    'create_override_from_review',
    'get_override_summary_for_decision'
]
