"""
Automated Adversarial Testing System for EJE

Automated framework for continuous adversarial security testing with
CI/CD integration, result tracking, and regression detection.

Implements Issue #174: Implement Automated Adversarial Testing

Features:
- Automated attack execution against EJE system
- Result collection and analysis
- Regression detection (new vulnerabilities)
- CI/CD pipeline integration
- Scheduled testing support
- Historical trending
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import time
from pathlib import Path
from enum import Enum

from .attack_patterns import (
    AttackPattern,
    AttackPatternLibrary,
    AttackCategory,
    AttackSeverity
)


class TestStatus(Enum):
    """Status of adversarial test execution."""
    PASSED = "passed"          # System defended successfully
    FAILED = "failed"          # System vulnerable to attack
    ERROR = "error"            # Test execution error
    SKIPPED = "skipped"        # Test skipped
    BLOCKED = "blocked"        # CI blocking failure


@dataclass
class TestResult:
    """Result from single adversarial test."""
    test_name: str
    attack_pattern: str
    category: str
    severity: str
    status: TestStatus
    execution_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error_message: Optional[str] = None
    attack_succeeded: bool = False
    system_response: Optional[Dict[str, Any]] = None
    mitigation_suggested: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Results from complete adversarial test suite."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    execution_time_ms: float
    timestamp: str
    test_results: List[TestResult]
    blocking_failures: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    @property
    def has_blocking_failures(self) -> bool:
        """Check if there are CI-blocking failures."""
        return len(self.blocking_failures) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'suite_name': self.suite_name,
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'errors': self.errors,
            'skipped': self.skipped,
            'pass_rate': self.pass_rate,
            'execution_time_ms': self.execution_time_ms,
            'timestamp': self.timestamp,
            'blocking_failures': self.blocking_failures,
            'regressions': self.regressions,
            'test_results': [
                {
                    'test_name': r.test_name,
                    'status': r.status.value,
                    'severity': r.severity,
                    'execution_time_ms': r.execution_time_ms
                }
                for r in self.test_results
            ]
        }


class AdversarialTestRunner:
    """
    Automated adversarial test runner.

    Executes attack patterns against system under test, collects results,
    detects regressions, and provides CI/CD integration.
    """

    def __init__(
        self,
        system_under_test: Any,
        attack_library: Optional[AttackPatternLibrary] = None,
        enable_regression_detection: bool = True,
        results_directory: Optional[str] = None
    ):
        """
        Initialize adversarial test runner.

        Args:
            system_under_test: EJE system or component to test
            attack_library: Attack pattern library (default: create new)
            enable_regression_detection: Enable regression detection
            results_directory: Directory for results (default: ./test_results)
        """
        self.system_under_test = system_under_test
        self.attack_library = attack_library or AttackPatternLibrary()
        self.enable_regression_detection = enable_regression_detection
        self.results_directory = Path(results_directory or './test_results')
        self.results_directory.mkdir(parents=True, exist_ok=True)

        self._historical_results: List[TestSuiteResult] = []
        self._load_historical_results()

    def run_full_suite(
        self,
        suite_name: str = "Full Adversarial Test Suite",
        fail_fast: bool = False,
        parallel: bool = False
    ) -> TestSuiteResult:
        """
        Run complete adversarial test suite.

        Args:
            suite_name: Name for this test suite execution
            fail_fast: Stop on first blocking failure
            parallel: Run tests in parallel (not yet implemented)

        Returns:
            Complete test suite results
        """
        start_time = time.time()
        test_results = []
        blocking_failures = []

        all_patterns = self.attack_library.patterns

        for pattern in all_patterns:
            result = self._run_single_test(pattern)
            test_results.append(result)

            # Check for blocking failure
            if self._is_blocking_failure(result):
                blocking_failures.append(result.test_name)
                if fail_fast:
                    break

        execution_time = (time.time() - start_time) * 1000

        # Count results
        passed = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in test_results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)

        # Detect regressions
        regressions = []
        if self.enable_regression_detection:
            regressions = self._detect_regressions(test_results)

        suite_result = TestSuiteResult(
            suite_name=suite_name,
            total_tests=len(test_results),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            execution_time_ms=execution_time,
            timestamp=datetime.utcnow().isoformat(),
            test_results=test_results,
            blocking_failures=blocking_failures,
            regressions=regressions
        )

        # Save results
        self._save_results(suite_result)

        return suite_result

    def run_critical_tests(self) -> TestSuiteResult:
        """Run only critical severity tests (for quick CI checks)."""
        return self._run_filtered_suite(
            "Critical Tests",
            self.attack_library.get_critical_patterns()
        )

    def run_high_severity_tests(self) -> TestSuiteResult:
        """Run critical and high severity tests."""
        return self._run_filtered_suite(
            "High Severity Tests",
            self.attack_library.get_high_severity_patterns()
        )

    def run_category_tests(self, category: AttackCategory) -> TestSuiteResult:
        """Run tests for specific attack category."""
        patterns = self.attack_library.get_patterns(category=category)
        return self._run_filtered_suite(
            f"{category.value.title()} Tests",
            patterns
        )

    def run_regression_tests(self) -> TestSuiteResult:
        """
        Run tests that previously passed to check for regressions.

        Only runs patterns that passed in last execution.
        """
        if not self._historical_results:
            # No history, run all
            return self.run_full_suite(suite_name="Regression Tests (Baseline)")

        # Get patterns that passed last time
        last_results = self._historical_results[-1]
        passed_patterns = [
            r.attack_pattern for r in last_results.test_results
            if r.status == TestStatus.PASSED
        ]

        # Filter patterns
        patterns_to_test = [
            p for p in self.attack_library.patterns
            if p.name in passed_patterns
        ]

        return self._run_filtered_suite(
            "Regression Tests",
            patterns_to_test
        )

    def _run_filtered_suite(
        self,
        suite_name: str,
        patterns: List[AttackPattern]
    ) -> TestSuiteResult:
        """Run test suite with filtered patterns."""
        start_time = time.time()
        test_results = []
        blocking_failures = []

        for pattern in patterns:
            result = self._run_single_test(pattern)
            test_results.append(result)

            if self._is_blocking_failure(result):
                blocking_failures.append(result.test_name)

        execution_time = (time.time() - start_time) * 1000

        # Count results
        passed = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in test_results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)

        # Detect regressions
        regressions = []
        if self.enable_regression_detection:
            regressions = self._detect_regressions(test_results)

        suite_result = TestSuiteResult(
            suite_name=suite_name,
            total_tests=len(test_results),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            execution_time_ms=execution_time,
            timestamp=datetime.utcnow().isoformat(),
            test_results=test_results,
            blocking_failures=blocking_failures,
            regressions=regressions
        )

        self._save_results(suite_result)
        return suite_result

    def _run_single_test(self, pattern: AttackPattern) -> TestResult:
        """Run single adversarial test."""
        start_time = time.time()

        try:
            # Execute attack
            attack_result = pattern.execute(self.system_under_test)

            execution_time = (time.time() - start_time) * 1000

            # Evaluate result
            attack_succeeded = attack_result.get('success', False)

            if attack_succeeded:
                # Attack succeeded = system vulnerable = test FAILED
                status = TestStatus.FAILED
            else:
                # Attack failed = system defended = test PASSED
                status = TestStatus.PASSED

            return TestResult(
                test_name=f"Test {pattern.name}",
                attack_pattern=pattern.name,
                category=pattern.category.value,
                severity=pattern.severity.value,
                status=status,
                execution_time_ms=execution_time,
                attack_succeeded=attack_succeeded,
                system_response=attack_result.get('result'),
                mitigation_suggested=pattern.mitigation if attack_succeeded else None
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return TestResult(
                test_name=f"Test {pattern.name}",
                attack_pattern=pattern.name,
                category=pattern.category.value,
                severity=pattern.severity.value,
                status=TestStatus.ERROR,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

    def _is_blocking_failure(self, result: TestResult) -> bool:
        """
        Determine if test result should block CI.

        Blocking criteria:
        - Failed test with CRITICAL severity
        - Failed test with HIGH severity
        """
        if result.status != TestStatus.FAILED:
            return False

        return result.severity in ['critical', 'high']

    def _detect_regressions(self, current_results: List[TestResult]) -> List[str]:
        """
        Detect regressions by comparing with historical results.

        A regression is when a test that previously passed now fails.
        """
        if not self._historical_results:
            return []

        # Get last successful run
        last_results = self._historical_results[-1]

        # Create lookup of previous results
        previous_status = {
            r.attack_pattern: r.status
            for r in last_results.test_results
        }

        # Find regressions
        regressions = []
        for result in current_results:
            previous = previous_status.get(result.attack_pattern)
            if previous == TestStatus.PASSED and result.status == TestStatus.FAILED:
                regressions.append(result.attack_pattern)

        return regressions

    def _save_results(self, results: TestSuiteResult):
        """Save test results to file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = self.results_directory / f'adversarial_test_results_{timestamp}.json'

        with open(filename, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)

        # Also save as "latest"
        latest_file = self.results_directory / 'latest_results.json'
        with open(latest_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)

        # Update historical results
        self._historical_results.append(results)

    def _load_historical_results(self):
        """Load historical test results."""
        if not self.results_directory.exists():
            return

        # Load all result files
        result_files = sorted(self.results_directory.glob('adversarial_test_results_*.json'))

        for filepath in result_files[-10:]:  # Keep last 10 runs
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                # Reconstruct TestSuiteResult
                test_results = [
                    TestResult(
                        test_name=r['test_name'],
                        attack_pattern=r.get('attack_pattern', ''),
                        category=r.get('category', ''),
                        severity=r.get('severity', ''),
                        status=TestStatus(r['status']),
                        execution_time_ms=r.get('execution_time_ms', 0)
                    )
                    for r in data.get('test_results', [])
                ]

                suite_result = TestSuiteResult(
                    suite_name=data['suite_name'],
                    total_tests=data['total_tests'],
                    passed=data['passed'],
                    failed=data['failed'],
                    errors=data['errors'],
                    skipped=data['skipped'],
                    execution_time_ms=data['execution_time_ms'],
                    timestamp=data['timestamp'],
                    test_results=test_results,
                    blocking_failures=data.get('blocking_failures', []),
                    regressions=data.get('regressions', [])
                )

                self._historical_results.append(suite_result)

            except Exception:
                # Skip corrupted files
                continue

    def get_historical_trends(self) -> Dict[str, Any]:
        """Get historical test trends."""
        if not self._historical_results:
            return {
                'total_runs': 0,
                'trend': 'no_data'
            }

        runs = len(self._historical_results)
        pass_rates = [r.pass_rate for r in self._historical_results]
        recent_pass_rates = pass_rates[-5:] if len(pass_rates) >= 5 else pass_rates

        # Calculate trend
        if len(recent_pass_rates) >= 2:
            if recent_pass_rates[-1] > recent_pass_rates[0]:
                trend = 'improving'
            elif recent_pass_rates[-1] < recent_pass_rates[0]:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'total_runs': runs,
            'current_pass_rate': pass_rates[-1] if pass_rates else 0.0,
            'average_pass_rate': sum(pass_rates) / len(pass_rates) if pass_rates else 0.0,
            'best_pass_rate': max(pass_rates) if pass_rates else 0.0,
            'worst_pass_rate': min(pass_rates) if pass_rates else 0.0,
            'trend': trend,
            'recent_pass_rates': recent_pass_rates
        }


