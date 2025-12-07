"""
Healthcare-Specific Critics Module

Implements HIPAA-compliant critics for healthcare governance including:
- HIPAA Compliance Critic
- Medical Ethics Critics (beneficence, non-maleficence, autonomy, justice)
- Clinical Decision Support
- Drug Interaction Safety
- Patient Privacy Safeguards
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class CriticVerdict:
    """Standard critic response format"""
    verdict: str  # "ALLOW", "DENY", "ESCALATE"
    confidence: float  # 0.0-1.0
    justification: str
    metadata: Dict[str, Any] = None


class HIPAAComplianceCritic:
    """
    Evaluates requests for HIPAA compliance.
    Checks PHI handling, access controls, minimum necessary principle.
    """
    
    def __init__(self):
        self.name = "HIPAA Compliance Critic"
        self.weight = 1.0
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate case for HIPAA compliance"""
        # Check for PHI exposure risks
        text = case.get("text", "").lower()
        
        hipaa_risks = []
        if "patient" in text and ("share" in text or "disclose" in text):
            hipaa_risks.append("Potential PHI disclosure without authorization")
        if "medical record" in text and "unauthorized" in text:
            hipaa_risks.append("Unauthorized medical record access")
        if "health information" in text and not "protected" in text:
            hipaa_risks.append("Unprotected health information handling")
            
        if hipaa_risks:
            return {
                "verdict": "DENY",
                "confidence": 0.85,
                "justification": f"HIPAA violations detected: {'; '.join(hipaa_risks)}",
                "metadata": {"risks": hipaa_risks, "regulation": "HIPAA"}
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "No obvious HIPAA violations detected",
            "metadata": {"regulation": "HIPAA"}
        }


class MedicalEthicsCritic:
    """
    Evaluates medical decisions against four pillars of medical ethics:
    - Beneficence (do good)
    - Non-maleficence (do no harm)
    - Autonomy (patient choice)
    - Justice (fairness)
    """
    
    def __init__(self):
        self.name = "Medical Ethics Critic"
        self.weight = 0.9
        self.principles = ["beneficence", "non-maleficence", "autonomy", "justice"]
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate case against medical ethics principles"""
        text = case.get("text", "").lower()
        violations = []
        
        # Check beneficence
        if "withhold treatment" in text or "deny care" in text:
            violations.append("Potential beneficence violation: withholding beneficial treatment")
            
        # Check non-maleficence
        if "risk" in text and "harm" in text and "unnecessary" in text:
            violations.append("Potential non-maleficence violation: unnecessary harm risk")
            
        # Check autonomy
        if ("forced" in text or "without consent" in text) and "patient" in text:
            violations.append("Potential autonomy violation: lack of informed consent")
            
        # Check justice
        if "discriminat" in text or "unequal access" in text:
            violations.append("Potential justice violation: unequal treatment")
            
        if violations:
            return {
                "verdict": "DENY",
                "confidence": 0.8,
                "justification": f"Medical ethics concerns: {'; '.join(violations)}",
                "metadata": {"violations": violations, "principles": self.principles}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "Aligns with medical ethics principles",
            "metadata": {"principles": self.principles}
        }


class PatientPrivacyCritic:
    """
    Specialized critic for patient privacy beyond HIPAA requirements.
    Focuses on data minimization, purpose limitation, and consent.
    """
    
    def __init__(self):
        self.name = "Patient Privacy Critic"
        self.weight = 0.85
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate patient privacy implications"""
        text = case.get("text", "").lower()
        privacy_issues = []
        
        if "collect" in text and "data" in text and "unnecessary" in text:
            privacy_issues.append("Excessive data collection")
        if "share" in text and ("third party" in text or "vendor" in text):
            privacy_issues.append("Third-party data sharing without clear necessity")
        if "identify" in text and "patient" in text:
            privacy_issues.append("Potential re-identification risk")
            
        if privacy_issues:
            return {
                "verdict": "ESCALATE",
                "confidence": 0.75,
                "justification": f"Privacy concerns require review: {'; '.join(privacy_issues)}",
                "metadata": {"privacy_issues": privacy_issues}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "Privacy protections appear adequate",
            "metadata": {}
        }


class ClinicalDecisionCritic:
    """
    Evaluates clinical decision support requests for safety and appropriateness.
    """
    
    def __init__(self):
        self.name = "Clinical Decision Support Critic"
        self.weight = 0.95
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate clinical decision support request"""
        text = case.get("text", "").lower()
        concerns = []
        
        if "diagnos" in text and "without" in text and "examination" in text:
            concerns.append("Diagnosis without proper clinical examination")
        if "prescrib" in text and "without" in text and "assessment" in text:
            concerns.append("Prescription without proper patient assessment")
        if "emergency" in text and "delay" in text:
            concerns.append("Potential delay in emergency care")
            
        if concerns:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"Clinical safety concerns: {'; '.join(concerns)}",
                "metadata": {"concerns": concerns, "type": "clinical_decision"}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "Clinical decision process appears sound",
            "metadata": {"type": "clinical_decision"}
        }


class DrugInteractionCritic:
    """
    Checks for potential drug interactions and contraindications.
    Note: In production, this should integrate with drug database APIs.
    """
    
    def __init__(self):
        self.name = "Drug Interaction Critic"
        self.weight = 1.0
        # In production: integrate with drug database
        self.high_risk_combinations = {
            "warfarin+aspirin": "Increased bleeding risk",
            "maoi+ssri": "Serotonin syndrome risk",
        }
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate for drug interactions"""
        text = case.get("text", "").lower()
        
        # Check for medication mentions
        if "medication" in text or "drug" in text or "prescri" in text:
            # Simplified check - in production use proper drug interaction database
            if "multiple" in text and "medication" in text:
                return {
                    "verdict": "ESCALATE",
                    "confidence": 0.85,
                    "justification": "Multiple medications mentioned - drug interaction check required",
                    "metadata": {"requires": "pharmacist_review"}
                }
                
        return {
            "verdict": "ALLOW",
            "confidence": 0.6,
            "justification": "No obvious drug interaction concerns (limited analysis)",
            "metadata": {}
        }


# Export all critics
__all__ = [
    "HIPAAComplianceCritic",
    "MedicalEthicsCritic",
    "PatientPrivacyCritic",
    "ClinicalDecisionCritic",
    "DrugInteractionCritic",
    "CriticVerdict",
]
