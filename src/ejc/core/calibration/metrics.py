"""
Accuracy metrics and performance tracking for critics.

Calculates calibration metrics by comparing critic verdicts against ground truth.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import statistics


@dataclass
class CriticPerformance:
    """Performance metrics for a single critic."""

    critic_name: str
    accuracy: float  # Overall accuracy (0.0-1.0)
    precision: float  # Precision for each verdict
    recall: float  # Recall for each verdict
    f1_score: float  # F1 score

    # Confidence calibration metrics
    avg_confidence: float  # Average confidence when correct
    avg_confidence_when_wrong: float  # Average confidence when incorrect
    overconfidence_ratio: float  # Ratio of confidence to accuracy

    # Sample counts
    total_samples: int
    correct_predictions: int
    incorrect_predictions: int

    # Per-verdict breakdown
    verdict_accuracy: Dict[str, float] = field(default_factory=dict)

    # Temporal metrics
    recent_accuracy: Optional[float] = None  # Last 7 days
    accuracy_trend: Optional[str] = None  # "improving", "stable", "degrading"

    # Flags
    is_degraded: bool = False
    needs_retraining: bool = False

    @property
    def calibration_error(self) -> float:
        """
        Calculate calibration error (difference between confidence and accuracy).

        Lower is better. <0.1 is well-calibrated.
        """
        return abs(self.avg_confidence - self.accuracy)


@dataclass
class ConfusionMatrix:
    """Confusion matrix for a critic's predictions."""

    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def accuracy(self) -> float:
        """Calculate accuracy."""
        total = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total

    @property
    def precision(self) -> float:
        """Calculate precision."""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Calculate recall."""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """Calculate F1 score."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)


class AccuracyMetrics:
    """
    Calculates accuracy metrics for critics based on ground truth feedback.
    """

    @staticmethod
    def calculate_critic_performance(
        critic_name: str,
        feedback_data: List[Tuple[str, str, float]],  # (predicted, ground_truth, confidence)
        recent_window_days: int = 7
    ) -> CriticPerformance:
        """
        Calculate comprehensive performance metrics for a critic.

        Args:
            critic_name: Name of the critic
            feedback_data: List of (predicted_verdict, ground_truth_verdict, confidence)
            recent_window_days: Window for recent accuracy calculation

        Returns:
            CriticPerformance metrics
        """
        if not feedback_data:
            return CriticPerformance(
                critic_name=critic_name,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                avg_confidence=0.0,
                avg_confidence_when_wrong=0.0,
                overconfidence_ratio=0.0,
                total_samples=0,
                correct_predictions=0,
                incorrect_predictions=0,
            )

        # Calculate basic metrics
        correct = [pred == truth for pred, truth, _ in feedback_data]
        confidences = [conf for _, _, conf in feedback_data]

        total_samples = len(feedback_data)
        correct_predictions = sum(correct)
        incorrect_predictions = total_samples - correct_predictions
        accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0

        # Confidence metrics
        correct_confidences = [conf for (pred, truth, conf), is_correct in zip(feedback_data, correct) if is_correct]
        wrong_confidences = [conf for (pred, truth, conf), is_correct in zip(feedback_data, correct) if not is_correct]

        avg_confidence = statistics.mean(confidences) if confidences else 0.0
        avg_confidence_correct = statistics.mean(correct_confidences) if correct_confidences else 0.0
        avg_confidence_wrong = statistics.mean(wrong_confidences) if wrong_confidences else 0.0

        overconfidence_ratio = avg_confidence / accuracy if accuracy > 0 else 0.0

        # Per-verdict accuracy
        verdict_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        for pred, truth, _ in feedback_data:
            verdict_counts[pred]["total"] += 1
            if pred == truth:
                verdict_counts[pred]["correct"] += 1

        verdict_accuracy = {
            verdict: counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
            for verdict, counts in verdict_counts.items()
        }

        # Calculate precision/recall/F1 (treat as binary: ALLOW vs not-ALLOW)
        confusion = ConfusionMatrix()
        for pred, truth, _ in feedback_data:
            if pred == "ALLOW" and truth == "ALLOW":
                confusion.true_positives += 1
            elif pred == "ALLOW" and truth != "ALLOW":
                confusion.false_positives += 1
            elif pred != "ALLOW" and truth != "ALLOW":
                confusion.true_negatives += 1
            else:
                confusion.false_negatives += 1

        return CriticPerformance(
            critic_name=critic_name,
            accuracy=accuracy,
            precision=confusion.precision,
            recall=confusion.recall,
            f1_score=confusion.f1_score,
            avg_confidence=avg_confidence,
            avg_confidence_when_wrong=avg_confidence_wrong,
            overconfidence_ratio=overconfidence_ratio,
            total_samples=total_samples,
            correct_predictions=correct_predictions,
            incorrect_predictions=incorrect_predictions,
            verdict_accuracy=verdict_accuracy,
        )

    @staticmethod
    def detect_degradation(
        current_performance: CriticPerformance,
        historical_accuracy: List[float],
        degradation_threshold: float = 0.1
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if a critic's performance has degraded.

        Args:
            current_performance: Current performance metrics
            historical_accuracy: List of historical accuracy values
            degradation_threshold: Threshold for significant degradation

        Returns:
            (is_degraded, reason)
        """
        if not historical_accuracy or len(historical_accuracy) < 3:
            return False, None

        # Calculate baseline from historical data
        baseline_accuracy = statistics.mean(historical_accuracy)

        # Check if current accuracy is significantly lower
        if baseline_accuracy - current_performance.accuracy > degradation_threshold:
            return True, f"Accuracy dropped from {baseline_accuracy:.2f} to {current_performance.accuracy:.2f}"

        # Check for downward trend
        if len(historical_accuracy) >= 5:
            recent_trend = historical_accuracy[-5:]
            if all(recent_trend[i] >= recent_trend[i+1] for i in range(len(recent_trend)-1)):
                return True, "Consistent downward accuracy trend"

        # Check calibration error
        if current_performance.calibration_error > 0.2:
            return True, f"Poor calibration: error = {current_performance.calibration_error:.2f}"

        return False, None

    @staticmethod
    def calculate_accuracy_trend(
        accuracy_history: List[Tuple[datetime, float]],
        window_days: int = 30
    ) -> str:
        """
        Calculate accuracy trend over time.

        Args:
            accuracy_history: List of (timestamp, accuracy) tuples
            window_days: Window for trend calculation

        Returns:
            "improving", "stable", or "degrading"
        """
        if len(accuracy_history) < 2:
            return "stable"

        # Filter to recent window
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent = [(ts, acc) for ts, acc in accuracy_history if ts >= cutoff]

        if len(recent) < 2:
            return "stable"

        # Simple linear trend
        accuracies = [acc for _, acc in recent]
        first_half = accuracies[:len(accuracies)//2]
        second_half = accuracies[len(accuracies)//2:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        diff = second_avg - first_avg

        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "degrading"
        else:
            return "stable"
