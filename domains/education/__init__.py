"""Education domain governance module.

Provides domain-specific ethical oversight for educational institutions,
focusing on equity, privacy, and academic integrity.
"""

from .education_critics import (
    AcademicIntegrityCritic,
    EquityAllocationCritic,
    StudentPrivacyCritic,
    AccessibilityComplianceCritic,
    AdmissionsGradingBiasCritic,
)

__all__ = [
    "AcademicIntegrityCritic",
    "EquityAllocationCritic",
    "StudentPrivacyCritic",
    "AccessibilityComplianceCritic",
    "AdmissionsGradingBiasCritic",
]
