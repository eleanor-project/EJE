"""
Comprehensive unit tests for Task 6.3: Fallback Explanation Generator

Tests for:
- Clear failure reasons
- List affected critics
- Safety rationale
- Multi-audience explanations (general, technical, executive)
- Integration with FallbackEvidenceBundle
"""

import pytest
from datetime import datetime

from src.ejc.core.fallback.fallback_explainer import (
    FallbackExplainer,
    explain_fallback_bundle_simple,
    get_fallback_bundle_details
)
from src.ejc.core.fallback.fallback_evidence_schema import (
    FallbackEvidenceBundle,
    FallbackType,
    FailedCriticInfo,
    SystemStateAtTrigger,
    FallbackDecision
)


class TestFallbackExplanationBasics:
    """Test basic fallback explanation functionality (Task 6.3)"""

    def test_explain_bundle_structure(self):
        """Test explanation has all required components"""
        bundle = self._create_test_bundle()
        explainer = FallbackExplainer(audience="general")

        explanation = explainer.explain_fallback_bundle(bundle)

        # Task 6.3 requirements
        assert 'summary' in explanation
        assert 'trigger_explanation' in explanation
        assert 'failed_critics' in explanation  # List affected critics
        assert 'decision_explanation' in explanation
        assert 'safety_rationale' in explanation  # Safety rationale
        assert 'system_state_summary' in explanation

    def test_user_explanation_format(self):
        """Test user-friendly explanation formatting"""
        bundle = self._create_test_bundle()
        explainer = FallbackExplainer(audience="general")

        explanation = explainer.explain_bundle_to_user(bundle)

        # Should have structured sections
        assert "FALLBACK EVENT EXPLANATION" in explanation
        assert "WHY DID FALLBACK OCCUR?" in explanation
        assert "WHICH CRITICS WERE AFFECTED?" in explanation
        assert "WHAT DECISION WAS MADE?" in explanation
        assert "WHY IS THIS DECISION SAFE?" in explanation

    def test_explanation_with_no_failed_critics(self):
        """Test explanation when fallback triggered without critic failures"""
        bundle = self._create_test_bundle(failed_critics=[])
        explainer = FallbackExplainer(audience="general")

        explanation = explainer.explain_fallback_bundle(bundle)

        assert explanation['failed_critics'] == []
        user_exp = explainer.explain_bundle_to_user(bundle)
        assert "No critic failures" in user_exp

    def _create_test_bundle(self, failed_critics=None):
        """Helper to create test bundle"""
        if failed_critics is None:
            failed_critics = [
                FailedCriticInfo(
                    critic_name="safety_critic",
                    failure_reason="Execution timeout",
                    error_type="timeout"
                )
            ]

        system_state = SystemStateAtTrigger(
            total_critics_expected=3,
            total_critics_attempted=3,
            total_critics_succeeded=2,
            total_critics_failed=len(failed_critics),
            elapsed_time_ms=1500.0,
            timeout_threshold_ms=1000.0
        )

        decision = FallbackDecision(
            verdict="REVIEW",
            confidence=0.6,
            strategy_used="conservative",
            reason="Conservative fallback applied",
            is_safe_default=True,
            requires_human_review=True
        )

        return FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=failed_critics,
            system_state_at_trigger=system_state,
            fallback_decision=decision
        )


