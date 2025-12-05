"""
Unit Tests for Critic Explanation Formatter

Task 5.1: Per-Critic Explanation Formatter Tests

Tests the standardized explanation formatting for critic outputs,
including style enforcement, key information extraction, and
confidence/reasoning presentation.
"""

import pytest
from datetime import datetime

from ejc.core.explainability.critic_explanation_formatter import (
    CriticExplanationFormatter,
    CriticExplanation,
    ExplanationStyle,
    ConfidenceLevel,
    format_critic_output,
    format_multiple_critics
)


class TestCriticExplanationFormatter:
    """Tests for CriticExplanationFormatter"""

    def test_formatter_initialization(self):
        """Test formatter initialization with various options"""
        # Default initialization
        formatter = CriticExplanationFormatter()
        assert formatter.default_style == ExplanationStyle.VERBOSE
        assert formatter.enforce_style is True
        assert formatter.include_metadata is True

        # Custom initialization
        formatter = CriticExplanationFormatter(
            default_style=ExplanationStyle.COMPACT,
            enforce_style=False,
            include_metadata=False
        )
        assert formatter.default_style == ExplanationStyle.COMPACT
        assert formatter.enforce_style is False
        assert formatter.include_metadata is False

    def test_format_basic_critic_output(self):
        """Test formatting basic critic output"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'TestCritic',
            'verdict': 'ALLOW',
            'confidence': 0.85,
            'justification': 'The input appears safe and compliant with policies.'
        }

        explanation = formatter.format_critic_output(critic_output)

        assert explanation.critic_name == 'TestCritic'
        assert explanation.verdict == 'ALLOW'
        assert explanation.confidence == 0.85
        assert explanation.confidence_level == ConfidenceLevel.HIGH
        assert 'safe' in explanation.primary_reason.lower()

    def test_confidence_classification(self):
        """Test confidence level classification"""
        formatter = CriticExplanationFormatter()

        test_cases = [
            (0.95, ConfidenceLevel.VERY_HIGH),
            (0.80, ConfidenceLevel.HIGH),
            (0.60, ConfidenceLevel.MEDIUM),
            (0.40, ConfidenceLevel.LOW),
            (0.20, ConfidenceLevel.VERY_LOW)
        ]

        for confidence, expected_level in test_cases:
            level = formatter._classify_confidence(confidence)
            assert level == expected_level, f"Failed for confidence {confidence}"

    def test_extract_reasoning(self):
        """Test reasoning extraction from justification"""
        formatter = CriticExplanationFormatter()

        # Single line justification
        justification = "The request violates privacy policy."
        reasoning = ""
        primary, supporting = formatter._extract_reasoning(justification, reasoning)
        assert primary == "The request violates privacy policy."
        assert len(supporting) == 0

        # Multi-line justification
        justification = "Primary violation detected.\nSecondary issue found.\nAdditional concern noted."
        primary, supporting = formatter._extract_reasoning(justification, "")
        assert primary == "Primary violation detected."
        assert len(supporting) == 2
        assert "Secondary issue" in supporting[0]
        assert "Additional concern" in supporting[1]

    def test_extract_key_factors(self):
        """Test key factor extraction"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'TestCritic',
            'verdict': 'DENY',
            'confidence': 0.9,
            'risk_score': 0.75,
            'metadata': {
                'violations': ['privacy', 'security'],
                'severity': 'high'
            }
        }

        factors = formatter._extract_key_factors(critic_output)

        assert 'risk_score' in factors
        assert factors['risk_score'] == 0.75
        assert 'violations' in factors
        assert factors['violations'] == ['privacy', 'security']
        assert 'severity' in factors

    def test_generate_evidence_summary(self):
        """Test evidence summary generation"""
        formatter = CriticExplanationFormatter()

        # List evidence
        output1 = {'evidence': ['ev1', 'ev2', 'ev3']}
        summary1 = formatter._generate_evidence_summary(output1)
        assert "3 pieces" in summary1

        # Dict evidence
        output2 = {'evidence': {'type': 'test', 'source': 'manual'}}
        summary2 = formatter._generate_evidence_summary(output2)
        assert 'type' in summary2 and 'source' in summary2

        # No evidence
        output3 = {}
        summary3 = formatter._generate_evidence_summary(output3)
        assert summary3 is None

    def test_extract_warnings(self):
        """Test warning extraction"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'TestCritic',
            'warnings': ['Warning 1', 'Warning 2'],
            'metadata': {
                'warnings': 'Additional warning'
            }
        }

        warnings = formatter._extract_warnings(critic_output)

        assert len(warnings) == 3
        assert 'Warning 1' in warnings
        assert 'Warning 2' in warnings
        assert 'Additional warning' in warnings

    def test_extract_limitations(self):
        """Test limitation extraction"""
        formatter = CriticExplanationFormatter()

        # Low confidence should add limitation
        output1 = {
            'critic_name': 'TestCritic',
            'confidence': 0.3,
            'verdict': 'ALLOW'
        }
        limitations1 = formatter._extract_limitations(output1)
        assert len(limitations1) > 0
        assert any('confidence' in lim.lower() for lim in limitations1)

        # Explicit limitations
        output2 = {
            'critic_name': 'TestCritic',
            'confidence': 0.9,
            'limitations': ['Limited training data', 'Narrow scope']
        }
        limitations2 = formatter._extract_limitations(output2)
        assert 'Limited training data' in limitations2
        assert 'Narrow scope' in limitations2

    def test_style_enforcement(self):
        """Test style guideline enforcement"""
        formatter = CriticExplanationFormatter(enforce_style=True)

        # Test capitalization and period
        explanation = CriticExplanation(
            critic_name='TestCritic',
            verdict='ALLOW',
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            primary_reason='test reason without period'
        )

        enforced = formatter._enforce_style_guidelines(explanation)

        assert enforced.primary_reason[0].isupper()
        assert enforced.primary_reason.endswith('.')

        # Test length limit
        long_reason = 'a' * 300
        explanation2 = CriticExplanation(
            critic_name='TestCritic',
            verdict='ALLOW',
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            primary_reason=long_reason
        )

        enforced2 = formatter._enforce_style_guidelines(explanation2)
        assert len(enforced2.primary_reason) <= 200

    def test_format_verbose(self):
        """Test verbose text formatting"""
        formatter = CriticExplanationFormatter()

        explanation = CriticExplanation(
            critic_name='TestCritic',
            verdict='DENY',
            confidence=0.92,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            primary_reason='Violates security policy.',
            supporting_reasons=['Uses deprecated protocol', 'Missing authentication'],
            key_factors={'risk_level': 'high', 'violations': 2}
        )

        text = formatter._format_verbose(explanation)

        assert 'TestCritic' in text
        assert 'DENY' in text
        assert '0.92' in text
        assert 'Violates security policy' in text
        assert 'deprecated protocol' in text
        assert 'Missing authentication' in text
        assert 'Key Factors' in text

    def test_format_compact(self):
        """Test compact text formatting"""
        formatter = CriticExplanationFormatter()

        explanation = CriticExplanation(
            critic_name='TestCritic',
            verdict='ALLOW',
            confidence=0.75,
            confidence_level=ConfidenceLevel.HIGH,
            primary_reason='Request approved.'
        )

        text = formatter._format_compact(explanation)

        assert 'TestCritic' in text
        assert 'ALLOW' in text
        assert '0.75' in text
        assert 'Request approved' in text
        # Compact format should be one line
        assert '\n' not in text.strip()

    def test_format_narrative(self):
        """Test narrative text formatting"""
        formatter = CriticExplanationFormatter()

        explanation = CriticExplanation(
            critic_name='PrivacyCritic',
            verdict='ESCALATE',
            confidence=0.65,
            confidence_level=ConfidenceLevel.MEDIUM,
            primary_reason='Potential privacy concern detected.',
            supporting_reasons=['Personal data present', 'Consent unclear'],
            warnings=['Review recommended']
        )

        text = formatter._format_narrative(explanation)

        # Narrative should be cohesive prose
        assert 'PrivacyCritic' in text
        assert 'determined' in text or 'verdict' in text
        assert 'ESCALATE' in text
        assert 'medium confidence' in text.lower()
        assert 'privacy concern' in text.lower()
        assert 'personal data' in text.lower() or 'consent' in text.lower()

    def test_format_to_text_styles(self):
        """Test formatting to text with different styles"""
        formatter = CriticExplanationFormatter()

        explanation = CriticExplanation(
            critic_name='TestCritic',
            verdict='ALLOW',
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            primary_reason='Test reason.'
        )

        # Test each style
        verbose = formatter.format_to_text(explanation, ExplanationStyle.VERBOSE)
        assert len(verbose) > 100
        assert '===' in verbose

        compact = formatter.format_to_text(explanation, ExplanationStyle.COMPACT)
        assert len(compact) < len(verbose)

        narrative = formatter.format_to_text(explanation, ExplanationStyle.NARRATIVE)
        assert 'determined' in narrative or 'verdict' in narrative

        structured = formatter.format_to_text(explanation, ExplanationStyle.STRUCTURED)
        assert '{' in structured  # JSON format

    def test_format_critic_output_with_metadata(self):
        """Test formatting with metadata"""
        formatter = CriticExplanationFormatter(include_metadata=True)

        critic_output = {
            'critic_name': 'MetaCritic',
            'verdict': 'ALLOW',
            'confidence': 0.88,
            'justification': 'Analysis complete.',
            'metadata': {
                'processing_time_ms': 125.5,
                'priority': 'high',
                'weight': 1.5,
                'timestamp': '2025-01-15T10:30:00Z'
            }
        }

        explanation = formatter.format_critic_output(critic_output)

        assert explanation.processing_time_ms == 125.5
        assert explanation.critic_priority == 'high'
        assert explanation.critic_weight == 1.5
        assert explanation.timestamp is not None

    def test_explanation_to_dict(self):
        """Test converting explanation to dictionary"""
        explanation = CriticExplanation(
            critic_name='TestCritic',
            verdict='DENY',
            confidence=0.9,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            primary_reason='Test reason.',
            supporting_reasons=['Reason 1', 'Reason 2'],
            key_factors={'score': 0.8}
        )

        data = explanation.to_dict()

        assert data['critic_name'] == 'TestCritic'
        assert data['verdict'] == 'DENY'
        assert data['confidence'] == 0.9
        assert data['confidence_level'] == 'very_high'
        assert data['primary_reason'] == 'Test reason.'
        assert len(data['supporting_reasons']) == 2
        assert 'score' in data['key_factors']

    def test_convenience_format_critic_output(self):
        """Test convenience function for formatting"""
        critic_output = {
            'critic_name': 'QuickCritic',
            'verdict': 'ALLOW',
            'confidence': 0.75,
            'justification': 'Request is safe.'
        }

        # Test verbose style
        text = format_critic_output(critic_output, ExplanationStyle.VERBOSE)
        assert 'QuickCritic' in text
        assert 'ALLOW' in text

        # Test compact style
        compact = format_critic_output(critic_output, ExplanationStyle.COMPACT)
        assert len(compact) < len(text)

    def test_format_multiple_critics(self):
        """Test formatting multiple critic outputs"""
        outputs = [
            {
                'critic_name': 'Critic1',
                'verdict': 'ALLOW',
                'confidence': 0.8,
                'justification': 'First critic approves.'
            },
            {
                'critic_name': 'Critic2',
                'verdict': 'DENY',
                'confidence': 0.9,
                'justification': 'Second critic denies.'
            },
            {
                'critic_name': 'Critic3',
                'verdict': 'ESCALATE',
                'confidence': 0.6,
                'justification': 'Third critic escalates.'
            }
        ]

        # Compact format
        compact = format_multiple_critics(outputs, ExplanationStyle.COMPACT)
        assert 'Critic1' in compact
        assert 'Critic2' in compact
        assert 'Critic3' in compact
        assert 'ALLOW' in compact
        assert 'DENY' in compact

        # Verbose format
        verbose = format_multiple_critics(outputs, ExplanationStyle.VERBOSE)
        assert len(verbose) > len(compact)
        assert 'Critic Explanations' in verbose

    def test_missing_fields_handling(self):
        """Test handling of missing/incomplete critic output"""
        formatter = CriticExplanationFormatter()

        # Minimal output
        minimal_output = {
            'critic_name': 'MinimalCritic',
            'verdict': 'UNKNOWN'
        }

        explanation = formatter.format_critic_output(minimal_output)

        assert explanation.critic_name == 'MinimalCritic'
        assert explanation.verdict == 'UNKNOWN'
        assert explanation.confidence == 0.5  # Default
        assert explanation.confidence_level == ConfidenceLevel.MEDIUM

        # Empty output should still work
        empty_output = {}
        explanation2 = formatter.format_critic_output(empty_output)
        assert explanation2.critic_name == 'UnknownCritic'

    def test_complex_nested_factors(self):
        """Test extraction of complex nested factors"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'ComplexCritic',
            'verdict': 'DENY',
            'confidence': 0.85,
            'risk_score': 0.9,
            'safety_score': 0.3,
            'metadata': {
                'violations': {
                    'privacy': 3,
                    'security': 2
                },
                'patterns_matched': ['pattern_a', 'pattern_b'],
                'severity': 'critical'
            }
        }

        explanation = formatter.format_critic_output(critic_output)

        assert 'risk_score' in explanation.key_factors
        assert 'safety_score' in explanation.key_factors
        assert 'violations' in explanation.key_factors
        assert 'patterns_matched' in explanation.key_factors

    def test_style_persistence_across_formats(self):
        """Test that style is maintained across different formats"""
        formatter = CriticExplanationFormatter(
            default_style=ExplanationStyle.COMPACT,
            enforce_style=True
        )

        critic_output = {
            'critic_name': 'StyleCritic',
            'verdict': 'ALLOW',
            'confidence': 0.7,
            'justification': 'test without capitalization or period'
        }

        explanation = formatter.format_critic_output(critic_output)

        # Style enforcement should have applied
        assert explanation.primary_reason[0].isupper()
        assert explanation.primary_reason.endswith('.')

    def test_timestamp_handling(self):
        """Test timestamp parsing and handling"""
        formatter = CriticExplanationFormatter()

        # ISO format timestamp
        critic_output = {
            'critic_name': 'TimeCritic',
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'metadata': {
                'timestamp': '2025-01-15T10:30:00Z'
            }
        }

        explanation = formatter.format_critic_output(critic_output)
        assert explanation.timestamp is not None
        assert isinstance(explanation.timestamp, datetime)

        # No timestamp provided - should use current time
        critic_output2 = {
            'critic_name': 'TimeCritic2',
            'verdict': 'ALLOW',
            'confidence': 0.8
        }

        explanation2 = formatter.format_critic_output(critic_output2)
        assert explanation2.timestamp is not None


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_justification(self):
        """Test handling of empty justification"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'SilentCritic',
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'justification': ''
        }

        explanation = formatter.format_critic_output(critic_output)
        assert explanation.primary_reason != ''  # Should have fallback

    def test_very_long_justification(self):
        """Test handling of very long justification"""
        formatter = CriticExplanationFormatter(enforce_style=True)

        long_text = 'a' * 500

        critic_output = {
            'critic_name': 'VerboseCritic',
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'justification': long_text
        }

        explanation = formatter.format_critic_output(critic_output)

        # Should be truncated by style enforcement
        assert len(explanation.primary_reason) <= 200

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'UnicödeCritic™',
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'justification': 'Contains special characters: ñ, ü, ©, ®, ™'
        }

        explanation = formatter.format_critic_output(critic_output)
        text = formatter.format_to_text(explanation)

        assert 'UnicödeCritic' in text
        assert '™' in text

    def test_none_values(self):
        """Test handling of None values in output"""
        formatter = CriticExplanationFormatter()

        critic_output = {
            'critic_name': 'NullCritic',
            'verdict': None,
            'confidence': None,
            'justification': None
        }

        # Should handle gracefully
        explanation = formatter.format_critic_output(critic_output)
        assert explanation.critic_name == 'NullCritic'
        assert explanation.verdict == 'UNKNOWN'  # Default for None
        assert explanation.confidence == 0.5  # Default

    def test_invalid_confidence_values(self):
        """Test handling of invalid confidence values"""
        formatter = CriticExplanationFormatter()

        # Confidence > 1.0
        output1 = {
            'critic_name': 'HighCritic',
            'verdict': 'ALLOW',
            'confidence': 1.5  # Invalid but should be handled
        }

        explanation1 = formatter.format_critic_output(output1)
        # Should still classify, even if out of range
        assert explanation1.confidence_level is not None

        # Negative confidence
        output2 = {
            'critic_name': 'LowCritic',
            'verdict': 'ALLOW',
            'confidence': -0.5
        }

        explanation2 = formatter.format_critic_output(output2)
        assert explanation2.confidence_level is not None
