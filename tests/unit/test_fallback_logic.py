"""
Comprehensive unit tests for Task 6.2: Fallback Logic Implementation

Tests for:
- Timeout detection and handling
- Schema validation failure detection
- Audit bundle creation (FallbackEvidenceBundle)
- Safe fallback decisions
- Complete auditability
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.ejc.core.fallback.fallback_engine import (
    FallbackEngine,
    FallbackStrategy,
    FallbackTrigger,
    FallbackResult
)
from src.ejc.core.fallback.fallback_evidence_schema import (
    FallbackEvidenceBundle,
    FallbackType,
    FailedCriticInfo,
    SystemStateAtTrigger,
    FallbackDecision
)
from src.ejc.core.error_handling import CriticTimeoutException
from src.ejc.core.evidence_normalizer import ValidationError


class TestTimeoutDetection:
    """Test timeout detection in fallback logic (Task 6.2)"""

    def test_timeout_threshold_exceeded(self):
        """Test fallback triggered when timeout threshold exceeded"""
        engine = FallbackEngine(timeout_threshold_ms=1000.0)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=1500.0
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert 'exceeds threshold' in reason
        assert '1500' in reason

    def test_timeout_threshold_not_exceeded(self):
        """Test fallback not triggered when within timeout threshold"""
        engine = FallbackEngine(timeout_threshold_ms=2000.0)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=1500.0
        )

        assert should_fb is False
        assert trigger is None

    def test_timeout_with_critic_timeout_exception(self):
        """Test detection of critics that timed out with exception"""
        engine = FallbackEngine()
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timed out'),
                'error_type': 'timeout'
            },
            {
                'critic': 'critic2',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timed out'),
                'error_type': 'timeout'
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert 'timed out' in reason.lower()

    def test_timeout_majority_critics(self):
        """Test fallback when majority of critics time out"""
        engine = FallbackEngine()
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': TimeoutError('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'critic2',
                'verdict': 'ERROR',
                'error': TimeoutError('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'critic3',
                'verdict': 'ALLOW',
                'confidence': 0.9
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert '2/3' in reason

    def test_no_timeout_when_threshold_not_set(self):
        """Test timeout checking skipped when threshold not configured"""
        engine = FallbackEngine(timeout_threshold_ms=None)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=5000.0  # High elapsed time
        )

        # Should not trigger timeout since threshold is None
        assert should_fb is False


class TestSchemaValidationDetection:
    """Test schema validation failure detection (Task 6.2)"""

    def test_schema_validation_errors_trigger_fallback(self):
        """Test fallback triggered when schema validation errors present"""
        engine = FallbackEngine()
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]
        validation_errors = [
            ValidationError(field='verdict', error='Invalid verdict', severity='error'),
            ValidationError(field='confidence', error='Out of range', severity='error')
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            validation_errors=validation_errors
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert 'validation error' in reason.lower()
        assert '2' in reason

    def test_schema_validation_warnings_dont_trigger_fallback(self):
        """Test fallback not triggered by warnings, only errors"""
        engine = FallbackEngine()
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]
        validation_errors = [
            ValidationError(field='metadata', error='Missing field', severity='warning'),
            ValidationError(field='tags', error='Deprecated field', severity='info')
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            validation_errors=validation_errors
        )

        # No critical errors, so no fallback
        assert should_fb is False
        assert trigger is None

    def test_mixed_validation_errors_trigger_fallback(self):
        """Test fallback triggered when both errors and warnings present"""
        engine = FallbackEngine()
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]
        validation_errors = [
            ValidationError(field='verdict', error='Invalid', severity='error'),
            ValidationError(field='meta', error='Missing', severity='warning')
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            validation_errors=validation_errors
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert '1' in reason  # Only 1 critical error


class TestFallbackAuditBundles:
    """Test FallbackEvidenceBundle creation for auditability (Task 6.2)"""

    def test_audit_bundle_created_for_fallback(self):
        """Test that audit bundle is created when fallback occurs"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Failed')},
            {'critic': 'critic2', 'verdict': 'ERROR', 'error': Exception('Failed')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED,
            context={'input_text': 'Test input'}
        )

        assert 'audit_bundle' in result.metadata
        assert 'audit_bundle_id' in result.metadata

        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_type'] == FallbackType.ALL_CRITICS_FAILED.value
        assert len(bundle_dict['failed_critics']) == 2

    def test_audit_bundle_disabled(self):
        """Test that audit bundle not created when disabled"""
        engine = FallbackEngine(enable_audit_bundles=False)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Failed')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        assert 'audit_bundle' not in result.metadata

    def test_audit_bundle_contains_timeout_info(self):
        """Test audit bundle contains timeout information"""
        engine = FallbackEngine(
            enable_audit_bundles=True,
            timeout_threshold_ms=1000.0
        )
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            }
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.TIMEOUT,
            elapsed_time_ms=1500.0
        )

        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_type'] == FallbackType.TIMEOUT_EXCEEDED.value
        assert bundle_dict['system_state_at_trigger']['elapsed_time_ms'] == 1500.0
        assert bundle_dict['system_state_at_trigger']['timeout_threshold_ms'] == 1000.0

        # Check failed critic info
        failed_critic = bundle_dict['failed_critics'][0]
        assert failed_critic['error_type'] == 'timeout'

    def test_audit_bundle_contains_validation_errors(self):
        """Test audit bundle contains validation error information"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]
        validation_errors = [
            ValidationError(field='verdict', error='Invalid format', severity='error'),
            ValidationError(field='confidence', error='Deprecated', severity='warning')
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.TIMEOUT,  # Using TIMEOUT as schema validation maps here
            validation_errors=validation_errors
        )

        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_type'] == FallbackType.SCHEMA_VALIDATION_FAILED.value
        assert len(bundle_dict['errors']) == 1
        assert len(bundle_dict['warnings']) == 1
        assert 'Invalid format' in bundle_dict['errors'][0]

    def test_audit_bundle_system_state(self):
        """Test audit bundle captures complete system state"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')},
            {'critic': 'critic2', 'verdict': 'ALLOW', 'confidence': 0.8}
        ]
        context = {
            'system_version': '2.0.0',
            'environment': 'staging',
            'request_id': 'req-123',
            'correlation_id': 'corr-456',
            'user_id': 'user-789',
            'session_id': 'sess-abc'
        }

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.MAJORITY_CRITICS_FAILED,
            context=context,
            elapsed_time_ms=250.0
        )

        system_state = result.metadata['audit_bundle']['system_state_at_trigger']
        assert system_state['total_critics_expected'] == 2
        assert system_state['total_critics_attempted'] == 2
        assert system_state['total_critics_succeeded'] == 1
        assert system_state['total_critics_failed'] == 1
        assert system_state['elapsed_time_ms'] == 250.0
        assert system_state['system_version'] == '2.0.0'
        assert system_state['environment'] == 'staging'
        assert system_state['request_id'] == 'req-123'

    def test_audit_bundle_fallback_decision(self):
        """Test audit bundle captures fallback decision details"""
        engine = FallbackEngine(
            enable_audit_bundles=True,
            default_strategy=FallbackStrategy.CONSERVATIVE
        )
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        decision = result.metadata['audit_bundle']['fallback_decision']
        assert decision['verdict'] == 'REVIEW'  # Conservative default
        assert decision['strategy_used'] == 'conservative'
        assert decision['is_safe_default'] is True
        assert decision['requires_human_review'] is True  # Low confidence
        assert 'decision_time_ms' in decision
        assert decision['decision_time_ms'] >= 0


