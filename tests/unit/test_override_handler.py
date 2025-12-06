"""
Tests for Override Handler - Task 7.2

Comprehensive test suite for the override handler implementation.

Tests cover:
- Basic override application
- Validation checks
- Metadata creation and tracking
- Helper methods
- Edge cases and error conditions
"""

import pytest
from datetime import datetime, timedelta
from copy import deepcopy

from src.ejc.core.governance import (
    OverrideHandler,
    OverrideRequest,
    OverrideOutcome,
    OverrideReason,
    ReviewerRole,
    OverrideValidationError,
    apply_override,
    validate_override
)
from src.ejc.core.decision import Decision


# Test Fixtures

@pytest.fixture
def sample_decision():
    """Create a sample decision for testing."""
    return Decision(
        decision_id="dec_12345",
        input_data={"case_id": "case_001", "action": "process"},
        critic_reports=[
            {"critic": "safety", "verdict": "ALLOW", "confidence": 0.9},
            {"critic": "fairness", "verdict": "ALLOW", "confidence": 0.8}
        ],
        aggregation={
            "overall_verdict": "ALLOW",
            "confidence": 0.85,
            "consensus": "unanimous"
        },
        governance_outcome={
            "verdict": "ALLOW",
            "confidence": 0.85,
            "safeguards_triggered": []
        },
        precedents=[],
        escalated=False,
        timestamp="2025-01-15T10:30:00Z"
    )


@pytest.fixture
def sample_override_request():
    """Create a sample override request for testing."""
    return OverrideRequest(
        reviewer_id="reviewer_001",
        reviewer_name="Dr. Jane Smith",
        reviewer_role=ReviewerRole.ETHICS_OFFICER,
        reviewer_email="jane.smith@example.org",
        decision_id="dec_12345",
        original_outcome="ALLOW",
        proposed_outcome=OverrideOutcome.DENY,
        justification="After ethical review, the original decision did not properly account for potential harm to vulnerable populations.",
        reason_category=OverrideReason.ETHICAL_CONCERN,
        priority=7
    )


@pytest.fixture
def override_handler():
    """Create an override handler instance."""
    return OverrideHandler(preserve_original=True)


# Test Classes

class TestBasicOverrideApplication:
    """Test basic override application functionality."""

    def test_apply_override_changes_verdict(self, override_handler, sample_decision, sample_override_request):
        """Test that applying override changes the verdict"""
        original_verdict = sample_decision.governance_outcome["verdict"]
        assert original_verdict == "ALLOW"

        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)

        assert updated_decision.governance_outcome["verdict"] == "DENY"
        assert updated_decision.governance_outcome["verdict"] != original_verdict

    def test_apply_override_marks_as_human_modified(self, override_handler, sample_decision, sample_override_request):
        """Test that override marks decision as human-modified"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)

        assert updated_decision.governance_outcome["human_modified"] is True
        assert "override" in updated_decision.governance_outcome

    def test_apply_override_preserves_original_when_enabled(self, sample_decision, sample_override_request):
        """Test that preserve_original=True doesn't modify input decision"""
        handler = OverrideHandler(preserve_original=True)
        original_verdict = sample_decision.governance_outcome["verdict"]

        updated_decision = handler.apply_override(sample_decision, sample_override_request)

        # Original should be unchanged
        assert sample_decision.governance_outcome["verdict"] == original_verdict
        assert sample_decision.governance_outcome.get("human_modified") is None

        # Updated should be changed
        assert updated_decision.governance_outcome["verdict"] == "DENY"
        assert updated_decision.governance_outcome["human_modified"] is True

    def test_apply_override_modifies_in_place_when_disabled(self, sample_decision, sample_override_request):
        """Test that preserve_original=False modifies decision in-place"""
        handler = OverrideHandler(preserve_original=False)

        updated_decision = handler.apply_override(sample_decision, sample_override_request)

        # Should be the same object
        assert updated_decision is sample_decision
        assert sample_decision.governance_outcome["verdict"] == "DENY"
        assert sample_decision.governance_outcome["human_modified"] is True


