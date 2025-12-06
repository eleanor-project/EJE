"""
Fallback Evidence Bundle Creation

Creates evidence bundles for fallback scenarios, documenting errors,
partial results, and fallback reasoning.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from ..evidence_normalizer import (
    EvidenceBundle,
    InputSnapshot,
    InputMetadata,
    CriticOutput,
    BundleMetadata,
    Flags,
    JustificationSynthesis,
    ConflictingEvidence,
    ConfidenceAssessment,
    ValidationError
)
from .fallback_engine import FallbackResult, FallbackStrategy
from ...utils.logging import get_logger


logger = get_logger("ejc.fallback.bundle")


def create_fallback_evidence_bundle(
    input_text: str,
    input_context: Optional[Dict[str, Any]],
    critic_outputs: List[Dict[str, Any]],
    fallback_result: FallbackResult,
    system_version: str = "1.0.0",
    correlation_id: Optional[str] = None
) -> EvidenceBundle:
    """
    Create an evidence bundle for a fallback scenario.

    Args:
        input_text: Original input text
        input_context: Input context
        critic_outputs: List of critic outputs (including failed ones)
        fallback_result: Result from fallback engine
        system_version: System version
        correlation_id: Correlation ID for tracing

    Returns:
        EvidenceBundle documenting the fallback scenario
    """
    # Create input snapshot
    input_snapshot = InputSnapshot(
        text=input_text,
        context=input_context or {},
        metadata=InputMetadata(),
        context_hash=""  # Will be auto-generated
    )

    # Convert critic outputs to CriticOutput objects
    critic_output_objects = []
    validation_errors = []
    successful_critics = []
    failed_critics = []

    for idx, raw_output in enumerate(critic_outputs):
        try:
            # Normalize critic output
            critic_output = CriticOutput(
                critic=raw_output.get('critic', f'unknown_critic_{idx}'),
                verdict=raw_output.get('verdict', 'ERROR'),
                confidence=float(raw_output.get('confidence', 0.0)),
                justification=raw_output.get('justification', 'No justification provided'),
                weight=float(raw_output.get('weight', 1.0)),
                priority=raw_output.get('priority')
            )
            critic_output_objects.append(critic_output)

            # Track successful vs failed
            if critic_output.verdict == 'ERROR':
                failed_critics.append(critic_output.critic)
            else:
                successful_critics.append(critic_output.critic)

        except Exception as e:
            validation_errors.append(
                ValidationError(
                    field=f"critic_outputs[{idx}]",
                    error=f"Failed to normalize critic output: {str(e)}",
                    severity="warning"
                )
            )

    # Add synthetic fallback critic output
    fallback_critic = CriticOutput(
        critic="fallback_engine",
        verdict=fallback_result.fallback_verdict,
        confidence=fallback_result.confidence,
        justification=fallback_result.reason,
        weight=1.0,
        priority="override" if fallback_result.fallback_strategy == FallbackStrategy.ESCALATE else None
    )
    critic_output_objects.append(fallback_critic)

    # Create justification synthesis
    conflicting_evidence = []
    if failed_critics:
        conflicting_evidence.append(
            ConflictingEvidence(
                critics=failed_critics,
                description=f"{len(failed_critics)} critic(s) failed during evaluation"
            )
        )

    # Calculate confidence assessment
    if successful_critics:
        confidences = [c.confidence for c in critic_output_objects if c.verdict != 'ERROR']
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        conf_variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences) if confidences else 0.0

        # Determine consensus level
        if not successful_critics:
            consensus = "conflicted"
        elif len(successful_critics) == len(critic_outputs):
            consensus = "unanimous"
        elif len(successful_critics) >= len(critic_outputs) * 0.8:
            consensus = "strong"
        elif len(successful_critics) >= len(critic_outputs) * 0.5:
            consensus = "moderate"
        else:
            consensus = "weak"

        confidence_assessment = ConfidenceAssessment(
            average_confidence=avg_conf,
            confidence_variance=conf_variance,
            consensus_level=consensus
        )
    else:
        confidence_assessment = ConfidenceAssessment(
            average_confidence=0.0,
            confidence_variance=0.0,
            consensus_level="conflicted"
        )

    justification_synthesis = JustificationSynthesis(
        summary=f"Fallback applied: {fallback_result.reason}",
        supporting_evidence=[
            f"Fallback strategy: {fallback_result.fallback_strategy.value}",
            f"Trigger: {fallback_result.trigger_reason}",
            f"Successful critics: {len(successful_critics)}/{len(critic_outputs)}",
            f"Final verdict: {fallback_result.fallback_verdict}"
        ],
        conflicting_evidence=conflicting_evidence,
        confidence_assessment=confidence_assessment
    )

    # Create bundle metadata
    metadata = BundleMetadata(
        system_version=system_version,
        environment="production",  # Fallback typically used in production
        correlation_id=correlation_id,
        flags=Flags(
            requires_human_review=fallback_result.fallback_strategy == FallbackStrategy.ESCALATE or fallback_result.confidence < 0.5,
            is_fallback=True,
            is_test=False
        )
    )

    # Add fallback-specific metadata
    metadata_dict = metadata.model_dump()
    metadata_dict['fallback'] = fallback_result.to_dict()
    metadata_dict['critic_failures'] = {
        'total': len(critic_outputs),
        'failed': len(failed_critics),
        'successful': len(successful_critics),
        'failed_critic_names': failed_critics
    }

    # Reconstruct metadata from dict (to preserve custom fields)
    # Note: This is a workaround since Pydantic doesn't allow arbitrary fields
    # In production, you'd want to extend BundleMetadata or use a separate field

    # Create evidence bundle
    bundle = EvidenceBundle(
        bundle_id=str(uuid.uuid4()),
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        input_snapshot=input_snapshot,
        critic_outputs=critic_output_objects,
        justification_synthesis=justification_synthesis,
        metadata=metadata,
        validation_errors=validation_errors
    )

    logger.info(f"Created fallback evidence bundle with {len(successful_critics)} successful critics")

    return bundle


def create_partial_failure_bundle(
    input_text: str,
    input_context: Optional[Dict[str, Any]],
    successful_outputs: List[Dict[str, Any]],
    failed_outputs: List[Dict[str, Any]],
    aggregated_verdict: str,
    system_version: str = "1.0.0"
) -> EvidenceBundle:
    """
    Create evidence bundle for partial critic failure scenario.

    Args:
        input_text: Original input text
        input_context: Input context
        successful_outputs: Successfully completed critic outputs
        failed_outputs: Failed critic outputs
        aggregated_verdict: Final aggregated verdict
        system_version: System version

    Returns:
        EvidenceBundle documenting partial failure
    """
    # Combine all outputs
    all_outputs = successful_outputs + failed_outputs

    # Create a synthetic fallback result
    from .fallback_engine import FallbackResult, FallbackStrategy, FallbackTrigger

    fallback_result = FallbackResult(
        triggered=True,
        trigger_reason=FallbackTrigger.MAJORITY_CRITICS_FAILED.value,
        fallback_strategy=FallbackStrategy.MAJORITY,
        fallback_verdict=aggregated_verdict,
        confidence=0.7,
        reason=f"Partial failure: {len(successful_outputs)} of {len(all_outputs)} critics succeeded"
    )

    return create_fallback_evidence_bundle(
        input_text=input_text,
        input_context=input_context,
        critic_outputs=all_outputs,
        fallback_result=fallback_result,
        system_version=system_version
    )


def augment_bundle_with_fallback(
    bundle: EvidenceBundle,
    fallback_result: FallbackResult
) -> EvidenceBundle:
    """
    Augment an existing evidence bundle with fallback information.

    Args:
        bundle: Existing evidence bundle
        fallback_result: Fallback result to add

    Returns:
        Updated evidence bundle
    """
    # Mark bundle as fallback
    bundle.metadata.flags.is_fallback = True

    # Add fallback critic
    fallback_critic = CriticOutput(
        critic="fallback_engine",
        verdict=fallback_result.fallback_verdict,
        confidence=fallback_result.confidence,
        justification=fallback_result.reason,
        weight=1.0,
        priority="override" if fallback_result.fallback_strategy == FallbackStrategy.ESCALATE else None
    )
    bundle.critic_outputs.append(fallback_critic)

    # Update justification synthesis
    if bundle.justification_synthesis:
        bundle.justification_synthesis.summary = (
            f"{bundle.justification_synthesis.summary} | Fallback applied: {fallback_result.reason}"
        )
        bundle.justification_synthesis.supporting_evidence.append(
            f"Fallback strategy: {fallback_result.fallback_strategy.value}"
        )
    else:
        bundle.justification_synthesis = JustificationSynthesis(
            summary=f"Fallback applied: {fallback_result.reason}",
            supporting_evidence=[f"Fallback strategy: {fallback_result.fallback_strategy.value}"]
        )

    logger.info(f"Augmented bundle {bundle.bundle_id} with fallback information")

    return bundle
