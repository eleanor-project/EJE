"""
Multi-Critic Justification Synthesis Module

Aggregates individual critic justifications into unified explanations,
highlighting agreement, disagreement, and providing composite reasoning.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field


class AgreementGroup(BaseModel):
    """Group of critics that agree on a particular point"""
    critics: List[str]
    verdict: str
    common_reasoning: str
    average_confidence: float
    weight_sum: float


class DisagreementPoint(BaseModel):
    """Point of disagreement between critics"""
    topic: str
    positions: List[Dict[str, Any]]
    description: str


class SynthesizedJustification(BaseModel):
    """Synthesized explanation combining all critic justifications"""
    summary: str
    unanimous_points: List[str] = Field(default_factory=list)
    majority_view: Optional[str] = None
    minority_views: List[str] = Field(default_factory=list)
    disagreements: List[DisagreementPoint] = Field(default_factory=list)
    confidence_assessment: str
    key_considerations: List[str] = Field(default_factory=list)
    agreement_groups: List[AgreementGroup] = Field(default_factory=list)


class JustificationSynthesizer:
    """
    Synthesizes multiple critic justifications into a unified explanation.

    Provides:
    - Identification of agreement and disagreement
    - Composite justification highlighting key points
    - Confidence assessment across all critics
    - Structured output for explanations
    """

    def __init__(
        self,
        consensus_threshold: float = 0.7,
        min_confidence_for_strong_view: float = 0.8
    ):
        """
        Initialize the justification synthesizer.

        Args:
            consensus_threshold: Threshold for considering a view as majority (0-1)
            min_confidence_for_strong_view: Minimum confidence to highlight a view
        """
        self.consensus_threshold = consensus_threshold
        self.min_confidence_for_strong_view = min_confidence_for_strong_view

    def synthesize(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> SynthesizedJustification:
        """
        Synthesize justifications from multiple critics into a unified explanation.

        Args:
            critic_outputs: List of critic output dictionaries containing:
                - critic: name of the critic
                - verdict: the critic's verdict
                - confidence: confidence level (0-1)
                - justification: text explanation
                - weight: optional weight (default 1.0)

        Returns:
            SynthesizedJustification object with unified explanation
        """
        if not critic_outputs:
            return SynthesizedJustification(
                summary="No critic outputs available for synthesis",
                confidence_assessment="No confidence data"
            )

        # Group critics by verdict
        verdict_groups = self._group_by_verdict(critic_outputs)

        # Identify agreement groups
        agreement_groups = self._identify_agreement_groups(verdict_groups)

        # Extract unanimous points
        unanimous = self._extract_unanimous_points(critic_outputs)

        # Determine majority and minority views
        majority_view, minority_views = self._determine_majority_minority(
            verdict_groups, critic_outputs
        )

        # Identify disagreement points
        disagreements = self._identify_disagreements(critic_outputs, verdict_groups)

        # Extract key considerations from all critics
        key_considerations = self._extract_key_considerations(critic_outputs)

        # Assess overall confidence
        confidence_assessment = self._assess_confidence(critic_outputs)

        # Generate summary
        summary = self._generate_summary(
            critic_outputs, verdict_groups, agreement_groups, unanimous
        )

        return SynthesizedJustification(
            summary=summary,
            unanimous_points=unanimous,
            majority_view=majority_view,
            minority_views=minority_views,
            disagreements=disagreements,
            confidence_assessment=confidence_assessment,
            key_considerations=key_considerations,
            agreement_groups=agreement_groups
        )

    def _group_by_verdict(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group critics by their verdict"""
        groups = defaultdict(list)
        for output in critic_outputs:
            verdict = output.get('verdict', 'REVIEW')
            groups[verdict].append(output)
        return dict(groups)

    def _identify_agreement_groups(
        self,
        verdict_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[AgreementGroup]:
        """Identify groups of critics that agree"""
        agreement_groups = []

        for verdict, critics in verdict_groups.items():
            if len(critics) > 0:
                critic_names = [c.get('critic', 'unknown') for c in critics]
                confidences = [c.get('confidence', 0.0) for c in critics]
                weights = [c.get('weight', 1.0) for c in critics]

                # Extract common themes from justifications
                common_reasoning = self._extract_common_reasoning(critics)

                group = AgreementGroup(
                    critics=critic_names,
                    verdict=verdict,
                    common_reasoning=common_reasoning,
                    average_confidence=sum(confidences) / len(confidences),
                    weight_sum=sum(weights)
                )
                agreement_groups.append(group)

        return agreement_groups

    def _extract_common_reasoning(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> str:
        """Extract common reasoning themes from multiple critics"""
        justifications = [c.get('justification', '') for c in critic_outputs]

        if not justifications:
            return "No common reasoning identified"

        # Simple approach: take first justification as representative
        # In a more sophisticated version, use NLP to extract common themes
        if len(justifications) == 1:
            return justifications[0]

        # For multiple justifications, create a combined statement
        return f"{len(justifications)} critics agree, citing: {justifications[0][:100]}..."

    def _extract_unanimous_points(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract points where all critics agree"""
        if len(critic_outputs) < 2:
            return []

        # Check if all critics have the same verdict
        verdicts = set(c.get('verdict') for c in critic_outputs)
        if len(verdicts) == 1 and list(verdicts)[0] not in ['ERROR', 'REVIEW']:
            verdict = list(verdicts)[0]
            return [f"All {len(critic_outputs)} critics agree on verdict: {verdict}"]

        return []

    def _determine_majority_minority(
        self,
        verdict_groups: Dict[str, List[Dict[str, Any]]],
        all_outputs: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], List[str]]:
        """Determine majority and minority views"""
        if not verdict_groups:
            return None, []

        total_critics = len(all_outputs)

        # Calculate weighted support for each verdict
        verdict_support = {}
        for verdict, critics in verdict_groups.items():
            if verdict in ['ERROR', 'REVIEW']:
                continue

            weighted_support = sum(
                c.get('confidence', 0.0) * c.get('weight', 1.0)
                for c in critics
            )
            verdict_support[verdict] = {
                'count': len(critics),
                'weighted_support': weighted_support,
                'critics': critics
            }

        if not verdict_support:
            return None, []

        # Find majority
        max_verdict = max(verdict_support.items(), key=lambda x: x[1]['count'])
        max_count = max_verdict[1]['count']
        majority_threshold = total_critics * self.consensus_threshold

        majority_view = None
        if max_count >= majority_threshold:
            critics = max_verdict[1]['critics']
            avg_conf = sum(c.get('confidence', 0.0) for c in critics) / len(critics)
            majority_view = (
                f"{max_verdict[0]}: {max_count}/{total_critics} critics "
                f"(avg confidence: {avg_conf:.2f})"
            )

        # Identify minority views
        minority_views = []
        for verdict, data in verdict_support.items():
            if verdict != max_verdict[0] and data['count'] > 0:
                critics = data['critics']
                avg_conf = sum(c.get('confidence', 0.0) for c in critics) / len(critics)
                minority_view = (
                    f"{verdict}: {data['count']}/{total_critics} critics "
                    f"(avg confidence: {avg_conf:.2f})"
                )
                minority_views.append(minority_view)

        return majority_view, minority_views

    def _identify_disagreements(
        self,
        critic_outputs: List[Dict[str, Any]],
        verdict_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[DisagreementPoint]:
        """Identify and structure disagreement points"""
        disagreements = []

        # Check for verdict disagreements
        active_verdicts = [v for v in verdict_groups.keys() if v not in ['ERROR', 'REVIEW']]
        if len(active_verdicts) > 1:
            positions = []
            for verdict in active_verdicts:
                critics = verdict_groups[verdict]
                critic_names = [c.get('critic', 'unknown') for c in critics]
                avg_confidence = sum(c.get('confidence', 0.0) for c in critics) / len(critics)

                positions.append({
                    'verdict': verdict,
                    'critics': critic_names,
                    'count': len(critics),
                    'average_confidence': avg_confidence
                })

            disagreements.append(DisagreementPoint(
                topic="Primary Verdict",
                positions=positions,
                description=f"Critics disagree on primary verdict across {len(active_verdicts)} options"
            ))

        # Check for confidence level disagreements within same verdict
        for verdict, critics in verdict_groups.items():
            if len(critics) > 1:
                confidences = [c.get('confidence', 0.0) for c in critics]
                conf_variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)

                if conf_variance > 0.1:  # Significant variance
                    disagreements.append(DisagreementPoint(
                        topic=f"Confidence Levels for {verdict}",
                        positions=[{
                            'critic': c.get('critic'),
                            'confidence': c.get('confidence')
                        } for c in critics],
                        description=f"Critics voting {verdict} have divergent confidence levels (variance: {conf_variance:.3f})"
                    ))

        return disagreements

    def _extract_key_considerations(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key considerations from all critic justifications"""
        considerations = []

        # Group by verdict to extract key points
        for output in critic_outputs:
            critic = output.get('critic', 'unknown')
            verdict = output.get('verdict', 'REVIEW')
            justification = output.get('justification', '')
            confidence = output.get('confidence', 0.0)

            # Only include high-confidence considerations
            if confidence >= self.min_confidence_for_strong_view:
                consideration = f"{critic} ({verdict}, conf: {confidence:.2f}): {justification[:100]}"
                considerations.append(consideration)

        return considerations[:10]  # Limit to top 10 considerations

    def _assess_confidence(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> str:
        """Assess overall confidence across all critics"""
        confidences = [c.get('confidence', 0.0) for c in critic_outputs]

        if not confidences:
            return "No confidence data available"

        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        if len(confidences) > 1:
            variance = sum((c - avg_confidence)**2 for c in confidences) / len(confidences)
            consistency = "high" if variance < 0.1 else "moderate" if variance < 0.3 else "low"
        else:
            consistency = "N/A (single critic)"

        if avg_confidence > 0.8:
            level = "very high"
        elif avg_confidence > 0.6:
            level = "high"
        elif avg_confidence > 0.4:
            level = "moderate"
        else:
            level = "low"

        return (
            f"Overall confidence: {level} (avg: {avg_confidence:.2f}, "
            f"range: {min_confidence:.2f}-{max_confidence:.2f}, "
            f"consistency: {consistency})"
        )

    def _generate_summary(
        self,
        critic_outputs: List[Dict[str, Any]],
        verdict_groups: Dict[str, List[Dict[str, Any]]],
        agreement_groups: List[AgreementGroup],
        unanimous_points: List[str]
    ) -> str:
        """Generate a comprehensive summary of all justifications"""
        num_critics = len(critic_outputs)

        if unanimous_points:
            return f"All {num_critics} critics unanimously agree. " + unanimous_points[0]

        # Check if there's a clear majority
        active_groups = [g for g in agreement_groups if g.verdict not in ['ERROR', 'REVIEW']]

        if not active_groups:
            return f"{num_critics} critics provided feedback, but no clear consensus emerged."

        # Sort by weight and critic count
        active_groups.sort(key=lambda g: (g.weight_sum, len(g.critics)), reverse=True)
        top_group = active_groups[0]

        if len(active_groups) == 1:
            return (
                f"{len(top_group.critics)} critic(s) recommend {top_group.verdict}. "
                f"{top_group.common_reasoning}"
            )

        # Multiple groups - show split
        summary_parts = []
        for group in active_groups[:3]:  # Top 3 groups
            summary_parts.append(
                f"{len(group.critics)} critic(s) vote {group.verdict}"
            )

        return (
            f"Critics are split: {', '.join(summary_parts)}. "
            f"Primary reasoning from {top_group.verdict} position: {top_group.common_reasoning[:150]}"
        )


# Convenience functions
def synthesize_justifications(
    critic_outputs: List[Dict[str, Any]]
) -> SynthesizedJustification:
    """
    Convenience function to synthesize justifications with default settings.

    Args:
        critic_outputs: List of critic output dictionaries

    Returns:
        SynthesizedJustification object
    """
    synthesizer = JustificationSynthesizer()
    return synthesizer.synthesize(critic_outputs)


def get_unified_explanation(
    critic_outputs: List[Dict[str, Any]]
) -> str:
    """
    Get a simple unified explanation string.

    Args:
        critic_outputs: List of critic output dictionaries

    Returns:
        String summary of synthesized justifications
    """
    synthesized = synthesize_justifications(critic_outputs)
    return synthesized.summary


def has_consensus(
    critic_outputs: List[Dict[str, Any]],
    threshold: float = 0.7
) -> bool:
    """
    Check if critics have reached consensus.

    Args:
        critic_outputs: List of critic output dictionaries
        threshold: Consensus threshold (0-1)

    Returns:
        True if consensus reached, False otherwise
    """
    synthesizer = JustificationSynthesizer(consensus_threshold=threshold)
    synthesized = synthesizer.synthesize(critic_outputs)
    return len(synthesized.unanimous_points) > 0 or synthesized.majority_view is not None
