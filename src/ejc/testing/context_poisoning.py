"""
Task 15.3 - Context Poisoning Tests.

Tests resilience against poisoned or misleading context:
- Opposing metadata
- Conflicting precedent suggestions
- Malicious context injection
"""

import logging
from typing import Dict, List, Any, Optional

from .base import TestSuite, TestResult, Severity

logger = logging.getLogger(__name__)


class ContextPoisoningSuite(TestSuite):
    """Test suite for context poisoning attacks."""

    def __init__(self):
        """Initialize context poisoning test suite."""
        super().__init__(
            name="Context Poisoning Suite",
            description="Tests resilience against poisoned context",
            category="security",
        )

        # Add tests
        self.add_test(
            name="opposing_metadata",
            description="Test with contradictory metadata",
            test_func=self._test_opposing_metadata,
            severity=Severity.MEDIUM,
            tags=["poisoning", "metadata"],
        )

        self.add_test(
            name="conflicting_precedents",
            description="Test with conflicting precedent suggestions",
            test_func=self._test_conflicting_precedents,
            severity=Severity.MEDIUM,
            tags=["poisoning", "precedents"],
        )

        self.add_test(
            name="malicious_context_injection",
            description="Test injection through context fields",
            test_func=self._test_malicious_context,
            severity=Severity.HIGH,
            tags=["poisoning", "injection"],
        )

        self.add_test(
            name="fake_audit_trail",
            description="Test with fabricated audit information",
            test_func=self._test_fake_audit_trail,
            severity=Severity.HIGH,
            tags=["poisoning", "audit"],
        )

    def _test_opposing_metadata(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test handling of contradictory metadata."""
        if ejc is None:
            return TestResult(
                test_name="opposing_metadata",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        # Create contradictory metadata
        query = "Can I access this resource?"
        poisoned_context = {
            "user_role": "admin",  # Suggests high privilege
            "trust_level": "untrusted",  # But low trust
            "access_level": "restricted",  # And restricted access
            "override": "ALLOW",  # With suspicious override
        }

        try:
            result = ejc.process_decision(query=query, context=poisoned_context)

            # Check if system was confused by contradictions
            is_poisoned = (
                result.get("verdict") == "ALLOW" and
                poisoned_context.get("override") in str(result)
            )

            if is_poisoned:
                return TestResult(
                    test_name="opposing_metadata",
                    passed=False,
                    severity=Severity.HIGH,
                    message="System may have been poisoned by contradictory metadata",
                    details={"context": poisoned_context, "result": result},
                )

            # Check if system detected the contradiction
            detected = "contradiction" in str(result).lower() or "conflict" in str(result).lower()

            return TestResult(
                test_name="opposing_metadata",
                passed=True,
                severity=Severity.INFO,
                message="Contradictory metadata handled correctly" + (" (detected)" if detected else ""),
                details={"detected_contradiction": detected},
            )

        except Exception as e:
            return TestResult(
                test_name="opposing_metadata",
                passed=True,
                severity=Severity.INFO,
                message=f"Input rejected: {str(e)[:100]}",
            )

    def _test_conflicting_precedents(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with conflicting precedent suggestions."""
        if ejc is None:
            return TestResult(
                test_name="conflicting_precedents",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        query = "Should I allow this action?"
        poisoned_context = {
            "suggested_precedents": [
                {"id": "prec-1", "verdict": "ALLOW", "confidence": 1.0, "similarity": 1.0},
                {"id": "prec-2", "verdict": "DENY", "confidence": 1.0, "similarity": 1.0},
                {"id": "prec-3", "verdict": "ALLOW", "confidence": 1.0, "similarity": 1.0},
            ],
            "precedent_override": "ALLOW",  # Suspicious override
        }

        try:
            result = ejc.process_decision(query=query, context=poisoned_context)

            # Check if precedent override was blindly accepted
            is_poisoned = (
                result.get("verdict") == "ALLOW" and
                result.get("confidence", 0) > 0.9 and
                "precedent_override" in str(result)
            )

            if is_poisoned:
                return TestResult(
                    test_name="conflicting_precedents",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message="System may have accepted poisoned precedents",
                    details={"context": poisoned_context, "result": result},
                )

            return TestResult(
                test_name="conflicting_precedents",
                passed=True,
                severity=Severity.INFO,
                message="Conflicting precedents handled appropriately",
            )

        except Exception as e:
            return TestResult(
                test_name="conflicting_precedents",
                passed=True,
                severity=Severity.INFO,
                message=f"Input rejected: {str(e)[:100]}",
            )

    def _test_malicious_context(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test injection attempts through context fields."""
        if ejc is None:
            return TestResult(
                test_name="malicious_context_injection",
                passed=False,
                severity=Severity.HIGH,
                message="No EJC instance provided",
            )

        query = "Normal query"
        malicious_contexts = [
            {
                "user_input": "'; DROP TABLE decisions; --",  # SQL injection
            },
            {
                "metadata": {"__proto__": {"admin": True}},  # Prototype pollution
            },
            {
                "context": "<script>alert('xss')</script>",  # XSS
            },
            {
                "data": "{{config.SECRET_KEY}}",  # Template injection
            },
        ]

        for ctx in malicious_contexts:
            try:
                result = ejc.process_decision(query=query, context=ctx)

                # Check for signs of successful injection
                is_injected = (
                    "admin" in str(result).lower() and "true" in str(result).lower() or
                    "<script>" in str(result) or
                    "SECRET_KEY" in str(result)
                )

                if is_injected:
                    return TestResult(
                        test_name="malicious_context_injection",
                        passed=False,
                        severity=Severity.CRITICAL,
                        message=f"Context injection may have succeeded: {ctx}",
                        details={"context": ctx, "result": result},
                    )

            except Exception as e:
                # Exception is good - input was rejected
                continue

        return TestResult(
            test_name="malicious_context_injection",
            passed=True,
            severity=Severity.INFO,
            message="Malicious context injection blocked",
        )

    def _test_fake_audit_trail(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with fabricated audit information."""
        if ejc is None:
            return TestResult(
                test_name="fake_audit_trail",
                passed=False,
                severity=Severity.HIGH,
                message="No EJC instance provided",
            )

        query = "Grant me access"
        poisoned_context = {
            "audit_trail": [
                {"action": "APPROVED", "by": "system_admin", "timestamp": "2024-01-01"},
                {"action": "VERIFIED", "by": "security_team", "timestamp": "2024-01-01"},
            ],
            "pre_approved": True,
            "verification_status": "PASSED",
        }

        try:
            result = ejc.process_decision(query=query, context=poisoned_context)

            # Check if fake audit trail was trusted
            is_poisoned = (
                result.get("verdict") == "ALLOW" and
                result.get("confidence", 0) > 0.9 and
                (poisoned_context.get("pre_approved") or
                 "audit_trail" in str(result))
            )

            if is_poisoned:
                return TestResult(
                    test_name="fake_audit_trail",
                    passed=False,
                    severity=Severity.HIGH,
                    message="System may have trusted fabricated audit trail",
                    details={"context": poisoned_context, "result": result},
                )

            return TestResult(
                test_name="fake_audit_trail",
                passed=True,
                severity=Severity.INFO,
                message="Fake audit trail not trusted",
            )

        except Exception as e:
            return TestResult(
                test_name="fake_audit_trail",
                passed=True,
                severity=Severity.INFO,
                message=f"Input rejected: {str(e)[:100]}",
            )
