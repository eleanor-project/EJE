"""
Tests for the critic calibration system.

Tests feedback collection, accuracy tracking, threshold tuning, and degradation detection.
"""

import pytest
from datetime import datetime, timedelta
from ejc.core.calibration import (
    CriticCalibrator,
    FeedbackCollector,
    GroundTruth,
    AccuracyMetrics,
    ConfidenceTuner,
    CriticPerformance,
)


@pytest.fixture
def feedback_collector():
    """Create feedback collector with in-memory DB."""
    return FeedbackCollector(db_uri="sqlite:///:memory:")


@pytest.fixture
def calibrator(feedback_collector):
    """Create calibrator instance."""
    return CriticCalibrator(feedback_collector=feedback_collector)


@pytest.fixture
def sample_ground_truth():
    """Create sample ground truth."""
    return GroundTruth(
        decision_id="test-123",
        verdict="ALLOW",
        confidence=0.95,
        reviewer_id="reviewer-1",
        justification="This action is clearly ethical",
        critic_verdicts={
            "rights_critic": "ALLOW",
            "safety_critic": "ALLOW",
            "fairness_critic": "REVIEW",
        },
    )


class TestFeedbackCollector:
    """Test ground truth feedback collection."""

    def test_submit_feedback(self, feedback_collector, sample_ground_truth):
        """Test submitting ground truth feedback."""
        entry_id = feedback_collector.submit_feedback(sample_ground_truth)
        assert entry_id is not None

    def test_invalid_verdict(self, feedback_collector):
        """Test that invalid verdicts are rejected."""
        gt = GroundTruth(
            decision_id="test-123",
            verdict="INVALID",
            confidence=0.9,
            reviewer_id="reviewer-1",
        )
        with pytest.raises(ValueError, match="Invalid verdict"):
            feedback_collector.submit_feedback(gt)

    def test_invalid_confidence(self, feedback_collector):
        """Test that invalid confidence values are rejected."""
        gt = GroundTruth(
            decision_id="test-123",
            verdict="ALLOW",
            confidence=1.5,  # Invalid: > 1.0
            reviewer_id="reviewer-1",
        )
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            feedback_collector.submit_feedback(gt)

    def test_retrieve_feedback(self, feedback_collector, sample_ground_truth):
        """Test retrieving feedback."""
        feedback_collector.submit_feedback(sample_ground_truth)

        feedback = feedback_collector.get_feedback(decision_id="test-123")
        assert len(feedback) == 1
        assert feedback[0].decision_id == "test-123"
        assert feedback[0].verdict == "ALLOW"

    def test_feedback_count(self, feedback_collector, sample_ground_truth):
        """Test feedback counting."""
        assert feedback_collector.get_feedback_count() == 0

        feedback_collector.submit_feedback(sample_ground_truth)
        assert feedback_collector.get_feedback_count() == 1

    def test_date_filtering(self, feedback_collector):
        """Test filtering feedback by date."""
        # Submit feedback with different timestamps
        gt1 = GroundTruth(
            decision_id="old",
            verdict="ALLOW",
            confidence=0.9,
            reviewer_id="reviewer-1",
            timestamp=(datetime.utcnow() - timedelta(days=10)).isoformat(),
        )
        gt2 = GroundTruth(
            decision_id="recent",
            verdict="DENY",
            confidence=0.9,
            reviewer_id="reviewer-1",
            timestamp=datetime.utcnow().isoformat(),
        )

        feedback_collector.submit_feedback(gt1)
        feedback_collector.submit_feedback(gt2)

        # Filter for recent only
        start_date = datetime.utcnow() - timedelta(days=5)
        recent_feedback = feedback_collector.get_feedback(start_date=start_date)

        assert len(recent_feedback) == 1
        assert recent_feedback[0].decision_id == "recent"


