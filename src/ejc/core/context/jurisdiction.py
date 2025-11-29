"""
Jurisdiction-aware reasoning for legal and regulatory context.

Adapts ethical decisions based on jurisdiction-specific laws and regulations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class PrivacyRegime(Enum):
    """Privacy regulatory regimes."""
    GDPR = "gdpr"  # EU General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    PIPEDA = "pipeda"  # Canadian Personal Information Protection
    LGPD = "lgpd"  # Brazilian General Data Protection Law
    NONE = "none"  # No specific regime


@dataclass
class JurisdictionContext:
    """Context information for a specific jurisdiction."""

    jurisdiction_id: str
    name: str
    region: str  # e.g., "EU", "US-CA", "US-Federal", "Brazil"

    # Privacy and data protection
    privacy_regime: PrivacyRegime
    data_residency_required: bool = False
    consent_required: bool = True
    right_to_erasure: bool = False

    # Content and speech
    hate_speech_laws: bool = False
    misinformation_regulations: bool = False
    content_moderation_required: bool = False

    # AI-specific regulations
    ai_transparency_required: bool = False
    algorithmic_accountability: bool = False
    automated_decision_limits: bool = False

    # Additional constraints
    specific_rules: Dict[str, any] = field(default_factory=dict)
    prohibited_actions: Set[str] = field(default_factory=set)
    required_disclosures: List[str] = field(default_factory=list)

    def applies_to(self, action: str) -> bool:
        """Check if this jurisdiction's rules apply to an action."""
        return action not in self.prohibited_actions

    def get_compliance_requirements(self, action_type: str) -> List[str]:
        """Get compliance requirements for an action type."""
        requirements = []

        if action_type == "data_collection":
            if self.consent_required:
                requirements.append("Obtain explicit user consent")
            if self.privacy_regime == PrivacyRegime.GDPR:
                requirements.append("Provide purpose limitation and data minimization")
            if self.data_residency_required:
                requirements.append("Store data within jurisdiction")

        elif action_type == "automated_decision":
            if self.automated_decision_limits:
                requirements.append("Provide human oversight for significant decisions")
            if self.ai_transparency_required:
                requirements.append("Explain decision-making process")

        elif action_type == "content_moderation":
            if self.content_moderation_required:
                requirements.append("Implement content moderation policies")
            if self.hate_speech_laws:
                requirements.append("Remove illegal hate speech")

        return requirements


