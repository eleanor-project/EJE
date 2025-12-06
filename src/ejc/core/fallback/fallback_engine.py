"""
Fallback Engine Core

Implements fallback logic for error scenarios, critic failures, and graceful degradation.
Provides multiple fallback strategies with configurable triggers and actions.

Features:
- Multiple fallback strategies (conservative, permissive, escalation)
- Automatic error detection and handling
- Graceful degradation with partial critic results
- Configurable fallback triggers
- Detailed fallback reasoning and audit trails
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import time

from ..evidence_normalizer import EvidenceBundle, CriticOutput, ValidationError
from .fallback_evidence_schema import (
    FallbackEvidenceBundle,
    FallbackType,
    FailedCriticInfo,
    SystemStateAtTrigger,
    FallbackDecision
)
from ..error_handling import CriticTimeoutException
from ...utils.logging import get_logger


logger = get_logger("ejc.fallback.engine")


class FallbackStrategy(Enum):
    """Fallback strategy types"""
    CONSERVATIVE = "conservative"  # Default to most restrictive (DENY/REVIEW)
    PERMISSIVE = "permissive"      # Default to least restrictive (ALLOW with warnings)
    ESCALATE = "escalate"          # Always escalate to human review
    FAIL_SAFE = "fail_safe"        # Use configured safe default
    MAJORITY = "majority"          # Use majority of successful critics
    PRECEDENT = "precedent"        # Use similar precedent cases


class FallbackTrigger(Enum):
    """Conditions that trigger fallback logic"""
    ALL_CRITICS_FAILED = "all_critics_failed"
    MAJORITY_CRITICS_FAILED = "majority_critics_failed"
    HIGH_ERROR_RATE = "high_error_rate"
    CRITICAL_CRITIC_FAILED = "critical_critic_failed"
    TIMEOUT = "timeout"
    INSUFFICIENT_CONFIDENCE = "insufficient_confidence"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class FallbackResult:
    """Result of fallback logic application"""
    triggered: bool
    trigger_reason: str
    fallback_strategy: FallbackStrategy
    fallback_verdict: str
    confidence: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'triggered': self.triggered,
            'trigger_reason': self.trigger_reason,
            'fallback_strategy': self.fallback_strategy.value,
            'fallback_verdict': self.fallback_verdict,
            'confidence': self.confidence,
            'reason': self.reason,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class FallbackEngine:
    """
    Fallback engine for handling errors and graceful degradation.

    Implements multiple fallback strategies with configurable triggers
    to ensure system resilience in error scenarios.
    """

    def __init__(
        self,
        default_strategy: FallbackStrategy = FallbackStrategy.CONSERVATIVE,
        error_rate_threshold: float = 0.5,
        min_successful_critics: int = 1,
        critical_critics: Optional[List[str]] = None,
        safe_default_verdict: str = "REVIEW",
        timeout_threshold_ms: Optional[float] = None,
        enable_audit_bundles: bool = True
    ):
        """
        Initialize fallback engine.

        Args:
            default_strategy: Default fallback strategy
            error_rate_threshold: Threshold for high error rate trigger
            min_successful_critics: Minimum successful critics required
            critical_critics: List of critic names that are critical
            safe_default_verdict: Safe default verdict for FAIL_SAFE strategy
            timeout_threshold_ms: Timeout threshold in milliseconds (None = no timeout checking)
            enable_audit_bundles: Whether to create FallbackEvidenceBundle for audit trails
        """
        self.default_strategy = default_strategy
        self.error_rate_threshold = error_rate_threshold
        self.min_successful_critics = min_successful_critics
        self.critical_critics = set(critical_critics or [])
        self.safe_default_verdict = safe_default_verdict
        self.timeout_threshold_ms = timeout_threshold_ms
        self.enable_audit_bundles = enable_audit_bundles

        # Strategy handlers
        self.strategy_handlers = {
            FallbackStrategy.CONSERVATIVE: self._apply_conservative,
            FallbackStrategy.PERMISSIVE: self._apply_permissive,
            FallbackStrategy.ESCALATE: self._apply_escalate,
            FallbackStrategy.FAIL_SAFE: self._apply_fail_safe,
            FallbackStrategy.MAJORITY: self._apply_majority
        }

    def should_fallback(
        self,
        critic_outputs: List[Dict[str, Any]],
        aggregation_result: Optional[Dict[str, Any]] = None,
        elapsed_time_ms: Optional[float] = None,
        validation_errors: Optional[List[Any]] = None
    ) -> tuple[bool, Optional[FallbackTrigger], str]:
        """
        Determine if fallback logic should be triggered.

        Task 6.2: Enhanced to detect timeouts and schema validation failures

        Args:
            critic_outputs: List of critic output dictionaries
            aggregation_result: Optional aggregation result
            elapsed_time_ms: Time elapsed in milliseconds (for timeout detection)
            validation_errors: List of validation errors (for schema validation detection)

        Returns:
            Tuple of (should_fallback, trigger, reason)
        """
        if not critic_outputs:
            return True, FallbackTrigger.ALL_CRITICS_FAILED, "No critic outputs available"

        # Task 6.2: Check for timeout exceeded
        if self.timeout_threshold_ms and elapsed_time_ms:
            if elapsed_time_ms > self.timeout_threshold_ms:
                return True, FallbackTrigger.TIMEOUT, f"Execution time {elapsed_time_ms:.0f}ms exceeds threshold {self.timeout_threshold_ms:.0f}ms"

        # Task 6.2: Check for schema validation failures
        if validation_errors:
            critical_errors = [e for e in validation_errors if getattr(e, 'severity', 'error') == 'error']
            if critical_errors:
                return True, FallbackTrigger.TIMEOUT, f"{len(critical_errors)} schema validation error(s) detected"

        # Count successes and failures
        total = len(critic_outputs)
        errors = sum(1 for c in critic_outputs if c.get('verdict') == 'ERROR')
        timeouts = sum(1 for c in critic_outputs if c.get('error_type') == 'timeout' or
                      isinstance(c.get('error'), (CriticTimeoutException, TimeoutError)))
        successful = total - errors

        # Task 6.2: Check for timeout failures
        if timeouts > 0:
            if timeouts == total:
                return True, FallbackTrigger.TIMEOUT, f"All {total} critics timed out"
            elif timeouts >= total / 2:
                return True, FallbackTrigger.TIMEOUT, f"{timeouts}/{total} critics timed out"

        # Check triggers
        # All critics failed
        if errors == total:
            return True, FallbackTrigger.ALL_CRITICS_FAILED, f"All {total} critics failed"

        # Majority failed
        if errors > total / 2:
            return True, FallbackTrigger.MAJORITY_CRITICS_FAILED, f"{errors}/{total} critics failed"

        # High error rate
        error_rate = errors / total if total > 0 else 1.0
        if error_rate >= self.error_rate_threshold:
            return True, FallbackTrigger.HIGH_ERROR_RATE, f"Error rate {error_rate:.1%} exceeds threshold"

        # Critical critic failed
        for critic in critic_outputs:
            if critic.get('critic') in self.critical_critics and critic.get('verdict') == 'ERROR':
                return True, FallbackTrigger.CRITICAL_CRITIC_FAILED, f"Critical critic '{critic['critic']}' failed"

        # Insufficient successful critics
        if successful < self.min_successful_critics:
            return True, FallbackTrigger.MAJORITY_CRITICS_FAILED, f"Only {successful} successful critics (min: {self.min_successful_critics})"

        # Check confidence if aggregation available
        if aggregation_result:
            confidence = aggregation_result.get('avg_confidence', 1.0)
            if confidence < 0.3:  # Very low confidence
                return True, FallbackTrigger.INSUFFICIENT_CONFIDENCE, f"Very low confidence ({confidence:.2f})"

        return False, None, ""

    def apply_fallback(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        strategy: Optional[FallbackStrategy] = None,
        context: Optional[Dict[str, Any]] = None,
        elapsed_time_ms: Optional[float] = None,
        validation_errors: Optional[List[Any]] = None
    ) -> FallbackResult:
        """
        Apply fallback logic with specified strategy.

        Task 6.2: Enhanced to create FallbackEvidenceBundle for auditability

        Args:
            critic_outputs: List of critic outputs (including failed ones)
            trigger: Fallback trigger condition
            strategy: Fallback strategy (uses default if None)
            context: Additional context for fallback decision
            elapsed_time_ms: Time elapsed in milliseconds
            validation_errors: List of validation errors

        Returns:
            FallbackResult with verdict and reasoning
        """
        strategy = strategy or self.default_strategy
        logger.warning(f"Applying fallback strategy '{strategy.value}' due to {trigger.value}")

        # Get strategy handler
        handler = self.strategy_handlers.get(strategy)
        if not handler:
            logger.error(f"Unknown fallback strategy: {strategy}")
            # Fall back to conservative
            handler = self._apply_conservative

        # Apply strategy
        try:
            start_time = time.time()
            result = handler(critic_outputs, trigger, context or {})
            decision_time_ms = (time.time() - start_time) * 1000

            # Task 6.2: Create audit bundle if enabled
            if self.enable_audit_bundles:
                audit_bundle = self._create_audit_bundle(
                    critic_outputs=critic_outputs,
                    trigger=trigger,
                    fallback_result=result,
                    context=context or {},
                    elapsed_time_ms=elapsed_time_ms,
                    validation_errors=validation_errors,
                    decision_time_ms=decision_time_ms
                )
                # Store audit bundle in result metadata
                result.metadata['audit_bundle'] = audit_bundle.to_dict()
                result.metadata['audit_bundle_id'] = audit_bundle.bundle_id

            return result
        except Exception as e:
            logger.error(f"Fallback strategy failed: {str(e)}, using fail-safe")
            return self._apply_fail_safe(critic_outputs, trigger, context or {})

    def _apply_conservative(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> FallbackResult:
        """Conservative strategy: Default to most restrictive"""
        # Get successful critics
        successful = [c for c in critic_outputs if c.get('verdict') != 'ERROR']

        if successful:
            # Find most restrictive verdict
            verdicts = [c.get('verdict') for c in successful]
            if 'DENY' in verdicts or 'BLOCK' in verdicts:
                verdict = 'DENY'
                reason = "Conservative fallback: DENY verdict present in successful critics"
            elif 'REVIEW' in verdicts:
                verdict = 'REVIEW'
                reason = "Conservative fallback: REVIEW verdict present in successful critics"
            else:
                verdict = 'REVIEW'  # Default to review for safety
                reason = "Conservative fallback: Defaulting to REVIEW for safety"

            # Use minimum confidence from successful critics
            confidences = [c.get('confidence', 0.0) for c in successful]
            confidence = min(confidences) * 0.8  # Reduce confidence due to errors
        else:
            verdict = 'REVIEW'
            confidence = 0.0
            reason = "Conservative fallback: All critics failed, requiring human review"

        return FallbackResult(
            triggered=True,
            trigger_reason=trigger.value,
            fallback_strategy=FallbackStrategy.CONSERVATIVE,
            fallback_verdict=verdict,
            confidence=confidence,
            reason=reason,
            metadata={
                'successful_critics': len(successful),
                'total_critics': len(critic_outputs)
            }
        )

    def _apply_permissive(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> FallbackResult:
        """Permissive strategy: Default to least restrictive with warnings"""
        successful = [c for c in critic_outputs if c.get('verdict') != 'ERROR']

        if successful:
            # Find least restrictive verdict
            verdicts = [c.get('verdict') for c in successful]
            if 'ALLOW' in verdicts:
                verdict = 'ALLOW'
                reason = "Permissive fallback: ALLOW verdict present, proceeding with warnings"
            else:
                verdict = 'REVIEW'
                reason = "Permissive fallback: No ALLOW verdict, defaulting to REVIEW"

            confidences = [c.get('confidence', 0.0) for c in successful]
            confidence = max(confidences) * 0.7  # Moderate confidence reduction
        else:
            verdict = 'ALLOW'
            confidence = 0.3
            reason = "Permissive fallback: All critics failed, allowing with low confidence"

        return FallbackResult(
            triggered=True,
            trigger_reason=trigger.value,
            fallback_strategy=FallbackStrategy.PERMISSIVE,
            fallback_verdict=verdict,
            confidence=confidence,
            reason=reason,
            metadata={
                'warning': 'Permissive fallback applied - monitor decision closely',
                'successful_critics': len(successful),
                'total_critics': len(critic_outputs)
            }
        )

    def _apply_escalate(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> FallbackResult:
        """Escalation strategy: Always escalate to human review"""
        return FallbackResult(
            triggered=True,
            trigger_reason=trigger.value,
            fallback_strategy=FallbackStrategy.ESCALATE,
            fallback_verdict='REVIEW',
            confidence=0.0,
            reason="Fallback triggered: Escalating to human review",
            metadata={
                'requires_human_review': True,
                'escalation_reason': trigger.value,
                'total_critics': len(critic_outputs),
                'failed_critics': len([c for c in critic_outputs if c.get('verdict') == 'ERROR'])
            }
        )

    def _apply_fail_safe(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> FallbackResult:
        """Fail-safe strategy: Use configured safe default"""
        return FallbackResult(
            triggered=True,
            trigger_reason=trigger.value,
            fallback_strategy=FallbackStrategy.FAIL_SAFE,
            fallback_verdict=self.safe_default_verdict,
            confidence=0.5,
            reason=f"Fail-safe fallback: Using safe default verdict '{self.safe_default_verdict}'",
            metadata={
                'safe_default': self.safe_default_verdict,
                'total_critics': len(critic_outputs)
            }
        )

    def _apply_majority(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> FallbackResult:
        """Majority strategy: Use majority verdict from successful critics"""
        successful = [c for c in critic_outputs if c.get('verdict') != 'ERROR']

        if not successful:
            # Fall back to fail-safe if no successful critics
            return self._apply_fail_safe(critic_outputs, trigger, context)

        # Count verdicts
        verdict_counts: Dict[str, int] = {}
        for critic in successful:
            verdict = critic.get('verdict', 'REVIEW')
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Get majority verdict
        majority_verdict = max(verdict_counts, key=verdict_counts.get)
        majority_count = verdict_counts[majority_verdict]

        # Calculate confidence based on majority strength
        confidence = (majority_count / len(successful)) * 0.8  # Reduce due to errors

        return FallbackResult(
            triggered=True,
            trigger_reason=trigger.value,
            fallback_strategy=FallbackStrategy.MAJORITY,
            fallback_verdict=majority_verdict,
            confidence=confidence,
            reason=f"Majority fallback: {majority_count}/{len(successful)} successful critics voted '{majority_verdict}'",
            metadata={
                'verdict_distribution': verdict_counts,
                'successful_critics': len(successful),
                'total_critics': len(critic_outputs)
            }
        )

    def _create_audit_bundle(
        self,
        critic_outputs: List[Dict[str, Any]],
        trigger: FallbackTrigger,
        fallback_result: FallbackResult,
        context: Dict[str, Any],
        elapsed_time_ms: Optional[float],
        validation_errors: Optional[List[Any]],
        decision_time_ms: float
    ) -> FallbackEvidenceBundle:
        """
        Create FallbackEvidenceBundle for audit trail.

        Task 6.2: Provides complete auditability for fallback decisions

        Args:
            critic_outputs: List of critic outputs
            trigger: Fallback trigger
            fallback_result: The fallback result
            context: Additional context
            elapsed_time_ms: Time elapsed in milliseconds
            validation_errors: List of validation errors
            decision_time_ms: Time taken to make decision

        Returns:
            FallbackEvidenceBundle for logging and audit
        """
        # Map FallbackTrigger to FallbackType
        trigger_to_type = {
            FallbackTrigger.ALL_CRITICS_FAILED: FallbackType.ALL_CRITICS_FAILED,
            FallbackTrigger.MAJORITY_CRITICS_FAILED: FallbackType.MAJORITY_CRITICS_FAILED,
            FallbackTrigger.CRITICAL_CRITIC_FAILED: FallbackType.CRITICAL_CRITIC_FAILED,
            FallbackTrigger.TIMEOUT: FallbackType.TIMEOUT_EXCEEDED,
            FallbackTrigger.HIGH_ERROR_RATE: FallbackType.HIGH_ERROR_RATE,
            FallbackTrigger.INSUFFICIENT_CONFIDENCE: FallbackType.INSUFFICIENT_CONFIDENCE,
            FallbackTrigger.MANUAL_OVERRIDE: FallbackType.MANUAL_OVERRIDE
        }
        fallback_type = trigger_to_type.get(trigger, FallbackType.SYSTEM_ERROR)

        # Detect schema validation type if validation_errors present
        if validation_errors and len(validation_errors) > 0:
            fallback_type = FallbackType.SCHEMA_VALIDATION_FAILED

        # Extract failed critics
        failed_critics = []
        successful_outputs = []
        for critic_output in critic_outputs:
            if critic_output.get('verdict') == 'ERROR':
                # Determine error type
                error_type = critic_output.get('error_type', 'unknown')
                error = critic_output.get('error')
                if isinstance(error, (CriticTimeoutException, TimeoutError)):
                    error_type = 'timeout'
                elif error_type == 'unknown' and error:
                    error_type = type(error).__name__

                failed_critic = FailedCriticInfo(
                    critic_name=critic_output.get('critic', 'unknown'),
                    failure_reason=critic_output.get('justification', 'Unknown error'),
                    error_type=error_type,
                    error_message=str(error) if error else None,
                    stack_trace=critic_output.get('stack_trace'),
                    attempted_retries=critic_output.get('retries', 0)
                )
                failed_critics.append(failed_critic)
            else:
                successful_outputs.append(critic_output)

        # Build system state
        total_expected = context.get('total_critics_expected', len(critic_outputs))
        system_state = SystemStateAtTrigger(
            total_critics_expected=total_expected,
            total_critics_attempted=len(critic_outputs),
            total_critics_succeeded=len(successful_outputs),
            total_critics_failed=len(failed_critics),
            elapsed_time_ms=elapsed_time_ms or 0.0,
            timeout_threshold_ms=self.timeout_threshold_ms,
            system_version=context.get('system_version', '1.0.0'),
            environment=context.get('environment', 'production'),
            active_critics=[c.get('critic', 'unknown') for c in critic_outputs],
            request_id=context.get('request_id'),
            correlation_id=context.get('correlation_id'),
            user_id=context.get('user_id'),
            session_id=context.get('session_id'),
            additional_context=context
        )

        # Build fallback decision
        fallback_decision = FallbackDecision(
            verdict=fallback_result.fallback_verdict,
            confidence=fallback_result.confidence,
            strategy_used=fallback_result.fallback_strategy.value,
            reason=fallback_result.reason,
            is_safe_default=fallback_result.fallback_strategy in [
                FallbackStrategy.CONSERVATIVE,
                FallbackStrategy.ESCALATE,
                FallbackStrategy.FAIL_SAFE
            ],
            requires_human_review=(
                fallback_result.fallback_strategy == FallbackStrategy.ESCALATE or
                fallback_result.confidence < 0.5
            ),
            decision_time_ms=decision_time_ms
        )

        # Collect warnings and errors
        warnings = []
        errors = []
        if validation_errors:
            for ve in validation_errors:
                severity = getattr(ve, 'severity', 'error')
                message = getattr(ve, 'error', str(ve))
                if severity == 'error':
                    errors.append(message)
                else:
                    warnings.append(message)

        # Create bundle
        bundle = FallbackEvidenceBundle(
            fallback_type=fallback_type,
            failed_critics=failed_critics,
            system_state_at_trigger=system_state,
            fallback_decision=fallback_decision,
            input_text=context.get('input_text'),
            input_context=context.get('input_context', {}),
            successful_critic_outputs=successful_outputs,
            warnings=warnings,
            errors=errors,
            metadata={
                'trigger': trigger.value,
                'fallback_result': fallback_result.to_dict()
            }
        )

        logger.info(f"Created fallback audit bundle {bundle.bundle_id} for {fallback_type.value}")
        return bundle


# Convenience functions

def create_fallback_engine(
    strategy: str = "conservative",
    error_threshold: float = 0.5
) -> FallbackEngine:
    """
    Create a fallback engine with simple configuration.

    Args:
        strategy: Fallback strategy name
        error_threshold: Error rate threshold

    Returns:
        Configured FallbackEngine
    """
    strategy_map = {
        'conservative': FallbackStrategy.CONSERVATIVE,
        'permissive': FallbackStrategy.PERMISSIVE,
        'escalate': FallbackStrategy.ESCALATE,
        'fail_safe': FallbackStrategy.FAIL_SAFE,
        'majority': FallbackStrategy.MAJORITY
    }

    return FallbackEngine(
        default_strategy=strategy_map.get(strategy, FallbackStrategy.CONSERVATIVE),
        error_rate_threshold=error_threshold
    )