class TestSafeFallbackDecisions:
    """Test that fallback decisions are always safe (Task 6.2)"""

    def test_conservative_strategy_always_safe(self):
        """Test conservative strategy produces safe decisions"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.CONSERVATIVE)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        # Conservative should default to REVIEW (safe)
        assert result.fallback_verdict in ['REVIEW', 'DENY']
        assert result.triggered is True

    def test_escalate_strategy_requires_review(self):
        """Test escalate strategy always requires human review"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            enable_audit_bundles=True
        )
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        assert result.fallback_verdict == 'REVIEW'
        assert result.confidence == 0.0
        decision = result.metadata['audit_bundle']['fallback_decision']
        assert decision['requires_human_review'] is True

    def test_fail_safe_uses_safe_default(self):
        """Test fail-safe strategy uses configured safe default"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.FAIL_SAFE,
            safe_default_verdict='DENY'
        )
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        assert result.fallback_verdict == 'DENY'
        assert result.fallback_strategy == FallbackStrategy.FAIL_SAFE

    def test_timeout_fallback_safe_decision(self):
        """Test timeout triggers safe fallback decision"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            timeout_threshold_ms=1000.0
        )
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout')
            }
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.TIMEOUT,
            elapsed_time_ms=1500.0
        )

        # Should default to safe decision (REVIEW)
        assert result.fallback_verdict == 'REVIEW'
        assert result.confidence == 0.0

    def test_schema_validation_failure_safe_decision(self):
        """Test schema validation failure triggers safe decision"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.CONSERVATIVE)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]
        validation_errors = [
            ValidationError(field='verdict', error='Invalid', severity='error')
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.TIMEOUT,  # Schema validation uses this trigger
            validation_errors=validation_errors
        )

        # Should be safe (REVIEW)
        assert result.fallback_verdict == 'REVIEW'


class TestCompleteAuditability:
    """Test complete auditability of fallback decisions (Task 6.2)"""

    def test_audit_trail_serialization(self):
        """Test audit bundle can be serialized for logging"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED,
            context={'input_text': 'Test'}
        )

        # Verify bundle can be serialized
        bundle_dict = result.metadata['audit_bundle']
        assert isinstance(bundle_dict, dict)
        assert 'bundle_id' in bundle_dict
        assert 'timestamp' in bundle_dict
        assert 'fallback_type' in bundle_dict
        assert 'failed_critics' in bundle_dict
        assert 'system_state_at_trigger' in bundle_dict
        assert 'fallback_decision' in bundle_dict

    def test_audit_bundle_reconstruction(self):
        """Test audit bundle can be reconstructed from dict"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.ALL_CRITICS_FAILED
        )

        bundle_dict = result.metadata['audit_bundle']

        # Reconstruct bundle from dict
        reconstructed = FallbackEvidenceBundle.from_dict(bundle_dict)

        assert reconstructed.bundle_id == bundle_dict['bundle_id']
        assert reconstructed.fallback_type == FallbackType.ALL_CRITICS_FAILED
        assert len(reconstructed.failed_critics) == 1

    def test_failed_critic_info_complete(self):
        """Test FailedCriticInfo contains complete error details"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {
                'critic': 'safety_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Operation timed out after 5s'),
                'error_type': 'timeout',
                'justification': 'Critic execution exceeded time limit',
                'retries': 2
            }
        ]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=FallbackTrigger.TIMEOUT
        )

        failed_critic = result.metadata['audit_bundle']['failed_critics'][0]
        assert failed_critic['critic_name'] == 'safety_critic'
        assert failed_critic['error_type'] == 'timeout'
        assert 'timed out' in failed_critic['error_message'].lower()
        assert failed_critic['attempted_retries'] == 2

    def test_logging_of_fallback_event(self):
        """Test fallback events are properly logged"""
        engine = FallbackEngine(enable_audit_bundles=True)
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Error')}
        ]

        with patch('src.ejc.core.fallback.fallback_engine.logger') as mock_logger:
            result = engine.apply_fallback(
                critic_outputs=critic_outputs,
                trigger=FallbackTrigger.ALL_CRITICS_FAILED
            )

            # Verify warning was logged
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert 'fallback strategy' in warning_call.lower()
            assert 'all_critics_failed' in warning_call.lower()

            # Verify audit bundle creation was logged
            mock_logger.info.assert_called()
            info_call = mock_logger.info.call_args[0][0]
            assert 'audit bundle' in info_call.lower()


