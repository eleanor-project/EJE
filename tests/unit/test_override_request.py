"""
Comprehensive unit tests for Task 7.1: Override Request Model

Tests for:
- OverrideRequest Pydantic model
- Schema validation
- Field constraints
- Helper methods
- Related enums and models
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.ejc.core.governance.override_request import (
    OverrideRequest,
    OverrideOutcome,
    OverrideReason,
    ReviewerRole,
    OverrideRequestBatch
)


class TestOverrideRequestBasics:
    """Test basic OverrideRequest creation and required fields (Task 7.1)"""

    def test_create_minimal_override_request(self):
        """Test creating override request with only required fields"""
        request = OverrideRequest(
            reviewer_id="reviewer_123",
            justification="This decision requires override due to missing critical context from stakeholder consultation.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="decision_456",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER
        )

        assert request.reviewer_id == "reviewer_123"
        assert len(request.justification) > 10
        assert request.proposed_outcome == OverrideOutcome.ALLOW
        assert request.decision_id == "decision_456"
        assert request.reviewer_role == ReviewerRole.SENIOR_REVIEWER

        # Auto-generated fields
        assert request.request_id is not None
        assert isinstance(request.timestamp, datetime)

    def test_create_complete_override_request(self):
        """Test creating override request with all fields"""
        request = OverrideRequest(
            reviewer_id="reviewer_789",
            reviewer_name="Dr. Jane Smith",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            reviewer_email="jane.smith@org.com",
            decision_id="decision_abc",
            original_outcome="DENY",
            proposed_outcome=OverrideOutcome.ALLOW,
            justification="Detailed ethical review shows this case falls under exception policy XYZ.",
            reason_category=OverrideReason.ETHICAL_CONCERN,
            is_urgent=True,
            priority=8,
            additional_context={"case_id": "123", "department": "legal"},
            supporting_documents=["doc1.pdf", "doc2.pdf"],
            stakeholder_input="Stakeholders agree this is appropriate"
        )

        assert request.reviewer_name == "Dr. Jane Smith"
        assert request.reviewer_email == "jane.smith@org.com"
        assert request.reason_category == OverrideReason.ETHICAL_CONCERN
        assert request.is_urgent is True
        assert request.priority == 8
        assert len(request.supporting_documents) == 2

    def test_auto_generated_request_id(self):
        """Test that request ID is automatically generated as UUID"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="This needs override because of policy exception applicable here.",
            proposed_outcome=OverrideOutcome.REVIEW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD
        )

        assert request.request_id is not None
        assert len(request.request_id) == 36  # UUID format
        assert '-' in request.request_id

    def test_auto_generated_timestamp(self):
        """Test that timestamp is automatically set"""
        before = datetime.utcnow()
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Emergency override required due to critical system error detected.",
            proposed_outcome=OverrideOutcome.ESCALATE,
            decision_id="dec1",
            reviewer_role=ReviewerRole.SYSTEM_ADMINISTRATOR
        )
        after = datetime.utcnow()

        assert before <= request.timestamp <= after


class TestReviewerIDValidation:
    """Test reviewer ID field validation (Task 7.1 required field)"""

    def test_reviewer_id_required(self):
        """Test that reviewer_id is required"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                # reviewer_id missing
                justification="Valid justification here with enough details to meet minimum length.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('reviewer_id',) for e in errors)

    def test_reviewer_id_not_empty(self):
        """Test that reviewer_id cannot be empty string"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="",
                justification="Valid justification with sufficient content and explanation.",
                proposed_outcome=OverrideOutcome.DENY,
                decision_id="dec1",
                reviewer_role=ReviewerRole.LEGAL_COUNSEL
            )

        errors = exc_info.value.errors()
        assert any('reviewer_id' in str(e['loc']) for e in errors)

    def test_reviewer_id_max_length(self):
        """Test reviewer_id max length constraint"""
        long_id = "a" * 256  # 256 characters (over 255 limit)
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id=long_id,
                justification="Valid justification explaining the override necessity clearly.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.AUDITOR
            )

    def test_reviewer_id_valid_lengths(self):
        """Test valid reviewer_id lengths"""
        for length in [1, 50, 100, 255]:
            request = OverrideRequest(
                reviewer_id="a" * length,
                justification="Valid and detailed justification explaining all necessary context.",
                proposed_outcome=OverrideOutcome.REVIEW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.GOVERNANCE_BOARD
            )
            assert len(request.reviewer_id) == length


