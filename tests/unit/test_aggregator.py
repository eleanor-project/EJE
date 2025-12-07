"""Unit tests for the Aggregator"""
import pytest
from ejc.core.aggregator import Aggregator


class TestAggregator:
    """Test suite for Aggregator class"""

    def test_simple_allow_verdict(self):
        """Test aggregation when all critics vote ALLOW"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'
        assert output['avg_confidence'] > 0

    def test_simple_block_verdict(self):
        """Test aggregation when critics vote to block"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'BLOCK', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'BLOCK'

    def test_override_priority(self):
        """Test that override priority takes precedence"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25, 'critic_priorities': {}}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'Security', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': 'override'}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'BLOCK'
        assert 'Override' in output['reason']

    def test_review_on_disagreement(self):
        """Test that disagreement triggers REVIEW"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.1}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # With disagreement and different verdicts, should trigger REVIEW
        assert output['overall_verdict'] in ['REVIEW', 'BLOCK']

    def test_weighted_aggregation(self):
        """Test that weights affect the outcome"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 2.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 0.5, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Higher weighted ALLOW should dominate
        assert output['overall_verdict'] == 'ALLOW'

    def test_verdict_scores_present(self):
        """Test that verdict_scores are included in output"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert 'verdict_scores' in output
        assert 'ALLOW' in output['verdict_scores']
        assert 'BLOCK' in output['verdict_scores']

    def test_average_confidence(self):
        """Test that average confidence is calculated correctly"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.6, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Average of 0.8 and 0.6 should be 0.7
        assert output['avg_confidence'] == pytest.approx(0.7, rel=0.01)

    def test_missing_critic_results_returns_review(self):
        """No critic output should trigger REVIEW with informative reason."""
        agg = Aggregator()

        output = agg.aggregate([])

        assert output['overall_verdict'] == 'REVIEW'
        assert output['reason'] == 'No critic results available'
        assert output['verdict_scores'] == {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0}
        assert output['errors'] == {'count': 0, 'rate': 0.0}

    def test_conflict_detection_escalates_review(self):
        """Significant disagreement with high ambiguity should return REVIEW."""
        agg = Aggregator({'ambiguity_threshold': 0.05})

        results = [
            {'critic': 'fairness', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'safety', 'verdict': 'BLOCK', 'confidence': 0.82, 'weight': 1.0, 'priority': None},
        ]

        output = agg.aggregate(results)

        assert output['overall_verdict'] == 'REVIEW'
        assert 'ambiguity' in output and output['ambiguity'] > 0
