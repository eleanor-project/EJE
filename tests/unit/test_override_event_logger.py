"""
Unit tests for Override Event Logger - Task 7.3

Tests the override event logging functionality including:
- Event bundle creation
- Audit trail integration
- Reviewer identity capture
- Timestamp tracking
- Reasoning capture
- Original vs overridden decision tracking
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from ejc.core.decision import Decision
from ejc.core.governance.override_request import (
    OverrideRequest,
    OverrideOutcome,
    OverrideReason,
    ReviewerRole
)
from ejc.core.governance.override_event_logger import (
    create_override_event_bundle,
    log_override_event,
    log_override_event_simple
)


class TestCreateOverrideEventBundle:
    """Test event bundle creation."""

    def test_bundle_includes_event_type(self):
        """Event bundle should include event_type field."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ALLOW"
        )

        bundle = create_override_event_bundle(decision, override_request)

        assert "event_type" in bundle
        assert bundle["event_type"] == "override_applied"

    def test_bundle_includes_reviewer_identity(self):
        """Event bundle should include complete reviewer identity (Task 7.3)."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            reviewer_name="Dr. Jane Smith",
            reviewer_email="jane.smith@example.com",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            original_outcome="ALLOW"
        )

        bundle = create_override_event_bundle(decision, override_request)

        # Task 7.3 requirement: Reviewer identity
        assert "reviewer" in bundle
        assert bundle["reviewer"]["reviewer_id"] == "reviewer_1"
        assert bundle["reviewer"]["reviewer_name"] == "Dr. Jane Smith"
        assert bundle["reviewer"]["reviewer_email"] == "jane.smith@example.com"
        assert bundle["reviewer"]["reviewer_role"] == "ethics_officer"

    def test_bundle_includes_timestamps(self):
        """Event bundle should include all relevant timestamps (Task 7.3)."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp="2025-01-01T10:00:00"
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ALLOW"
        )

        applied_at = datetime(2025, 1, 1, 11, 0, 0)
        bundle = create_override_event_bundle(decision, override_request, applied_at)

        # Task 7.3 requirement: Timestamp
        assert "timestamp" in bundle
        assert "override_request_timestamp" in bundle
        assert "override_applied_timestamp" in bundle
        assert bundle["override_applied_timestamp"] == "2025-01-01T11:00:00"

    def test_bundle_includes_reasoning(self):
        """Event bundle should include reasoning and justification (Task 7.3)."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        justification_text = "After careful review of the case specifics and stakeholder input"
        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification=justification_text,
            reason_category=OverrideReason.POLICY_EXCEPTION,
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ALLOW"
        )

        bundle = create_override_event_bundle(decision, override_request)

        # Task 7.3 requirement: Reasoning
        assert "justification" in bundle
        assert bundle["justification"] == justification_text
        assert "reason_category" in bundle
        assert bundle["reason_category"] == "policy_exception"

    def test_bundle_includes_outcome_change(self):
        """Event bundle should track original vs overridden decision (Task 7.3)."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "DENY"},  # After override
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ALLOW"
        )

        bundle = create_override_event_bundle(decision, override_request)

        # Task 7.3 requirement: Original vs overridden decision
        assert "outcome_change" in bundle
        assert bundle["outcome_change"]["original_outcome"] == "ALLOW"
        assert bundle["outcome_change"]["proposed_outcome"] == "DENY"
        assert bundle["outcome_change"]["current_outcome"] == "DENY"

    def test_bundle_includes_decision_reference(self):
        """Event bundle should reference the decision being overridden."""
        decision_id = "dec_special_123"
        decision = Decision(
            decision_id=decision_id,
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp="2025-01-01T10:00:00"
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id=decision_id,
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        bundle = create_override_event_bundle(decision, override_request)

        assert "decision_id" in bundle
        assert bundle["decision_id"] == decision_id
        assert "decision_timestamp" in bundle
        assert bundle["decision_timestamp"] == "2025-01-01T10:00:00"

    def test_bundle_includes_metadata(self):
        """Event bundle should include additional metadata."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            is_urgent=True,
            priority=8,
            supporting_documents=["doc1.pdf", "doc2.pdf"],
            stakeholder_input="Stakeholder feedback here"
        )

        bundle = create_override_event_bundle(decision, override_request)

        assert "metadata" in bundle
        assert bundle["metadata"]["is_urgent"] is True
        assert bundle["metadata"]["priority"] == 8
        assert bundle["metadata"]["supporting_documents"] == ["doc1.pdf", "doc2.pdf"]
        assert bundle["metadata"]["stakeholder_input"] == "Stakeholder feedback here"

    def test_bundle_includes_escalation_status(self):
        """Event bundle should track escalation status."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "ESCALATE"},
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ESCALATE"
        )

        bundle = create_override_event_bundle(decision, override_request)

        assert "escalation_status" in bundle
        assert bundle["escalation_status"]["decision_escalated"] is True
        assert bundle["escalation_status"]["override_from_escalate"] is True

    def test_bundle_includes_decision_snapshot(self):
        """Event bundle should include snapshot of decision for forensics."""
        critic_reports = [
            {"critic": "safety", "verdict": "ALLOW"},
            {"critic": "ethics", "verdict": "DENY"}
        ]
        precedents = [{"id": "prec_1"}, {"id": "prec_2"}]

        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=critic_reports,
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "REVIEW"},
            precedents=precedents,
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        bundle = create_override_event_bundle(decision, override_request)

        assert "decision_snapshot" in bundle
        assert bundle["decision_snapshot"]["critic_count"] == 2
        assert bundle["decision_snapshot"]["precedent_count"] == 2

    def test_bundle_includes_required_audit_fields(self):
        """Event bundle should include fields required by SignedAuditLogger."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        bundle = create_override_event_bundle(decision, override_request)

        # SignedAuditLogger requires 'request_id' and 'timestamp'
        assert "request_id" in bundle
        assert "timestamp" in bundle
        assert bundle["request_id"] == "dec_123"


class TestLogOverrideEvent:
    """Test override event logging to audit trail."""

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_log_override_event_calls_audit_logger(self, mock_audit_log):
        """log_override_event should call the audit logger."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="ALLOW"
        )

        log_override_event(decision, override_request)

        # Verify audit logger was called
        assert mock_audit_log.called
        assert mock_audit_log.call_count == 1

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_log_override_event_returns_bundle(self, mock_audit_log):
        """log_override_event should return the event bundle."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        result = log_override_event(decision, override_request)

        assert isinstance(result, dict)
        assert result["event_type"] == "override_applied"
        assert result["decision_id"] == "dec_123"

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_log_override_event_uses_custom_timestamp(self, mock_audit_log):
        """log_override_event should accept custom applied timestamp."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        custom_time = datetime(2025, 6, 15, 14, 30, 0)
        result = log_override_event(decision, override_request, custom_time)

        assert result["override_applied_timestamp"] == "2025-06-15T14:30:00"

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_log_override_event_with_complete_request(self, mock_audit_log):
        """log_override_event should handle complete override requests."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            reviewer_name="Dr. Jane Smith",
            reviewer_email="jane.smith@example.com",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            justification="Complete justification with all details provided",
            reason_category=OverrideReason.ETHICAL_CONCERN,
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            original_outcome="ALLOW",
            is_urgent=True,
            priority=9,
            supporting_documents=["ethics_review.pdf"],
            stakeholder_input="Board expressed concerns"
        )

        result = log_override_event(decision, override_request)

        assert result["reviewer"]["reviewer_name"] == "Dr. Jane Smith"
        assert result["reviewer"]["reviewer_email"] == "jane.smith@example.com"
        assert result["reason_category"] == "ethical_concern"
        assert result["metadata"]["is_urgent"] is True
        assert result["metadata"]["priority"] == 9

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_log_override_event_raises_on_audit_failure(self, mock_audit_log):
        """log_override_event should raise if audit logging fails."""
        mock_audit_log.side_effect = Exception("Audit logging failed")

        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        with pytest.raises(Exception, match="Audit logging failed"):
            log_override_event(decision, override_request)


class TestLogOverrideEventSimple:
    """Test simplified override event logging."""

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_simple_logging_creates_event(self, mock_audit_log):
        """log_override_event_simple should create and log event."""
        result = log_override_event_simple(
            decision_id="dec_123",
            reviewer_id="reviewer_1",
            reviewer_name="Jane Smith",
            reviewer_role="ethics_officer",
            original_outcome="ALLOW",
            new_outcome="DENY",
            justification="Simple justification"
        )

        assert result["event_type"] == "override_applied"
        assert result["decision_id"] == "dec_123"
        assert result["reviewer"]["reviewer_id"] == "reviewer_1"
        assert result["outcome_change"]["original_outcome"] == "ALLOW"
        assert result["outcome_change"]["proposed_outcome"] == "DENY"
        assert mock_audit_log.called

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_simple_logging_with_reason_category(self, mock_audit_log):
        """log_override_event_simple should accept reason category."""
        result = log_override_event_simple(
            decision_id="dec_123",
            reviewer_id="reviewer_1",
            reviewer_name="Jane Smith",
            reviewer_role="ethics_officer",
            original_outcome="ALLOW",
            new_outcome="DENY",
            justification="Simple justification",
            reason_category="policy_exception"
        )

        assert result["reason_category"] == "policy_exception"

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_simple_logging_default_reason(self, mock_audit_log):
        """log_override_event_simple should default to 'other' reason."""
        result = log_override_event_simple(
            decision_id="dec_123",
            reviewer_id="reviewer_1",
            reviewer_name=None,
            reviewer_role="auditor",
            original_outcome="DENY",
            new_outcome="ALLOW",
            justification="Simple justification"
        )

        assert result["reason_category"] == "other"


class TestEventBundleIntegrity:
    """Test event bundle structure and integrity."""

    def test_all_task_requirements_present(self):
        """Event bundle should include all Task 7.3 requirements."""
        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            reviewer_name="Dr. Smith",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            justification="Complete justification explaining the override decision",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            original_outcome="ALLOW"
        )

        bundle = create_override_event_bundle(decision, override_request)

        # Verify all Task 7.3 requirements
        # 1. Reviewer identity
        assert "reviewer" in bundle
        assert bundle["reviewer"]["reviewer_id"] == "reviewer_1"

        # 2. Timestamp
        assert "timestamp" in bundle
        assert "override_applied_timestamp" in bundle

        # 3. Reasoning
        assert "justification" in bundle
        assert len(bundle["justification"]) > 0

        # 4. Original vs overridden decision
        assert "outcome_change" in bundle
        assert bundle["outcome_change"]["original_outcome"] == "ALLOW"
        assert bundle["outcome_change"]["proposed_outcome"] == "DENY"

    def test_bundle_serializable_to_json(self):
        """Event bundle should be JSON serializable."""
        import json

        decision = Decision(
            decision_id="dec_123",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_1",
            justification="Valid justification for testing purposes",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec_123",
            reviewer_role=ReviewerRole.ETHICS_OFFICER
        )

        bundle = create_override_event_bundle(decision, override_request)

        # Should be able to serialize to JSON without errors
        json_str = json.dumps(bundle)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Should be able to deserialize
        deserialized = json.loads(json_str)
        assert deserialized["event_type"] == "override_applied"


class TestIntegrationScenarios:
    """Test complete override logging scenarios."""

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_full_override_workflow_logging(self, mock_audit_log):
        """Test logging a complete override workflow."""
        # 1. Create original decision
        decision = Decision(
            decision_id="dec_prod_001",
            input_data={"query": "test query"},
            critic_reports=[
                {"critic": "safety", "verdict": "ALLOW", "confidence": 0.8},
                {"critic": "ethics", "verdict": "ALLOW", "confidence": 0.7}
            ],
            aggregation={"verdict": "ALLOW", "confidence": 0.75},
            governance_outcome={"verdict": "ALLOW"},
            precedents=[{"id": "prec_1"}],
            timestamp="2025-01-15T10:00:00"
        )

        # 2. Create override request
        override_request = OverrideRequest(
            reviewer_id="ethics_officer_jane",
            reviewer_name="Dr. Jane Smith",
            reviewer_email="jane.smith@org.com",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_prod_001",
            original_outcome="ALLOW",
            proposed_outcome=OverrideOutcome.DENY,
            justification="After thorough ethical review, this decision poses risks not captured by automated critics",
            reason_category=OverrideReason.ETHICAL_CONCERN,
            is_urgent=True,
            priority=8,
            supporting_documents=["ethical_analysis_v2.pdf"],
            stakeholder_input="Ethics board recommended denial"
        )

        # 3. Log override event
        event = log_override_event(decision, override_request)

        # 4. Verify complete audit trail
        assert event["decision_id"] == "dec_prod_001"
        assert event["reviewer"]["reviewer_id"] == "ethics_officer_jane"
        assert event["outcome_change"]["original_outcome"] == "ALLOW"
        assert event["outcome_change"]["proposed_outcome"] == "DENY"
        assert event["reason_category"] == "ethical_concern"
        assert event["metadata"]["is_urgent"] is True
        assert mock_audit_log.called

    @patch('ejc.core.governance.override_event_logger.write_signed_audit_log')
    def test_escalation_override_logging(self, mock_audit_log):
        """Test logging an override that involves escalation."""
        decision = Decision(
            decision_id="dec_esc_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "ESCALATE"},
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="senior_reviewer",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            decision_id="dec_esc_001",
            original_outcome="ESCALATE",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Board reviewed escalated case and approves with conditions"
        )

        event = log_override_event(decision, override_request)

        assert event["escalation_status"]["decision_escalated"] is True
        assert event["escalation_status"]["override_from_escalate"] is True
        assert event["outcome_change"]["original_outcome"] == "ESCALATE"
        assert event["outcome_change"]["proposed_outcome"] == "ALLOW"
