"""
Cultural norm adaptation for culturally-sensitive ethical reasoning.

Adapts decisions based on cultural values and sensitivities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class CulturalDimension(Enum):
    """Hofstede's cultural dimensions."""
    INDIVIDUALISM_COLLECTIVISM = "individualism"
    POWER_DISTANCE = "power_distance"
    UNCERTAINTY_AVOIDANCE = "uncertainty"
    MASCULINITY_FEMININITY = "masculinity"
    LONG_TERM_ORIENTATION = "long_term"
    INDULGENCE_RESTRAINT = "indulgence"


@dataclass
class CulturalContext:
    """Cultural context information."""

    culture_id: str
    name: str
    region: str

    # Hofstede dimensions (0-100 scale)
    individualism: int = 50  # Low=collectivist, High=individualist
    power_distance: int = 50  # Low=egalitarian, High=hierarchical
    uncertainty_avoidance: int = 50  # Low=flexible, High=structured
    masculinity: int = 50  # Low=nurturing, High=competitive
    long_term_orientation: int = 50  # Low=short-term, High=long-term
    indulgence: int = 50  # Low=restraint, High=indulgent

    # Communication style
    high_context_communication: bool = False
    direct_communication: bool = True

    # Social norms
    family_importance: str = "medium"  # "low", "medium", "high"
    respect_for_authority: str = "medium"
    religious_sensitivity: str = "medium"

    # Sensitive topics
    taboo_topics: Set[str] = field(default_factory=set)
    sensitive_topics: Set[str] = field(default_factory=set)

    # Values prioritization
    core_values: List[str] = field(default_factory=list)

    def get_communication_style(self) -> str:
        """Get recommended communication style."""
        if self.high_context_communication:
            return "implicit, relationship-focused"
        elif self.direct_communication:
            return "direct, fact-focused"
        else:
            return "balanced"

    def is_sensitive_topic(self, topic: str) -> bool:
        """Check if a topic is culturally sensitive."""
        return topic in self.taboo_topics or topic in self.sensitive_topics

    def get_cultural_considerations(self, action_type: str) -> List[str]:
        """Get cultural considerations for an action type."""
        considerations = []

        if action_type == "personal_data":
            if self.individualism < 40:  # Collectivist
                considerations.append("Consider family/group privacy concerns")
            if self.power_distance > 60:
                considerations.append("Respect hierarchical data access patterns")

        elif action_type == "decision_explanation":
            if self.high_context_communication:
                considerations.append("Provide context-rich explanations")
            if self.uncertainty_avoidance > 60:
                considerations.append("Provide detailed, structured explanations")

        elif action_type == "content_moderation":
            for topic in self.taboo_topics:
                considerations.append(f"Strong sensitivity to {topic}")
            if self.religious_sensitivity == "high":
                considerations.append("High religious sensitivity required")

        return considerations


