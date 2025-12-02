"""
Tests for MultiLevelExplainer (Issue #170)

Tests multi-level explanation generation for different audiences.
"""

import pytest
import json
from src.ejc.core.explainability.multi_level_explainer import (
    MultiLevelExplainer,
    AudienceLevel,
    MultiLevelExplanation
)


@pytest.fixture
def sample_decision():
    """Sample EJE decision for testing."""
    return {
        'decision_id': 'test_ml_001',
        'timestamp': '2024-01-01T12:00:00Z',
        'input_data': {
            'request_id': '12345',
            'amount': 5000,
            'credit_score': 720,
            'income': 75000
        },
        'critic_reports': [
            {
                'critic_name': 'CreditScoreCritic',
                'verdict': 'APPROVE',
                'confidence': 0.85,
                'justification': 'Credit score of 720 exceeds threshold of 650. Strong payment history observed.'
            },
            {
                'critic_name': 'IncomeVerificationCritic',
                'verdict': 'APPROVE',
                'confidence': 0.90,
                'justification': 'Income of 75000 is within acceptable range for requested amount.'
            },
            {
                'critic_name': 'FraudDetectionCritic',
                'verdict': 'DENY',
                'confidence': 0.60,
                'justification': 'Minor anomaly detected in transaction pattern. Recommend review.'
            }
        ],
        'aggregation': {
            'verdict': 'APPROVE',
            'confidence': 0.78,
            'agree_count': 2,
            'disagree_count': 1,
            'conflicts': []
        },
        'governance_outcome': {
            'verdict': 'APPROVE',
            'confidence': 0.78,
            'governance_applied': False
        },
        'precedents': [],
        'escalated': False
    }


@pytest.fixture
def explainer():
    """Create a MultiLevelExplainer instance."""
    return MultiLevelExplainer(include_justifications=True)


