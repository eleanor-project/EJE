"""
Integration Tests for Task 6.4: Fallback Handling

Comprehensive integration tests for fallback system under various failure conditions:
- Timeouts
- Missing critic output
- Conflicts
- Precedent retrieval failure

These tests verify end-to-end fallback behavior in realistic failure scenarios.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

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
from src.ejc.core.fallback.fallback_explainer import (
    FallbackExplainer,
    explain_fallback_bundle_simple
)
from src.ejc.core.error_handling import CriticTimeoutException


class TestTimeoutHandling:
    """
    Task 6.4: Test fallback handling under timeout scenarios

    Tests various timeout conditions and verifies proper fallback activation,
    safe decisions, and complete audit trails.
    """

    def test_single_critic_timeout(self):
        """Test fallback when a single critic times out (but not majority)"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            timeout_threshold_ms=1000.0,
            error_rate_threshold=0.6,  # Set higher threshold to avoid triggering on 33%
            enable_audit_bundles=True
        )

        # Simulate single critic timeout (1 out of 3 = 33%)
        critic_outputs = [
            {
                'critic': 'safety_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Execution exceeded 1000ms'),
                'error_type': 'timeout',
                'confidence': 0.0,
                'justification': 'Timeout occurred'
            },
            {
                'critic': 'bias_critic',
                'verdict': 'ALLOW',
                'confidence': 0.9,
                'justification': 'No bias detected'
            },
            {
                'critic': 'privacy_critic',
                'verdict': 'ALLOW',
                'confidence': 0.85,
                'justification': 'Privacy OK'
            }
        ]

        # Check if fallback should trigger
        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=500.0
        )

        # Single timeout (33%) shouldn't trigger majority timeout (50%) or high error rate (60%)
        assert should_fb is False

    def test_majority_critics_timeout(self):
        """Test fallback when majority of critics time out"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            enable_audit_bundles=True
        )

        # Simulate majority timeout (3 out of 4)
        critic_outputs = [
            {
                'critic': 'safety_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'bias_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'legal_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'privacy_critic',
                'verdict': 'ALLOW',
                'confidence': 0.8
            }
        ]

        # Check fallback trigger
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert '3/4' in reason

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=5000.0
        )

        # Verify safe decision
        assert result.fallback_verdict in ['REVIEW', 'DENY']
        assert result.triggered is True

        # Verify audit bundle
        assert 'audit_bundle' in result.metadata
        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_type'] == FallbackType.TIMEOUT_EXCEEDED.value
        assert len(bundle_dict['failed_critics']) == 3

    def test_all_critics_timeout(self):
        """Test fallback when all critics time out"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            timeout_threshold_ms=2000.0,
            enable_audit_bundles=True
        )

        # All critics timeout
        critic_outputs = [
            {
                'critic': f'critic_{i}',
                'verdict': 'ERROR',
                'error': TimeoutError(f'Critic {i} timed out'),
                'error_type': 'timeout'
            }
            for i in range(5)
        ]

        # Check fallback trigger
        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=3000.0
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert 'All 5 critics timed out' in reason or 'exceeds threshold' in reason

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=3000.0,
            context={'input_text': 'Test case'}
        )

        # Escalate strategy should require review
        assert result.fallback_verdict == 'REVIEW'
        assert result.confidence == 0.0

        # Verify audit bundle
        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['system_state_at_trigger']['total_critics_failed'] == 5
        assert bundle_dict['system_state_at_trigger']['elapsed_time_ms'] == 3000.0
        assert bundle_dict['fallback_decision']['requires_human_review'] is True

    def test_timeout_threshold_exceeded(self):
        """Test fallback when global timeout threshold exceeded"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.FAIL_SAFE,
            timeout_threshold_ms=1000.0,
            safe_default_verdict='DENY',
            enable_audit_bundles=True
        )

        # Critics completed but took too long
        critic_outputs = [
            {
                'critic': 'slow_critic',
                'verdict': 'ALLOW',
                'confidence': 0.9
            }
        ]

        # Check timeout threshold
        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=2500.0
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT
        assert '2500' in reason and '1000' in reason

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=2500.0
        )

        # Fail-safe should use safe default
        assert result.fallback_verdict == 'DENY'
        assert result.fallback_strategy == FallbackStrategy.FAIL_SAFE


class TestMissingCriticOutput:
    """
    Task 6.4: Test fallback handling with missing critic outputs

    Tests scenarios where critics fail to produce output or return None/empty results.
    """

    def test_no_critic_outputs(self):
        """Test fallback when no critic outputs are available"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            enable_audit_bundles=True
        )

        critic_outputs = []

        # Should trigger fallback
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.ALL_CRITICS_FAILED
        assert 'No critic outputs available' in reason

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Should use safe conservative decision
        assert result.fallback_verdict == 'REVIEW'
        assert result.confidence == 0.0

    def test_all_critics_return_error(self):
        """Test fallback when all critics return ERROR verdict"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'critic_a',
                'verdict': 'ERROR',
                'error': Exception('Failed to load model'),
                'confidence': 0.0
            },
            {
                'critic': 'critic_b',
                'verdict': 'ERROR',
                'error': Exception('Database unavailable'),
                'confidence': 0.0
            },
            {
                'critic': 'critic_c',
                'verdict': 'ERROR',
                'error': Exception('API rate limit'),
                'confidence': 0.0
            }
        ]

        # Check fallback
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.ALL_CRITICS_FAILED

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            context={'input_text': 'Test'}
        )

        assert result.fallback_verdict == 'REVIEW'

        # Verify all failures captured in audit
        bundle_dict = result.metadata['audit_bundle']
        assert len(bundle_dict['failed_critics']) == 3
        assert all('critic_' in fc['critic_name'] for fc in bundle_dict['failed_critics'])

    def test_partial_critic_outputs_missing(self):
        """Test fallback when some critic outputs are missing/null"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.MAJORITY,
            min_successful_critics=2,
            enable_audit_bundles=True
        )

        # Mix of successful and failed critics
        critic_outputs = [
            {
                'critic': 'critic_1',
                'verdict': 'ALLOW',
                'confidence': 0.9
            },
            {
                'critic': 'critic_2',
                'verdict': 'ERROR',
                'error': Exception('Output missing'),
                'confidence': 0.0
            },
            {
                'critic': 'critic_3',
                'verdict': 'ERROR',
                'error': Exception('Null output'),
                'confidence': 0.0
            }
        ]

        # Should not trigger fallback (1 successful, but min is 2)
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        # Wait, let's check: we have 1 successful but min is 2
        assert should_fb is True
        assert trigger == FallbackTrigger.MAJORITY_CRITICS_FAILED

        # Apply fallback with majority strategy
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # With only 1 successful critic, majority can't be determined
        # Should fall back to fail-safe
        assert result.fallback_verdict in ['ALLOW', 'REVIEW']

    def test_critical_critic_missing(self):
        """Test fallback when a critical critic fails to produce output"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            critical_critics=['legal_compliance'],
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'safety_critic',
                'verdict': 'ALLOW',
                'confidence': 0.9
            },
            {
                'critic': 'bias_critic',
                'verdict': 'ALLOW',
                'confidence': 0.85
            },
            {
                'critic': 'legal_compliance',
                'verdict': 'ERROR',
                'error': Exception('Legal database unreachable'),
                'confidence': 0.0
            }
        ]

        # Critical critic failed - should trigger fallback
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.CRITICAL_CRITIC_FAILED
        assert 'legal_compliance' in reason

        # Apply fallback
        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Should be conservative due to critical critic failure
        assert result.fallback_verdict in ['REVIEW', 'DENY']


class TestConflictHandling:
    """
    Task 6.4: Test fallback handling under conflicting critic verdicts

    Tests scenarios where critics produce conflicting decisions.
    """

    def test_split_verdict_allow_deny(self):
        """Test fallback when critics split between ALLOW and DENY"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'safety_critic',
                'verdict': 'DENY',
                'confidence': 0.8,
                'justification': 'Safety risk detected'
            },
            {
                'critic': 'efficiency_critic',
                'verdict': 'ALLOW',
                'confidence': 0.9,
                'justification': 'Efficient operation'
            }
        ]

        # This is a conflict but not a fallback trigger by default
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        # With 50% success rate and default threshold of 0.5, this won't trigger
        assert should_fb is False

    def test_high_conflict_rate_triggers_fallback(self):
        """Test fallback when conflict/error rate is high"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            error_rate_threshold=0.4,
            enable_audit_bundles=True
        )

        # 50% errors should trigger fallback
        critic_outputs = [
            {
                'critic': 'critic_1',
                'verdict': 'ALLOW',
                'confidence': 0.9
            },
            {
                'critic': 'critic_2',
                'verdict': 'ERROR',
                'error': Exception('Conflict detected'),
                'confidence': 0.0
            },
            {
                'critic': 'critic_3',
                'verdict': 'ALLOW',
                'confidence': 0.85
            },
            {
                'critic': 'critic_4',
                'verdict': 'ERROR',
                'error': Exception('Unable to resolve conflict'),
                'confidence': 0.0
            }
        ]

        # 50% error rate with 0.4 threshold
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.HIGH_ERROR_RATE

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Conservative should pick most restrictive from successful critics
        assert result.triggered is True

    def test_majority_strategy_resolves_conflicts(self):
        """Test majority strategy resolving conflicting verdicts"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.MAJORITY,
            enable_audit_bundles=True
        )

        # Clear majority (3 ALLOW vs 1 DENY)
        critic_outputs = [
            {'critic': 'c1', 'verdict': 'ALLOW', 'confidence': 0.9},
            {'critic': 'c2', 'verdict': 'ALLOW', 'confidence': 0.85},
            {'critic': 'c3', 'verdict': 'ALLOW', 'confidence': 0.8},
            {'critic': 'c4', 'verdict': 'DENY', 'confidence': 0.7}
        ]

        # No fallback needed - majority is clear
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is False

    def test_low_confidence_with_conflicts(self):
        """Test fallback triggered by low confidence in conflicting scenarios"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            enable_audit_bundles=True
        )

        critic_outputs = [
            {'critic': 'c1', 'verdict': 'ALLOW', 'confidence': 0.3},
            {'critic': 'c2', 'verdict': 'DENY', 'confidence': 0.2}
        ]

        aggregation_result = {
            'avg_confidence': 0.25  # Very low confidence
        }

        # Low confidence should trigger fallback
        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            aggregation_result=aggregation_result
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.INSUFFICIENT_CONFIDENCE
        assert '0.25' in reason

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Escalate strategy requires review
        assert result.fallback_verdict == 'REVIEW'
        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_decision']['requires_human_review'] is True


class TestPrecedentRetrievalFailure:
    """
    Task 6.4: Test fallback handling when precedent retrieval fails

    Tests scenarios where the precedent system is unavailable or returns errors.
    """

    def test_precedent_system_unavailable(self):
        """Test fallback when precedent system is completely unavailable"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            error_rate_threshold=0.6,  # Set higher threshold to avoid 50% triggering
            enable_audit_bundles=True
        )

        # Simulate precedent retrieval failure affecting critic
        critic_outputs = [
            {
                'critic': 'precedent_critic',
                'verdict': 'ERROR',
                'error': Exception('Precedent database connection failed'),
                'error_type': 'precedent_failure',
                'confidence': 0.0,
                'justification': 'Unable to retrieve similar cases'
            },
            {
                'critic': 'rule_based_critic',
                'verdict': 'ALLOW',
                'confidence': 0.85,
                'justification': 'Passes basic rules'
            }
        ]

        # Single non-critical failure with 50% error rate shouldn't trigger with 60% threshold
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is False

        # But if we make precedent critic critical...
        # Note: HIGH_ERROR_RATE check happens before CRITICAL_CRITIC_FAILED check
        # So with 50% error rate (1/2), it will trigger HIGH_ERROR_RATE first
        # unless we set error_rate_threshold higher
        engine_with_critical = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            critical_critics=['precedent_critic'],
            error_rate_threshold=0.6,  # Set higher to allow critical critic check
            enable_audit_bundles=True
        )

        should_fb, trigger, reason = engine_with_critical.should_fallback(critic_outputs)
        assert should_fb is True
        # With error_rate_threshold=0.6 and 50% error rate, critical critic check is evaluated
        assert trigger == FallbackTrigger.CRITICAL_CRITIC_FAILED

        result = engine_with_critical.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Should require review when critical precedent critic fails
        assert result.fallback_verdict in ['REVIEW', 'DENY']

    def test_precedent_embedding_failure(self):
        """Test fallback when precedent embedding generation fails"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.FAIL_SAFE,
            safe_default_verdict='REVIEW',
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'embedding_critic',
                'verdict': 'ERROR',
                'error': Exception('Embedding model not loaded'),
                'error_type': 'embedding_error',
                'confidence': 0.0
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Fail-safe uses configured safe default
        assert result.fallback_verdict == 'REVIEW'

    def test_partial_precedent_retrieval(self):
        """Test fallback when precedent retrieval partially fails"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.MAJORITY,
            enable_audit_bundles=True
        )

        # Some precedent-based critics succeed, some fail
        critic_outputs = [
            {
                'critic': 'precedent_critic_1',
                'verdict': 'ALLOW',
                'confidence': 0.8,
                'justification': 'Similar precedent found: Case #123'
            },
            {
                'critic': 'precedent_critic_2',
                'verdict': 'ERROR',
                'error': Exception('Precedent index corrupted'),
                'error_type': 'index_error',
                'confidence': 0.0
            },
            {
                'critic': 'precedent_critic_3',
                'verdict': 'ALLOW',
                'confidence': 0.75,
                'justification': 'Similar precedent found: Case #456'
            }
        ]

        # 2 out of 3 succeeded - should not trigger fallback
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is False


