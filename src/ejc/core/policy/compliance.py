"""
Compliance Flags and Checking

Provides compliance flag management and validation for governance decisions.
Tracks regulatory requirements, risk levels, and compliance status.

Features:
- Compliance flag definitions
- Multi-jurisdiction support
- Risk level assessment
- Compliance validation
- Audit trail integration
"""

from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ...utils.logging import get_logger


logger = get_logger("ejc.policy.compliance")


class ComplianceStandard(Enum):
    """Regulatory compliance standards"""
    GDPR = "GDPR"  # EU General Data Protection Regulation
    HIPAA = "HIPAA"  # US Health Insurance Portability and Accountability Act
    CCPA = "CCPA"  # California Consumer Privacy Act
    SOC2 = "SOC2"  # Service Organization Control 2
    ISO27001 = "ISO27001"  # Information Security Management
    FCRA = "FCRA"  # Fair Credit Reporting Act
    ECOA = "ECOA"  # Equal Credit Opportunity Act
    AML = "AML"  # Anti-Money Laundering
    KYC = "KYC"  # Know Your Customer
    FERPA = "FERPA"  # Family Educational Rights and Privacy Act
    EU_AI_ACT = "EU_AI_ACT"  # EU Artificial Intelligence Act


class RiskLevel(Enum):
    """Risk level classifications"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class ComplianceStatus(Enum):
    """Compliance validation status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


@dataclass
class ComplianceFlag:
    """Individual compliance flag"""
    standard: ComplianceStandard
    requirement: str  # Specific requirement (e.g., "data_minimization", "consent_required")
    triggered: bool = False
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'standard': self.standard.value,
            'requirement': self.requirement,
            'triggered': self.triggered,
            'status': self.status.value,
            'risk_level': self.risk_level.value,
            'reason': self.reason,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ComplianceFlags:
    """
    Collection of compliance flags for a decision.

    Tracks all regulatory requirements and their status.
    """
    flags: List[ComplianceFlag] = field(default_factory=list)
    jurisdiction: str = "US"  # Default jurisdiction
    applicable_standards: Set[ComplianceStandard] = field(default_factory=set)
    overall_status: ComplianceStatus = ComplianceStatus.UNKNOWN
    requires_human_review: bool = False

    def add_flag(self, flag: ComplianceFlag):
        """Add a compliance flag"""
        self.flags.append(flag)
        self.applicable_standards.add(flag.standard)

        # Update overall status
        self._update_overall_status()

    def get_flags_by_standard(self, standard: ComplianceStandard) -> List[ComplianceFlag]:
        """Get all flags for a specific standard"""
        return [f for f in self.flags if f.standard == standard]

    def get_triggered_flags(self) -> List[ComplianceFlag]:
        """Get all triggered flags"""
        return [f for f in self.flags if f.triggered]

    def get_non_compliant_flags(self) -> List[ComplianceFlag]:
        """Get all non-compliant flags"""
        return [f for f in self.flags if f.status == ComplianceStatus.NON_COMPLIANT]

    def has_critical_violations(self) -> bool:
        """Check if there are any critical compliance violations"""
        for flag in self.flags:
            if flag.triggered and flag.risk_level == RiskLevel.CRITICAL:
                return True
        return False

    def _update_overall_status(self):
        """Update overall compliance status"""
        if not self.flags:
            self.overall_status = ComplianceStatus.UNKNOWN
            return

        # Check for non-compliance
        non_compliant = [f for f in self.flags if f.status == ComplianceStatus.NON_COMPLIANT]
        if non_compliant:
            self.overall_status = ComplianceStatus.NON_COMPLIANT
            # Check if human review required
            for flag in non_compliant:
                if flag.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                    self.requires_human_review = True
            return

        # Check for review required
        review_needed = [f for f in self.flags if f.status == ComplianceStatus.REQUIRES_REVIEW]
        if review_needed:
            self.overall_status = ComplianceStatus.REQUIRES_REVIEW
            self.requires_human_review = True
            return

        # All compliant or not applicable
        self.overall_status = ComplianceStatus.COMPLIANT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'flags': [f.to_dict() for f in self.flags],
            'jurisdiction': self.jurisdiction,
            'applicable_standards': [s.value for s in self.applicable_standards],
            'overall_status': self.overall_status.value,
            'requires_human_review': self.requires_human_review,
            'summary': {
                'total_flags': len(self.flags),
                'triggered': len(self.get_triggered_flags()),
                'non_compliant': len(self.get_non_compliant_flags()),
                'has_critical': self.has_critical_violations()
            }
        }


