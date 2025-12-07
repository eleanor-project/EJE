"""
Healthcare Precedent Templates

Pre-defined templates for common healthcare scenarios to ensure
consistent decision-making across similar cases.
"""

from typing import Dict, Any, List


class HealthcarePrecedentTemplates:
    """Collection of precedent templates for healthcare domain"""
    
    @staticmethod
    def get_patient_data_access_template() -> Dict[str, Any]:
        """Template for patient data access requests"""
        return {
            "template_id": "healthcare-data-access-001",
            "category": "data_access",
            "required_checks": [
                "hipaa_compliance",
                "patient_privacy",
                "minimum_necessary"
            ],
            "escalation_criteria": {
                "phi_disclosure": True,
                "unauthorized_access": True
            },
            "precedent_factors": [
                "requester_role",
                "purpose_of_access",
                "data_scope",
                "patient_consent_status"
            ]
        }
    
    @staticmethod
    def get_treatment_decision_template() -> Dict[str, Any]:
        """Template for clinical treatment decisions"""
        return {
            "template_id": "healthcare-treatment-001",
            "category": "clinical_decision",
            "required_checks": [
                "medical_ethics",
                "clinical_decision",
                "patient_safety"
            ],
            "escalation_criteria": {
                "high_risk_procedure": True,
                "experimental_treatment": True,
                "informed_consent_missing": True
            },
            "precedent_factors": [
                "patient_condition",
                "treatment_risks",
                "alternative_options",
                "patient_preferences"
            ]
        }
    
    @staticmethod
    def get_medication_prescription_template() -> Dict[str, Any]:
        """Template for medication prescription decisions"""
        return {
            "template_id": "healthcare-medication-001",
            "category": "medication",
            "required_checks": [
                "drug_interaction",
                "clinical_decision",
                "patient_safety"
            ],
            "escalation_criteria": {
                "drug_interaction_detected": True,
                "contraindication_found": True,
                "dosage_concern": True
            },
            "precedent_factors": [
                "patient_medications",
                "allergies",
                "comorbidities",
                "dosage_appropriateness"
            ]
        }
    
    @staticmethod
    def get_data_sharing_template() -> Dict[str, Any]:
        """Template for health data sharing with third parties"""
        return {
            "template_id": "healthcare-data-sharing-001",
            "category": "data_sharing",
            "required_checks": [
                "hipaa_compliance",
                "patient_privacy",
                "data_security"
            ],
            "escalation_criteria": {
                "third_party_sharing": True,
                "international_transfer": True,
                "marketing_purpose": True
            },
            "precedent_factors": [
                "recipient_entity",
                "purpose_limitation",
                "patient_authorization",
                "data_protection_measures"
            ]
        }
    
    @staticmethod
    def get_emergency_care_template() -> Dict[str, Any]:
        """Template for emergency care scenarios"""
        return {
            "template_id": "healthcare-emergency-001",
            "category": "emergency",
            "required_checks": [
                "clinical_decision",
                "patient_safety"
            ],
            "escalation_criteria": {
                "life_threatening": False,  # No escalation in emergencies
                "immediate_action_required": False
            },
            "precedent_factors": [
                "urgency_level",
                "available_resources",
                "standard_of_care"
            ],
            "emergency_override": True
        }
    
    @classmethod
    def get_all_templates(cls) -> List[Dict[str, Any]]:
        """Get all available precedent templates"""
        return [
            cls.get_patient_data_access_template(),
            cls.get_treatment_decision_template(),
            cls.get_medication_prescription_template(),
            cls.get_data_sharing_template(),
            cls.get_emergency_care_template(),
        ]
    
    @classmethod
    def get_template_by_category(cls, category: str) -> Dict[str, Any]:
        """Retrieve template by category"""
        templates = cls.get_all_templates()
        for template in templates:
            if template.get("category") == category:
                return template
        return None


# Export
__all__ = ["HealthcarePrecedentTemplates"]