class TestAccuracyMetrics:
    """Test accuracy metrics calculation."""

    def test_perfect_accuracy(self):
        """Test metrics with perfect predictions."""
        feedback_data = [
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.95),
            ("DENY", "DENY", 0.85),
        ]

        perf = AccuracyMetrics.calculate_critic_performance(
            "test_critic", feedback_data
        )

        assert perf.accuracy == 1.0
        assert perf.correct_predictions == 3
        assert perf.incorrect_predictions == 0

    def test_partial_accuracy(self):
        """Test metrics with some incorrect predictions."""
        feedback_data = [
            ("ALLOW", "ALLOW", 0.9),   # Correct
            ("ALLOW", "DENY", 0.85),    # Incorrect
            ("DENY", "DENY", 0.95),     # Correct
            ("DENY", "ALLOW", 0.80),    # Incorrect
        ]

        perf = AccuracyMetrics.calculate_critic_performance(
            "test_critic", feedback_data
        )

        assert perf.accuracy == 0.5
        assert perf.correct_predictions == 2
        assert perf.incorrect_predictions == 2

    def test_calibration_error(self):
        """Test calibration error calculation."""
        # Perfect calibration: 90% confident, 90% accurate
        feedback_data = [
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "ALLOW", 0.9),
            ("ALLOW", "DENY", 0.9),   # 1 wrong
        ]

        perf = AccuracyMetrics.calculate_critic_performance(
            "test_critic", feedback_data
        )

        assert perf.accuracy == 0.9
        assert perf.avg_confidence == 0.9
        assert perf.calibration_error < 0.01  # Well calibrated

    def test_overconfident_critic(self):
        """Test detection of overconfident critics."""
        # 95% confident but only 60% accurate
        feedback_data = [
            ("ALLOW", "ALLOW", 0.95),
            ("ALLOW", "ALLOW", 0.95),
            ("ALLOW", "ALLOW", 0.95),
            ("ALLOW", "DENY", 0.95),
            ("ALLOW", "DENY", 0.95),
        ]

        perf = AccuracyMetrics.calculate_critic_performance(
            "test_critic", feedback_data
        )

        assert perf.accuracy == 0.6
        assert perf.avg_confidence == 0.95
        assert perf.overconfidence_ratio > 1.5  # Very overconfident

    def test_degradation_detection(self):
        """Test detection of degraded performance."""
        current_performance = CriticPerformance(
            critic_name="test",
            accuracy=0.65,
            precision=0.7,
            recall=0.6,
            f1_score=0.65,
            avg_confidence=0.8,
            avg_confidence_when_wrong=0.75,
            overconfidence_ratio=1.2,
            total_samples=100,
            correct_predictions=65,
            incorrect_predictions=35,
        )

        historical_accuracy = [0.85, 0.83, 0.82, 0.80, 0.78]

        is_degraded, reason = AccuracyMetrics.detect_degradation(
            current_performance, historical_accuracy, degradation_threshold=0.1
        )

        assert is_degraded is True
        assert "dropped" in reason.lower()


class TestConfidenceTuner:
    """Test confidence threshold tuning."""

    def test_calculate_optimal_thresholds(self):
        """Test threshold calculation with clear data."""
        # High confidence predictions that are accurate
        feedback_data = [
            ("ALLOW", "ALLOW", 0.95),
            ("ALLOW", "ALLOW", 0.90),
            ("ALLOW", "ALLOW", 0.85),
            ("ALLOW", "DENY", 0.60),   # Low confidence, wrong
            ("DENY", "DENY", 0.95),
            ("DENY", "DENY", 0.90),
        ]

        tuner = ConfidenceTuner(target_accuracy=0.90, min_samples=5)
        thresholds = tuner.calculate_optimal_thresholds(
            "test_critic", feedback_data
        )

        assert thresholds.critic_name == "test_critic"
        assert 0.0 <= thresholds.allow_threshold <= 1.0
        assert 0.0 <= thresholds.deny_threshold <= 1.0
        assert 0.0 <= thresholds.review_threshold <= 1.0

    def test_insufficient_data(self):
        """Test that tuner requires minimum samples."""
        feedback_data = [("ALLOW", "ALLOW", 0.9)]  # Only 1 sample

        tuner = ConfidenceTuner(min_samples=50)
        with pytest.raises(ValueError, match="Insufficient data"):
            tuner.calculate_optimal_thresholds("test_critic", feedback_data)

    def test_apply_threshold_adjustments(self):
        """Test applying thresholds to critic reports."""
        from ejc.core.calibration.tuner import ConfidenceThresholds

        thresholds = {
            "test_critic": ConfidenceThresholds(
                critic_name="test_critic",
                allow_threshold=0.8,
                deny_threshold=0.8,
                review_threshold=0.6,
                last_updated=datetime.utcnow().isoformat(),
                samples_used=100,
                performance_at_update=0.9,
            )
        }

        critic_reports = [
            {
                "critic": "test_critic",
                "verdict": "ALLOW",
                "confidence": 0.5,  # Below review threshold
            }
        ]

        tuner = ConfidenceTuner()
        adjusted = tuner.apply_threshold_adjustments(critic_reports, thresholds)

        assert adjusted[0]["verdict"] == "REVIEW"
        assert adjusted[0]["original_verdict"] == "ALLOW"
        assert "adjustment_reason" in adjusted[0]


