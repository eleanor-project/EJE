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

__all__ = [
    'AttackPattern',
    'AttackCategory',
    'AttackSeverity',
    'AttackPatternLibrary'
]
