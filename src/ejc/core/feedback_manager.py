"""
Feedback Management Module for EJE.
Handles human feedback signals, feedback loops, and integration with retraining.
"""
import datetime
import json
import os
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback that can be provided."""
    APPROVAL = "approval"  # Human approves the decision
    REJECTION = "rejection"  # Human rejects the decision
    CORRECTION = "correction"  # Human provides corrected verdict
    COMMENT = "comment"  # Human adds commentary
    RATING = "rating"  # Numeric rating (1-5)


class FeedbackSource(Enum):
    """Source of the feedback."""
    HUMAN_REVIEWER = "human_reviewer"
    DASHBOARD_UI = "dashboard_ui"
    API_ENDPOINT = "api_endpoint"
    AUTOMATED_AUDIT = "automated_audit"


@dataclass
class FeedbackSignal:
    """Structured feedback signal from humans or automated systems."""

    request_id: str
    feedback_type: FeedbackType
    source: FeedbackSource
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

    # Original decision info
    original_verdict: Optional[str] = None
    original_confidence: Optional[float] = None

    # Feedback data
    corrected_verdict: Optional[str] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    reviewer_id: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['feedback_type'] = self.feedback_type.value
        data['source'] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackSignal':
        """Create from dictionary."""
        data['feedback_type'] = FeedbackType(data['feedback_type'])
        data['source'] = FeedbackSource(data['source'])
        return cls(**data)


class FeedbackHook:
    """
    Abstract base for feedback hooks.
    Hooks are called when feedback is received.
    """

    def __call__(self, feedback: FeedbackSignal) -> None:
        """Process feedback signal."""
        raise NotImplementedError


class LoggingFeedbackHook(FeedbackHook):
    """Simple hook that logs feedback to file."""

    def __init__(self, log_path: str):
        self.log_path = log_path

    def __call__(self, feedback: FeedbackSignal) -> None:
        """Log feedback to JSONL file."""
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(feedback.to_dict()) + '\n')
            logger.info(f"Logged feedback for request {feedback.request_id}")
        except Exception as e:
            logger.error(f"Failed to log feedback: {e}")


class RetrainingFeedbackHook(FeedbackHook):
    """Hook that triggers retraining based on feedback."""

    def __init__(self, retraining_manager):
        self.retraining_manager = retraining_manager
        self.feedback_buffer: List[FeedbackSignal] = []
        self.buffer_size = 10

    def __call__(self, feedback: FeedbackSignal) -> None:
        """Add feedback to retraining buffer."""
        self.feedback_buffer.append(feedback)

        if len(self.feedback_buffer) >= self.buffer_size:
            self._trigger_retraining()

    def _trigger_retraining(self):
        """Process buffered feedback for retraining."""
        logger.info(f"Triggering retraining with {len(self.feedback_buffer)} feedback signals")

        # Analyze feedback patterns
        corrections = [f for f in self.feedback_buffer if f.feedback_type == FeedbackType.CORRECTION]
        rejections = [f for f in self.feedback_buffer if f.feedback_type == FeedbackType.REJECTION]

        # Adjust critic weights based on feedback
        for correction in corrections:
            # If a critic was wrong, decrease its weight
            # (This would need access to the original critic outputs)
            logger.info(f"Processing correction for request {correction.request_id}")

        # Clear buffer
        self.feedback_buffer.clear()


class MetricsFeedbackHook(FeedbackHook):
    """Hook that updates metrics based on feedback."""

    def __init__(self):
        self.metrics = {
            'total_feedback': 0,
            'approvals': 0,
            'rejections': 0,
            'corrections': 0,
            'average_rating': 0.0,
            'rating_count': 0
        }

    def __call__(self, feedback: FeedbackSignal) -> None:
        """Update metrics based on feedback."""
        self.metrics['total_feedback'] += 1

        if feedback.feedback_type == FeedbackType.APPROVAL:
            self.metrics['approvals'] += 1
        elif feedback.feedback_type == FeedbackType.REJECTION:
            self.metrics['rejections'] += 1
        elif feedback.feedback_type == FeedbackType.CORRECTION:
            self.metrics['corrections'] += 1

        if feedback.rating is not None:
            # Update average rating
            old_avg = self.metrics['average_rating']
            old_count = self.metrics['rating_count']
            new_count = old_count + 1
            new_avg = (old_avg * old_count + feedback.rating) / new_count
            self.metrics['average_rating'] = new_avg
            self.metrics['rating_count'] = new_count

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()


class FeedbackManager:
    """
    Central manager for handling feedback signals.
    Coordinates feedback hooks and storage.
    """

    def __init__(self, audit_logger, data_path: str = "./eleanor_data"):
        """
        Initialize feedback manager.

        Args:
            audit_logger: AuditLogger instance for storing feedback
            data_path: Path for feedback data storage
        """
        self.audit_logger = audit_logger
        self.data_path = data_path
        self.hooks: List[FeedbackHook] = []

        os.makedirs(self.data_path, exist_ok=True)

        # Default hooks
        self.logging_hook = LoggingFeedbackHook(f"{data_path}/feedback.jsonl")
        self.metrics_hook = MetricsFeedbackHook()

        self.add_hook(self.logging_hook)
        self.add_hook(self.metrics_hook)

    def add_hook(self, hook: FeedbackHook):
        """Register a feedback hook."""
        self.hooks.append(hook)
        logger.info(f"Registered feedback hook: {hook.__class__.__name__}")

    def remove_hook(self, hook: FeedbackHook):
        """Unregister a feedback hook."""
        self.hooks.remove(hook)
        logger.info(f"Unregistered feedback hook: {hook.__class__.__name__}")

    def submit_feedback(self, feedback: FeedbackSignal) -> None:
        """
        Submit feedback signal.

        Args:
            feedback: FeedbackSignal instance
        """
        logger.info(f"Received feedback for request {feedback.request_id}: {feedback.feedback_type.value}")

        # Store in audit log
        try:
            self.audit_logger.log_feedback(feedback.request_id, feedback.to_dict())
        except Exception as e:
            logger.error(f"Failed to log feedback to audit: {e}")

        # Call all hooks
        for hook in self.hooks:
            try:
                hook(feedback)
            except Exception as e:
                logger.error(f"Error in feedback hook {hook.__class__.__name__}: {e}")

    def create_feedback(
        self,
        request_id: str,
        feedback_type: FeedbackType,
        source: FeedbackSource = FeedbackSource.DASHBOARD_UI,
        **kwargs
    ) -> FeedbackSignal:
        """
        Convenience method to create and submit feedback.

        Args:
            request_id: ID of the decision being reviewed
            feedback_type: Type of feedback
            source: Source of the feedback
            **kwargs: Additional feedback fields

        Returns:
            Created FeedbackSignal
        """
        feedback = FeedbackSignal(
            request_id=request_id,
            feedback_type=feedback_type,
            source=source,
            **kwargs
        )
        self.submit_feedback(feedback)
        return feedback

    def get_metrics(self) -> Dict[str, Any]:
        """Get feedback metrics."""
        return self.metrics_hook.get_metrics()

    def get_feedback_for_request(self, request_id: Optional[str]) -> List[FeedbackSignal]:
        """
        Retrieve all feedback for a specific request.

        Args:
            request_id: Request ID to look up. If None, returns all feedback.

        Returns:
            List of FeedbackSignals
        """
        feedbacks: List[FeedbackSignal] = []

        # Prefer the structured audit log when available
        try:
            if hasattr(self.audit_logger, "get_feedback"):
                for entry in self.audit_logger.get_feedback(request_id):
                    feedbacks.append(FeedbackSignal.from_dict(entry))
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Error retrieving feedback from audit log: {e}")

        # Fallback to local feedback log file
        if not feedbacks:
            try:
                feedbacks.extend(self._load_feedback_file(request_id))
            except Exception as e:  # pragma: no cover - defensive logging
                logger.error(f"Error retrieving feedback from file: {e}")

        return feedbacks

    def _load_feedback_file(self, request_id: Optional[str] = None) -> List[FeedbackSignal]:
        """Load feedback from the local JSONL log."""
        path = f"{self.data_path}/feedback.jsonl"
        if not os.path.exists(path):
            return []

        feedbacks: List[FeedbackSignal] = []
        with open(path, "r") as f:
            for line in f:
                data = json.loads(line)
                if request_id and data.get("request_id") != request_id:
                    continue
                feedbacks.append(FeedbackSignal.from_dict(data))

        return feedbacks


class FeedbackAnalyzer:
    """Analyzes feedback patterns to identify issues and improvements."""

    def __init__(self, feedback_manager: FeedbackManager):
        self.feedback_manager = feedback_manager

    def analyze_critic_accuracy(self, critic_name: str) -> Dict[str, Any]:
        """
        Analyze accuracy of a specific critic based on feedback.

        Args:
            critic_name: Name of the critic to analyze

        Returns:
            Dictionary with accuracy metrics
        """
        feedbacks = self._load_all_feedback()
        critic_feedback = []
        for feedback in feedbacks:
            metadata = feedback.metadata or {}
            if metadata.get("critic") == critic_name or metadata.get("critic_name") == critic_name or metadata.get("target") == critic_name:
                critic_feedback.append(feedback)

        total = len(critic_feedback)
        if total == 0:
            return {
                'critic': critic_name,
                'agreement_rate': 1.0,
                'correction_count': 0,
                'needs_retraining': False
            }

        approvals = sum(1 for f in critic_feedback if f.feedback_type == FeedbackType.APPROVAL)
        rejections = sum(1 for f in critic_feedback if f.feedback_type == FeedbackType.REJECTION)
        corrections = sum(1 for f in critic_feedback if f.feedback_type == FeedbackType.CORRECTION)

        agreement_rate = approvals / total
        negative_ratio = (rejections + corrections) / total

        return {
            'critic': critic_name,
            'agreement_rate': agreement_rate,
            'correction_count': corrections,
            'needs_retraining': negative_ratio >= 0.3
        }

    def identify_drift(self) -> List[Dict[str, Any]]:
        """
        Identify critics showing performance drift based on feedback.

        Returns:
            List of critics with drift indicators
        """
        feedbacks = self._load_all_feedback()
        drift_indicators: Dict[str, Dict[str, Any]] = {}

        for feedback in feedbacks:
            metadata = feedback.metadata or {}
            critic_name = metadata.get("critic") or metadata.get("critic_name")
            if not critic_name:
                continue

            stats = drift_indicators.setdefault(critic_name, {"total": 0, "negative": 0})
            stats["total"] += 1
            if feedback.feedback_type in {FeedbackType.REJECTION, FeedbackType.CORRECTION}:
                stats["negative"] += 1

        drifting: List[Dict[str, Any]] = []
        for critic, stats in drift_indicators.items():
            if stats["total"] == 0:
                continue
            negative_ratio = stats["negative"] / stats["total"]
            if negative_ratio >= 0.4:
                drifting.append({
                    "critic": critic,
                    "negative_ratio": negative_ratio,
                    "signals": stats["total"]
                })

        return drifting

    def recommend_weight_adjustments(self) -> Dict[str, float]:
        """
        Recommend critic weight adjustments based on feedback patterns.

        Returns:
            Dictionary mapping critic names to recommended weights
        """
        feedbacks = self._load_all_feedback()
        critic_stats: Dict[str, Dict[str, int]] = {}

        for feedback in feedbacks:
            metadata = feedback.metadata or {}
            critic_name = metadata.get("critic") or metadata.get("critic_name")
            if not critic_name:
                continue

            stats = critic_stats.setdefault(critic_name, {"total": 0, "negative": 0})
            stats["total"] += 1
            if feedback.feedback_type in {FeedbackType.REJECTION, FeedbackType.CORRECTION}:
                stats["negative"] += 1

        recommendations: Dict[str, float] = {}
        for critic, stats in critic_stats.items():
            if stats["total"] == 0:
                continue
            negative_ratio = stats["negative"] / stats["total"]
            # Down-weight critics with higher negative ratios; clamp between 0.1 and 1.0
            recommendations[critic] = max(0.1, round(1.0 - negative_ratio, 2))

        return recommendations

    def _load_all_feedback(self) -> List[FeedbackSignal]:
        """Load all feedback signals from available stores."""
        signals: List[FeedbackSignal] = []

        try:
            signals.extend(self.get_feedback_for_request(request_id=None))
        except TypeError:
            # get_feedback_for_request expects a request_id; fall back to file scan
            signals.extend(self._load_feedback_file())

        # Deduplicate by request_id + timestamp to avoid double counting
        seen = set()
        unique_signals: List[FeedbackSignal] = []
        for signal in signals:
            key = (signal.request_id, signal.timestamp, signal.feedback_type.value)
            if key in seen:
                continue
            seen.add(key)
            unique_signals.append(signal)

        return unique_signals


# Convenience functions for common feedback scenarios

def approve_decision(
    feedback_manager: FeedbackManager,
    request_id: str,
    reviewer_id: str,
    comment: Optional[str] = None
) -> FeedbackSignal:
    """Quick approval of a decision."""
    return feedback_manager.create_feedback(
        request_id=request_id,
        feedback_type=FeedbackType.APPROVAL,
        source=FeedbackSource.HUMAN_REVIEWER,
        reviewer_id=reviewer_id,
        comment=comment
    )


def reject_decision(
    feedback_manager: FeedbackManager,
    request_id: str,
    reviewer_id: str,
    reason: str
) -> FeedbackSignal:
    """Quick rejection of a decision."""
    return feedback_manager.create_feedback(
        request_id=request_id,
        feedback_type=FeedbackType.REJECTION,
        source=FeedbackSource.HUMAN_REVIEWER,
        reviewer_id=reviewer_id,
        comment=reason
    )


def correct_decision(
    feedback_manager: FeedbackManager,
    request_id: str,
    original_verdict: str,
    corrected_verdict: str,
    reviewer_id: str,
    reason: str
) -> FeedbackSignal:
    """Provide corrected verdict for a decision."""
    return feedback_manager.create_feedback(
        request_id=request_id,
        feedback_type=FeedbackType.CORRECTION,
        source=FeedbackSource.HUMAN_REVIEWER,
        original_verdict=original_verdict,
        corrected_verdict=corrected_verdict,
        reviewer_id=reviewer_id,
        comment=reason
    )


def rate_decision(
    feedback_manager: FeedbackManager,
    request_id: str,
    rating: int,
    reviewer_id: str,
    comment: Optional[str] = None
) -> FeedbackSignal:
    """Rate a decision (1-5 stars)."""
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")

    return feedback_manager.create_feedback(
        request_id=request_id,
        feedback_type=FeedbackType.RATING,
        source=FeedbackSource.DASHBOARD_UI,
        rating=rating,
        reviewer_id=reviewer_id,
        comment=comment
    )
