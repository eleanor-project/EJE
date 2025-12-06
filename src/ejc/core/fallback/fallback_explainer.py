"""
Fallback Explanation Generator

Generates human-readable explanations for fallback scenarios,
helping users understand why fallback logic was triggered and what it means.
"""

from typing import Dict, List, Any, Optional
from .fallback_engine import FallbackResult, FallbackStrategy, FallbackTrigger
from .fallback_evidence_schema import FallbackEvidenceBundle, FallbackType
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

    def explain_fallback_bundle(
        self,
        bundle: FallbackEvidenceBundle,
        include_technical_details: bool = False
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explanation for FallbackEvidenceBundle.

        Task 6.3: Human-readable explanation for fallback events

        Args:
            bundle: FallbackEvidenceBundle to explain
            include_technical_details: Include technical error details

        Returns:
            Structured explanation with:
            - Clear failure reasons
            - List of affected critics
            - Safety rationale
        """
        explanation = {
            'summary': self._generate_bundle_summary(bundle),
            'trigger_explanation': self._explain_fallback_type(bundle.fallback_type),
            'failed_critics': self._list_failed_critics(bundle, include_technical_details),
            'decision_explanation': self._explain_bundle_decision(bundle),
            'safety_rationale': self._explain_safety_rationale(bundle),
            'system_state_summary': self._summarize_system_state(bundle),
        }

        if bundle.warnings:
            explanation['warnings'] = bundle.warnings

        if bundle.errors:
            explanation['errors'] = bundle.errors

        return explanation

    def explain_bundle_to_user(
        self,
        bundle: FallbackEvidenceBundle,
        verbose: bool = False
    ) -> str:
        """
        Generate user-friendly explanation string for FallbackEvidenceBundle.

        Task 6.3: Clear, human-readable fallback explanations

        Args:
            bundle: FallbackEvidenceBundle to explain
            verbose: Include detailed information

        Returns:
            Human-readable explanation string
        """
        parts = []

        # Summary
        parts.append("FALLBACK EVENT EXPLANATION")
        parts.append("=" * 60)
        parts.append("")
        parts.append(self._generate_bundle_summary(bundle))
        parts.append("")

        # What triggered the fallback
        parts.append("WHY DID FALLBACK OCCUR?")
        parts.append("-" * 60)
        parts.append(self._explain_fallback_type(bundle.fallback_type))
        parts.append("")

        # Which critics failed
        parts.append("WHICH CRITICS WERE AFFECTED?")
        parts.append("-" * 60)
        failed_critic_info = self._list_failed_critics(bundle, include_technical_details=verbose)
        if failed_critic_info:
            for critic_info in failed_critic_info:
                parts.append(f"• {critic_info['name']}: {critic_info['reason']}")
                if verbose and critic_info.get('error_type'):
                    parts.append(f"  Error Type: {critic_info['error_type']}")
        else:
            parts.append("No critic failures (triggered by other conditions)")
        parts.append("")

        # What decision was made
        parts.append("WHAT DECISION WAS MADE?")
        parts.append("-" * 60)
        parts.append(self._explain_bundle_decision(bundle))
        parts.append("")

        # Why is this safe
        parts.append("WHY IS THIS DECISION SAFE?")
        parts.append("-" * 60)
        parts.append(self._explain_safety_rationale(bundle))
        parts.append("")

        # System state (if verbose)
        if verbose:
            parts.append("SYSTEM STATE AT TRIGGER")
            parts.append("-" * 60)
            parts.append(self._summarize_system_state(bundle))
            parts.append("")

        # Warnings and errors
        if bundle.warnings:
            parts.append("WARNINGS:")
            for warning in bundle.warnings:
                parts.append(f"⚠  {warning}")
            parts.append("")

        if bundle.errors:
            parts.append("ERRORS:")
            for error in bundle.errors:
                parts.append(f"✗ {error}")
            parts.append("")

        return "\n".join(parts)

    def _generate_bundle_summary(self, bundle: FallbackEvidenceBundle) -> str:
        """
        Generate summary sentence for fallback bundle.

        Task 6.3: Clear failure reasons
        """
        fallback_type = bundle.fallback_type.value.replace('_', ' ').title()
        decision = bundle.fallback_decision
        verdict = decision.verdict
        confidence = decision.confidence

        failed_count = len(bundle.failed_critics)
        total_count = bundle.system_state_at_trigger.total_critics_attempted

        if self.audience == "executive":
            return f"Fallback Event: {fallback_type}. Decision: {verdict} ({confidence:.0%} confidence)"
        elif self.audience == "technical":
            return (
                f"Fallback triggered: {bundle.fallback_type.value}. "
                f"{failed_count}/{total_count} critics failed. "
                f"Strategy: {decision.strategy_used}. "
                f"Verdict: {verdict} (confidence: {confidence:.2f})"
            )
        else:  # general
            if failed_count == total_count:
                critic_msg = "All evaluation components failed"
            elif failed_count > 0:
                critic_msg = f"{failed_count} out of {total_count} evaluation components failed"
            else:
                critic_msg = "System triggered fallback procedures"

            return (
                f"{critic_msg}. The system used backup decision-making procedures "
                f"and reached a {verdict} decision with {confidence:.0%} confidence."
            )

    def _explain_fallback_type(self, fallback_type: FallbackType) -> str:
        """
        Explain why fallback was triggered based on type.

        Task 6.3: Clear failure reasons
        """
        explanations = {
            FallbackType.ALL_CRITICS_FAILED: {
                "general": "All evaluation components encountered errors and could not complete their analysis. This may indicate a system-wide issue that needs attention.",
                "technical": "All critics failed during execution. No successful critic outputs were produced. System initiated fallback procedure to provide a safe decision.",
                "executive": "Complete system failure across all evaluation components. Backup procedures activated."
            },
            FallbackType.MAJORITY_CRITICS_FAILED: {
                "general": "Most evaluation components encountered errors, though some completed successfully. The decision was made using the available successful results.",
                "technical": "Majority of critics (> 50%) failed during execution. Fallback logic applied using partial set of successful critic outputs.",
                "executive": "Partial system failure. Decision derived from available functioning components."
            },
            FallbackType.CRITICAL_CRITIC_FAILED: {
                "general": "A critical evaluation component that must succeed failed to complete. This component is essential for safe operation.",
                "technical": "A critic designated as 'critical' failed during execution. System policy requires fallback when critical critics fail.",
                "executive": "Critical component failure. Mandatory escalation procedures initiated."
            },
            FallbackType.TIMEOUT_EXCEEDED: {
                "general": "The evaluation process took too long and was stopped for safety. Long-running evaluations can indicate problems.",
                "technical": "Evaluation process exceeded configured timeout threshold. Fallback triggered to prevent system hang and ensure responsiveness.",
                "executive": "Processing timeout exceeded. Expedited decision procedures applied."
            },
            FallbackType.SCHEMA_VALIDATION_FAILED: {
                "general": "The evaluation results did not meet quality standards and could not be validated. This ensures only high-quality decisions proceed.",
                "technical": "Critic outputs failed schema validation checks. Data integrity issue detected, fallback required for safety.",
                "executive": "Data validation failure. Quality assurance procedures triggered fallback."
            },
            FallbackType.INSUFFICIENT_CONFIDENCE: {
                "general": "The system's confidence in its evaluation was too low to proceed normally. Low confidence indicates uncertainty that requires special handling.",
                "technical": "Aggregated confidence score below acceptable threshold. Fallback applied to ensure decision quality.",
                "executive": "Low confidence detected. Additional safeguards and review procedures applied."
            },
            FallbackType.HIGH_ERROR_RATE: {
                "general": "An unusually high number of errors occurred during evaluation. This pattern suggests a systemic problem requiring investigation.",
                "technical": "Error rate exceeded configured threshold, indicating potential systemic issues. Fallback triggered for system reliability.",
                "executive": "High error rate detected. Risk mitigation and monitoring procedures activated."
            },
            FallbackType.MANUAL_OVERRIDE: {
                "general": "A human operator manually activated the fallback process for this evaluation.",
                "technical": "Manual fallback trigger activated by authorized operator. Operator intervention supersedes normal processing.",
                "executive": "Manual intervention: Operator-initiated fallback override."
            },
            FallbackType.SYSTEM_ERROR: {
                "general": "An unexpected system error occurred that prevented normal evaluation. The system entered safe mode to handle the error.",
                "technical": "Unexpected system error during evaluation. Fallback safety mechanism engaged to provide graceful degradation.",
                "executive": "System error encountered. Emergency procedures activated."
            }
        }

        fallback_explanations = explanations.get(fallback_type, {})
        return fallback_explanations.get(
            self.audience,
            f"Fallback triggered due to: {fallback_type.value.replace('_', ' ')}"
        )

    def _list_failed_critics(
        self,
        bundle: FallbackEvidenceBundle,
        include_technical_details: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List failed critics with clear failure reasons.

        Task 6.3: List affected critics
        """
        failed_critic_list = []

        for failed_critic in bundle.failed_critics:
            critic_info = {
                'name': failed_critic.critic_name,
                'reason': failed_critic.failure_reason,
                'error_type': failed_critic.error_type
            }

            if include_technical_details:
                critic_info['error_message'] = failed_critic.error_message
                critic_info['retries'] = failed_critic.attempted_retries
                if failed_critic.stack_trace:
                    critic_info['stack_trace'] = failed_critic.stack_trace

            failed_critic_list.append(critic_info)

        return failed_critic_list

    def _explain_bundle_decision(self, bundle: FallbackEvidenceBundle) -> str:
        """Explain the fallback decision that was made"""
        decision = bundle.fallback_decision
        verdict = decision.verdict
        strategy = decision.strategy_used
        confidence = decision.confidence

        if self.audience == "executive":
            return f"Decision: {verdict} using {strategy} approach ({confidence:.0%} confidence)"
        elif self.audience == "technical":
            return (
                f"Fallback verdict: {verdict}. "
                f"Strategy: {strategy}. "
                f"Confidence: {confidence:.2f}. "
                f"Reason: {decision.reason}"
            )
        else:  # general
            verdict_explanations = {
                'ALLOW': f"The request was approved using {strategy} procedures.",
                'DENY': f"The request was denied using {strategy} procedures.",
                'REVIEW': f"The request requires human review before a final decision. This ensures careful examination when the system encounters issues.",
                'ESCALATE': f"The request has been escalated to a supervisor for careful review."
            }
            base_exp = verdict_explanations.get(
                verdict,
                f"Decision: {verdict} using {strategy} approach"
            )
            return f"{base_exp} The system's confidence in this decision is {confidence:.0%}."

    def _explain_safety_rationale(self, bundle: FallbackEvidenceBundle) -> str:
        """
        Explain why the fallback decision is safe.

        Task 6.3: Safety rationale
        """
        decision = bundle.fallback_decision

        # Build safety rationale
        rationale_points = []

        # 1. Safe default check
        if decision.is_safe_default:
            rationale_points.append(
                "The decision uses a proven safe-default strategy that prioritizes caution and risk minimization."
            )

        # 2. Human review requirement
        if decision.requires_human_review:
            rationale_points.append(
                "Human review is required before final action, ensuring expert oversight for critical decisions."
            )

        # 3. Conservative approach for high failure rates
        if bundle.get_failure_rate() > 0.5:
            rationale_points.append(
                f"With a {bundle.get_failure_rate():.0%} failure rate, the system applies conservative "
                "safeguards to minimize risk."
            )

        # 4. Strategy-specific safety
        strategy = decision.strategy_used
        strategy_safety = {
            'conservative': "The conservative strategy defaults to the most restrictive safe verdict, minimizing risk of harm.",
            'escalate': "The escalation strategy ensures expert human review, providing maximum safety for uncertain cases.",
            'fail_safe': "The fail-safe strategy uses a pre-approved safe default verdict that has been validated for error scenarios.",
            'majority': "The majority strategy relies on consensus from successful components, providing collective decision confidence.",
            'permissive': "The permissive strategy is applied with enhanced monitoring and reduced confidence, ensuring oversight."
        }
        if strategy in strategy_safety:
            rationale_points.append(strategy_safety[strategy])

        # 5. Successful critics consideration
        successful_count = bundle.system_state_at_trigger.total_critics_succeeded
        if successful_count > 0:
            rationale_points.append(
                f"{successful_count} evaluation component(s) completed successfully and contributed to the decision."
            )

        # 6. Audit trail
        rationale_points.append(
            f"This decision is fully logged and auditable (Bundle ID: {bundle.bundle_id[:8]}...)."
        )

        if self.audience == "executive":
            return f"Safety ensured through: {len(rationale_points)} safeguards including {'human review, ' if decision.requires_human_review else ''}safe-default procedures, and complete audit trail."
        elif self.audience == "technical":
            return "Safety rationale:\n  - " + "\n  - ".join(rationale_points)
        else:  # general
            return "This decision is safe because:\n• " + "\n• ".join(rationale_points)

    def _summarize_system_state(self, bundle: FallbackEvidenceBundle) -> str:
        """Summarize system state at trigger time"""
        state = bundle.system_state_at_trigger

        if self.audience == "executive":
            return (
                f"System state: {state.total_critics_succeeded}/{state.total_critics_attempted} components succeeded. "
                f"Elapsed time: {state.elapsed_time_ms:.0f}ms."
            )
        elif self.audience == "technical":
            return (
                f"System State:\n"
                f"  - Expected critics: {state.total_critics_expected}\n"
                f"  - Attempted: {state.total_critics_attempted}\n"
                f"  - Succeeded: {state.total_critics_succeeded}\n"
                f"  - Failed: {state.total_critics_failed}\n"
                f"  - Elapsed time: {state.elapsed_time_ms:.0f}ms\n"
                f"  - Timeout threshold: {state.timeout_threshold_ms or 'Not set'}ms\n"
                f"  - Environment: {state.environment}\n"
                f"  - System version: {state.system_version}"
            )
        else:  # general
            success_rate = (state.total_critics_succeeded / state.total_critics_attempted * 100
                          if state.total_critics_attempted > 0 else 0)
            return (
                f"When fallback occurred: {state.total_critics_succeeded} out of "
                f"{state.total_critics_attempted} components succeeded ({success_rate:.0f}% success rate). "
                f"Processing took {state.elapsed_time_ms:.0f} milliseconds."
            )


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


def explain_fallback_bundle_simple(
    bundle: FallbackEvidenceBundle,
    audience: str = "general",
    verbose: bool = False
) -> str:
    """
    Simple convenience function for FallbackEvidenceBundle explanation.

    Task 6.3: Fallback Explanation Generator

    Args:
        bundle: FallbackEvidenceBundle to explain
        audience: Target audience (general, technical, executive)
        verbose: Include detailed technical information

    Returns:
        Human-readable explanation string
    """
    explainer = FallbackExplainer(audience=audience)
    return explainer.explain_bundle_to_user(bundle, verbose=verbose)


def get_fallback_bundle_details(
    bundle: FallbackEvidenceBundle,
    include_technical_details: bool = False
) -> Dict[str, Any]:
    """
    Get structured details from FallbackEvidenceBundle.

    Task 6.3: Clear failure reasons, affected critics list, safety rationale

    Args:
        bundle: FallbackEvidenceBundle to extract details from
        include_technical_details: Include technical error information

    Returns:
        Dictionary with:
        - summary: Overall summary
        - trigger_explanation: Why fallback occurred
        - failed_critics: List of failed critics with reasons
        - decision_explanation: What decision was made
        - safety_rationale: Why the decision is safe
        - system_state_summary: System state at trigger
    """
    explainer = FallbackExplainer(audience="general")
    return explainer.explain_fallback_bundle(bundle, include_technical_details)
