"""
Unit tests for Fallback Evidence Schema

Task 6.1: Fallback Evidence Bundle
Tests for schema capturing fallback events, including reasons and fallback decision.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from ejc.core.fallback.fallback_evidence_schema import (
    FallbackType,
    FailedCriticInfo,
    SystemStateAtTrigger,
    FallbackDecision,
    FallbackEvidenceBundle
)


class TestFallbackType:
    """Tests for FallbackType enum"""

    def test_all_fallback_types_exist(self):
        """Test that all expected fallback types are defined"""
        expected_types = [
            'ALL_CRITICS_FAILED',
            'MAJORITY_CRITICS_FAILED',
            'CRITICAL_CRITIC_FAILED',
            'TIMEOUT_EXCEEDED',
            'SCHEMA_VALIDATION_FAILED',
            'INSUFFICIENT_CONFIDENCE',
            'HIGH_ERROR_RATE',
            'MANUAL_OVERRIDE',
            'SYSTEM_ERROR'
        ]

        for type_name in expected_types:
            assert hasattr(FallbackType, type_name)
            assert isinstance(getattr(FallbackType, type_name), FallbackType)

    def test_fallback_type_values(self):
        """Test fallback type enum values"""
        assert FallbackType.ALL_CRITICS_FAILED.value == 'all_critics_failed'
        assert FallbackType.TIMEOUT_EXCEEDED.value == 'timeout_exceeded'
        assert FallbackType.SYSTEM_ERROR.value == 'system_error'


class TestFailedCriticInfo:
    """Tests for FailedCriticInfo dataclass"""

    def test_create_failed_critic_info(self):
        """Test creating FailedCriticInfo"""
        info = FailedCriticInfo(
            critic_name='BiasDetector',
            failure_reason='Timeout exceeded',
            error_type='timeout',
            error_message='Critic did not respond within 5 seconds',
            attempted_retries=2
        )

        assert info.critic_name == 'BiasDetector'
        assert info.failure_reason == 'Timeout exceeded'
        assert info.error_type == 'timeout'
        assert info.error_message == 'Critic did not respond within 5 seconds'
        assert info.attempted_retries == 2
        assert isinstance(info.timestamp, datetime)

    def test_failed_critic_info_to_dict(self):
        """Test converting FailedCriticInfo to dict"""
        info = FailedCriticInfo(
            critic_name='PrivacyGuard',
            failure_reason='Exception raised',
            error_type='exception',
            error_message='ValueError: Invalid input'
        )

        result = info.to_dict()

        assert result['critic_name'] == 'PrivacyGuard'
        assert result['failure_reason'] == 'Exception raised'
        assert result['error_type'] == 'exception'
        assert result['error_message'] == 'ValueError: Invalid input'
        assert 'timestamp' in result
        assert result['attempted_retries'] == 0

    def test_failed_critic_info_with_stack_trace(self):
        """Test FailedCriticInfo with stack trace"""
        stack_trace = """Traceback (most recent call last):
  File "critic.py", line 42, in evaluate
    result = self.process()