class TestMultiLevelExplainer:
    """Test suite for MultiLevelExplainer."""

    def test_initialization(self, explainer):
        """Test explainer initialization."""
        assert explainer.include_justifications is True

    def test_executive_summary(self, explainer, sample_decision):
        """Test executive summary generation."""
        summary = explainer.explain(sample_decision, level=AudienceLevel.EXECUTIVE)

        # Should be brief (1-2 sentences)
        assert len(summary) < 200

        # Should mention verdict
        assert 'APPROVE' in summary

        # Should mention confidence
        assert '78%' in summary or '0.78' in summary

        # Should be complete sentences
        assert summary.endswith('.')

    def test_layperson_explanation(self, explainer, sample_decision):
        """Test layperson explanation generation."""
        explanation = explainer.explain(sample_decision, level=AudienceLevel.LAYPERSON)

        # Should be in plain language
        assert 'approved' in explanation.lower()

        # Should mention number of criteria
        assert '3' in explanation

        # Should not use technical jargon
        technical_terms = ['algorithm', 'heuristic', 'parameter']
        for term in technical_terms:
            assert term not in explanation.lower()

        # Should explain the process
        assert 'criteri' in explanation.lower() or 'evaluat' in explanation.lower()

    def test_technical_explanation(self, explainer, sample_decision):
        """Test technical explanation generation."""
        explanation = explainer.explain(sample_decision, level=AudienceLevel.TECHNICAL)

        # Should include technical details
        assert 'Decision ID' in explanation
        assert 'Confidence:' in explanation

        # Should include input data
        assert '720' in explanation  # credit score
        assert '75000' in explanation  # income

        # Should include critic details
        assert 'CreditScoreCritic' in explanation
        assert 'IncomeVerificationCritic' in explanation

        # Should show aggregation logic
        assert 'Aggregation' in explanation
        assert 'Weighted majority' in explanation or 'voting' in explanation.lower()

    def test_audit_trail(self, explainer, sample_decision):
        """Test audit trail generation."""
        audit = explainer.explain(sample_decision, level=AudienceLevel.AUDIT)

        # Should be valid JSON
        audit_data = json.loads(audit)

        # Should include all required fields
        assert 'decision_id' in audit_data
        assert 'timestamp' in audit_data
        assert 'input_data' in audit_data
        assert 'critic_evaluations' in audit_data
        assert 'aggregation' in audit_data
        assert 'audit_metadata' in audit_data

        # Should have all critics
        assert len(audit_data['critic_evaluations']) == 3

    def test_explain_all_levels(self, explainer, sample_decision):
        """Test generating all explanation levels at once."""
        all_levels = explainer.explain_all_levels(sample_decision)

        # Should return MultiLevelExplanation
        assert isinstance(all_levels, MultiLevelExplanation)

        # Should have all levels
        assert all_levels.executive_summary
        assert all_levels.layperson_explanation
        assert all_levels.technical_explanation
        assert all_levels.audit_trail

        # Executive should be shortest
        assert len(all_levels.executive_summary) < len(all_levels.layperson_explanation)
        assert len(all_levels.layperson_explanation) < len(all_levels.technical_explanation)

    def test_confidence_to_text(self, explainer):
        """Test confidence conversion to text."""
        assert explainer._confidence_to_text(0.95) == "very confident"
        assert explainer._confidence_to_text(0.80) == "confident"
        assert explainer._confidence_to_text(0.65) == "reasonably certain"
        assert explainer._confidence_to_text(0.55) == "moderately confident"
        assert explainer._confidence_to_text(0.40) == "somewhat uncertain"

    def test_humanize_critic_name(self, explainer):
        """Test critic name humanization."""
        assert explainer._humanize_critic_name('CreditScoreCritic') == 'Credit Score'
        assert explainer._humanize_critic_name('FraudDetectionCritic') == 'Fraud Detection'
        assert explainer._humanize_critic_name('income_verification_critic') == 'Income Verification Critic'

    def test_simplify_language(self, explainer):
        """Test technical language simplification."""
        technical = "The parameter exceeds the threshold by a statistically significant margin"
        simplified = explainer._simplify_language(technical)

        assert 'setting' in simplified  # parameter -> setting
        assert 'limit' in simplified     # threshold -> limit
        assert 'meaningful' in simplified  # statistically significant -> meaningful

    def test_no_technical_jargon_in_layperson(self, explainer, sample_decision):
        """Test that layperson explanations avoid technical jargon."""
        explanation = explainer.explain(sample_decision, level=AudienceLevel.LAYPERSON)

        # These technical terms should be simplified or avoided
        jargon = [
            'algorithm',
            'heuristic',
            'parameter',
            'threshold',
            'anomaly detection',
            'statistically'
        ]

        for term in jargon:
            assert term not in explanation.lower(), f"Found technical jargon: {term}"

    def test_complete_audit_trail(self, explainer, sample_decision):
        """Test that audit trail includes all decision components."""
        audit_data = explainer._generate_audit_trail_data(sample_decision)

        # Check all components present
        assert audit_data['decision_id'] == 'test_ml_001'
        assert len(audit_data['critic_evaluations']) == 3
        assert 'aggregation' in audit_data
        assert 'governance_outcome' in audit_data

        # Check audit metadata
        metadata = audit_data['audit_metadata']
        assert metadata['total_critics'] == 3
        assert 'consensus_reached' in metadata
        assert 'conflicts_detected' in metadata

    def test_consensus_detection(self, explainer, sample_decision):
        """Test consensus detection in decisions."""
        # Sample decision has no consensus (2 APPROVE, 1 DENY)
        assert explainer._check_consensus(sample_decision) is False

        # Create unanimous decision
        unanimous_decision = sample_decision.copy()
        unanimous_decision['critic_reports'] = [
            {'verdict': 'APPROVE', 'confidence': 0.9},
            {'verdict': 'APPROVE', 'confidence': 0.85},
            {'verdict': 'APPROVE', 'confidence': 0.88}
        ]
        assert explainer._check_consensus(unanimous_decision) is True

    def test_comparison_generation(self, explainer, sample_decision):
        """Test comparative explanation generation."""
        # Create second decision with different outcome
        decision2 = sample_decision.copy()
        decision2['decision_id'] = 'test_ml_002'
        decision2['governance_outcome'] = {
            'verdict': 'DENY',
            'confidence': 0.65
        }

        comparison = explainer.generate_comparison(
            sample_decision,
            decision2,
            level=AudienceLevel.LAYPERSON
        )

        # Should mention both decisions
        assert 'Request 1' in comparison
        assert 'Request 2' in comparison

        # Should mention different outcomes
        assert 'different' in comparison.lower()

    def test_executive_comparison(self, explainer, sample_decision):
        """Test executive-level comparison."""
        decision2 = sample_decision.copy()
        decision2['governance_outcome'] = {
            'verdict': 'DENY',
            'confidence': 0.65
        }

        comparison = explainer._generate_executive_comparison(sample_decision, decision2)

        # Should be brief
        assert len(comparison) < 200

        # Should mention both verdicts
        assert 'APPROVE' in comparison
        assert 'DENY' in comparison

    def test_metadata_extraction(self, explainer, sample_decision):
        """Test metadata extraction from decision."""
        metadata = explainer._extract_metadata(sample_decision)

        assert metadata['decision_id'] == 'test_ml_001'
        assert metadata['num_critics'] == 3
        assert metadata['final_verdict'] == 'APPROVE'
        assert metadata['final_confidence'] == 0.78
        assert metadata['consensus'] is False
        assert metadata['escalated'] is False

    def test_key_reason_extraction(self, explainer, sample_decision):
        """Test extraction of key reason for decision."""
        key_reason = explainer._extract_key_reason(sample_decision)

        # Should extract from most confident agreeing critic
        assert key_reason
        assert len(key_reason) <= 80  # Should be truncated

    def test_governance_explanation(self, explainer):
        """Test explanation when governance rules are applied."""
        decision_with_governance = {
            'decision_id': 'gov_001',
            'input_data': {},
            'critic_reports': [
                {
                    'critic_name': 'Critic1',
                    'verdict': 'APPROVE',
                    'confidence': 0.7,
                    'justification': 'Standard approval.'
                }
            ],
            'aggregation': {
                'verdict': 'APPROVE',
                'confidence': 0.7
            },
            'governance_outcome': {
                'verdict': 'DENY',  # Governance override
                'confidence': 0.8,
                'governance_applied': True,
                'rules_applied': ['high_risk_override']
            }
        }

        layperson_exp = explainer.explain(
            decision_with_governance,
            level=AudienceLevel.LAYPERSON
        )

        # Should mention policy/governance
        assert 'policy' in layperson_exp.lower() or 'rule' in layperson_exp.lower()

        technical_exp = explainer.explain(
            decision_with_governance,
            level=AudienceLevel.TECHNICAL
        )

        # Should include governance details
        assert 'Governance Applied: True' in technical_exp
        assert 'high_risk_override' in technical_exp

    def test_handles_empty_decision(self, explainer):
        """Test handling of empty/minimal decisions."""
        empty_decision = {
            'decision_id': 'empty_001',
            'input_data': {},
            'critic_reports': [],
            'aggregation': {},
            'governance_outcome': {}
        }

        # Should handle all levels without errors
        executive = explainer.explain(empty_decision, level=AudienceLevel.EXECUTIVE)
        assert executive  # Should return something

        layperson = explainer.explain(empty_decision, level=AudienceLevel.LAYPERSON)
        assert layperson

        technical = explainer.explain(empty_decision, level=AudienceLevel.TECHNICAL)
        assert technical

        audit = explainer.explain(empty_decision, level=AudienceLevel.AUDIT)
        audit_data = json.loads(audit)
        assert audit_data['decision_id'] == 'empty_001'

    def test_without_justifications(self, sample_decision):
        """Test explanation generation without critic justifications."""
        explainer_no_just = MultiLevelExplainer(include_justifications=False)

        explanation = explainer_no_just.explain(
            sample_decision,
            level=AudienceLevel.LAYPERSON
        )

        # Should still generate explanation
        assert explanation
        assert 'approved' in explanation.lower()

        # Justifications should not be included in detail
        # (basic structure might still mention evaluation)

    def test_developer_level_alias(self, explainer, sample_decision):
        """Test that DEVELOPER level works as alias for TECHNICAL."""
        developer_exp = explainer.explain(sample_decision, level=AudienceLevel.DEVELOPER)
        technical_exp = explainer.explain(sample_decision, level=AudienceLevel.TECHNICAL)

        # Should be similar (both technical explanations)
        assert 'Decision ID' in developer_exp
        assert 'Confidence:' in developer_exp


