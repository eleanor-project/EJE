"""Unit tests for CustomRuleCritic"""
import pytest
from src.eje.critics.community.custom_rule import CustomRuleCritic


class TestCustomRuleCritic:
    """Test suite for CustomRuleCritic"""

    def test_allow_with_transparency_keyword(self):
        """Test that cases with 'transparency' keyword get ALLOW verdict"""
        critic = CustomRuleCritic()
        case = {"text": "This case involves transparency in decision-making"}

        result = critic.evaluate(case)

        assert result['verdict'] == 'ALLOW'
        assert result['confidence'] == 1.0
        assert 'justification' in result

    def test_review_without_transparency(self):
        """Test that cases without 'transparency' keyword get REVIEW verdict"""
        critic = CustomRuleCritic()
        case = {"text": "This is a regular case"}

        result = critic.evaluate(case)

        assert result['verdict'] == 'REVIEW'
        assert result['confidence'] == 0.5
        assert 'justification' in result

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive"""
        critic = CustomRuleCritic()
        case = {"text": "TRANSPARENCY is important"}

        result = critic.evaluate(case)

        assert result['verdict'] == 'ALLOW'
        assert result['confidence'] == 1.0

    def test_returns_required_fields(self):
        """Test that critic returns all required fields"""
        critic = CustomRuleCritic()
        case = {"text": "test case"}

        result = critic.evaluate(case)

        assert 'verdict' in result
        assert 'confidence' in result
        assert 'justification' in result
        assert isinstance(result['verdict'], str)
        assert isinstance(result['confidence'], (int, float))
        assert isinstance(result['justification'], str)

    def test_handles_empty_text(self):
        """Test that critic handles edge cases gracefully"""
        critic = CustomRuleCritic()
        case = {"text": ""}

        result = critic.evaluate(case)

        # Should still return valid result
        assert 'verdict' in result
        assert result['verdict'] == 'REVIEW'  # No transparency keyword in empty string