class TestClearFailureReasons:
    """Test clear failure reason explanations (Task 6.3 requirement)"""

    def test_timeout_failure_explanation(self):
        """Test timeout failure is clearly explained"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="bias_critic",
                    failure_reason="Operation timed out after 5 seconds",
                    error_type="timeout"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=5000.0,
                timeout_threshold_ms=3000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="All critics timed out"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        # Should explain timeout clearly
        trigger_exp = explanation['trigger_explanation']
        assert 'timeout' in trigger_exp.lower() or 'too long' in trigger_exp.lower()

    def test_all_critics_failed_explanation(self):
        """Test all critics failed is clearly explained"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="critic1",
                    failure_reason="API error",
                    error_type="exception"
                ),
                FailedCriticInfo(
                    critic_name="critic2",
                    failure_reason="Connection timeout",
                    error_type="timeout"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=0,
                total_critics_failed=2,
                elapsed_time_ms=1000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="All critics failed"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        trigger_exp = explanation['trigger_explanation']
        assert 'all' in trigger_exp.lower()
        assert 'component' in trigger_exp.lower() or 'critic' in trigger_exp.lower()

    def test_schema_validation_failure_explanation(self):
        """Test schema validation failure is clearly explained"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.SCHEMA_VALIDATION_FAILED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=1,
                total_critics_failed=0,
                elapsed_time_ms=500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.5,
                strategy_used="conservative",
                reason="Schema validation failed"
            ),
            errors=["Invalid verdict format", "Missing required field"]
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        trigger_exp = explanation['trigger_explanation']
        assert 'validation' in trigger_exp.lower() or 'quality' in trigger_exp.lower()
        assert explanation['errors'] == bundle.errors


class TestListAffectedCritics:
    """Test listing affected critics (Task 6.3 requirement)"""

    def test_list_single_failed_critic(self):
        """Test listing a single failed critic"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.CRITICAL_CRITIC_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="legal_compliance_critic",
                    failure_reason="Database connection lost",
                    error_type="connection_error",
                    error_message="Could not connect to legal database",
                    attempted_retries=3
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=3,
                total_critics_attempted=3,
                total_critics_succeeded=2,
                total_critics_failed=1,
                elapsed_time_ms=800.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.4,
                strategy_used="conservative",
                reason="Critical critic failed"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        failed_critics = explanation['failed_critics']
        assert len(failed_critics) == 1
        assert failed_critics[0]['name'] == "legal_compliance_critic"
        assert failed_critics[0]['reason'] == "Database connection lost"
        assert failed_critics[0]['error_type'] == "connection_error"

    def test_list_multiple_failed_critics(self):
        """Test listing multiple failed critics with different error types"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.MAJORITY_CRITICS_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="critic_A",
                    failure_reason="Timeout during analysis",
                    error_type="timeout"
                ),
                FailedCriticInfo(
                    critic_name="critic_B",
                    failure_reason="Invalid input format",
                    error_type="validation_error"
                ),
                FailedCriticInfo(
                    critic_name="critic_C",
                    failure_reason="API rate limit exceeded",
                    error_type="rate_limit"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=4,
                total_critics_attempted=4,
                total_critics_succeeded=1,
                total_critics_failed=3,
                elapsed_time_ms=2000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.3,
                strategy_used="conservative",
                reason="Majority of critics failed"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        failed_critics = explanation['failed_critics']
        assert len(failed_critics) == 3

        # Check all critics are listed with their reasons
        names = [c['name'] for c in failed_critics]
        assert "critic_A" in names
        assert "critic_B" in names
        assert "critic_C" in names

        # Check reasons are present
        for critic in failed_critics:
            assert 'name' in critic
            assert 'reason' in critic
            assert 'error_type' in critic

    def test_failed_critics_with_technical_details(self):
        """Test failed critics list includes technical details when requested"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.HIGH_ERROR_RATE,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="ml_critic",
                    failure_reason="Model inference failed",
                    error_type="model_error",
                    error_message="CUDA out of memory error",
                    stack_trace="Traceback (most recent call last)...",
                    attempted_retries=2
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=0,
                total_critics_failed=2,
                elapsed_time_ms=1200.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="High error rate"
            )
        )

        explainer = FallbackExplainer(audience="technical")
        explanation = explainer.explain_fallback_bundle(bundle, include_technical_details=True)

        failed_critics = explanation['failed_critics']
        critic = failed_critics[0]

        # Should include technical details
        assert 'error_message' in critic
        assert critic['error_message'] == "CUDA out of memory error"
        assert 'retries' in critic
        assert critic['retries'] == 2
        assert 'stack_trace' in critic

    def test_user_friendly_failed_critics_display(self):
        """Test failed critics are displayed clearly in user-facing explanation"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="safety_critic",
                    failure_reason="Network connection lost",
                    error_type="network_error"
                ),
                FailedCriticInfo(
                    critic_name="bias_critic",
                    failure_reason="Service unavailable",
                    error_type="service_error"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=0,
                total_critics_failed=2,
                elapsed_time_ms=1000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="All critics failed"
            )
        )

        explainer = FallbackExplainer(audience="general")
        user_explanation = explainer.explain_bundle_to_user(bundle)

        # Should list both critics clearly
        assert "safety_critic" in user_explanation
        assert "bias_critic" in user_explanation
        assert "Network connection lost" in user_explanation
        assert "Service unavailable" in user_explanation


class TestSafetyRationale:
    """Test safety rationale explanations (Task 6.3 requirement)"""

    def test_safe_default_rationale(self):
        """Test safety rationale explains safe default"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.5,
                strategy_used="conservative",
                reason="Using safe default",
                is_safe_default=True,
                requires_human_review=False
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        safety_rationale = explanation['safety_rationale']
        assert 'safe' in safety_rationale.lower()
        assert 'default' in safety_rationale.lower() or 'proven' in safety_rationale.lower()

    def test_human_review_rationale(self):
        """Test safety rationale explains human review requirement"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.CRITICAL_CRITIC_FAILED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.3,
                strategy_used="escalate",
                reason="Requires human review",
                is_safe_default=True,
                requires_human_review=True
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        safety_rationale = explanation['safety_rationale']
        assert 'human' in safety_rationale.lower() and 'review' in safety_rationale.lower()

    def test_conservative_strategy_rationale(self):
        """Test safety rationale explains conservative strategy"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.MAJORITY_CRITICS_FAILED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=3,
                total_critics_attempted=3,
                total_critics_succeeded=1,
                total_critics_failed=2,
                elapsed_time_ms=1000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="DENY",
                confidence=0.7,
                strategy_used="conservative",
                reason="Conservative approach",
                is_safe_default=True
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        safety_rationale = explanation['safety_rationale']
        assert 'conservative' in safety_rationale.lower()
        assert 'restrictive' in safety_rationale.lower() or 'risk' in safety_rationale.lower()

    def test_audit_trail_rationale(self):
        """Test safety rationale includes audit trail"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=2000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.5,
                strategy_used="conservative",
                reason="Timeout"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        safety_rationale = explanation['safety_rationale']
        assert 'audit' in safety_rationale.lower() or 'logged' in safety_rationale.lower()
        assert bundle.bundle_id[:8] in safety_rationale  # Bundle ID reference

    def test_successful_critics_rationale(self):
        """Test safety rationale mentions successful critics"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.MAJORITY_CRITICS_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="critic1",
                    failure_reason="Error",
                    error_type="error"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=3,
                total_critics_attempted=3,
                total_critics_succeeded=2,
                total_critics_failed=1,
                elapsed_time_ms=800.0
            ),
            fallback_decision=FallbackDecision(
                verdict="ALLOW",
                confidence=0.8,
                strategy_used="majority",
                reason="Majority succeeded"
            )
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        safety_rationale = explanation['safety_rationale']
        assert '2' in safety_rationale  # 2 successful critics
        assert 'component' in safety_rationale.lower() or 'critic' in safety_rationale.lower()