class TestJustificationValidation:
    """Test justification field validation (Task 7.1 required field)"""

    def test_justification_required(self):
        """Test that justification is required"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                # justification missing
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('justification',) for e in errors)

    def test_justification_minimum_length(self):
        """Test justification minimum length (10 characters)"""
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id="rev1",
                justification="Short",  # Only 5 characters
                proposed_outcome=OverrideOutcome.DENY,
                decision_id="dec1",
                reviewer_role=ReviewerRole.ETHICS_OFFICER
            )

    def test_justification_not_empty_whitespace(self):
        """Test that justification cannot be only whitespace"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="           ",  # Only spaces
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.TECHNICAL_LEAD
            )

        # Should fail on custom validator
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_justification_rejects_placeholder(self):
        """Test that placeholder text is rejected"""
        # Use longer placeholders to pass min_length check
        placeholders = [
            "TODO - fill in later",
            "TBD placeholder",
            "to be determined soon",
            "fill this out later please",
            "placeholder text here"
        ]

        for placeholder in placeholders:
            with pytest.raises(ValidationError) as exc_info:
                OverrideRequest(
                    reviewer_id="rev1",
                    justification=placeholder,
                    proposed_outcome=OverrideOutcome.REVIEW,
                    decision_id="dec1",
                    reviewer_role=ReviewerRole.LEGAL_COUNSEL
                )

            # Check for our custom error message about placeholder text
            error_msg = str(exc_info.value).lower()
            assert "placeholder" in error_msg or "must be different" in error_msg

    def test_justification_accepts_valid_content(self):
        """Test that real justifications are accepted"""
        valid_justifications = [
            "After thorough ethical review and stakeholder consultation, this override is necessary.",
            "Policy exception XYZ-123 applies to this specific case based on documented precedent.",
            "Technical error in original decision - missing critical context data from upstream system.",
            "Emergency override required due to immediate risk to user safety and system integrity."
        ]

        for just in valid_justifications:
            request = OverrideRequest(
                reviewer_id="rev1",
                justification=just,
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER
            )
            assert request.justification == just.strip()

    def test_justification_max_length(self):
        """Test justification maximum length (10000 characters)"""
        long_just = "a" * 10001  # 10001 characters
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id="rev1",
                justification=long_just,
                proposed_outcome=OverrideOutcome.DENY,
                decision_id="dec1",
                reviewer_role=ReviewerRole.ETHICS_OFFICER
            )