class TestOverrideValidation:
    """Test override request validation."""

    def test_expired_override_rejected(self, override_handler, sample_decision):
        """Test that expired override requests are rejected"""
        # Create a request with future expiration, then manually expire it
        expired_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_12345",
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="This override request has expired and should not be applied.",
            expires_at=datetime.utcnow() + timedelta(hours=1)  # Future initially
        )

        # Manually set to expired (bypass Pydantic validation)
        object.__setattr__(expired_request, 'expires_at', datetime.utcnow() - timedelta(hours=1))

        with pytest.raises(OverrideValidationError, match="has expired"):
            override_handler.apply_override(sample_decision, expired_request)

    def test_mismatched_decision_id_rejected(self, override_handler, sample_decision):
        """Test that override with wrong decision ID is rejected"""
        wrong_id_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.LEGAL_COUNSEL,
            decision_id="dec_WRONG",  # Wrong ID
            proposed_outcome=OverrideOutcome.ESCALATE,
            justification="This override has a mismatched decision ID and should be rejected."
        )

        with pytest.raises(OverrideValidationError, match="does not match"):
            override_handler.apply_override(sample_decision, wrong_id_request)

    def test_mismatched_original_outcome_rejected(self, override_handler, sample_decision):
        """Test that override with wrong original outcome is rejected"""
        # Decision has verdict "ALLOW", but request expects "DENY"
        wrong_outcome_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_12345",
            original_outcome="DENY",  # Wrong - decision is actually ALLOW
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="This override expects the wrong original outcome and should be rejected."
        )

        with pytest.raises(OverrideValidationError, match="expects original outcome"):
            override_handler.apply_override(sample_decision, wrong_outcome_request)

    def test_valid_override_without_original_outcome(self, override_handler, sample_decision):
        """Test that override without original_outcome specified is accepted"""
        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_12345",
            # No original_outcome specified
            proposed_outcome=OverrideOutcome.ESCALATE,
            justification="Override without specifying original outcome should work fine."
        )

        # Should not raise
        updated_decision = override_handler.apply_override(sample_decision, request)
        assert updated_decision.governance_outcome["verdict"] == "ESCALATE"

    def test_validate_only_returns_true_for_valid(self, override_handler, sample_decision, sample_override_request):
        """Test validate_only returns True for valid request"""
        is_valid = override_handler.validate_only(sample_decision, sample_override_request)
        assert is_valid is True

    def test_validate_only_returns_false_for_invalid(self, override_handler, sample_decision):
        """Test validate_only returns False for invalid request"""
        invalid_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_WRONG",
            proposed_outcome=OverrideOutcome.DENY,
            justification="This request has an invalid decision ID."
        )

        is_valid = override_handler.validate_only(sample_decision, invalid_request)
        assert is_valid is False