class CulturalNormAdapter:
    """Adapts ethical reasoning based on cultural context."""

    def __init__(self):
        """Initialize with common cultural contexts."""
        self.cultures: Dict[str, CulturalContext] = {}
        self._initialize_common_cultures()

    def _initialize_common_cultures(self):
        """Initialize common cultural contexts (simplified representations)."""

        # US/Western
        self.register(CulturalContext(
            culture_id="US",
            name="United States",
            region="North America",
            individualism=91,
            power_distance=40,
            uncertainty_avoidance=46,
            masculinity=62,
            long_term_orientation=26,
            indulgence=68,
            high_context_communication=False,
            direct_communication=True,
            family_importance="medium",
            respect_for_authority="medium",
            religious_sensitivity="medium",
            sensitive_topics={"politics", "religion", "personal_finance"},
            core_values=["freedom", "individual_rights", "equality"],
        ))

        # East Asian (China as example)
        self.register(CulturalContext(
            culture_id="CN",
            name="China",
            region="East Asia",
            individualism=20,
            power_distance=80,
            uncertainty_avoidance=30,
            masculinity=66,
            long_term_orientation=87,
            indulgence=24,
            high_context_communication=True,
            direct_communication=False,
            family_importance="high",
            respect_for_authority="high",
            religious_sensitivity="low",
            taboo_topics={"political_criticism"},
            sensitive_topics={"family_honor", "social_status"},
            core_values=["harmony", "respect", "family", "long_term_thinking"],
        ))

        # Middle East (simplified)
        self.register(CulturalContext(
            culture_id="MENA",
            name="Middle East",
            region="Middle East",
            individualism=38,
            power_distance=80,
            uncertainty_avoidance=68,
            masculinity=53,
            long_term_orientation=35,
            indulgence=34,
            high_context_communication=True,
            direct_communication=False,
            family_importance="high",
            respect_for_authority="high",
            religious_sensitivity="high",
            taboo_topics={"religious_criticism", "immodesty"},
            sensitive_topics={"family_honor", "gender_roles"},
            core_values=["honor", "hospitality", "faith", "family"],
        ))

        # Scandinavia
        self.register(CulturalContext(
            culture_id="NORDIC",
            name="Nordic Countries",
            region="Northern Europe",
            individualism=71,
            power_distance=31,
            uncertainty_avoidance=35,
            masculinity=8,  # Very nurturing/egalitarian
            long_term_orientation=53,
            indulgence=57,
            high_context_communication=False,
            direct_communication=True,
            family_importance="medium",
            respect_for_authority="low",
            religious_sensitivity="low",
            sensitive_topics={"inequality", "environmental_harm"},
            core_values=["equality", "sustainability", "work-life_balance", "welfare"],
        ))

    def register(self, culture: CulturalContext):
        """Register a cultural context."""
        self.cultures[culture.culture_id] = culture

    def get(self, culture_id: str) -> Optional[CulturalContext]:
        """Get cultural context by ID."""
        return self.cultures.get(culture_id)

    def adapt_message(
        self,
        message: str,
        culture: CulturalContext
    ) -> Dict:
        """
        Adapt a message for cultural context.

        Args:
            message: Original message
            culture: Target cultural context

        Returns:
            Adaptation recommendations
        """
        recommendations = []

        # Communication style adaptation
        if culture.high_context_communication:
            recommendations.append("Add contextual background and relationship building")

        if not culture.direct_communication:
            recommendations.append("Use indirect phrasing to soften assertions")

        # Respect for authority
        if culture.respect_for_authority == "high" and culture.power_distance > 60:
            recommendations.append("Show deference to authority figures")

        # Cultural values alignment
        if "equality" in culture.core_values and "inequality" in message.lower():
            recommendations.append("Frame in terms of fairness and equal treatment")

        if "harmony" in culture.core_values:
            recommendations.append("Emphasize consensus and avoiding conflict")

        return {
            "adapted": len(recommendations) > 0,
            "recommendations": recommendations,
            "communication_style": culture.get_communication_style(),
        }

    def check_cultural_sensitivity(
        self,
        content: str,
        cultures: List[CulturalContext]
    ) -> Dict:
        """
        Check content for cultural sensitivity issues.

        Args:
            content: Content to check
            cultures: List of cultural contexts to consider

        Returns:
            Sensitivity report
        """
        issues = []
        warnings = []

        content_lower = content.lower()

        for culture in cultures:
            # Check taboo topics
            for topic in culture.taboo_topics:
                if topic.replace("_", " ") in content_lower:
                    issues.append({
                        "culture": culture.name,
                        "issue": f"Taboo topic: {topic}",
                        "severity": "high",
                    })

            # Check sensitive topics
            for topic in culture.sensitive_topics:
                if topic.replace("_", " ") in content_lower:
                    warnings.append({
                        "culture": culture.name,
                        "topic": topic,
                        "severity": "medium",
                        "recommendation": f"Approach {topic} with cultural sensitivity",
                    })

        return {
            "culturally_appropriate": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "cultures_considered": [c.name for c in cultures],
        }

    def get_value_alignment(
        self,
        action_values: List[str],
        culture: CulturalContext
    ) -> Dict:
        """
        Check alignment between action values and cultural values.

        Args:
            action_values: Values promoted by the action
            culture: Cultural context

        Returns:
            Alignment analysis
        """
        aligned = []
        conflicting = []
        neutral = []

        for value in action_values:
            value_lower = value.lower().replace("_", " ")

            # Check for alignment
            if any(
                cv.lower().replace("_", " ") in value_lower
                or value_lower in cv.lower().replace("_", " ")
                for cv in culture.core_values
            ):
                aligned.append(value)

            # Check for conflict (simplified)
            elif (culture.individualism < 30 and "individual" in value_lower):
                conflicting.append(value)
            elif (culture.individualism > 70 and "collective" in value_lower):
                conflicting.append(value)
            else:
                neutral.append(value)

        alignment_score = len(aligned) / len(action_values) if action_values else 0.0

        return {
            "alignment_score": alignment_score,
            "aligned_values": aligned,
            "conflicting_values": conflicting,
            "neutral_values": neutral,
            "recommendation": self._get_alignment_recommendation(alignment_score),
        }

    def _get_alignment_recommendation(self, score: float) -> str:
        """Get recommendation based on alignment score."""
        if score > 0.7:
            return "Strong cultural alignment - proceed with confidence"
        elif score > 0.4:
            return "Moderate alignment - consider adaptations"
        else:
            return "Weak alignment - significant cultural adaptation needed"
