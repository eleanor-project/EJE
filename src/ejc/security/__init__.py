"""
EJC Security Module

Adversarial testing and security hardening for EJE system.

Components:
- Attack Pattern Library: Comprehensive adversarial attack patterns
- Adversarial Testing: Automated security testing framework
- Robustness Scoring: Quantitative security metrics
- Red Team Daemon: Continuous security validation
"""

from .attack_patterns import (
    AttackPattern,
    AttackCategory,
    AttackSeverity,
    AttackPatternLibrary
)
from .adversarial_testing import (
    AdversarialTestRunner,
    CICDIntegration,
    TestResult,
    TestSuiteResult,
    TestStatus
)
from .robustness_scoring import (
    RobustnessScorer,
    RobustnessMetrics,
    CompositeScore,
    BenchmarkResult
)

__all__ = [
    # Attack Patterns
    'AttackPattern',
    'AttackCategory',
    'AttackSeverity',
    'AttackPatternLibrary',
    # Adversarial Testing
    'AdversarialTestRunner',
    'CICDIntegration',
    'TestResult',
    'TestSuiteResult',
    'TestStatus',
    # Robustness Scoring
    'RobustnessScorer',
    'RobustnessMetrics',
    'CompositeScore',
    'BenchmarkResult'
]
