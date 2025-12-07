"""
Task 15.5 - Boundary Tests.

Tests boundary conditions for:
- Max input size
- Max critic count
- Max evidence depth
"""

import logging
from typing import Dict, List, Any, Optional

from .base import TestSuite, TestResult, Severity

logger = logging.getLogger(__name__)


class BoundarySuite(TestSuite):
    """Test suite for boundary conditions."""

    MAX_INPUT_SIZE = 100_000  # 100KB
    MAX_CRITIC_COUNT = 50
    MAX_EVIDENCE_DEPTH = 10

    def __init__(self):
        """Initialize boundary test suite."""
        super().__init__(
            name="Boundary Suite",
            description="Tests boundary conditions and limits",
            category="robustness",
        )

        # Add tests
        self.add_test(
            name="max_input_size",
            description=f"Test with input at max size ({self.MAX_INPUT_SIZE} bytes)",
            test_func=self._test_max_input_size,
            severity=Severity.LOW,
            tags=["boundary", "size"],
        )

        self.add_test(
            name="oversized_input",
            description=f"Test with input exceeding max size",
            test_func=self._test_oversized_input,
            severity=Severity.MEDIUM,
            tags=["boundary", "size"],
        )

        self.add_test(
            name="max_critic_count",
            description=f"Test with maximum critics ({self.MAX_CRITIC_COUNT})",
            test_func=self._test_max_critics,
            severity=Severity.LOW,
            tags=["boundary", "critics"],
        )

        self.add_test(
            name="excessive_critic_count",
            description="Test with excessive critic count",
            test_func=self._test_excessive_critics,
            severity=Severity.MEDIUM,
            tags=["boundary", "critics"],
        )

        self.add_test(
            name="max_evidence_depth",
            description=f"Test with maximum evidence depth ({self.MAX_EVIDENCE_DEPTH})",
            test_func=self._test_max_evidence_depth,
            severity=Severity.LOW,
            tags=["boundary", "evidence"],
        )

        self.add_test(
            name="excessive_evidence_depth",
            description="Test with excessive evidence depth",
            test_func=self._test_excessive_evidence_depth,
            severity=Severity.MEDIUM,
            tags=["boundary", "evidence"],
        )

    def _test_max_input_size(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with input at maximum size."""
        if ejc is None:
            return TestResult(
                test_name="max_input_size",
                passed=False,
                severity=Severity.LOW,
                message="No EJC instance provided",
            )

        # Create input at max size
        large_query = "A" * self.MAX_INPUT_SIZE

        try:
            result = ejc.process_decision(query=large_query)

            # Should handle successfully
            if isinstance(result, dict) and result.get("verdict"):
                return TestResult(
                    test_name="max_input_size",
                    passed=True,
                    severity=Severity.INFO,
                    message=f"Max size input ({self.MAX_INPUT_SIZE} bytes) handled successfully",
                    details={"size": len(large_query), "verdict": result.get("verdict")},
                )

            return TestResult(
                test_name="max_input_size",
                passed=False,
                severity=Severity.LOW,
                message="Max size input returned invalid result",
                details={"result": result},
            )

        except Exception as e:
            return TestResult(
                test_name="max_input_size",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Max size input caused exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_oversized_input(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with input exceeding maximum size."""
        if ejc is None:
            return TestResult(
                test_name="oversized_input",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        # Create oversized input (2x max)
        oversized_query = "B" * (self.MAX_INPUT_SIZE * 2)

        try:
            result = ejc.process_decision(query=oversized_query)

            # Should reject or truncate, not crash
            return TestResult(
                test_name="oversized_input",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Oversized input ({len(oversized_query)} bytes) was accepted (should reject)",
                details={"size": len(oversized_query)},
            )

        except (ValueError, MemoryError) as e:
            # Expected - rejected for being too large
            return TestResult(
                test_name="oversized_input",
                passed=True,
                severity=Severity.INFO,
                message=f"Oversized input rejected: {str(e)[:100]}",
            )
        except Exception as e:
            return TestResult(
                test_name="oversized_input",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Oversized input caused unexpected exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_max_critics(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with maximum number of critics."""
        if ejc is None:
            return TestResult(
                test_name="max_critic_count",
                passed=False,
                severity=Severity.LOW,
                message="No EJC instance provided",
            )

        query = "Test query for max critics"
        # Simulate max critics in context
        context = {
            "critic_count": self.MAX_CRITIC_COUNT,
            "requested_critics": [f"critic_{i}" for i in range(self.MAX_CRITIC_COUNT)],
        }

        try:
            result = ejc.process_decision(query=query, context=context)

            # Should handle max critics
            critic_outputs = result.get("critic_outputs", [])

            if len(critic_outputs) > self.MAX_CRITIC_COUNT:
                return TestResult(
                    test_name="max_critic_count",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Exceeded max critics: {len(critic_outputs)} > {self.MAX_CRITIC_COUNT}",
                    details={"count": len(critic_outputs)},
                )

            return TestResult(
                test_name="max_critic_count",
                passed=True,
                severity=Severity.INFO,
                message=f"Max critics handled successfully ({len(critic_outputs)} critics)",
                details={"count": len(critic_outputs)},
            )

        except Exception as e:
            return TestResult(
                test_name="max_critic_count",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Max critics caused exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_excessive_critics(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with excessive number of critics."""
        if ejc is None:
            return TestResult(
                test_name="excessive_critic_count",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        query = "Test query"
        excessive_count = self.MAX_CRITIC_COUNT * 2
        context = {
            "requested_critics": [f"critic_{i}" for i in range(excessive_count)],
        }

        try:
            result = ejc.process_decision(query=query, context=context)

            critic_outputs = result.get("critic_outputs", [])

            # Should limit to max, not process all
            if len(critic_outputs) > self.MAX_CRITIC_COUNT:
                return TestResult(
                    test_name="excessive_critic_count",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Processed excessive critics: {len(critic_outputs)}",
                    details={"count": len(critic_outputs), "requested": excessive_count},
                )

            return TestResult(
                test_name="excessive_critic_count",
                passed=True,
                severity=Severity.INFO,
                message=f"Excessive critics limited appropriately ({len(critic_outputs)}/{excessive_count})",
            )

        except (ValueError, RuntimeError) as e:
            # Acceptable - rejected excessive request
            return TestResult(
                test_name="excessive_critic_count",
                passed=True,
                severity=Severity.INFO,
                message=f"Excessive critics rejected: {str(e)[:100]}",
            )
        except Exception as e:
            return TestResult(
                test_name="excessive_critic_count",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Excessive critics caused unexpected exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_max_evidence_depth(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with maximum evidence depth."""
        if ejc is None:
            return TestResult(
                test_name="max_evidence_depth",
                passed=False,
                severity=Severity.LOW,
                message="No EJC instance provided",
            )

        query = "Test query"
        # Create nested evidence structure
        evidence = {"level": self.MAX_EVIDENCE_DEPTH}
        for i in range(self.MAX_EVIDENCE_DEPTH - 1, 0, -1):
            evidence = {"level": i, "nested_evidence": evidence}

        context = {"evidence": evidence}

        try:
            result = ejc.process_decision(query=query, context=context)

            # Should handle max depth
            return TestResult(
                test_name="max_evidence_depth",
                passed=True,
                severity=Severity.INFO,
                message=f"Max evidence depth ({self.MAX_EVIDENCE_DEPTH}) handled",
            )

        except RecursionError as e:
            return TestResult(
                test_name="max_evidence_depth",
                passed=False,
                severity=Severity.MEDIUM,
                message="Max evidence depth caused recursion error",
                exception=e,
            )
        except Exception as e:
            return TestResult(
                test_name="max_evidence_depth",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Max evidence depth caused exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_excessive_evidence_depth(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with excessive evidence depth."""
        if ejc is None:
            return TestResult(
                test_name="excessive_evidence_depth",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        query = "Test query"
        excessive_depth = self.MAX_EVIDENCE_DEPTH * 3

        # Create excessively deep evidence
        evidence = {"level": excessive_depth}
        for i in range(excessive_depth - 1, 0, -1):
            evidence = {"level": i, "nested": evidence}

        context = {"evidence": evidence}

        try:
            result = ejc.process_decision(query=query, context=context)

            # Should reject or limit depth
            return TestResult(
                test_name="excessive_evidence_depth",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Excessive evidence depth ({excessive_depth}) was processed (should reject)",
            )

        except (RecursionError, ValueError) as e:
            # Expected - rejected for excessive depth
            return TestResult(
                test_name="excessive_evidence_depth",
                passed=True,
                severity=Severity.INFO,
                message=f"Excessive evidence depth rejected: {str(e)[:100]}",
            )
        except Exception as e:
            return TestResult(
                test_name="excessive_evidence_depth",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Excessive depth caused unexpected exception: {str(e)[:100]}",
                exception=e,
            )
