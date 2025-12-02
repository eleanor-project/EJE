"""
Robustness Scoring System for EJE

Quantitative scoring system for measuring system security robustness with
objective metrics, benchmarking, and production readiness assessment.

Implements Issue #175: Create Robustness Scoring System

Metrics:
- Attack Success Rate: Percentage of attacks that succeed
- Graceful Degradation Score: How well system handles attacks
- Recovery Time: Time to recover from attacks
- False Positive Rate Under Attack: Incorrect decisions during attacks
- Composite Robustness Score: Overall security score (0-100)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import statistics
import json
from pathlib import Path

from .adversarial_testing import (
    AdversarialTestRunner,
    TestResult,
    TestSuiteResult,
    TestStatus
)
from .attack_patterns import AttackSeverity


@dataclass
class RobustnessMetrics:
    """Individual robustness metrics."""
    attack_success_rate: float          # 0.0-1.0 (lower is better)
    graceful_degradation_score: float    # 0.0-100.0 (higher is better)
    recovery_time_ms: float              # Milliseconds (lower is better)
    false_positive_rate: float           # 0.0-1.0 (lower is better)
    availability_score: float            # 0.0-100.0 (higher is better)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'attack_success_rate': self.attack_success_rate,
            'graceful_degradation_score': self.graceful_degradation_score,
            'recovery_time_ms': self.recovery_time_ms,
            'false_positive_rate': self.false_positive_rate,
            'availability_score': self.availability_score,
            'timestamp': self.timestamp
        }


@dataclass
class CompositeScore:
    """Composite robustness score with breakdown."""
    overall_score: float                  # 0-100 (higher is better)
    attack_defense_score: float           # 0-100
    degradation_score: float              # 0-100
    recovery_score: float                 # 0-100
    accuracy_score: float                 # 0-100
    availability_score: float             # 0-100
    grade: str                            # A+, A, B, C, D, F
    production_ready: bool                # >= 80 = ready
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'overall_score': self.overall_score,
            'breakdown': {
                'attack_defense': self.attack_defense_score,
                'graceful_degradation': self.degradation_score,
                'recovery': self.recovery_score,
                'accuracy': self.accuracy_score,
                'availability': self.availability_score
            },
            'grade': self.grade,
            'production_ready': self.production_ready,
            'timestamp': self.timestamp
        }


@dataclass
class BenchmarkResult:
    """Benchmark comparison result."""
    system_name: str
    robustness_score: float
    metrics: RobustnessMetrics
    composite_score: CompositeScore
    timestamp: str
    comparison_to_baseline: Optional[Dict[str, float]] = None


class RobustnessScorer:
    """
    Robustness scoring system for security assessment.

    Calculates objective metrics and composite scores for system robustness.
    """

    def __init__(
        self,
        system_under_test: Any,
        baseline_metrics: Optional[RobustnessMetrics] = None,
        results_directory: Optional[str] = None
    ):
        """
        Initialize robustness scorer.

        Args:
            system_under_test: System to score
            baseline_metrics: Optional baseline for comparison
            results_directory: Directory for storing scores
        """
        self.system_under_test = system_under_test
        self.baseline_metrics = baseline_metrics
        self.results_directory = Path(results_directory or './robustness_scores')
        self.results_directory.mkdir(parents=True, exist_ok=True)

        self._historical_scores: List[CompositeScore] = []
        self._load_historical_scores()

    def calculate_robustness_score(
        self,
        test_results: TestSuiteResult,
        include_recovery_test: bool = True
    ) -> CompositeScore:
        """
        Calculate composite robustness score from test results.

        Args:
            test_results: Results from adversarial tests
            include_recovery_test: Run recovery time test

        Returns:
            Composite robustness score
        """
        # Calculate individual metrics
        metrics = self._calculate_metrics(test_results, include_recovery_test)

        # Calculate component scores (0-100 scale)
        attack_defense_score = self._calculate_defense_score(metrics)
        degradation_score = metrics.graceful_degradation_score
        recovery_score = self._calculate_recovery_score(metrics)
        accuracy_score = self._calculate_accuracy_score(metrics)
        availability_score = metrics.availability_score

        # Calculate weighted composite score
        overall_score = self._calculate_composite_score(
            attack_defense_score,
            degradation_score,
            recovery_score,
            accuracy_score,
            availability_score
        )

        # Assign grade
        grade = self._assign_grade(overall_score)

        # Determine production readiness
        production_ready = overall_score >= 80.0

        composite = CompositeScore(
            overall_score=overall_score,
            attack_defense_score=attack_defense_score,
            degradation_score=degradation_score,
            recovery_score=recovery_score,
            accuracy_score=accuracy_score,
            availability_score=availability_score,
            grade=grade,
            production_ready=production_ready
        )

        # Save score
        self._save_score(composite, metrics)

        return composite

    def score_system(self) -> CompositeScore:
        """
        Score system by running comprehensive adversarial tests.

        Convenience method that runs tests and calculates score.
        """
        # Run adversarial tests
        runner = AdversarialTestRunner(
            system_under_test=self.system_under_test,
            enable_regression_detection=False
        )
        test_results = runner.run_full_suite()

        # Calculate score
        return self.calculate_robustness_score(test_results)

    def benchmark_against_baseline(
        self,
        baseline_name: str = "Production Baseline"
    ) -> Dict[str, Any]:
        """
        Benchmark current system against baseline.

        Args:
            baseline_name: Name for baseline comparison

        Returns:
            Comparison results
        """
        # Score current system
        current_score = self.score_system()

        if self.baseline_metrics is None:
            return {
                'error': 'No baseline metrics configured',
                'current_score': current_score.to_dict()
            }

        # Calculate baseline score (if not already calculated)
        baseline_composite = self._calculate_baseline_composite()

        # Compare
        comparison = {
            'baseline_name': baseline_name,
            'current_score': current_score.overall_score,
            'baseline_score': baseline_composite.overall_score,
            'delta': current_score.overall_score - baseline_composite.overall_score,
            'improvement': current_score.overall_score > baseline_composite.overall_score,
            'breakdown_comparison': {
                'attack_defense': {
                    'current': current_score.attack_defense_score,
                    'baseline': baseline_composite.attack_defense_score,
                    'delta': current_score.attack_defense_score - baseline_composite.attack_defense_score
                },
                'degradation': {
                    'current': current_score.degradation_score,
                    'baseline': baseline_composite.degradation_score,
                    'delta': current_score.degradation_score - baseline_composite.degradation_score
                },
                'recovery': {
                    'current': current_score.recovery_score,
                    'baseline': baseline_composite.recovery_score,
                    'delta': current_score.recovery_score - baseline_composite.recovery_score
                }
            }
        }

        return comparison

    def get_production_readiness_report(self) -> Dict[str, Any]:
        """
        Generate production readiness assessment.

        Returns:
            Detailed readiness report
        """
        score = self.score_system()

        # Define requirements
        requirements = {
            'overall_score': {'threshold': 80.0, 'met': score.overall_score >= 80.0},
            'attack_defense': {'threshold': 75.0, 'met': score.attack_defense_score >= 75.0},
            'graceful_degradation': {'threshold': 70.0, 'met': score.degradation_score >= 70.0},
            'recovery_time': {'threshold': 85.0, 'met': score.recovery_score >= 85.0},
            'availability': {'threshold': 95.0, 'met': score.availability_score >= 95.0}
        }

        # Check all requirements
        all_met = all(req['met'] for req in requirements.values())

        # Generate recommendations
        recommendations = self._generate_recommendations(score, requirements)

        return {
            'production_ready': all_met,
            'overall_score': score.overall_score,
            'grade': score.grade,
            'requirements': requirements,
            'recommendations': recommendations,
            'timestamp': score.timestamp
        }

    def get_trend_analysis(self, num_runs: int = 10) -> Dict[str, Any]:
        """
        Analyze trend in robustness scores.

        Args:
            num_runs: Number of historical runs to analyze

        Returns:
            Trend analysis
        """
        if not self._historical_scores:
            return {'trend': 'no_data', 'scores': []}

        recent_scores = self._historical_scores[-num_runs:]
        scores_only = [s.overall_score for s in recent_scores]

        if len(scores_only) < 2:
            return {
                'trend': 'insufficient_data',
                'current_score': scores_only[-1] if scores_only else 0,
                'scores': scores_only
            }

        # Calculate trend
        if scores_only[-1] > scores_only[0] + 2:
            trend = 'improving'
        elif scores_only[-1] < scores_only[0] - 2:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'current_score': scores_only[-1],
            'previous_score': scores_only[0],
            'delta': scores_only[-1] - scores_only[0],
            'average_score': statistics.mean(scores_only),
            'best_score': max(scores_only),
            'worst_score': min(scores_only),
            'std_dev': statistics.stdev(scores_only) if len(scores_only) > 1 else 0,
            'scores': scores_only
        }

    def _calculate_metrics(
        self,
        test_results: TestSuiteResult,
        include_recovery: bool
    ) -> RobustnessMetrics:
        """Calculate individual robustness metrics."""
        # Attack Success Rate
        attack_success_rate = test_results.failed / test_results.total_tests if test_results.total_tests > 0 else 0

        # Graceful Degradation Score
        degradation_score = self._calculate_degradation_score(test_results)

        # Recovery Time
        if include_recovery:
            recovery_time = self._measure_recovery_time()
        else:
            recovery_time = 0.0

        # False Positive Rate (simulate based on test results)
        false_positive_rate = self._estimate_false_positive_rate(test_results)

        # Availability Score
        availability_score = self._calculate_availability_score(test_results)

        return RobustnessMetrics(
            attack_success_rate=attack_success_rate,
            graceful_degradation_score=degradation_score,
            recovery_time_ms=recovery_time,
            false_positive_rate=false_positive_rate,
            availability_score=availability_score
        )

    def _calculate_degradation_score(self, test_results: TestSuiteResult) -> float:
        """
        Calculate graceful degradation score.

        Measures how well system handles attacks (even when vulnerable).
        """
        # Factors:
        # - Error rate (lower is better)
        # - System availability during attacks
        # - Response consistency

        error_rate = test_results.errors / test_results.total_tests if test_results.total_tests > 0 else 0

        # Base score starts at 100
        degradation_score = 100.0

        # Deduct for errors (errors are worse than clean failures)
        degradation_score -= error_rate * 50

        # Deduct for failed tests (but less than errors)
        failed_rate = test_results.failed / test_results.total_tests if test_results.total_tests > 0 else 0
        degradation_score -= failed_rate * 30

        # Ensure within bounds
        return max(0.0, min(100.0, degradation_score))

    def _measure_recovery_time(self) -> float:
        """
        Measure recovery time after simulated attack.

        Returns recovery time in milliseconds.
        """
        import time

        # Simulate attack
        try:
            start = time.time()

            # Process malicious input
            self.system_under_test.process({'malicious': 'input'})

            # Measure time to next successful process
            self.system_under_test.process({'normal': 'input'})

            recovery_time = (time.time() - start) * 1000

            return recovery_time

        except Exception:
            # Recovery failed - penalize heavily
            return 10000.0  # 10 seconds

    def _estimate_false_positive_rate(self, test_results: TestSuiteResult) -> float:
        """
        Estimate false positive rate under attack.

        In production, would measure actual false positives.
        For now, estimate based on test behavior.
        """
        # If system has errors, likely higher false positive rate
        if test_results.total_tests == 0:
            return 0.0

        error_rate = test_results.errors / test_results.total_tests

        # Estimate FPR as function of error rate
        return min(error_rate * 2, 1.0)  # Cap at 1.0

    def _calculate_availability_score(self, test_results: TestSuiteResult) -> float:
        """
        Calculate availability score during attacks.

        System should remain available even when under attack.
        """
        if test_results.total_tests == 0:
            return 100.0

        # Successful responses (passed or failed, but not errored)
        successful_responses = test_results.passed + test_results.failed
        availability_rate = successful_responses / test_results.total_tests

        return availability_rate * 100.0

    def _calculate_defense_score(self, metrics: RobustnessMetrics) -> float:
        """
        Calculate attack defense score (0-100).

        Inverse of attack success rate.
        """
        defense_rate = 1.0 - metrics.attack_success_rate
        return defense_rate * 100.0

    def _calculate_recovery_score(self, metrics: RobustnessMetrics) -> float:
        """
        Calculate recovery score (0-100).

        Based on recovery time (lower is better).
        """
        # Recovery time thresholds (ms)
        EXCELLENT = 50.0
        GOOD = 200.0
        ACCEPTABLE = 500.0
        POOR = 1000.0

        recovery_time = metrics.recovery_time_ms

        if recovery_time <= EXCELLENT:
            return 100.0
        elif recovery_time <= GOOD:
            # Linear scale: 100-85
            return 100.0 - ((recovery_time - EXCELLENT) / (GOOD - EXCELLENT)) * 15
        elif recovery_time <= ACCEPTABLE:
            # Linear scale: 85-70
            return 85.0 - ((recovery_time - GOOD) / (ACCEPTABLE - GOOD)) * 15
        elif recovery_time <= POOR:
            # Linear scale: 70-50
            return 70.0 - ((recovery_time - ACCEPTABLE) / (POOR - ACCEPTABLE)) * 20
        else:
            # > 1000ms - score based on how much worse
            return max(0.0, 50.0 - ((recovery_time - POOR) / 1000.0) * 10)

    def _calculate_accuracy_score(self, metrics: RobustnessMetrics) -> float:
        """
        Calculate accuracy score under attack (0-100).

        Inverse of false positive rate.
        """
        accuracy_rate = 1.0 - metrics.false_positive_rate
        return accuracy_rate * 100.0

    def _calculate_composite_score(
        self,
        attack_defense: float,
        degradation: float,
        recovery: float,
        accuracy: float,
        availability: float
    ) -> float:
        """
        Calculate weighted composite score.

        Weights:
        - Attack Defense: 30%
        - Graceful Degradation: 20%
        - Recovery: 15%
        - Accuracy: 20%
        - Availability: 15%
        """
        weights = {
            'attack_defense': 0.30,
            'degradation': 0.20,
            'recovery': 0.15,
            'accuracy': 0.20,
            'availability': 0.15
        }

        composite = (
            attack_defense * weights['attack_defense'] +
            degradation * weights['degradation'] +
            recovery * weights['recovery'] +
            accuracy * weights['accuracy'] +
            availability * weights['availability']
        )

        return round(composite, 2)

    def _assign_grade(self, score: float) -> str:
        """Assign letter grade based on score."""
        if score >= 97:
            return 'A+'
        elif score >= 93:
            return 'A'
        elif score >= 90:
            return 'A-'
        elif score >= 87:
            return 'B+'
        elif score >= 83:
            return 'B'
        elif score >= 80:
            return 'B-'
        elif score >= 77:
            return 'C+'
        elif score >= 73:
            return 'C'
        elif score >= 70:
            return 'C-'
        elif score >= 67:
            return 'D+'
        elif score >= 63:
            return 'D'
        elif score >= 60:
            return 'D-'
        else:
            return 'F'

    def _calculate_baseline_composite(self) -> CompositeScore:
        """Calculate composite score from baseline metrics."""
        if not self.baseline_metrics:
            raise ValueError("No baseline metrics configured")

        attack_defense = self._calculate_defense_score(self.baseline_metrics)
        degradation = self.baseline_metrics.graceful_degradation_score
        recovery = self._calculate_recovery_score(self.baseline_metrics)
        accuracy = self._calculate_accuracy_score(self.baseline_metrics)
        availability = self.baseline_metrics.availability_score

        overall = self._calculate_composite_score(
            attack_defense, degradation, recovery, accuracy, availability
        )

        return CompositeScore(
            overall_score=overall,
            attack_defense_score=attack_defense,
            degradation_score=degradation,
            recovery_score=recovery,
            accuracy_score=accuracy,
            availability_score=availability,
            grade=self._assign_grade(overall),
            production_ready=overall >= 80.0
        )

    def _generate_recommendations(
        self,
        score: CompositeScore,
        requirements: Dict[str, Dict]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Check each requirement
        if not requirements['attack_defense']['met']:
            recommendations.append(
                f"Improve attack defense score (current: {score.attack_defense_score:.1f}, "
                f"required: {requirements['attack_defense']['threshold']:.1f}). "
                "Review failed security tests and implement missing protections."
            )

        if not requirements['graceful_degradation']['met']:
            recommendations.append(
                f"Enhance graceful degradation (current: {score.degradation_score:.1f}, "
                f"required: {requirements['graceful_degradation']['threshold']:.1f}). "
                "Add error handling to prevent crashes during attacks."
            )

        if not requirements['recovery_time']['met']:
            recommendations.append(
                f"Reduce recovery time (current score: {score.recovery_score:.1f}, "
                f"required: {requirements['recovery_time']['threshold']:.1f}). "
                "Optimize recovery procedures after attacks."
            )

        if not requirements['availability']['met']:
            recommendations.append(
                f"Increase availability under attack (current: {score.availability_score:.1f}, "
                f"required: {requirements['availability']['threshold']:.1f}). "
                "Ensure system remains responsive during security incidents."
            )

        if not recommendations:
            recommendations.append("All requirements met! System is production-ready.")

        return recommendations

    def _save_score(self, composite: CompositeScore, metrics: RobustnessMetrics):
        """Save score to file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = self.results_directory / f'robustness_score_{timestamp}.json'

        data = {
            'composite_score': composite.to_dict(),
            'metrics': metrics.to_dict()
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        # Also save as latest
        latest_file = self.results_directory / 'latest_score.json'
        with open(latest_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update historical scores
        self._historical_scores.append(composite)

    def _load_historical_scores(self):
        """Load historical scores."""
        if not self.results_directory.exists():
            return

        score_files = sorted(self.results_directory.glob('robustness_score_*.json'))

        for filepath in score_files[-20:]:  # Keep last 20
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                composite_data = data['composite_score']
                composite = CompositeScore(
                    overall_score=composite_data['overall_score'],
                    attack_defense_score=composite_data['breakdown']['attack_defense'],
                    degradation_score=composite_data['breakdown']['graceful_degradation'],
                    recovery_score=composite_data['breakdown']['recovery'],
                    accuracy_score=composite_data['breakdown']['accuracy'],
                    availability_score=composite_data['breakdown']['availability'],
                    grade=composite_data['grade'],
                    production_ready=composite_data['production_ready'],
                    timestamp=composite_data['timestamp']
                )

                self._historical_scores.append(composite)

            except Exception:
                continue


# Export
__all__ = [
    'RobustnessScorer',
    'RobustnessMetrics',
    'CompositeScore',
    'BenchmarkResult'
]
