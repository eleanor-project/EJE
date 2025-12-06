"""
Fallback Explanation Generator

Generates human-readable explanations for fallback scenarios,
helping users understand why fallback logic was triggered and what it means.
"""

from typing import Dict, List, Any, Optional
from .fallback_engine import FallbackResult, FallbackStrategy, FallbackTrigger
from ...utils.logging import get_logger


logger = get_logger("ejc.fallback.explainer")


class FallbackExplainer:
    """
    Generates explanations for fallback scenarios.

    Provides context-aware explanations at different technical levels.
    """

    def __init__(self, audience: str = "general"):
        """
        Initialize fallback explainer.

        Args:
            audience: Target audience (general, technical, executive)
        """
        self.audience = audience

        # Explanation templates by trigger
        self.trigger_explanations = {
            FallbackTrigger.ALL_CRITICS_FAILED: {
                "general": "All evaluation components encountered errors and could not complete their analysis.",
                "technical": "All critics failed during execution. System initiated fallback procedure to provide a decision.",
                "executive": "System components failed. Backup decision process activated."
            },
            FallbackTrigger.MAJORITY_CRITICS_FAILED: {
                "general": "Most evaluation components encountered errors, but some completed successfully.",
                "technical": "Majority of critics failed (> 50%). Fallback logic applied using successful critic results.",
                "executive": "Partial system failure. Decision made using available components."
            },
            FallbackTrigger.HIGH_ERROR_RATE: {
                "general": "An unusually high number of errors occurred during evaluation.",
                "technical": "Error rate exceeded configured threshold. Fallback triggered for system reliability.",
                "executive": "High error rate detected. Risk mitigation procedures applied."
            },
            FallbackTrigger.CRITICAL_CRITIC_FAILED: {
                "general": "A critical evaluation component failed and could not be completed.",
                "technical": "A critic marked as critical failed during execution. Fallback required per policy.",
                "executive": "Critical component failure. Escalation procedures initiated."
            },
            FallbackTrigger.TIMEOUT: {
                "general": "The evaluation process took too long and was stopped for safety.",
                "technical": "Evaluation exceeded timeout threshold. Fallback applied to prevent system hang.",
                "executive": "Processing timeout. Expedited decision process used."
            },
            FallbackTrigger.INSUFFICIENT_CONFIDENCE: {
                "general": "The system's confidence in its evaluation was too low to proceed normally.",
                "technical": "Aggregated confidence below acceptable threshold. Fallback for quality assurance.",
                "executive": "Low confidence in decision. Additional safeguards applied."
            },
            FallbackTrigger.MANUAL_OVERRIDE: {
                "general": "A human operator manually activated the fallback process.",
                "technical": "Manual fallback trigger activated by operator.",
                "executive": "Manual intervention: Operator-initiated fallback."
            }
        }

        # Strategy explanations
        self.strategy_explanations = {
            FallbackStrategy.CONSERVATIVE: {
                "general": "The system chose the most cautious approach to minimize risk.",
                "technical": "Conservative fallback strategy: defaulted to most restrictive verdict from successful critics.",
                "executive": "Risk-minimization approach applied."
            },
            FallbackStrategy.PERMISSIVE: {
                "general": "The system chose to allow the request with reduced confidence and additional monitoring.",
                "technical": "Permissive fallback strategy: defaulted to least restrictive verdict with warnings.",
                "executive": "Permissive decision with enhanced monitoring."
            },
            FallbackStrategy.ESCALATE: {
                "general": "The system is sending this decision to a human reviewer for careful examination.",
                "technical": "Escalation strategy: requiring human review before final decision.",
                "executive": "Human review required for final decision."
            },
            FallbackStrategy.FAIL_SAFE: {
                "general": "The system used a pre-configured safe default decision.",
                "technical": "Fail-safe strategy: applied configured safe default verdict.",
                "executive": "Safe default procedures activated."
            },
            FallbackStrategy.MAJORITY: {
                "general": "The system used the majority opinion from successful evaluation components.",
                "technical": "Majority strategy: verdict determined by majority of successful critics.",
                "executive": "Decision based on majority of available components."
            }
        }

    def explain_fallback(
        self,
        fallback_result: FallbackResult,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explanation for fallback scenario.

        Args:
            fallback_result: Fallback result to explain
            include_recommendations: Include recommendations for operators

        Returns:
            Structured explanation dictionary
        """
        explanation = {
            'summary': self._generate_summary(fallback_result),
            'trigger_explanation': self._explain_trigger(fallback_result.trigger_reason),
            'strategy_explanation': self._explain_strategy(fallback_result.fallback_strategy),
            'decision_explanation': self._explain_decision(fallback_result),
            'confidence_explanation': self._explain_confidence(fallback_result.confidence)
        }

        if include_recommendations:
            explanation['recommendations'] = self._generate_recommendations(fallback_result)

        return explanation

    def explain_to_user(self, fallback_result: FallbackResult) -> str:
        """
        Generate user-friendly explanation string.

        Args:
            fallback_result: Fallback result to explain

        Returns:
            Human-readable explanation string
        """
        parts = []

        # Summary
        summary = self._generate_summary(fallback_result)
        parts.append(summary)
        parts.append("")

        # Trigger
        trigger_exp = self._explain_trigger(fallback_result.trigger_reason)
        parts.append(f"Reason: {trigger_exp}")
        parts.append("")

        # Strategy
        strategy_exp = self._explain_strategy(fallback_result.fallback_strategy)
        parts.append(f"Action Taken: {strategy_exp}")
        parts.append("")

        # Decision
        decision_exp = self._explain_decision(fallback_result)
        parts.append(f"Decision: {decision_exp}")
        parts.append("")

        # Confidence
        conf_exp = self._explain_confidence(fallback_result.confidence)
        parts.append(f"Confidence: {conf_exp}")

        return "\n".join(parts)

    def _generate_summary(self, fallback_result: FallbackResult) -> str:
        """Generate summary sentence"""
        trigger = fallback_result.trigger_reason
        strategy = fallback_result.fallback_strategy.value
        verdict = fallback_result.fallback_verdict

        if self.audience == "executive":
            return f"Fallback activated ({trigger}). {strategy.title()} approach yielded: {verdict}"
        elif self.audience == "technical":
            return f"Fallback triggered by {trigger}. Applied {strategy} strategy, resulting in {verdict} verdict."
        else:  # general
            return f"The system encountered an issue ({trigger}) and used backup procedures to reach a {verdict} decision."

    def _explain_trigger(self, trigger_reason: str) -> str:
        """Explain trigger reason"""
        # Parse trigger string (might be enum value or description)
        for trigger_enum in FallbackTrigger:
            if trigger_enum.value in trigger_reason.lower():
                explanations = self.trigger_explanations.get(trigger_enum, {})
                return explanations.get(self.audience, trigger_reason)

        return trigger_reason  # Return as-is if no match

    def _explain_strategy(self, strategy: FallbackStrategy) -> str:
        """Explain fallback strategy"""
        explanations = self.strategy_explanations.get(strategy, {})
        return explanations.get(self.audience, f"{strategy.value} strategy applied")

    def _explain_decision(self, fallback_result: FallbackResult) -> str:
        """Explain the decision reached"""
        verdict = fallback_result.fallback_verdict
        reason = fallback_result.reason

        if self.audience == "executive":
            return f"Final decision: {verdict}"
        elif self.audience == "technical":
            return f"Fallback verdict: {verdict}. Reason: {reason}"
        else:  # general
            verdict_explanations = {
                'ALLOW': 'The request was approved.',
                'DENY': 'The request was denied.',
                'REVIEW': 'The request requires human review before a final decision.',
                'ESCALATE': 'The request has been escalated to a supervisor.'
            }
            return verdict_explanations.get(verdict, f"Decision: {verdict}")

    def _explain_confidence(self, confidence: float) -> str:
        """Explain confidence level"""
        if confidence >= 0.8:
            level = "high"
            desc = "very reliable"
        elif confidence >= 0.6:
            level = "moderate"
            desc = "reasonably reliable"
        elif confidence >= 0.4:
            level = "low"
            desc = "less certain"
        else:
            level = "very low"
            desc = "highly uncertain"

        if self.audience == "executive":
            return f"{level.title()} confidence ({confidence:.0%})"
        elif self.audience == "technical":
            return f"Confidence: {confidence:.2f} ({level})"
        else:  # general
            return f"The system is {desc} about this decision ({confidence:.0%} confidence)."

    def _generate_recommendations(self, fallback_result: FallbackResult) -> List[str]:
        """Generate recommendations for operators"""
        recommendations = []

        # Based on trigger
        if 'failed' in fallback_result.trigger_reason.lower():
            recommendations.append("Investigate critic failures in system logs")
            recommendations.append("Check for infrastructure issues or resource constraints")

        # Based on confidence
        if fallback_result.confidence < 0.5:
            recommendations.append("Consider manual review of this decision")
            recommendations.append("Monitor similar cases for patterns")

        # Based on strategy
        if fallback_result.fallback_strategy == FallbackStrategy.ESCALATE:
            recommendations.append("Human review required before final action")
            recommendations.append("Review case details and context carefully")

        # Based on metadata
        if fallback_result.metadata.get('warning'):
            recommendations.append(fallback_result.metadata['warning'])

        return recommendations

    def format_for_audit(
        self,
        fallback_result: FallbackResult,
        original_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format fallback explanation for audit trail.

        Args:
            fallback_result: Fallback result
            original_inputs: Original input data

        Returns:
            Audit-formatted explanation
        """
        audit_record = {
            'event_type': 'fallback_triggered',
            'timestamp': fallback_result.timestamp.isoformat(),
            'trigger': {
                'reason': fallback_result.trigger_reason,
                'description': self._explain_trigger(fallback_result.trigger_reason)
            },
            'strategy': {
                'applied': fallback_result.fallback_strategy.value,
                'description': self._explain_strategy(fallback_result.fallback_strategy)
            },
            'outcome': {
                'verdict': fallback_result.fallback_verdict,
                'confidence': fallback_result.confidence,
                'reason': fallback_result.reason
            },
            'explanation': self.explain_fallback(fallback_result, include_recommendations=False),
            'metadata': fallback_result.metadata
        }

        if original_inputs:
            audit_record['original_inputs'] = {
                'text': original_inputs.get('text', ''),
                'context_summary': str(original_inputs.get('context', {}))[:200]  # Truncate for brevity
            }

        return audit_record


# Convenience functions

def explain_fallback_simple(
    fallback_result: FallbackResult,
    audience: str = "general"
) -> str:
    """
    Simple convenience function for fallback explanation.

    Args:
        fallback_result: Fallback result to explain
        audience: Target audience

    Returns:
        Human-readable explanation string
    """
    explainer = FallbackExplainer(audience=audience)
    return explainer.explain_to_user(fallback_result)


def create_fallback_audit_record(
    fallback_result: FallbackResult,
    original_inputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create audit record for fallback event.

    Args:
        fallback_result: Fallback result
        original_inputs: Original input data

    Returns:
        Audit record dictionary
    """
    explainer = FallbackExplainer(audience="technical")
    return explainer.format_for_audit(fallback_result, original_inputs)
