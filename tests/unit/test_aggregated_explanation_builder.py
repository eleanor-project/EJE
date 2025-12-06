"""
Unit tests for Aggregated Explanation Builder

Task 5.2: Aggregated Explanation Builder
Tests for combining critic explanations into structured narratives.
"""

import pytest
from datetime import datetime
from typing import List

from ejc.core.explainability.critic_explanation_formatter import (
    CriticExplanation,
    ConfidenceLevel
)
from ejc.core.explainability.aggregated_explanation_builder import (
    AggregatedExplanationBuilder,
    AggregationMode,
    ConsensusLevel,
    VerdictAnalysis,
    ConsistencyAnalysis,
    AggregatedExplanation,
    aggregate_explanations
)


class TestVerdictAnalysis:
    """Tests for VerdictAnalysis dataclass"""

    def test_verdict_analysis_creation(self):
        """Test creating a VerdictAnalysis"""
        analysis = VerdictAnalysis(
            verdict="ALLOW",
            count=3,
            percentage=75.0,
            critics=["Critic1", "Critic2", "Critic3"],
            avg_confidence=0.85,
            reasons=["Safe transaction", "No violations detected"]
        )

        assert analysis.verdict == "ALLOW"
        assert analysis.count == 3
        assert analysis.percentage == 75.0
        assert len(analysis.critics) == 3
        assert analysis.avg_confidence == 0.85
        assert len(analysis.reasons) == 2


class TestConsistencyAnalysis:
    """Tests for ConsistencyAnalysis dataclass"""

    def test_consistency_analysis_creation(self):
        """Test creating a ConsistencyAnalysis"""
        analysis = ConsistencyAnalysis(
            agreeing_critics=[("Critic1", "Critic2")],
            common_reasons=["Shared reason"],
            consensus_level=ConsensusLevel.UNANIMOUS,
            disagreeing_critics=[],
            conflicting_verdicts=[],
            conflicting_reasons=[],
            total_critics=2,
            unique_verdicts=1
        )

        assert analysis.consensus_level == ConsensusLevel.UNANIMOUS
        assert len(analysis.agreeing_critics) == 1
        assert analysis.total_critics == 2


class TestAggregatedExplanation:
    """Tests for AggregatedExplanation dataclass"""

    def test_aggregated_explanation_creation(self):
        """Test creating an AggregatedExplanation"""
        explanation = AggregatedExplanation(
            dominant_verdict="ALLOW",
            overall_confidence=0.85,
            consensus_level=ConsensusLevel.UNANIMOUS,
            total_critics=3,
            verdict_breakdown={},
            consistency=ConsistencyAnalysis()
        )

        assert explanation.dominant_verdict == "ALLOW"
        assert explanation.overall_confidence == 0.85
        assert explanation.consensus_level == ConsensusLevel.UNANIMOUS

    def test_to_dict(self):
        """Test converting to dictionary"""
        verdict_analysis = VerdictAnalysis(
            verdict="ALLOW",
            count=2,
            percentage=100.0,
            critics=["Critic1", "Critic2"],
            avg_confidence=0.9
        )

        explanation = AggregatedExplanation(
            dominant_verdict="ALLOW",
            overall_confidence=0.85,
            consensus_level=ConsensusLevel.UNANIMOUS,
            total_critics=2,
            verdict_breakdown={"ALLOW": verdict_analysis},
            consistency=ConsistencyAnalysis(consensus_level=ConsensusLevel.UNANIMOUS)
        )

        result = explanation.to_dict()

        assert result['dominant_verdict'] == "ALLOW"
        assert result['overall_confidence'] == 0.85
        assert result['consensus_level'] == 'unanimous'
        assert result['total_critics'] == 2
        assert 'ALLOW' in result['verdict_breakdown']