ValueError: Invalid input"""

        info = FailedCriticInfo(
            critic_name='ComplianceChecker',
            failure_reason='Processing error',
            error_type='exception',
            stack_trace=stack_trace
        )

        assert info.stack_trace == stack_trace
        assert 'Traceback' in info.to_dict()['stack_trace']


class TestSystemStateAtTrigger:
    """Tests for SystemStateAtTrigger dataclass"""

    def test_create_system_state(self):
        """Test creating SystemStateAtTrigger"""
        state = SystemStateAtTrigger(
            total_critics_expected=5,
            total_critics_attempted=5,
            total_critics_succeeded=2,
            total_critics_failed=3,
            elapsed_time_ms=1250.5,
            timeout_threshold_ms=5000.0,
            active_critics=['BiasDetector', 'PrivacyGuard', 'ComplianceChecker'],
            request_id='req-12345'
        )

        assert state.total_critics_expected == 5
        assert state.total_critics_attempted == 5
        assert state.total_critics_succeeded == 2
        assert state.total_critics_failed == 3
        assert state.elapsed_time_ms == 1250.5
        assert state.timeout_threshold_ms == 5000.0
        assert len(state.active_critics) == 3
        assert state.request_id == 'req-12345'

    def test_system_state_to_dict(self):
        """Test converting SystemStateAtTrigger to dict"""
        state = SystemStateAtTrigger(
            total_critics_expected=3,
            total_critics_attempted=3,
            total_critics_succeeded=1,
            total_critics_failed=2,
            elapsed_time_ms=500.0,
            memory_usage_mb=256.5,
            cpu_usage_percent=45.2,
            environment='staging'
        )

        result = state.to_dict()

        assert result['total_critics_expected'] == 3
        assert result['total_critics_succeeded'] == 1
        assert result['total_critics_failed'] == 2
        assert result['memory_usage_mb'] == 256.5
        assert result['cpu_usage_percent'] == 45.2
        assert result['environment'] == 'staging'

    def test_system_state_with_additional_context(self):
        """Test SystemStateAtTrigger with additional context"""
        additional_context = {
            'load_balancer_region': 'us-west-2',
            'instance_id': 'i-1234567890abcdef0',
            'deployment_version': 'v1.2.3'
        }

        state = SystemStateAtTrigger(
            total_critics_expected=4,
            total_critics_attempted=4,
            total_critics_succeeded=0,
            total_critics_failed=4,
            elapsed_time_ms=100.0,
            additional_context=additional_context
        )

        assert state.additional_context == additional_context
        result = state.to_dict()
        assert result['additional_context']['load_balancer_region'] == 'us-west-2'


class TestFallbackDecision:
    """Tests for FallbackDecision dataclass"""

    def test_create_fallback_decision(self):
        """Test creating FallbackDecision"""
        decision = FallbackDecision(
            verdict='DENY',
            confidence=0.85,
            strategy_used='conservative',
            reason='Insufficient successful critics for safe decision',
            alternative_verdicts=['REVIEW', 'ESCALATE'],
            requires_human_review=True
        )

        assert decision.verdict == 'DENY'
        assert decision.confidence == 0.85
        assert decision.strategy_used == 'conservative'
        assert decision.requires_human_review is True
        assert 'REVIEW' in decision.alternative_verdicts

    def test_fallback_decision_to_dict(self):
        """Test converting FallbackDecision to dict"""
        decision = FallbackDecision(
            verdict='ESCALATE',
            confidence=0.5,
            strategy_used='escalate',
            reason='Critical critic failed',
            is_safe_default=True,
            decision_time_ms=15.5
        )

        result = decision.to_dict()

        assert result['verdict'] == 'ESCALATE'
        assert result['confidence'] == 0.5
        assert result['strategy_used'] == 'escalate'
        assert result['is_safe_default'] is True
        assert result['decision_time_ms'] == 15.5
        assert 'decision_timestamp' in result

    def test_fallback_decision_defaults(self):
        """Test FallbackDecision default values"""
        decision = FallbackDecision(
            verdict='REVIEW',
            confidence=0.6,
            strategy_used='fail_safe',
            reason='Defaulting to safe option'
        )

        assert decision.is_safe_default is True
        assert decision.requires_human_review is False
        assert decision.alternative_verdicts == []
        assert isinstance(decision.decision_timestamp, datetime)


class TestFallbackEvidenceBundle:
    """Tests for FallbackEvidenceBundle dataclass"""

    @pytest.fixture
    def sample_failed_critics(self):
        """Create sample failed critics"""
        return [
            FailedCriticInfo(
                critic_name='BiasDetector',
                failure_reason='Timeout',
                error_type='timeout',
                error_message='Exceeded 5s timeout'
            ),
            FailedCriticInfo(
                critic_name='PrivacyGuard',
                failure_reason='Exception',
                error_type='exception',
                error_message='NullPointerException'
            )
        ]

    @pytest.fixture
    def sample_system_state(self):
        """Create sample system state"""
        return SystemStateAtTrigger(
            total_critics_expected=4,
            total_critics_attempted=4,
            total_critics_succeeded=2,
            total_critics_failed=2,
            elapsed_time_ms=3500.0,
            timeout_threshold_ms=5000.0,
            active_critics=['BiasDetector', 'PrivacyGuard', 'ComplianceChecker', 'SecurityScanner']
        )

    @pytest.fixture
    def sample_fallback_decision(self):
        """Create sample fallback decision"""
        return FallbackDecision(
            verdict='REVIEW',
            confidence=0.7,
            strategy_used='conservative',
            reason='50% critic failure rate',
            requires_human_review=True
        )

    def test_create_fallback_evidence_bundle(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test creating a complete FallbackEvidenceBundle"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.MAJORITY_CRITICS_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision,
            input_text="Sample transaction for review",
            input_context={'amount': 1000, 'user_id': 'user123'}
        )

        assert bundle.fallback_type == FallbackType.MAJORITY_CRITICS_FAILED
        assert len(bundle.failed_critics) == 2
        assert bundle.system_state_at_trigger.total_critics_failed == 2
        assert bundle.fallback_decision.verdict == 'REVIEW'
        assert bundle.input_text == "Sample transaction for review"
        assert bundle.input_context['amount'] == 1000
        assert isinstance(bundle.bundle_id, str)
        assert len(bundle.bundle_id) > 0

    def test_fallback_bundle_to_dict(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test converting FallbackEvidenceBundle to dict"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision
        )

        result = bundle.to_dict()

        assert result['fallback_type'] == 'timeout_exceeded'
        assert len(result['failed_critics']) == 2
        assert 'system_state_at_trigger' in result
        assert 'fallback_decision' in result
        assert 'bundle_id' in result
        assert 'timestamp' in result

    def test_fallback_bundle_from_dict(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test creating FallbackEvidenceBundle from dict"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision
        )

        # Convert to dict and back
        bundle_dict = bundle.to_dict()
        restored_bundle = FallbackEvidenceBundle.from_dict(bundle_dict)

        assert restored_bundle.fallback_type == bundle.fallback_type
        assert len(restored_bundle.failed_critics) == len(bundle.failed_critics)
        assert restored_bundle.fallback_decision.verdict == bundle.fallback_decision.verdict
        assert restored_bundle.system_state_at_trigger.total_critics_failed == bundle.system_state_at_trigger.total_critics_failed

    def test_fallback_bundle_is_critical(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test is_critical() method"""
        # Critical: ALL_CRITICS_FAILED
        bundle1 = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision
        )
        assert bundle1.is_critical() is True

        # Critical: CRITICAL_CRITIC_FAILED
        bundle2 = FallbackEvidenceBundle(
            fallback_type=FallbackType.CRITICAL_CRITIC_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision
        )
        assert bundle2.is_critical() is True

        # Critical: requires_human_review
        decision_with_review = FallbackDecision(
            verdict='ESCALATE',
            confidence=0.5,
            strategy_used='escalate',
            reason='Needs review',
            requires_human_review=True
        )
        bundle3 = FallbackEvidenceBundle(
            fallback_type=FallbackType.HIGH_ERROR_RATE,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=decision_with_review
        )
        assert bundle3.is_critical() is True

        # Not critical
        non_critical_decision = FallbackDecision(
            verdict='ALLOW',
            confidence=0.9,
            strategy_used='permissive',
            reason='Low risk',
            requires_human_review=False
        )
        non_critical_state = SystemStateAtTrigger(
            total_critics_expected=3,
            total_critics_attempted=3,
            total_critics_succeeded=2,
            total_critics_failed=1,
            elapsed_time_ms=100.0
        )
        bundle4 = FallbackEvidenceBundle(
            fallback_type=FallbackType.INSUFFICIENT_CONFIDENCE,
            failed_critics=[sample_failed_critics[0]],
            system_state_at_trigger=non_critical_state,
            fallback_decision=non_critical_decision
        )
        assert bundle4.is_critical() is False

    def test_fallback_bundle_get_failure_rate(self, sample_system_state):
        """Test get_failure_rate() method"""
        # 50% failure rate
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.HIGH_ERROR_RATE,
            failed_critics=[],
            system_state_at_trigger=sample_system_state,
            fallback_decision=FallbackDecision(
                verdict='DENY',
                confidence=0.7,
                strategy_used='conservative',
                reason='High failure rate'
            )
        )

        assert bundle.get_failure_rate() == 0.5

        # 100% failure rate
        all_failed_state = SystemStateAtTrigger(
            total_critics_expected=3,
            total_critics_attempted=3,
            total_critics_succeeded=0,
            total_critics_failed=3,
            elapsed_time_ms=100.0
        )
        bundle2 = FallbackEvidenceBundle(
            fallback_type=FallbackType.ALL_CRITICS_FAILED,
            failed_critics=[],
            system_state_at_trigger=all_failed_state,
            fallback_decision=FallbackDecision(
                verdict='DENY',
                confidence=0.5,
                strategy_used='fail_safe',
                reason='All failed'
            )
        )
        assert bundle2.get_failure_rate() == 1.0

    def test_fallback_bundle_get_summary(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test get_summary() method"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.MAJORITY_CRITICS_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision
        )

        summary = bundle.get_summary()

        assert 'majority_critics_failed' in summary
        assert '2 critics failed' in summary
        assert 'REVIEW' in summary
        assert '70%' in summary
        assert 'conservative' in summary

    def test_fallback_bundle_with_warnings_and_errors(self):
        """Test FallbackEvidenceBundle with warnings and errors"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.SYSTEM_ERROR,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=1,
                total_critics_attempted=1,
                total_critics_succeeded=0,
                total_critics_failed=1,
                elapsed_time_ms=50.0
            ),
            fallback_decision=FallbackDecision(
                verdict='DENY',
                confidence=0.5,
                strategy_used='fail_safe',
                reason='System error'
            ),
            warnings=['High load detected', 'Database latency increased'],
            errors=['Connection timeout', 'Service unavailable']
        )

        assert len(bundle.warnings) == 2
        assert len(bundle.errors) == 2
        assert 'High load detected' in bundle.warnings
        assert 'Connection timeout' in bundle.errors

        result = bundle.to_dict()
        assert len(result['warnings']) == 2
        assert len(result['errors']) == 2

    def test_fallback_bundle_with_recovery(self):
        """Test FallbackEvidenceBundle with recovery information"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.TIMEOUT_EXCEEDED,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=1,
                total_critics_failed=1,
                elapsed_time_ms=6000.0,
                timeout_threshold_ms=5000.0
            ),
            fallback_decision=FallbackDecision(
                verdict='REVIEW',
                confidence=0.6,
                strategy_used='conservative',
                reason='Timeout with partial results'
            ),
            recovery_attempted=True,
            recovery_successful=False,
            recovery_details='Retry failed after 2 attempts'
        )

        assert bundle.recovery_attempted is True
        assert bundle.recovery_successful is False
        assert 'Retry failed' in bundle.recovery_details

        result = bundle.to_dict()
        assert result['recovery_attempted'] is True
        assert result['recovery_successful'] is False

    def test_fallback_bundle_serialization_roundtrip(
        self,
        sample_failed_critics,
        sample_system_state,
        sample_fallback_decision
    ):
        """Test complete serialization and deserialization roundtrip"""
        original = FallbackEvidenceBundle(
            fallback_type=FallbackType.SCHEMA_VALIDATION_FAILED,
            failed_critics=sample_failed_critics,
            system_state_at_trigger=sample_system_state,
            fallback_decision=sample_fallback_decision,
            input_text='Test input',
            input_context={'key': 'value'},
            successful_critic_outputs=[{'critic': 'test', 'verdict': 'ALLOW'}],
            warnings=['Warning 1'],
            errors=['Error 1'],
            metadata={'custom_field': 'custom_value'}
        )

        # Convert to dict
        data = original.to_dict()

        # Create from dict
        restored = FallbackEvidenceBundle.from_dict(data)

        # Verify key fields match
        assert restored.fallback_type == original.fallback_type
        assert len(restored.failed_critics) == len(original.failed_critics)
        assert restored.fallback_decision.verdict == original.fallback_decision.verdict
        assert restored.input_text == original.input_text
        assert restored.input_context == original.input_context
        assert len(restored.warnings) == len(original.warnings)
        assert len(restored.errors) == len(original.errors)
        assert restored.metadata == original.metadata


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_zero_critics_attempted(self):
        """Test system state with zero critics attempted"""
        state = SystemStateAtTrigger(
            total_critics_expected=0,
            total_critics_attempted=0,
            total_critics_succeeded=0,
            total_critics_failed=0,
            elapsed_time_ms=0.0
        )

        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.SYSTEM_ERROR,
            failed_critics=[],
            system_state_at_trigger=state,
            fallback_decision=FallbackDecision(
                verdict='DENY',
                confidence=0.0,
                strategy_used='fail_safe',
                reason='No critics available'
            )
        )

        assert bundle.get_failure_rate() == 0.0

    def test_empty_failed_critics_list(self):
        """Test bundle with no failed critics"""
        bundle = FallbackEvidenceBundle(
            fallback_type=FallbackType.INSUFFICIENT_CONFIDENCE,
            failed_critics=[],
            system_state_at_trigger=SystemStateAtTrigger(
                total_critics_expected=2,
                total_critics_attempted=2,
                total_critics_succeeded=2,
                total_critics_failed=0,
                elapsed_time_ms=100.0
            ),
            fallback_decision=FallbackDecision(
                verdict='REVIEW',
                confidence=0.45,
                strategy_used='conservative',
                reason='Low confidence despite all critics succeeding'
            )
        )

        assert len(bundle.failed_critics) == 0
        assert bundle.get_failure_rate() == 0.0

    def test_multiple_fallback_types(self):
        """Test that all fallback types can be used"""
        for fallback_type in FallbackType:
            bundle = FallbackEvidenceBundle(
                fallback_type=fallback_type,
                failed_critics=[],
                system_state_at_trigger=SystemStateAtTrigger(
                    total_critics_expected=1,
                    total_critics_attempted=1,
                    total_critics_succeeded=0,
                    total_critics_failed=1,
                    elapsed_time_ms=100.0
                ),
                fallback_decision=FallbackDecision(
                    verdict='DENY',
                    confidence=0.5,
                    strategy_used='conservative',
                    reason=f'Triggered by {fallback_type.value}'
                )
            )

            assert bundle.fallback_type == fallback_type
            assert fallback_type.value in bundle.get_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
