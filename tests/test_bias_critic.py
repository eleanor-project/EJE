"""
Tests for Bias & Objectivity Integrity Critic - Phase 5A

Tests bias detection and fairness analysis functionality.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.critics.official.bias_objectivity_critic import BiasObjectivityCritic


class TestBiasObjectivityCritic:
    """Test suite for Bias & Objectivity Integrity Critic."""

    @pytest.fixture
    def critic(self):
        """Create a BiasObjectivityCritic instance."""
        return BiasObjectivityCritic(
            protected_attributes=['race', 'gender', 'age'],
            fairness_threshold=0.8
        )

    def test_critic_initialization(self, critic):
        """Test critic initializes correctly."""
        assert critic.name == "BiasObjectivityCritic"
        assert critic.weight == 1.5  # Higher weight for critical concern
        assert critic.priority == "high"
        assert len(critic.protected_attributes) == 3
        assert critic.fairness_threshold == 0.8

    def test_evaluate_basic_case(self, critic):
        """Test basic case evaluation."""
        case = {
            'text': 'AI system for loan approval using credit history',
            'context': {
                'data_description': 'Balanced dataset with diverse demographics',
                'model_type': 'logistic_regression'
            }
        }

        result = critic.evaluate(case)

        assert 'verdict' in result
        assert 'confidence' in result
        assert 'justification' in result
        assert 'bias_risk_score' in result
        assert result['verdict'] in ['ALLOW', 'DENY', 'REVIEW']
        assert 0.0 <= result['confidence'] <= 1.0
        assert 0.0 <= result['bias_risk_score'] <= 1.0

    def test_high_bias_risk_detection(self, critic):
        """Test detection of high bias risk."""
        case = {
            'text': 'AI hiring system with historical bias and imbalanced training data',
            'context': {
                'data_description': 'Legacy data from traditional hiring practices, severely underrepresented minorities',
                'model_type': 'neural_network',
                'protected_groups': {'majority': 1000, 'minority': 50}
            }
        }

        result = critic.evaluate(case)

        # Should detect high bias risk
        assert result['bias_risk_score'] > 0.5
        # Likely verdict is DENY or REVIEW
        assert result['verdict'] in ['DENY', 'REVIEW']
        # Should detect bias signals
        assert len(result['detected_bias_types']) > 0
        assert 'historical_bias' in result['detected_bias_types'] or \
               'representation_bias' in result['detected_bias_types']

    def test_low_bias_risk_detection(self, critic):
        """Test detection of low bias risk."""
        case = {
            'text': 'Well-designed recommendation system with fairness constraints',
            'context': {
                'data_description': 'Balanced, representative, and diverse dataset with regular fairness audits',
                'model_type': 'fair_classifier',
                'protected_groups': {'group_a': 500, 'group_b': 480, 'group_c': 520}
            }
        }

        result = critic.evaluate(case)

        # Should detect low bias risk
        assert result['bias_risk_score'] < 0.5
        # Likely verdict is ALLOW
        assert result['verdict'] in ['ALLOW', 'REVIEW']

    def test_fairness_assessment_with_outcomes(self, critic):
        """Test fairness assessment when outcome data is provided."""
        case = {
            'text': 'Credit scoring system',
            'context': {
                'outcomes': {
                    'group_a': {'positive': 80, 'total': 100},
                    'group_b': {'positive': 85, 'total': 100}
                },
                'protected_groups': {'group_a': 100, 'group_b': 100}
            }
        }

        result = critic.evaluate(case)

        # Should calculate fairness score
        assert 'fairness_metrics' in result
        assert 'score' in result['fairness_metrics']
        # Groups have similar rates (80% vs 85%), should be fair
        assert result['fairness_metrics']['score'] > 0.5

    def test_fairness_assessment_disparate_impact(self, critic):
        """Test detection of disparate impact."""
        case = {
            'text': 'Loan approval system',
            'context': {
                'outcomes': {
                    'group_a': {'positive': 90, 'total': 100},  # 90% approval
                    'group_b': {'positive': 50, 'total': 100}   # 50% approval - disparate impact
                },
                'protected_groups': {'group_a': 100, 'group_b': 100}
            }
        }

        result = critic.evaluate(case)

        # Should detect unfairness (50/90 = 0.556 < 0.8 threshold)
        assert result['fairness_metrics']['score'] < 0.8
        # Should have higher bias risk
        assert result['bias_risk_score'] > 0.4

    def test_representation_score_calculation(self, critic):
        """Test representation scoring."""
        # Test with severely imbalanced groups
        case1 = {
            'text': 'AI system',
            'context': {
                'protected_groups': {'majority': 950, 'minority': 50}  # 5% minority
            }
        }

        result1 = critic.evaluate(case1)
        assert result1['representation_score'] < 0.5  # Poor representation

        # Test with balanced groups
        case2 = {
            'text': 'AI system',
            'context': {
                'protected_groups': {'group_a': 400, 'group_b': 350, 'group_c': 250}
            }
        }

        result2 = critic.evaluate(case2)
        assert result2['representation_score'] > 0.5  # Good representation

    def test_bias_signal_detection(self, critic):
        """Test various bias type keyword detection."""
        # Test historical bias keywords
        case = {
            'text': 'System trained on historical data following legacy patterns',
            'context': {'data_description': ''}
        }

        result = critic.evaluate(case)
        assert 'historical_bias' in result['detected_bias_types']

        # Test sampling bias keywords
        case2 = {
            'text': 'Model using convenience sample with non-random selection',
            'context': {'data_description': ''}
        }

        result2 = critic.evaluate(case2)
        assert 'sampling_bias' in result2['detected_bias_types']

    def test_output_validation(self, critic):
        """Test that output matches expected format."""
        case = {
            'text': 'Test AI system',
            'context': {}
        }

        result = critic.evaluate(case)

        # Check required fields
        assert 'verdict' in result
        assert 'confidence' in result
        assert 'justification' in result
        assert 'critic' in result  # Added by _enrich_output
        assert 'weight' in result
        assert 'priority' in result
        assert 'timestamp' in result

        # Check custom fields
        assert 'bias_risk_score' in result
        assert 'detected_bias_types' in result
        assert 'fairness_metrics' in result
        assert 'representation_score' in result

    def test_empty_case_handling(self, critic):
        """Test handling of cases with minimal information."""
        case = {
            'text': 'AI system',
            'context': {}
        }

        result = critic.evaluate(case)

        # Should return neutral/review verdict without crashing
        assert result['verdict'] in ['ALLOW', 'REVIEW', 'DENY']
        assert isinstance(result['justification'], str)
        assert len(result['justification']) > 0


def test_bias_type_taxonomy():
    """Test that all 17 bias types are defined."""
    assert len(BiasObjectivityCritic.BIAS_TYPES) == 17
    assert 'historical_bias' in BiasObjectivityCritic.BIAS_TYPES
    assert 'representation_bias' in BiasObjectivityCritic.BIAS_TYPES
    assert 'algorithmic_bias' in BiasObjectivityCritic.BIAS_TYPES


def test_fairness_thresholds():
    """Test fairness metric thresholds are properly defined."""
    thresholds = BiasObjectivityCritic.FAIRNESS_THRESHOLDS
    assert 'disparate_impact' in thresholds
    assert thresholds['disparate_impact'] == 0.8  # 80% rule
    assert 'statistical_parity' in thresholds
    assert 'equal_opportunity' in thresholds
