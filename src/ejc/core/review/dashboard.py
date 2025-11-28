"""
Review dashboard data models and utilities.

Provides data structures for building interactive review dashboards,
including queue management, statistics, and filtering.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class QueueFilter(Enum):
    """Filter options for review queue."""

    ALL = "all"
    CRITICAL = "critical"
    HIGH_PRIORITY = "high_priority"
    HIGH_DISSENT = "high_dissent"
    PRIVACY_SENSITIVE = "privacy_sensitive"
    OVERDUE = "overdue"
    ASSIGNED_TO_ME = "assigned_to_me"


class QueueSortOrder(Enum):
    """Sort order for review queue."""

    PRIORITY_DESC = "priority_desc"
    DISSENT_DESC = "dissent_desc"
    OLDEST_FIRST = "oldest_first"
    NEWEST_FIRST = "newest_first"
    DEADLINE_SOON = "deadline_soon"


@dataclass
class ReviewQueueItem:
    """Single item in review queue."""

    bundle_id: str
    case_id: str
    priority: str
    dissent_index: float
    disagreement_type: str
    escalated_at: datetime
    deadline: Optional[datetime]
    prompt_preview: str  # First 100 chars
    majority_verdict: str
    split_ratio: str
    num_similar_precedents: int
    is_privacy_sensitive: bool = False
    is_safety_critical: bool = False
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_overdue(self) -> bool:
        """Check if review is overdue."""
        if not self.deadline:
            return False
        return datetime.utcnow() > self.deadline

    def time_until_deadline(self) -> Optional[timedelta]:
        """Get time remaining until deadline."""
        if not self.deadline:
            return None
        return self.deadline - datetime.utcnow()


@dataclass
class ReviewQueueStats:
    """Statistics for review queue."""

    total_pending: int
    critical_count: int
    high_priority_count: int
    overdue_count: int
    avg_dissent_index: float
    avg_time_in_queue: timedelta
    by_disagreement_type: Dict[str, int]
    by_priority: Dict[str, int]
    by_majority_verdict: Dict[str, int]


@dataclass
class ReviewerStats:
    """Statistics for individual reviewer."""

    reviewer_id: str
    total_reviews: int
    avg_confidence: float
    avg_review_time: timedelta
    verdict_distribution: Dict[str, int]
    agreement_with_critics: float  # % of times agrees with majority
    override_rate: float  # % of times overrides critic consensus
    reviews_this_week: int
    reviews_this_month: int


class ReviewDashboard:
    """
    Review dashboard for managing human review queue.

    Provides filtering, sorting, statistics, and assignment management
    for escalated cases requiring human review.
    """

    def __init__(self, storage_backend: Optional[Any] = None):
        """
        Initialize review dashboard.

        Args:
            storage_backend: Optional storage for persisting queue state
        """
        self.storage = storage_backend
        self.queue: List[ReviewQueueItem] = []
        self.completed_reviews: List[Dict] = []

    def add_to_queue(self, bundle: Any) -> ReviewQueueItem:
        """
        Add escalation bundle to review queue.

        Args:
            bundle: EscalationBundle to add

        Returns:
            ReviewQueueItem created
        """
        # Extract prompt preview
        prompt = bundle.input_data.get("prompt", "")
        prompt_preview = prompt[:100] + ("..." if len(prompt) > 100 else "")

        # Extract context flags
        context = bundle.input_data.get("context", {})
        is_privacy_sensitive = context.get("privacy_sensitive", False)
        is_safety_critical = context.get("safety_critical", False)

        # Create queue item
        item = ReviewQueueItem(
            bundle_id=bundle.bundle_id,
            case_id=bundle.case_id,
            priority=bundle.priority,
            dissent_index=bundle.dissent_analysis.dissent_index,
            disagreement_type=bundle.dissent_analysis.disagreement_type,
            escalated_at=bundle.escalated_at,
            deadline=bundle.review_deadline,
            prompt_preview=prompt_preview,
            majority_verdict=bundle.dissent_analysis.majority_verdict,
            split_ratio=bundle.dissent_analysis.split_ratio,
            num_similar_precedents=len(bundle.similar_precedents),
            is_privacy_sensitive=is_privacy_sensitive,
            is_safety_critical=is_safety_critical,
            metadata={
                "num_critics": bundle.metadata.get("num_critics", 0),
                "conflicting_principles": bundle.dissent_analysis.conflicting_principles
            }
        )

        self.queue.append(item)

        if self.storage:
            self._persist_queue()

        return item

    def get_queue(
        self,
        filter_by: QueueFilter = QueueFilter.ALL,
        sort_by: QueueSortOrder = QueueSortOrder.PRIORITY_DESC,
        assigned_to: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ReviewQueueItem]:
        """
        Get filtered and sorted review queue.

        Args:
            filter_by: Filter to apply
            sort_by: Sort order
            assigned_to: Filter by assignee
            limit: Maximum number of items to return

        Returns:
            Filtered and sorted queue items
        """
        # Apply filters
        filtered = self._apply_filter(self.queue, filter_by, assigned_to)

        # Apply sort
        sorted_queue = self._apply_sort(filtered, sort_by)

        # Apply limit
        if limit:
            sorted_queue = sorted_queue[:limit]

        return sorted_queue

    def _apply_filter(
        self,
        items: List[ReviewQueueItem],
        filter_by: QueueFilter,
        assigned_to: Optional[str]
    ) -> List[ReviewQueueItem]:
        """Apply queue filter."""
        filtered = items

        # Apply filter
        if filter_by == QueueFilter.CRITICAL:
            filtered = [i for i in filtered if i.priority == "critical"]
        elif filter_by == QueueFilter.HIGH_PRIORITY:
            filtered = [i for i in filtered if i.priority in ["critical", "high"]]
        elif filter_by == QueueFilter.HIGH_DISSENT:
            filtered = [i for i in filtered if i.dissent_index >= 0.7]
        elif filter_by == QueueFilter.PRIVACY_SENSITIVE:
            filtered = [i for i in filtered if i.is_privacy_sensitive]
        elif filter_by == QueueFilter.OVERDUE:
            filtered = [i for i in filtered if i.is_overdue()]
        elif filter_by == QueueFilter.ASSIGNED_TO_ME:
            if assigned_to:
                filtered = [i for i in filtered if i.assigned_to == assigned_to]

        return filtered

    def _apply_sort(
        self,
        items: List[ReviewQueueItem],
        sort_by: QueueSortOrder
    ) -> List[ReviewQueueItem]:
        """Apply sort order."""
        if sort_by == QueueSortOrder.PRIORITY_DESC:
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            return sorted(
                items,
                key=lambda x: (priority_order.get(x.priority, 4), -x.dissent_index)
            )
        elif sort_by == QueueSortOrder.DISSENT_DESC:
            return sorted(items, key=lambda x: x.dissent_index, reverse=True)
        elif sort_by == QueueSortOrder.OLDEST_FIRST:
            return sorted(items, key=lambda x: x.escalated_at)
        elif sort_by == QueueSortOrder.NEWEST_FIRST:
            return sorted(items, key=lambda x: x.escalated_at, reverse=True)
        elif sort_by == QueueSortOrder.DEADLINE_SOON:
            # Items with deadlines first, sorted by deadline
            with_deadline = [i for i in items if i.deadline]
            without_deadline = [i for i in items if not i.deadline]
            with_deadline_sorted = sorted(with_deadline, key=lambda x: x.deadline)
            return with_deadline_sorted + without_deadline

        return items

    def assign_review(self, bundle_id: str, reviewer_id: str) -> bool:
        """
        Assign review to a specific reviewer.

        Args:
            bundle_id: Bundle to assign
            reviewer_id: Reviewer to assign to

        Returns:
            True if assigned successfully
        """
        for item in self.queue:
            if item.bundle_id == bundle_id:
                item.assigned_to = reviewer_id
                if self.storage:
                    self._persist_queue()
                return True

        return False

    def complete_review(
        self,
        bundle_id: str,
        feedback: Any,
        final_verdict: str
    ) -> bool:
        """
        Mark review as completed.

        Args:
            bundle_id: Bundle ID
            feedback: ReviewFeedback object
            final_verdict: Final verdict after review

        Returns:
            True if completed successfully
        """
        # Find and remove from queue
        item_idx = None
        for idx, item in enumerate(self.queue):
            if item.bundle_id == bundle_id:
                item_idx = idx
                break

        if item_idx is None:
            return False

        item = self.queue.pop(item_idx)

        # Add to completed
        self.completed_reviews.append({
            "bundle_id": bundle_id,
            "case_id": item.case_id,
            "reviewer_id": feedback.reviewer_id,
            "verdict": final_verdict,
            "confidence": feedback.confidence,
            "completed_at": datetime.utcnow(),
            "time_in_queue": datetime.utcnow() - item.escalated_at,
            "priority": item.priority,
            "dissent_index": item.dissent_index
        })

        if self.storage:
            self._persist_queue()
            self._persist_completed()

        return True

    def get_stats(self) -> ReviewQueueStats:
        """Get queue statistics."""
        if not self.queue:
            return ReviewQueueStats(
                total_pending=0,
                critical_count=0,
                high_priority_count=0,
                overdue_count=0,
                avg_dissent_index=0.0,
                avg_time_in_queue=timedelta(0),
                by_disagreement_type={},
                by_priority={},
                by_majority_verdict={}
            )

        # Count categories
        critical_count = sum(1 for i in self.queue if i.priority == "critical")
        high_priority_count = sum(1 for i in self.queue if i.priority in ["critical", "high"])
        overdue_count = sum(1 for i in self.queue if i.is_overdue())

        # Average dissent
        avg_dissent = sum(i.dissent_index for i in self.queue) / len(self.queue)

        # Average time in queue
        now = datetime.utcnow()
        total_time = sum(
            (now - i.escalated_at for i in self.queue),
            timedelta(0)
        )
        avg_time = total_time / len(self.queue)

        # Count by category
        by_disagreement = {}
        by_priority = {}
        by_verdict = {}

        for item in self.queue:
            # Disagreement type
            dt = item.disagreement_type
            by_disagreement[dt] = by_disagreement.get(dt, 0) + 1

            # Priority
            by_priority[item.priority] = by_priority.get(item.priority, 0) + 1

            # Verdict
            by_verdict[item.majority_verdict] = by_verdict.get(item.majority_verdict, 0) + 1

        return ReviewQueueStats(
            total_pending=len(self.queue),
            critical_count=critical_count,
            high_priority_count=high_priority_count,
            overdue_count=overdue_count,
            avg_dissent_index=avg_dissent,
            avg_time_in_queue=avg_time,
            by_disagreement_type=by_disagreement,
            by_priority=by_priority,
            by_majority_verdict=by_verdict
        )

    def get_reviewer_stats(self, reviewer_id: str) -> ReviewerStats:
        """
        Get statistics for specific reviewer.

        Args:
            reviewer_id: Reviewer to get stats for

        Returns:
            ReviewerStats object
        """
        # Filter completed reviews by reviewer
        reviews = [
            r for r in self.completed_reviews
            if r.get("reviewer_id") == reviewer_id
        ]

        if not reviews:
            return ReviewerStats(
                reviewer_id=reviewer_id,
                total_reviews=0,
                avg_confidence=0.0,
                avg_review_time=timedelta(0),
                verdict_distribution={},
                agreement_with_critics=0.0,
                override_rate=0.0,
                reviews_this_week=0,
                reviews_this_month=0
            )

        # Calculate stats
        total_reviews = len(reviews)
        avg_confidence = sum(r.get("confidence", 0.0) for r in reviews) / total_reviews

        total_time = sum(
            (r.get("time_in_queue", timedelta(0)) for r in reviews),
            timedelta(0)
        )
        avg_review_time = total_time / total_reviews

        # Verdict distribution
        verdict_dist = {}
        for r in reviews:
            verdict = r.get("verdict", "unknown")
            verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1

        # Time-based counts
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        reviews_this_week = sum(
            1 for r in reviews
            if r.get("completed_at", datetime.min) >= week_ago
        )

        reviews_this_month = sum(
            1 for r in reviews
            if r.get("completed_at", datetime.min) >= month_ago
        )

        # Placeholder for agreement metrics (would need critic data)
        agreement_with_critics = 0.75  # Placeholder
        override_rate = 0.15  # Placeholder

        return ReviewerStats(
            reviewer_id=reviewer_id,
            total_reviews=total_reviews,
            avg_confidence=avg_confidence,
            avg_review_time=avg_review_time,
            verdict_distribution=verdict_dist,
            agreement_with_critics=agreement_with_critics,
            override_rate=override_rate,
            reviews_this_week=reviews_this_week,
            reviews_this_month=reviews_this_month
        )

    def _persist_queue(self):
        """Persist queue to storage backend."""
        if self.storage:
            try:
                self.storage.save_queue(self.queue)
            except Exception as e:
                logger.error(f"Failed to persist queue: {e}")

    def _persist_completed(self):
        """Persist completed reviews to storage backend."""
        if self.storage:
            try:
                self.storage.save_completed(self.completed_reviews)
            except Exception as e:
                logger.error(f"Failed to persist completed reviews: {e}")

    def export_queue_summary(self) -> Dict[str, Any]:
        """
        Export queue summary for dashboard display.

        Returns:
            Summary dict with queue overview and items
        """
        stats = self.get_stats()

        return {
            "summary": {
                "total_pending": stats.total_pending,
                "critical": stats.critical_count,
                "high_priority": stats.high_priority_count,
                "overdue": stats.overdue_count,
                "avg_dissent_index": round(stats.avg_dissent_index, 3),
                "avg_time_in_queue_hours": stats.avg_time_in_queue.total_seconds() / 3600
            },
            "by_category": {
                "disagreement_type": stats.by_disagreement_type,
                "priority": stats.by_priority,
                "majority_verdict": stats.by_majority_verdict
            },
            "queue_items": [
                {
                    "bundle_id": item.bundle_id,
                    "priority": item.priority,
                    "dissent_index": round(item.dissent_index, 3),
                    "disagreement_type": item.disagreement_type,
                    "prompt_preview": item.prompt_preview,
                    "split_ratio": item.split_ratio,
                    "assigned_to": item.assigned_to,
                    "is_overdue": item.is_overdue(),
                    "time_until_deadline": (
                        item.time_until_deadline().total_seconds() / 3600
                        if item.time_until_deadline() else None
                    )
                }
                for item in self.get_queue(limit=50)
            ]
        }
