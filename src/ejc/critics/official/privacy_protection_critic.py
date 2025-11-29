"""
Privacy Protection Critic - Phase 5B

Implements comprehensive privacy analysis aligned with World Bank AI Governance Report (Section 4.3).

Features:
- PII/sensitive data detection
- Privacy-Enhancing Technology (PET) assessment
- Consent and transparency evaluation
- Data minimization analysis
- GDPR/privacy law compliance checking
- Privacy impact assessment
- Data retention and disposal verification

References:
- World Bank Report Section 4.3: "Data Privacy"
- World Bank Report Section 5.3: "Privacy-Enhancing Technologies"
- World Bank Report Table 6: "Data Privacy Checklist"
"""

import sys
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.base_critic import RuleBasedCritic


class PrivacyProtectionCritic(RuleBasedCritic):
    """
    Privacy Protection Critic implementing World Bank privacy standards.

    Evaluates AI systems for privacy compliance, data protection measures,
    and appropriate use of Privacy-Enhancing Technologies (PETs).
    """

    # Privacy-Enhancing Technologies (World Bank Section 5.3)
    SUPPORTED_PETS = {
        'differential_privacy': 'Adds calibrated noise to protect individual privacy',
        'federated_learning': 'Trains models without centralizing data',
        'homomorphic_encryption': 'Enables computation on encrypted data',
        'secure_mpc': 'Multi-party computation without revealing inputs',
        'tee': 'Trusted Execution Environments for secure processing'
    }

    # PII categories
    PII_CATEGORIES = {
        'direct_identifiers': ['name', 'ssn', 'email', 'phone', 'address', 'id number'],
        'quasi_identifiers': ['age', 'gender', 'zip code', 'birth date', 'race'],
        'sensitive_attributes': ['health', 'financial', 'biometric', 'genetic', 'political'],
        'behavioral_data': ['browsing', 'location', 'purchase', 'communication']
    }

    # World Bank Data Privacy Checklist (Table 6) - 5 categories, 17 items
    WB_PRIVACY_CHECKLIST = {
        'collection_from_subject': [
            'legal_basis_identified',
            'purpose_specified',
            'consent_obtained',
            'information_provided',
            'rights_explained'
        ],
        'collection_from_third_party': [
            'third_party_verified',
            'subject_informed'
        ],
        'use_and_provision': [
            'purpose_limitation',
            'third_party_disclosure_limited'
        ],
        'retention_and_disposal': [
            'retention_period_defined',
            'secure_disposal_planned'
        ],
        'pseudonymization': [
            'pseudonymization_applied',
            'reidentification_prevented',
            'key_management_secure'
        ]
    }

    # Privacy risk thresholds
    PRIVACY_THRESHOLDS = {
        'high_risk': 0.7,      # DENY if risk > 0.7
        'medium_risk': 0.4,    # REVIEW if risk > 0.4
        'pet_required': 0.5    # PET recommended if risk > 0.5
    }

    def __init__(
        self,
        name: str = "PrivacyProtectionCritic",
        weight: float = 1.5,  # Higher weight for critical privacy concern
        priority: Optional[str] = "high",
        timeout: Optional[float] = 30.0,
        require_pet: bool = False,
        strict_mode: bool = False
    ) -> None:
        """
        Initialize Privacy Protection Critic.

        Args:
            name: Critic identifier
            weight: Aggregation weight (higher for critical concern)
            priority: Priority level
            timeout: Maximum execution time
            require_pet: Whether PET usage is mandatory
            strict_mode: Whether to apply strict privacy standards (e.g., GDPR)
        """
        super().__init__(name=name, weight=weight, priority=priority, timeout=timeout)
        self.require_pet = require_pet
        self.strict_mode = strict_mode

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply privacy protection and data security analysis rules.

        Args:
            case: Case dictionary with:
                - text: Description of the AI decision/system
                - context: Optional context including:
                    - data_types: Types of data being processed
                    - data_sources: Where data comes from
                    - pet_usage: Privacy-enhancing technologies in use
                    - consent_mechanism: How consent is obtained
                    - retention_policy: Data retention and disposal policy
                    - third_party_sharing: Whether data is shared with third parties
                    - pseudonymization: Whether data is pseudonymized
                    - encryption: Encryption methods used

        Returns:
            Dict with verdict, confidence, justification
        """
        text = case.get('text', '')
        context = case.get('context', {})

        # Extract privacy-relevant information
        data_types = context.get('data_types', [])
        data_sources = context.get('data_sources', [])
        pet_usage = context.get('pet_usage', [])
        consent_mechanism = context.get('consent_mechanism', '')
        retention_policy = context.get('retention_policy', '')
        third_party_sharing = context.get('third_party_sharing', False)
        pseudonymization = context.get('pseudonymization', False)
        encryption = context.get('encryption', '')

        # Perform privacy analysis
        pii_risk = self._assess_pii_risk(text, data_types)
        pet_score = self._evaluate_pet_usage(pet_usage, pii_risk)
        consent_score = self._assess_consent(consent_mechanism)
        minimization_score = self._check_data_minimization(text, data_types)
        retention_score = self._evaluate_retention(retention_policy)
        checklist_compliance = self._check_wb_compliance({
            'consent': consent_mechanism,
            'retention': retention_policy,
            'pseudonymization': pseudonymization,
            'third_party': third_party_sharing
        })

        # Calculate overall privacy risk
        privacy_risk = self._calculate_privacy_risk(
            pii_risk,
            pet_score,
            consent_score,
            minimization_score,
            retention_score,
            checklist_compliance
        )

        # Determine verdict
        if privacy_risk > self.PRIVACY_THRESHOLDS['high_risk']:
            verdict = 'DENY'
            confidence = min(0.95, privacy_risk)
            justification = self._generate_high_risk_justification(
                pii_risk, pet_score, checklist_compliance
            )
        elif privacy_risk > self.PRIVACY_THRESHOLDS['medium_risk']:
            verdict = 'REVIEW'
            confidence = 0.7 + (privacy_risk - 0.4) * 0.5
            justification = self._generate_medium_risk_justification(
                pii_risk, pet_score, checklist_compliance
            )
        else:
            verdict = 'ALLOW'
            confidence = 0.8 - privacy_risk
            justification = self._generate_low_risk_justification(
                pet_score, checklist_compliance
            )

        return {
            'verdict': verdict,
            'confidence': confidence,
            'justification': justification,
            'privacy_risk_score': privacy_risk,
            'pii_risk': pii_risk,
            'pet_score': pet_score,
            'consent_score': consent_score,
            'minimization_score': minimization_score,
            'retention_score': retention_score,
            'wb_checklist_compliance': checklist_compliance,
            'recommended_pets': self._recommend_pets(pii_risk, pet_usage)
        }

    def _assess_pii_risk(self, text: str, data_types: List[str]) -> float:
        """
        Assess risk based on PII and sensitive data handling.

        Returns:
            Risk score between 0 (low) and 1 (high)
        """
        text_lower = text.lower()
        data_types_lower = [dt.lower() for dt in data_types]
        risk_score = 0.0

        # Check for direct identifiers (highest risk)
        direct_count = sum(
            1 for identifier in self.PII_CATEGORIES['direct_identifiers']
            if identifier in text_lower or any(identifier in dt for dt in data_types_lower)
        )
        risk_score += min(direct_count * 0.15, 0.4)

        # Check for sensitive attributes (high risk)
        sensitive_count = sum(
            1 for attr in self.PII_CATEGORIES['sensitive_attributes']
            if attr in text_lower or any(attr in dt for dt in data_types_lower)
        )
        risk_score += min(sensitive_count * 0.12, 0.3)

        # Check for quasi-identifiers (medium risk)
        quasi_count = sum(
            1 for identifier in self.PII_CATEGORIES['quasi_identifiers']
            if identifier in text_lower or any(identifier in dt for dt in data_types_lower)
        )
        risk_score += min(quasi_count * 0.05, 0.2)

        # Check for behavioral data (medium risk)
        behavioral_count = sum(
            1 for behavior in self.PII_CATEGORIES['behavioral_data']
            if behavior in text_lower or any(behavior in dt for dt in data_types_lower)
        )
        risk_score += min(behavioral_count * 0.05, 0.1)

        return min(risk_score, 1.0)

    def _evaluate_pet_usage(self, pet_usage: List[str], pii_risk: float) -> float:
        """
        Evaluate appropriateness of Privacy-Enhancing Technology usage.

        Returns:
            PET score between 0 (inadequate) and 1 (excellent)
        """
        if not pet_usage:
            # No PETs used
            if pii_risk > 0.5:
                return 0.2  # Inadequate for high PII risk
            elif pii_risk > 0.3:
                return 0.5  # Suboptimal for medium PII risk
            else:
                return 0.7  # Acceptable for low PII risk

        # Check if appropriate PETs are used
        pet_usage_lower = [pet.lower() for pet in pet_usage]
        recognized_pets = sum(
            1 for pet in self.SUPPORTED_PETS.keys()
            if any(pet in p for p in pet_usage_lower)
        )

        if recognized_pets == 0:
            return 0.6  # PETs mentioned but not recognized

        # Score based on number and appropriateness of PETs
        base_score = 0.7 + (recognized_pets * 0.1)
        return min(base_score, 1.0)

    def _assess_consent(self, consent_mechanism: str) -> float:
        """
        Assess consent mechanism quality.

        Returns:
            Consent score between 0 (poor) and 1 (excellent)
        """
        if not consent_mechanism:
            return 0.3  # No consent mechanism

        consent_lower = consent_mechanism.lower()

        # Check for strong consent indicators
        strong_indicators = [
            'explicit consent', 'informed consent', 'opt-in',
            'granular', 'specific purpose', 'withdrawable'
        ]
        strong_count = sum(1 for indicator in strong_indicators if indicator in consent_lower)

        # Check for weak consent indicators
        weak_indicators = [
            'implied', 'opt-out', 'blanket', 'pre-checked', 'bundled'
        ]
        weak_count = sum(1 for indicator in weak_indicators if indicator in consent_lower)

        if strong_count >= 3:
            return 0.9
        elif strong_count >= 2:
            return 0.75
        elif strong_count >= 1 and weak_count == 0:
            return 0.6
        elif weak_count > 0:
            return 0.4
        else:
            return 0.5

    def _check_data_minimization(self, text: str, data_types: List[str]) -> float:
        """
        Check if data minimization principle is followed.

        Returns:
            Minimization score between 0 (poor) and 1 (good)
        """
        text_lower = text.lower()

        # Positive indicators
        positive_indicators = [
            'minimal', 'necessary', 'essential', 'required only',
            'purpose-limited', 'need-to-know', 'least privilege'
        ]
        positive_count = sum(1 for indicator in positive_indicators if indicator in text_lower)

        # Negative indicators
        negative_indicators = [
            'all available', 'comprehensive', 'extensive', 'broad collection',
            'just in case', 'future use'
        ]
        negative_count = sum(1 for indicator in negative_indicators if indicator in text_lower)

        # Check data volume
        data_count = len(data_types) if data_types else 0
        volume_penalty = min(data_count * 0.05, 0.3) if data_count > 5 else 0

        base_score = 0.6
        score = base_score + (positive_count * 0.15) - (negative_count * 0.15) - volume_penalty

        return max(0.0, min(score, 1.0))

    def _evaluate_retention(self, retention_policy: str) -> float:
        """
        Evaluate data retention and disposal policy.

        Returns:
            Retention score between 0 (poor) and 1 (good)
        """
        if not retention_policy:
            return 0.3  # No retention policy

        retention_lower = retention_policy.lower()

        # Check for good retention practices
        good_indicators = [
            'time-limited', 'automatic deletion', 'defined period',
            'secure disposal', 'anonymization', 'regular review'
        ]
        good_count = sum(1 for indicator in good_indicators if indicator in retention_lower)

        # Check for concerning practices
        bad_indicators = [
            'indefinite', 'permanent', 'no limit', 'retained forever'
        ]
        bad_count = sum(1 for indicator in bad_indicators if indicator in retention_lower)

        if bad_count > 0:
            return 0.2
        elif good_count >= 3:
            return 0.9
        elif good_count >= 2:
            return 0.75
        elif good_count >= 1:
            return 0.6
        else:
            return 0.5

    def _check_wb_compliance(self, privacy_info: Dict[str, Any]) -> float:
        """
        Check compliance with World Bank Privacy Checklist (Table 6).

        Returns:
            Compliance score between 0 (non-compliant) and 1 (fully compliant)
        """
        compliance_score = 0.0
        total_items = 17  # Total items in WB checklist

        # Collection from subject (5 items)
        if privacy_info.get('consent'):
            compliance_score += 5 / total_items

        # Collection from third party (2 items)
        if privacy_info.get('third_party') is False:
            compliance_score += 2 / total_items
        elif privacy_info.get('third_party') and 'verified' in str(privacy_info.get('consent', '')).lower():
            compliance_score += 1 / total_items

        # Use and provision (2 items)
        # Assumed compliant if consent exists
        if privacy_info.get('consent'):
            compliance_score += 2 / total_items

        # Retention and disposal (2 items)
        if privacy_info.get('retention'):
            compliance_score += 2 / total_items

        # Pseudonymization (3 items)
        if privacy_info.get('pseudonymization'):
            compliance_score += 3 / total_items

        return min(compliance_score, 1.0)

    def _calculate_privacy_risk(
        self,
        pii_risk: float,
        pet_score: float,
        consent_score: float,
        minimization_score: float,
        retention_score: float,
        checklist_compliance: float
    ) -> float:
        """
        Calculate overall privacy risk score.

        Returns:
            Risk score between 0 (low risk) and 1 (high risk)
        """
        # Convert scores to risk (invert for positive scores)
        pet_risk = 1.0 - pet_score
        consent_risk = 1.0 - consent_score
        minimization_risk = 1.0 - minimization_score
        retention_risk = 1.0 - retention_score
        compliance_risk = 1.0 - checklist_compliance

        # Weighted combination (total = 1.0)
        total_risk = (
            0.30 * pii_risk +           # PII handling is critical
            0.25 * pet_risk +            # PET usage is important
            0.15 * consent_risk +        # Consent is important
            0.10 * minimization_risk +   # Data minimization matters
            0.10 * retention_risk +      # Retention policy matters
            0.10 * compliance_risk       # WB compliance matters
        )

        return min(total_risk, 1.0)

    def _recommend_pets(self, pii_risk: float, current_pets: List[str]) -> List[str]:
        """
        Recommend Privacy-Enhancing Technologies based on risk level.

        Returns:
            List of recommended PET names
        """
        recommendations = []
        current_pets_lower = [pet.lower() for pet in current_pets]

        if pii_risk > 0.7:
            # High risk: recommend multiple strong PETs
            if not any('differential' in pet for pet in current_pets_lower):
                recommendations.append('differential_privacy')
            if not any('homomorphic' in pet or 'encryption' in pet for pet in current_pets_lower):
                recommendations.append('homomorphic_encryption')
            if not any('tee' in pet or 'trusted execution' in pet for pet in current_pets_lower):
                recommendations.append('tee')
        elif pii_risk > 0.4:
            # Medium risk: recommend moderate PETs
            if not any('differential' in pet for pet in current_pets_lower):
                recommendations.append('differential_privacy')
            if not any('federated' in pet for pet in current_pets_lower):
                recommendations.append('federated_learning')
        elif pii_risk > 0.2:
            # Low-medium risk: recommend basic PETs
            if not any('differential' in pet for pet in current_pets_lower):
                recommendations.append('differential_privacy')

        return recommendations

    def _generate_high_risk_justification(
        self,
        pii_risk: float,
        pet_score: float,
        checklist_compliance: float
    ) -> str:
        """Generate justification for high privacy risk cases."""
        justification = "PRIVACY RISK DETECTED: This AI system shows significant privacy concerns. "

        if pii_risk > 0.6:
            justification += "High-risk PII and sensitive data detected. "

        if pet_score < 0.5:
            justification += "Inadequate Privacy-Enhancing Technology usage. "

        if checklist_compliance < 0.5:
            justification += "Low compliance with World Bank Privacy Checklist. "

        justification += "Recommendation: DO NOT DEPLOY until privacy measures are strengthened. "
        justification += "Required actions: (1) Implement appropriate PETs (differential privacy, encryption), "
        justification += "(2) Ensure explicit informed consent, (3) Apply data minimization, "
        justification += "(4) Define clear retention policy, (5) Complete World Bank privacy checklist."

        return justification

    def _generate_medium_risk_justification(
        self,
        pii_risk: float,
        pet_score: float,
        checklist_compliance: float
    ) -> str:
        """Generate justification for medium privacy risk cases."""
        justification = "REVIEW RECOMMENDED: Privacy concerns require attention. "

        issues = []
        if pii_risk > 0.4:
            issues.append("PII handling")
        if pet_score < 0.7:
            issues.append("PET implementation")
        if checklist_compliance < 0.7:
            issues.append("compliance gaps")

        if issues:
            justification += f"Areas of concern: {', '.join(issues)}. "

        justification += "Recommended actions: (1) Enhance PET usage, "
        justification += "(2) Strengthen consent mechanisms, (3) Review data minimization, "
        justification += "(4) Address World Bank checklist gaps."

        return justification

    def _generate_low_risk_justification(
        self,
        pet_score: float,
        checklist_compliance: float
    ) -> str:
        """Generate justification for low privacy risk cases."""
        justification = f"PRIVACY ASSESSMENT: System demonstrates good privacy practices. "
        justification += f"PET usage score: {pet_score:.2f}, WB compliance: {checklist_compliance:.2f}. "
        justification += "Recommendation: Maintain current privacy measures. "
        justification += "Continue monitoring: (1) Data access logs, (2) PET effectiveness, "
        justification += "(3) User consent status, (4) Regular privacy audits."

        return justification


# Export
__all__ = ['PrivacyProtectionCritic']