class TestIntegrationScenarios:
    """Integration tests for complete fallback scenarios (Task 6.2)"""

    def test_timeout_with_partial_success(self):
        """Test timeout scenario with some successful critics"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.MAJORITY,
            enable_audit_bundles=True
        )
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            },
            {'critic': 'critic2', 'verdict': 'ALLOW', 'confidence': 0.8},
            {'critic': 'critic3', 'verdict': 'ALLOW', 'confidence': 0.9}
        ]

        # Check if fallback should trigger
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is False  # Majority succeeded

        # Even without fallback trigger, we can simulate applying it
        # (in practice, would only apply if should_fallback returned True)

    def test_all_critics_timeout(self):
        """Test scenario where all critics time out"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            enable_audit_bundles=True,
            timeout_threshold_ms=1000.0
        )
        critic_outputs = [
            {
                'critic': 'critic1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'critic2',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=1500.0
        )

        assert result.fallback_verdict == 'REVIEW'
        bundle = result.metadata['audit_bundle']
        assert bundle['fallback_type'] == FallbackType.TIMEOUT_EXCEEDED.value
        assert len(bundle['failed_critics']) == 2

    def test_schema_validation_with_critic_failures(self):
        """Test schema validation failure combined with critic failures"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            enable_audit_bundles=True
        )
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR', 'error': Exception('Failed')},
            {'critic': 'critic2', 'verdict': 'ALLOW', 'confidence': 0.7}
        ]
        validation_errors = [
            ValidationError(field='verdict', error='Invalid type', severity='error')
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            validation_errors=validation_errors
        )
        assert should_fb is True

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            validation_errors=validation_errors
        )

        bundle = result.metadata['audit_bundle']
        assert bundle['fallback_type'] == FallbackType.SCHEMA_VALIDATION_FAILED.value
        assert len(bundle['errors']) > 0
        assert bundle['fallback_decision']['requires_human_review'] is True

    def test_complete_workflow_with_audit(self):
        """Test complete workflow: detection -> fallback -> audit"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            timeout_threshold_ms=2000.0,
            enable_audit_bundles=True
        )

        # Simulate critic execution
        critic_outputs = [
            {'critic': 'safety_critic', 'verdict': 'ERROR', 'error': Exception('Failed')},
            {'critic': 'bias_critic', 'verdict': 'ALLOW', 'confidence': 0.6}
        ]
        elapsed_time = 1800.0

        # Step 1: Check if fallback needed
        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=elapsed_time
        )
        assert should_fb is True

        # Step 2: Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=elapsed_time,
            context={
                'input_text': 'Test legal scenario',
                'request_id': 'req-xyz'
            }
        )

        # Step 3: Verify complete audit trail
        assert result.triggered is True
        assert 'audit_bundle' in result.metadata
        bundle = result.metadata['audit_bundle']

        # Verify all components present
        assert 'bundle_id' in bundle
        assert 'fallback_type' in bundle
        assert 'failed_critics' in bundle
        assert 'system_state_at_trigger' in bundle
        assert 'fallback_decision' in bundle
        assert bundle['input_text'] == 'Test legal scenario'

        # Verify decision is safe
        assert result.fallback_verdict in ['REVIEW', 'DENY']
        assert bundle['fallback_decision']['is_safe_default'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