class TestProposedOutcomeValidation:
    """Test proposed outcome field validation (Task 7.1 required field)"""

    def test_proposed_outcome_required(self):
        """Test that proposed_outcome is required"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="Valid detailed justification explaining the context and rationale.",
                # proposed_outcome missing
                decision_id="dec1",
                reviewer_role=ReviewerRole.GOVERNANCE_BOARD
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('proposed_outcome',) for e in errors)

    def test_all_valid_outcomes(self):
        """Test all valid override outcomes"""
        outcomes = [
            OverrideOutcome.ALLOW,
            OverrideOutcome.DENY,
            OverrideOutcome.REVIEW,
            OverrideOutcome.ESCALATE
        ]

        for outcome in outcomes:
            request = OverrideRequest(
                reviewer_id="rev1",
                justification="Detailed explanation for this specific override decision and context.",
                proposed_outcome=outcome,
                decision_id="dec1",
                reviewer_role=ReviewerRole.AUDITOR
            )
            assert request.proposed_outcome == outcome

    def test_invalid_outcome_rejected(self):
        """Test that invalid outcome values are rejected"""
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id="rev1",
                justification="Valid justification text with appropriate length and content.",
                proposed_outcome="INVALID_OUTCOME",  # Not a valid OverrideOutcome
                decision_id="dec1",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER
            )


class TestDecisionIDValidation:
    """Test decision ID field validation"""

    def test_decision_id_required(self):
        """Test that decision_id is required"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="Complete justification with all necessary details and reasoning.",
                proposed_outcome=OverrideOutcome.ALLOW,
                # decision_id missing
                reviewer_role=ReviewerRole.TECHNICAL_LEAD
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('decision_id',) for e in errors)

    def test_decision_id_not_empty(self):
        """Test that decision_id cannot be empty"""
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id="rev1",
                justification="Comprehensive justification explaining all aspects of the override.",
                proposed_outcome=OverrideOutcome.DENY,
                decision_id="",
                reviewer_role=ReviewerRole.LEGAL_COUNSEL
            )


class TestReviewerRoleValidation:
    """Test reviewer role field validation"""

    def test_reviewer_role_required(self):
        """Test that reviewer_role is required"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="Thorough explanation of why this override is necessary and justified.",
                proposed_outcome=OverrideOutcome.REVIEW,
                decision_id="dec1"
                # reviewer_role missing
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('reviewer_role',) for e in errors)

    def test_all_valid_reviewer_roles(self):
        """Test all valid reviewer roles"""
        roles = [
            ReviewerRole.SENIOR_REVIEWER,
            ReviewerRole.ETHICS_OFFICER,
            ReviewerRole.LEGAL_COUNSEL,
            ReviewerRole.TECHNICAL_LEAD,
            ReviewerRole.GOVERNANCE_BOARD,
            ReviewerRole.AUDITOR,
            ReviewerRole.SYSTEM_ADMINISTRATOR
        ]

        for role in roles:
            request = OverrideRequest(
                reviewer_id="rev1",
                justification="Proper justification with sufficient detail for override approval.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=role
            )
            assert request.reviewer_role == role


class TestOptionalFieldValidation:
    """Test validation of optional fields"""

    def test_reviewer_email_pattern(self):
        """Test email validation pattern"""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@domain",
            "user domain@example.com"
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                OverrideRequest(
                    reviewer_id="rev1",
                    justification="Valid justification with complete explanation of override rationale.",
                    proposed_outcome=OverrideOutcome.ALLOW,
                    decision_id="dec1",
                    reviewer_role=ReviewerRole.ETHICS_OFFICER,
                    reviewer_email=email
                )

    def test_valid_reviewer_emails(self):
        """Test valid email formats"""
        valid_emails = [
            "user@example.com",
            "jane.smith@organization.org",
            "admin+override@company.co.uk"
        ]

        for email in valid_emails:
            request = OverrideRequest(
                reviewer_id="rev1",
                justification="Comprehensive justification explaining the need for this override.",
                proposed_outcome=OverrideOutcome.DENY,
                decision_id="dec1",
                reviewer_role=ReviewerRole.LEGAL_COUNSEL,
                reviewer_email=email
            )
            assert request.reviewer_email == email

    def test_priority_range_validation(self):
        """Test priority must be between 0 and 10"""
        # Test invalid priorities
        for priority in [-1, 11, 100]:
            with pytest.raises(ValidationError):
                OverrideRequest(
                    reviewer_id="rev1",
                    justification="Detailed justification for override with all required context.",
                    proposed_outcome=OverrideOutcome.REVIEW,
                    decision_id="dec1",
                    reviewer_role=ReviewerRole.SENIOR_REVIEWER,
                    priority=priority
                )

        # Test valid priorities
        for priority in [0, 5, 10]:
            request = OverrideRequest(
                reviewer_id="rev1",
                justification="Complete and thorough justification for this override request.",
                proposed_outcome=OverrideOutcome.ESCALATE,
                decision_id="dec1",
                reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
                priority=priority
            )
            assert request.priority == priority

    def test_original_outcome_pattern(self):
        """Test original_outcome must match valid verdict pattern"""
        valid_outcomes = ["ALLOW", "DENY", "REVIEW", "ESCALATE"]
        for outcome in valid_outcomes:
            # Ensure proposed_outcome differs from original_outcome
            proposed = OverrideOutcome.DENY if outcome != "DENY" else OverrideOutcome.ALLOW
            request = OverrideRequest(
                reviewer_id="rev1",
                justification="Clear and detailed explanation for why this override is needed.",
                proposed_outcome=proposed,
                decision_id="dec1",
                reviewer_role=ReviewerRole.AUDITOR,
                original_outcome=outcome
            )
            assert request.original_outcome == outcome

        # Test invalid outcome
        with pytest.raises(ValidationError):
            OverrideRequest(
                reviewer_id="rev1",
                justification="Valid justification explaining the override decision thoroughly.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.TECHNICAL_LEAD,
                original_outcome="INVALID"
            )


class TestModelValidators:
    """Test custom model validators"""

    def test_expiration_must_be_future(self):
        """Test that expiration time must be in the future"""
        past_time = datetime.utcnow() - timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="Justification with complete details explaining override necessity.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER,
                expires_at=past_time
            )

        assert "future" in str(exc_info.value).lower()

    def test_valid_future_expiration(self):
        """Test that future expiration time is accepted"""
        future_time = datetime.utcnow() + timedelta(hours=24)

        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Thorough explanation of override rationale with supporting evidence.",
            proposed_outcome=OverrideOutcome.DENY,
            decision_id="dec1",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            expires_at=future_time
        )

        assert request.expires_at == future_time

    def test_proposed_outcome_must_differ_from_original(self):
        """Test that proposed outcome must be different from original"""
        with pytest.raises(ValidationError) as exc_info:
            OverrideRequest(
                reviewer_id="rev1",
                justification="Complete justification with all required information and context.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.LEGAL_COUNSEL,
                original_outcome="ALLOW"  # Same as proposed
            )

        assert "different" in str(exc_info.value).lower()

    def test_proposed_differs_from_original_valid(self):
        """Test that different proposed and original outcomes work"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Detailed explanation for changing decision based on new information.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            original_outcome="DENY"
        )

        assert request.proposed_outcome.value != request.original_outcome


