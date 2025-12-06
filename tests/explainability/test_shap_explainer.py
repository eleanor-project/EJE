"""
Tests for SHAPExplainer (Issue #168)

Tests SHAP integration for feature attribution in EJE decisions.
"""

import pytest
from src.ejc.core.explainability.shap_explainer import (
    SHAPExplainer,
    SHAPExplanation
)


@pytest.fixture
def sample_decision():
    """Sample EJE decision for testing."""
    return {
        'decision_id': 'test_shap_001',
        'input_data': {
            'request_id': '12345',
            'user_id': 'user_001',
            'amount': 5000,
            'credit_score': 720,
            'income': 75000,
            'debt_ratio': 0.35,
            'employment_years': 5
        },
        'critic_reports': [
            {
                'critic_name': 'CreditScoreCritic',
                'verdict': 'APPROVE',
                'confidence': 0.85,
                'justification': 'Credit score of 720 is excellent. Strong repayment history.'
            },
            {
                'critic_name': 'IncomeVerificationCritic',
                'verdict': 'APPROVE',
                'confidence': 0.90,
                'justification': 'Income of 75000 is sufficient. Stable employment years of 5.'
            },
            {
                'critic_name': 'DebtRatioCritic',
                'verdict': 'DENY',
                'confidence': 0.70,
                'justification': 'Debt ratio of 0.35 is slightly elevated. May impact repayment capacity.'
            }
        ],
        'aggregation': {
            'verdict': 'APPROVE',
            'confidence': 0.82
        },
        'governance_outcome': {
            'verdict': 'APPROVE',
            'confidence': 0.82
        }
    }


@pytest.fixture
def explainer():
    """Create a SHAP explainer instance."""
    return SHAPExplainer(
        enable_caching=True,
        cache_size=128,
        max_display_features=10
    )