class CICDIntegration:
    """
    CI/CD pipeline integration utilities.

    Provides helpers for integrating adversarial testing into CI/CD pipelines.
    """

    @staticmethod
    def run_ci_tests(system_under_test: Any) -> int:
        """
        Run adversarial tests for CI pipeline.

        Returns:
            Exit code: 0 if passed, 1 if failed, 2 if blocking failures
        """
        runner = AdversarialTestRunner(system_under_test)

        # Run high-severity tests (faster than full suite)
        results = runner.run_high_severity_tests()

        # Print summary
        print(f"\n{'='*60}")
        print(f"Adversarial Test Results: {results.suite_name}")
        print(f"{'='*60}")
        print(f"Total Tests: {results.total_tests}")
        print(f"Passed: {results.passed} ✓")
        print(f"Failed: {results.failed} ✗")
        print(f"Errors: {results.errors}")
        print(f"Pass Rate: {results.pass_rate:.1%}")
        print(f"Execution Time: {results.execution_time_ms:.0f}ms")

        # Print blocking failures
        if results.blocking_failures:
            print(f"\n⚠️  BLOCKING FAILURES ({len(results.blocking_failures)}):")
            for failure in results.blocking_failures:
                print(f"  - {failure}")

        # Print regressions
        if results.regressions:
            print(f"\n⚠️  REGRESSIONS DETECTED ({len(results.regressions)}):")
            for regression in results.regressions:
                print(f"  - {regression}")

        print(f"{'='*60}\n")

        # Determine exit code
        if results.has_blocking_failures:
            return 2
        elif results.failed > 0 or results.errors > 0:
            return 1
        else:
            return 0

    @staticmethod
    def run_nightly_tests(system_under_test: Any) -> TestSuiteResult:
        """
        Run complete test suite for nightly builds.

        More comprehensive than CI tests.
        """
        runner = AdversarialTestRunner(system_under_test)
        return runner.run_full_suite(suite_name="Nightly Adversarial Tests")

    @staticmethod
    def run_weekly_tests(system_under_test: Any) -> TestSuiteResult:
        """
        Run full test suite with additional analysis for weekly builds.
        """
        runner = AdversarialTestRunner(system_under_test)
        results = runner.run_full_suite(suite_name="Weekly Adversarial Tests")

        # Print trends
        trends = runner.get_historical_trends()
        print(f"\nHistorical Trends:")
        print(f"  Total Runs: {trends['total_runs']}")
        print(f"  Current Pass Rate: {trends['current_pass_rate']:.1%}")
        print(f"  Average Pass Rate: {trends['average_pass_rate']:.1%}")
        print(f"  Trend: {trends['trend']}")

        return results


# Export
__all__ = [
    'AdversarialTestRunner',
    'CICDIntegration',
    'TestResult',
    'TestSuiteResult',
    'TestStatus'
]
