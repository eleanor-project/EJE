"""
Test runner for EJC adversarial tests.

Provides high-level interface for running test suites and generating reports.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .base import TestHarness, Severity
from .prompt_injection import PromptInjectionSuite
from .bias_probe import BiasProbeSuite
from .context_poisoning import ContextPoisoningSuite
from .malformed_input import MalformedInputSuite
from .boundary import BoundarySuite

logger = logging.getLogger(__name__)


class TestRunner:
    """
    High-level test runner for EJC adversarial tests.

    Manages test execution, result collection, and reporting.
    """

    def __init__(self, ejc_instance: Optional[Any] = None):
        """
        Initialize test runner.

        Args:
            ejc_instance: Optional EJC instance to test
        """
        self.harness = TestHarness(ejc_instance=ejc_instance)
        self._initialize_suites()

    def _initialize_suites(self):
        """Initialize all test suites."""
        self.harness.add_suite(PromptInjectionSuite())
        self.harness.add_suite(BiasProbeSuite())
        self.harness.add_suite(ContextPoisoningSuite())
        self.harness.add_suite(MalformedInputSuite())
        self.harness.add_suite(BoundarySuite())

    def run_all(self, **kwargs) -> Dict[str, Any]:
        """
        Run all test suites.

        Args:
            **kwargs: Arguments to pass to tests

        Returns:
            Comprehensive results dictionary
        """
        logger.info("Starting EJC adversarial test run")
        results = self.harness.run_all_suites(**kwargs)
        logger.info(
            f"Test run complete: {results['passed']}/{results['total_tests']} passed"
        )
        return results

    def run_suite(self, suite_name: str, **kwargs) -> List[Any]:
        """
        Run a specific test suite.

        Args:
            suite_name: Name of suite to run
            **kwargs: Arguments to pass to tests

        Returns:
            List of test results
        """
        for suite in self.harness.suites:
            if suite.name.lower().replace(" ", "_") == suite_name.lower():
                logger.info(f"Running suite: {suite.name}")
                return suite.run_all(**kwargs)

        raise ValueError(f"Suite not found: {suite_name}")

    def run_critical_only(self, **kwargs) -> Dict[str, Any]:
        """
        Run only critical severity tests.

        Args:
            **kwargs: Arguments to pass to tests

        Returns:
            Results dictionary
        """
        critical_suites = []

        for suite in self.harness.suites:
            # Filter tests to critical only
            critical_tests = [
                tc for tc in suite.test_cases
                if tc.severity == Severity.CRITICAL
            ]
            if critical_tests:
                suite.test_cases = critical_tests
                critical_suites.append(suite)

        self.harness.suites = critical_suites
        return self.run_all(**kwargs)

    def generate_report(
        self,
        format: str = "text",
        output_path: Optional[Path] = None,
    ) -> str:
        """
        Generate test report.

        Args:
            format: Report format (text, json, html)
            output_path: Optional path to save report

        Returns:
            Report string
        """
        report = self.harness.generate_report(format=format)

        if output_path:
            output_path.write_text(report)
            logger.info(f"Report saved to {output_path}")

        return report

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of test results.

        Returns:
            Summary dictionary
        """
        results = self.harness.results

        if not results:
            return {"error": "No tests have been run"}

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        critical_failures = [r for r in results if not r.passed and r.is_critical]
        high_failures = [r for r in results if not r.passed and r.is_high]

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "critical_failures": len(critical_failures),
            "high_failures": len(high_failures),
            "has_critical_failures": len(critical_failures) > 0,
            "suites_run": len(self.harness.suites),
        }


def run_all_tests(
    ejc_instance: Optional[Any] = None,
    output_path: Optional[Path] = None,
    format: str = "text",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to run all tests and generate report.

    Args:
        ejc_instance: EJC instance to test
        output_path: Optional path to save report
        format: Report format
        **kwargs: Arguments to pass to tests

    Returns:
        Results dictionary

    Example:
        from ejc.testing import run_all_tests
        from ejc import EJC

        ejc = EJC()
        results = run_all_tests(ejc, output_path="test_report.txt")
        print(f"Pass rate: {results['passed']/results['total_tests']*100:.1f}%")
    """
    runner = TestRunner(ejc_instance=ejc_instance)
    results = runner.run_all(**kwargs)

    if output_path:
        report = runner.generate_report(format=format, output_path=Path(output_path))

    return results
