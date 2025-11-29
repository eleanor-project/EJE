"""
Main calibration engine for critic performance management.

Integrates feedback collection, accuracy tracking, threshold tuning, and degradation detection.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from .feedback import FeedbackCollector, GroundTruth
from .metrics import AccuracyMetrics, CriticPerformance
from .tuner import ConfidenceTuner, ConfidenceThresholds
from ...utils.logging import get_logger

logger = get_logger("ejc.calibration")


class CriticCalibrator:
    """
    Main calibration engine for managing critic performance.

    Responsibilities:
    - Collect ground truth feedback from human reviewers
    - Track critic accuracy against ground truth
    - Auto-tune confidence thresholds
    - Detect degraded critics
    - Generate performance reports
    """

    def __init__(
        self,
        feedback_collector: Optional[FeedbackCollector] = None,
        confidence_tuner: Optional[ConfidenceTuner] = None,
        degradation_threshold: float = 0.1,
        min_samples_for_tuning: int = 50
    ):
        """
        Initialize calibrator.

        Args:
            feedback_collector: Feedback collection system (creates default if None)
            confidence_tuner: Confidence tuning system (creates default if None)
            degradation_threshold: Threshold for detecting degradation
            min_samples_for_tuning: Minimum samples before tuning thresholds
        """
        self.feedback_collector = feedback_collector or FeedbackCollector()
        self.confidence_tuner = confidence_tuner or ConfidenceTuner(
            min_samples=min_samples_for_tuning
        )
        self.degradation_threshold = degradation_threshold
        self.min_samples_for_tuning = min_samples_for_tuning

        # Cache for performance data
        self._performance_cache: Dict[str, CriticPerformance] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def submit_ground_truth(self, ground_truth: GroundTruth) -> str:
        """
        Submit ground truth feedback for a decision.

        Args:
            ground_truth: Ground truth verdict from human reviewer

        Returns:
            Feedback entry ID

        Raises:
            ValueError: If ground truth data is invalid
        """
        logger.info(f"Submitting ground truth for decision {ground_truth.decision_id}")
        entry_id = self.feedback_collector.submit_feedback(ground_truth)

        # Invalidate cache since we have new data
        self._invalidate_cache()

        return entry_id

    def get_critic_performance(
        self,
        critic_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Optional[CriticPerformance]:
        """
        Get performance metrics for a critic.

        Args:
            critic_name: Name of the critic
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            use_cache: Whether to use cached results

        Returns:
            CriticPerformance metrics or None if insufficient data
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            cached = self._performance_cache.get(critic_name)
            if cached:
                return cached

        # Fetch ground truth feedback
        feedback_entries = self.feedback_collector.get_feedback(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

        if not feedback_entries:
            logger.warning(f"No feedback data available for {critic_name}")
            return None

        # Extract data for this critic
        critic_data = []
        for entry in feedback_entries:
            if critic_name in entry.critic_verdicts:
                critic_verdict = entry.critic_verdicts[critic_name]
                # Assuming critic verdicts are stored as strings, not dicts
                if isinstance(critic_verdict, dict):
                    verdict = critic_verdict.get("verdict", "REVIEW")
                    confidence = critic_verdict.get("confidence", 0.5)
                else:
                    verdict = critic_verdict
                    confidence = 0.5  # Default if not available

                critic_data.append((verdict, entry.verdict, confidence))

        if not critic_data:
            logger.warning(f"No data found for critic {critic_name}")
            return None

        # Calculate performance
        performance = AccuracyMetrics.calculate_critic_performance(
            critic_name, critic_data
        )

        # Check for degradation
        # For this, we'd need historical data - simplified here
        is_degraded, reason = self._check_degradation(critic_name, performance)
        performance.is_degraded = is_degraded
        if is_degraded:
            performance.needs_retraining = True
            logger.warning(f"Critic {critic_name} degraded: {reason}")

        # Cache the result
        self._performance_cache[critic_name] = performance
        if not self._cache_timestamp:
            self._cache_timestamp = datetime.utcnow()

        return performance

    def get_all_critic_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, CriticPerformance]:
        """
        Get performance metrics for all critics.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            Dict of critic_name -> CriticPerformance
        """
        # Get all feedback
        feedback_entries = self.feedback_collector.get_feedback(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not feedback_entries:
            return {}

        # Group by critic
        critic_data_map = defaultdict(list)
        for entry in feedback_entries:
            for critic_name, critic_verdict in entry.critic_verdicts.items():
                if isinstance(critic_verdict, dict):
                    verdict = critic_verdict.get("verdict", "REVIEW")
                    confidence = critic_verdict.get("confidence", 0.5)
                else:
                    verdict = critic_verdict
                    confidence = 0.5

                critic_data_map[critic_name].append((verdict, entry.verdict, confidence))

        # Calculate performance for each critic
        performance_map = {}
        for critic_name, critic_data in critic_data_map.items():
            performance = AccuracyMetrics.calculate_critic_performance(
                critic_name, critic_data
            )

            # Check degradation
            is_degraded, reason = self._check_degradation(critic_name, performance)
            performance.is_degraded = is_degraded
            if is_degraded:
                performance.needs_retraining = True

            performance_map[critic_name] = performance

        return performance_map

    def tune_critic_thresholds(
        self,
        critic_name: str,
        target_accuracy: float = 0.90
    ) -> Optional[ConfidenceThresholds]:
        """
        Auto-tune confidence thresholds for a critic.

        Args:
            critic_name: Name of the critic to tune
            target_accuracy: Target accuracy to achieve

        Returns:
            Tuned confidence thresholds or None if insufficient data

        Raises:
            ValueError: If insufficient data for tuning
        """
        logger.info(f"Tuning thresholds for {critic_name}")

        # Get feedback data
        feedback_entries = self.feedback_collector.get_feedback(limit=10000)

        # Extract data for this critic
        critic_data = []
        for entry in feedback_entries:
            if critic_name in entry.critic_verdicts:
                critic_verdict = entry.critic_verdicts[critic_name]
                if isinstance(critic_verdict, dict):
                    verdict = critic_verdict.get("verdict", "REVIEW")
                    confidence = critic_verdict.get("confidence", 0.5)
                else:
                    verdict = critic_verdict
                    confidence = 0.5

                critic_data.append((verdict, entry.verdict, confidence))

        if len(critic_data) < self.min_samples_for_tuning:
            logger.warning(
                f"Insufficient data for tuning {critic_name}: "
                f"{len(critic_data)} < {self.min_samples_for_tuning}"
            )
            return None

        # Calculate optimal thresholds
        tuner = ConfidenceTuner(target_accuracy=target_accuracy, min_samples=self.min_samples_for_tuning)
        thresholds = tuner.calculate_optimal_thresholds(critic_name, critic_data)

        logger.info(
            f"Tuned {critic_name}: ALLOW≥{thresholds.allow_threshold}, "
            f"DENY≥{thresholds.deny_threshold}, REVIEW<{thresholds.review_threshold}"
        )

        return thresholds

    def tune_all_thresholds(
        self,
        target_accuracy: float = 0.90
    ) -> Dict[str, ConfidenceThresholds]:
        """
        Auto-tune confidence thresholds for all critics.

        Args:
            target_accuracy: Target accuracy to achieve

        Returns:
            Dict of critic_name -> ConfidenceThresholds
        """
        logger.info("Tuning thresholds for all critics")

        # Get all feedback
        feedback_entries = self.feedback_collector.get_feedback(limit=10000)

        # Group by critic
        critic_data_map = defaultdict(list)
        for entry in feedback_entries:
            for critic_name, critic_verdict in entry.critic_verdicts.items():
                if isinstance(critic_verdict, dict):
                    verdict = critic_verdict.get("verdict", "REVIEW")
                    confidence = critic_verdict.get("confidence", 0.5)
                else:
                    verdict = critic_verdict
                    confidence = 0.5

                critic_data_map[critic_name].append((verdict, entry.verdict, confidence))

        # Tune each critic
        thresholds_map = {}
        tuner = ConfidenceTuner(target_accuracy=target_accuracy, min_samples=self.min_samples_for_tuning)

        for critic_name, critic_data in critic_data_map.items():
            if len(critic_data) < self.min_samples_for_tuning:
                logger.info(f"Skipping {critic_name}: insufficient data")
                continue

            try:
                thresholds = tuner.calculate_optimal_thresholds(critic_name, critic_data)
                thresholds_map[critic_name] = thresholds
            except Exception as e:
                logger.error(f"Failed to tune {critic_name}: {e}")

        logger.info(f"Tuned {len(thresholds_map)} critics")
        return thresholds_map

    def get_degraded_critics(self) -> List[Tuple[str, CriticPerformance, str]]:
        """
        Get list of degraded critics that need attention.

        Returns:
            List of (critic_name, performance, reason) tuples
        """
        all_performance = self.get_all_critic_performance()

        degraded = []
        for critic_name, performance in all_performance.items():
            if performance.is_degraded:
                reason = f"Accuracy: {performance.accuracy:.2%}"
                if performance.calibration_error > 0.2:
                    reason += f", Calibration error: {performance.calibration_error:.2f}"
                degraded.append((critic_name, performance, reason))

        return degraded

    def _check_degradation(
        self,
        critic_name: str,
        current_performance: CriticPerformance
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a critic's performance has degraded.

        Args:
            critic_name: Name of the critic
            current_performance: Current performance metrics

        Returns:
            (is_degraded, reason)
        """
        # Simple degradation check - could be enhanced with historical data
        if current_performance.accuracy < 0.7:
            return True, f"Low accuracy: {current_performance.accuracy:.2%}"

        if current_performance.calibration_error > 0.2:
            return True, f"High calibration error: {current_performance.calibration_error:.2f}"

        if current_performance.overconfidence_ratio > 1.3:
            return True, f"Overconfident: ratio={current_performance.overconfidence_ratio:.2f}"

        return False, None

    def _is_cache_valid(self) -> bool:
        """Check if performance cache is still valid."""
        if not self._cache_timestamp:
            return False

        age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl_seconds

    def _invalidate_cache(self):
        """Invalidate the performance cache."""
        self._performance_cache.clear()
        self._cache_timestamp = None

    def generate_calibration_report(self) -> Dict:
        """
        Generate comprehensive calibration report.

        Returns:
            Dict with calibration metrics and recommendations
        """
        all_performance = self.get_all_critic_performance()
        degraded = self.get_degraded_critics()

        total_critics = len(all_performance)
        total_degraded = len(degraded)

        avg_accuracy = sum(p.accuracy for p in all_performance.values()) / total_critics if total_critics > 0 else 0.0
        avg_calibration_error = sum(p.calibration_error for p in all_performance.values()) / total_critics if total_critics > 0 else 0.0

        total_feedback = self.feedback_collector.get_feedback_count()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_critics": total_critics,
                "degraded_critics": total_degraded,
                "avg_accuracy": avg_accuracy,
                "avg_calibration_error": avg_calibration_error,
                "total_feedback_samples": total_feedback,
            },
            "critic_performance": {
                name: {
                    "accuracy": perf.accuracy,
                    "precision": perf.precision,
                    "recall": perf.recall,
                    "f1_score": perf.f1_score,
                    "calibration_error": perf.calibration_error,
                    "is_degraded": perf.is_degraded,
                    "needs_retraining": perf.needs_retraining,
                }
                for name, perf in all_performance.items()
            },
            "degraded_critics": [
                {
                    "name": name,
                    "accuracy": perf.accuracy,
                    "reason": reason,
                }
                for name, perf, reason in degraded
            ],
            "recommendations": self._generate_recommendations(all_performance, degraded),
        }

    def _generate_recommendations(
        self,
        all_performance: Dict[str, CriticPerformance],
        degraded: List[Tuple[str, CriticPerformance, str]]
    ) -> List[str]:
        """Generate actionable recommendations based on calibration data."""
        recommendations = []

        if degraded:
            recommendations.append(
                f"⚠️  {len(degraded)} critic(s) degraded - consider retraining or investigation"
            )

        # Check if we have enough data for tuning
        feedback_count = self.feedback_collector.get_feedback_count()
        if feedback_count < self.min_samples_for_tuning:
            recommendations.append(
                f"📊 Need more feedback data for tuning: {feedback_count}/{self.min_samples_for_tuning}"
            )
        else:
            recommendations.append(
                "✅ Sufficient data for threshold tuning - consider running tune_all_thresholds()"
            )

        # Check calibration errors
        high_calibration = [
            name for name, perf in all_performance.items()
            if perf.calibration_error > 0.15
        ]
        if high_calibration:
            recommendations.append(
                f"🎯 {len(high_calibration)} critic(s) poorly calibrated: {', '.join(high_calibration)}"
            )

        return recommendations