class TestExplanationQuality:
    """Test the quality and appropriateness of explanations."""

    def test_executive_brevity(self, explainer, sample_decision):
        """Test that executive summaries are brief."""
        summary = explainer.explain(sample_decision, level=AudienceLevel.EXECUTIVE)

        # Should be 1-2 sentences (< 200 chars typically)
        assert len(summary) < 250

        # Should have few sentences (count periods)
        sentence_count = summary.count('.')
        assert sentence_count <= 3

    def test_layperson_clarity(self, explainer, sample_decision):
        """Test that layperson explanations are clear."""
        explanation = explainer.explain(sample_decision, level=AudienceLevel.LAYPERSON)

        # Should use simple words
        simple_words = ['approved', 'criteria', 'evaluated', 'passed', 'review']
        word_count = sum(1 for word in simple_words if word in explanation.lower())
        assert word_count >= 2

        # Should avoid complex terms
        complex_terms = ['algorithm', 'heuristic', 'statistical', 'optimization']
        for term in complex_terms:
            assert term not in explanation.lower()

    def test_technical_completeness(self, explainer, sample_decision):
        """Test that technical explanations are complete."""
        explanation = explainer.explain(sample_decision, level=AudienceLevel.TECHNICAL)

        # Should include all critics
        for report in sample_decision['critic_reports']:
            assert report['critic_name'] in explanation

        # Should include numeric values
        assert '0.85' in explanation or '0.8500' in explanation  # confidence
        assert '720' in explanation  # credit score

        # Should include method details
        assert 'Aggregation' in explanation

    def test_audit_completeness(self, explainer, sample_decision):
        """Test that audit trails are complete."""
        audit = explainer.explain(sample_decision, level=AudienceLevel.AUDIT)
        audit_data = json.loads(audit)

        # Should be able to reconstruct decision from audit
        assert audit_data['input_data'] == sample_decision['input_data']
        assert len(audit_data['critic_evaluations']) == len(sample_decision['critic_reports'])

        # Should include metadata for auditing
        assert 'audit_metadata' in audit_data
        assert 'timestamp' in audit_data


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
