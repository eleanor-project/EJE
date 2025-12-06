"""
Unit tests for Counterfactual Template Placeholder

Task 5.3: Counterfactual Placeholder
Tests for simple template-based counterfactual explanation generation.
"""

import pytest
from typing import List, Dict, Any

from ejc.core.explainability.counterfactual_generator import (
    CounterfactualTemplatePlaceholder
)


class TestCounterfactualTemplatePlaceholder:
    """Tests for CounterfactualTemplatePlaceholder"""

    @pytest.fixture
    def placeholder(self):
        """Create a placeholder instance"""
        return CounterfactualTemplatePlaceholder()

    def test_initialization(self, placeholder):
        """Test that placeholder initializes correctly"""
        assert placeholder is not None
        assert hasattr(placeholder, 'TEMPLATES')
        assert len(placeholder.TEMPLATES) > 0

    def test_templates_exist(self, placeholder):
        """Test that all expected templates exist"""
        expected_templates = [
            'critic_flip',
            'confidence_change',
            'factor_change',
            'threshold',
            'consensus',
            'generic'
        ]

        for template_name in expected_templates:
            assert template_name in placeholder.TEMPLATES
            assert isinstance(placeholder.TEMPLATES[template_name], str)
            assert len(placeholder.TEMPLATES[template_name]) > 0

    def test_generate_generic_counterfactual(self, placeholder):
        """Test generating generic counterfactual"""
        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY"
        )

        assert isinstance(result, str)
        assert "ALLOW" in result
        assert "DENY" in result
        assert len(result) > 0

    def test_generate_generic_no_target(self, placeholder):
        """Test generating generic counterfactual without target"""
        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW"
        )

        assert isinstance(result, str)
        assert "ALLOW" in result
        assert len(result) > 0

    def test_generate_critic_flip_counterfactual(self, placeholder):
        """Test generating critic flip counterfactual"""
        context = {
            'critic': 'BiasDetector',
            'from_verdict': 'DENY',
            'to_verdict': 'ALLOW'
        }

        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context=context
        )

        assert isinstance(result, str)
        assert "BiasDetector" in result
        assert "ALLOW" in result or "DENY" in result
        assert len(result) > 0

    def test_generate_confidence_change_counterfactual(self, placeholder):
        """Test generating confidence change counterfactual"""
        context = {
            'original_conf': 0.6,
            'target_conf': 0.9,
            'direction': 'increased'
        }

        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context=context
        )

        assert isinstance(result, str)
        assert "confidence" in result.lower()
        assert "%" in result  # Confidence formatted as percentage
        assert len(result) > 0

    def test_generate_factor_change_counterfactual(self, placeholder):
        """Test generating factor change counterfactual"""
        context = {
            'factor': 'transaction_amount',
            'from_value': 1000,
            'to_value': 500
        }

        result = placeholder.generate_simple_counterfactual(
            original_verdict="DENY",
            target_verdict="ALLOW",
            context=context
        )

        assert isinstance(result, str)
        assert "transaction_amount" in result
        assert "1000" in result or "500" in result
        assert len(result) > 0

    def test_generate_threshold_counterfactual(self, placeholder):
        """Test generating threshold counterfactual"""
        context = {
            'direction': 'lower'
        }

        result = placeholder.generate_simple_counterfactual(
            original_verdict="DENY",
            target_verdict="ALLOW",
            context=context
        )

        assert isinstance(result, str)
        assert "threshold" in result.lower()
        assert "lower" in result
        assert len(result) > 0

    def test_generate_consensus_counterfactual(self, placeholder):
        """Test generating consensus counterfactual"""
        context = {
            'consensus_level': 'unanimous'
        }

        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context=context
        )

        assert isinstance(result, str)
        assert "consensus" in result.lower()
        assert "unanimous" in result
        assert len(result) > 0

    def test_generate_multiple_counterfactuals(self, placeholder):
        """Test generating multiple counterfactuals"""
        possible_verdicts = ['ALLOW', 'DENY', 'ESCALATE']

        result = placeholder.generate_multiple_counterfactuals(
            original_verdict="ALLOW",
            possible_verdicts=possible_verdicts
        )

        assert isinstance(result, list)
        # Should generate for DENY and ESCALATE (not ALLOW since it's original)
        assert len(result) == 2
        assert all(isinstance(cf, str) for cf in result)
        assert all(len(cf) > 0 for cf in result)

    def test_generate_multiple_with_context(self, placeholder):
        """Test generating multiple counterfactuals with context"""
        possible_verdicts = ['ALLOW', 'DENY', 'ESCALATE', 'REVIEW']
        context = {
            'critic': 'PrivacyGuard',
            'from_verdict': 'DENY',
            'to_verdict': 'ALLOW'
        }

        result = placeholder.generate_multiple_counterfactuals(
            original_verdict="DENY",
            possible_verdicts=possible_verdicts,
            context=context
        )

        assert isinstance(result, list)
        assert len(result) == 3  # ALLOW, ESCALATE, REVIEW (not DENY)
        assert all("PrivacyGuard" in cf for cf in result)

    def test_generate_from_decision_simple(self, placeholder):
        """Test generating from a simple decision object"""
        decision = {
            'governance_outcome': {
                'verdict': 'ALLOW',
                'confidence': 0.85
            },
            'critic_reports': [
                {
                    'critic_name': 'BiasDetector',
                    'verdict': 'ALLOW',
                    'confidence': 0.9
                },
                {
                    'critic_name': 'PrivacyGuard',
                    'verdict': 'DENY',
                    'confidence': 0.7
                }
            ]
        }

        result = placeholder.generate_from_decision(decision, max_counterfactuals=3)

        assert isinstance(result, list)
        assert len(result) <= 3
        assert all(isinstance(cf, str) for cf in result)
        # Should reference the critics
        assert any("BiasDetector" in cf or "PrivacyGuard" in cf for cf in result)

    def test_generate_from_decision_no_critics(self, placeholder):
        """Test generating from decision with no critic reports"""
        decision = {
            'governance_outcome': {
                'verdict': 'DENY'
            },
            'critic_reports': []
        }

        result = placeholder.generate_from_decision(decision, max_counterfactuals=2)

        assert isinstance(result, list)
        assert len(result) <= 2
        assert all(isinstance(cf, str) for cf in result)
        # Should still generate generic counterfactuals
        assert all(len(cf) > 0 for cf in result)

    def test_generate_from_decision_aggregation_format(self, placeholder):
        """Test generating from decision with aggregation format"""
        decision = {
            'aggregation': {
                'verdict': 'ESCALATE',
                'confidence': 0.65
            },
            'critic_reports': [
                {
                    'critic_name': 'ComplianceChecker',
                    'verdict': 'ESCALATE',
                    'confidence': 0.8
                }
            ]
        }

        result = placeholder.generate_from_decision(decision)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "ComplianceChecker" in result[0]

    def test_extract_verdict_governance_outcome(self, placeholder):
        """Test extracting verdict from governance_outcome"""
        decision = {
            'governance_outcome': {
                'verdict': 'ALLOW'
            }
        }

        verdict = placeholder._extract_verdict(decision)
        assert verdict == 'ALLOW'

    def test_extract_verdict_aggregation(self, placeholder):
        """Test extracting verdict from aggregation"""
        decision = {
            'aggregation': {
                'verdict': 'DENY'
            }
        }

        verdict = placeholder._extract_verdict(decision)
        assert verdict == 'DENY'

    def test_extract_verdict_unknown(self, placeholder):
        """Test extracting verdict when not found"""
        decision = {}

        verdict = placeholder._extract_verdict(decision)
        assert verdict == 'UNKNOWN'

    def test_different_verdict_types(self, placeholder):
        """Test with different verdict types"""
        verdicts = ['ALLOW', 'DENY', 'ESCALATE', 'REVIEW', 'APPROVE', 'REJECT']

        for original in verdicts:
            for target in verdicts:
                if original != target:
                    result = placeholder.generate_simple_counterfactual(
                        original_verdict=original,
                        target_verdict=target
                    )
                    assert isinstance(result, str)
                    assert len(result) > 0

    def test_empty_context(self, placeholder):
        """Test with empty context dict"""
        result = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context={}
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_confidence_direction_inference(self, placeholder):
        """Test that confidence direction is inferred correctly"""
        # Increase
        context_increase = {
            'original_conf': 0.5,
            'target_conf': 0.9
        }

        result_increase = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context=context_increase
        )

        assert "increased" in result_increase.lower() or "50%" in result_increase

        # Decrease
        context_decrease = {
            'original_conf': 0.9,
            'target_conf': 0.5
        }

        result_decrease = placeholder.generate_simple_counterfactual(
            original_verdict="ALLOW",
            target_verdict="DENY",
            context=context_decrease
        )

        assert "decreased" in result_decrease.lower() or "90%" in result_decrease

    def test_max_counterfactuals_limit(self, placeholder):
        """Test that max_counterfactuals is respected"""
        decision = {
            'governance_outcome': {'verdict': 'ALLOW'},
            'critic_reports': [
                {'critic_name': f'Critic{i}', 'verdict': 'DENY'}
                for i in range(10)  # 10 critics
            ]
        }

        for max_count in [1, 2, 3, 5]:
            result = placeholder.generate_from_decision(
                decision,
                max_counterfactuals=max_count
            )
            assert len(result) <= max_count

    def test_template_formatting(self, placeholder):
        """Test that all templates can be formatted without errors"""
        # Test critic_flip
        assert "{original}" in placeholder.TEMPLATES['critic_flip']
        assert "{target}" in placeholder.TEMPLATES['critic_flip']
        assert "{critic}" in placeholder.TEMPLATES['critic_flip']

        # Test confidence_change
        assert "{original_conf" in placeholder.TEMPLATES['confidence_change']
        assert "{target_conf" in placeholder.TEMPLATES['confidence_change']

        # Test factor_change
        assert "{factor}" in placeholder.TEMPLATES['factor_change']
        assert "{from_value}" in placeholder.TEMPLATES['factor_change']

        # Test that all templates have at least one placeholder
        for template_name, template in placeholder.TEMPLATES.items():
            assert "{" in template and "}" in template, f"Template {template_name} should have placeholders"

        # Test specific required placeholders for each template
        assert "{critic}" in placeholder.TEMPLATES['critic_flip']
        assert "{factor}" in placeholder.TEMPLATES['factor_change']
        assert "{direction}" in placeholder.TEMPLATES['threshold']
        assert "{consensus_level}" in placeholder.TEMPLATES['consensus']


