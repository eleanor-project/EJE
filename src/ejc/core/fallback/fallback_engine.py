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

from ..evidence_normalizer import EvidenceBundle, CriticOutput
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
        safe_default_verdict: str = "REVIEW"
    ):
        """
        Initialize fallback engine.

        Args:
            default_strategy: Default fallback strategy
            error_rate_threshold: Threshold for high error rate trigger
            min_successful_critics: Minimum successful critics required
            critical_critics: List of critic names that are critical
            safe_default_verdict: Safe default verdict for FAIL_SAFE strategy
        """
        self.default_strategy = default_strategy
        self.error_rate_threshold = error_rate_threshold
        self.min_successful_critics = min_successful_critics
        self.critical_critics = set(critical_critics or [])
        self.safe_default_verdict = safe_default_verdict

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
        aggregation_result: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[FallbackTrigger], str]:
        """
        Determine if fallback logic should be triggered.

        Args:
            critic_outputs: List of critic output dictionaries
            aggregation_result: Optional aggregation result

        Returns:
            Tuple of (should_fallback, trigger, reason)
        """
        if not critic_outputs:
            return True, FallbackTrigger.ALL_CRITICS_FAILED, "No critic outputs available"

        # Count successes and failures
        total = len(critic_outputs)
        errors = sum(1 for c in critic_outputs if c.get('verdict') == 'ERROR')
        successful = total - errors

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
        context: Optional[Dict[str, Any]] = None
    ) -> FallbackResult:
        """
        Apply fallback logic with specified strategy.

        Args:
            critic_outputs: List of critic outputs (including failed ones)
            trigger: Fallback trigger condition
            strategy: Fallback strategy (uses default if None)
            context: Additional context for fallback decision

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
            return handler(critic_outputs, trigger, context or {})
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