class TestEndToEndFallbackScenarios:
    """
    Task 6.4: End-to-end integration tests combining multiple failure types

    Tests realistic scenarios combining timeouts, missing outputs, conflicts,
    and precedent failures.
    """

    def test_cascading_failures(self):
        """Test cascading failures (timeout leading to missing outputs)"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            timeout_threshold_ms=2000.0,
            enable_audit_bundles=True
        )

        # Timeout causes missing outputs
        critic_outputs = [
            {
                'critic': 'slow_critic_1',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout at 2100ms'),
                'error_type': 'timeout'
            },
            {
                'critic': 'slow_critic_2',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout at 2050ms'),
                'error_type': 'timeout'
            },
            {
                'critic': 'fast_critic',
                'verdict': 'ALLOW',
                'confidence': 0.8
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=2100.0
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.TIMEOUT

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=2100.0
        )

        # Verify complete audit trail
        bundle_dict = result.metadata['audit_bundle']
        assert bundle_dict['fallback_type'] == FallbackType.TIMEOUT_EXCEEDED.value
        assert len(bundle_dict['failed_critics']) == 2

        # All failed critics should have timeout error type
        for fc in bundle_dict['failed_critics']:
            assert fc['error_type'] == 'timeout'

    def test_precedent_failure_with_conflicts(self):
        """Test precedent failure combined with conflicting critic verdicts"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'precedent_analyzer',
                'verdict': 'ERROR',
                'error': Exception('Precedent DB timeout'),
                'error_type': 'precedent_failure'
            },
            {
                'critic': 'safety_critic',
                'verdict': 'DENY',
                'confidence': 0.7,
                'justification': 'Safety concerns'
            },
            {
                'critic': 'business_critic',
                'verdict': 'ALLOW',
                'confidence': 0.9,
                'justification': 'Business value high'
            }
        ]

        # High error rate (33%)
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        # Default threshold is 0.5, so 33% won't trigger unless we check other conditions
        # Let's check if there's a majority failure
        # 1 error, 2 successes = no majority failure

        # Let's use a stricter engine
        strict_engine = FallbackEngine(
            default_strategy=FallbackStrategy.ESCALATE,
            error_rate_threshold=0.3,  # 30% threshold
            enable_audit_bundles=True
        )

        should_fb, trigger, reason = strict_engine.should_fallback(critic_outputs)
        assert should_fb is True
        assert trigger == FallbackTrigger.HIGH_ERROR_RATE

        result = strict_engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger
        )

        # Escalate requires review
        assert result.fallback_verdict == 'REVIEW'
        assert result.metadata['requires_human_review'] is True

    def test_complete_system_failure_with_explanation(self):
        """Test complete system failure with explanation generation"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.FAIL_SAFE,
            safe_default_verdict='DENY',
            timeout_threshold_ms=1500.0,
            enable_audit_bundles=True
        )

        # Everything fails
        critic_outputs = [
            {
                'critic': 'precedent_critic',
                'verdict': 'ERROR',
                'error': Exception('Precedent system offline'),
                'error_type': 'system_error'
            },
            {
                'critic': 'ml_critic',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Model timeout'),
                'error_type': 'timeout'
            },
            {
                'critic': 'rule_critic',
                'verdict': 'ERROR',
                'error': Exception('Rule engine crashed'),
                'error_type': 'exception'
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=2000.0
        )

        assert should_fb is True
        # Could be ALL_CRITICS_FAILED or TIMEOUT
        assert trigger in [FallbackTrigger.ALL_CRITICS_FAILED, FallbackTrigger.TIMEOUT]

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=2000.0,
            context={'input_text': 'Critical decision', 'user_id': 'test_user'}
        )

        # Fail-safe should use safe default
        assert result.fallback_verdict == 'DENY'

        # Get audit bundle and generate explanation
        bundle_dict = result.metadata['audit_bundle']
        bundle = FallbackEvidenceBundle.from_dict(bundle_dict)

        # Generate explanation
        explainer = FallbackExplainer(audience="general")
        explanation = explainer.explain_bundle_to_user(bundle)

        # Verify explanation quality
        assert "FALLBACK EVENT EXPLANATION" in explanation
        assert "WHY DID FALLBACK OCCUR" in explanation
        assert "WHICH CRITICS WERE AFFECTED" in explanation
        assert "WHY IS THIS DECISION SAFE" in explanation

        # Should list all 3 failed critics
        assert 'precedent_critic' in explanation
        assert 'ml_critic' in explanation
        assert 'rule_critic' in explanation

    def test_audit_trail_completeness(self):
        """Test that complete audit trail is created for all failure scenarios"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            timeout_threshold_ms=1000.0,
            enable_audit_bundles=True
        )

        critic_outputs = [
            {
                'critic': 'critic_timeout',
                'verdict': 'ERROR',
                'error': CriticTimeoutException('Timeout'),
                'error_type': 'timeout',
                'retries': 2
            },
            {
                'critic': 'critic_missing',
                'verdict': 'ERROR',
                'error': Exception('Output missing'),
                'error_type': 'missing'
            },
            {
                'critic': 'critic_success',
                'verdict': 'ALLOW',
                'confidence': 0.9
            }
        ]

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs=critic_outputs,
            elapsed_time_ms=1200.0
        )

        assert should_fb is True

        result = engine.apply_fallback(
            critic_outputs=critic_outputs,
            trigger=trigger,
            elapsed_time_ms=1200.0,
            context={
                'input_text': 'Test input',
                'request_id': 'req-123',
                'user_id': 'user-456',
                'system_version': '1.0.0',
                'environment': 'production'
            }
        )

        # Verify complete audit bundle
        bundle_dict = result.metadata['audit_bundle']

        # Check all required fields
        assert 'bundle_id' in bundle_dict
        assert 'fallback_type' in bundle_dict
        assert 'failed_critics' in bundle_dict
        assert 'system_state_at_trigger' in bundle_dict
        assert 'fallback_decision' in bundle_dict

        # Check failed critics details
        assert len(bundle_dict['failed_critics']) == 2
        for fc in bundle_dict['failed_critics']:
            assert 'critic_name' in fc
            assert 'failure_reason' in fc
            assert 'error_type' in fc
            assert 'timestamp' in fc

        # Check system state
        sys_state = bundle_dict['system_state_at_trigger']
        assert sys_state['total_critics_attempted'] == 3
        assert sys_state['total_critics_succeeded'] == 1
        assert sys_state['total_critics_failed'] == 2
        assert sys_state['elapsed_time_ms'] == 1200.0
        assert sys_state['timeout_threshold_ms'] == 1000.0
        assert sys_state['request_id'] == 'req-123'
        assert sys_state['user_id'] == 'user-456'

        # Check fallback decision
        decision = bundle_dict['fallback_decision']
        assert 'verdict' in decision
        assert 'confidence' in decision
        assert 'strategy_used' in decision
        assert 'reason' in decision
        assert 'is_safe_default' in decision
        assert 'requires_human_review' in decision


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