class TestIntegration:
    """Integration tests for counterfactual template generation"""

    def test_realistic_scenario(self):
        """Test a realistic usage scenario"""
        placeholder = CounterfactualTemplatePlaceholder()

        # Simulate a real decision
        decision = {
            'governance_outcome': {
                'verdict': 'DENY',
                'confidence': 0.82
            },
            'critic_reports': [
                {
                    'critic_name': 'BiasDetector',
                    'verdict': 'ALLOW',
                    'confidence': 0.75,
                    'justification': 'No bias detected'
                },
                {
                    'critic_name': 'PrivacyGuard',
                    'verdict': 'DENY',
                    'confidence': 0.95,
                    'justification': 'Privacy violation detected'
                },
                {
                    'critic_name': 'ComplianceChecker',
                    'verdict': 'DENY',
                    'confidence': 0.88,
                    'justification': 'Non-compliant with regulations'
                }
            ]
        }

        counterfactuals = placeholder.generate_from_decision(decision)

        # Should generate counterfactuals
        assert len(counterfactuals) > 0

        # Should reference specific critics
        all_text = ' '.join(counterfactuals)
        critic_names = ['BiasDetector', 'PrivacyGuard', 'ComplianceChecker']
        assert any(name in all_text for name in critic_names)

    def test_mixed_verdicts(self):
        """Test with mixed verdicts from critics"""
        placeholder = CounterfactualTemplatePlaceholder()

        decision = {
            'governance_outcome': {'verdict': 'ESCALATE'},
            'critic_reports': [
                {'critic_name': 'Critic1', 'verdict': 'ALLOW'},
                {'critic_name': 'Critic2', 'verdict': 'DENY'},
                {'critic_name': 'Critic3', 'verdict': 'ESCALATE'},
                {'critic_name': 'Critic4', 'verdict': 'REVIEW'}
            ]
        }

        counterfactuals = placeholder.generate_from_decision(
            decision,
            max_counterfactuals=4
        )

        # Should generate up to 4 counterfactuals
        assert len(counterfactuals) <= 4
        assert all(isinstance(cf, str) for cf in counterfactuals)
        assert all(len(cf) > 0 for cf in counterfactuals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
