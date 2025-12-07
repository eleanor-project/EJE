"""
Healthcare Domain Configuration

Configuration settings for healthcare governance module.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class HealthcareConfig:
    """Configuration for healthcare domain"""
    
    # HIPAA Compliance Settings
    phi_protection_level: str = "strict"  # strict, moderate, minimal
    minimum_necessary_enforcement: bool = True
    audit_all_phi_access: bool = True
    
    # Medical Ethics Settings
    enable_beneficence_check: bool = True
    enable_non_maleficence_check: bool = True
    enable_autonomy_check: bool = True
    enable_justice_check: bool = True
    
    # Clinical Decision Support
    require_clinical_validation: bool = True
    emergency_override_enabled: bool = True
    clinician_review_threshold: float = 0.7  # Confidence below this requires review
    
    # Drug Interaction
    drug_interaction_api_url: str = ""  # External drug database API
    enable_drug_interaction_checks: bool = True
    escalate_on_multiple_meds: bool = True
    
    # Privacy Settings
    data_minimization_enforced: bool = True
    purpose_limitation_check: bool = True
    third_party_sharing_requires_approval: bool = True
    
    # Critic Weights
    critic_weights: Dict[str, float] = field(default_factory=lambda: {
        "hipaa_compliance": 1.0,
        "medical_ethics": 0.9,
        "patient_privacy": 0.85,
        "clinical_decision": 0.95,
        "drug_interaction": 1.0,
    })
    
    # Escalation Settings
    escalation_threshold: float = 0.8
    require_human_review_for_deny: bool = True
    
    # Integration Settings
    clinical_workflow_integration: bool = False
    ehr_system_integration: bool = False
    
    @classmethod
    def get_default_config(cls) -> "HealthcareConfig":
        """Return default configuration"""
        return cls()
    
    @classmethod
    def get_pilot_config(cls) -> "HealthcareConfig":
        """Configuration for pilot deployments"""
        config = cls()
        config.require_human_review_for_deny = True
        config.escalation_threshold = 0.7
        return config
    
    @classmethod
    def get_production_config(cls) -> "HealthcareConfig":
        """Configuration for production deployments"""
        config = cls()
        config.audit_all_phi_access = True
        config.phi_protection_level = "strict"
        config.require_clinical_validation = True
        return config


# Export
__all__ = ["HealthcareConfig"]
