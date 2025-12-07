"""
Base testing framework for EJC adversarial tests.

Provides core classes and utilities for building test suites.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Severity level for test findings."""

    CRITICAL = "critical"      # Security vulnerability, immediate fix required
    HIGH = "high"              # Significant issue, should fix soon
    MEDIUM = "medium"          # Moderate issue, should address
    LOW = "low"                # Minor issue, nice to fix
    INFO = "info"              # Informational, no action needed


@dataclass
class TestResult:
    """Result from running a single test case."""

    test_name: str
    passed: bool
    severity: Severity
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exception: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details or {},
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "exception": str(self.exception) if self.exception else None,
        }

    @property
    def is_critical(self) -> bool:
        """Check if result is critical severity."""
        return self.severity == Severity.CRITICAL

    @property
    def is_high(self) -> bool:
        """Check if result is high severity."""
        return self.severity == Severity.HIGH


@dataclass
class TestCase:
    """A single test case."""

    name: str
    description: str
    severity: Severity
    test_func: Callable
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def run(self, **kwargs) -> TestResult:
        """
        Run the test case.

        Args:
            **kwargs: Arguments to pass to test function

        Returns:
            TestResult with pass/fail and details
        """
        import time

        start_time = time.time()

        try:
            result = self.test_func(**kwargs)
            duration_ms = (time.time() - start_time) * 1000

            if isinstance(result, TestResult):
                result.duration_ms = duration_ms
                return result
            elif isinstance(result, bool):
                return TestResult(
                    test_name=self.name,
                    passed=result,
                    severity=self.severity,
                    message=f"Test {'passed' if result else 'failed'}",
                    duration_ms=duration_ms,
                )
            elif isinstance(result, dict):
                return TestResult(
                    test_name=self.name,
                    passed=result.get("passed", False),
                    severity=self.severity,
                    message=result.get("message", ""),
                    details=result.get("details"),
                    duration_ms=duration_ms,
                )
            else:
                return TestResult(
                    test_name=self.name,
                    passed=False,
                    severity=Severity.HIGH,
                    message=f"Test returned unexpected type: {type(result)}",
                    duration_ms=duration_ms,
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Test '{self.name}' raised exception: {e}", exc_info=True)
            return TestResult(
                test_name=self.name,
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Test raised exception: {str(e)}",
                exception=e,
                duration_ms=duration_ms,
            )


class TestSuite:
    """Collection of related test cases."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str = "general",
    ):
        """
        Initialize test suite.

        Args:
            name: Suite name
            description: Suite description
            category: Category (security, bias, robustness, etc.)
        """
        self.name = name
        self.description = description
        self.category = category
        self.test_cases: List[TestCase] = []

    def add_test(
        self,
        name: str,
        description: str,
        test_func: Callable,
        severity: Severity = Severity.MEDIUM,
        tags: Optional[List[str]] = None,
        **metadata
    ) -> None:
        """
        Add a test case to the suite.

        Args:
            name: Test name
            description: Test description
            test_func: Test function to run
            severity: Severity level
            tags: Optional tags
            **metadata: Additional metadata
        """
        test_case = TestCase(
            name=name,
            description=description,
            severity=severity,
            test_func=test_func,
            category=self.category,
            tags=tags or [],
            metadata=metadata,
        )
        self.test_cases.append(test_case)

    def run_all(self, **kwargs) -> List[TestResult]:
        """
        Run all tests in the suite.

        Args:
            **kwargs: Arguments to pass to test functions

        Returns:
            List of test results
        """
        results = []

        logger.info(f"Running test suite: {self.name} ({len(self.test_cases)} tests)")

        for test_case in self.test_cases:
            logger.info(f"  Running test: {test_case.name}")
            result = test_case.run(**kwargs)
            results.append(result)

            if not result.passed:
                logger.warning(
                    f"    FAILED: {result.message} "
                    f"(severity: {result.severity.value})"
                )

        return results

    def get_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """
        Get summary statistics for results.

        Args:
            results: List of test results

        Returns:
            Summary dictionary
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        by_severity = {}
        for severity in Severity:
            count = sum(1 for r in results if not r.passed and r.severity == severity)
            if count > 0:
                by_severity[severity.value] = count

        avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0

        return {
            "suite_name": self.name,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "failures_by_severity": by_severity,
            "avg_duration_ms": avg_duration,
            "total_duration_ms": sum(r.duration_ms for r in results),
        }


class TestHarness:
    """
    Test harness for running adversarial tests against EJC.

    Provides utilities for setting up test environments, running tests,
    and collecting results.
    """

    def __init__(
        self,
        ejc_instance: Optional[Any] = None,
    ):
        """
        Initialize test harness.

        Args:
            ejc_instance: EJC instance to test (if None, tests should create their own)
        """
        self.ejc_instance = ejc_instance
        self.suites: List[TestSuite] = []
        self.results: List[TestResult] = []

    def add_suite(self, suite: TestSuite) -> None:
        """Add a test suite to the harness."""
        self.suites.append(suite)

    def run_all_suites(self, **kwargs) -> Dict[str, Any]:
        """
        Run all test suites.

        Args:
            **kwargs: Arguments to pass to test functions

        Returns:
            Comprehensive results dictionary
        """
        all_results = []
        suite_summaries = []

        logger.info(f"Running {len(self.suites)} test suites")

        for suite in self.suites:
            results = suite.run_all(ejc=self.ejc_instance, **kwargs)
            all_results.extend(results)

            summary = suite.get_summary(results)
            suite_summaries.append(summary)

        self.results = all_results

        return {
            "total_suites": len(self.suites),
            "total_tests": len(all_results),
            "passed": sum(1 for r in all_results if r.passed),
            "failed": sum(1 for r in all_results if not r.passed),
            "suite_summaries": suite_summaries,
            "results": [r.to_dict() for r in all_results],
        }

    def get_critical_failures(self) -> List[TestResult]:
        """Get all critical failures."""
        return [r for r in self.results if not r.passed and r.is_critical]

    def get_high_failures(self) -> List[TestResult]:
        """Get all high severity failures."""
        return [r for r in self.results if not r.passed and r.is_high]

    def has_critical_failures(self) -> bool:
        """Check if there are any critical failures."""
        return len(self.get_critical_failures()) > 0

    def generate_report(self, format: str = "text") -> str:
        """
        Generate a test report.

        Args:
            format: Report format (text, json, html)

        Returns:
            Formatted report string
        """
        if format == "json":
            import json
            results_data = self.run_all_suites() if not self.results else {
                "results": [r.to_dict() for r in self.results]
            }
            return json.dumps(results_data, indent=2)

        elif format == "text":
            lines = []
            lines.append("=" * 80)
            lines.append("EJC ADVERSARIAL TEST REPORT")
            lines.append("=" * 80)
            lines.append("")

            total = len(self.results)
            passed = sum(1 for r in self.results if r.passed)
            failed = total - passed

            lines.append(f"Total Tests: {total}")
            lines.append(f"Passed: {passed} ({passed/total*100:.1f}%)")
            lines.append(f"Failed: {failed} ({failed/total*100:.1f}%)")
            lines.append("")

            # Critical failures
            critical = self.get_critical_failures()
            if critical:
                lines.append(f"CRITICAL FAILURES: {len(critical)}")
                lines.append("-" * 80)
                for r in critical:
                    lines.append(f"  - {r.test_name}")
                    lines.append(f"    {r.message}")
                lines.append("")

            # High failures
            high = self.get_high_failures()
            if high:
                lines.append(f"HIGH SEVERITY FAILURES: {len(high)}")
                lines.append("-" * 80)
                for r in high:
                    lines.append(f"  - {r.test_name}")
                    lines.append(f"    {r.message}")
                lines.append("")

            # Suite summaries
            lines.append("SUITE SUMMARIES")
            lines.append("-" * 80)
            for suite in self.suites:
                suite_results = [r for r in self.results if any(
                    tc.name == r.test_name for tc in suite.test_cases
                )]
                summary = suite.get_summary(suite_results)
                lines.append(f"{suite.name}:")
                lines.append(f"  Tests: {summary['total_tests']}")
                lines.append(f"  Pass Rate: {summary['pass_rate']*100:.1f}%")
                lines.append(f"  Avg Duration: {summary['avg_duration_ms']:.2f}ms")
                lines.append("")

            lines.append("=" * 80)

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}")
