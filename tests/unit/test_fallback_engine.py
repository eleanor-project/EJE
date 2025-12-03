"""
Comprehensive tests for Fallback Engine functionality.

Tests cover:
- Fallback trigger detection
- Fallback strategy application
- Fallback evidence bundle creation
- Fallback explanation generation
- Edge cases and error handling
"""

import pytest
from datetime import datetime

from ejc.core.fallback.fallback_engine import (
    FallbackEngine,
    FallbackStrategy,
    FallbackTrigger,
    FallbackResult,
    create_fallback_engine,
)
from ejc.core.fallback.fallback_bundle import (
    create_fallback_evidence_bundle,
    create_partial_failure_bundle,
    augment_bundle_with_fallback,
)
from ejc.core.fallback.fallback_explainer import (
    FallbackExplainer,
    explain_fallback_simple,
    create_fallback_audit_record,
)
from ejc.core.evidence_normalizer import EvidenceNormalizer


class TestFallbackEngine:
    """Tests for fallback engine core functionality"""

    def test_engine_initialization(self):
        """Test fallback engine initialization"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            error_rate_threshold=0.5,
            min_successful_critics=1
        )

        assert engine.default_strategy == FallbackStrategy.CONSERVATIVE
        assert engine.error_rate_threshold == 0.5

    def test_should_fallback_all_critics_failed(self):
        """Test fallback trigger when all critics fail"""
        engine = FallbackEngine()

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR'},
            {'critic': 'critic2', 'verdict': 'ERROR'},
            {'critic': 'critic3', 'verdict': 'ERROR'},
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.ALL_CRITICS_FAILED
        assert "All" in reason

    def test_should_fallback_majority_failed(self):
        """Test fallback trigger when majority of critics fail"""
        engine = FallbackEngine()

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW'},
            {'critic': 'critic2', 'verdict': 'ERROR'},
            {'critic': 'critic3', 'verdict': 'ERROR'},
            {'critic': 'critic4', 'verdict': 'ERROR'},
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.MAJORITY_CRITICS_FAILED

    def test_should_fallback_high_error_rate(self):
        """Test fallback trigger on high error rate"""
        engine = FallbackEngine(error_rate_threshold=0.4)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW'},
            {'critic': 'critic2', 'verdict': 'ALLOW'},
            {'critic': 'critic3', 'verdict': 'ERROR'},
            {'critic': 'critic4', 'verdict': 'ERROR'},
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.HIGH_ERROR_RATE

    def test_should_fallback_critical_critic_failed(self):
        """Test fallback trigger when critical critic fails"""
        engine = FallbackEngine(critical_critics=['safety_critic'])

        critic_outputs = [
            {'critic': 'safety_critic', 'verdict': 'ERROR'},
            {'critic': 'other_critic', 'verdict': 'ALLOW'},
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is True
        assert trigger == FallbackTrigger.CRITICAL_CRITIC_FAILED
        assert 'safety_critic' in reason

    def test_should_fallback_insufficient_confidence(self):
        """Test fallback trigger on very low confidence"""
        engine = FallbackEngine()

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9},
        ]

        aggregation_result = {'avg_confidence': 0.2}  # Very low

        should_fb, trigger, reason = engine.should_fallback(
            critic_outputs,
            aggregation_result
        )

        assert should_fb is True
        assert trigger == FallbackTrigger.INSUFFICIENT_CONFIDENCE

    def test_no_fallback_needed(self):
        """Test that fallback not triggered when all is well"""
        engine = FallbackEngine()

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9},
            {'critic': 'critic2', 'verdict': 'DENY', 'confidence': 0.85},
            {'critic': 'critic3', 'verdict': 'ALLOW', 'confidence': 0.92},
        ]

        should_fb, trigger, reason = engine.should_fallback(critic_outputs)

        assert should_fb is False

    def test_conservative_strategy_with_denies(self):
        """Test conservative strategy defaults to most restrictive"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.CONSERVATIVE)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9},
            {'critic': 'critic2', 'verdict': 'DENY', 'confidence': 0.85},
            {'critic': 'critic3', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.HIGH_ERROR_RATE
        )

        assert result.fallback_verdict == 'DENY'
        assert result.triggered is True

    def test_conservative_strategy_defaults_to_review(self):
        """Test conservative strategy defaults to REVIEW when no DENY"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.CONSERVATIVE)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9},
            {'critic': 'critic2', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.HIGH_ERROR_RATE
        )

        assert result.fallback_verdict == 'REVIEW'

    def test_permissive_strategy(self):
        """Test permissive strategy allows with warnings"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.PERMISSIVE)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.8},
            {'critic': 'critic2', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.MAJORITY_CRITICS_FAILED
        )

        assert result.fallback_verdict == 'ALLOW'
        assert 'warning' in result.metadata

    def test_escalate_strategy(self):
        """Test escalate strategy always escalates"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.ESCALATE)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.ALL_CRITICS_FAILED
        )

        assert result.fallback_verdict == 'REVIEW'
        assert result.metadata['requires_human_review'] is True

    def test_fail_safe_strategy(self):
        """Test fail-safe strategy uses configured default"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.FAIL_SAFE,
            safe_default_verdict='DENY'
        )

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.ALL_CRITICS_FAILED
        )

        assert result.fallback_verdict == 'DENY'

    def test_majority_strategy(self):
        """Test majority strategy uses majority verdict"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.MAJORITY)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9},
            {'critic': 'critic2', 'verdict': 'ALLOW', 'confidence': 0.85},
            {'critic': 'critic3', 'verdict': 'DENY', 'confidence': 0.8},
            {'critic': 'critic4', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.HIGH_ERROR_RATE
        )

        assert result.fallback_verdict == 'ALLOW'  # 2 ALLOW vs 1 DENY
        assert 'verdict_distribution' in result.metadata

    def test_majority_strategy_fallback_on_all_errors(self):
        """Test majority strategy falls back to fail-safe on all errors"""
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.MAJORITY,
            safe_default_verdict='REVIEW'
        )

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ERROR'},
            {'critic': 'critic2', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.ALL_CRITICS_FAILED
        )

        # Should fall back to fail-safe
        assert result.fallback_verdict == 'REVIEW'

    def test_confidence_reduction(self):
        """Test that confidence is reduced during fallback"""
        engine = FallbackEngine(default_strategy=FallbackStrategy.CONSERVATIVE)

        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 1.0},
            {'critic': 'critic2', 'verdict': 'ERROR'},
        ]

        result = engine.apply_fallback(
            critic_outputs,
            FallbackTrigger.HIGH_ERROR_RATE
        )

        # Confidence should be reduced from 1.0
        assert result.confidence < 1.0


class TestFallbackBundle:
    """Tests for fallback evidence bundle creation"""

    def test_create_fallback_evidence_bundle(self):
        """Test creating fallback evidence bundle"""
        critic_outputs = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9, 'justification': 'OK'},
            {'critic': 'critic2', 'verdict': 'ERROR', 'confidence': 0.0, 'justification': 'Failed'},
        ]

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason='high_error_rate',
            fallback_strategy=FallbackStrategy.CONSERVATIVE,
            fallback_verdict='REVIEW',
            confidence=0.7,
            reason='Fallback applied due to errors'
        )

        bundle = create_fallback_evidence_bundle(
            input_text='Test input',
            input_context={'domain': 'test'},
            critic_outputs=critic_outputs,
            fallback_result=fallback_result
        )

        assert bundle is not None
        assert bundle.metadata.flags.is_fallback is True
        # Should have original critics + fallback critic
        assert len(bundle.critic_outputs) == 3  # 2 original + 1 fallback

        # Check fallback critic added
        fallback_critic = [c for c in bundle.critic_outputs if c.critic == 'fallback_engine']
        assert len(fallback_critic) == 1
        assert fallback_critic[0].verdict == 'REVIEW'

    def test_create_partial_failure_bundle(self):
        """Test creating bundle for partial failure scenario"""
        successful = [
            {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9, 'justification': 'OK'}
        ]

        failed = [
            {'critic': 'critic2', 'verdict': 'ERROR', 'confidence': 0.0, 'justification': 'Failed'}
        ]

        bundle = create_partial_failure_bundle(
            input_text='Test input',
            input_context={},
            successful_outputs=successful,
            failed_outputs=failed,
            aggregated_verdict='ALLOW'
        )

        assert bundle is not None
        assert bundle.metadata.flags.is_fallback is True
        # Should include justification about partial failure
        assert 'Partial failure' in bundle.justification_synthesis.summary

    def test_augment_bundle_with_fallback(self):
        """Test augmenting existing bundle with fallback info"""
        # Create normal bundle first
        normalizer = EvidenceNormalizer()
        bundle = normalizer.normalize(
            input_text='Test',
            critic_outputs=[
                {'critic': 'critic1', 'verdict': 'ALLOW', 'confidence': 0.9, 'justification': 'OK'}
            ]
        )

        original_count = len(bundle.critic_outputs)

        # Create fallback result
        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason='test_trigger',
            fallback_strategy=FallbackStrategy.ESCALATE,
            fallback_verdict='REVIEW',
            confidence=0.5,
            reason='Test fallback'
        )

        # Augment bundle
        augmented = augment_bundle_with_fallback(bundle, fallback_result)

        assert augmented.metadata.flags.is_fallback is True
        assert len(augmented.critic_outputs) == original_count + 1  # Fallback critic added
        assert 'Fallback applied' in augmented.justification_synthesis.summary


class TestFallbackExplainer:
    """Tests for fallback explanation generation"""

    def test_explainer_initialization(self):
        """Test explainer initialization with different audiences"""
        explainer_general = FallbackExplainer(audience='general')
        explainer_technical = FallbackExplainer(audience='technical')
        explainer_executive = FallbackExplainer(audience='executive')

        assert explainer_general.audience == 'general'
        assert explainer_technical.audience == 'technical'
        assert explainer_executive.audience == 'executive'

    def test_explain_fallback_structure(self):
        """Test fallback explanation structure"""
        explainer = FallbackExplainer()

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.HIGH_ERROR_RATE.value,
            fallback_strategy=FallbackStrategy.CONSERVATIVE,
            fallback_verdict='REVIEW',
            confidence=0.6,
            reason='High error rate detected'
        )

        explanation = explainer.explain_fallback(fallback_result)

        assert 'summary' in explanation
        assert 'trigger_explanation' in explanation
        assert 'strategy_explanation' in explanation
        assert 'decision_explanation' in explanation
        assert 'confidence_explanation' in explanation
        assert 'recommendations' in explanation

    def test_explain_to_user_general(self):
        """Test user-friendly explanation for general audience"""
        explainer = FallbackExplainer(audience='general')

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.ALL_CRITICS_FAILED.value,
            fallback_strategy=FallbackStrategy.ESCALATE,
            fallback_verdict='REVIEW',
            confidence=0.0,
            reason='All components failed'
        )

        text = explainer.explain_to_user(fallback_result)

        assert isinstance(text, str)
        assert len(text) > 0
        # Should be readable, not too technical
        assert 'Fallback' in text or 'backup' in text

    def test_explain_to_user_technical(self):
        """Test technical explanation"""
        explainer = FallbackExplainer(audience='technical')

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.CRITICAL_CRITIC_FAILED.value,
            fallback_strategy=FallbackStrategy.CONSERVATIVE,
            fallback_verdict='DENY',
            confidence=0.8,
            reason='Critical critic failure'
        )

        text = explainer.explain_to_user(fallback_result)

        # Should include technical details
        assert 'critic' in text.lower() or 'fallback' in text.lower()

    def test_explain_to_user_executive(self):
        """Test executive summary explanation"""
        explainer = FallbackExplainer(audience='executive')

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.TIMEOUT.value,
            fallback_strategy=FallbackStrategy.FAIL_SAFE,
            fallback_verdict='REVIEW',
            confidence=0.5,
            reason='Timeout occurred'
        )

        text = explainer.explain_to_user(fallback_result)

        # Should be concise and high-level
        assert len(text) < 1000  # Relatively short

    def test_format_for_audit(self):
        """Test audit trail formatting"""
        explainer = FallbackExplainer(audience='technical')

        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.MAJORITY_CRITICS_FAILED.value,
            fallback_strategy=FallbackStrategy.MAJORITY,
            fallback_verdict='ALLOW',
            confidence=0.65,
            reason='Majority verdict used',
            metadata={'successful': 2, 'failed': 3}
        )

        original_inputs = {
            'text': 'Original input text',
            'context': {'key': 'value'}
        }

        audit_record = explainer.format_for_audit(fallback_result, original_inputs)

        assert audit_record['event_type'] == 'fallback_triggered'
        assert 'timestamp' in audit_record
        assert 'trigger' in audit_record
        assert 'strategy' in audit_record
        assert 'outcome' in audit_record
        assert 'original_inputs' in audit_record

    def test_confidence_explanation_levels(self):
        """Test confidence level explanations"""
        explainer = FallbackExplainer(audience='general')

        # Test different confidence levels
        test_cases = [
            (0.95, 'high'),
            (0.75, 'moderate'),
            (0.55, 'low'),
            (0.25, 'very low')
        ]

        for confidence, expected_level in test_cases:
            explanation = explainer._explain_confidence(confidence)
            # Should mention level or describe confidence
            assert len(explanation) > 0

    def test_recommendations_generation(self):
        """Test that recommendations are generated appropriately"""
        explainer = FallbackExplainer()

        # Low confidence case
        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.HIGH_ERROR_RATE.value,
            fallback_strategy=FallbackStrategy.CONSERVATIVE,
            fallback_verdict='REVIEW',
            confidence=0.3,  # Low
            reason='High error rate'
        )

        recommendations = explainer._generate_recommendations(fallback_result)

        assert len(recommendations) > 0
        # Should recommend manual review for low confidence
        assert any('review' in r.lower() for r in recommendations)

    def test_convenience_functions(self):
        """Test convenience functions"""
        fallback_result = FallbackResult(
            triggered=True,
            trigger_reason=FallbackTrigger.ALL_CRITICS_FAILED.value,
            fallback_strategy=FallbackStrategy.ESCALATE,
            fallback_verdict='REVIEW',
            confidence=0.0,
            reason='All failed'
        )

        # Test explain_fallback_simple
        explanation = explain_fallback_simple(fallback_result, audience='general')
        assert isinstance(explanation, str)
        assert len(explanation) > 0

        # Test create_fallback_audit_record
        audit = create_fallback_audit_record(fallback_result)
        assert audit['event_type'] == 'fallback_triggered'


class TestFallbackEngineIntegration:
    """Integration tests for complete fallback workflow"""

    def test_end_to_end_fallback_workflow(self):
        """Test complete fallback workflow: detect -> apply -> bundle -> explain"""
        # Create engine
        engine = FallbackEngine(
            default_strategy=FallbackStrategy.CONSERVATIVE,
            error_rate_threshold=0.5
        )

        # Simulate critic failure scenario
        critic_outputs = [
            {'critic': 'bias_critic', 'verdict': 'ALLOW', 'confidence': 0.95, 'justification': 'No bias'},
            {'critic': 'harm_critic', 'verdict': 'ERROR', 'confidence': 0.0, 'justification': 'Failed'},
            {'critic': 'safety_critic', 'verdict': 'ERROR', 'confidence': 0.0, 'justification': 'Failed'},
        ]

        # Step 1: Check if fallback needed
        should_fb, trigger, reason = engine.should_fallback(critic_outputs)
        assert should_fb is True

        # Step 2: Apply fallback strategy
        fallback_result = engine.apply_fallback(
            critic_outputs,
            trigger,
            context={'input_text': 'Test input'}
        )
        assert fallback_result.triggered is True

        # Step 3: Create evidence bundle
        bundle = create_fallback_evidence_bundle(
            input_text='Test input for fallback',
            input_context={'domain': 'test'},
            critic_outputs=critic_outputs,
            fallback_result=fallback_result
        )
        assert bundle.metadata.flags.is_fallback is True

        # Step 4: Generate explanation
        explainer = FallbackExplainer(audience='technical')
        explanation = explainer.explain_fallback(fallback_result)
        assert 'summary' in explanation

        # Step 5: Create audit record
        audit = explainer.format_for_audit(
            fallback_result,
            {'text': 'Test input'}
        )
        assert audit['event_type'] == 'fallback_triggered'

    def test_create_fallback_engine_convenience(self):
        """Test convenience function for creating fallback engine"""
        engine = create_fallback_engine(
            strategy='conservative',
            error_threshold=0.4
        )

        assert engine.default_strategy == FallbackStrategy.CONSERVATIVE
        assert engine.error_rate_threshold == 0.4