class TestMultiAudienceExplanations:
    """Test explanations for different audiences (Task 6.3)"""

    def test_general_audience_explanation(self):
        """Test general audience gets non-technical explanation"""
        bundle = self._create_test_bundle()
        explainer = FallbackExplainer(audience="general")

        explanation = explainer.explain_bundle_to_user(bundle)

        # Should be user-friendly
        assert "evaluation components" in explanation.lower() or "system" in explanation.lower()
        # Should avoid jargon
        assert "critics" not in explanation.lower() or "evaluation components" in explanation.lower()

    def test_technical_audience_explanation(self):
        """Test technical audience gets detailed technical explanation"""
        bundle = self._create_test_bundle()
        explainer = FallbackExplainer(audience="technical")

        explanation = explainer.explain_bundle_to_user(bundle)

        # Should include technical terms
        assert "critic" in explanation.lower() or "fallback" in explanation.lower()
        # Should include technical details
        assert "strategy" in explanation.lower()

    def test_executive_audience_explanation(self):
        """Test executive audience gets concise high-level explanation"""
        bundle = self._create_test_bundle()
        explainer = FallbackExplainer(audience="executive")

        explanation = explainer.explain_bundle_to_user(bundle)

        # Should be concise
        assert len(explanation) < 2000  # Rough check for brevity
        # Should focus on decisions and outcomes
        assert "decision" in explanation.lower() or "verdict" in explanation.lower()

    def test_audience_specific_summary(self):
        """Test summary differs by audience"""
        bundle = self._create_test_bundle()

        general_exp = FallbackExplainer(audience="general")
        technical_exp = FallbackExplainer(audience="technical")
        executive_exp = FallbackExplainer(audience="executive")

        general_summary = general_exp._generate_bundle_summary(bundle)
        technical_summary = technical_exp._generate_bundle_summary(bundle)
        executive_summary = executive_exp._generate_bundle_summary(bundle)

        # Summaries should be different
        assert general_summary != technical_summary
        assert technical_summary != executive_summary

    def _create_test_bundle(self):
        """Helper to create test bundle"""
        return FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="test_critic",
                    failure_reason="Timeout",
                    error_type="timeout"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=1,
                total_critics_failed=1,
                elapsed_time_ms=1500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.6,
                strategy_used="conservative",
                reason="Timeout occurred"
            )
        )


