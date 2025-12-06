"""
Fallback Evidence Bundle Schema

Task 6.1: Fallback Evidence Bundle
Schema for capturing fallback events, including reasons and fallback decision.

This module defines the data structures for documenting fallback scenarios,
providing complete audit trails and system state snapshots when fallbacks occur.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class FallbackType(Enum):
    """Types of fallback scenarios"""
    ALL_CRITICS_FAILED = "all_critics_failed"
    MAJORITY_CRITICS_FAILED = "majority_critics_failed"
    CRITICAL_CRITIC_FAILED = "critical_critic_failed"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    INSUFFICIENT_CONFIDENCE = "insufficient_confidence"
    HIGH_ERROR_RATE = "high_error_rate"
    MANUAL_OVERRIDE = "manual_override"
    SYSTEM_ERROR = "system_error"


@dataclass
class FailedCriticInfo:
    """Information about a failed critic"""
    critic_name: str
    failure_reason: str
    error_type: str  # e.g., 'timeout', 'exception', 'validation_error'
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attempted_retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'critic_name': self.critic_name,
            'failure_reason': self.failure_reason,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'timestamp': self.timestamp.isoformat(),
            'attempted_retries': self.attempted_retries
        }


@dataclass
class SystemStateAtTrigger:
    """System state snapshot when fallback was triggered"""
    # System metrics
    total_critics_expected: int
    total_critics_attempted: int
    total_critics_succeeded: int
    total_critics_failed: int

    # Timing information
    elapsed_time_ms: float
    timeout_threshold_ms: Optional[float] = None

    # Resource utilization
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # System configuration
    system_version: str = "1.0.0"
    environment: str = "production"

    # Active configuration
    active_critics: List[str] = field(default_factory=list)
    disabled_critics: List[str] = field(default_factory=list)

    # Request metadata
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Additional context
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_critics_expected': self.total_critics_expected,
            'total_critics_attempted': self.total_critics_attempted,
            'total_critics_succeeded': self.total_critics_succeeded,
            'total_critics_failed': self.total_critics_failed,
            'elapsed_time_ms': self.elapsed_time_ms,
            'timeout_threshold_ms': self.timeout_threshold_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'system_version': self.system_version,
            'environment': self.environment,
            'active_critics': self.active_critics,
            'disabled_critics': self.disabled_critics,
            'request_id': self.request_id,
            'correlation_id': self.correlation_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'additional_context': self.additional_context
        }


@dataclass
class FallbackDecision:
    """The fallback decision that was made"""
    verdict: str  # The fallback verdict (DENY, ALLOW, REVIEW, ESCALATE)
    confidence: float  # Confidence in the fallback decision (0.0-1.0)
    strategy_used: str  # Strategy applied (conservative, permissive, escalate, etc.)
    reason: str  # Human-readable reason for the decision

    # Alternative verdicts considered
    alternative_verdicts: List[str] = field(default_factory=list)

    # Safety checks
    is_safe_default: bool = True
    requires_human_review: bool = False

    # Timing
    decision_timestamp: datetime = field(default_factory=datetime.utcnow)
    decision_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'verdict': self.verdict,
            'confidence': self.confidence,
            'strategy_used': self.strategy_used,
            'reason': self.reason,
            'alternative_verdicts': self.alternative_verdicts,
            'is_safe_default': self.is_safe_default,
            'requires_human_review': self.requires_human_review,
            'decision_timestamp': self.decision_timestamp.isoformat(),
            'decision_time_ms': self.decision_time_ms
        }


@dataclass
class FallbackEvidenceBundle:
    """
    Complete evidence bundle for a fallback scenario.

    Task 6.1: Schema for capturing fallback events

    This class provides a structured, serializable record of:
    - What triggered the fallback (fallback_type)
    - Which critics failed (failed_critics)
    - System state when fallback occurred (system_state_at_trigger)
    - The fallback decision made
    - Complete audit trail
    """

    # Required fields per Task 6.1
    fallback_type: FallbackType
    failed_critics: List[FailedCriticInfo]
    system_state_at_trigger: SystemStateAtTrigger

    # Fallback decision
    fallback_decision: FallbackDecision

    # Identification
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0.0"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Input context (what was being evaluated when fallback occurred)
    input_text: Optional[str] = None
    input_context: Dict[str, Any] = field(default_factory=dict)

    # Successful critic outputs (if any)
    successful_critic_outputs: List[Dict[str, Any]] = field(default_factory=list)

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Recovery attempts
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_details: Optional[str] = None

    # Audit trail
    created_by: str = "fallback_engine"
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'bundle_id': self.bundle_id,
            'version': self.version,
            'timestamp': self.timestamp.isoformat(),
            'fallback_type': self.fallback_type.value,
            'failed_critics': [fc.to_dict() for fc in self.failed_critics],
            'system_state_at_trigger': self.system_state_at_trigger.to_dict(),
            'fallback_decision': self.fallback_decision.to_dict(),
            'input_text': self.input_text,
            'input_context': self.input_context,
            'successful_critic_outputs': self.successful_critic_outputs,
            'warnings': self.warnings,
            'errors': self.errors,
            'recovery_attempted': self.recovery_attempted,
            'recovery_successful': self.recovery_successful,
            'recovery_details': self.recovery_details,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FallbackEvidenceBundle':
        """
        Create FallbackEvidenceBundle from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            FallbackEvidenceBundle instance
        """
        # Parse fallback_type
        fallback_type = FallbackType(data['fallback_type'])

        # Parse failed_critics
        failed_critics = [
            FailedCriticInfo(
                critic_name=fc['critic_name'],
                failure_reason=fc['failure_reason'],
                error_type=fc['error_type'],
                error_message=fc.get('error_message'),
                stack_trace=fc.get('stack_trace'),
                timestamp=datetime.fromisoformat(fc['timestamp']) if isinstance(fc.get('timestamp'), str) else fc.get('timestamp', datetime.utcnow()),
                attempted_retries=fc.get('attempted_retries', 0)
            )
            for fc in data['failed_critics']
        ]

        # Parse system_state_at_trigger
        ss = data['system_state_at_trigger']
        system_state = SystemStateAtTrigger(
            total_critics_expected=ss['total_critics_expected'],
            total_critics_attempted=ss['total_critics_attempted'],
            total_critics_succeeded=ss['total_critics_succeeded'],
            total_critics_failed=ss['total_critics_failed'],
            elapsed_time_ms=ss['elapsed_time_ms'],
            timeout_threshold_ms=ss.get('timeout_threshold_ms'),
            memory_usage_mb=ss.get('memory_usage_mb'),
            cpu_usage_percent=ss.get('cpu_usage_percent'),
            system_version=ss.get('system_version', '1.0.0'),
            environment=ss.get('environment', 'production'),
            active_critics=ss.get('active_critics', []),
            disabled_critics=ss.get('disabled_critics', []),
            request_id=ss.get('request_id'),
            correlation_id=ss.get('correlation_id'),
            user_id=ss.get('user_id'),
            session_id=ss.get('session_id'),
            additional_context=ss.get('additional_context', {})
        )

        # Parse fallback_decision
        fd = data['fallback_decision']
        fallback_decision = FallbackDecision(
            verdict=fd['verdict'],
            confidence=fd['confidence'],
            strategy_used=fd['strategy_used'],
            reason=fd['reason'],
            alternative_verdicts=fd.get('alternative_verdicts', []),
            is_safe_default=fd.get('is_safe_default', True),
            requires_human_review=fd.get('requires_human_review', False),
            decision_timestamp=datetime.fromisoformat(fd['decision_timestamp']) if isinstance(fd.get('decision_timestamp'), str) else fd.get('decision_timestamp', datetime.utcnow()),
            decision_time_ms=fd.get('decision_time_ms', 0.0)
        )

        return cls(
            fallback_type=fallback_type,
            failed_critics=failed_critics,
            system_state_at_trigger=system_state,
            fallback_decision=fallback_decision,
            bundle_id=data.get('bundle_id', str(uuid.uuid4())),
            version=data.get('version', '1.0.0'),
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data.get('timestamp'), str) else data.get('timestamp', datetime.utcnow()),
            input_text=data.get('input_text'),
            input_context=data.get('input_context', {}),
            successful_critic_outputs=data.get('successful_critic_outputs', []),
            warnings=data.get('warnings', []),
            errors=data.get('errors', []),
            recovery_attempted=data.get('recovery_attempted', False),
            recovery_successful=data.get('recovery_successful', False),
            recovery_details=data.get('recovery_details'),
            created_by=data.get('created_by', 'fallback_engine'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.utcnow()),
            metadata=data.get('metadata', {})
        )

    def is_critical(self) -> bool:
        """Check if this fallback event is critical (requires immediate attention)"""
        return (
            self.fallback_type in [
                FallbackType.ALL_CRITICS_FAILED,
                FallbackType.CRITICAL_CRITIC_FAILED,
                FallbackType.SYSTEM_ERROR
            ] or
            self.fallback_decision.requires_human_review or
            self.system_state_at_trigger.total_critics_succeeded == 0
        )

    def get_failure_rate(self) -> float:
        """Calculate the failure rate of critics"""
        total = self.system_state_at_trigger.total_critics_attempted
        if total == 0:
            return 0.0
        failed = self.system_state_at_trigger.total_critics_failed
        return failed / total

    def get_summary(self) -> str:
        """Get a human-readable summary of this fallback event"""
        return (
            f"Fallback triggered: {self.fallback_type.value} | "
            f"{len(self.failed_critics)} critics failed | "
            f"Decision: {self.fallback_decision.verdict} "
            f"({self.fallback_decision.confidence:.0%} confidence) | "
            f"Strategy: {self.fallback_decision.strategy_used}"
        )


# Export
__all__ = [
    'FallbackType',
    'FailedCriticInfo',
    'SystemStateAtTrigger',
    'FallbackDecision',
    'FallbackEvidenceBundle'
]
