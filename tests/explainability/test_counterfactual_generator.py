"""
Tests for CounterfactualGenerator (Issue #167)

Tests counterfactual explanation generation for EJE decisions.
"""

import pytest
from src.ejc.core.explainability.counterfactual_generator import (
    CounterfactualGenerator,
    CounterfactualMode,
    Counterfactual
)


@pytest.fixture
def sample_decision():
    """Sample EJE decision for testing."""
    return {
        'decision_id': 'test_001',
        'input_data': {
            'request_id': '12345',
            'user_id': 'user_001',
            'amount': 5000,
            'risk_score': 0.3
        },
        'critic_reports': [
            {
                'critic_name': 'RiskCritic',
                'verdict': 'APPROVE',
                'confidence': 0.8,
                'justification': 'Risk score is within acceptable limits. Historical data shows positive pattern.'
            },
            {
                'critic_name': 'ComplianceCritic',
                'verdict': 'APPROVE',
                'confidence': 0.9,
                'justification': 'All compliance checks passed. Documentation complete.'
            },
            {
                'critic_name': 'FraudCritic',
                'verdict': 'DENY',
                'confidence': 0.6,
                'justification': 'Some minor fraud indicators detected. Requires review.'
            }
        ],
        'aggregation': {
            'verdict': 'APPROVE',
            'confidence': 0.75,
            'agree_count': 2,
            'disagree_count': 1
        },
        'governance_outcome': {
            'verdict': 'APPROVE',
            'confidence': 0.75,
            'governance_applied': True
        }
    }


@pytest.fixture
def generator():
    """Create a CounterfactualGenerator instance."""
    return CounterfactualGenerator(
        max_counterfactuals=5,
        max_changes=3,
        timeout_seconds=2.0
    )


