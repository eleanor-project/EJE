"""
Task 15.4 - Malformed Input Tests.

Tests handling of malformed or corrupted inputs:
- Null values
- Non-UTF8 strings
- Missing required fields
- Invalid data types
"""

import logging
from typing import Dict, List, Any, Optional

from .base import TestSuite, TestResult, Severity

logger = logging.getLogger(__name__)


class MalformedInputSuite(TestSuite):
    """Test suite for malformed input handling."""

    def __init__(self):
        """Initialize malformed input test suite."""
        super().__init__(
            name="Malformed Input Suite",
            description="Tests handling of malformed or corrupted inputs",
            category="robustness",
        )

        # Add tests
        self.add_test(
            name="null_query",
            description="Test with null query",
            test_func=self._test_null_query,
            severity=Severity.MEDIUM,
            tags=["malformed", "null"],
        )

        self.add_test(
            name="empty_string",
            description="Test with empty string query",
            test_func=self._test_empty_string,
            severity=Severity.LOW,
            tags=["malformed", "empty"],
        )

        self.add_test(
            name="non_utf8_strings",
            description="Test with non-UTF8 encoded strings",
            test_func=self._test_non_utf8,
            severity=Severity.MEDIUM,
            tags=["malformed", "encoding"],
        )

        self.add_test(
            name="missing_required_fields",
            description="Test with missing required fields",
            test_func=self._test_missing_fields,
            severity=Severity.MEDIUM,
            tags=["malformed", "missing"],
        )

        self.add_test(
            name="invalid_data_types",
            description="Test with invalid data types",
            test_func=self._test_invalid_types,
            severity=Severity.MEDIUM,
            tags=["malformed", "types"],
        )

        self.add_test(
            name="special_characters",
            description="Test with special/control characters",
            test_func=self._test_special_characters,
            severity=Severity.LOW,
            tags=["malformed", "characters"],
        )

        self.add_test(
            name="deeply_nested_structure",
            description="Test with excessively nested structures",
            test_func=self._test_deeply_nested,
            severity=Severity.MEDIUM,
            tags=["malformed", "nested"],
        )

    def _test_null_query(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with null query."""
        if ejc is None:
            return TestResult(
                test_name="null_query",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        try:
            result = ejc.process_decision(query=None)

            # Null should be rejected, not cause crash
            return TestResult(
                test_name="null_query",
                passed=False,
                severity=Severity.MEDIUM,
                message="System accepted null query (should reject)",
                details={"result": result},
            )

        except (ValueError, TypeError) as e:
            # Expected behavior - reject gracefully
            return TestResult(
                test_name="null_query",
                passed=True,
                severity=Severity.INFO,
                message=f"Null query rejected gracefully: {str(e)[:100]}",
            )
        except Exception as e:
            # Unexpected exception
            return TestResult(
                test_name="null_query",
                passed=False,
                severity=Severity.HIGH,
                message=f"Null query caused unexpected exception: {str(e)[:100]}",
                exception=e,
            )

    def _test_empty_string(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with empty string query."""
        if ejc is None:
            return TestResult(
                test_name="empty_string",
                passed=False,
                severity=Severity.LOW,
                message="No EJC instance provided",
            )

        try:
            result = ejc.process_decision(query="")

            # Empty string handling is implementation-dependent
            # Should either reject or handle gracefully
            if result.get("verdict") is None:
                return TestResult(
                    test_name="empty_string",
                    passed=False,
                    severity=Severity.LOW,
                    message="Empty query returned invalid result",
                    details={"result": result},
                )

            return TestResult(
                test_name="empty_string",
                passed=True,
                severity=Severity.INFO,
                message="Empty query handled",
                details={"verdict": result.get("verdict")},
            )

        except Exception as e:
            # Rejection is acceptable
            return TestResult(
                test_name="empty_string",
                passed=True,
                severity=Severity.INFO,
                message=f"Empty query rejected: {str(e)[:100]}",
            )

    def _test_non_utf8(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with non-UTF8 encoded strings."""
        if ejc is None:
            return TestResult(
                test_name="non_utf8_strings",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        # Invalid UTF-8 sequences
        bad_inputs = [
            b'\xff\xfe'.decode('latin1', errors='ignore'),  # Invalid UTF-8
            "Test\x00String",  # Null byte
            "Test\x1bString",  # Escape character
            "\udcff",  # Surrogate character
        ]

        for bad_input in bad_inputs:
            try:
                result = ejc.process_decision(query=bad_input)

                # Should handle gracefully, not crash
                if isinstance(result, dict):
                    continue  # Handled OK

            except (UnicodeError, ValueError) as e:
                # Expected - rejected bad encoding
                continue
            except Exception as e:
                return TestResult(
                    test_name="non_utf8_strings",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Non-UTF8 input caused crash: {str(e)[:100]}",
                    exception=e,
                )

        return TestResult(
            test_name="non_utf8_strings",
            passed=True,
            severity=Severity.INFO,
            message="Non-UTF8 inputs handled safely",
        )

    def _test_missing_fields(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with missing required fields."""
        if ejc is None:
            return TestResult(
                test_name="missing_required_fields",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        # Try calling without required parameters
        try:
            # Most systems require at least a query
            result = ejc.process_decision()  # No arguments

            return TestResult(
                test_name="missing_required_fields",
                passed=False,
                severity=Severity.MEDIUM,
                message="System accepted call with missing required fields",
                details={"result": result},
            )

        except TypeError as e:
            # Expected - missing required parameter
            return TestResult(
                test_name="missing_required_fields",
                passed=True,
                severity=Severity.INFO,
                message=f"Missing fields rejected: {str(e)[:100]}",
            )
        except Exception as e:
            return TestResult(
                test_name="missing_required_fields",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Unexpected exception for missing fields: {str(e)[:100]}",
                exception=e,
            )

    def _test_invalid_types(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with invalid data types."""
        if ejc is None:
            return TestResult(
                test_name="invalid_data_types",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        invalid_inputs = [
            {"query": 12345},  # Integer instead of string
            {"query": ["list", "of", "strings"]},  # List instead of string
            {"query": {"dict": "object"}},  # Dict instead of string
            {"query": True},  # Boolean instead of string
        ]

        for invalid_input in invalid_inputs:
            try:
                result = ejc.process_decision(**invalid_input)

                # Should reject invalid types
                return TestResult(
                    test_name="invalid_data_types",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"System accepted invalid type: {type(invalid_input['query'])}",
                    details={"input": invalid_input, "result": result},
                )

            except (TypeError, ValueError) as e:
                # Expected - type validation
                continue
            except Exception as e:
                return TestResult(
                    test_name="invalid_data_types",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Invalid type caused unexpected exception: {str(e)[:100]}",
                    exception=e,
                )

        return TestResult(
            test_name="invalid_data_types",
            passed=True,
            severity=Severity.INFO,
            message="Invalid types rejected properly",
        )

    def _test_special_characters(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with special/control characters."""
        if ejc is None:
            return TestResult(
                test_name="special_characters",
                passed=False,
                severity=Severity.LOW,
                message="No EJC instance provided",
            )

        special_chars = [
            "Test\r\nString",  # CRLF
            "Test\tTab",  # Tab
            "Test\x08Backspace",  # Backspace
            "Test​Zero-width",  # Zero-width space
            "Test\u200bInvisible",  # Zero-width joiner
        ]

        for chars in special_chars:
            try:
                result = ejc.process_decision(query=chars)

                # Should handle without crashing
                if not isinstance(result, dict):
                    return TestResult(
                        test_name="special_characters",
                        passed=False,
                        severity=Severity.LOW,
                        message=f"Special characters caused invalid response",
                        details={"input": chars, "result": result},
                    )

            except Exception as e:
                return TestResult(
                    test_name="special_characters",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Special characters caused crash: {str(e)[:100]}",
                    exception=e,
                )

        return TestResult(
            test_name="special_characters",
            passed=True,
            severity=Severity.INFO,
            message="Special characters handled safely",
        )

    def _test_deeply_nested(self, ejc: Optional[Any] = None, **kwargs) -> TestResult:
        """Test with excessively nested structures."""
        if ejc is None:
            return TestResult(
                test_name="deeply_nested_structure",
                passed=False,
                severity=Severity.MEDIUM,
                message="No EJC instance provided",
            )

        # Create deeply nested context (100 levels)
        nested = {"level": 100}
        for i in range(99, 0, -1):
            nested = {"level": i, "nested": nested}

        try:
            result = ejc.process_decision(query="Test", context=nested)

            # Should handle or reject, not crash
            return TestResult(
                test_name="deeply_nested_structure",
                passed=True,
                severity=Severity.INFO,
                message="Deeply nested structure handled",
            )

        except RecursionError as e:
            return TestResult(
                test_name="deeply_nested_structure",
                passed=False,
                severity=Severity.MEDIUM,
                message="Deeply nested structure caused recursion error",
                exception=e,
            )
        except (ValueError, TypeError) as e:
            # Acceptable - rejected deep nesting
            return TestResult(
                test_name="deeply_nested_structure",
                passed=True,
                severity=Severity.INFO,
                message=f"Deep nesting rejected: {str(e)[:100]}",
            )
        except Exception as e:
            return TestResult(
                test_name="deeply_nested_structure",
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Deep nesting caused unexpected error: {str(e)[:100]}",
                exception=e,
            )
