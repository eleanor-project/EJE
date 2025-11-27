"""
Enhanced human review module.

Provides escalation bundles, dissent analysis, templated feedback forms,
and review dashboard functionality.
"""

from .escalation import (
    EscalationBundle,
    EscalationBundleBuilder,
    CriticVote,
    DissentAnalysis,
    SimilarCase
)

from .feedback import (
    ReviewFeedback,
    FeedbackQuestion,
    FeedbackResponse,
    FeedbackFormBuilder,
    FeedbackAggregator,
    FeedbackType,
    VerdictOption
)

from .dashboard import (
    ReviewDashboard,
    ReviewQueueItem,
    ReviewQueueStats,
    ReviewerStats,
    QueueFilter,
    QueueSortOrder
)

__all__ = [
    # Escalation
    "EscalationBundle",
    "EscalationBundleBuilder",
    "CriticVote",
    "DissentAnalysis",
    "SimilarCase",
    # Feedback
    "ReviewFeedback",
    "FeedbackQuestion",
    "FeedbackResponse",
    "FeedbackFormBuilder",
    "FeedbackAggregator",
    "FeedbackType",
    "VerdictOption",
    # Dashboard
    "ReviewDashboard",
    "ReviewQueueItem",
    "ReviewQueueStats",
    "ReviewerStats",
    "QueueFilter",
    "QueueSortOrder"
]