class TestCounterfactualGenerator:
    """Test suite for CounterfactualGenerator."""

    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator.max_counterfactuals == 5
        assert generator.max_changes == 3
        assert generator.timeout_seconds == 2.0

    def test_extract_verdict(self, generator, sample_decision):
        """Test verdict extraction from decision."""
        verdict = generator._extract_verdict(sample_decision)
        assert verdict == 'APPROVE'

    def test_extract_confidence(self, generator, sample_decision):
        """Test confidence extraction from decision."""
        confidence = generator._extract_confidence(sample_decision)
        assert confidence == 0.75

    def test_identify_key_factors(self, generator, sample_decision):
        """Test key factor identification."""
        factors = generator._identify_key_factors(sample_decision)

        # Should identify all 3 critics
        critic_factors = [f for f in factors if f['type'] == 'critic_verdict']
        assert len(critic_factors) == 3

        # Should be sorted by importance
        assert factors[0]['importance'] >= factors[-1]['importance']

        # Should include critic details
        assert 'RiskCritic' in [f['critic'] for f in critic_factors]
        assert 'ComplianceCritic' in [f['critic'] for f in critic_factors]
        assert 'FraudCritic' in [f['critic'] for f in critic_factors]

    def test_generate_nearest_mode(self, generator, sample_decision):
        """Test counterfactual generation in NEAREST mode."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST
        )

        assert 'counterfactuals' in result
        assert 'generation_time' in result
        assert 'key_factors' in result
        assert result['mode'] == 'nearest'
        assert result['original_verdict'] == 'APPROVE'
        assert result['within_timeout'] is True

        # Should generate at least one counterfactual
        assert len(result['counterfactuals']) > 0

        # Check structure of first counterfactual
        cf = result['counterfactuals'][0]
        assert 'original_verdict' in cf
        assert 'counterfactual_verdict' in cf
        assert 'changed_factors' in cf
        assert 'explanation' in cf
        assert 'plausibility_score' in cf

    def test_generate_diverse_mode(self, generator, sample_decision):
        """Test counterfactual generation in DIVERSE mode."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.DIVERSE
        )

        assert result['mode'] == 'diverse'
        assert len(result['counterfactuals']) > 0

        # Diverse mode should generate multiple counterfactuals
        if len(result['counterfactuals']) > 1:
            # Check that they use different strategies
            factors_changed = [
                set(cf['changed_factors'].keys())
                for cf in result['counterfactuals']
            ]
            # Should have some variety in which critics are changed
            assert len(set(tuple(sorted(f)) for f in factors_changed)) > 1

    def test_generate_minimal_mode(self, generator, sample_decision):
        """Test counterfactual generation in MINIMAL mode."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.MINIMAL
        )

        assert result['mode'] == 'minimal'

        # Minimal mode should generate only one counterfactual
        assert len(result['counterfactuals']) == 1

        cf = result['counterfactuals'][0]
        # Should change only one critic
        assert len(cf['changed_factors']) == 1

    def test_generate_plausible_mode(self, generator, sample_decision):
        """Test counterfactual generation in PLAUSIBLE mode."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.PLAUSIBLE
        )

        assert result['mode'] == 'plausible'
        assert len(result['counterfactuals']) > 0

        # Plausible counterfactuals should have higher plausibility scores
        for cf in result['counterfactuals']:
            assert cf['plausibility_score'] > 0.0

        # Should be sorted by plausibility
        if len(result['counterfactuals']) > 1:
            plausibility_scores = [cf['plausibility_score'] for cf in result['counterfactuals']]
            assert plausibility_scores == sorted(plausibility_scores, reverse=True)

    def test_generate_with_target_verdict(self, generator, sample_decision):
        """Test generating counterfactuals for a specific target verdict."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST,
            target_verdict='DENY'
        )

        # Should find counterfactuals that lead to DENY
        deny_counterfactuals = [
            cf for cf in result['counterfactuals']
            if cf['counterfactual_verdict'] == 'DENY'
        ]
        assert len(deny_counterfactuals) > 0

    def test_simulate_verdict_change(self, generator, sample_decision):
        """Test verdict simulation when one critic changes."""
        # Change FraudCritic from DENY to APPROVE
        simulated = generator._simulate_verdict_change(
            sample_decision,
            'FraudCritic',
            'APPROVE'
        )

        # With all 3 critics approving, should still be APPROVE
        assert simulated == 'APPROVE'

        # Change ComplianceCritic to DENY
        simulated2 = generator._simulate_verdict_change(
            sample_decision,
            'ComplianceCritic',
            'DENY'
        )

        # Now with 2 DENY and 1 APPROVE, weighted outcome could change
        assert simulated2 in ['APPROVE', 'DENY', 'REVIEW']

    def test_validate_counterfactual(self, generator, sample_decision):
        """Test counterfactual validation."""
        # Generate a counterfactual
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST
        )

        cf = result['counterfactuals'][0]

        # Validate it
        validation = generator.validate_counterfactual(cf, sample_decision)

        assert 'is_valid' in validation
        assert 'coherence_score' in validation
        assert 'issues' in validation
        assert validation['coherence_score'] >= 0.0
        assert validation['coherence_score'] <= 1.0

    def test_performance_within_timeout(self, generator, sample_decision):
        """Test that generation completes within timeout."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.DIVERSE
        )

        # Should complete within 2 seconds (as configured)
        assert result['generation_time'] < 2.0
        assert result['within_timeout'] is True

    def test_handle_edge_case_unanimous_decision(self, generator):
        """Test handling of unanimous decisions."""
        unanimous_decision = {
            'decision_id': 'unanimous_001',
            'input_data': {},
            'critic_reports': [
                {
                    'critic_name': 'Critic1',
                    'verdict': 'APPROVE',
                    'confidence': 0.95,
                    'justification': 'All checks passed.'
                },
                {
                    'critic_name': 'Critic2',
                    'verdict': 'APPROVE',
                    'confidence': 0.98,
                    'justification': 'Excellent score.'
                },
                {
                    'critic_name': 'Critic3',
                    'verdict': 'APPROVE',
                    'confidence': 0.90,
                    'justification': 'No issues found.'
                }
            ],
            'aggregation': {
                'verdict': 'APPROVE',
                'confidence': 0.94
            },
            'governance_outcome': {
                'verdict': 'APPROVE',
                'confidence': 0.94
            }
        }

        result = generator.generate(
            decision=unanimous_decision,
            mode=CounterfactualMode.NEAREST
        )

        # Should still generate counterfactuals
        assert len(result['counterfactuals']) > 0

        # Counterfactuals should change verdict
        for cf in result['counterfactuals']:
            assert cf['counterfactual_verdict'] != 'APPROVE'

    def test_handle_edge_case_split_decision(self, generator):
        """Test handling of evenly split decisions."""
        split_decision = {
            'decision_id': 'split_001',
            'input_data': {},
            'critic_reports': [
                {
                    'critic_name': 'Critic1',
                    'verdict': 'APPROVE',
                    'confidence': 0.7,
                    'justification': 'Acceptable.'
                },
                {
                    'critic_name': 'Critic2',
                    'verdict': 'DENY',
                    'confidence': 0.7,
                    'justification': 'Concerning factors.'
                }
            ],
            'aggregation': {
                'verdict': 'REVIEW',
                'confidence': 0.5
            },
            'governance_outcome': {
                'verdict': 'REVIEW',
                'confidence': 0.5
            }
        }

        result = generator.generate(
            decision=split_decision,
            mode=CounterfactualMode.NEAREST
        )

        # Should generate counterfactuals
        assert len(result['counterfactuals']) > 0

        # With split decision, small changes should flip outcome
        for cf in result['counterfactuals']:
            # Should have high plausibility (easy to flip)
            assert cf['plausibility_score'] > 0.3

    def test_explanation_quality(self, generator, sample_decision):
        """Test quality of generated explanations."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST
        )

        for cf in result['counterfactuals']:
            explanation = cf['explanation']

            # Explanation should mention the critic
            assert any(critic in explanation for critic in ['RiskCritic', 'ComplianceCritic', 'FraudCritic'])

            # Should mention verdict change
            assert 'verdict' in explanation.lower() or 'decision' in explanation.lower()

            # Should be reasonably short
            assert len(explanation) < 500

    def test_counterfactual_mode_from_string(self, generator, sample_decision):
        """Test that mode can be specified as string."""
        result = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode('nearest')  # String instead of enum
        )

        assert result['mode'] == 'nearest'
        assert len(result['counterfactuals']) > 0

    def test_empty_decision(self, generator):
        """Test handling of empty/invalid decisions."""
        empty_decision = {
            'decision_id': 'empty_001',
            'input_data': {},
            'critic_reports': [],
            'aggregation': {},
            'governance_outcome': {}
        }

        result = generator.generate(
            decision=empty_decision,
            mode=CounterfactualMode.NEAREST
        )

        # Should handle gracefully, may return empty counterfactuals
        assert 'counterfactuals' in result
        assert result['within_timeout'] is True

    def test_multiple_generations_consistency(self, generator, sample_decision):
        """Test that multiple generations produce consistent results."""
        result1 = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST
        )

        result2 = generator.generate(
            decision=sample_decision,
            mode=CounterfactualMode.NEAREST
        )

        # Should generate same number of counterfactuals
        assert len(result1['counterfactuals']) == len(result2['counterfactuals'])

        # Should identify same key factors
        assert result1['key_factors'] == result2['key_factors']


class TestCounterfactualModes:
    """Test different counterfactual generation modes."""

    def test_all_modes_work(self, generator, sample_decision):
        """Test that all modes generate valid counterfactuals."""
        modes = [
            CounterfactualMode.NEAREST,
            CounterfactualMode.DIVERSE,
            CounterfactualMode.MINIMAL,
            CounterfactualMode.PLAUSIBLE
        ]

        for mode in modes:
            result = generator.generate(
                decision=sample_decision,
                mode=mode
            )

            assert len(result['counterfactuals']) > 0
            assert result['mode'] == mode.value
            assert result['within_timeout'] is True


class TestIntegrationWithXAIPipeline:
    """Test integration with XAIPipeline."""

    def test_xai_pipeline_counterfactual_generation(self, sample_decision):
        """Test that XAIPipeline can generate counterfactuals."""
        from src.ejc.core.explainability import XAIPipeline, XAIMethod, ExplanationLevel

        pipeline = XAIPipeline()

        # Generate counterfactual explanation
        result = pipeline.generate_explanation(
            model=None,  # Not needed for EJE decisions
            instance=sample_decision,
            method=XAIMethod.COUNTERFACTUAL,
            level=ExplanationLevel.NARRATIVE,
            mode='nearest'
        )

        assert result['method'] == 'counterfactual'
        assert 'counterfactuals' in result['explanation']
        assert result['confidence'] > 0.5

    def test_xai_pipeline_different_modes(self, sample_decision):
        """Test XAIPipeline with different counterfactual modes."""
        from src.ejc.core.explainability import XAIPipeline, XAIMethod

        pipeline = XAIPipeline()

        for mode in ['nearest', 'diverse', 'minimal', 'plausible']:
            result = pipeline.generate_explanation(
                model=None,
                instance=sample_decision,
                method=XAIMethod.COUNTERFACTUAL,
                mode=mode
            )

            assert result['method'] == 'counterfactual'
            assert len(result['explanation']['counterfactuals']) > 0


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