class ComplianceChecker:
    """
    Compliance checker for governance decisions.

    Validates decisions against regulatory requirements.
    """

    def __init__(
        self,
        jurisdiction: str = "US",
        applicable_standards: Optional[List[ComplianceStandard]] = None
    ):
        """
        Initialize compliance checker.

        Args:
            jurisdiction: Legal jurisdiction (US, EU, UK, etc.)
            applicable_standards: List of applicable compliance standards
        """
        self.jurisdiction = jurisdiction
        self.applicable_standards = set(applicable_standards or [])

        # Define compliance rules for each standard
        self.compliance_rules = {
            ComplianceStandard.GDPR: self._check_gdpr,
            ComplianceStandard.HIPAA: self._check_hipaa,
            ComplianceStandard.CCPA: self._check_ccpa,
            ComplianceStandard.EU_AI_ACT: self._check_eu_ai_act,
            ComplianceStandard.FCRA: self._check_fcra,
            ComplianceStandard.ECOA: self._check_ecoa
        }

    def check_compliance(self, decision_data: Dict[str, Any]) -> ComplianceFlags:
        """
        Check decision compliance against applicable standards.

        Args:
            decision_data: Decision context and results

        Returns:
            ComplianceFlags object with all compliance checks
        """
        flags = ComplianceFlags(jurisdiction=self.jurisdiction)

        # Check each applicable standard
        for standard in self.applicable_standards:
            if standard in self.compliance_rules:
                checker = self.compliance_rules[standard]
                standard_flags = checker(decision_data)
                for flag in standard_flags:
                    flags.add_flag(flag)

        logger.info(f"Compliance check complete: {flags.overall_status.value}")
        return flags

    def _check_gdpr(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check GDPR compliance requirements"""
        flags = []

        # Data minimization
        if decision_data.get('uses_personal_data', False):
            has_minimization = decision_data.get('data_minimization_applied', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.GDPR,
                requirement="data_minimization",
                triggered=not has_minimization,
                status=ComplianceStatus.COMPLIANT if has_minimization else ComplianceStatus.REQUIRES_REVIEW,
                risk_level=RiskLevel.HIGH,
                reason="GDPR requires data minimization" if not has_minimization else "Data minimization applied"
            ))

        # Consent requirements
        requires_consent = decision_data.get('requires_consent', False)
        has_consent = decision_data.get('user_consent_obtained', False)
        if requires_consent:
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.GDPR,
                requirement="consent_required",
                triggered=not has_consent,
                status=ComplianceStatus.COMPLIANT if has_consent else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.CRITICAL,
                reason="User consent required but not obtained" if not has_consent else "User consent obtained"
            ))

        # Right to explanation (automated decisions)
        is_automated = decision_data.get('is_automated_decision', True)
        has_explanation = decision_data.get('explanation_available', False)
        if is_automated:
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.GDPR,
                requirement="right_to_explanation",
                triggered=not has_explanation,
                status=ComplianceStatus.COMPLIANT if has_explanation else ComplianceStatus.REQUIRES_REVIEW,
                risk_level=RiskLevel.HIGH,
                reason="Automated decision requires explanation capability"
            ))

        return flags

    def _check_hipaa(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check HIPAA compliance requirements"""
        flags = []

        # PHI encryption
        uses_phi = decision_data.get('uses_protected_health_info', False)
        if uses_phi:
            is_encrypted = decision_data.get('data_encrypted', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.HIPAA,
                requirement="phi_encryption",
                triggered=not is_encrypted,
                status=ComplianceStatus.COMPLIANT if is_encrypted else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.CRITICAL,
                reason="PHI must be encrypted at rest and in transit"
            ))

            # Access controls
            has_access_controls = decision_data.get('access_controls_enabled', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.HIPAA,
                requirement="access_controls",
                triggered=not has_access_controls,
                status=ComplianceStatus.COMPLIANT if has_access_controls else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
                reason="HIPAA requires strict access controls for PHI"
            ))

        return flags

    def _check_ccpa(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check CCPA compliance requirements"""
        flags = []

        # Right to opt-out of sale
        data_sold = decision_data.get('personal_data_sold', False)
        opt_out_available = decision_data.get('opt_out_mechanism_available', False)
        if data_sold:
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.CCPA,
                requirement="opt_out_of_sale",
                triggered=not opt_out_available,
                status=ComplianceStatus.COMPLIANT if opt_out_available else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
                reason="CCPA requires opt-out mechanism for data sale"
            ))

        return flags

    def _check_eu_ai_act(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check EU AI Act compliance requirements"""
        flags = []

        # High-risk AI system requirements
        is_high_risk = decision_data.get('is_high_risk_ai', False)
        if is_high_risk:
            # Risk management system
            has_risk_management = decision_data.get('risk_management_system', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.EU_AI_ACT,
                requirement="risk_management_system",
                triggered=not has_risk_management,
                status=ComplianceStatus.COMPLIANT if has_risk_management else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.CRITICAL,
                reason="High-risk AI systems require risk management"
            ))

            # Human oversight
            has_human_oversight = decision_data.get('human_oversight_enabled', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.EU_AI_ACT,
                requirement="human_oversight",
                triggered=not has_human_oversight,
                status=ComplianceStatus.COMPLIANT if has_human_oversight else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
                reason="High-risk AI requires human oversight"
            ))

        return flags

    def _check_fcra(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check FCRA compliance (credit reporting)"""
        flags = []

        # Adverse action notice
        is_credit_decision = decision_data.get('is_credit_decision', False)
        verdict = decision_data.get('overall_verdict', '')
        if is_credit_decision and verdict in ['DENY', 'BLOCK']:
            notice_provided = decision_data.get('adverse_action_notice', False)
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.FCRA,
                requirement="adverse_action_notice",
                triggered=not notice_provided,
                status=ComplianceStatus.COMPLIANT if notice_provided else ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
                reason="FCRA requires adverse action notice for credit denials"
            ))

        return flags

    def _check_ecoa(self, decision_data: Dict[str, Any]) -> List[ComplianceFlag]:
        """Check ECOA compliance (equal credit opportunity)"""
        flags = []

        # Prohibited basis check
        uses_protected_characteristics = decision_data.get('uses_protected_characteristics', False)
        if uses_protected_characteristics:
            flags.append(ComplianceFlag(
                standard=ComplianceStandard.ECOA,
                requirement="prohibited_basis",
                triggered=True,
                status=ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.CRITICAL,
                reason="ECOA prohibits discrimination based on protected characteristics"
            ))

        return flags
