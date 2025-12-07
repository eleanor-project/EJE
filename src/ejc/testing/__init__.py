"""
EJC Adversarial Testing Framework.

Comprehensive test suites for security, robustness, and fairness validation.
"""

from .base import (
    TestCase,
    TestResult,
    TestSuite,
    TestHarness,
    Severity,
)
from .prompt_injection import PromptInjectionSuite
from .bias_probe import BiasProbeSuite
from .context_poisoning import ContextPoisoningSuite
from .malformed_input import MalformedInputSuite
from .boundary import BoundarySuite
from .runner import TestRunner, run_all_tests

__all__ = [
    # Base framework
    "TestCase",
    "TestResult",
    "TestSuite",
    "TestHarness",
    "Severity",
    # Test suites
    "PromptInjectionSuite",
    "BiasProbeSuite",
    "ContextPoisoningSuite",
    "MalformedInputSuite",
    "BoundarySuite",
    # Runner
    "TestRunner",
    "run_all_tests",
]
