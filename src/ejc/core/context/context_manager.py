"""
Main context manager integrating jurisdiction, cultural, and domain contexts.

Provides unified API for context-aware ethical reasoning.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .jurisdiction import JurisdictionRegistry, JurisdictionContext
from .cultural import CulturalNormAdapter, CulturalContext
from .domain import DomainSpecialization, DomainContext
from ...utils.logging import get_logger

logger = get_logger("ejc.context")


@dataclass
class ContextualizedRequest:
    """Request with full contextual information."""

    action: Dict
    jurisdictions: List[JurisdictionContext]
    cultures: List[CulturalContext]
    domain: DomainContext

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "jurisdictions": [j.jurisdiction_id for j in self.jurisdictions],
            "cultures": [c.culture_id for c in self.cultures],
            "domain": self.domain.domain_id,
        }


class ContextManager:
    """
    Main context manager for context-aware ethical reasoning.

    Integrates:
    - Jurisdiction awareness (legal/regulatory)
    - Cultural sensitivity (values/norms)
    - Domain specialization (healthcare, finance, etc.)
    """

    def __init__(self):
        """Initialize context manager."""
        self.jurisdiction_registry = JurisdictionRegistry()
        self.cultural_adapter = CulturalNormAdapter()
        self.domain_specialization = DomainSpecialization()

    def contextualize_request(
        self,
        action: Dict,
        user_location: Optional[str] = None,
        data_location: Optional[str] = None,
        service_location: Optional[str] = None,
        culture_id: Optional[str] = None,
        domain_id: Optional[str] = None
    ) -> ContextualizedRequest:
        """
        Add full context to a request.

        Args:
            action: Action to contextualize
            user_location: User's jurisdiction
            data_location: Data storage jurisdiction
            service_location: Service provision jurisdiction
            culture_id: Cultural context ID
            domain_id: Domain ID

        Returns:
            Contextualized request
        """
        # Determine applicable jurisdictions
        jurisdictions = self.jurisdiction_registry.get_applicable_jurisdictions(
            user_location, data_location, service_location
        )

        # Get cultural context
        cultures = []
        if culture_id:
            culture = self.cultural_adapter.get(culture_id)
            if culture:
                cultures.append(culture)

        # Infer culture from jurisdiction if not specified
        if not cultures and jurisdictions:
            # Simple mapping - could be more sophisticated
            culture_map = {
                "EU": "NORDIC",  # Simplified
                "US-CA": "US",
                "CN": "CN",
                "BR": "US",  # Simplified
            }
            for jurisdiction in jurisdictions:
                culture_id = culture_map.get(jurisdiction.jurisdiction_id)
                if culture_id:
                    culture = self.cultural_adapter.get(culture_id)
                    if culture and culture not in cultures:
                        cultures.append(culture)

        # Get domain context
        domain = self.domain_specialization.get(domain_id or "general")

        logger.info(
            f"Contextualized request: {len(jurisdictions)} jurisdictions, "
            f"{len(cultures)} cultures, domain={domain.name}"
        )

        return ContextualizedRequest(
            action=action,
            jurisdictions=jurisdictions,
            cultures=cultures,
            domain=domain,
        )

    def analyze_with_context(
        self,
        contextualized_request: ContextualizedRequest
    ) -> Dict:
        """
        Perform comprehensive context-aware analysis.

        Args:
            contextualized_request: Contextualized request

        Returns:
            Comprehensive analysis with all contextual considerations
        """
        action = contextualized_request.action
        jurisdictions = contextualized_request.jurisdictions
        cultures = contextualized_request.cultures
        domain = contextualized_request.domain

        # Jurisdiction compliance check
        jurisdiction_analysis = self.jurisdiction_registry.check_compliance(
            action, jurisdictions
        )

        # Cultural sensitivity check
        content = action.get("content", action.get("description", ""))
        cultural_analysis = self.cultural_adapter.check_cultural_sensitivity(
            content, cultures
        )

        # Domain-specific ethics analysis
        domain_analysis = self.domain_specialization.apply_domain_ethics(
            action, domain
        )

        # Combine analyses
        overall_compliant = (
            jurisdiction_analysis["compliant"] and
            cultural_analysis["culturally_appropriate"] and
            len(domain_analysis["violations"]) == 0
        )

        # Aggregate all recommendations
        all_recommendations = []
        all_recommendations.extend(jurisdiction_analysis.get("warnings", []))
        all_recommendations.extend(
            [f"Cultural: {w['recommendation']}" for w in cultural_analysis.get("warnings", [])]
        )
        all_recommendations.extend(domain_analysis.get("recommendations", []))

        # Calculate overall risk level
        risk_factors = []
        if not jurisdiction_analysis["compliant"]:
            risk_factors.append("jurisdiction_violations")
        if not cultural_analysis["culturally_appropriate"]:
            risk_factors.append("cultural_issues")
        if domain_analysis["is_high_risk"]:
            risk_factors.append("high_risk_domain")

        risk_level = self._calculate_risk_level(risk_factors, jurisdiction_analysis, domain_analysis)

        return {
            "overall_compliant": overall_compliant,
            "risk_level": risk_level,
            "jurisdiction_analysis": jurisdiction_analysis,
            "cultural_analysis": cultural_analysis,
            "domain_analysis": domain_analysis,
            "context": contextualized_request.to_dict(),
            "recommendations": all_recommendations,
            "summary": self._generate_summary(
                overall_compliant, risk_level, risk_factors
            ),
        }

    def get_context_requirements(
        self,
        action_type: str,
        jurisdictions: List[str],
        cultures: List[str],
        domain: str
    ) -> Dict:
        """
        Get all contextual requirements for an action type.

        Args:
            action_type: Type of action
            jurisdictions: List of jurisdiction IDs
            cultures: List of culture IDs
            domain: Domain ID

        Returns:
            Comprehensive requirements
        """
        # Get jurisdiction contexts
        jurisdiction_contexts = [
            self.jurisdiction_registry.get(j)
            for j in jurisdictions
            if self.jurisdiction_registry.get(j)
        ]

        # Get cultural contexts
        culture_contexts = [
            self.cultural_adapter.get(c)
            for c in cultures
            if self.cultural_adapter.get(c)
        ]

        # Get domain context
        domain_context = self.domain_specialization.get(domain)

        # Aggregate requirements
        jurisdiction_requirements = self.jurisdiction_registry.get_strictest_requirements(
            jurisdiction_contexts, action_type
        )

        cultural_considerations = []
        for culture in culture_contexts:
            considerations = culture.get_cultural_considerations(action_type)
            cultural_considerations.extend(considerations)

        domain_safeguards = domain_context.get_safeguards_for(action_type)
        domain_checks = domain_context.mandatory_checks

        return {
            "action_type": action_type,
            "jurisdiction_requirements": jurisdiction_requirements,
            "cultural_considerations": list(set(cultural_considerations)),
            "domain_safeguards": domain_safeguards,
            "domain_checks": domain_checks,
            "combined_requirements": self._combine_requirements(
                jurisdiction_requirements,
                cultural_considerations,
                domain_safeguards,
                domain_checks
            ),
        }

    def _calculate_risk_level(
        self,
        risk_factors: List[str],
        jurisdiction_analysis: Dict,
        domain_analysis: Dict
    ) -> str:
        """Calculate overall risk level."""
        if jurisdiction_analysis.get("violations"):
            return "critical"

        if domain_analysis.get("violations"):
            return "high"

        if len(risk_factors) >= 2:
            return "high"

        if len(risk_factors) == 1:
            return "medium"

        if jurisdiction_analysis.get("warnings") or domain_analysis.get("missing_safeguards"):
            return "medium"

        return "low"

    def _generate_summary(
        self,
        compliant: bool,
        risk_level: str,
        risk_factors: List[str]
    ) -> str:
        """Generate executive summary."""
        if compliant and risk_level == "low":
            return "✅ Action is contextually appropriate and compliant"

        if not compliant:
            return f"⛔ Action has compliance issues: {', '.join(risk_factors)}"

        if risk_level == "high":
            return f"⚠️ High risk action - requires enhanced oversight"

        if risk_level == "medium":
            return f"⚠️ Moderate concerns - review recommendations"

        return "Action requires contextual review"

    def _combine_requirements(
        self,
        jurisdiction_reqs: List[str],
        cultural_considerations: List[str],
        domain_safeguards: List[str],
        domain_checks: List[str]
    ) -> List[Dict]:
        """Combine all requirements into prioritized list."""
        combined = []

        # Critical: jurisdiction requirements
        for req in jurisdiction_reqs:
            combined.append({
                "requirement": req,
                "type": "jurisdiction",
                "priority": "critical",
            })

        # High: domain checks
        for check in domain_checks:
            combined.append({
                "requirement": check,
                "type": "domain_check",
                "priority": "high",
            })

        # Medium: domain safeguards
        for safeguard in domain_safeguards:
            combined.append({
                "requirement": safeguard,
                "type": "domain_safeguard",
                "priority": "medium",
            })

        # Low: cultural considerations
        for consideration in cultural_considerations:
            combined.append({
                "requirement": consideration,
                "type": "cultural",
                "priority": "low",
            })

        return combined