class TestAggregatedExplanationBuilder:
    """Tests for AggregatedExplanationBuilder"""

    @pytest.fixture
    def builder(self):
        """Create a builder instance"""
        return AggregatedExplanationBuilder()

    @pytest.fixture
    def sample_explanations_unanimous(self) -> List[CriticExplanation]:
        """Create sample explanations with unanimous agreement"""
        return [
            CriticExplanation(
                critic_name="BiasDetector",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="No bias detected in transaction.",
                supporting_reasons=["Fair distribution", "Equal treatment"],
                key_factors={"bias_score": 0.1, "fairness": 0.95}
            ),
            CriticExplanation(
                critic_name="PrivacyGuard",
                verdict="ALLOW",
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Privacy requirements met.",
                supporting_reasons=["Proper anonymization", "Consent obtained"],
                key_factors={"privacy_score": 0.9, "data_sensitivity": "low"}
            ),
            CriticExplanation(
                critic_name="ComplianceChecker",
                verdict="ALLOW",
                confidence=0.88,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Compliant with all regulations.",
                supporting_reasons=["GDPR compliant", "Local laws satisfied"],
                key_factors={"compliance_score": 0.92}
            )
        ]

    @pytest.fixture
    def sample_explanations_split(self) -> List[CriticExplanation]:
        """Create sample explanations with split verdict"""
        return [
            CriticExplanation(
                critic_name="BiasDetector",
                verdict="ALLOW",
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Low bias detected.",
                key_factors={"bias_score": 0.2}
            ),
            CriticExplanation(
                critic_name="PrivacyGuard",
                verdict="DENY",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Privacy violation detected.",
                key_factors={"privacy_score": 0.3}
            ),
            CriticExplanation(
                critic_name="ComplianceChecker",
                verdict="ALLOW",
                confidence=0.75,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Regulation compliant.",
                key_factors={"compliance_score": 0.85}
            ),
            CriticExplanation(
                critic_name="SecurityScanner",
                verdict="DENY",
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Security risk identified.",
                key_factors={"security_score": 0.4}
            )
        ]

    def test_build_with_empty_list(self, builder):
        """Test that building with empty list raises error"""
        with pytest.raises(ValueError, match="Cannot aggregate empty list"):
            builder.build([])

    def test_build_unanimous_agreement(self, builder, sample_explanations_unanimous):
        """Test building aggregation with unanimous agreement"""
        result = builder.build(sample_explanations_unanimous)

        assert result.dominant_verdict == "ALLOW"
        assert result.consensus_level == ConsensusLevel.UNANIMOUS
        assert result.total_critics == 3
        assert len(result.verdict_breakdown) == 1
        assert result.overall_confidence > 0.8

    def test_build_split_verdict(self, builder, sample_explanations_split):
        """Test building aggregation with split verdict"""
        result = builder.build(sample_explanations_split)

        assert result.total_critics == 4
        assert len(result.verdict_breakdown) == 2
        assert result.consensus_level in [
            ConsensusLevel.SPLIT,
            ConsensusLevel.MAJORITY,
            ConsensusLevel.NO_CONSENSUS
        ]

        # Check both verdicts are represented
        assert "ALLOW" in result.verdict_breakdown
        assert "DENY" in result.verdict_breakdown

    def test_verdict_analysis(self, builder, sample_explanations_unanimous):
        """Test verdict analysis"""
        verdict_breakdown = builder._analyze_verdicts(sample_explanations_unanimous)

        assert len(verdict_breakdown) == 1
        assert "ALLOW" in verdict_breakdown

        allow_analysis = verdict_breakdown["ALLOW"]
        assert allow_analysis.count == 3
        assert allow_analysis.percentage == 100.0
        assert len(allow_analysis.critics) == 3
        assert 0.85 <= allow_analysis.avg_confidence <= 0.9

    def test_determine_dominant_verdict_simple(self, builder):
        """Test determining dominant verdict with clear majority"""
        verdict_breakdown = {
            "ALLOW": VerdictAnalysis(
                verdict="ALLOW",
                count=3,
                percentage=75.0,
                avg_confidence=0.8
            ),
            "DENY": VerdictAnalysis(
                verdict="DENY",
                count=1,
                percentage=25.0,
                avg_confidence=0.9
            )
        }

        dominant = builder._determine_dominant_verdict(verdict_breakdown)
        assert dominant == "ALLOW"

    def test_determine_dominant_verdict_tie_uses_confidence(self, builder):
        """Test that ties are broken by confidence"""
        verdict_breakdown = {
            "ALLOW": VerdictAnalysis(
                verdict="ALLOW",
                count=2,
                percentage=50.0,
                avg_confidence=0.7
            ),
            "DENY": VerdictAnalysis(
                verdict="DENY",
                count=2,
                percentage=50.0,
                avg_confidence=0.9
            )
        }

        dominant = builder._determine_dominant_verdict(verdict_breakdown)
        assert dominant == "DENY"  # Higher confidence

    def test_consistency_analysis_unanimous(self, builder, sample_explanations_unanimous):
        """Test consistency analysis with unanimous agreement"""
        verdict_breakdown = builder._analyze_verdicts(sample_explanations_unanimous)
        consistency = builder._analyze_consistency(
            sample_explanations_unanimous,
            verdict_breakdown
        )

        assert consistency.consensus_level == ConsensusLevel.UNANIMOUS
        assert consistency.total_critics == 3
        assert consistency.unique_verdicts == 1
        assert len(consistency.agreeing_critics) > 0
        assert len(consistency.disagreeing_critics) == 0

    def test_consistency_analysis_split(self, builder, sample_explanations_split):
        """Test consistency analysis with split verdict"""
        verdict_breakdown = builder._analyze_verdicts(sample_explanations_split)
        consistency = builder._analyze_consistency(
            sample_explanations_split,
            verdict_breakdown
        )

        assert consistency.total_critics == 4
        assert consistency.unique_verdicts == 2
        assert len(consistency.disagreeing_critics) > 0

    def test_overall_confidence_calculation(self, builder, sample_explanations_unanimous):
        """Test overall confidence calculation"""
        verdict_breakdown = builder._analyze_verdicts(sample_explanations_unanimous)
        confidence = builder._calculate_overall_confidence(
            sample_explanations_unanimous,
            verdict_breakdown,
            "ALLOW"
        )

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # High confidence for unanimous agreement

    def test_merge_reasoning(self, builder, sample_explanations_unanimous):
        """Test merging reasoning from multiple critics"""
        primary, supporting = builder._merge_reasoning(
            sample_explanations_unanimous,
            "ALLOW"
        )

        assert len(primary) == 3  # One from each critic
        assert all("." in reason for reason in primary)  # Proper formatting
        assert len(supporting) > 0

    def test_merge_reasoning_with_dissent(self, builder, sample_explanations_split):
        """Test merging reasoning includes dissenting opinions"""
        primary, supporting = builder._merge_reasoning(
            sample_explanations_split,
            "ALLOW"  # Dominant verdict
        )

        # Should have primary reasons from ALLOW critics
        assert len(primary) > 0

        # Should include dissenting opinions in supporting
        dissenting_found = any("dissented" in reason for reason in supporting)
        assert dissenting_found

    def test_aggregate_factors(self, builder, sample_explanations_unanimous):
        """Test aggregating key factors"""
        factors = builder._aggregate_factors(sample_explanations_unanimous)

        # Should have aggregated scores
        assert "bias_score" in factors or "privacy_score" in factors

    def test_collect_warnings(self, builder):
        """Test collecting warnings from multiple critics"""
        explanations = [
            CriticExplanation(
                critic_name="Critic1",
                verdict="ALLOW",
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Test",
                warnings=["Warning 1", "Warning 2"]
            ),
            CriticExplanation(
                critic_name="Critic2",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Test",
                warnings=["Warning 2", "Warning 3"]
            )
        ]

        warnings = builder._collect_warnings(explanations)

        # Should have unique warnings with critic names
        assert len(warnings) == 3
        assert any("Critic1" in w for w in warnings)

    def test_collect_limitations(self, builder):
        """Test collecting limitations"""
        explanations = [
            CriticExplanation(
                critic_name="Critic1",
                verdict="ALLOW",
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Test",
                limitations=["Limited data", "Incomplete analysis"]
            ),
            CriticExplanation(
                critic_name="Critic2",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Test",
                limitations=["Incomplete analysis"]
            )
        ]

        limitations = builder._collect_limitations(explanations)

        # Should have unique limitations
        assert "Limited data" in limitations
        assert "Incomplete analysis" in limitations

    def test_format_long_form(self, builder, sample_explanations_unanimous):
        """Test long-form formatting"""
        aggregated = builder.build(sample_explanations_unanimous)
        text = builder.format_to_text(aggregated, AggregationMode.LONG_FORM)

        assert "AGGREGATED DECISION EXPLANATION" in text
        assert "Executive Summary" in text
        assert "Verdict Breakdown" in text
        assert "Consistency Analysis" in text
        assert "Primary Reasoning" in text
        assert aggregated.dominant_verdict in text

    def test_format_short_form(self, builder, sample_explanations_unanimous):
        """Test short-form formatting"""
        aggregated = builder.build(sample_explanations_unanimous)
        text = builder.format_to_text(aggregated, AggregationMode.SHORT_FORM)

        # Should be concise
        assert len(text) < 500
        assert aggregated.dominant_verdict in text
        assert "%" in text  # Should show confidence percentage

    def test_format_executive(self, builder, sample_explanations_unanimous):
        """Test executive summary formatting"""
        aggregated = builder.build(sample_explanations_unanimous)
        text = builder.format_to_text(aggregated, AggregationMode.EXECUTIVE)

        assert "EXECUTIVE SUMMARY" in text
        assert "Decision:" in text
        assert "Confidence:" in text
        assert "Consensus:" in text
        assert "Key Points:" in text

    def test_format_structured(self, builder, sample_explanations_unanimous):
        """Test structured (JSON) formatting"""
        import json

        aggregated = builder.build(sample_explanations_unanimous)
        text = builder.format_to_text(aggregated, AggregationMode.STRUCTURED)

        # Should be valid JSON
        data = json.loads(text)
        assert data['dominant_verdict'] == "ALLOW"
        assert 'overall_confidence' in data
        assert 'verdict_breakdown' in data

    def test_consensus_level_classification(self, builder):
        """Test consensus level classification logic"""
        # Unanimous
        explanations_unanimous = [
            CriticExplanation(
                critic_name=f"Critic{i}",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Test"
            )
            for i in range(4)
        ]
        result = builder.build(explanations_unanimous)
        assert result.consistency.consensus_level == ConsensusLevel.UNANIMOUS

        # Strong majority (75%+)
        explanations_strong = [
            CriticExplanation(
                critic_name=f"Critic{i}",
                verdict="ALLOW" if i < 3 else "DENY",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Test"
            )
            for i in range(4)
        ]
        result = builder.build(explanations_strong)
        assert result.consistency.consensus_level == ConsensusLevel.STRONG_MAJORITY

        # Split (50-50)
        explanations_split = [
            CriticExplanation(
                critic_name=f"Critic{i}",
                verdict="ALLOW" if i < 2 else "DENY",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Test"
            )
            for i in range(4)
        ]
        result = builder.build(explanations_split)
        assert result.consistency.consensus_level == ConsensusLevel.SPLIT

    def test_default_mode(self):
        """Test that default mode is used"""
        builder = AggregatedExplanationBuilder(default_mode=AggregationMode.SHORT_FORM)
        assert builder.default_mode == AggregationMode.SHORT_FORM

    def test_confidence_threshold(self):
        """Test confidence threshold parameter"""
        builder = AggregatedExplanationBuilder(confidence_threshold=0.8)
        assert builder.confidence_threshold == 0.8

    def test_with_single_critic(self, builder):
        """Test aggregation with just one critic"""
        single_explanation = [
            CriticExplanation(
                critic_name="SingleCritic",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Single reason"
            )
        ]

        result = builder.build(single_explanation)

        assert result.dominant_verdict == "ALLOW"
        assert result.total_critics == 1
        assert result.consensus_level == ConsensusLevel.UNANIMOUS

    def test_with_many_critics(self, builder):
        """Test aggregation with many critics"""
        many_explanations = [
            CriticExplanation(
                critic_name=f"Critic{i}",
                verdict="ALLOW" if i % 3 != 0 else "DENY",
                confidence=0.7 + (i % 3) * 0.1,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason=f"Reason {i}"
            )
            for i in range(10)
        ]

        result = builder.build(many_explanations)

        assert result.total_critics == 10
        assert len(result.verdict_breakdown) == 2  # ALLOW and DENY