class TestSHAPExplainer:
    """Test suite for SHAP Explainer."""

    def test_initialization(self, explainer):
        """Test explainer initialization."""
        assert explainer.enable_caching is True
        assert explainer.cache_size == 128
        assert explainer.max_display_features == 10
        assert isinstance(explainer._cache, dict)

    def test_explain_decision(self, explainer, sample_decision):
        """Test SHAP explanation generation for a decision."""
        explanation = explainer.explain_decision(sample_decision)

        # Should return explanation structure
        assert 'decision_id' in explanation
        assert 'explanation_type' in explanation
        assert 'critic_explanations' in explanation
        assert 'aggregate_explanation' in explanation
        assert 'features' in explanation
        assert 'computation_time' in explanation
        assert explanation['available'] is True

        # Should have explanations for all critics
        assert len(explanation['critic_explanations']) == 3

        # Should have aggregate explanation
        assert explanation['aggregate_explanation'] is not None

    def test_feature_extraction(self, explainer, sample_decision):
        """Test feature extraction from decision."""
        features = explainer._extract_features(sample_decision)

        # Should extract all features except metadata
        assert 'amount' in features
        assert 'credit_score' in features
        assert 'income' in features
        assert 'debt_ratio' in features
        assert 'employment_years' in features

        # Should not include metadata fields
        assert 'request_id' not in features
        assert 'user_id' not in features

    def test_critic_explanation(self, explainer, sample_decision):
        """Test SHAP explanation for individual critics."""
        explanation = explainer.explain_decision(sample_decision)

        critic_exp = explanation['critic_explanations'][0]

        # Should have all required fields
        assert 'feature_names' in critic_exp
        assert 'feature_values' in critic_exp
        assert 'shap_values' in critic_exp
        assert 'base_value' in critic_exp
        assert 'output_value' in critic_exp
        assert 'critic_name' in critic_exp
        assert 'computation_time' in critic_exp

        # SHAP values should match number of features
        assert len(critic_exp['shap_values']) == len(critic_exp['feature_names'])

    def test_aggregate_explanation(self, explainer, sample_decision):
        """Test aggregate SHAP explanation."""
        explanation = explainer.explain_decision(sample_decision)

        agg_exp = explanation['aggregate_explanation']

        # Should have aggregated SHAP values
        assert 'shap_values' in agg_exp
        assert 'feature_names' in agg_exp
        assert 'output_value' in agg_exp

        # Should aggregate across all critics
        assert len(agg_exp['shap_values']) > 0

    def test_feature_importance_calculation(self, explainer, sample_decision):
        """Test feature importance calculation logic."""
        critic_report = sample_decision['critic_reports'][0]
        features = explainer._extract_features(sample_decision)

        importance_scores = explainer._calculate_critic_feature_importance(
            critic_report,
            features
        )

        # Should return scores for all features
        assert len(importance_scores) == len(features)

        # Scores should be reasonable (not too extreme)
        for score in importance_scores:
            assert -1.0 <= score <= 1.0

    def test_caching_functionality(self, explainer, sample_decision):
        """Test that caching works correctly."""
        # First call
        result1 = explainer.explain_decision(sample_decision)
        cached_count1 = result1['cached_count']

        # Second call with same decision
        result2 = explainer.explain_decision(sample_decision)
        cached_count2 = result2['cached_count']

        # Second call should have more cached results
        assert cached_count2 >= cached_count1

    def test_cache_clearing(self, explainer, sample_decision):
        """Test cache clearing functionality."""
        # Generate explanation to populate cache
        explainer.explain_decision(sample_decision)
        assert len(explainer._cache) > 0

        # Clear cache
        explainer.clear_cache()
        assert len(explainer._cache) == 0

    def test_global_explanation(self, explainer, sample_decision):
        """Test global SHAP explanation across multiple decisions."""
        # Create multiple decisions
        decisions = [sample_decision.copy() for _ in range(3)]

        # Modify them slightly
        for i, decision in enumerate(decisions):
            decision['decision_id'] = f'test_{i}'
            decision['input_data']['amount'] = 5000 + (i * 1000)

        # Generate global explanation
        global_exp = explainer.explain_global(decisions, top_k_features=5)

        # Should return global structure
        assert 'explanation_type' in global_exp
        assert global_exp['explanation_type'] == 'global'
        assert 'num_decisions' in global_exp
        assert global_exp['num_decisions'] == 3
        assert 'top_features' in global_exp
        assert len(global_exp['top_features']) <= 5

        # Features should be ranked
        for i, feature in enumerate(global_exp['top_features']):
            assert 'feature' in feature
            assert 'importance' in feature
            assert 'rank' in feature
            assert feature['rank'] == i + 1

    def test_visualization_waterfall(self, explainer, sample_decision):
        """Test waterfall plot visualization data generation."""
        explanation = explainer.explain_decision(sample_decision)

        viz_data = explainer.visualize(explanation, plot_type='waterfall')

        assert viz_data['plot_type'] == 'waterfall'
        assert 'base_value' in viz_data
        assert 'output_value' in viz_data
        assert 'features' in viz_data

        # Features should have required fields
        for feature in viz_data['features']:
            assert 'name' in feature
            assert 'value' in feature
            assert 'shap_value' in feature
            assert 'cumulative' in feature

    def test_visualization_bar(self, explainer, sample_decision):
        """Test bar plot visualization data generation."""
        explanation = explainer.explain_decision(sample_decision)

        viz_data = explainer.visualize(explanation, plot_type='bar')

        assert viz_data['plot_type'] == 'bar'
        assert 'features' in viz_data

        for feature in viz_data['features']:
            assert 'name' in feature
            assert 'value' in feature
            assert 'shap_value' in feature
            assert 'abs_shap_value' in feature

    def test_visualization_force(self, explainer, sample_decision):
        """Test force plot visualization data generation."""
        explanation = explainer.explain_decision(sample_decision)

        viz_data = explainer.visualize(explanation, plot_type='force')

        assert viz_data['plot_type'] == 'force'
        assert 'base_value' in viz_data
        assert 'output_value' in viz_data
        assert 'positive_features' in viz_data
        assert 'negative_features' in viz_data

    def test_get_top_features(self, explainer, sample_decision):
        """Test getting top N features."""
        explanation = explainer.explain_decision(sample_decision)

        top_features = explainer.get_top_features(explanation, n=3)

        # Should return top 3 features
        assert len(top_features) <= 3

        # Should be sorted by importance
        if len(top_features) > 1:
            importances = [f['abs_importance'] for f in top_features]
            assert importances == sorted(importances, reverse=True)

        # Each feature should have required fields
        for feature in top_features:
            assert 'feature' in feature
            assert 'value' in feature
            assert 'shap_value' in feature
            assert 'abs_importance' in feature
            assert 'direction' in feature
            assert feature['direction'] in ['positive', 'negative']

    def test_performance_stats(self, explainer, sample_decision):
        """Test performance statistics retrieval."""
        # Generate some explanations
        explainer.explain_decision(sample_decision)

        stats = explainer.get_performance_stats()

        assert 'cache_enabled' in stats
        assert 'cache_size' in stats
        assert 'cache_capacity' in stats
        assert 'cache_hit_rate' in stats

        assert stats['cache_enabled'] is True
        assert stats['cache_capacity'] == 128

    def test_performance_within_threshold(self, explainer, sample_decision):
        """Test that SHAP computation is within performance threshold."""
        explanation = explainer.explain_decision(sample_decision)

        # Should complete quickly (< 1 second for this simple case)
        assert explanation['computation_time'] < 1.0

    def test_handles_empty_decision(self, explainer):
        """Test handling of empty/invalid decisions."""
        empty_decision = {
            'decision_id': 'empty_001',
            'input_data': {},
            'critic_reports': [],
            'aggregation': {},
            'governance_outcome': {}
        }

        explanation = explainer.explain_decision(empty_decision)

        # Should handle gracefully
        assert 'critic_explanations' in explanation
        assert len(explanation['critic_explanations']) == 0
        assert explanation['available'] is True

    def test_handles_missing_features(self, explainer):
        """Test handling of decisions with no features."""
        no_features_decision = {
            'decision_id': 'no_features_001',
            'input_data': {
                'id': '123',  # Metadata only
                'timestamp': '2024-01-01'
            },
            'critic_reports': [
                {
                    'critic_name': 'TestCritic',
                    'verdict': 'APPROVE',
                    'confidence': 0.8,
                    'justification': 'Test'
                }
            ],
            'aggregation': {'verdict': 'APPROVE', 'confidence': 0.8},
            'governance_outcome': {'verdict': 'APPROVE', 'confidence': 0.8}
        }

        explanation = explainer.explain_decision(no_features_decision)

        # Should handle gracefully with no features
        assert explanation['available'] is True
        assert len(explanation['features']) == 0

    def test_consistency_across_calls(self, explainer, sample_decision):
        """Test that multiple calls produce consistent results."""
        result1 = explainer.explain_decision(sample_decision)
        result2 = explainer.explain_decision(sample_decision)

        # Should have same number of critic explanations
        assert len(result1['critic_explanations']) == len(result2['critic_explanations'])

        # Should extract same features
        assert result1['features'] == result2['features']

    def test_different_verdicts_different_signs(self, explainer):
        """Test that APPROVE and DENY produce different signs."""
        approve_decision = {
            'decision_id': 'approve_001',
            'input_data': {'feature1': 100, 'feature2': 200},
            'critic_reports': [
                {
                    'critic_name': 'TestCritic',
                    'verdict': 'APPROVE',
                    'confidence': 0.9,
                    'justification': 'feature1 is excellent'
                }
            ],
            'aggregation': {'verdict': 'APPROVE', 'confidence': 0.9},
            'governance_outcome': {'verdict': 'APPROVE', 'confidence': 0.9}
        }

        deny_decision = {
            'decision_id': 'deny_001',
            'input_data': {'feature1': 100, 'feature2': 200},
            'critic_reports': [
                {
                    'critic_name': 'TestCritic',
                    'verdict': 'DENY',
                    'confidence': 0.9,
                    'justification': 'feature1 is concerning'
                }
            ],
            'aggregation': {'verdict': 'DENY', 'confidence': 0.9},
            'governance_outcome': {'verdict': 'DENY', 'confidence': 0.9}
        }

        approve_exp = explainer.explain_decision(approve_decision)
        deny_exp = explainer.explain_decision(deny_decision)

        # APPROVE should have positive output, DENY negative
        approve_output = approve_exp['aggregate_explanation']['output_value']
        deny_output = deny_exp['aggregate_explanation']['output_value']

        assert approve_output > 0
        assert deny_output < 0


