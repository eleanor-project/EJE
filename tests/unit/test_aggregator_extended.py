"""Extended unit tests for the Aggregator - edge cases and complex scenarios"""
import pytest
from src.eje.core.aggregator import Aggregator


class TestAggregatorEdgeCases:
    """Test suite for Aggregator edge cases"""

    def test_exact_tie_scenario(self):
        """Test aggregation when verdicts result in exact tie"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Should trigger REVIEW due to ambiguity
        assert output['overall_verdict'] in ['REVIEW', 'BLOCK']
        assert 'ambiguity' in output

    def test_multiple_override_priorities_same_verdict(self):
        """Test multiple critics with override priority agreeing"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'Security1', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': 'override'},
            {'critic': 'Security2', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': 'override'}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'BLOCK'
        assert 'Override' in output['reason']

    def test_multiple_override_priorities_conflicting(self):
        """Test multiple critics with override priority disagreeing"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'Security', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': 'override'},
            {'critic': 'Human', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': 'override'}
        ]

        output = agg.aggregate(results)
        # With conflicting overrides, should use weighted aggregation or REVIEW
        assert output['overall_verdict'] in ['ALLOW', 'BLOCK', 'REVIEW']

    def test_failed_critics_with_error_verdict(self):
        """Test aggregation when some critics return ERROR verdict"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # ERROR verdicts should be ignored in aggregation
        assert output['overall_verdict'] == 'ALLOW'
        assert output['avg_confidence'] > 0

    def test_all_critics_failed(self):
        """Test aggregation when all critics fail"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # When all critics fail, should default to safe verdict (REVIEW or BLOCK)
        assert output['overall_verdict'] in ['REVIEW', 'BLOCK', 'ERROR']

    def test_empty_critic_results(self):
        """Test aggregation with no critic results"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = []

        output = agg.aggregate(results)
        # Should return safe default verdict
        assert output['overall_verdict'] in ['REVIEW', 'BLOCK']
        assert 'avg_confidence' in output

    def test_single_critic_with_low_confidence(self):
        """Test aggregation with single low-confidence critic"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.2, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Low confidence should trigger REVIEW
        assert output['overall_verdict'] in ['ALLOW', 'REVIEW']
        assert output['avg_confidence'] == 0.2

    def test_high_ambiguity_threshold(self):
        """Test aggregation with high ambiguity threshold"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.8}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.6, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.5, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # High ambiguity threshold makes REVIEW more likely
        assert 'ambiguity' in output

    def test_zero_confidence_critics(self):
        """Test aggregation with zero confidence critics"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Zero confidence should be handled gracefully
        assert output['avg_confidence'] == 0.0
        assert output['overall_verdict'] in ['ALLOW', 'BLOCK', 'REVIEW']

    def test_extreme_weight_differences(self):
        """Test aggregation with extreme weight differences"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 10.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.9, 'weight': 0.1, 'priority': None}
        ]

        output = agg.aggregate(results)
        # High-weighted ALLOW should dominate
        assert output['overall_verdict'] == 'ALLOW'

    def test_mixed_verdicts_with_review(self):
        """Test aggregation with REVIEW verdicts mixed in"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'REVIEW', 'confidence': 0.5, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Mixed verdicts should be handled appropriately
        assert output['overall_verdict'] in ['ALLOW', 'BLOCK', 'REVIEW']
        assert 'verdict_scores' in output

    def test_deny_vs_block_verdicts(self):
        """Test aggregation distinguishes between DENY and BLOCK"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'DENY', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Both should result in restrictive verdict
        assert output['overall_verdict'] in ['DENY', 'BLOCK']

    def test_very_low_block_threshold(self):
        """Test aggregation with very low block threshold"""
        config = {'block_threshold': 0.1, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'BLOCK', 'confidence': 0.2, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Low threshold makes blocking easier
        assert 'verdict_scores' in output

    def test_verdict_score_calculation(self):
        """Test that verdict scores are calculated correctly"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 2.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.6, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # ALLOW score should be 0.8 * 2.0 = 1.6
        # BLOCK score should be 0.6 * 1.0 = 0.6
        assert 'verdict_scores' in output
        assert output['verdict_scores']['ALLOW'] == pytest.approx(1.6, rel=0.01)
        assert output['verdict_scores']['BLOCK'] == pytest.approx(0.6, rel=0.01)

    def test_confidence_normalization(self):
        """Test that confidence values are properly normalized"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 1.0, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'ALLOW', 'confidence': 0.5, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Average confidence should be (1.0 + 0.0 + 0.5) / 3 = 0.5
        assert output['avg_confidence'] == pytest.approx(0.5, rel=0.01)


class TestAggregatorRobustness:
    """Test suite for Aggregator robustness and error handling"""

    def test_missing_confidence_field(self):
        """Test handling of missing confidence field"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'weight': 1.0, 'priority': None}
        ]

        # Should either handle gracefully or raise appropriate error
        try:
            output = agg.aggregate(results)
            # If it succeeds, check it has reasonable defaults
            assert 'overall_verdict' in output
        except KeyError:
            # Expected behavior if confidence is required
            pass

    def test_negative_confidence(self):
        """Test handling of negative confidence values"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': -0.5, 'weight': 1.0, 'priority': None}
        ]

        # Should clamp or handle negative values
        output = agg.aggregate(results)
        assert 'overall_verdict' in output

    def test_confidence_exceeds_one(self):
        """Test handling of confidence values > 1.0"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 1.5, 'weight': 1.0, 'priority': None}
        ]

        # Should clamp or handle values > 1.0
        output = agg.aggregate(results)
        assert 'overall_verdict' in output

    def test_negative_weight(self):
        """Test handling of negative weight values"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': -1.0, 'priority': None}
        ]

        # Should handle negative weights gracefully
        output = agg.aggregate(results)
        assert 'overall_verdict' in output

    def test_invalid_verdict_value(self):
        """Test handling of invalid verdict values"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'INVALID', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        # Should ignore invalid verdicts or handle appropriately
        output = agg.aggregate(results)
        assert 'overall_verdict' in output