class JurisdictionRegistry:
    """Registry of jurisdiction contexts."""

    def __init__(self):
        """Initialize with common jurisdictions."""
        self.jurisdictions: Dict[str, JurisdictionContext] = {}
        self._initialize_common_jurisdictions()

    def _initialize_common_jurisdictions(self):
        """Initialize common jurisdiction contexts."""

        # European Union - GDPR
        self.register(JurisdictionContext(
            jurisdiction_id="EU",
            name="European Union",
            region="EU",
            privacy_regime=PrivacyRegime.GDPR,
            data_residency_required=False,  # Can use adequacy decisions
            consent_required=True,
            right_to_erasure=True,
            hate_speech_laws=True,
            misinformation_regulations=True,
            ai_transparency_required=True,
            algorithmic_accountability=True,
            automated_decision_limits=True,
            required_disclosures=[
                "GDPR Article 13 information",
                "Right to object to automated decisions",
            ],
        ))

        # California - CCPA
        self.register(JurisdictionContext(
            jurisdiction_id="US-CA",
            name="California",
            region="US-CA",
            privacy_regime=PrivacyRegime.CCPA,
            data_residency_required=False,
            consent_required=False,  # Opt-out model
            right_to_erasure=True,
            hate_speech_laws=False,
            content_moderation_required=True,
            ai_transparency_required=True,
            required_disclosures=[
                "CCPA privacy notice",
                "Do Not Sell disclosure",
            ],
        ))

        # US Federal - HIPAA (Healthcare)
        self.register(JurisdictionContext(
            jurisdiction_id="US-HIPAA",
            name="US Healthcare (HIPAA)",
            region="US-Federal",
            privacy_regime=PrivacyRegime.HIPAA,
            data_residency_required=False,
            consent_required=True,
            right_to_erasure=False,
            ai_transparency_required=False,
            specific_rules={
                "phi_protection": True,
                "minimum_necessary": True,
                "breach_notification": True,
            },
            prohibited_actions={
                "unauthorized_phi_disclosure",
                "marketing_without_consent",
            },
            required_disclosures=[
                "HIPAA Notice of Privacy Practices",
                "Breach notification if applicable",
            ],
        ))

        # Brazil - LGPD
        self.register(JurisdictionContext(
            jurisdiction_id="BR",
            name="Brazil",
            region="Brazil",
            privacy_regime=PrivacyRegime.LGPD,
            data_residency_required=True,
            consent_required=True,
            right_to_erasure=True,
            hate_speech_laws=True,
            misinformation_regulations=True,
            required_disclosures=[
                "LGPD Article 9 information",
            ],
        ))

        # Canada - PIPEDA
        self.register(JurisdictionContext(
            jurisdiction_id="CA",
            name="Canada",
            region="Canada",
            privacy_regime=PrivacyRegime.PIPEDA,
            data_residency_required=False,
            consent_required=True,
            right_to_erasure=False,
            ai_transparency_required=True,
            automated_decision_limits=True,
            required_disclosures=[
                "PIPEDA privacy policy",
            ],
        ))

    def register(self, jurisdiction: JurisdictionContext):
        """Register a jurisdiction context."""
        self.jurisdictions[jurisdiction.jurisdiction_id] = jurisdiction

    def get(self, jurisdiction_id: str) -> Optional[JurisdictionContext]:
        """Get jurisdiction context by ID."""
        return self.jurisdictions.get(jurisdiction_id)

    def get_applicable_jurisdictions(
        self,
        user_location: Optional[str] = None,
        data_location: Optional[str] = None,
        service_location: Optional[str] = None
    ) -> List[JurisdictionContext]:
        """
        Determine applicable jurisdictions based on locations.

        Args:
            user_location: Where the user is located
            data_location: Where data is stored
            service_location: Where service is provided

        Returns:
            List of applicable jurisdiction contexts
        """
        applicable = []

        # User location jurisdiction
        if user_location and user_location in self.jurisdictions:
            applicable.append(self.jurisdictions[user_location])

        # Data location jurisdiction (especially if residency required)
        if data_location and data_location in self.jurisdictions:
            ctx = self.jurisdictions[data_location]
            if ctx.data_residency_required:
                applicable.append(ctx)

        # Service location jurisdiction
        if service_location and service_location in self.jurisdictions:
            if self.jurisdictions[service_location] not in applicable:
                applicable.append(self.jurisdictions[service_location])

        return applicable

    def get_strictest_requirements(
        self,
        jurisdictions: List[JurisdictionContext],
        action_type: str
    ) -> List[str]:
        """
        Get strictest requirements across multiple jurisdictions.

        Implements "highest common denominator" approach.

        Args:
            jurisdictions: List of applicable jurisdictions
            action_type: Type of action being performed

        Returns:
            Combined list of requirements
        """
        all_requirements = set()

        for jurisdiction in jurisdictions:
            requirements = jurisdiction.get_compliance_requirements(action_type)
            all_requirements.update(requirements)

        return sorted(list(all_requirements))

    def check_compliance(
        self,
        action: Dict,
        jurisdictions: List[JurisdictionContext]
    ) -> Dict:
        """
        Check if an action complies with jurisdiction requirements.

        Args:
            action: Action dict with type and details
            jurisdictions: Applicable jurisdictions

        Returns:
            Compliance report dict
        """
        action_type = action.get("type", "unknown")

        violations = []
        warnings = []
        requirements_met = []

        for jurisdiction in jurisdictions:
            # Check prohibited actions
            if action_type in jurisdiction.prohibited_actions:
                violations.append({
                    "jurisdiction": jurisdiction.name,
                    "issue": f"Action '{action_type}' is prohibited",
                    "severity": "critical",
                })

            # Check requirements
            requirements = jurisdiction.get_compliance_requirements(action_type)
            for req in requirements:
                # Simple check - in real system, would validate action details
                if req not in action.get("compliance_measures", []):
                    warnings.append({
                        "jurisdiction": jurisdiction.name,
                        "requirement": req,
                        "severity": "medium",
                    })
                else:
                    requirements_met.append(req)

        is_compliant = len(violations) == 0

        return {
            "compliant": is_compliant,
            "violations": violations,
            "warnings": warnings,
            "requirements_met": requirements_met,
            "applicable_jurisdictions": [j.name for j in jurisdictions],
        }
