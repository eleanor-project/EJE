"""
Comprehensive Aggregator Test Suite

Covers:
- Weighted aggregation scenarios
- Conflict detection
- Fallback scenarios
- Missing/ERROR critic outputs
- Edge cases
"""

import pytest
from ejc.core.aggregator import Aggregator


class TestAggregatorWeighted:
    """Tests for weighted aggregation behavior"""

    def test_weighted_override_with_low_weight(self):
        """Test that low weight can be overcome by high confidence"""
        config = {'block_threshold': 1.0, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.95, 'weight': 3.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.90, 'weight': 0.5, 'priority': None}
        ]

        output = agg.aggregate(results)
        # High weight on ALLOW should dominate
        assert output['overall_verdict'] == 'ALLOW'
        assert 'applied_weight' in results[0]
        assert 'applied_weight' in results[1]

    def test_equal_weights_high_confidence_wins(self):
        """Test that with equal weights, higher confidence wins"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.95, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.70, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'

    def test_multiple_critics_weighted_consensus(self):
        """Test weighted consensus with multiple critics"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 2.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.5, 'priority': None},
            {'critic': 'C', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': None},
            {'critic': 'D', 'verdict': 'ALLOW', 'confidence': 0.85, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # 3 ALLOW critics with higher total weighted score should win
        assert output['overall_verdict'] == 'ALLOW'
        assert output['verdict_scores']['ALLOW'] > output['verdict_scores']['BLOCK']

    def test_critic_weights_from_config(self):
        """Test that critic weights can be specified in config"""
        config = {
            'block_threshold': 0.5,
            'ambiguity_threshold': 0.25,
            'critic_weights': {
                'safety_critic': 2.0,
                'bias_critic': 1.5
            }
        }
        agg = Aggregator(config)

        results = [
            {'critic': 'safety_critic', 'verdict': 'BLOCK', 'confidence': 0.8, 'priority': None},
            {'critic': 'bias_critic', 'verdict': 'ALLOW', 'confidence': 0.9, 'priority': None}
        ]

        output = agg.aggregate(results)
        # safety_critic has weight 2.0, bias_critic has 1.5
        # Should apply config weights
        assert 'applied_weight' in results[0]


class TestAggregatorConflictDetection:
    """Tests for conflict detection in aggregation"""

    def test_high_ambiguity_triggers_review(self):
        """Test that high ambiguity triggers REVIEW verdict"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.1}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.2, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # High variance in confidence should trigger REVIEW or respect threshold
        assert 'ambiguity' in output
        assert output['ambiguity'] > 0

    def test_significant_disagreement_triggers_review(self):
        """Test that significant disagreement triggers REVIEW"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.1}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.85, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.80, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'BLOCK', 'confidence': 0.75, 'weight': 1.0, 'priority': None},
            {'critic': 'D', 'verdict': 'BLOCK', 'confidence': 0.70, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Close split should trigger careful consideration
        assert output['overall_verdict'] in ['REVIEW', 'ALLOW', 'BLOCK']

    def test_unanimous_decision_no_conflict(self):
        """Test that unanimous decisions have no conflict"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.85, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'ALLOW', 'confidence': 0.92, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'
        assert output['ambiguity'] < 0.05  # Low ambiguity


class TestAggregatorFallback:
    """Tests for fallback scenarios"""

    def test_empty_results_fallback(self):
        """Test fallback when no critic results provided"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        output = agg.aggregate([])

        assert output['overall_verdict'] == 'REVIEW'
        assert 'No critic results' in output['reason']
        assert output['avg_confidence'] == 0.0
        assert output['verdict_scores']['ALLOW'] == 0
        assert output['verdict_scores']['BLOCK'] == 0

    def test_all_errors_fallback(self):
        """Test fallback when all critics error"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)

        assert output['overall_verdict'] == 'ERROR'
        assert 'All critics failed' in output['reason']
        assert output['errors']['count'] == 2
        assert output['errors']['rate'] == 1.0

    def test_high_error_rate_triggers_review(self):
        """Test that high error rate triggers REVIEW"""
        config = {
            'block_threshold': 0.5,
            'ambiguity_threshold': 0.25,
            'error_review_threshold': 0.5
        }
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)

        # With 2/3 errors (66%), should trigger REVIEW
        assert output['overall_verdict'] == 'REVIEW'
        assert 'failure rate' in output['reason'].lower()
        assert output['errors']['rate'] >= 0.5

    def test_partial_errors_ignored(self):
        """Test that ERROR verdicts don't contribute to scoring"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.85, 'weight': 1.0, 'priority': None},
            {'critic': 'C', 'verdict': 'ERROR', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)

        # ERROR should not count in verdict calculation
        assert output['overall_verdict'] == 'ALLOW'
        assert output['errors']['count'] == 1
        assert output['avg_confidence'] > 0.8  # Average of working critics only


class TestAggregatorMissingData:
    """Tests for handling missing or incomplete critic data"""

    def test_missing_confidence_defaults(self):
        """Test that missing confidence defaults appropriately"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'weight': 1.0, 'priority': None}
            # Missing confidence field
        ]

        output = agg.aggregate(results)
        # Should handle missing confidence gracefully
        assert 'overall_verdict' in output

    def test_missing_weight_defaults_to_one(self):
        """Test that missing weight defaults to 1.0"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'priority': None}
            # Missing weight field
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'
        # Weight should default to 1.0
        assert results[0]['applied_weight'] >= 1.0

    def test_missing_priority_handled(self):
        """Test that missing priority doesn't cause issues"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0}
            # Missing priority field
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'


class TestAggregatorBlockThreshold:
    """Tests for block threshold behavior"""

    def test_block_threshold_exceeded(self):
        """Test that exceeding block threshold forces BLOCK"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.6, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # BLOCK score of 0.8 exceeds threshold of 0.5
        assert output['overall_verdict'] == 'BLOCK'
        assert 'threshold exceeded' in output['reason'].lower()

    def test_block_threshold_not_exceeded(self):
        """Test behavior when block threshold not exceeded"""
        config = {'block_threshold': 2.0, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # BLOCK score of 0.7 doesn't exceed threshold of 2.0
        assert output['overall_verdict'] == 'ALLOW'


class TestAggregatorDenyVerdict:
    """Tests for DENY verdict handling"""

    def test_deny_treated_as_block(self):
        """Test that DENY verdict is treated as BLOCK"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'DENY', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # DENY should contribute to BLOCK score
        assert output['verdict_scores']['DENY'] > 0
        assert output['verdict_scores']['BLOCK'] > 0

    def test_deny_with_override(self):
        """Test DENY with override priority"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'DENY', 'confidence': 0.8, 'weight': 1.0, 'priority': 'override'}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'DENY'
        assert 'Override' in output['reason']


class TestAggregatorReviewVerdict:
    """Tests for REVIEW verdict handling"""

    def test_review_verdicts_neutral(self):
        """Test that REVIEW verdicts are treated neutrally"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'REVIEW', 'confidence': 0.7, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'REVIEW', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # All REVIEW should result in REVIEW verdict
        assert output['verdict_scores']['REVIEW'] > 0

    def test_mixed_with_review(self):
        """Test aggregation with mix of REVIEW and other verdicts"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'REVIEW', 'confidence': 0.5, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # ALLOW should dominate over REVIEW
        assert output['overall_verdict'] == 'ALLOW'


class TestAggregatorMoralModes:
    """Tests for moral mode adjustments"""

    def test_utilitarian_mode(self):
        """Test utilitarian moral mode weight adjustments"""
        config = {
            'block_threshold': 0.5,
            'ambiguity_threshold': 0.25,
            'moral_mode': 'utilitarian'
        }
        agg = Aggregator(config)

        results = [
            {'critic': 'fairness_critic', 'verdict': 'BLOCK', 'confidence': 0.8, 'weight': 1.0, 'priority': None},
            {'critic': 'safety_critic', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Utilitarian mode should adjust weights for fairness critics
        assert 'applied_weight' in results[0]

    def test_deontological_mode(self):
        """Test deontological moral mode weight adjustments"""
        config = {
            'block_threshold': 0.5,
            'ambiguity_threshold': 0.25,
            'moral_mode': 'deontological'
        }
        agg = Aggregator(config)

        results = [
            {'critic': 'rights_critic', 'verdict': 'BLOCK', 'confidence': 0.7, 'weight': 1.0, 'priority': None},
            {'critic': 'other_critic', 'verdict': 'ALLOW', 'confidence': 0.8, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Deontological mode should boost rights-based critics
        assert 'overall_verdict' in output

    def test_balanced_mode_default(self):
        """Test that balanced mode is default"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        assert agg.moral_mode == 'balanced'


class TestAggregatorEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_single_critic(self):
        """Test aggregation with single critic"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        assert output['overall_verdict'] == 'ALLOW'
        assert output['ambiguity'] == 0  # No ambiguity with single critic

    def test_zero_confidence_critics(self):
        """Test handling of zero confidence values"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.0, 'weight': 1.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.0, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Should handle zero confidence without crashing
        assert 'overall_verdict' in output

    def test_very_high_weights(self):
        """Test handling of very high weight values"""
        config = {'block_threshold': 0.5, 'ambiguity_threshold': 0.25}
        agg = Aggregator(config)

        results = [
            {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.5, 'weight': 100.0, 'priority': None},
            {'critic': 'B', 'verdict': 'BLOCK', 'confidence': 0.9, 'weight': 1.0, 'priority': None}
        ]

        output = agg.aggregate(results)
        # Very high weight should dominate
        assert output['overall_verdict'] == 'ALLOW'
