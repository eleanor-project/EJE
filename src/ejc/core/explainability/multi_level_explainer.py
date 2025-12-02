"""
Multi-Level Explanation System for EJE

Creates tiered explanations for different audience technical levels:
- Executive: High-level summary (1-2 sentences)
- Layperson: Plain language explanation
- Technical: Detailed technical information
- Audit: Complete decision record

Implements Issue #170: Multi-Level Explanation System

References:
- World Bank AI Governance Report (Section 5.1): Multi-level explainability
- Miller (2019): "Explanation in Artificial Intelligence: Insights from the Social Sciences"
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import json


class AudienceLevel(Enum):
    """Explanation audience levels."""
    EXECUTIVE = "executive"           # C-suite, board members
    LAYPERSON = "layperson"          # End users, general public
    TECHNICAL = "technical"          # Developers, data scientists
    AUDIT = "audit"                  # Auditors, compliance officers
    DEVELOPER = "developer"          # Same as technical (alias)


@dataclass
class MultiLevelExplanation:
    """Complete multi-level explanation for a decision."""
    decision_id: str
    executive_summary: str
    layperson_explanation: str
    technical_explanation: str
    audit_trail: Dict[str, Any]
    metadata: Dict[str, Any]


class MultiLevelExplainer:
    """
    Generates explanations at multiple technical levels for different audiences.

    Adapts language, detail level, and content based on audience:
    - Executive: Verdict + confidence + key reason
    - Layperson: Why this decision? What factors mattered?
    - Technical: Algorithm details, parameters, critic logic
    - Audit: Complete traceable record with all data
    """

    def __init__(self, include_justifications: bool = True):
        """
        Initialize multi-level explainer.

        Args:
            include_justifications: Include critic justifications in explanations
        """
        self.include_justifications = include_justifications

    def explain(
        self,
        decision: Dict[str, Any],
        level: AudienceLevel = AudienceLevel.LAYPERSON,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate explanation at specified audience level.

        Args:
            decision: EJE Decision object (as dict)
            level: Audience level for explanation
            context: Additional context for explanation generation

        Returns:
            Explanation text appropriate for audience level
        """
        if level == AudienceLevel.EXECUTIVE:
            return self._generate_executive_summary(decision, context)
        elif level == AudienceLevel.LAYPERSON:
            return self._generate_layperson_explanation(decision, context)
        elif level in [AudienceLevel.TECHNICAL, AudienceLevel.DEVELOPER]:
            return self._generate_technical_explanation(decision, context)
        elif level == AudienceLevel.AUDIT:
            return self._generate_audit_trail(decision, context)
        else:
            return self._generate_layperson_explanation(decision, context)

    def explain_all_levels(
        self,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MultiLevelExplanation:
        """
        Generate explanations at all audience levels.

        Args:
            decision: EJE Decision object (as dict)
            context: Additional context

        Returns:
            MultiLevelExplanation with all explanation levels
        """
        return MultiLevelExplanation(
            decision_id=decision.get('decision_id', 'unknown'),
            executive_summary=self._generate_executive_summary(decision, context),
            layperson_explanation=self._generate_layperson_explanation(decision, context),
            technical_explanation=self._generate_technical_explanation(decision, context),
            audit_trail=self._generate_audit_trail_data(decision),
            metadata=self._extract_metadata(decision)
        )

    def _generate_executive_summary(
        self,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate executive summary (1-2 sentences).

        Format: "Decision: [VERDICT] with [X%] confidence. [Key reason]."
        """
        verdict = self._get_final_verdict(decision)
        confidence = self._get_final_confidence(decision)
        key_reason = self._extract_key_reason(decision)

        # Format confidence as percentage
        confidence_pct = int(confidence * 100)

        summary = f"Decision: {verdict} with {confidence_pct}% confidence."

        if key_reason:
            summary += f" {key_reason}."

        return summary

    def _generate_layperson_explanation(
        self,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate plain language explanation without technical jargon.

        Focuses on:
        - What was decided and why
        - Key factors that influenced the decision
        - Simple, clear language
        """
        verdict = self._get_final_verdict(decision)
        confidence = self._get_final_confidence(decision)
        critic_reports = decision.get('critic_reports', [])

        # Start with the decision
        explanation_parts = []

        # Opening statement
        verdict_text = {
            'APPROVE': 'approved',
            'DENY': 'declined',
            'REVIEW': 'flagged for review'
        }.get(verdict, 'decided')

        confidence_text = self._confidence_to_text(confidence)

        explanation_parts.append(
            f"Your request was {verdict_text}. We are {confidence_text} about this decision."
        )

        # Explain the process
        if critic_reports:
            explanation_parts.append(
                f"\nWe evaluated your request using {len(critic_reports)} different criteria:"
            )

            # Summarize critic evaluations
            for i, report in enumerate(critic_reports, 1):
                critic_name = self._humanize_critic_name(report.get('critic_name', 'Evaluator'))
                verdict = report.get('verdict', 'UNKNOWN')
                justification = report.get('justification', '')

                # Simplify verdict
                verdict_simple = {
                    'APPROVE': 'passed',
                    'DENY': 'flagged concerns',
                    'REVIEW': 'needed review'
                }.get(verdict, 'evaluated')

                # Extract first sentence of justification
                reason = justification.split('.')[0] if justification else 'Evaluation completed'

                explanation_parts.append(f"\n{i}. {critic_name}: {verdict_simple}")
                if self.include_justifications and reason:
                    # Simplify technical language
                    reason_simple = self._simplify_language(reason)
                    explanation_parts.append(f"   → {reason_simple}")

        # Add aggregation explanation
        aggregation = decision.get('aggregation', {})
        if aggregation:
            agree_count = aggregation.get('agree_count', 0)
            total_count = len(critic_reports)

            if agree_count == total_count:
                explanation_parts.append(
                    f"\nAll {total_count} criteria agreed on this decision."
                )
            elif agree_count > total_count / 2:
                explanation_parts.append(
                    f"\nMost criteria ({agree_count} out of {total_count}) supported this decision."
                )
            else:
                explanation_parts.append(
                    f"\nThe criteria showed mixed results, with {agree_count} out of {total_count} in agreement."
                )

        # Add governance note if applied
        governance = decision.get('governance_outcome', {})
        if governance and governance.get('governance_applied', False):
            explanation_parts.append(
                "\nAdditional policy rules were applied to reach the final decision."
            )

        return ''.join(explanation_parts)

    def _generate_technical_explanation(
        self,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate detailed technical explanation for developers and data scientists.

        Includes:
        - Algorithm details
        - Critic parameters and weights
        - Aggregation logic
        - Confidence calculations
        """
        explanation_parts = []

        # Header
        decision_id = decision.get('decision_id', 'unknown')
        verdict = self._get_final_verdict(decision)
        confidence = self._get_final_confidence(decision)

        explanation_parts.append(
            f"=== EJE Decision Technical Report ===\n"
            f"Decision ID: {decision_id}\n"
            f"Final Verdict: {verdict}\n"
            f"Confidence: {confidence:.4f}\n"
        )

        # Input data
        input_data = decision.get('input_data', {})
        explanation_parts.append(f"\n--- Input Data ---")
        explanation_parts.append(f"\n{json.dumps(input_data, indent=2)}")

        # Critic evaluations
        critic_reports = decision.get('critic_reports', [])
        explanation_parts.append(f"\n\n--- Critic Evaluations ({len(critic_reports)} critics) ---")

        for i, report in enumerate(critic_reports, 1):
            critic_name = report.get('critic_name', f'Critic{i}')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.0)
            justification = report.get('justification', 'N/A')

            explanation_parts.append(
                f"\n{i}. {critic_name}:\n"
                f"   Verdict: {verdict}\n"
                f"   Confidence: {confidence:.4f}\n"
                f"   Justification: {justification}"
            )

        # Aggregation logic
        aggregation = decision.get('aggregation', {})
        explanation_parts.append(f"\n\n--- Aggregation Logic ---")
        explanation_parts.append(f"\nMethod: Weighted majority voting")
        explanation_parts.append(f"\nAggregated Verdict: {aggregation.get('verdict', 'N/A')}")
        explanation_parts.append(f"\nAggregated Confidence: {aggregation.get('confidence', 0.0):.4f}")
        explanation_parts.append(f"\nAgree Count: {aggregation.get('agree_count', 0)}")
        explanation_parts.append(f"\nDisagree Count: {aggregation.get('disagree_count', 0)}")

        # Check for conflicts
        conflicts = aggregation.get('conflicts', [])
        if conflicts:
            explanation_parts.append(f"\nConflicts Detected: {len(conflicts)}")
            for conflict in conflicts:
                explanation_parts.append(f"\n  - {conflict.get('type', 'Unknown')}: {conflict.get('description', 'N/A')}")

        # Governance
        governance = decision.get('governance_outcome', {})
        if governance:
            explanation_parts.append(f"\n\n--- Governance ---")
            explanation_parts.append(f"\nGovernance Applied: {governance.get('governance_applied', False)}")
            if governance.get('governance_applied'):
                explanation_parts.append(f"\nFinal Verdict: {governance.get('verdict', 'N/A')}")
                explanation_parts.append(f"\nFinal Confidence: {governance.get('confidence', 0.0):.4f}")
                rules_applied = governance.get('rules_applied', [])
                if rules_applied:
                    explanation_parts.append(f"\nRules Applied: {', '.join(rules_applied)}")

        # Precedents
        precedents = decision.get('precedents', [])
        if precedents:
            explanation_parts.append(f"\n\n--- Precedents ({len(precedents)} found) ---")
            for i, prec in enumerate(precedents[:3], 1):  # Top 3
                explanation_parts.append(
                    f"\n{i}. Precedent ID: {prec.get('id', 'N/A')}"
                    f"\n   Similarity: {prec.get('similarity', 0.0):.4f}"
                    f"\n   Outcome: {prec.get('outcome', 'N/A')}"
                )

        return ''.join(explanation_parts)

    def _generate_audit_trail(
        self,
        decision: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate complete audit trail as formatted text.

        Returns audit trail data as JSON string for compliance.
        """
        audit_data = self._generate_audit_trail_data(decision)
        return json.dumps(audit_data, indent=2, sort_keys=True)

    def _generate_audit_trail_data(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete audit trail data structure.

        Includes all decision data for compliance and auditing.
        """
        return {
            'decision_id': decision.get('decision_id', 'unknown'),
            'timestamp': decision.get('timestamp', ''),
            'input_data': decision.get('input_data', {}),
            'critic_evaluations': [
                {
                    'critic_name': r.get('critic_name', ''),
                    'verdict': r.get('verdict', ''),
                    'confidence': r.get('confidence', 0.0),
                    'justification': r.get('justification', ''),
                    'metadata': r.get('metadata', {})
                }
                for r in decision.get('critic_reports', [])
            ],
            'aggregation': decision.get('aggregation', {}),
            'governance_outcome': decision.get('governance_outcome', {}),
            'precedents': decision.get('precedents', []),
            'escalated': decision.get('escalated', False),
            'audit_metadata': {
                'total_critics': len(decision.get('critic_reports', [])),
                'consensus_reached': self._check_consensus(decision),
                'conflicts_detected': len(decision.get('aggregation', {}).get('conflicts', [])),
                'governance_applied': decision.get('governance_outcome', {}).get('governance_applied', False)
            }
        }

    def _get_final_verdict(self, decision: Dict[str, Any]) -> str:
        """Extract final verdict from decision."""
        governance = decision.get('governance_outcome', {})
        if governance and 'verdict' in governance:
            return governance['verdict']

        aggregation = decision.get('aggregation', {})
        if aggregation and 'verdict' in aggregation:
            return aggregation['verdict']

        return 'UNKNOWN'

    def _get_final_confidence(self, decision: Dict[str, Any]) -> float:
        """Extract final confidence from decision."""
        governance = decision.get('governance_outcome', {})
        if governance and 'confidence' in governance:
            return governance['confidence']

        aggregation = decision.get('aggregation', {})
        if aggregation and 'confidence' in aggregation:
            return aggregation['confidence']

        return 0.5

    def _extract_key_reason(self, decision: Dict[str, Any]) -> str:
        """Extract the key reason for the decision."""
        # Find the most confident critic that agrees with final verdict
        final_verdict = self._get_final_verdict(decision)
        critic_reports = decision.get('critic_reports', [])

        agreeing_critics = [
            r for r in critic_reports
            if r.get('verdict') == final_verdict
        ]

        if not agreeing_critics:
            return "Based on evaluation criteria"

        # Get most confident agreeing critic
        most_confident = max(agreeing_critics, key=lambda r: r.get('confidence', 0.0))

        # Extract first sentence of justification
        justification = most_confident.get('justification', '')
        if justification:
            first_sentence = justification.split('.')[0]
            return first_sentence[:80]  # Limit length

        return "Based on evaluation criteria"

    def _confidence_to_text(self, confidence: float) -> str:
        """Convert confidence score to human-readable text."""
        if confidence >= 0.9:
            return "very confident"
        elif confidence >= 0.75:
            return "confident"
        elif confidence >= 0.6:
            return "reasonably certain"
        elif confidence >= 0.5:
            return "moderately confident"
        else:
            return "somewhat uncertain"

    def _humanize_critic_name(self, critic_name: str) -> str:
        """Convert technical critic names to human-readable form."""
        # Remove "Critic" suffix
        name = critic_name.replace('Critic', '').strip()

        # Convert CamelCase to spaces
        import re
        name = re.sub('([A-Z])', r' \1', name).strip()

        # Convert snake_case to spaces
        name = name.replace('_', ' ')

        # Capitalize properly
        name = name.title()

        # Add descriptive suffix
        if not name:
            return "Evaluation System"

        return name

    def _simplify_language(self, text: str) -> str:
        """Simplify technical language for layperson explanations."""
        # Replace technical terms with simpler alternatives
        replacements = {
            'threshold': 'limit',
            'parameter': 'setting',
            'algorithm': 'process',
            'heuristic': 'rule',
            'metric': 'measure',
            'optimal': 'best',
            'suboptimal': 'not ideal',
            'deviation': 'difference',
            'anomaly': 'unusual pattern',
            'correlation': 'relationship',
            'statistically significant': 'meaningful',
            'within acceptable range': 'acceptable',
            'exceeds limits': 'too high',
            'below minimum': 'too low'
        }

        simplified = text
        for technical, simple in replacements.items():
            simplified = simplified.replace(technical, simple)

        return simplified

    def _check_consensus(self, decision: Dict[str, Any]) -> bool:
        """Check if critics reached consensus."""
        critic_reports = decision.get('critic_reports', [])
        if not critic_reports:
            return False

        verdicts = [r.get('verdict') for r in critic_reports]
        return len(set(verdicts)) == 1

    def _extract_metadata(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata about the decision."""
        critic_reports = decision.get('critic_reports', [])

        return {
            'decision_id': decision.get('decision_id', 'unknown'),
            'timestamp': decision.get('timestamp', ''),
            'num_critics': len(critic_reports),
            'final_verdict': self._get_final_verdict(decision),
            'final_confidence': self._get_final_confidence(decision),
            'consensus': self._check_consensus(decision),
            'conflicts': len(decision.get('aggregation', {}).get('conflicts', [])),
            'governance_applied': decision.get('governance_outcome', {}).get('governance_applied', False),
            'escalated': decision.get('escalated', False)
        }

    def generate_comparison(
        self,
        decision1: Dict[str, Any],
        decision2: Dict[str, Any],
        level: AudienceLevel = AudienceLevel.LAYPERSON
    ) -> str:
        """
        Generate comparative explanation between two decisions.

        Args:
            decision1: First decision
            decision2: Second decision
            level: Audience level

        Returns:
            Comparative explanation text
        """
        verdict1 = self._get_final_verdict(decision1)
        verdict2 = self._get_final_verdict(decision2)

        if level == AudienceLevel.EXECUTIVE:
            return self._generate_executive_comparison(decision1, decision2)
        elif level == AudienceLevel.LAYPERSON:
            return self._generate_layperson_comparison(decision1, decision2)
        else:
            return self._generate_technical_comparison(decision1, decision2)

    def _generate_executive_comparison(
        self,
        decision1: Dict[str, Any],
        decision2: Dict[str, Any]
    ) -> str:
        """Generate executive-level comparison."""
        verdict1 = self._get_final_verdict(decision1)
        verdict2 = self._get_final_verdict(decision2)
        conf1 = self._get_final_confidence(decision1)
        conf2 = self._get_final_confidence(decision2)

        if verdict1 == verdict2:
            return f"Both decisions resulted in {verdict1}. Confidence levels: {conf1:.0%} vs {conf2:.0%}."
        else:
            return f"Decision outcomes differ: {verdict1} vs {verdict2}. Different factors led to these results."

    def _generate_layperson_comparison(
        self,
        decision1: Dict[str, Any],
        decision2: Dict[str, Any]
    ) -> str:
        """Generate layperson-level comparison."""
        verdict1 = self._get_final_verdict(decision1)
        verdict2 = self._get_final_verdict(decision2)

        comparison = f"Comparing the two requests:\n\n"
        comparison += f"Request 1: {verdict1}\n"
        comparison += f"Request 2: {verdict2}\n\n"

        if verdict1 == verdict2:
            comparison += "Both requests had the same outcome. "
        else:
            comparison += "The requests had different outcomes. "

        comparison += "Key differences in the evaluations led to these results."

        return comparison

    def _generate_technical_comparison(
        self,
        decision1: Dict[str, Any],
        decision2: Dict[str, Any]
    ) -> str:
        """Generate technical-level comparison."""
        comparison = "=== Decision Comparison ===\n\n"

        comparison += f"Decision 1: {decision1.get('decision_id', 'N/A')}\n"
        comparison += f"  Verdict: {self._get_final_verdict(decision1)}\n"
        comparison += f"  Confidence: {self._get_final_confidence(decision1):.4f}\n"
        comparison += f"  Critics: {len(decision1.get('critic_reports', []))}\n\n"

        comparison += f"Decision 2: {decision2.get('decision_id', 'N/A')}\n"
        comparison += f"  Verdict: {self._get_final_verdict(decision2)}\n"
        comparison += f"  Confidence: {self._get_final_confidence(decision2):.4f}\n"
        comparison += f"  Critics: {len(decision2.get('critic_reports', []))}\n"

        return comparison


# Export
__all__ = ['MultiLevelExplainer', 'AudienceLevel', 'MultiLevelExplanation']
