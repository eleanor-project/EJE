"""
Override Handler - Task 7.2

Implements the override pipeline for applying human reviewer overrides to decisions.

Provides:
- Override request validation
- Override application to decisions
- Decision update with new outcome
- Metadata marking for human modifications

The handler ensures complete auditability and maintains decision integrity
while allowing authorized human reviewers to override automated decisions.
"""

from typing import Optional
from datetime import datetime
from copy import deepcopy

from .override_request import OverrideRequest, OverrideOutcome
from ..decision import Decision
from ..error_handling import GovernanceException
from ...utils.logging import get_logger

logger = get_logger("ejc.governance.override_handler")


class OverrideValidationError(GovernanceException):
    """Raised when an override request fails validation."""
    pass


class OverrideHandler:
    """
    Handles application of human override requests to decisions.

    Task 7.2 Requirements:
    - Validate request
    - Apply override
    - Update decision
    - Mark decision as human-modified

    The handler provides a complete override pipeline that ensures:
    1. Override requests are valid and not expired
    2. Decision IDs match between request and decision
    3. Original outcomes match (if specified in request)
    4. Override is applied to decision's governance_outcome
    5. Complete metadata is added for audit trail
    """

    def __init__(self, preserve_original: bool = True):
        """
        Initialize the override handler.

        Args:
            preserve_original: If True, preserve original decision state in metadata
        """
        self.preserve_original = preserve_original

    def apply_override(
        self,
        decision: Decision,
        override_request: OverrideRequest
    ) -> Decision:
        """
        Apply an override request to a decision.

        This is the main entry point for the override pipeline.

        Args:
            decision: The decision to override
            override_request: The validated override request

        Returns:
            The modified decision with override applied

        Raises:
            OverrideValidationError: If override request validation fails

        Example:
            >>> handler = OverrideHandler()
            >>> request = OverrideRequest(
            ...     reviewer_id="reviewer_123",
            ...     justification="Case requires human judgment due to...",
            ...     proposed_outcome=OverrideOutcome.ALLOW,
            ...     decision_id="dec_456",
            ...     reviewer_role=ReviewerRole.ETHICS_OFFICER
            ... )
            >>> updated_decision = handler.apply_override(decision, request)
        """
        logger.info(
            f"Applying override {override_request.request_id[:8]} to decision "
            f"{decision.decision_id[:8]} by {override_request.reviewer_id}"
        )

        # Step 1: Validate request
        self._validate_override_request(override_request, decision)

        # Make a copy if needed
        if self.preserve_original:
            decision = deepcopy(decision)

        # Capture original verdict before updating
        original_verdict = decision.governance_outcome.get("verdict")

        # Step 2: Apply override to governance_outcome
        self._update_governance_outcome(decision, override_request)

        # Step 3: Mark decision as human-modified
        self._add_override_metadata(decision, override_request, original_verdict)

        # Step 4: Update decision escalation status if changing to/from ESCALATE
        if override_request.proposed_outcome == OverrideOutcome.ESCALATE:
            decision.escalated = True
        elif override_request.original_outcome == "ESCALATE":
            # If we're overriding away from ESCALATE, keep escalated=True
            # but note in metadata that human resolved it
            decision.escalated = True

        logger.info(
            f"Override applied: {override_request.original_outcome or 'N/A'} → "
            f"{override_request.proposed_outcome.value}"
        )

        return decision

    def _validate_override_request(
        self,
        override_request: OverrideRequest,
        decision: Decision
    ) -> None:
        """
        Validate that the override request can be applied to the decision.

        Validation checks:
        1. Request hasn't expired
        2. Decision ID matches
        3. Original outcome matches (if specified in request)

        Args:
            override_request: The override request to validate
            decision: The decision being overridden

        Raises:
            OverrideValidationError: If validation fails
        """
        # Check expiration
        if override_request.is_expired():
            raise OverrideValidationError(
                f"Override request {override_request.request_id} has expired at "
                f"{override_request.expires_at}"
            )

        # Check decision ID match
        if override_request.decision_id != decision.decision_id:
            raise OverrideValidationError(
                f"Override request decision_id '{override_request.decision_id}' does not "
                f"match decision '{decision.decision_id}'"
            )

        # Check original outcome if specified
        if override_request.original_outcome is not None:
            current_verdict = decision.governance_outcome.get("verdict")
            if current_verdict != override_request.original_outcome:
                raise OverrideValidationError(
                    f"Override request expects original outcome '{override_request.original_outcome}' "
                    f"but decision has '{current_verdict}'"
                )

    def _update_governance_outcome(
        self,
        decision: Decision,
        override_request: OverrideRequest
    ) -> None:
        """
        Update the decision's governance_outcome with the override.

        This modifies the verdict in governance_outcome to match the
        proposed outcome from the override request.

        Args:
            decision: The decision to update
            override_request: The override request with new outcome
        """
        # Store original verdict before override
        original_verdict = decision.governance_outcome.get("verdict")

        # Update the verdict
        decision.governance_outcome["verdict"] = override_request.proposed_outcome.value

        # Log the change
        logger.debug(
            f"Updated governance_outcome verdict: {original_verdict} → "
            f"{override_request.proposed_outcome.value}"
        )

    def _add_override_metadata(
        self,
        decision: Decision,
        override_request: OverrideRequest,
        original_verdict: Optional[str]
    ) -> None:
        """
        Add override metadata to the decision for audit trail.

        Marks the decision as human-modified and includes complete
        information about the override for auditability.

        Args:
            decision: The decision to mark as overridden
            override_request: The override request with metadata
            original_verdict: The verdict before the override was applied
        """
        # Create override metadata
        override_metadata = {
            "human_modified": True,
            "override_applied": True,
            "override_id": override_request.request_id,
            "override_timestamp": datetime.utcnow().isoformat(),
            "override_by": {
                "reviewer_id": override_request.reviewer_id,
                "reviewer_name": override_request.reviewer_name,
                "reviewer_role": override_request.reviewer_role.value,
                "reviewer_email": override_request.reviewer_email
            },
            "override_justification": override_request.justification,
            "override_reason_category": override_request.reason_category.value,
            "original_outcome": override_request.original_outcome or original_verdict,
            "proposed_outcome": override_request.proposed_outcome.value,
            "is_urgent": override_request.is_urgent,
            "priority": override_request.priority,
            "supporting_documents": override_request.supporting_documents,
            "stakeholder_input": override_request.stakeholder_input
        }

        # Add to governance_outcome
        decision.governance_outcome["override"] = override_metadata

        # Also set a top-level flag for easy checking
        decision.governance_outcome["human_modified"] = True

        logger.debug(f"Added override metadata to decision {decision.decision_id[:8]}")

    def validate_only(
        self,
        decision: Decision,
        override_request: OverrideRequest
    ) -> bool:
        """
        Validate an override request without applying it.

        Useful for checking if an override can be applied before actually applying it.

        Args:
            decision: The decision that would be overridden
            override_request: The override request to validate

        Returns:
            True if validation passes, False otherwise
        """
        try:
            self._validate_override_request(override_request, decision)
            return True
        except OverrideValidationError as e:
            logger.warning(f"Override validation failed: {e}")
            return False

    def has_been_overridden(self, decision: Decision) -> bool:
        """
        Check if a decision has been overridden by a human.

        Args:
            decision: The decision to check

        Returns:
            True if decision has been overridden, False otherwise
        """
        return decision.governance_outcome.get("human_modified", False)

    def get_override_metadata(self, decision: Decision) -> Optional[dict]:
        """
        Get the override metadata from a decision if it exists.

        Args:
            decision: The decision to get metadata from

        Returns:
            Override metadata dict if present, None otherwise
        """
        return decision.governance_outcome.get("override")

    def get_override_summary(self, decision: Decision) -> Optional[str]:
        """
        Get a human-readable summary of the override if present.

        Args:
            decision: The decision to summarize

        Returns:
            Summary string if decision was overridden, None otherwise
        """
        if not self.has_been_overridden(decision):
            return None

        metadata = self.get_override_metadata(decision)
        if not metadata:
            return "Decision was human-modified (details unavailable)"

        reviewer_name = metadata["override_by"].get("reviewer_name") or metadata["override_by"]["reviewer_id"]
        role = metadata["override_by"]["reviewer_role"]
        original = metadata["original_outcome"]
        proposed = metadata["proposed_outcome"]
        reason = metadata["override_reason_category"]

        return (
            f"Override by {reviewer_name} ({role}): {original} → {proposed} "
            f"[Reason: {reason}]"
        )


# Convenience functions

def apply_override(
    decision: Decision,
    override_request: OverrideRequest,
    preserve_original: bool = True
) -> Decision:
    """
    Apply an override request to a decision.

    Convenience function that creates a handler and applies the override.

    Args:
        decision: The decision to override
        override_request: The override request to apply
        preserve_original: If True, return a copy instead of modifying in-place

    Returns:
        The decision with override applied

    Raises:
        OverrideValidationError: If validation fails
    """
    handler = OverrideHandler(preserve_original=preserve_original)
    return handler.apply_override(decision, override_request)


def validate_override(decision: Decision, override_request: OverrideRequest) -> bool:
    """
    Validate an override request without applying it.

    Convenience function for validation-only checks.

    Args:
        decision: The decision that would be overridden
        override_request: The override request to validate

    Returns:
        True if valid, False otherwise
    """
    handler = OverrideHandler()
    return handler.validate_only(decision, override_request)


# Export all public interfaces
__all__ = [
    'OverrideHandler',
    'OverrideValidationError',
    'apply_override',
    'validate_override'
]