class TestIntegrationWithXAIPipeline:
    """Test SHAP integration with XAIPipeline."""

    def test_xai_pipeline_shap_generation(self, sample_decision):
        """Test that XAIPipeline can generate SHAP explanations."""
        from src.ejc.core.explainability import XAIPipeline, XAIMethod, ExplanationLevel

        pipeline = XAIPipeline()

        # Generate SHAP explanation
        result = pipeline.generate_explanation(
            model=None,
            instance=sample_decision,
            method=XAIMethod.SHAP,
            level=ExplanationLevel.NARRATIVE
        )

        assert result['method'] == 'shap'
        assert result['confidence'] > 0.5
        assert 'critic_explanations' in result['explanation']
        assert 'aggregate_explanation' in result['explanation']

    def test_xai_pipeline_shap_technical_level(self, sample_decision):
        """Test SHAP with technical explanation level."""
        from src.ejc.core.explainability import XAIPipeline, XAIMethod, ExplanationLevel

        pipeline = XAIPipeline()

        result = pipeline.generate_explanation(
            model=None,
            instance=sample_decision,
            method=XAIMethod.SHAP,
            level=ExplanationLevel.TECHNICAL
        )

        assert result['method'] == 'shap'
        assert 'features' in result['explanation']


class TestCachingPerformance:
    """Test caching performance improvements."""

    def test_cache_improves_performance(self, sample_decision):
        """Test that caching improves performance on repeated calls."""
        explainer = SHAPExplainer(enable_caching=True)

        # First call (uncached)
        result1 = explainer.explain_decision(sample_decision)
        time1 = result1['computation_time']

        # Second call (should use cache for some critics)
        result2 = explainer.explain_decision(sample_decision)
        cached_count = result2['cached_count']

        # Should have cached some critics
        assert cached_count > 0

    def test_cache_disabled(self, sample_decision):
        """Test that caching can be disabled."""
        explainer = SHAPExplainer(enable_caching=False)

        result1 = explainer.explain_decision(sample_decision)
        result2 = explainer.explain_decision(sample_decision)

        # Should not cache anything
        assert result2['cached_count'] == 0
        assert len(explainer._cache) == 0

    def test_cache_size_limit(self):
        """Test that cache respects size limit."""
        explainer = SHAPExplainer(enable_caching=True, cache_size=2)

        # Create multiple different decisions
        for i in range(5):
            decision = {
                'decision_id': f'test_{i}',
                'input_data': {'feature': i},
                'critic_reports': [
                    {
                        'critic_name': f'Critic{i}',
                        'verdict': 'APPROVE',
                        'confidence': 0.8,
                        'justification': f'Test {i}'
                    }
                ],
                'aggregation': {'verdict': 'APPROVE', 'confidence': 0.8},
                'governance_outcome': {'verdict': 'APPROVE', 'confidence': 0.8}
            }
            explainer.explain_decision(decision)

        # Cache should not exceed size limit
        assert len(explainer._cache) <= 2


class TestVisualizationFormats:
    """Test different visualization formats."""

    def test_all_visualization_types(self, explainer, sample_decision):
        """Test that all visualization types work."""
        explanation = explainer.explain_decision(sample_decision)

        plot_types = ['waterfall', 'bar', 'force']

        for plot_type in plot_types:
            viz_data = explainer.visualize(explanation, plot_type=plot_type)
            assert viz_data['plot_type'] == plot_type
            assert 'error' not in viz_data

    def test_invalid_plot_type(self, explainer, sample_decision):
        """Test handling of invalid plot type."""
        explanation = explainer.explain_decision(sample_decision)

        viz_data = explainer.visualize(explanation, plot_type='invalid')

        assert 'error' in viz_data


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
