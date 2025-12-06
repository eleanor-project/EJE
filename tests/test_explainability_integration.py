"""
Integration Tests for Explainability Module

Task 5.4: Explainability Tests
Comprehensive integration tests validating the entire explainability pipeline:
- Individual critic explanations
- Aggregated explanation correctness
- Counterfactual formatting
- End-to-end workflow
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from ejc.core.explainability.critic_explanation_formatter import (
    CriticExplanationFormatter,
    CriticExplanation,
    ExplanationStyle,
    ConfidenceLevel,
    format_critic_output,
    format_multiple_critics
)
from ejc.core.explainability.aggregated_explanation_builder import (
    AggregatedExplanationBuilder,
    AggregationMode,
    ConsensusLevel,
    aggregate_explanations
)
from ejc.core.explainability.counterfactual_generator import (
    CounterfactualTemplatePlaceholder
)


class TestIndividualCriticExplanations:
    """Integration tests for individual critic explanation formatting"""

    @pytest.fixture
    def sample_critic_outputs(self) -> List[Dict[str, Any]]:
        """Sample critic outputs for testing"""
        return [
            {
                'critic_name': 'BiasDetector',
                'verdict': 'ALLOW',
                'confidence': 0.92,
                'justification': 'No significant bias detected in transaction patterns.',
                'reasoning': 'Fair distribution across demographic groups.',
                'metadata': {
                    'processing_time_ms': 45.2,
                    'priority': 'high'
                },
                'violations': [],
                'bias_score': 0.08
            },
            {
                'critic_name': 'PrivacyGuard',
                'verdict': 'DENY',
                'confidence': 0.88,
                'justification': 'Privacy violation detected.',
                'reasoning': 'Insufficient data anonymization for sensitive fields.',
                'metadata': {
                    'processing_time_ms': 38.7,
                    'priority': 'critical'
                },
                'warnings': ['PII exposure risk'],
                'privacy_score': 0.35
            },
            {
                'critic_name': 'ComplianceChecker',
                'verdict': 'ALLOW',
                'confidence': 0.95,
                'justification': 'All compliance requirements met.',
                'reasoning': 'GDPR and local regulations satisfied.',
                'metadata': {
                    'processing_time_ms': 52.1,
                    'priority': 'high'
                },
                'compliance_score': 0.96
            }
        ]

    def test_format_single_critic_verbose(self, sample_critic_outputs):
        """Test formatting single critic in verbose mode"""
        formatter = CriticExplanationFormatter(default_style=ExplanationStyle.VERBOSE)

        explanation = formatter.format_critic_output(sample_critic_outputs[0])

        assert explanation.critic_name == 'BiasDetector'
        assert explanation.verdict == 'ALLOW'
        assert explanation.confidence == 0.92
        assert explanation.confidence_level == ConfidenceLevel.VERY_HIGH
        assert len(explanation.primary_reason) > 0

        # Format to text
        text = formatter.format_to_text(explanation)
        assert 'BiasDetector' in text
        assert 'ALLOW' in text
        assert '0.92' in text

    def test_format_multiple_critics_styles(self, sample_critic_outputs):
        """Test formatting multiple critics in different styles"""
        formatter = CriticExplanationFormatter()

        # Test all styles
        for style in ExplanationStyle:
            explanations = [
                formatter.format_critic_output(output)
                for output in sample_critic_outputs
            ]

            for explanation in explanations:
                text = formatter.format_to_text(explanation, style)
                assert isinstance(text, str)
                assert len(text) > 0

                if style == ExplanationStyle.COMPACT:
                    # Compact should be shorter
                    assert len(text) < 300
                elif style == ExplanationStyle.VERBOSE:
                    # Verbose should include metadata
                    assert 'Verdict:' in text or explanation.critic_name in text

    def test_critic_warnings_and_limitations(self, sample_critic_outputs):
        """Test that warnings and limitations are extracted"""
        formatter = CriticExplanationFormatter()

        # PrivacyGuard has a warning
        explanation = formatter.format_critic_output(sample_critic_outputs[1])

        assert len(explanation.warnings) > 0
        assert 'PII exposure risk' in explanation.warnings[0]

    def test_convenience_format_functions(self, sample_critic_outputs):
        """Test convenience functions work correctly"""
        # Test format_critic_output
        result = format_critic_output(
            sample_critic_outputs[0],
            ExplanationStyle.COMPACT
        )

        assert isinstance(result, str)
        assert 'BiasDetector' in result

        # Test format_multiple_critics
        result = format_multiple_critics(
            sample_critic_outputs,
            ExplanationStyle.COMPACT
        )

        assert isinstance(result, str)
        assert 'BiasDetector' in result
        assert 'PrivacyGuard' in result
        assert 'ComplianceChecker' in result


class TestAggregatedExplanations:
    """Integration tests for aggregated explanation correctness"""

    @pytest.fixture
    def critic_explanations_unanimous(self) -> List[CriticExplanation]:
        """Create unanimous critic explanations"""
        return [
            CriticExplanation(
                critic_name="BiasDetector",
                verdict="ALLOW",
                confidence=0.92,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="No bias detected.",
                key_factors={'bias_score': 0.08}
            ),
            CriticExplanation(
                critic_name="PrivacyGuard",
                verdict="ALLOW",
                confidence=0.88,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Privacy requirements met.",
                key_factors={'privacy_score': 0.90}
            ),
            CriticExplanation(
                critic_name="ComplianceChecker",
                verdict="ALLOW",
                confidence=0.95,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Compliant with regulations.",
                key_factors={'compliance_score': 0.96}
            )
        ]

    @pytest.fixture
    def critic_explanations_split(self) -> List[CriticExplanation]:
        """Create split verdict explanations"""
        return [
            CriticExplanation(
                critic_name="BiasDetector",
                verdict="ALLOW",
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Acceptable bias levels.",
                warnings=["Minor bias in age group"]
            ),
            CriticExplanation(
                critic_name="PrivacyGuard",
                verdict="DENY",
                confidence=0.90,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Privacy violation detected.",
                warnings=["PII exposure risk"]
            ),
            CriticExplanation(
                critic_name="ComplianceChecker",
                verdict="ALLOW",
                confidence=0.88,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Compliant overall."
            ),
            CriticExplanation(
                critic_name="SecurityScanner",
                verdict="DENY",
                confidence=0.87,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Security risk identified.",
                warnings=["Potential vulnerability"]
            )
        ]

    def test_unanimous_aggregation(self, critic_explanations_unanimous):
        """Test aggregation with unanimous verdict"""
        builder = AggregatedExplanationBuilder()

        result = builder.build(critic_explanations_unanimous)

        assert result.dominant_verdict == "ALLOW"
        assert result.consensus_level == ConsensusLevel.UNANIMOUS
        assert result.total_critics == 3
        assert len(result.verdict_breakdown) == 1
        assert result.overall_confidence > 0.85

    def test_split_verdict_aggregation(self, critic_explanations_split):
        """Test aggregation with split verdicts"""
        builder = AggregatedExplanationBuilder()

        result = builder.build(critic_explanations_split)

        assert result.total_critics == 4
        assert len(result.verdict_breakdown) == 2  # ALLOW and DENY
        assert result.consensus_level in [
            ConsensusLevel.SPLIT,
            ConsensusLevel.MAJORITY
        ]

        # Should have both verdicts represented
        assert 'ALLOW' in result.verdict_breakdown
        assert 'DENY' in result.verdict_breakdown

    def test_aggregated_warnings_collection(self, critic_explanations_split):
        """Test that warnings are properly aggregated"""
        builder = AggregatedExplanationBuilder()

        result = builder.build(critic_explanations_split)

        # Should collect all warnings
        assert len(result.all_warnings) > 0

        # Should include warnings from multiple critics
        all_warnings_text = ' '.join(result.all_warnings)
        assert 'bias' in all_warnings_text.lower() or 'pii' in all_warnings_text.lower()

    def test_aggregation_output_modes(self, critic_explanations_unanimous):
        """Test all aggregation output modes"""
        builder = AggregatedExplanationBuilder()
        aggregated = builder.build(critic_explanations_unanimous)

        # Test all modes
        for mode in AggregationMode:
            text = builder.format_to_text(aggregated, mode)

            assert isinstance(text, str)
            assert len(text) > 0
            assert 'ALLOW' in text

            if mode == AggregationMode.SHORT_FORM:
                assert len(text) < 500
            elif mode == AggregationMode.LONG_FORM:
                assert len(text) > 200

    def test_convenience_aggregate_function(self, critic_explanations_unanimous):
        """Test convenience aggregate_explanations function"""
        result = aggregate_explanations(
            critic_explanations_unanimous,
            AggregationMode.SHORT_FORM
        )

        assert isinstance(result, str)
        assert 'ALLOW' in result


class TestCounterfactualFormatting:
    """Integration tests for counterfactual formatting"""

    @pytest.fixture
    def sample_decision(self) -> Dict[str, Any]:
        """Sample decision for counterfactual generation"""
        return {
            'governance_outcome': {
                'verdict': 'DENY',
                'confidence': 0.85
            },
            'critic_reports': [
                {
                    'critic_name': 'BiasDetector',
                    'verdict': 'ALLOW',
                    'confidence': 0.75
                },
                {
                    'critic_name': 'PrivacyGuard',
                    'verdict': 'DENY',
                    'confidence': 0.92
                },
                {
                    'critic_name': 'ComplianceChecker',
                    'verdict': 'DENY',
                    'confidence': 0.88
                }
            ]
        }

    def test_generate_simple_counterfactual(self):
        """Test simple counterfactual generation"""
        generator = CounterfactualTemplatePlaceholder()

        result = generator.generate_simple_counterfactual(
            original_verdict="DENY",
            target_verdict="ALLOW"
        )

        assert isinstance(result, str)
        assert "DENY" in result
        assert "ALLOW" in result
        assert "change" in result.lower()

    def test_counterfactual_with_context(self):
        """Test counterfactual with critic context"""
        generator = CounterfactualTemplatePlaceholder()

        context = {
            'critic': 'PrivacyGuard',
            'from_verdict': 'DENY',
            'to_verdict': 'ALLOW'
        }

        result = generator.generate_simple_counterfactual(
            original_verdict="DENY",
            target_verdict="ALLOW",
            context=context
        )

        assert 'PrivacyGuard' in result
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_from_decision(self, sample_decision):
        """Test generating counterfactuals from decision object"""
        generator = CounterfactualTemplatePlaceholder()

        counterfactuals = generator.generate_from_decision(sample_decision)

        assert isinstance(counterfactuals, list)
        assert len(counterfactuals) > 0
        assert all(isinstance(cf, str) for cf in counterfactuals)

        # Should reference critics
        all_text = ' '.join(counterfactuals)
        assert 'BiasDetector' in all_text or 'PrivacyGuard' in all_text

    def test_multiple_counterfactual_scenarios(self):
        """Test multiple counterfactual scenarios"""
        generator = CounterfactualTemplatePlaceholder()

        scenarios = [
            ('ALLOW', 'DENY'),
            ('DENY', 'ALLOW'),
            ('ESCALATE', 'ALLOW'),
            ('ALLOW', 'REVIEW')
        ]

        for original, target in scenarios:
            result = generator.generate_simple_counterfactual(original, target)
            assert original in result
            assert target in result


class TestEndToEndWorkflow:
    """Integration tests for complete explainability workflow"""

    @pytest.fixture
    def complete_decision(self) -> Dict[str, Any]:
        """Complete decision object with all components"""
        return {
            'governance_outcome': {
                'verdict': 'DENY',
                'confidence': 0.82,
                'justification': 'Majority of critics recommend denial'
            },
            'critic_reports': [
                {
                    'critic_name': 'BiasDetector',
                    'verdict': 'ALLOW',
                    'confidence': 0.78,
                    'justification': 'Bias levels acceptable',
                    'reasoning': 'Fair treatment across groups',
                    'metadata': {'processing_time_ms': 42.5},
                    'bias_score': 0.15
                },
                {
                    'critic_name': 'PrivacyGuard',
                    'verdict': 'DENY',
                    'confidence': 0.91,
                    'justification': 'Privacy concerns identified',
                    'reasoning': 'Insufficient anonymization',
                    'metadata': {'processing_time_ms': 38.2},
                    'warnings': ['PII exposure'],
                    'privacy_score': 0.42
                },
                {
                    'critic_name': 'ComplianceChecker',
                    'verdict': 'DENY',
                    'confidence': 0.85,
                    'justification': 'Compliance issues detected',
                    'reasoning': 'GDPR requirements not fully met',
                    'metadata': {'processing_time_ms': 55.8},
                    'compliance_score': 0.68
                }
            ],
            'input_data': {
                'transaction_id': 'TXN-12345',
                'amount': 5000,
                'user_age': 34
            }
        }

    def test_complete_explanation_pipeline(self, complete_decision):
        """Test the complete explanation generation pipeline"""
        # Step 1: Format individual critic explanations
        formatter = CriticExplanationFormatter()
        critic_explanations = []

        for report in complete_decision['critic_reports']:
            explanation = formatter.format_critic_output(report)
            critic_explanations.append(explanation)

        assert len(critic_explanations) == 3

        # Step 2: Aggregate explanations
        builder = AggregatedExplanationBuilder()
        aggregated = builder.build(critic_explanations)

        assert aggregated.dominant_verdict == 'DENY'
        assert aggregated.total_critics == 3

        # Step 3: Generate counterfactuals
        cf_generator = CounterfactualTemplatePlaceholder()
        counterfactuals = cf_generator.generate_from_decision(complete_decision)

        assert len(counterfactuals) > 0

        # Step 4: Format everything for output
        long_form = builder.format_to_text(aggregated, AggregationMode.LONG_FORM)
        short_form = builder.format_to_text(aggregated, AggregationMode.SHORT_FORM)

        assert len(long_form) > len(short_form)
        assert 'DENY' in long_form
        assert 'DENY' in short_form

    def test_explanation_consistency(self, complete_decision):
        """Test that explanations are consistent across components"""
        # Format critics
        formatter = CriticExplanationFormatter()
        critic_explanations = [
            formatter.format_critic_output(report)
            for report in complete_decision['critic_reports']
        ]

        # Aggregate
        builder = AggregatedExplanationBuilder()
        aggregated = builder.build(critic_explanations)

        # Verify consistency
        verdicts_from_critics = [exp.verdict for exp in critic_explanations]
        verdicts_in_aggregation = list(aggregated.verdict_breakdown.keys())

        # All verdicts in aggregation should come from critics
        for verdict in verdicts_in_aggregation:
            assert verdict in verdicts_from_critics

    def test_warnings_propagation(self, complete_decision):
        """Test that warnings propagate through the pipeline"""
        # Format critics
        formatter = CriticExplanationFormatter()
        critic_explanations = [
            formatter.format_critic_output(report)
            for report in complete_decision['critic_reports']
        ]

        # Check individual warnings
        individual_warnings = []
        for exp in critic_explanations:
            individual_warnings.extend(exp.warnings)

        # Aggregate
        builder = AggregatedExplanationBuilder()
        aggregated = builder.build(critic_explanations)

        # Aggregated warnings should include individual warnings
        assert len(aggregated.all_warnings) > 0
        if individual_warnings:
            # At least some warnings should propagate
            assert any(
                any(iw in aw for aw in aggregated.all_warnings)
                for iw in individual_warnings
            )

    def test_different_consensus_scenarios(self):
        """Test explanation pipeline with different consensus levels"""
        scenarios = [
            # Unanimous
            ([('BiasDetector', 'ALLOW'), ('PrivacyGuard', 'ALLOW'), ('ComplianceChecker', 'ALLOW')], ConsensusLevel.UNANIMOUS),
            # Split
            ([('BiasDetector', 'ALLOW'), ('PrivacyGuard', 'DENY')], ConsensusLevel.SPLIT),
        ]

        formatter = CriticExplanationFormatter()
        builder = AggregatedExplanationBuilder()

        for critic_verdicts, expected_consensus in scenarios:
            # Create mock reports
            reports = [
                {
                    'critic_name': name,
                    'verdict': verdict,
                    'confidence': 0.85,
                    'justification': f'{name} says {verdict}'
                }
                for name, verdict in critic_verdicts
            ]

            # Format and aggregate
            explanations = [formatter.format_critic_output(r) for r in reports]
            aggregated = builder.build(explanations)

            assert aggregated.consensus_level == expected_consensus

    def test_serialization_roundtrip(self, complete_decision):
        """Test that explanations can be serialized and remain valid"""
        formatter = CriticExplanationFormatter()
        builder = AggregatedExplanationBuilder()

        # Generate explanations
        critic_explanations = [
            formatter.format_critic_output(report)
            for report in complete_decision['critic_reports']
        ]

        aggregated = builder.build(critic_explanations)

        # Serialize to dict
        aggregated_dict = aggregated.to_dict()

        # Verify structure
        assert 'dominant_verdict' in aggregated_dict
        assert 'overall_confidence' in aggregated_dict
        assert 'consensus_level' in aggregated_dict
        assert 'verdict_breakdown' in aggregated_dict

        # Verify values match
        assert aggregated_dict['dominant_verdict'] == aggregated.dominant_verdict
        assert aggregated_dict['overall_confidence'] == aggregated.overall_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
