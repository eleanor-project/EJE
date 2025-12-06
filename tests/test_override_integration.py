"""
Integration Tests for Task 7.4: Override System

Comprehensive integration tests for the complete override workflow:
- Valid override flows (Tasks 7.1 + 7.2 + 7.3)
- Invalid override scenarios
- Multiple override attempts
- Audit propagation

These tests verify end-to-end override behavior from request creation
through handler application to audit logging.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

from src.ejc.core.decision import Decision
from src.ejc.core.governance.override_request import (
    OverrideRequest,
    OverrideOutcome,
    OverrideReason,
    ReviewerRole,
    OverrideRequestBatch
)
from src.ejc.core.governance.override_handler import (
    OverrideHandler,
    OverrideValidationError,
    apply_override,
    validate_override
)
from src.ejc.core.governance.override_event_logger import (
    log_override_event,
    log_override_event_simple,
    create_override_event_bundle
)


class TestValidOverrideFlow:
    """
    Task 7.4: Test valid override flows end-to-end

    Tests the complete workflow from override request creation through
    handler application to audit logging.
    """

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_complete_valid_override_workflow(self, mock_audit_log):
        """
        Test complete valid override workflow: Request → Handler → Logger → Audit

        This is the primary integration test verifying the full override pipeline.
        """
        # Step 1: Create original decision
        original_decision = Decision(
            decision_id="dec_integration_001",
            input_data={"query": "Test query for integration"},
            critic_reports=[
                {"critic": "safety", "verdict": "DENY", "confidence": 0.8},
                {"critic": "ethics", "verdict": "DENY", "confidence": 0.7}
            ],
            aggregation={"verdict": "DENY", "confidence": 0.75},
            governance_outcome={"verdict": "DENY"},
            precedents=[],
            timestamp=datetime.utcnow().isoformat()
        )

        # Step 2: Create override request (Task 7.1)
        override_request = OverrideRequest(
            reviewer_id="integration_reviewer_001",
            reviewer_name="Integration Test Reviewer",
            reviewer_email="integration@test.com",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_integration_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Integration test: After detailed review, this decision should be allowed",
            reason_category=OverrideReason.POLICY_EXCEPTION,
            is_urgent=False,
            priority=5
        )

        # Validate request was created properly
        assert override_request.reviewer_id == "integration_reviewer_001"
        assert override_request.proposed_outcome == OverrideOutcome.ALLOW

        # Step 3: Apply override using handler (Task 7.2)
        handler = OverrideHandler(preserve_original=True)
        updated_decision = handler.apply_override(original_decision, override_request)

        # Verify decision was updated
        assert updated_decision.governance_outcome["verdict"] == "ALLOW"
        assert updated_decision.governance_outcome["human_modified"] is True
        assert "override" in updated_decision.governance_outcome

        # Verify override metadata
        override_meta = updated_decision.governance_outcome["override"]
        assert override_meta["override_by"]["reviewer_id"] == "integration_reviewer_001"
        assert override_meta["original_outcome"] == "DENY"
        assert override_meta["proposed_outcome"] == "ALLOW"

        # Step 4: Log override event (Task 7.3)
        event_bundle = log_override_event(updated_decision, override_request)

        # Verify event bundle was created
        assert event_bundle["event_type"] == "override_applied"
        assert event_bundle["decision_id"] == "dec_integration_001"
        assert event_bundle["reviewer"]["reviewer_id"] == "integration_reviewer_001"
        assert event_bundle["outcome_change"]["original_outcome"] == "DENY"
        assert event_bundle["outcome_change"]["proposed_outcome"] == "ALLOW"

        # Step 5: Verify audit logging was called (Task 7.4: Audit propagation)
        assert mock_audit_log.called
        assert mock_audit_log.call_count == 1

        # Verify the wrapper passed to audit logger has correct structure
        call_args = mock_audit_log.call_args[0][0]
        assert hasattr(call_args, 'to_dict')
        logged_data = call_args.to_dict()
        assert logged_data["event_type"] == "override_applied"
        assert logged_data["decision_id"] == "dec_integration_001"

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_override_with_escalation(self, mock_audit_log):
        """Test override workflow when decision is escalated"""
        # Create escalated decision
        decision = Decision(
            decision_id="dec_escalated_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "ESCALATE"},
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        # Override from ESCALATE to ALLOW
        override_request = OverrideRequest(
            reviewer_id="senior_reviewer",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_escalated_001",
            original_outcome="ESCALATE",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Board reviewed and approved the escalated case"
        )

        # Apply override
        handler = OverrideHandler()
        updated_decision = handler.apply_override(decision, override_request)

        # Verify escalated flag remains true (human resolved it)
        assert updated_decision.escalated is True
        assert updated_decision.governance_outcome["verdict"] == "ALLOW"

        # Log event
        event = log_override_event(updated_decision, override_request)

        # Verify escalation tracking in event
        assert event["escalation_status"]["decision_escalated"] is True
        assert event["escalation_status"]["override_from_escalate"] is True
        assert mock_audit_log.called

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_override_with_all_metadata(self, mock_audit_log):
        """Test override with complete metadata and supporting information"""
        decision = Decision(
            decision_id="dec_complete_001",
            input_data={"complex": "case"},
            critic_reports=[
                {"critic": "safety", "verdict": "DENY"},
                {"critic": "ethics", "verdict": "ALLOW"},
                {"critic": "privacy", "verdict": "DENY"}
            ],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            precedents=[{"id": "prec_1"}, {"id": "prec_2"}],
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="complete_reviewer",
            reviewer_name="Dr. Complete Reviewer",
            reviewer_email="complete@example.com",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_complete_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Complete justification with all supporting information and detailed reasoning",
            reason_category=OverrideReason.STAKEHOLDER_INPUT,
            is_urgent=True,
            priority=9,
            supporting_documents=["review.pdf", "stakeholder_input.docx"],
            stakeholder_input="Multiple stakeholders provided input supporting approval",
            additional_context={"review_type": "comprehensive", "duration_hours": 4}
        )

        # Apply and log
        handler = OverrideHandler()
        updated_decision = handler.apply_override(decision, override_request)
        event = log_override_event(updated_decision, override_request)

        # Verify all metadata is captured
        assert event["metadata"]["is_urgent"] is True
        assert event["metadata"]["priority"] == 9
        assert "review.pdf" in event["metadata"]["supporting_documents"]
        assert "stakeholder_input.docx" in event["metadata"]["supporting_documents"]
        assert event["metadata"]["stakeholder_input"] == "Multiple stakeholders provided input supporting approval"
        assert event["metadata"]["additional_context"]["review_type"] == "comprehensive"
        assert mock_audit_log.called


class TestInvalidOverrideScenarios:
    """
    Task 7.4: Test invalid override scenarios

    Tests various invalid override attempts and verifies proper error handling.
    """

    def test_expired_override_request(self):
        """Test that expired override requests are rejected"""
        decision = Decision(
            decision_id="dec_expired_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        # Create request that expires in the past
        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_expired_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="This request has expired and should be rejected"
        )

        # Manually set expiration to past (bypass Pydantic validation)
        past_time = datetime.utcnow() - timedelta(hours=1)
        object.__setattr__(override_request, 'expires_at', past_time)

        # Attempt to apply - should raise OverrideValidationError
        handler = OverrideHandler()
        with pytest.raises(OverrideValidationError, match="expired"):
            handler.apply_override(decision, override_request)

    def test_mismatched_decision_id(self):
        """Test that mismatched decision IDs are rejected"""
        decision = Decision(
            decision_id="dec_correct_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        # Create request with wrong decision ID
        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_wrong_001",  # Wrong ID!
            proposed_outcome=OverrideOutcome.DENY,
            justification="This should be rejected due to mismatched decision ID"
        )

        # Should raise validation error
        handler = OverrideHandler()
        with pytest.raises(OverrideValidationError, match="does not match"):
            handler.apply_override(decision, override_request)

    def test_mismatched_original_outcome(self):
        """Test that mismatched original outcomes are rejected"""
        decision = Decision(
            decision_id="dec_mismatch_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},  # Actually ALLOW
            timestamp=datetime.utcnow().isoformat()
        )

        # Request claims original was DENY but it's actually ALLOW
        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.LEGAL_COUNSEL,
            decision_id="dec_mismatch_001",
            original_outcome="DENY",  # Wrong!
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="This should be rejected due to original outcome mismatch"
        )

        # Should raise validation error
        handler = OverrideHandler()
        with pytest.raises(OverrideValidationError, match="expects original outcome"):
            handler.apply_override(decision, override_request)

    def test_validate_only_detects_errors(self):
        """Test that validate_only method correctly detects invalid overrides"""
        decision = Decision(
            decision_id="dec_validate_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        # Valid request
        valid_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_validate_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Valid override request for testing"
        )

        # Invalid request (wrong decision ID)
        invalid_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_wrong_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Invalid override request for testing"
        )

        handler = OverrideHandler()

        # Valid should pass
        assert handler.validate_only(decision, valid_request) is True

        # Invalid should fail
        assert handler.validate_only(decision, invalid_request) is False

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_audit_logging_failure_propagates(self, mock_audit_log):
        """Test that audit logging failures are properly propagated"""
        mock_audit_log.side_effect = Exception("Audit system unavailable")

        decision = Decision(
            decision_id="dec_audit_fail_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_audit_fail_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Testing audit failure handling"
        )

        # Override should apply successfully
        handler = OverrideHandler()
        updated_decision = handler.apply_override(decision, override_request)
        assert updated_decision.governance_outcome["verdict"] == "DENY"

        # But logging should raise
        with pytest.raises(Exception, match="Audit system unavailable"):
            log_override_event(updated_decision, override_request)


class TestMultipleOverrideAttempts:
    """
    Task 7.4: Test multiple override attempts on the same decision

    Tests scenarios where a decision is overridden multiple times.
    """

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_sequential_overrides_on_same_decision(self, mock_audit_log):
        """Test multiple sequential overrides on the same decision"""
        # Original decision: DENY
        decision = Decision(
            decision_id="dec_multi_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        handler = OverrideHandler(preserve_original=False)  # Modify in place

        # First override: DENY → ALLOW
        override_1 = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_multi_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="First override: changing to ALLOW"
        )

        decision = handler.apply_override(decision, override_1)
        event_1 = log_override_event(decision, override_1)

        assert decision.governance_outcome["verdict"] == "ALLOW"
        assert event_1["outcome_change"]["original_outcome"] == "DENY"
        assert event_1["outcome_change"]["proposed_outcome"] == "ALLOW"

        # Second override: ALLOW → REVIEW
        override_2 = OverrideRequest(
            reviewer_id="reviewer_002",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_multi_001",
            original_outcome="ALLOW",  # Now ALLOW is the original
            proposed_outcome=OverrideOutcome.REVIEW,
            justification="Second override: escalating to REVIEW"
        )

        decision = handler.apply_override(decision, override_2)
        event_2 = log_override_event(decision, override_2)

        assert decision.governance_outcome["verdict"] == "REVIEW"
        assert event_2["outcome_change"]["original_outcome"] == "ALLOW"
        assert event_2["outcome_change"]["proposed_outcome"] == "REVIEW"

        # Third override: REVIEW → ESCALATE
        override_3 = OverrideRequest(
            reviewer_id="reviewer_003",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_multi_001",
            original_outcome="REVIEW",
            proposed_outcome=OverrideOutcome.ESCALATE,
            justification="Third override: requires governance board review"
        )

        decision = handler.apply_override(decision, override_3)
        event_3 = log_override_event(decision, override_3)

        assert decision.governance_outcome["verdict"] == "ESCALATE"
        assert decision.escalated is True
        assert event_3["outcome_change"]["proposed_outcome"] == "ESCALATE"

        # Verify audit log was called 3 times
        assert mock_audit_log.call_count == 3

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_batch_override_requests(self, mock_audit_log):
        """Test processing a batch of override requests"""
        # Create multiple decisions
        decisions = [
            Decision(
                decision_id=f"dec_batch_{i:03d}",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "DENY"},
                governance_outcome={"verdict": "DENY"},
                timestamp=datetime.utcnow().isoformat()
            )
            for i in range(3)
        ]

        # Create batch of override requests
        override_requests = [
            OverrideRequest(
                reviewer_id="batch_reviewer",
                reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
                decision_id=f"dec_batch_{i:03d}",
                original_outcome="DENY",
                proposed_outcome=OverrideOutcome.ALLOW,
                justification=f"Batch override {i}: approval after review"
            )
            for i in range(3)
        ]

        batch = OverrideRequestBatch(
            requests=override_requests,
            batch_submitted_by="batch_reviewer"
        )

        assert batch.get_request_count() == 3

        # Process batch
        handler = OverrideHandler()
        updated_decisions = []

        for decision, request in zip(decisions, batch.requests):
            updated = handler.apply_override(decision, request)
            log_override_event(updated, request)
            updated_decisions.append(updated)

        # Verify all were processed
        assert len(updated_decisions) == 3
        for dec in updated_decisions:
            assert dec.governance_outcome["verdict"] == "ALLOW"
            assert dec.governance_outcome["human_modified"] is True

        # Verify audit log called for each
        assert mock_audit_log.call_count == 3

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_override_metadata_preserved_across_multiple_changes(self, mock_audit_log):
        """Test that override metadata is updated with each override"""
        decision = Decision(
            decision_id="dec_meta_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        handler = OverrideHandler(preserve_original=False)

        # First override
        override_1 = OverrideRequest(
            reviewer_id="reviewer_first",
            reviewer_name="First Reviewer",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_meta_001",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="First override justification"
        )

        decision = handler.apply_override(decision, override_1)
        assert decision.governance_outcome["override"]["override_by"]["reviewer_id"] == "reviewer_first"

        # Second override - metadata should be updated
        override_2 = OverrideRequest(
            reviewer_id="reviewer_second",
            reviewer_name="Second Reviewer",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            decision_id="dec_meta_001",
            original_outcome="ALLOW",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Second override justification"
        )

        decision = handler.apply_override(decision, override_2)

        # Latest override metadata should reflect second reviewer
        assert decision.governance_outcome["override"]["override_by"]["reviewer_id"] == "reviewer_second"
        assert decision.governance_outcome["override"]["override_by"]["reviewer_name"] == "Second Reviewer"
        assert decision.governance_outcome["override"]["original_outcome"] == "ALLOW"
        assert decision.governance_outcome["override"]["proposed_outcome"] == "DENY"


class TestAuditPropagation:
    """
    Task 7.4: Test audit propagation

    Tests that override events are properly logged to the audit system
    with complete information.
    """

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_audit_receives_complete_event_bundle(self, mock_audit_log):
        """Test that audit system receives complete event bundle"""
        decision = Decision(
            decision_id="dec_audit_001",
            input_data={"test": "data"},
            critic_reports=[{"critic": "safety", "verdict": "DENY"}],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            precedents=[{"id": "prec_1"}],
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="audit_reviewer",
            reviewer_name="Audit Test Reviewer",
            reviewer_email="audit@test.com",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_audit_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Testing complete audit propagation",
            reason_category=OverrideReason.POLICY_EXCEPTION
        )

        handler = OverrideHandler()
        updated_decision = handler.apply_override(decision, override_request)
        log_override_event(updated_decision, override_request)

        # Verify audit was called
        assert mock_audit_log.called

        # Extract the event that was logged
        logged_wrapper = mock_audit_log.call_args[0][0]
        logged_event = logged_wrapper.to_dict()

        # Verify all required fields are present
        assert logged_event["event_type"] == "override_applied"
        assert logged_event["decision_id"] == "dec_audit_001"

        # Reviewer identity (Task 7.3)
        assert logged_event["reviewer"]["reviewer_id"] == "audit_reviewer"
        assert logged_event["reviewer"]["reviewer_name"] == "Audit Test Reviewer"
        assert logged_event["reviewer"]["reviewer_email"] == "audit@test.com"
        assert logged_event["reviewer"]["reviewer_role"] == "auditor"

        # Timestamps (Task 7.3)
        assert "timestamp" in logged_event
        assert "override_request_timestamp" in logged_event
        assert "override_applied_timestamp" in logged_event

        # Reasoning (Task 7.3)
        assert logged_event["justification"] == "Testing complete audit propagation"
        assert logged_event["reason_category"] == "policy_exception"

        # Outcome change (Task 7.3)
        assert logged_event["outcome_change"]["original_outcome"] == "DENY"
        assert logged_event["outcome_change"]["proposed_outcome"] == "ALLOW"

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_simple_logging_propagates_to_audit(self, mock_audit_log):
        """Test that simple logging also propagates to audit system"""
        log_override_event_simple(
            decision_id="dec_simple_001",
            reviewer_id="simple_reviewer",
            reviewer_name="Simple Reviewer",
            reviewer_role="senior_reviewer",
            original_outcome="DENY",
            new_outcome="ALLOW",
            justification="Simple logging test",
            reason_category="other"
        )

        # Verify audit was called
        assert mock_audit_log.called
        logged_wrapper = mock_audit_log.call_args[0][0]
        logged_event = logged_wrapper.to_dict()

        assert logged_event["event_type"] == "override_applied"
        assert logged_event["decision_id"] == "dec_simple_001"
        assert logged_event["reviewer"]["reviewer_id"] == "simple_reviewer"
        assert logged_event["outcome_change"]["original_outcome"] == "DENY"
        assert logged_event["outcome_change"]["proposed_outcome"] == "ALLOW"

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_audit_called_with_serializable_data(self, mock_audit_log):
        """Test that data sent to audit is JSON serializable"""
        import json

        decision = Decision(
            decision_id="dec_serialize_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="serialization_test",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_serialize_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Testing JSON serialization of audit data"
        )

        handler = OverrideHandler()
        updated_decision = handler.apply_override(decision, override_request)
        log_override_event(updated_decision, override_request)

        # Extract logged data
        logged_wrapper = mock_audit_log.call_args[0][0]
        logged_event = logged_wrapper.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(logged_event)
        assert isinstance(json_str, str)

        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized["event_type"] == "override_applied"


class TestEdgeCasesAndIntegration:
    """Additional edge cases and integration scenarios"""

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_convenience_functions_work_end_to_end(self, mock_audit_log):
        """Test that convenience functions work in integration"""
        decision = Decision(
            decision_id="dec_convenience_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="convenience_reviewer",
            reviewer_role=ReviewerRole.LEGAL_COUNSEL,
            decision_id="dec_convenience_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Testing convenience functions in integration"
        )

        # Test validate_override convenience function
        is_valid = validate_override(decision, override_request)
        assert is_valid is True

        # Test apply_override convenience function
        updated = apply_override(decision, override_request, preserve_original=True)
        assert updated.governance_outcome["verdict"] == "ALLOW"

        # Test logging
        log_override_event(updated, override_request)
        assert mock_audit_log.called

    @patch('src.ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_full_workflow_with_helper_methods(self, mock_audit_log):
        """Test full workflow using handler helper methods"""
        decision = Decision(
            decision_id="dec_helpers_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="helper_reviewer",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_helpers_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Testing helper methods in integration"
        )

        handler = OverrideHandler()

        # Check if already overridden (should be False)
        assert handler.has_been_overridden(decision) is False
        assert handler.get_override_metadata(decision) is None
        assert handler.get_override_summary(decision) is None

        # Apply override
        updated = handler.apply_override(decision, override_request)

        # Check if overridden (should be True)
        assert handler.has_been_overridden(updated) is True
        assert handler.get_override_metadata(updated) is not None

        # Get summary
        summary = handler.get_override_summary(updated)
        assert "helper_reviewer" in summary
        assert "ALLOW" in summary
        assert "DENY" in summary