class TestOverrideMetadata:
    """Test override metadata creation and tracking."""

    def test_metadata_includes_override_id(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes the override request ID"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["override_id"] == sample_override_request.request_id

    def test_metadata_includes_reviewer_info(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes complete reviewer information"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["override_by"]["reviewer_id"] == "reviewer_001"
        assert metadata["override_by"]["reviewer_name"] == "Dr. Jane Smith"
        assert metadata["override_by"]["reviewer_role"] == "ethics_officer"
        assert metadata["override_by"]["reviewer_email"] == "jane.smith@example.org"

    def test_metadata_includes_justification(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes the justification"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["override_justification"] == sample_override_request.justification
        assert len(metadata["override_justification"]) > 0

    def test_metadata_includes_outcomes(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes both original and proposed outcomes"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["original_outcome"] == "ALLOW"
        assert metadata["proposed_outcome"] == "DENY"

    def test_metadata_includes_reason_category(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes the categorized reason"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["override_reason_category"] == "ethical_concern"

    def test_metadata_includes_timestamp(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes an override timestamp"""
        before = datetime.utcnow()
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        after = datetime.utcnow()

        metadata = updated_decision.governance_outcome["override"]
        override_timestamp = datetime.fromisoformat(metadata["override_timestamp"])

        # Timestamp should be between before and after
        assert before <= override_timestamp <= after

    def test_metadata_includes_priority_and_urgency(self, override_handler, sample_decision, sample_override_request):
        """Test that metadata includes priority and urgency flags"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["priority"] == 7
        assert "is_urgent" in metadata

    def test_metadata_includes_supporting_info(self, override_handler, sample_decision):
        """Test that metadata includes supporting documents and stakeholder input"""
        request = OverrideRequest(
            reviewer_id="reviewer_002",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_12345",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Override with supporting documentation and stakeholder input.",
            supporting_documents=["doc1.pdf", "doc2.pdf"],
            stakeholder_input="Stakeholders expressed concerns about the original decision."
        )

        updated_decision = override_handler.apply_override(sample_decision, request)
        metadata = updated_decision.governance_outcome["override"]

        assert metadata["supporting_documents"] == ["doc1.pdf", "doc2.pdf"]
        assert metadata["stakeholder_input"] == "Stakeholders expressed concerns about the original decision."

    def test_metadata_stores_original_when_not_specified(self, override_handler, sample_decision):
        """Test that metadata stores current verdict as original when not specified"""
        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_12345",
            # original_outcome not specified
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="Override without explicit original outcome specified."
        )

        updated_decision = override_handler.apply_override(sample_decision, request)
        metadata = updated_decision.governance_outcome["override"]

        # Should use the decision's current verdict
        assert metadata["original_outcome"] == "ALLOW"


class TestHelperMethods:
    """Test helper methods for checking override status."""

    def test_has_been_overridden_true_after_override(self, override_handler, sample_decision, sample_override_request):
        """Test has_been_overridden returns True after override"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)

        assert override_handler.has_been_overridden(updated_decision) is True

    def test_has_been_overridden_false_before_override(self, override_handler, sample_decision):
        """Test has_been_overridden returns False for unmodified decision"""
        assert override_handler.has_been_overridden(sample_decision) is False

    def test_get_override_metadata_returns_dict_after_override(self, override_handler, sample_decision, sample_override_request):
        """Test get_override_metadata returns metadata dict after override"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        metadata = override_handler.get_override_metadata(updated_decision)

        assert metadata is not None
        assert isinstance(metadata, dict)
        assert metadata["override_id"] == sample_override_request.request_id

    def test_get_override_metadata_returns_none_before_override(self, override_handler, sample_decision):
        """Test get_override_metadata returns None for unmodified decision"""
        metadata = override_handler.get_override_metadata(sample_decision)
        assert metadata is None

    def test_get_override_summary_returns_string_after_override(self, override_handler, sample_decision, sample_override_request):
        """Test get_override_summary returns summary string after override"""
        updated_decision = override_handler.apply_override(sample_decision, sample_override_request)
        summary = override_handler.get_override_summary(updated_decision)

        assert summary is not None
        assert isinstance(summary, str)
        assert "Dr. Jane Smith" in summary
        assert "ethics_officer" in summary
        assert "ALLOW" in summary
        assert "DENY" in summary

    def test_get_override_summary_returns_none_before_override(self, override_handler, sample_decision):
        """Test get_override_summary returns None for unmodified decision"""
        summary = override_handler.get_override_summary(sample_decision)
        assert summary is None


class TestEscalationHandling:
    """Test handling of escalation status during overrides."""

    def test_override_to_escalate_sets_escalated_flag(self, override_handler, sample_decision):
        """Test that overriding to ESCALATE sets decision.escalated=True"""
        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_12345",
            proposed_outcome=OverrideOutcome.ESCALATE,
            justification="This case requires escalation to human review."
        )

        updated_decision = override_handler.apply_override(sample_decision, request)

        assert updated_decision.escalated is True
        assert updated_decision.governance_outcome["verdict"] == "ESCALATE"

    def test_override_from_escalate_keeps_escalated_flag(self, override_handler, sample_decision):
        """Test that overriding from ESCALATE keeps escalated=True"""
        # Set up decision as escalated
        sample_decision.governance_outcome["verdict"] = "ESCALATE"
        sample_decision.escalated = True

        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_12345",
            original_outcome="ESCALATE",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="After human review, this case can be allowed."
        )

        updated_decision = override_handler.apply_override(sample_decision, request)

        # Escalated flag should remain True (human resolved it)
        assert updated_decision.escalated is True
        assert updated_decision.governance_outcome["verdict"] == "ALLOW"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_apply_override_convenience_function(self, sample_decision, sample_override_request):
        """Test apply_override convenience function works"""
        updated_decision = apply_override(sample_decision, sample_override_request)

        assert updated_decision.governance_outcome["verdict"] == "DENY"
        assert updated_decision.governance_outcome["human_modified"] is True

    def test_apply_override_preserves_original_by_default(self, sample_decision, sample_override_request):
        """Test apply_override preserves original by default"""
        original_verdict = sample_decision.governance_outcome["verdict"]
        updated_decision = apply_override(sample_decision, sample_override_request)

        # Original should be unchanged
        assert sample_decision.governance_outcome["verdict"] == original_verdict
        # Updated should be changed
        assert updated_decision.governance_outcome["verdict"] == "DENY"

    def test_apply_override_can_modify_in_place(self, sample_decision, sample_override_request):
        """Test apply_override can modify in-place when requested"""
        updated_decision = apply_override(sample_decision, sample_override_request, preserve_original=False)

        # Should be same object
        assert updated_decision is sample_decision
        assert sample_decision.governance_outcome["verdict"] == "DENY"

    def test_validate_override_convenience_function_valid(self, sample_decision, sample_override_request):
        """Test validate_override convenience function for valid request"""
        is_valid = validate_override(sample_decision, sample_override_request)
        assert is_valid is True

    def test_validate_override_convenience_function_invalid(self, sample_decision):
        """Test validate_override convenience function for invalid request"""
        invalid_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_WRONG",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Invalid request for testing validation."
        )

        is_valid = validate_override(sample_decision, invalid_request)
        assert is_valid is False


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_override_to_same_outcome_allowed(self, override_handler, sample_decision):
        """Test that overriding to the same outcome is allowed (no-op override)"""
        # This might happen if justification needs to be added
        # Note: The OverrideRequest model validator prevents same outcome if original_outcome is set
        # But if original_outcome is not set, it should work
        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_12345",
            # Don't set original_outcome
            proposed_outcome=OverrideOutcome.ALLOW,  # Same as current
            justification="Adding justification for why ALLOW is still correct after review."
        )

        updated_decision = override_handler.apply_override(sample_decision, request)

        assert updated_decision.governance_outcome["verdict"] == "ALLOW"
        assert updated_decision.governance_outcome["human_modified"] is True

    def test_multiple_overrides_possible(self, override_handler, sample_decision):
        """Test that a decision can be overridden multiple times"""
        # First override
        request1 = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_12345",
            proposed_outcome=OverrideOutcome.DENY,
            justification="First override: changing to DENY."
        )

        decision1 = override_handler.apply_override(sample_decision, request1)
        assert decision1.governance_outcome["verdict"] == "DENY"

        # Second override (on the already-overridden decision)
        request2 = OverrideRequest(
            reviewer_id="reviewer_002",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_12345",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="Second override: further review needed."
        )

        decision2 = override_handler.apply_override(decision1, request2)
        assert decision2.governance_outcome["verdict"] == "REVIEW"
        assert decision2.governance_outcome["human_modified"] is True

        # Most recent override metadata should be present
        metadata = decision2.governance_outcome["override"]
        assert metadata["override_by"]["reviewer_id"] == "reviewer_002"

    def test_override_with_minimal_decision_structure(self, override_handler):
        """Test override works with minimal decision structure"""
        minimal_decision = Decision(
            decision_id="dec_minimal",
            input_data={},
            critic_reports=[],
            aggregation={},
            governance_outcome={"verdict": "REVIEW"}  # Minimal governance_outcome
        )

        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_minimal",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Overriding minimal decision structure for testing."
        )

        updated_decision = override_handler.apply_override(minimal_decision, request)

        assert updated_decision.governance_outcome["verdict"] == "ALLOW"
        assert updated_decision.governance_outcome["human_modified"] is True

    def test_override_with_future_expiration(self, override_handler, sample_decision):
        """Test override with future expiration is accepted"""
        request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_12345",
            proposed_outcome=OverrideOutcome.ESCALATE,
            justification="Override with future expiration should be accepted.",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        # Should not raise
        updated_decision = override_handler.apply_override(sample_decision, request)
        assert updated_decision.governance_outcome["verdict"] == "ESCALATE"

    def test_override_all_outcome_types(self, override_handler, sample_decision):
        """Test that all outcome types can be applied"""
        outcomes = [
            OverrideOutcome.ALLOW,
            OverrideOutcome.DENY,
            OverrideOutcome.REVIEW,
            OverrideOutcome.ESCALATE
        ]

        for outcome in outcomes:
            request = OverrideRequest(
                reviewer_id="reviewer_001",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER,
                decision_id="dec_12345",
                proposed_outcome=outcome,
                justification=f"Testing override to {outcome.value}."
            )

            decision_copy = deepcopy(sample_decision)
            updated_decision = override_handler.apply_override(decision_copy, request)

            assert updated_decision.governance_outcome["verdict"] == outcome.value
            assert updated_decision.governance_outcome["human_modified"] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
