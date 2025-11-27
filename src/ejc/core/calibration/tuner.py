"""
Confidence threshold auto-tuning based on critic performance.

Automatically adjusts confidence thresholds to improve decision quality.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import statistics


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for a critic."""

    critic_name: str
    allow_threshold: float  # Confidence required for ALLOW verdict
    deny_threshold: float  # Confidence required for DENY verdict
    review_threshold: float  # Confidence below which to escalate

    # Metadata
    last_updated: str
    samples_used: int
    performance_at_update: float  # Accuracy when thresholds were set


class ConfidenceTuner:
    """
    Auto-tunes confidence thresholds based on critic performance.

    Adjusts thresholds to:
    1. Maximize accuracy
    2. Minimize false positives/negatives
    3. Properly calibrate confidence with actual performance
    """

    def __init__(
        self,
        target_accuracy: float = 0.90,
        min_samples: int = 50
    ):
        """
        Initialize confidence tuner.

        Args:
            target_accuracy: Target accuracy to achieve (0.0-1.0)
            min_samples: Minimum samples required before tuning
        """
        self.target_accuracy = target_accuracy
        self.min_samples = min_samples

    def calculate_optimal_thresholds(
        self,
        critic_name: str,
        feedback_data: List[Tuple[str, str, float]],  # (predicted, ground_truth, confidence)
        current_thresholds: Optional[ConfidenceThresholds] = None
    ) -> ConfidenceThresholds:
        """
        Calculate optimal confidence thresholds for a critic.

        Args:
            critic_name: Name of the critic
            feedback_data: List of (predicted_verdict, ground_truth_verdict, confidence)
            current_thresholds: Current thresholds (optional)

        Returns:
            Optimized confidence thresholds

        Raises:
            ValueError: If insufficient data for tuning
        """
        if len(feedback_data) < self.min_samples:
            raise ValueError(
                f"Insufficient data for tuning: {len(feedback_data)} < {self.min_samples}"
            )

        # Separate by verdict type
        allow_data = [(truth, conf) for pred, truth, conf in feedback_data if pred == "ALLOW"]
        deny_data = [(truth, conf) for pred, truth, conf in feedback_data if pred == "DENY"]

        # Calculate optimal thresholds for each verdict
        allow_threshold = self._calculate_threshold_for_verdict(
            allow_data, target_verdict="ALLOW", target_accuracy=self.target_accuracy
        )

        deny_threshold = self._calculate_threshold_for_verdict(
            deny_data, target_verdict="DENY", target_accuracy=self.target_accuracy
        )

        # Review threshold is the minimum confidence where we trust the critic
        # Set it based on calibration error
        review_threshold = self._calculate_review_threshold(feedback_data)

        # Calculate current performance
        correct = sum(1 for pred, truth, _ in feedback_data if pred == truth)
        accuracy = correct / len(feedback_data)

        from datetime import datetime
        return ConfidenceThresholds(
            critic_name=critic_name,
            allow_threshold=allow_threshold,
            deny_threshold=deny_threshold,
            review_threshold=review_threshold,
            last_updated=datetime.utcnow().isoformat(),
            samples_used=len(feedback_data),
            performance_at_update=accuracy
        )

    def _calculate_threshold_for_verdict(
        self,
        verdict_data: List[Tuple[str, float]],  # (ground_truth, confidence)
        target_verdict: str,
        target_accuracy: float
    ) -> float:
        """
        Calculate optimal confidence threshold for a specific verdict.

        Finds the confidence threshold that achieves target accuracy.

        Args:
            verdict_data: List of (ground_truth, confidence) for this verdict
            target_verdict: The verdict we're optimizing for (ALLOW/DENY)
            target_accuracy: Target accuracy to achieve

        Returns:
            Optimal confidence threshold
        """
        if not verdict_data:
            return 0.7  # Default threshold

        # Try different thresholds and find one that achieves target accuracy
        confidences = sorted([conf for _, conf in verdict_data])

        best_threshold = 0.7
        best_accuracy = 0.0

        for threshold in confidences:
            # Calculate accuracy if we only accept predictions above this threshold
            above_threshold = [(truth, conf) for truth, conf in verdict_data if conf >= threshold]

            if not above_threshold:
                continue

            correct = sum(1 for truth, _ in above_threshold if truth == target_verdict)
            accuracy = correct / len(above_threshold)

            # Prefer higher thresholds if accuracy is similar (more conservative)
            if accuracy >= target_accuracy and accuracy >= best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold

        return round(best_threshold, 2)

    def _calculate_review_threshold(
        self,
        feedback_data: List[Tuple[str, str, float]]
    ) -> float:
        """
        Calculate threshold below which decisions should be reviewed.

        Uses calibration error to determine when the critic is unreliable.

        Args:
            feedback_data: List of (predicted, ground_truth, confidence)

        Returns:
            Review threshold
        """
        if not feedback_data:
            return 0.6  # Default

        # Calculate calibration error at different confidence levels
        confidence_buckets = {}
        for pred, truth, conf in feedback_data:
            bucket = round(conf, 1)  # 0.1, 0.2, ..., 1.0
            if bucket not in confidence_buckets:
                confidence_buckets[bucket] = {"correct": 0, "total": 0}

            confidence_buckets[bucket]["total"] += 1
            if pred == truth:
                confidence_buckets[bucket]["correct"] += 1

        # Find the confidence level where accuracy drops below acceptable
        acceptable_accuracy = 0.7  # Below this, we want review

        for conf_level in sorted(confidence_buckets.keys()):
            bucket = confidence_buckets[conf_level]
            accuracy = bucket["correct"] / bucket["total"]

            if accuracy < acceptable_accuracy:
                # This confidence level is unreliable, set review threshold above it
                return min(conf_level + 0.1, 0.9)

        # If all levels are accurate, set a conservative threshold
        return 0.5

    def should_retune(
        self,
        current_thresholds: ConfidenceThresholds,
        recent_performance: float,
        new_samples: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if thresholds should be retuned.

        Args:
            current_thresholds: Current threshold settings
            recent_performance: Recent accuracy performance
            new_samples: Number of new samples since last tuning

        Returns:
            (should_retune, reason)
        """
        # Retune if performance has degraded significantly
        if recent_performance < current_thresholds.performance_at_update - 0.1:
            return True, "Performance degraded significantly"

        # Retune if we have a lot of new data
        if new_samples >= current_thresholds.samples_used * 0.5:
            return True, f"Significant new data: {new_samples} new samples"

        # Retune if it's been a while (based on samples, not time)
        total_samples = current_thresholds.samples_used + new_samples
        if total_samples >= current_thresholds.samples_used * 2:
            return True, "Double the training data available"

        return False, None

    def apply_threshold_adjustments(
        self,
        critic_reports: List[Dict],
        thresholds: Dict[str, ConfidenceThresholds]
    ) -> List[Dict]:
        """
        Apply confidence thresholds to critic reports.

        Adjusts verdicts based on calibrated thresholds.

        Args:
            critic_reports: List of critic report dicts
            thresholds: Dict of critic_name -> ConfidenceThresholds

        Returns:
            Adjusted critic reports
        """
        adjusted_reports = []

        for report in critic_reports:
            critic_name = report.get("critic", "unknown")
            confidence = report.get("confidence", 0.5)
            verdict = report.get("verdict", "REVIEW")

            # Get thresholds for this critic
            threshold = thresholds.get(critic_name)
            if not threshold:
                # No calibration data, keep original
                adjusted_reports.append(report)
                continue

            # Apply threshold logic
            adjusted_report = report.copy()

            # If confidence is below review threshold, escalate
            if confidence < threshold.review_threshold:
                adjusted_report["verdict"] = "REVIEW"
                adjusted_report["original_verdict"] = verdict
                adjusted_report["adjustment_reason"] = "Low confidence (below review threshold)"

            # If ALLOW but below allow threshold, review instead
            elif verdict == "ALLOW" and confidence < threshold.allow_threshold:
                adjusted_report["verdict"] = "REVIEW"
                adjusted_report["original_verdict"] = verdict
                adjusted_report["adjustment_reason"] = "ALLOW confidence below threshold"

            # If DENY but below deny threshold, review instead
            elif verdict == "DENY" and confidence < threshold.deny_threshold:
                adjusted_report["verdict"] = "REVIEW"
                adjusted_report["original_verdict"] = verdict
                adjusted_report["adjustment_reason"] = "DENY confidence below threshold"

            adjusted_reports.append(adjusted_report)

        return adjusted_reports