class TestConvenienceFunctions:
    """Test convenience functions for Task 6.3"""

    def test_explain_fallback_bundle_simple(self):
        """Test simple convenience function"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="All failed"
            )
        )

        explanation = explain_fallback_bundle_simple(bundle)

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "FALLBACK" in explanation

    def test_explain_fallback_bundle_simple_with_audience(self):
        """Test simple function with different audiences"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=2000.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.5,
                strategy_used="conservative",
                reason="Timeout"
            )
        )

        general = explain_fallback_bundle_simple(bundle, audience="general")
        technical = explain_fallback_bundle_simple(bundle, audience="technical")

        assert general != technical
        assert isinstance(general, str)
        assert isinstance(technical, str)

    def test_get_fallback_bundle_details(self):
        """Test structured details convenience function"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.SCHEMA_VALIDATION_FAILED,
            failed_critics=[
                FailedCriticInfo(
                    critic_name="validator_critic",
                    failure_reason="Invalid output",
                    error_type="validation"
                )
            ],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=1,
                total_critics_failed=1,
                elapsed_time_ms=600.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.4,
                strategy_used="conservative",
                reason="Schema validation failed"
            )
        )

        details = get_fallback_bundle_details(bundle)

        # Should have all required fields
        assert 'summary' in details
        assert 'trigger_explanation' in details
        assert 'failed_critics' in details
        assert 'decision_explanation' in details
        assert 'safety_rationale' in details
        assert 'system_state_summary' in details

        # Failed critics should be listed
        assert len(details['failed_critics']) == 1
        assert details['failed_critics'][0]['name'] == "validator_critic"


class TestIntegrationWithTasks61And62:
    """Test integration with Task 6.1 (schema) and Task 6.2 (logic)"""

    def test_all_fallback_types_explained(self):
        """Test all FallbackType values have explanations"""
        for fallback_type in FallbackType:
            bundle = FallbackEvidenceBundle(
                fallback_type=fallback_type,
                failed_critics=[],
                system_state_at_trigger=SystemStateAtTrigger(
                    total_critics_expected=1,
                    total_critics_attempted=1,
                    total_critics_succeeded=0,
                    total_critics_failed=1,
                    elapsed_time_ms=500.0
                ),
                fallback_decision=FallbackDecision(
                    verdict="REVIEW",
                    confidence=0.5,
                    strategy_used="conservative",
                    reason="Test"
                )
            )

            explainer = FallbackExplainer(audience="general")
            explanation = explainer.explain_fallback_bundle(bundle)

            # Should have a trigger explanation for every type
            assert explanation['trigger_explanation']
            assert len(explanation['trigger_explanation']) > 0

    def test_warnings_and_errors_displayed(self):
        """Test warnings and errors from bundle are displayed"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.SYSTEM_ERROR,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=500.0
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.0,
                strategy_used="conservative",
                reason="System error"
            ),
            warnings=["Low memory detected", "High CPU usage"],
            errors=["Database connection failed"]
        )

        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_fallback_bundle(bundle)

        assert 'warnings' in explanation
        assert explanation['warnings'] == bundle.warnings
        assert 'errors' in explanation
        assert explanation['errors'] == bundle.errors

        # Should also appear in user explanation
        user_exp = explainer.explain_bundle_to_user(bundle)
        assert "Low memory detected" in user_exp
        assert "Database connection failed" in user_exp

    def test_verbose_mode_includes_system_state(self):
        """Test verbose mode includes system state details"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.HIGH_ERROR_RATE,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=5,
                total_critics_attempted=5,
                total_critics_succeeded=2,
                total_critics_failed=3,
                elapsed_time_ms=1800.0,
                timeout_threshold_ms=2000.0,
                system_version="2.0.0",
                environment="production"
            ),
            fallback_decision=FallbackDecision(
                verdict="REVIEW",
                confidence=0.3,
                strategy_used="conservative",
                reason="High error rate"
            )
        )

        # Test general audience
        general_explainer = FallbackExplainer(audience="general")
        general_verbose = general_explainer.explain_bundle_to_user(bundle, verbose=True)
        assert "SYSTEM STATE" in general_verbose
        assert "1800" in general_verbose  # elapsed time

        # Test technical audience for technical details
        technical_explainer = FallbackExplainer(audience="technical")
        technical_verbose = technical_explainer.explain_bundle_to_user(bundle, verbose=True)
        assert "SYSTEM STATE" in technical_verbose
        assert "production" in technical_verbose
        assert "2.0.0" in technical_verbose


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
