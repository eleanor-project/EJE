"""
Tests for Privacy Protection Critic - Phase 5B

Tests privacy analysis, PET recommendations, and World Bank compliance checking.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.critics.official.privacy_protection_critic import PrivacyProtectionCritic


class TestPrivacyProtectionCritic:
    """Test suite for Privacy Protection Critic."""

    def test_critic_initialization(self):
        """Test critic can be initialized with default parameters."""
        critic = PrivacyProtectionCritic()
        assert critic.name == "PrivacyProtectionCritic"
        assert critic.weight == 1.5
        assert critic.priority == "high"

    def test_high_pii_risk_detection(self):
        """Test detection of high PII risk scenarios."""
        critic = PrivacyProtectionCritic()

        case = {
            'text': 'System processes user SSN, email, phone numbers, and health records',
            'context': {
                'data_types': ['ssn', 'email', 'phone', 'health_data'],
                'pet_usage': [],
                'consent_mechanism': '',
                'retention_policy': ''
            }
        }

        result = critic.evaluate(case)

        assert result['verdict'] in ['DENY', 'REVIEW']
        assert result['pii_risk'] > 0.5
        assert 'privacy' in result['justification'].lower()

    def test_with_privacy_protections(self):
        """Test case with appropriate privacy protections."""
        critic = PrivacyProtectionCritic()

        case = {
            'text': 'System uses differential privacy and encryption for analytics',
            'context': {
                'data_types': ['aggregated_data'],
                'pet_usage': ['differential_privacy', 'encryption'],
                'consent_mechanism': 'explicit informed consent with granular controls',
                'retention_policy': 'data deleted after 30 days with secure disposal',
                'pseudonymization': True
            }
        }

        result = critic.evaluate(case)

        assert result['verdict'] in ['ALLOW', 'REVIEW']
        assert result['pet_score'] > 0.5
        assert result['consent_score'] > 0.5

    def test_pet_recommendations(self):
        """Test PET recommendations for high-risk data."""
        critic = PrivacyProtectionCritic()

        case = {
            'text': 'Processing sensitive biometric data',
            'context': {
                'data_types': ['biometric', 'genetic'],
                'pet_usage': [],
            }
        }

        result = critic.evaluate(case)

        assert 'recommended_pets' in result
        assert len(result['recommended_pets']) > 0
        assert result['pii_risk'] > 0.6  # High risk for biometric data

    def test_world_bank_compliance_checking(self):
        """Test World Bank privacy checklist compliance."""
        critic = PrivacyProtectionCritic()

        # Case with good compliance
        compliant_case = {
            'text': 'Privacy-compliant data processing',
            'context': {
                'data_types': ['age', 'gender'],
                'consent_mechanism': 'explicit consent obtained',
                'retention_policy': 'time-limited with automatic deletion',
                'pseudonymization': True,
                'third_party_sharing': False
            }
        }

        result = critic.evaluate(compliant_case)

        assert result['wb_checklist_compliance'] > 0.5
        assert result['verdict'] in ['ALLOW', 'REVIEW']

    def test_no_consent_mechanism(self):
        """Test handling of missing consent mechanism."""
        critic = PrivacyProtectionCritic()

        case = {
            'text': 'Collecting user data',
            'context': {
                'data_types': ['email', 'name'],
                'consent_mechanism': '',  # No consent
                'pet_usage': []
            }
        }

        result = critic.evaluate(case)

        assert result['consent_score'] < 0.5
        assert result['verdict'] in ['DENY', 'REVIEW']

    def test_data_minimization_assessment(self):
        """Test data minimization principle checking."""
        critic = PrivacyProtectionCritic()

        # Good minimization
        minimal_case = {
            'text': 'Collecting only necessary data for specified purpose',
            'context': {
                'data_types': ['user_id', 'purchase_amount']
            }
        }

        result = critic.evaluate(minimal_case)
        assert result['minimization_score'] > 0.5

        # Poor minimization
        excessive_case = {
            'text': 'Collecting all available data just in case for future use',
            'context': {
                'data_types': [
                    'name', 'email', 'phone', 'address', 'ssn',
                    'browsing_history', 'location', 'contacts', 'photos'
                ]
            }
        }

        result = critic.evaluate(excessive_case)
        assert result['minimization_score'] < 0.6

    def test_retention_policy_evaluation(self):
        """Test retention and disposal policy evaluation."""
        critic = PrivacyProtectionCritic()

        # Good retention policy
        good_case = {
            'text': 'Data retention policy',
            'context': {
                'retention_policy': 'Data retained for 90 days then automatically deleted with secure disposal'
            }
        }

        result = critic.evaluate(good_case)
        assert result['retention_score'] > 0.6

        # Bad retention policy
        bad_case = {
            'text': 'Data retention policy',
            'context': {
                'retention_policy': 'Data retained indefinitely'
            }
        }

        result = critic.evaluate(bad_case)
        assert result['retention_score'] < 0.5

    def test_strict_mode(self):
        """Test strict mode for enhanced privacy requirements."""
        critic = PrivacyProtectionCritic(strict_mode=True)

        case = {
            'text': 'Processing personal data',
            'context': {
                'data_types': ['email', 'name'],
                'pet_usage': [],
                'consent_mechanism': 'implied consent'
            }
        }

        result = critic.evaluate(case)

        # Strict mode should be more critical
        assert result['verdict'] in ['DENY', 'REVIEW']

    def test_output_format(self):
        """Test that output contains all required fields."""
        critic = PrivacyProtectionCritic()

        case = {
            'text': 'Test case',
            'context': {}
        }

        result = critic.evaluate(case)

        # Check required fields
        required_fields = [
            'verdict', 'confidence', 'justification',
            'privacy_risk_score', 'pii_risk', 'pet_score',
            'consent_score', 'minimization_score', 'retention_score',
            'wb_checklist_compliance', 'recommended_pets'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Check metadata added by base critic
        assert 'critic' in result
        assert 'timestamp' in result
        assert result['critic'] == "PrivacyProtectionCritic"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
