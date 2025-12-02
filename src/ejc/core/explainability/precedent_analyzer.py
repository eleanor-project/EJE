"""
Comparative Precedent Analysis for EJE

Explains decisions in context of similar past cases using jurisprudence-style reasoning.
Retrieves similar precedents, highlights similarities/differences, and shows consistency.

Implements Issue #171: Build Comparative Precedent Analysis

References:
- Case-Based Reasoning (CBR) literature
- Legal AI precedent analysis systems
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class ComparisonType(Enum):
    """Types of precedent comparisons."""
    IDENTICAL = "identical"              # Essentially the same case
    SIMILAR_ALIGNED = "similar_aligned"  # Similar case, same outcome
    SIMILAR_DIVERGENT = "similar_divergent"  # Similar case, different outcome
    ANALOGOUS = "analogous"              # Analogous but distinct
    DISTINGUISHABLE = "distinguishable"  # Clearly different


@dataclass
class PrecedentComparison:
    """Comparison between current decision and a precedent."""
    precedent_id: str
    similarity_score: float
    comparison_type: ComparisonType
    similarities: List[str]
    differences: List[str]
    alignment_explanation: str
    precedent_verdict: str
    current_verdict: str
    precedent_data: Dict[str, Any] = field(default_factory=dict)


class PrecedentAnalyzer:
    """
    Analyzes decisions in context of similar precedents.

    Provides jurisprudence-style reasoning showing:
    - How current decision aligns with or differs from precedents
    - Key similarities and differences
    - Consistency analysis across precedents
    - Evolution of decisions over time
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize precedent analyzer.

        Args:
            similarity_threshold: Minimum similarity score to consider precedent relevant
        """
        self.similarity_threshold = similarity_threshold

    def analyze(
        self,
        decision: Dict[str, Any],
        precedents: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze decision in context of precedents.

        Args:
            decision: Current EJE decision
            precedents: List of precedent cases (or None to use decision's precedents)
            top_k: Number of top precedents to analyze

        Returns:
            Comprehensive precedent analysis
        """
        # Use precedents from decision if not provided
        if precedents is None:
            precedents = decision.get('precedents', [])

        # Filter and sort by similarity
        relevant_precedents = self._filter_relevant_precedents(precedents)[:top_k]

        if not relevant_precedents:
            return {
                'decision_id': decision.get('decision_id', 'unknown'),
                'has_precedents': False,
                'message': 'No relevant precedents found for comparison'
            }

        # Analyze each precedent
        comparisons = []
        for prec in relevant_precedents:
            comparison = self._compare_with_precedent(decision, prec)
            if comparison:
                comparisons.append(comparison)

        # Generate summary
        summary = self._generate_summary(decision, comparisons)

        # Detect patterns
        patterns = self._detect_patterns(comparisons)

        return {
            'decision_id': decision.get('decision_id', 'unknown'),
            'current_verdict': self._get_verdict(decision),
            'has_precedents': True,
            'num_precedents_analyzed': len(comparisons),
            'comparisons': [self._comparison_to_dict(c) for c in comparisons],
            'summary': summary,
            'patterns': patterns,
            'consistency_score': self._calculate_consistency(decision, comparisons)
        }

    def explain_alignment(
        self,
        decision: Dict[str, Any],
        precedent: Dict[str, Any]
    ) -> str:
        """
        Generate natural language explanation of how decision aligns with precedent.

        Format: "This case is like [precedent] but different because [reasons]"

        Args:
            decision: Current decision
            precedent: Precedent case

        Returns:
            Natural language explanation
        """
        comparison = self._compare_with_precedent(decision, precedent)

        if not comparison:
            return "Unable to generate comparison."

        # Build explanation
        explanation_parts = []

        # Similarity statement
        prec_id = precedent.get('id', 'a previous case')
        similarity_pct = int(comparison.similarity_score * 100)

        explanation_parts.append(
            f"This case is {similarity_pct}% similar to {prec_id}."
        )

        # Alignment or divergence
        if comparison.comparison_type in [ComparisonType.SIMILAR_ALIGNED, ComparisonType.IDENTICAL]:
            explanation_parts.append(
                f"\nBoth cases resulted in {comparison.current_verdict}, showing consistent decision-making."
            )
        elif comparison.comparison_type == ComparisonType.SIMILAR_DIVERGENT:
            explanation_parts.append(
                f"\nHowever, {prec_id} resulted in {comparison.precedent_verdict}, "
                f"while this case is {comparison.current_verdict}."
            )

        # Key similarities
        if comparison.similarities:
            explanation_parts.append(f"\n\nKey similarities:")
            for i, sim in enumerate(comparison.similarities[:3], 1):
                explanation_parts.append(f"\n{i}. {sim}")

        # Key differences (especially for divergent cases)
        if comparison.differences:
            explanation_parts.append(f"\n\nKey differences:")
            for i, diff in enumerate(comparison.differences[:3], 1):
                explanation_parts.append(f"\n{i}. {diff}")

        # Alignment explanation
        if comparison.alignment_explanation:
            explanation_parts.append(f"\n\n{comparison.alignment_explanation}")

        return ''.join(explanation_parts)

    def visualize_comparison(
        self,
        decision: Dict[str, Any],
        precedents: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate visualization data for precedent comparison.

        Args:
            decision: Current decision
            precedents: List of precedent cases
            top_k: Number of precedents to visualize

        Returns:
            Visualization data structure
        """
        analysis = self.analyze(decision, precedents, top_k)

        if not analysis['has_precedents']:
            return {'type': 'none', 'message': 'No precedents to visualize'}

        # Create comparison matrix visualization
        comparisons = analysis['comparisons']

        nodes = []
        edges = []

        # Central node: current decision
        current_verdict = analysis['current_verdict']
        nodes.append({
            'id': 'current',
            'label': 'Current Decision',
            'verdict': current_verdict,
            'type': 'current',
            'style': {'color': '#4A90E2', 'size': 'large'}
        })

        # Precedent nodes
        for i, comp in enumerate(comparisons):
            prec_id = comp['precedent_id']
            nodes.append({
                'id': prec_id,
                'label': f'Precedent {i+1}',
                'verdict': comp['precedent_verdict'],
                'similarity': comp['similarity_score'],
                'type': 'precedent',
                'style': {
                    'color': self._get_precedent_color(comp),
                    'size': 'medium'
                }
            })

            # Edge from current to precedent
            edges.append({
                'source': 'current',
                'target': prec_id,
                'similarity': comp['similarity_score'],
                'comparison_type': comp['comparison_type'],
                'label': f"{int(comp['similarity_score']*100)}% similar",
                'style': {
                    'thickness': comp['similarity_score'] * 5,
                    'color': self._get_edge_color(comp)
                }
            })

        return {
            'type': 'precedent_network',
            'nodes': nodes,
            'edges': edges,
            'layout': 'radial',  # Current decision in center, precedents around it
            'legend': {
                'node_colors': {
                    'current': 'Current decision',
                    'aligned': 'Aligned precedent (same verdict)',
                    'divergent': 'Divergent precedent (different verdict)'
                },
                'edge_thickness': 'Represents similarity score'
            }
        }

    def _filter_relevant_precedents(self, precedents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter precedents by relevance and sort by similarity."""
        relevant = [
            p for p in precedents
            if p.get('similarity', 0.0) >= self.similarity_threshold
        ]

        # Sort by similarity (descending)
        relevant.sort(key=lambda p: p.get('similarity', 0.0), reverse=True)

        return relevant

    def _compare_with_precedent(
        self,
        decision: Dict[str, Any],
        precedent: Dict[str, Any]
    ) -> Optional[PrecedentComparison]:
        """Compare current decision with a precedent case."""
        # Extract verdicts
        current_verdict = self._get_verdict(decision)
        precedent_verdict = precedent.get('outcome', 'UNKNOWN')

        # Get similarity score
        similarity_score = precedent.get('similarity', 0.0)

        # Determine comparison type
        comparison_type = self._determine_comparison_type(
            similarity_score,
            current_verdict,
            precedent_verdict
        )

        # Find similarities and differences
        similarities = self._find_similarities(decision, precedent)
        differences = self._find_differences(decision, precedent)

        # Generate alignment explanation
        alignment_explanation = self._generate_alignment_explanation(
            comparison_type,
            current_verdict,
            precedent_verdict,
            differences
        )

        return PrecedentComparison(
            precedent_id=precedent.get('id', 'unknown'),
            similarity_score=similarity_score,
            comparison_type=comparison_type,
            similarities=similarities,
            differences=differences,
            alignment_explanation=alignment_explanation,
            precedent_verdict=precedent_verdict,
            current_verdict=current_verdict,
            precedent_data=precedent
        )

    def _determine_comparison_type(
        self,
        similarity: float,
        current_verdict: str,
        precedent_verdict: str
    ) -> ComparisonType:
        """Determine the type of comparison between cases."""
        if similarity >= 0.95:
            return ComparisonType.IDENTICAL
        elif similarity >= 0.8:
            if current_verdict == precedent_verdict:
                return ComparisonType.SIMILAR_ALIGNED
            else:
                return ComparisonType.SIMILAR_DIVERGENT
        elif similarity >= 0.6:
            return ComparisonType.ANALOGOUS
        else:
            return ComparisonType.DISTINGUISHABLE

    def _find_similarities(
        self,
        decision: Dict[str, Any],
        precedent: Dict[str, Any]
    ) -> List[str]:
        """Identify key similarities between decision and precedent."""
        similarities = []

        # Compare input features
        current_input = decision.get('input_data', {})
        precedent_input = precedent.get('input_data', {})

        for key in current_input:
            if key in precedent_input:
                current_val = current_input[key]
                precedent_val = precedent_input[key]

                # Check if values are similar
                if self._values_similar(current_val, precedent_val):
                    similarities.append(
                        f"Similar {key}: {current_val} vs {precedent_val}"
                    )

        # Compare critic verdicts
        current_critics = {
            r.get('critic_name'): r.get('verdict')
            for r in decision.get('critic_reports', [])
        }
        precedent_critics = precedent.get('critic_verdicts', {})

        for critic_name, current_verdict in current_critics.items():
            if critic_name in precedent_critics:
                if current_verdict == precedent_critics[critic_name]:
                    similarities.append(
                        f"{critic_name} reached same verdict: {current_verdict}"
                    )

        return similarities[:5]  # Top 5 similarities

    def _find_differences(
        self,
        decision: Dict[str, Any],
        precedent: Dict[str, Any]
    ) -> List[str]:
        """Identify key differences between decision and precedent."""
        differences = []

        # Compare input features
        current_input = decision.get('input_data', {})
        precedent_input = precedent.get('input_data', {})

        for key in current_input:
            if key in precedent_input:
                current_val = current_input[key]
                precedent_val = precedent_input[key]

                # Check if values differ significantly
                if not self._values_similar(current_val, precedent_val):
                    differences.append(
                        f"Different {key}: {current_val} (current) vs {precedent_val} (precedent)"
                    )

        # Features unique to current decision
        unique_current = set(current_input.keys()) - set(precedent_input.keys())
        if unique_current:
            differences.append(
                f"Current case has additional factors: {', '.join(list(unique_current)[:3])}"
            )

        # Compare final verdicts if different
        current_verdict = self._get_verdict(decision)
        precedent_verdict = precedent.get('outcome', 'UNKNOWN')

        if current_verdict != precedent_verdict:
            differences.append(
                f"Different outcomes: {current_verdict} (current) vs {precedent_verdict} (precedent)"
            )

        return differences[:5]  # Top 5 differences

    def _values_similar(self, val1: Any, val2: Any) -> bool:
        """Check if two values are similar."""
        # Numeric comparison
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # Within 10% is considered similar
            if val2 == 0:
                return val1 == 0
            return abs(val1 - val2) / abs(val2) < 0.1

        # String comparison
        if isinstance(val1, str) and isinstance(val2, str):
            return val1.lower() == val2.lower()

        # Exact match for other types
        return val1 == val2

    def _generate_alignment_explanation(
        self,
        comparison_type: ComparisonType,
        current_verdict: str,
        precedent_verdict: str,
        differences: List[str]
    ) -> str:
        """Generate explanation of alignment or divergence."""
        if comparison_type == ComparisonType.IDENTICAL:
            return "This case is essentially identical to the precedent, justifying the same outcome."

        elif comparison_type == ComparisonType.SIMILAR_ALIGNED:
            return f"Despite minor differences, both cases appropriately result in {current_verdict}."

        elif comparison_type == ComparisonType.SIMILAR_DIVERGENT:
            if differences:
                key_diff = differences[0] if len(differences) > 0 else "case-specific factors"
                return f"While similar, the different outcome is justified by: {key_diff}"
            return "The different outcome reflects case-specific considerations."

        elif comparison_type == ComparisonType.ANALOGOUS:
            return "The cases share key characteristics but differ in important respects."

        else:
            return "The cases are sufficiently distinct to warrant separate analysis."

    def _generate_summary(
        self,
        decision: Dict[str, Any],
        comparisons: List[PrecedentComparison]
    ) -> str:
        """Generate summary of precedent analysis."""
        if not comparisons:
            return "No relevant precedents found for comparison."

        current_verdict = self._get_verdict(decision)

        # Count aligned vs divergent
        aligned = sum(1 for c in comparisons if c.current_verdict == c.precedent_verdict)
        divergent = len(comparisons) - aligned

        summary_parts = []

        summary_parts.append(
            f"Analyzed {len(comparisons)} similar precedent cases."
        )

        if aligned == len(comparisons):
            summary_parts.append(
                f"\nAll precedents align with the current {current_verdict} decision, demonstrating consistency."
            )
        elif aligned > divergent:
            summary_parts.append(
                f"\n{aligned} out of {len(comparisons)} precedents align with this decision, "
                f"showing general consistency."
            )
        else:
            summary_parts.append(
                f"\nPrecedents show mixed outcomes ({aligned} aligned, {divergent} divergent), "
                f"reflecting case-specific factors."
            )

        # Mention highest similarity
        highest_sim = max(comparisons, key=lambda c: c.similarity_score)
        summary_parts.append(
            f"\nMost similar case ({highest_sim.precedent_id}): "
            f"{int(highest_sim.similarity_score * 100)}% similarity, "
            f"outcome was {highest_sim.precedent_verdict}."
        )

        return ''.join(summary_parts)

    def _detect_patterns(self, comparisons: List[PrecedentComparison]) -> Dict[str, Any]:
        """Detect patterns across precedents."""
        if not comparisons:
            return {}

        # Pattern: Verdict consistency
        verdict_distribution = {}
        for comp in comparisons:
            verdict = comp.precedent_verdict
            verdict_distribution[verdict] = verdict_distribution.get(verdict, 0) + 1

        # Pattern: Similarity distribution
        avg_similarity = sum(c.similarity_score for c in comparisons) / len(comparisons)

        # Pattern: Alignment rate
        aligned_count = sum(
            1 for c in comparisons
            if c.current_verdict == c.precedent_verdict
        )
        alignment_rate = aligned_count / len(comparisons)

        return {
            'verdict_distribution': verdict_distribution,
            'average_similarity': avg_similarity,
            'alignment_rate': alignment_rate,
            'highly_similar_count': sum(1 for c in comparisons if c.similarity_score >= 0.8),
            'divergent_count': sum(
                1 for c in comparisons
                if c.comparison_type == ComparisonType.SIMILAR_DIVERGENT
            )
        }

    def _calculate_consistency(
        self,
        decision: Dict[str, Any],
        comparisons: List[PrecedentComparison]
    ) -> float:
        """Calculate consistency score with precedents."""
        if not comparisons:
            return 0.0

        # Weight by similarity and alignment
        total_weighted_score = 0.0
        total_weight = 0.0

        for comp in comparisons:
            weight = comp.similarity_score
            alignment = 1.0 if comp.current_verdict == comp.precedent_verdict else 0.0

            total_weighted_score += alignment * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return total_weighted_score / total_weight

    def _get_verdict(self, decision: Dict[str, Any]) -> str:
        """Extract verdict from decision."""
        governance = decision.get('governance_outcome', {})
        if governance and 'verdict' in governance:
            return governance['verdict']

        aggregation = decision.get('aggregation', {})
        if aggregation and 'verdict' in aggregation:
            return aggregation['verdict']

        return 'UNKNOWN'

    def _get_precedent_color(self, comparison: Dict[str, Any]) -> str:
        """Get color for precedent node based on alignment."""
        if comparison['current_verdict'] == comparison['precedent_verdict']:
            return '#2ECC71'  # Green for aligned
        else:
            return '#E74C3C'  # Red for divergent

    def _get_edge_color(self, comparison: Dict[str, Any]) -> str:
        """Get color for edge based on comparison type."""
        comp_type = comparison['comparison_type']

        if comp_type in ['identical', 'similar_aligned']:
            return '#2ECC71'  # Green
        elif comp_type == 'similar_divergent':
            return '#E74C3C'  # Red
        else:
            return '#95A5A6'  # Gray

    def _comparison_to_dict(self, comparison: PrecedentComparison) -> Dict[str, Any]:
        """Convert PrecedentComparison to dictionary."""
        return {
            'precedent_id': comparison.precedent_id,
            'similarity_score': comparison.similarity_score,
            'comparison_type': comparison.comparison_type.value,
            'similarities': comparison.similarities,
            'differences': comparison.differences,
            'alignment_explanation': comparison.alignment_explanation,
            'precedent_verdict': comparison.precedent_verdict,
            'current_verdict': comparison.current_verdict
        }


# Export
__all__ = ['PrecedentAnalyzer', 'ComparisonType', 'PrecedentComparison']
