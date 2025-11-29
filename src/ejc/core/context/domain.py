"""
Domain-specific ethics tuning for specialized contexts.

Adapts ethical reasoning for specific domains like healthcare, finance, education.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class EthicalPrinciple(Enum):
    """Common ethical principles across domains."""
    BENEFICENCE = "beneficence"  # Do good
    NON_MALEFICENCE = "non_maleficence"  # Do no harm
    AUTONOMY = "autonomy"  # Respect self-determination
    JUSTICE = "justice"  # Fairness and equity
    FIDELITY = "fidelity"  # Trust and loyalty
    TRANSPARENCY = "transparency"  # Openness and honesty
    PRIVACY = "privacy"  # Confidentiality
    ACCOUNTABILITY = "accountability"  # Responsibility


@dataclass
class DomainContext:
    """Domain-specific ethical context."""

    domain_id: str
    name: str
    description: str

    # Principle prioritization (higher = more important)
    principle_weights: Dict[EthicalPrinciple, float] = field(default_factory=dict)

    # Domain-specific rules
    mandatory_checks: List[str] = field(default_factory=list)
    prohibited_actions: Set[str] = field(default_factory=set)
    required_safeguards: List[str] = field(default_factory=list)

    # Risk factors
    high_risk_categories: Set[str] = field(default_factory=set)
    special_protections: List[str] = field(default_factory=list)

    # Regulatory requirements
    compliance_frameworks: List[str] = field(default_factory=list)
    audit_requirements: List[str] = field(default_factory=list)

    def get_prioritized_principles(self) -> List[tuple[EthicalPrinciple, float]]:
        """Get principles in priority order."""
        return sorted(
            self.principle_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def requires_special_handling(self, category: str) -> bool:
        """Check if a category requires special handling."""
        return category in self.high_risk_categories

    def get_safeguards_for(self, action_type: str) -> List[str]:
        """Get required safeguards for an action type."""
        safeguards = list(self.required_safeguards)

        # Add action-specific safeguards
        if action_type in self.high_risk_categories:
            safeguards.append(f"Enhanced monitoring for {action_type}")
            safeguards.append("Human oversight required")

        return safeguards


class DomainSpecialization:
    """Manages domain-specific ethical specializations."""

    def __init__(self):
        """Initialize with common domain contexts."""
        self.domains: Dict[str, DomainContext] = {}
        self._initialize_common_domains()

    def _initialize_common_domains(self):
        """Initialize common domain contexts."""

        # Healthcare
        self.register(DomainContext(
            domain_id="healthcare",
            name="Healthcare",
            description="Medical and health-related applications",
            principle_weights={
                EthicalPrinciple.NON_MALEFICENCE: 1.0,  # Highest priority
                EthicalPrinciple.BENEFICENCE: 0.95,
                EthicalPrinciple.AUTONOMY: 0.9,
                EthicalPrinciple.PRIVACY: 0.85,
                EthicalPrinciple.JUSTICE: 0.8,
                EthicalPrinciple.FIDELITY: 0.75,
                EthicalPrinciple.TRANSPARENCY: 0.7,
                EthicalPrinciple.ACCOUNTABILITY: 0.9,
            },
            mandatory_checks=[
                "Patient safety verification",
                "Medical professional oversight",
                "Informed consent validation",
                "HIPAA compliance check",
            ],
            prohibited_actions={
                "diagnosis_without_oversight",
                "treatment_recommendation_without_disclaimer",
                "phi_disclosure_without_authorization",
            },
            required_safeguards=[
                "Clinical validation required",
                "Licensed professional review",
                "Patient privacy protection",
                "Adverse event monitoring",
            ],
            high_risk_categories={
                "diagnosis",
                "treatment",
                "medication",
                "surgery_related",
                "mental_health",
            },
            special_protections=[
                "Vulnerable populations (children, elderly)",
                "Mental health patients",
                "Emergency situations",
            ],
            compliance_frameworks=["HIPAA", "FDA_regulations", "medical_ethics_codes"],
            audit_requirements=[
                "Clinical outcomes tracking",
                "Safety incident reporting",
                "Quality metrics monitoring",
            ],
        ))

        # Finance
        self.register(DomainContext(
            domain_id="finance",
            name="Financial Services",
            description="Banking, investment, and financial applications",
            principle_weights={
                EthicalPrinciple.FIDELITY: 1.0,  # Fiduciary duty highest
                EthicalPrinciple.TRANSPARENCY: 0.95,
                EthicalPrinciple.ACCOUNTABILITY: 0.9,
                EthicalPrinciple.JUSTICE: 0.85,  # Fair treatment
                EthicalPrinciple.PRIVACY: 0.8,
                EthicalPrinciple.AUTONOMY: 0.75,
                EthicalPrinciple.NON_MALEFICENCE: 0.85,
                EthicalPrinciple.BENEFICENCE: 0.7,
            },
            mandatory_checks=[
                "Fiduciary duty verification",
                "Conflict of interest check",
                "Risk disclosure validation",
                "Regulatory compliance check",
            ],
            prohibited_actions={
                "insider_trading",
                "market_manipulation",
                "undisclosed_conflicts",
                "predatory_lending",
            },
            required_safeguards=[
                "Transaction monitoring",
                "Fraud detection",
                "Risk assessment",
                "Audit trail maintenance",
            ],
            high_risk_categories={
                "investment_advice",
                "lending_decisions",
                "credit_scoring",
                "algorithmic_trading",
            },
            special_protections=[
                "Retail investors",
                "Vulnerable consumers",
                "Small businesses",
            ],
            compliance_frameworks=["SEC", "FINRA", "SOX", "KYC_AML"],
            audit_requirements=[
                "Transaction audit trails",
                "Algorithmic decision logging",
                "Compliance reporting",
            ],
        ))

        # Education
        self.register(DomainContext(
            domain_id="education",
            name="Education",
            description="Educational and learning applications",
            principle_weights={
                EthicalPrinciple.BENEFICENCE: 1.0,  # Student benefit highest
                EthicalPrinciple.JUSTICE: 0.95,  # Educational equity
                EthicalPrinciple.NON_MALEFICENCE: 0.9,
                EthicalPrinciple.AUTONOMY: 0.85,
                EthicalPrinciple.PRIVACY: 0.9,  # Student privacy
                EthicalPrinciple.TRANSPARENCY: 0.8,
                EthicalPrinciple.FIDELITY: 0.75,
                EthicalPrinciple.ACCOUNTABILITY: 0.85,
            },
            mandatory_checks=[
                "Age-appropriateness verification",
                "Educational value assessment",
                "Accessibility check",
                "FERPA compliance",
            ],
            prohibited_actions={
                "student_data_commercialization",
                "discriminatory_grading",
                "privacy_violation",
            },
            required_safeguards=[
                "Parental consent for minors",
                "Data minimization",
                "Bias monitoring in assessments",
                "Age-appropriate content filtering",
            ],
            high_risk_categories={
                "student_assessment",
                "personalization",
                "behavioral_tracking",
                "special_education",
            },
            special_protections=[
                "Minors",
                "Students with disabilities",
                "English language learners",
            ],
            compliance_frameworks=["FERPA", "COPPA", "accessibility_standards"],
            audit_requirements=[
                "Bias audits in assessments",
                "Learning outcome tracking",
                "Privacy compliance monitoring",
            ],
        ))

        # General/Default
        self.register(DomainContext(
            domain_id="general",
            name="General Purpose",
            description="General-purpose applications",
            principle_weights={
                EthicalPrinciple.NON_MALEFICENCE: 1.0,
                EthicalPrinciple.AUTONOMY: 0.9,
                EthicalPrinciple.TRANSPARENCY: 0.85,
                EthicalPrinciple.PRIVACY: 0.85,
                EthicalPrinciple.JUSTICE: 0.8,
                EthicalPrinciple.ACCOUNTABILITY: 0.8,
                EthicalPrinciple.BENEFICENCE: 0.75,
                EthicalPrinciple.FIDELITY: 0.7,
            },
            mandatory_checks=[
                "Basic safety check",
                "Privacy impact assessment",
                "User consent validation",
            ],
            prohibited_actions={
                "deception",
                "manipulation",
                "unauthorized_data_use",
            },
            required_safeguards=[
                "Clear user notification",
                "Opt-out mechanisms",
                "Data protection",
            ],
            high_risk_categories={
                "personal_data",
                "automated_decisions",
                "behavioral_influence",
            },
            compliance_frameworks=["general_privacy_laws"],
        ))

    def register(self, domain: DomainContext):
        """Register a domain context."""
        self.domains[domain.domain_id] = domain

    def get(self, domain_id: str) -> Optional[DomainContext]:
        """Get domain context by ID."""
        return self.domains.get(domain_id, self.domains.get("general"))

    def apply_domain_ethics(
        self,
        action: Dict,
        domain: DomainContext
    ) -> Dict:
        """
        Apply domain-specific ethical analysis to an action.

        Args:
            action: Action dict to analyze
            domain: Domain context

        Returns:
            Domain-specific analysis
        """
        action_type = action.get("type", "unknown")
        category = action.get("category", "general")

        # Check prohibitions
        violations = []
        if action_type in domain.prohibited_actions:
            violations.append({
                "type": "prohibited_action",
                "action": action_type,
                "severity": "critical",
            })

        # Check required safeguards
        safeguards = domain.get_safeguards_for(action_type)
        missing_safeguards = [
            s for s in safeguards
            if s not in action.get("safeguards", [])
        ]

        # Check mandatory checks
        missing_checks = [
            c for c in domain.mandatory_checks
            if c not in action.get("checks_performed", [])
        ]

        # Assess risk level
        is_high_risk = domain.requires_special_handling(category)

        # Evaluate principle alignment
        principle_scores = {}
        for principle, weight in domain.principle_weights.items():
            # Simplified scoring - real implementation would be more sophisticated
            alignment = action.get("principle_scores", {}).get(principle.value, 0.5)
            weighted_score = alignment * weight
            principle_scores[principle.value] = {
                "alignment": alignment,
                "weight": weight,
                "weighted_score": weighted_score,
            }

        overall_score = sum(
            scores["weighted_score"]
            for scores in principle_scores.values()
        ) / len(principle_scores) if principle_scores else 0.5

        return {
            "domain": domain.name,
            "overall_score": overall_score,
            "is_high_risk": is_high_risk,
            "violations": violations,
            "missing_safeguards": missing_safeguards,
            "missing_checks": missing_checks,
            "principle_alignment": principle_scores,
            "compliance_required": domain.compliance_frameworks,
            "recommendations": self._generate_recommendations(
                domain, violations, missing_safeguards, is_high_risk
            ),
        }

    def _generate_recommendations(
        self,
        domain: DomainContext,
        violations: List[Dict],
        missing_safeguards: List[str],
        is_high_risk: bool
    ) -> List[str]:
        """Generate domain-specific recommendations."""
        recommendations = []

        if violations:
            recommendations.append(
                f"⛔ CRITICAL: {len(violations)} prohibited actions detected"
            )

        if missing_safeguards:
            recommendations.append(
                f"⚠️ Implement required safeguards: {', '.join(missing_safeguards[:3])}"
            )

        if is_high_risk:
            recommendations.append(
                "🔍 High-risk category - enhanced oversight required"
            )

        if not recommendations:
            recommendations.append(
                f"✅ Action appears compliant with {domain.name} domain ethics"
            )

        return recommendations
