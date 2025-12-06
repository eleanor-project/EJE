"""
Integration Tests for Override Workflow

Tests the integration of the override system with the decision pipeline,
including complete workflows, batch processing, and helper utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.ejc.core.decision import Decision
from src.ejc.core.governance.override_workflow import (
    apply_decision_override,
    apply_batch_overrides,
    get_escalated_decisions,
    create_override_from_review,
    get_override_summary_for_decision
)
from src.ejc.core.governance.override_request import (
    OverrideRequest,
    OverrideOutcome,
    OverrideReason,
    ReviewerRole,
    OverrideRequestBatch
)
from src.ejc.core.governance.override_handler import OverrideValidationError


class TestApplyDecisionOverride:
    """Test the main override workflow function."""

    @patch('src.ejc.core.governance.override_workflow.store_precedent_case')
    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_complete_override_workflow(
        self,
        mock_log_event,
        mock_audit_log,
        mock_store_precedent
    ):
        """Test complete override workflow with all steps."""
        # Create decision
        decision = Decision(
            decision_id="dec_workflow_001",
            input_data={"query": "test"},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        # Create override request
        override_request = OverrideRequest(
            reviewer_id="reviewer_workflow",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            decision_id="dec_workflow_001",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Complete workflow test with all integration points"
        )

        precedent_config = {"enabled": True, "backend": "memory"}

        # Apply override with full workflow
        result = apply_decision_override(
            decision,
            override_request,
            store_as_precedent=True,
            precedent_config=precedent_config,
            preserve_original=True
        )

        # Verify decision was updated
        assert result.governance_outcome["verdict"] == "ALLOW"
        assert result.governance_outcome["human_modified"] is True

        # Verify all workflow steps were called
        assert mock_log_event.called, "Override event should be logged"
        assert mock_audit_log.called, "Audit log should be updated"
        assert mock_store_precedent.called, "Precedent should be stored"

    @patch('src.ejc.core.governance.override_workflow.store_precedent_case')
    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_workflow_without_precedent_storage(
        self,
        mock_log_event,
        mock_audit_log,
        mock_store_precedent
    ):
        """Test workflow when precedent storage is disabled."""
        decision = Decision(
            decision_id="dec_no_prec_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            decision_id="dec_no_prec_001",
            proposed_outcome=OverrideOutcome.DENY,
            justification="Testing without precedent storage"
        )

        # Apply without precedent storage
        result = apply_decision_override(
            decision,
            override_request,
            store_as_precedent=False,
            preserve_original=True
        )

        assert result.governance_outcome["verdict"] == "DENY"
        assert mock_log_event.called
        assert mock_audit_log.called
        assert not mock_store_precedent.called, "Precedent should not be stored"

    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_workflow_handles_escalated_decision(
        self,
        mock_log_event,
        mock_audit_log
    ):
        """Test workflow with an escalated decision."""
        decision = Decision(
            decision_id="dec_escalated_001",
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
            decision_id="dec_escalated_001",
            original_outcome="ESCALATE",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Board resolved escalation with approval"
        )

        result = apply_decision_override(decision, override_request)

        assert result.governance_outcome["verdict"] == "ALLOW"
        assert result.escalated is True  # Remains True (human resolved it)
        assert mock_log_event.called
        assert mock_audit_log.called

    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_workflow_validation_error_propagates(
        self,
        mock_log_event,
        mock_audit_log
    ):
        """Test that validation errors are properly propagated."""
        decision = Decision(
            decision_id="dec_correct_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        # Wrong decision ID
        override_request = OverrideRequest(
            reviewer_id="reviewer_001",
            reviewer_role=ReviewerRole.AUDITOR,
            decision_id="dec_wrong_001",  # Mismatch!
            proposed_outcome=OverrideOutcome.DENY,
            justification="This should fail validation"
        )

        with pytest.raises(OverrideValidationError):
            apply_decision_override(decision, override_request)

        # Logging should not be called if validation fails
        assert not mock_log_event.called
        assert not mock_audit_log.called


class TestBatchOverrides:
    """Test batch override processing."""

    @patch('src.ejc.core.governance.override_workflow.store_precedent_case')
    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_successful_batch_processing(
        self,
        mock_log_event,
        mock_audit_log,
        mock_store_precedent
    ):
        """Test successful processing of a batch of overrides."""
        # Create 3 decisions
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
                reviewer_role=ReviewerRole.SENIOR_REVIEWER,
                decision_id=f"dec_batch_{i:03d}",
                original_outcome="DENY",
                proposed_outcome=OverrideOutcome.ALLOW,
                justification=f"Batch override {i}"
            )
            for i in range(3)
        ]

        batch = OverrideRequestBatch(
            requests=override_requests,
            batch_submitted_by="batch_reviewer"
        )

        # Process batch
        results = apply_batch_overrides(
            decisions,
            batch,
            store_as_precedent=False  # Simplify for test
        )

        # Verify results
        assert results["total_processed"] == 3
        assert results["success_count"] == 3
        assert results["failure_count"] == 0
        assert len(results["successful"]) == 3
        assert len(results["failed"]) == 0

        # Verify all decisions were updated
        for decision in results["successful"]:
            assert decision.governance_outcome["verdict"] == "ALLOW"

    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_batch_with_partial_failures(
        self,
        mock_log_event,
        mock_audit_log
    ):
        """Test batch processing with some failures."""
        # Create 2 decisions
        decisions = [
            Decision(
                decision_id="dec_batch_001",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "DENY"},
                governance_outcome={"verdict": "DENY"},
                timestamp=datetime.utcnow().isoformat()
            ),
            Decision(
                decision_id="dec_batch_002",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "ALLOW"},
                governance_outcome={"verdict": "ALLOW"},
                timestamp=datetime.utcnow().isoformat()
            )
        ]

        # Create requests where one has wrong decision ID
        override_requests = [
            OverrideRequest(
                reviewer_id="batch_reviewer",
                reviewer_role=ReviewerRole.TECHNICAL_LEAD,
                decision_id="dec_batch_001",
                proposed_outcome=OverrideOutcome.ALLOW,
                justification="Valid override"
            ),
            OverrideRequest(
                reviewer_id="batch_reviewer",
                reviewer_role=ReviewerRole.TECHNICAL_LEAD,
                decision_id="dec_batch_WRONG",  # This won't match
                proposed_outcome=OverrideOutcome.DENY,
                justification="Invalid override"
            )
        ]

        batch = OverrideRequestBatch(
            requests=override_requests,
            batch_submitted_by="batch_reviewer"
        )

        # Process batch with continue_on_error=True
        results = apply_batch_overrides(
            decisions,
            batch,
            continue_on_error=True,
            store_as_precedent=False
        )

        # Verify partial success
        assert results["total_processed"] == 2
        assert results["success_count"] == 1
        assert results["failure_count"] == 1
        assert len(results["successful"]) == 1
        assert len(results["failed"]) == 1

        # Verify failure details
        failed = results["failed"][0]
        assert failed["decision_id"] == "dec_batch_WRONG"
        assert "not found" in failed["error"]


class TestHelperFunctions:
    """Test helper utility functions."""

    def test_get_escalated_decisions(self):
        """Test filtering of escalated decisions."""
        decisions = [
            Decision(
                decision_id="dec_normal_001",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "ALLOW"},
                governance_outcome={"verdict": "ALLOW"},
                escalated=False,
                timestamp=datetime.utcnow().isoformat()
            ),
            Decision(
                decision_id="dec_escalated_001",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "REVIEW"},
                governance_outcome={"verdict": "ESCALATE"},
                escalated=True,
                timestamp=datetime.utcnow().isoformat()
            ),
            Decision(
                decision_id="dec_escalated_002",
                input_data={},
                critic_reports=[],
                aggregation={"verdict": "REVIEW"},
                governance_outcome={"verdict": "ESCALATE"},
                escalated=True,
                timestamp=datetime.utcnow().isoformat()
            )
        ]

        escalated = get_escalated_decisions(decisions)

        assert len(escalated) == 2
        assert all(d.escalated for d in escalated)

    def test_get_escalated_excludes_already_overridden(self):
        """Test that already overridden decisions are excluded by default."""
        # Create escalated decision that has been overridden
        overridden_decision = Decision(
            decision_id="dec_overridden_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={
                "verdict": "ALLOW",
                "human_modified": True,
                "override": {"override_id": "override_123"}
            },
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        # Create escalated decision that has not been overridden
        pending_decision = Decision(
            decision_id="dec_pending_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "ESCALATE"},
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        decisions = [overridden_decision, pending_decision]

        # Get escalated (should exclude already overridden by default)
        escalated = get_escalated_decisions(decisions, include_overridden=False)
        assert len(escalated) == 1
        assert escalated[0].decision_id == "dec_pending_001"

        # Get all escalated (including overridden)
        all_escalated = get_escalated_decisions(decisions, include_overridden=True)
        assert len(all_escalated) == 2

    def test_create_override_from_review(self):
        """Test convenience function for creating override requests."""
        decision = Decision(
            decision_id="dec_review_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={"verdict": "DENY"},
            timestamp=datetime.utcnow().isoformat()
        )

        request = create_override_from_review(
            decision,
            reviewer_id="reviewer_123",
            reviewer_role="ethics_officer",
            new_outcome="ALLOW",
            justification="After review, this should be allowed",
            reviewer_name="Dr. Smith",
            is_urgent=True
        )

        assert request.reviewer_id == "reviewer_123"
        assert request.reviewer_role == ReviewerRole.ETHICS_OFFICER
        assert request.decision_id == "dec_review_001"
        assert request.original_outcome == "DENY"
        assert request.proposed_outcome == OverrideOutcome.ALLOW
        assert request.justification == "After review, this should be allowed"
        assert request.reviewer_name == "Dr. Smith"
        assert request.is_urgent is True

    def test_create_override_from_review_invalid_outcome(self):
        """Test error handling for invalid outcome."""
        decision = Decision(
            decision_id="dec_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        with pytest.raises(ValueError, match="Invalid outcome"):
            create_override_from_review(
                decision,
                reviewer_id="reviewer_001",
                reviewer_role="auditor",
                new_outcome="INVALID_OUTCOME",
                justification="Test"
            )

    def test_create_override_from_review_invalid_role(self):
        """Test error handling for invalid reviewer role."""
        decision = Decision(
            decision_id="dec_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        with pytest.raises(ValueError, match="Invalid reviewer role"):
            create_override_from_review(
                decision,
                reviewer_id="reviewer_001",
                reviewer_role="invalid_role",
                new_outcome="DENY",
                justification="Test"
            )

    def test_get_override_summary_for_decision(self):
        """Test getting override summary from a decision."""
        # Create decision with override metadata
        decision = Decision(
            decision_id="dec_summary_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "DENY"},
            governance_outcome={
                "verdict": "ALLOW",
                "human_modified": True,
                "override": {
                    "override_id": "override_123",
                    "override_timestamp": "2025-01-15T10:30:00",
                    "override_by": {
                        "reviewer_id": "reviewer_001",
                        "reviewer_name": "Dr. Jane Smith",
                        "reviewer_role": "ethics_officer",
                        "reviewer_email": "jane@example.com"
                    },
                    "override_justification": "Ethical review complete",
                    "override_reason_category": "ethical_concern",
                    "original_outcome": "DENY",
                    "proposed_outcome": "ALLOW",
                    "is_urgent": True,
                    "priority": 8
                }
            },
            timestamp=datetime.utcnow().isoformat()
        )

        summary = get_override_summary_for_decision(decision)

        assert summary is not None
        assert summary["is_overridden"] is True
        assert summary["override_id"] == "override_123"
        assert summary["reviewer_id"] == "reviewer_001"
        assert summary["reviewer_name"] == "Dr. Jane Smith"
        assert summary["reviewer_role"] == "ethics_officer"
        assert summary["original_outcome"] == "DENY"
        assert summary["proposed_outcome"] == "ALLOW"
        assert summary["current_outcome"] == "ALLOW"
        assert summary["is_urgent"] is True
        assert summary["priority"] == 8
        assert "human_readable_summary" in summary

    def test_get_override_summary_not_overridden(self):
        """Test getting summary from non-overridden decision returns None."""
        decision = Decision(
            decision_id="dec_normal_001",
            input_data={},
            critic_reports=[],
            aggregation={"verdict": "ALLOW"},
            governance_outcome={"verdict": "ALLOW"},
            timestamp=datetime.utcnow().isoformat()
        )

        summary = get_override_summary_for_decision(decision)
        assert summary is None


class TestWorkflowEndToEnd:
    """End-to-end workflow tests."""

    @patch('src.ejc.core.governance.override_workflow.store_precedent_case')
    @patch('src.ejc.core.governance.override_workflow.write_signed_audit_log')
    @patch('src.ejc.core.governance.override_workflow.log_override_event')
    def test_complete_review_and_override_workflow(
        self,
        mock_log_event,
        mock_audit_log,
        mock_store_precedent
    ):
        """Test complete workflow from escalation to override."""
        # 1. Create escalated decision
        decision = Decision(
            decision_id="dec_complete_001",
            input_data={"query": "Complex ethical case"},
            critic_reports=[
                {"critic": "ethics", "verdict": "REVIEW", "confidence": 0.5}
            ],
            aggregation={"verdict": "REVIEW"},
            governance_outcome={"verdict": "ESCALATE", "safeguards_triggered": ["uncertainty"]},
            escalated=True,
            timestamp=datetime.utcnow().isoformat()
        )

        # 2. Find escalated decisions
        escalated = get_escalated_decisions([decision])
        assert len(escalated) == 1

        # 3. Create override from review
        override_request = create_override_from_review(
            decision,
            reviewer_id="ethics_board_chair",
            reviewer_role="governance_board",
            new_outcome="ALLOW",
            justification="After thorough ethics board review, approval granted with conditions",
            reviewer_name="Dr. Ethics Board Chair",
            reviewer_email="chair@ethics.org",
            is_urgent=True,
            priority=9
        )

        # 4. Apply override
        updated_decision = apply_decision_override(
            decision,
            override_request,
            store_as_precedent=True,
            precedent_config={"enabled": True},
            preserve_original=True
        )

        # 5. Verify complete workflow
        assert updated_decision.governance_outcome["verdict"] == "ALLOW"
        assert updated_decision.governance_outcome["human_modified"] is True

        # 6. Get summary
        summary = get_override_summary_for_decision(updated_decision)
        assert summary is not None
        assert summary["reviewer_name"] == "Dr. Ethics Board Chair"
        assert summary["original_outcome"] == "ESCALATE"
        assert summary["current_outcome"] == "ALLOW"

        # Verify all integration points were called
        assert mock_log_event.called
        assert mock_audit_log.called
        assert mock_store_precedent.called