class TestConvenienceFunction:
    """Tests for convenience function"""

    def test_aggregate_explanations_function(self):
        """Test the aggregate_explanations convenience function"""
        explanations = [
            CriticExplanation(
                critic_name="Critic1",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Safe"
            ),
            CriticExplanation(
                critic_name="Critic2",
                verdict="ALLOW",
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Compliant"
            )
        ]

        result = aggregate_explanations(explanations, AggregationMode.SHORT_FORM)

        assert isinstance(result, str)
        assert "ALLOW" in result

    def test_aggregate_explanations_default_mode(self):
        """Test that default mode is short form"""
        explanations = [
            CriticExplanation(
                critic_name="Critic1",
                verdict="ALLOW",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Safe"
            )
        ]

        result = aggregate_explanations(explanations)

        # Should be concise (short form default)
        assert isinstance(result, str)
        assert len(result) < 500


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_mixed_confidence_levels(self):
        """Test handling critics with very different confidence levels"""
        builder = AggregatedExplanationBuilder()

        explanations = [
            CriticExplanation(
                critic_name="HighConfidence",
                verdict="ALLOW",
                confidence=0.95,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Very confident"
            ),
            CriticExplanation(
                critic_name="LowConfidence",
                verdict="ALLOW",
                confidence=0.4,
                confidence_level=ConfidenceLevel.LOW,
                primary_reason="Not very confident"
            )
        ]

        result = builder.build(explanations)
        assert result.dominant_verdict == "ALLOW"
        assert 0.4 < result.overall_confidence < 0.95

    def test_empty_reasons(self):
        """Test handling critics with empty reasons"""
        builder = AggregatedExplanationBuilder()

        explanations = [
            CriticExplanation(
                critic_name="EmptyReason",
                verdict="ALLOW",
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason=""
            )
        ]

        result = builder.build(explanations)
        assert result.dominant_verdict == "ALLOW"

    def test_three_way_split(self):
        """Test handling three different verdicts"""
        builder = AggregatedExplanationBuilder()

        explanations = [
            CriticExplanation(
                critic_name="Critic1",
                verdict="ALLOW",
                confidence=0.8,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Allow"
            ),
            CriticExplanation(
                critic_name="Critic2",
                verdict="DENY",
                confidence=0.85,
                confidence_level=ConfidenceLevel.HIGH,
                primary_reason="Deny"
            ),
            CriticExplanation(
                critic_name="Critic3",
                verdict="ESCALATE",
                confidence=0.9,
                confidence_level=ConfidenceLevel.VERY_HIGH,
                primary_reason="Escalate"
            )
        ]

        result = builder.build(explanations)
        assert len(result.verdict_breakdown) == 3
        assert result.consensus_level == ConsensusLevel.NO_CONSENSUS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
