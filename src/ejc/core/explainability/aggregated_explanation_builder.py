"""
Aggregated Explanation Builder

Task 5.2: Aggregated Explanation Builder

Combines critic explanations into one structured narrative.
Merges reasoning from multiple critics, highlights consistencies
and inconsistencies, and supports long-form and short-form modes.

Features:
- Multi-critic explanation aggregation
- Consistency and conflict detection
- Unified narrative generation
- Long-form and short-form output modes
- Structured data export
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
from datetime import datetime

from .critic_explanation_formatter import CriticExplanation, ConfidenceLevel
from ...utils.logging import get_logger


logger = get_logger("ejc.explainability.aggregated_builder")


class AggregationMode(Enum):
    """Output mode for aggregated explanations"""
    LONG_FORM = "long_form"        # Detailed narrative with full analysis
    SHORT_FORM = "short_form"      # Concise summary
    STRUCTURED = "structured"      # Full structured data
    EXECUTIVE = "executive"        # Executive summary format


class ConsensusLevel(Enum):
    """Level of consensus among critics"""
    UNANIMOUS = "unanimous"              # All critics agree
    STRONG_MAJORITY = "strong_majority"  # 75%+ agreement
    MAJORITY = "majority"                # 50-75% agreement
    SPLIT = "split"                      # Even split
    NO_CONSENSUS = "no_consensus"        # No clear pattern


@dataclass
class VerdictAnalysis:
    """Analysis of verdicts across critics"""
    verdict: str
    count: int
    percentage: float
    critics: List[str] = field(default_factory=list)
    avg_confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class ConsistencyAnalysis:
    """Analysis of consistency/inconsistency between critics"""
    # Agreements
    agreeing_critics: List[Tuple[str, str]] = field(default_factory=list)
    common_reasons: List[str] = field(default_factory=list)
    consensus_level: ConsensusLevel = ConsensusLevel.NO_CONSENSUS

    # Disagreements
    disagreeing_critics: List[Tuple[str, str, str]] = field(default_factory=list)  # (critic1, critic2, reason)
    conflicting_verdicts: List[VerdictAnalysis] = field(default_factory=list)
    conflicting_reasons: List[str] = field(default_factory=list)

    # Metadata
    total_critics: int = 0
    unique_verdicts: int = 0


@dataclass
class AggregatedExplanation:
    """
    Aggregated explanation combining multiple critic outputs.

    Provides a unified view of all critic analyses with consistency
    detection and conflict highlighting.
    """
    # Overall assessment
    dominant_verdict: str
    overall_confidence: float
    consensus_level: ConsensusLevel

    # Critic breakdown
    total_critics: int
    verdict_breakdown: Dict[str, VerdictAnalysis]

    # Consistency analysis
    consistency: ConsistencyAnalysis

    # Merged reasoning
    primary_reasons: List[str] = field(default_factory=list)
    supporting_reasons: List[str] = field(default_factory=list)

    # Aggregated factors
    key_factors: Dict[str, Any] = field(default_factory=dict)
    all_warnings: List[str] = field(default_factory=list)
    all_limitations: List[str] = field(default_factory=list)

    # Individual explanations
    critic_explanations: List[CriticExplanation] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'dominant_verdict': self.dominant_verdict,
            'overall_confidence': self.overall_confidence,
            'consensus_level': self.consensus_level.value,
            'total_critics': self.total_critics,
            'verdict_breakdown': {
                verdict: {
                    'count': analysis.count,
                    'percentage': analysis.percentage,
                    'critics': analysis.critics,
                    'avg_confidence': analysis.avg_confidence,
                    'reasons': analysis.reasons
                }
                for verdict, analysis in self.verdict_breakdown.items()
            },
            'consistency': {
                'consensus_level': self.consistency.consensus_level.value,
                'agreeing_critics': self.consistency.agreeing_critics,
                'common_reasons': self.consistency.common_reasons,
                'disagreeing_critics': self.consistency.disagreeing_critics,
                'conflicting_verdicts': [
                    {
                        'verdict': v.verdict,
                        'count': v.count,
                        'percentage': v.percentage,
                        'critics': v.critics
                    }
                    for v in self.consistency.conflicting_verdicts
                ],
                'conflicting_reasons': self.consistency.conflicting_reasons
            },
            'primary_reasons': self.primary_reasons,
            'supporting_reasons': self.supporting_reasons,
            'key_factors': self.key_factors,
            'warnings': self.all_warnings,
            'limitations': self.all_limitations,
            'timestamp': self.timestamp.isoformat()
        }


class AggregatedExplanationBuilder:
    """
    Builds aggregated explanations from multiple critic outputs.

    Analyzes consistency, detects conflicts, and generates unified
    narratives that synthesize reasoning from all critics.
    """

    def __init__(
        self,
        default_mode: AggregationMode = AggregationMode.LONG_FORM,
        confidence_threshold: float = 0.7,
        majority_threshold: float = 0.5
    ):
        """
        Initialize aggregated explanation builder.

        Args:
            default_mode: Default output mode
            confidence_threshold: Threshold for high confidence
            majority_threshold: Threshold for majority consensus
        """
        self.default_mode = default_mode
        self.confidence_threshold = confidence_threshold
        self.majority_threshold = majority_threshold

    def build(
        self,
        explanations: List[CriticExplanation]
    ) -> AggregatedExplanation:
        """
        Build aggregated explanation from multiple critic explanations.

        Args:
            explanations: List of critic explanations to aggregate

        Returns:
            AggregatedExplanation object
        """
        if not explanations:
            raise ValueError("Cannot aggregate empty list of explanations")

        logger.info(f"Aggregating {len(explanations)} critic explanations")

        # Analyze verdicts
        verdict_breakdown = self._analyze_verdicts(explanations)
        dominant_verdict = self._determine_dominant_verdict(verdict_breakdown)

        # Analyze consistency
        consistency = self._analyze_consistency(explanations, verdict_breakdown)

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            explanations, verdict_breakdown, dominant_verdict
        )

        # Merge reasoning
        primary_reasons, supporting_reasons = self._merge_reasoning(
            explanations, dominant_verdict
        )

        # Aggregate factors
        key_factors = self._aggregate_factors(explanations)

        # Collect warnings and limitations
        all_warnings = self._collect_warnings(explanations)
        all_limitations = self._collect_limitations(explanations)

        # Build aggregated explanation
        aggregated = AggregatedExplanation(
            dominant_verdict=dominant_verdict,
            overall_confidence=overall_confidence,
            consensus_level=consistency.consensus_level,
            total_critics=len(explanations),
            verdict_breakdown=verdict_breakdown,
            consistency=consistency,
            primary_reasons=primary_reasons,
            supporting_reasons=supporting_reasons,
            key_factors=key_factors,
            all_warnings=all_warnings,
            all_limitations=all_limitations,
            critic_explanations=explanations,
            timestamp=datetime.utcnow()
        )

        logger.info(
            f"Aggregation complete: {dominant_verdict} "
            f"({consistency.consensus_level.value}, {overall_confidence:.2f} confidence)"
        )

        return aggregated

    def format_to_text(
        self,
        aggregated: AggregatedExplanation,
        mode: Optional[AggregationMode] = None
    ) -> str:
        """
        Format aggregated explanation as text.

        Args:
            aggregated: Aggregated explanation to format
            mode: Output mode (uses default if None)

        Returns:
            Formatted text
        """
        mode = mode or self.default_mode

        if mode == AggregationMode.LONG_FORM:
            return self._format_long_form(aggregated)
        elif mode == AggregationMode.SHORT_FORM:
            return self._format_short_form(aggregated)
        elif mode == AggregationMode.EXECUTIVE:
            return self._format_executive(aggregated)
        else:  # STRUCTURED
            import json
            return json.dumps(aggregated.to_dict(), indent=2)

    def _analyze_verdicts(
        self,
        explanations: List[CriticExplanation]
    ) -> Dict[str, VerdictAnalysis]:
        """Analyze verdict distribution across critics"""
        verdict_counts = Counter(exp.verdict for exp in explanations)
        verdict_critics = defaultdict(list)
        verdict_confidences = defaultdict(list)
        verdict_reasons = defaultdict(set)

        total = len(explanations)

        for exp in explanations:
            verdict_critics[exp.verdict].append(exp.critic_name)
            verdict_confidences[exp.verdict].append(exp.confidence)
            verdict_reasons[exp.verdict].add(exp.primary_reason)

        breakdown = {}
        for verdict, count in verdict_counts.items():
            breakdown[verdict] = VerdictAnalysis(
                verdict=verdict,
                count=count,
                percentage=count / total * 100,
                critics=verdict_critics[verdict],
                avg_confidence=sum(verdict_confidences[verdict]) / len(verdict_confidences[verdict]),
                reasons=list(verdict_reasons[verdict])
            )

        return breakdown

    def _determine_dominant_verdict(
        self,
        verdict_breakdown: Dict[str, VerdictAnalysis]
    ) -> str:
        """Determine the dominant verdict based on count and confidence"""
        if not verdict_breakdown:
            return "UNKNOWN"

        # Find verdict with highest count
        max_count = max(analysis.count for analysis in verdict_breakdown.values())
        top_verdicts = [
            verdict for verdict, analysis in verdict_breakdown.items()
            if analysis.count == max_count
        ]

        # If tie, use highest average confidence
        if len(top_verdicts) > 1:
            return max(
                top_verdicts,
                key=lambda v: verdict_breakdown[v].avg_confidence
            )

        return top_verdicts[0]

    def _analyze_consistency(
        self,
        explanations: List[CriticExplanation],
        verdict_breakdown: Dict[str, VerdictAnalysis]
    ) -> ConsistencyAnalysis:
        """Analyze consistency and conflicts between critics"""
        total_critics = len(explanations)
        unique_verdicts = len(verdict_breakdown)

        # Determine consensus level
        if unique_verdicts == 1:
            consensus_level = ConsensusLevel.UNANIMOUS
        else:
            max_percentage = max(
                analysis.percentage for analysis in verdict_breakdown.values()
            )
            if max_percentage >= 75:
                consensus_level = ConsensusLevel.STRONG_MAJORITY
            elif max_percentage == 50:
                consensus_level = ConsensusLevel.SPLIT
            elif max_percentage > 50:
                consensus_level = ConsensusLevel.MAJORITY
            else:
                consensus_level = ConsensusLevel.NO_CONSENSUS

        # Find agreeing critics (same verdict)
        agreeing_critics = []
        for verdict, analysis in verdict_breakdown.items():
            if analysis.count > 1:
                critics = analysis.critics
                for i in range(len(critics)):
                    for j in range(i + 1, len(critics)):
                        agreeing_critics.append((critics[i], critics[j]))

        # Find disagreeing critics (different verdicts)
        disagreeing_critics = []
        verdict_items = list(verdict_breakdown.items())
        for i in range(len(verdict_items)):
            for j in range(i + 1, len(verdict_items)):
                verdict1, analysis1 = verdict_items[i]
                verdict2, analysis2 = verdict_items[j]

                for critic1 in analysis1.critics:
                    for critic2 in analysis2.critics:
                        reason = f"{verdict1} vs {verdict2}"
                        disagreeing_critics.append((critic1, critic2, reason))

        # Find common reasons
        all_reasons = [exp.primary_reason for exp in explanations]
        reason_counts = Counter(all_reasons)
        common_reasons = [
            reason for reason, count in reason_counts.items()
            if count > 1
        ]

        # Find conflicting reasons
        conflicting_reasons = []
        if len(verdict_breakdown) > 1:
            # Reasons that support different verdicts are conflicting
            for verdict, analysis in verdict_breakdown.items():
                for reason in analysis.reasons:
                    if reason not in common_reasons:
                        conflicting_reasons.append(f"{verdict}: {reason}")

        return ConsistencyAnalysis(
            agreeing_critics=agreeing_critics,
            common_reasons=common_reasons,
            consensus_level=consensus_level,
            disagreeing_critics=disagreeing_critics,
            conflicting_verdicts=list(verdict_breakdown.values()),
            conflicting_reasons=conflicting_reasons,
            total_critics=total_critics,
            unique_verdicts=unique_verdicts
        )

    def _calculate_overall_confidence(
        self,
        explanations: List[CriticExplanation],
        verdict_breakdown: Dict[str, VerdictAnalysis],
        dominant_verdict: str
    ) -> float:
        """Calculate overall confidence in the aggregated decision"""
        if not explanations:
            return 0.0

        # Get critics who voted for dominant verdict
        dominant_analysis = verdict_breakdown.get(dominant_verdict)
        if not dominant_analysis:
            return 0.0

        # Weight by:
        # 1. Percentage of critics agreeing (consensus strength)
        # 2. Average confidence of agreeing critics
        consensus_weight = dominant_analysis.percentage / 100
        confidence_weight = dominant_analysis.avg_confidence

        # Combined metric
        overall = (consensus_weight * 0.6) + (confidence_weight * 0.4)

        return min(overall, 1.0)

    def _merge_reasoning(
        self,
        explanations: List[CriticExplanation],
        dominant_verdict: str
    ) -> Tuple[List[str], List[str]]:
        """Merge reasoning from all critics"""
        primary_reasons = []
        supporting_reasons = []

        # Collect reasons from critics with dominant verdict
        for exp in explanations:
            if exp.verdict == dominant_verdict:
                if exp.primary_reason not in primary_reasons:
                    primary_reasons.append(exp.primary_reason)

                for reason in exp.supporting_reasons:
                    if reason not in supporting_reasons:
                        supporting_reasons.append(reason)

        # Also note dissenting opinions
        dissenting = []
        for exp in explanations:
            if exp.verdict != dominant_verdict:
                dissenting.append(
                    f"{exp.critic_name} dissented with {exp.verdict}: {exp.primary_reason}"
                )

        if dissenting:
            supporting_reasons.extend(dissenting)

        return primary_reasons, supporting_reasons

    def _aggregate_factors(
        self,
        explanations: List[CriticExplanation]
    ) -> Dict[str, Any]:
        """Aggregate key factors from all critics"""
        aggregated = {}

        # Collect all factor keys
        all_keys = set()
        for exp in explanations:
            all_keys.update(exp.key_factors.keys())

        # Aggregate by key
        for key in all_keys:
            values = []
            for exp in explanations:
                if key in exp.key_factors:
                    values.append(exp.key_factors[key])

            # Aggregate based on type
            if all(isinstance(v, (int, float)) for v in values):
                # Numeric: use average
                aggregated[key] = sum(values) / len(values)
            elif all(isinstance(v, list) for v in values):
                # Lists: concatenate unique items
                all_items = []
                for v in values:
                    all_items.extend(v)
                aggregated[key] = list(set(all_items))
            else:
                # Other: use most common
                aggregated[key] = Counter(values).most_common(1)[0][0]

        return aggregated

    def _collect_warnings(
        self,
        explanations: List[CriticExplanation]
    ) -> List[str]:
        """Collect all unique warnings"""
        warnings = []
        seen = set()

        for exp in explanations:
            for warning in exp.warnings:
                if warning not in seen:
                    warnings.append(f"{exp.critic_name}: {warning}")
                    seen.add(warning)

        return warnings

    def _collect_limitations(
        self,
        explanations: List[CriticExplanation]
    ) -> List[str]:
        """Collect all unique limitations"""
        limitations = []
        seen = set()

        for exp in explanations:
            for limitation in exp.limitations:
                if limitation not in seen:
                    limitations.append(limitation)
                    seen.add(limitation)

        return limitations

    def _format_long_form(self, aggregated: AggregatedExplanation) -> str:
        """Format as detailed long-form narrative"""
        lines = []

        # Title
        lines.append("=" * 60)
        lines.append("AGGREGATED DECISION EXPLANATION")
        lines.append("=" * 60)
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"Dominant Verdict: {aggregated.dominant_verdict}")
        lines.append(f"Overall Confidence: {aggregated.overall_confidence:.2%}")
        lines.append(f"Consensus Level: {aggregated.consensus_level.value.replace('_', ' ').title()}")
        lines.append(f"Critics Analyzed: {aggregated.total_critics}")
        lines.append("")

        # Verdict Breakdown
        lines.append("## Verdict Breakdown")
        lines.append("")
        for verdict, analysis in sorted(
            aggregated.verdict_breakdown.items(),
            key=lambda x: x[1].count,
            reverse=True
        ):
            lines.append(f"**{verdict}**: {analysis.count}/{aggregated.total_critics} critics ({analysis.percentage:.1f}%)")
            lines.append(f"  Average Confidence: {analysis.avg_confidence:.2f}")
            lines.append(f"  Critics: {', '.join(analysis.critics)}")
            lines.append("")

        # Consistency Analysis
        lines.append("## Consistency Analysis")
        lines.append("")

        if aggregated.consistency.consensus_level == ConsensusLevel.UNANIMOUS:
            lines.append("✓ **Unanimous Agreement**: All critics agree on the verdict.")
        elif aggregated.consistency.common_reasons:
            lines.append(f"✓ **Common Reasoning** ({len(aggregated.consistency.common_reasons)} shared points):")
            for reason in aggregated.consistency.common_reasons:
                lines.append(f"  - {reason}")

        lines.append("")

        if aggregated.consistency.disagreeing_critics:
            lines.append(f"⚠ **Disagreements Detected** ({len(aggregated.consistency.disagreeing_critics)} pairs):")
            # Show up to 5 disagreements
            for critic1, critic2, reason in aggregated.consistency.disagreeing_critics[:5]:
                lines.append(f"  - {critic1} vs {critic2}: {reason}")
            if len(aggregated.consistency.disagreeing_critics) > 5:
                remaining = len(aggregated.consistency.disagreeing_critics) - 5
                lines.append(f"  ... and {remaining} more disagreements")

        lines.append("")

        # Primary Reasoning
        lines.append("## Primary Reasoning")
        lines.append("")
        for i, reason in enumerate(aggregated.primary_reasons, 1):
            lines.append(f"{i}. {reason}")
        lines.append("")

        # Supporting Analysis
        if aggregated.supporting_reasons:
            lines.append("## Supporting Analysis")
            lines.append("")
            for reason in aggregated.supporting_reasons:
                lines.append(f"  • {reason}")
            lines.append("")

        # Key Factors
        if aggregated.key_factors:
            lines.append("## Key Factors")
            lines.append("")
            for key, value in aggregated.key_factors.items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        # Warnings
        if aggregated.all_warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in aggregated.all_warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        # Limitations
        if aggregated.all_limitations:
            lines.append("## Limitations")
            lines.append("")
            for limitation in aggregated.all_limitations:
                lines.append(f"  ℹ {limitation}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def _format_short_form(self, aggregated: AggregatedExplanation) -> str:
        """Format as concise short-form summary"""
        lines = []

        # One-line summary
        consensus_desc = aggregated.consistency.consensus_level.value.replace('_', ' ')
        lines.append(
            f"**{aggregated.dominant_verdict}** "
            f"({aggregated.overall_confidence:.0%} confidence, "
            f"{consensus_desc}, "
            f"{aggregated.total_critics} critics)"
        )
        lines.append("")

        # Primary reason
        if aggregated.primary_reasons:
            lines.append(f"Primary: {aggregated.primary_reasons[0]}")

        # Show conflicts if any
        if len(aggregated.verdict_breakdown) > 1:
            others = [
                f"{v.count} {v.verdict}"
                for v in sorted(
                    aggregated.verdict_breakdown.values(),
                    key=lambda x: x.count,
                    reverse=True
                )[1:]
            ]
            lines.append(f"Dissent: {', '.join(others)}")

        return "\n".join(lines)

    def _format_executive(self, aggregated: AggregatedExplanation) -> str:
        """Format as executive summary"""
        lines = []

        lines.append("EXECUTIVE SUMMARY")
        lines.append("=" * 40)
        lines.append("")

        # Decision
        lines.append(f"Decision: {aggregated.dominant_verdict}")
        lines.append(f"Confidence: {aggregated.overall_confidence:.0%}")
        lines.append("")

        # Consensus
        consensus_map = {
            ConsensusLevel.UNANIMOUS: "All critics agree",
            ConsensusLevel.STRONG_MAJORITY: "Strong majority consensus",
            ConsensusLevel.MAJORITY: "Majority consensus",
            ConsensusLevel.SPLIT: "Critics are split",
            ConsensusLevel.NO_CONSENSUS: "No clear consensus"
        }
        lines.append(f"Consensus: {consensus_map.get(aggregated.consistency.consensus_level, 'Unknown')}")
        lines.append("")

        # Key Points
        lines.append("Key Points:")
        for i, reason in enumerate(aggregated.primary_reasons[:3], 1):
            lines.append(f"  {i}. {reason}")

        # Warnings (if critical)
        if aggregated.all_warnings:
            lines.append("")
            lines.append("Important Warnings:")
            for warning in aggregated.all_warnings[:3]:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)


def aggregate_explanations(
    explanations: List[CriticExplanation],
    mode: AggregationMode = AggregationMode.SHORT_FORM
) -> str:
    """
    Convenience function to aggregate and format explanations.

    Args:
        explanations: List of critic explanations
        mode: Output mode

    Returns:
        Formatted aggregated explanation
    """
    builder = AggregatedExplanationBuilder(default_mode=mode)
    aggregated = builder.build(explanations)
    return builder.format_to_text(aggregated, mode)