class TestHelperMethods:
    """Test helper methods on OverrideRequest"""

    def test_is_expired_with_no_expiration(self):
        """Test is_expired() returns False when no expiration set"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Comprehensive justification explaining all aspects of this override.",
            proposed_outcome=OverrideOutcome.REVIEW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.AUDITOR
        )

        assert request.is_expired() is False

    def test_is_expired_with_future_expiration(self):
        """Test is_expired() returns False for future expiration"""
        future_time = datetime.utcnow() + timedelta(days=7)
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Valid and complete justification for this override request.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.SENIOR_REVIEWER,
            expires_at=future_time
        )

        assert request.is_expired() is False

    def test_is_emergency_with_urgent_flag(self):
        """Test is_emergency() returns True when is_urgent=True"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Emergency override due to critical system failure requiring immediate action.",
            proposed_outcome=OverrideOutcome.ESCALATE,
            decision_id="dec1",
            reviewer_role=ReviewerRole.SYSTEM_ADMINISTRATOR,
            is_urgent=True
        )

        assert request.is_emergency() is True

    def test_is_emergency_with_emergency_reason(self):
        """Test is_emergency() returns True with EMERGENCY reason"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Critical emergency situation requiring immediate override and escalation.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            reason_category=OverrideReason.EMERGENCY
        )

        assert request.is_emergency() is True

    def test_is_emergency_normal_request(self):
        """Test is_emergency() returns False for normal requests"""
        request = OverrideRequest(
            reviewer_id="rev1",
            justification="Standard override request based on policy exception and review.",
            proposed_outcome=OverrideOutcome.REVIEW,
            decision_id="dec1",
            reviewer_role=ReviewerRole.TECHNICAL_LEAD,
            is_urgent=False,
            reason_category=OverrideReason.POLICY_EXCEPTION
        )

        assert request.is_emergency() is False

    def test_to_dict_serialization(self):
        """Test to_dict() produces valid dictionary"""
        request = OverrideRequest(
            reviewer_id="rev123",
            reviewer_name="Jane Doe",
            justification="Complete override justification with all necessary details and context.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="dec456",
            reviewer_role=ReviewerRole.ETHICS_OFFICER,
            original_outcome="DENY"
        )

        result = request.to_dict()

        assert isinstance(result, dict)
        assert result['reviewer_id'] == "rev123"
        assert result['reviewer_name'] == "Jane Doe"
        assert result['proposed_outcome'] == "ALLOW"
        assert result['decision_id'] == "dec456"
        assert result['reviewer_role'] == "ethics_officer"
        assert result['original_outcome'] == "DENY"

    def test_get_summary(self):
        """Test get_summary() produces readable summary"""
        request = OverrideRequest(
            reviewer_id="rev123",
            reviewer_name="Dr. Smith",
            justification="Detailed justification for override based on stakeholder consultation.",
            proposed_outcome=OverrideOutcome.ALLOW,
            decision_id="decision_abc",
            reviewer_role=ReviewerRole.GOVERNANCE_BOARD,
            original_outcome="DENY",
            reason_category=OverrideReason.STAKEHOLDER_INPUT
        )

        summary = request.get_summary()

        assert "Dr. Smith" in summary
        assert "DENY → ALLOW" in summary
        assert "stakeholder_input" in summary
        assert isinstance(summary, str)


class TestOverrideRequestBatch:
    """Test OverrideRequestBatch model"""

    def test_create_batch(self):
        """Test creating a batch of override requests"""
        requests = [
            OverrideRequest(
                reviewer_id=f"rev{i}",
                justification=f"Override justification number {i} with complete details and explanation.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id=f"dec{i}",
                reviewer_role=ReviewerRole.SENIOR_REVIEWER
            )
            for i in range(3)
        ]

        batch = OverrideRequestBatch(
            requests=requests,
            batch_submitted_by="admin_user"
        )

        assert batch.get_request_count() == 3
        assert batch.batch_submitted_by == "admin_user"
        assert batch.batch_id is not None

    def test_batch_requires_at_least_one_request(self):
        """Test that batch requires at least one request"""
        with pytest.raises(ValidationError):
            OverrideRequestBatch(
                requests=[],  # Empty list
                batch_submitted_by="admin"
            )

    def test_get_urgent_count(self):
        """Test counting urgent requests in batch"""
        requests = [
            OverrideRequest(
                reviewer_id="rev1",
                justification="Emergency override required for system recovery and user safety.",
                proposed_outcome=OverrideOutcome.ALLOW,
                decision_id="dec1",
                reviewer_role=ReviewerRole.SYSTEM_ADMINISTRATOR,
                is_urgent=True
            ),
            OverrideRequest(
                reviewer_id="rev2",
                justification="Standard policy exception override for documented precedent case.",
                proposed_outcome=OverrideOutcome.REVIEW,
                decision_id="dec2",
                reviewer_role=ReviewerRole.LEGAL_COUNSEL,
                is_urgent=False
            ),
            OverrideRequest(
                reviewer_id="rev3",
                justification="Critical ethical concern requiring urgent review and escalation.",
                proposed_outcome=OverrideOutcome.ESCALATE,
                decision_id="dec3",
                reviewer_role=ReviewerRole.ETHICS_OFFICER,
                is_urgent=True
            )
        ]

        batch = OverrideRequestBatch(
            requests=requests,
            batch_submitted_by="batch_admin"
        )

        assert batch.get_urgent_count() == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
