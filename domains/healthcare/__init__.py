"""
Healthcare Governance Domain Module

This module provides healthcare-specific governance capabilities including:
- HIPAA compliance critics
- Medical ethics critics (beneficence, non-maleficence, autonomy, justice)
- Clinical decision support integration
- Drug interaction safety checks
- Patient privacy safeguards
- Healthcare precedent templates

Part of the EJE Domains framework for domain-specific governance.
"""

from .healthcare_critics import (
    HIPAAComplianceCritic,
    MedicalEthicsCritic,
    PatientPrivacyCritic,
    ClinicalDecisionCritic,
    DrugInteractionCritic,
)

from .healthcare_config import HealthcareConfig
from .precedent_templates import HealthcarePrecedentTemplates

__all__ = [
    "HIPAAComplianceCritic",
    "MedicalEthicsCritic",
    "PatientPrivacyCritic",
    "ClinicalDecisionCritic",
    "DrugInteractionCritic",
    "HealthcareConfig",
    "HealthcarePrecedentTemplates",
]

__version__ = "1.0.0"