class TestCriticCalibrator:
    """Test main calibrator integration."""

    def test_submit_ground_truth(self, calibrator, sample_ground_truth):
        """Test submitting ground truth through calibrator."""
        entry_id = calibrator.submit_ground_truth(sample_ground_truth)
        assert entry_id is not None

    def test_get_critic_performance_insufficient_data(self, calibrator):
        """Test that None is returned when no data available."""
        performance = calibrator.get_critic_performance("nonexistent_critic")
        assert performance is None

    def test_get_critic_performance_with_data(self, calibrator):
        """Test getting performance with sufficient data."""
        # Submit multiple feedback entries
        for i in range(10):
            gt = GroundTruth(
                decision_id=f"test-{i}",
                verdict="ALLOW" if i < 8 else "DENY",
                confidence=0.9,
                reviewer_id="reviewer-1",
                critic_verdicts={
                    "test_critic": "ALLOW" if i < 9 else "DENY",
                },
            )
            calibrator.submit_ground_truth(gt)

        performance = calibrator.get_critic_performance("test_critic")
        assert performance is not None
        assert performance.critic_name == "test_critic"
        assert 0.0 <= performance.accuracy <= 1.0

    def test_get_all_critic_performance(self, calibrator):
        """Test getting performance for all critics."""
        # Submit feedback for multiple critics
        gt = GroundTruth(
            decision_id="test-1",
            verdict="ALLOW",
            confidence=0.9,
            reviewer_id="reviewer-1",
            critic_verdicts={
                "critic_a": "ALLOW",
                "critic_b": "DENY",
                "critic_c": "ALLOW",
            },
        )
        calibrator.submit_ground_truth(gt)

        all_performance = calibrator.get_all_critic_performance()
        assert len(all_performance) == 3
        assert "critic_a" in all_performance
        assert "critic_b" in all_performance
        assert "critic_c" in all_performance

    def test_generate_calibration_report(self, calibrator):
        """Test generating comprehensive calibration report."""
        # Submit some feedback
        for i in range(5):
            gt = GroundTruth(
                decision_id=f"test-{i}",
                verdict="ALLOW",
                confidence=0.9,
                reviewer_id="reviewer-1",
                critic_verdicts={"test_critic": "ALLOW"},
            )
            calibrator.submit_ground_truth(gt)

        report = calibrator.generate_calibration_report()

        assert "timestamp" in report
        assert "summary" in report
        assert "critic_performance" in report
        assert "recommendations" in report
        assert report["summary"]["total_critics"] >= 0
        assert report["summary"]["total_feedback_samples"] >= 0

    def test_get_degraded_critics(self, calibrator):
        """Test identifying degraded critics."""
        # Submit feedback showing degraded performance
        for i in range(20):
            gt = GroundTruth(
                decision_id=f"test-{i}",
                verdict="ALLOW",
                confidence=0.9,
                reviewer_id="reviewer-1",
                critic_verdicts={
                    "bad_critic": "DENY",  # Always wrong
                },
            )
            calibrator.submit_ground_truth(gt)

        degraded = calibrator.get_degraded_critics()

        # Should detect the poorly performing critic
        assert len(degraded) > 0
        critic_names = [name for name, _, _ in degraded]
        assert "bad_critic" in critic_names


class TestIntegrationCalibration:
    """Integration tests for full calibration workflow."""

    def test_full_calibration_workflow(self, calibrator):
        """Test complete workflow: feedback → performance → tuning."""
        # Step 1: Submit diverse feedback
        test_data = [
            ("ALLOW", "ALLOW", 0.95),
            ("ALLOW", "ALLOW", 0.90),
            ("ALLOW", "ALLOW", 0.88),
            ("ALLOW", "DENY", 0.65),   # Wrong
            ("DENY", "DENY", 0.92),
            ("DENY", "DENY", 0.90),
            ("DENY", "ALLOW", 0.70),   # Wrong
            ("REVIEW", "REVIEW", 0.80),
        ]

        for i, (verdict, truth, conf) in enumerate(test_data):
            gt = GroundTruth(
                decision_id=f"test-{i}",
                verdict=truth,
                confidence=0.9,
                reviewer_id="reviewer-1",
                critic_verdicts={"rights_critic": verdict},
            )
            calibrator.submit_ground_truth(gt)

        # Step 2: Get performance
        performance = calibrator.get_critic_performance("rights_critic")
        assert performance is not None
        assert performance.total_samples == len(test_data)

        # Step 3: Check calibration report
        report = calibrator.generate_calibration_report()
        assert "rights_critic" in report["critic_performance"]

        # Step 4: Verify recommendations are provided
        assert len(report["recommendations"]) > 0
