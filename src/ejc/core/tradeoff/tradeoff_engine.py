"""
Ethical Trade-Off Engine (TFE) - Phase 5A

Detects and resolves ethical value tensions in AI decision-making.

Implements World Bank AI Governance Report Section 4.5 recommendations:
"These trade-offs arise because optimizing one aspect can detract from another,
requiring careful balance" (Report p.22, Table 2)

Key Trade-Offs Managed:
1. Fairness ↔ Transparency
2. Privacy ↔ Utility
3. Transparency ↔ Accountability
4. Fairness ↔ Accountability

References:
- World Bank Report Section 4.5: "Comprehensive Ethics"
- World Bank Report p.22, Table 2: "Ethical Trade-Offs"
"""

from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class EthicalPrinciple(Enum):
    """Core ethical principles that may conflict."""
    FAIRNESS = "fairness"
    TRANSPARENCY = "transparency"
    PRIVACY = "privacy"
    ACCOUNTABILITY = "accountability"
    UTILITY = "utility"
    AUTONOMY = "autonomy"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"


class TradeOffType(Enum):
    """Types of ethical trade-offs."""
    FAIRNESS_TRANSPARENCY = "fairness_transparency"
    PRIVACY_UTILITY = "privacy_utility"
    TRANSPARENCY_ACCOUNTABILITY = "transparency_accountability"
    FAIRNESS_ACCOUNTABILITY = "fairness_accountability"
    PRIVACY_TRANSPARENCY = "privacy_transparency"
    UTILITY_FAIRNESS = "utility_fairness"


@dataclass
class TradeOffDetection:
    """Represents a detected ethical trade-off."""
    tradeoff_type: TradeOffType
    principle1: EthicalPrinciple
    principle2: EthicalPrinciple
    principle1_score: float  # 0-1, how well principle1 is satisfied
    principle2_score: float  # 0-1, how well principle2 is satisfied
    tension_level: float     # 0-1, degree of conflict
    description: str
    recommendations: List[str]


@dataclass
class TradeOffResolution:
    """Represents a resolved trade-off with recommendations."""
    detection: TradeOffDetection
    resolution_strategy: str
    balanced_approach: str
    implementation_steps: List[str]
    monitoring_metrics: List[str]
    confidence: float


class TradeOffEngine:
    """
    Ethical Trade-Off Engine.

    Detects ethical value tensions, analyzes conflicts, and recommends
    balanced resolutions aligned with World Bank governance principles.
    """

    # Trade-off thresholds
    TENSION_THRESHOLD = 0.3  # Minimum tension to flag a trade-off
    HIGH_TENSION_THRESHOLD = 0.6  # High tension requiring immediate attention

    def __init__(self):
        """Initialize the Trade-Off Engine."""
        self.detected_tradeoffs: List[TradeOffDetection] = []
        self.resolution_history: List[TradeOffResolution] = []

    def analyze_critic_signals(
        self,
        critic_results: Dict[str, Any]
    ) -> List[TradeOffDetection]:
        """
        Analyze critic outputs to detect ethical trade-offs.

        Args:
            critic_results: Dictionary mapping critic names to their results
                           Each result should contain verdict, confidence, etc.

        Returns:
            List of detected trade-offs
        """
        self.detected_tradeoffs = []

        # Extract ethical principle scores from critics
        principle_scores = self._extract_principle_scores(critic_results)

        # Detect trade-offs between principles
        self._detect_fairness_transparency_tradeoff(principle_scores, critic_results)
        self._detect_privacy_utility_tradeoff(principle_scores, critic_results)
        self._detect_transparency_accountability_tradeoff(principle_scores, critic_results)
        self._detect_fairness_accountability_tradeoff(principle_scores, critic_results)

        return self.detected_tradeoffs

    def _extract_principle_scores(
        self,
        critic_results: Dict[str, Any]
    ) -> Dict[EthicalPrinciple, float]:
        """
        Extract ethical principle scores from critic results.

        Maps critic names to ethical principles and extracts confidence/scores.
        """
        scores = {}

        # Map critic results to principles
        if 'BiasObjectivityCritic' in critic_results:
            result = critic_results['BiasObjectivityCritic']
            fairness_score = 1.0 - result.get('bias_risk_score', 0.5)
            scores[EthicalPrinciple.FAIRNESS] = fairness_score

        if 'TransparencyCritic' in critic_results:
            result = critic_results['TransparencyCritic']
            scores[EthicalPrinciple.TRANSPARENCY] = result.get('confidence', 0.5)

        if 'PrivacyProtectionCritic' in critic_results:
            result = critic_results['PrivacyProtectionCritic']
            scores[EthicalPrinciple.PRIVACY] = result.get('confidence', 0.5)

        if 'AccountabilityCritic' in critic_results:
            result = critic_results['AccountabilityCritic']
            scores[EthicalPrinciple.ACCOUNTABILITY] = result.get('confidence', 0.5)

        # Default scores for missing principles
        for principle in EthicalPrinciple:
            if principle not in scores:
                scores[principle] = 0.5  # Neutral

        return scores

    def _detect_fairness_transparency_tradeoff(
        self,
        scores: Dict[EthicalPrinciple, float],
        critic_results: Dict[str, Any]
    ):
        """
        Detect Fairness ↔ Transparency trade-off.

        Example: Revealing model internals (transparency) may expose protected
        group information (reducing fairness guarantees).
        """
        fairness = scores.get(EthicalPrinciple.FAIRNESS, 0.5)
        transparency = scores.get(EthicalPrinciple.TRANSPARENCY, 0.5)

        # Detect tension: high fairness but low transparency, or vice versa
        tension = abs(fairness - transparency)

        if tension > self.TENSION_THRESHOLD:
            if fairness > transparency:
                desc = "High fairness achieved but with reduced transparency. Model may use protected attributes in complex ways that are difficult to explain."
                recommendations = [
                    "Implement fairness-aware explainability techniques",
                    "Provide group-level explanations instead of individual",
                    "Use privacy-preserving explanation methods (e.g., differential privacy for SHAP)"
                ]
            else:
                desc = "High transparency but potential fairness concerns. Exposed model logic may reveal disparate treatment."
                recommendations = [
                    "Audit explanations for bias amplification",
                    "Apply fairness constraints before generating explanations",
                    "Use aggregated explanations to avoid revealing individual protected attributes"
                ]

            detection = TradeOffDetection(
                tradeoff_type=TradeOffType.FAIRNESS_TRANSPARENCY,
                principle1=EthicalPrinciple.FAIRNESS,
                principle2=EthicalPrinciple.TRANSPARENCY,
                principle1_score=fairness,
                principle2_score=transparency,
                tension_level=tension,
                description=desc,
                recommendations=recommendations
            )
            self.detected_tradeoffs.append(detection)

    def _detect_privacy_utility_tradeoff(
        self,
        scores: Dict[EthicalPrinciple, float],
        critic_results: Dict[str, Any]
    ):
        """
        Detect Privacy ↔ Utility trade-off.

        Example: Strong privacy protections (e.g., differential privacy) may
        reduce model accuracy and utility.
        """
        privacy = scores.get(EthicalPrinciple.PRIVACY, 0.5)
        utility = scores.get(EthicalPrinciple.UTILITY, 0.5)

        tension = abs(privacy - utility)

        if tension > self.TENSION_THRESHOLD:
            if privacy > utility:
                desc = "Strong privacy protections in place but may limit model utility and accuracy."
                recommendations = [
                    "Optimize privacy budget allocation",
                    "Use advanced PETs (federated learning, homomorphic encryption)",
                    "Evaluate privacy-utility frontier with systematic experimentation",
                    "Consider tiered access levels with varying privacy guarantees"
                ]
            else:
                desc = "High utility achieved but with potential privacy risks. Model may rely on sensitive attributes."
                recommendations = [
                    "Implement privacy-enhancing technologies (PETs)",
                    "Apply differential privacy to model outputs",
                    "Use data minimization and pseudonymization",
                    "Conduct privacy impact assessment (PIA)"
                ]

            detection = TradeOffDetection(
                tradeoff_type=TradeOffType.PRIVACY_UTILITY,
                principle1=EthicalPrinciple.PRIVACY,
                principle2=EthicalPrinciple.UTILITY,
                principle1_score=privacy,
                principle2_score=utility,
                tension_level=tension,
                description=desc,
                recommendations=recommendations
            )
            self.detected_tradeoffs.append(detection)

    def _detect_transparency_accountability_tradeoff(
        self,
        scores: Dict[EthicalPrinciple, float],
        critic_results: Dict[str, Any]
    ):
        """
        Detect Transparency ↔ Accountability trade-off.

        Example: Full transparency of decision processes may create accountability
        gaps if no single entity can be held responsible.
        """
        transparency = scores.get(EthicalPrinciple.TRANSPARENCY, 0.5)
        accountability = scores.get(EthicalPrinciple.ACCOUNTABILITY, 0.5)

        tension = abs(transparency - accountability)

        if tension > self.TENSION_THRESHOLD:
            if transparency > accountability:
                desc = "High transparency but unclear accountability. Distributed responsibility may dilute ownership."
                recommendations = [
                    "Implement clear responsibility assignment matrix (RACI)",
                    "Define escalation paths for different decision types",
                    "Maintain audit logs linking decisions to responsible parties",
                    "Establish governance board for high-stakes decisions"
                ]
            else:
                desc = "Clear accountability but limited transparency. Decision processes may be opaque to stakeholders."
                recommendations = [
                    "Publish decision guidelines and criteria",
                    "Provide tiered explanations based on stakeholder roles",
                    "Implement external audit mechanisms",
                    "Create stakeholder feedback channels"
                ]

            detection = TradeOffDetection(
                tradeoff_type=TradeOffType.TRANSPARENCY_ACCOUNTABILITY,
                principle1=EthicalPrinciple.TRANSPARENCY,
                principle2=EthicalPrinciple.ACCOUNTABILITY,
                principle1_score=transparency,
                principle2_score=accountability,
                tension_level=tension,
                description=desc,
                recommendations=recommendations
            )
            self.detected_tradeoffs.append(detection)

    def _detect_fairness_accountability_tradeoff(
        self,
        scores: Dict[EthicalPrinciple, float],
        critic_results: Dict[str, Any]
    ):
        """
        Detect Fairness ↔ Accountability trade-off.

        Example: Ensuring group fairness may require distributed decision-making
        that complicates individual accountability.
        """
        fairness = scores.get(EthicalPrinciple.FAIRNESS, 0.5)
        accountability = scores.get(EthicalPrinciple.ACCOUNTABILITY, 0.5)

        tension = abs(fairness - accountability)

        if tension > self.TENSION_THRESHOLD:
            if fairness > accountability:
                desc = "Strong fairness measures but accountability challenges. Multiple stakeholders involved in ensuring fairness."
                recommendations = [
                    "Implement distributed responsibility framework (per WB Report p.10)",
                    "Assign fairness monitoring roles across AI lifecycle",
                    "Create fairness review boards with clear mandates",
                    "Document fairness-accountability tradeoff decisions"
                ]
            else:
                desc = "Clear accountability but potential fairness gaps. Centralized decisions may overlook group impacts."
                recommendations = [
                    "Include diverse stakeholders in accountability chain",
                    "Mandate fairness checks in decision approval process",
                    "Establish fairness metrics as accountability KPIs",
                    "Require fairness impact statements for major decisions"
                ]

            detection = TradeOffDetection(
                tradeoff_type=TradeOffType.FAIRNESS_ACCOUNTABILITY,
                principle1=EthicalPrinciple.FAIRNESS,
                principle2=EthicalPrinciple.ACCOUNTABILITY,
                principle1_score=fairness,
                principle2_score=accountability,
                tension_level=tension,
                description=desc,
                recommendations=recommendations
            )
            self.detected_tradeoffs.append(detection)

    def resolve_tradeoff(
        self,
        detection: TradeOffDetection,
        context: Optional[Dict[str, Any]] = None
    ) -> TradeOffResolution:
        """
        Generate resolution strategy for a detected trade-off.

        Args:
            detection: The trade-off detection to resolve
            context: Optional context about the application domain, risk level, etc.

        Returns:
            Trade-off resolution with balanced approach
        """
        context = context or {}
        risk_level = context.get('risk_level', 'medium')  # low, medium, high

        # Determine resolution strategy based on trade-off type and context
        if detection.tradeoff_type == TradeOffType.FAIRNESS_TRANSPARENCY:
            resolution = self._resolve_fairness_transparency(detection, risk_level)

        elif detection.tradeoff_type == TradeOffType.PRIVACY_UTILITY:
            resolution = self._resolve_privacy_utility(detection, risk_level)

        elif detection.tradeoff_type == TradeOffType.TRANSPARENCY_ACCOUNTABILITY:
            resolution = self._resolve_transparency_accountability(detection, risk_level)

        elif detection.tradeoff_type == TradeOffType.FAIRNESS_ACCOUNTABILITY:
            resolution = self._resolve_fairness_accountability(detection, risk_level)

        else:
            # Generic resolution
            resolution = self._generic_resolution(detection, risk_level)

        self.resolution_history.append(resolution)
        return resolution

    def _resolve_fairness_transparency(
        self,
        detection: TradeOffDetection,
        risk_level: str
    ) -> TradeOffResolution:
        """Resolve Fairness-Transparency trade-off."""
        if risk_level == 'high':
            # Prioritize fairness in high-risk scenarios
            strategy = "Fairness-First with Constrained Transparency"
            approach = "Implement strong fairness guarantees while providing aggregated, privacy-preserving explanations."
        else:
            # Balance both in lower-risk scenarios
            strategy = "Balanced Approach with Fairness-Aware Explanations"
            approach = "Use fairness-aware XAI techniques (e.g., group-wise SHAP) to maintain both principles."

        return TradeOffResolution(
            detection=detection,
            resolution_strategy=strategy,
            balanced_approach=approach,
            implementation_steps=detection.recommendations,
            monitoring_metrics=[
                'Disparate impact ratio',
                'Explanation coverage',
                'User comprehension scores',
                'Protected attribute exposure'
            ],
            confidence=0.8
        )

    def _resolve_privacy_utility(
        self,
        detection: TradeOffDetection,
        risk_level: str
    ) -> TradeOffResolution:
        """Resolve Privacy-Utility trade-off."""
        if risk_level == 'high':
            strategy = "Privacy-Preserving with Acceptable Utility Degradation"
            approach = "Apply strong PETs (differential privacy, federated learning) even if utility decreases moderately."
        else:
            strategy = "Optimize Privacy-Utility Frontier"
            approach = "Systematically explore privacy budget allocation to maximize utility under privacy constraints."

        return TradeOffResolution(
            detection=detection,
            resolution_strategy=strategy,
            balanced_approach=approach,
            implementation_steps=detection.recommendations,
            monitoring_metrics=[
                'Privacy budget consumption',
                'Model accuracy',
                'Reconstruction attack success rate',
                'User satisfaction'
            ],
            confidence=0.85
        )

    def _resolve_transparency_accountability(
        self,
        detection: TradeOffDetection,
        risk_level: str
    ) -> TradeOffResolution:
        """Resolve Transparency-Accountability trade-off."""
        strategy = "Distributed Responsibility with Clear Documentation"
        approach = "Implement distributed responsibility framework (per WB Report) with comprehensive audit trails."

        return TradeOffResolution(
            detection=detection,
            resolution_strategy=strategy,
            balanced_approach=approach,
            implementation_steps=detection.recommendations,
            monitoring_metrics=[
                'Audit trail completeness',
                'Responsibility assignment coverage',
                'Stakeholder clarity scores',
                'Decision appeal rates'
            ],
            confidence=0.75
        )

    def _resolve_fairness_accountability(
        self,
        detection: TradeOffDetection,
        risk_level: str
    ) -> TradeOffResolution:
        """Resolve Fairness-Accountability trade-off."""
        strategy = "Multi-Stakeholder Accountability with Fairness Mandates"
        approach = "Assign fairness oversight roles across the AI lifecycle with clear accountability for each stage."

        return TradeOffResolution(
            detection=detection,
            resolution_strategy=strategy,
            balanced_approach=approach,
            implementation_steps=detection.recommendations,
            monitoring_metrics=[
                'Fairness metric compliance',
                'Accountability role coverage',
                'Review board effectiveness',
                'Stakeholder representation'
            ],
            confidence=0.8
        )

    def _generic_resolution(
        self,
        detection: TradeOffDetection,
        risk_level: str
    ) -> TradeOffResolution:
        """Generic resolution for other trade-offs."""
        strategy = "Context-Aware Balancing"
        approach = f"Balance {detection.principle1.value} and {detection.principle2.value} based on context and risk level."

        return TradeOffResolution(
            detection=detection,
            resolution_strategy=strategy,
            balanced_approach=approach,
            implementation_steps=detection.recommendations,
            monitoring_metrics=[
                f'{detection.principle1.value}_score',
                f'{detection.principle2.value}_score',
                'overall_ethics_score'
            ],
            confidence=0.7
        )

    def generate_tradeoff_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive trade-off analysis report.

        Returns:
            Dictionary containing all detected trade-offs and resolutions
        """
        return {
            'total_tradeoffs': len(self.detected_tradeoffs),
            'high_tension_tradeoffs': [
                t for t in self.detected_tradeoffs
                if t.tension_level > self.HIGH_TENSION_THRESHOLD
            ],
            'all_tradeoffs': self.detected_tradeoffs,
            'resolutions': self.resolution_history,
            'summary': self._generate_summary()
        }

    def _generate_summary(self) -> str:
        """Generate textual summary of trade-off analysis."""
        if not self.detected_tradeoffs:
            return "No ethical trade-offs detected. All principles appear balanced."

        high_tension = sum(
            1 for t in self.detected_tradeoffs
            if t.tension_level > self.HIGH_TENSION_THRESHOLD
        )

        summary = f"Detected {len(self.detected_tradeoffs)} ethical trade-off(s), "
        summary += f"including {high_tension} high-tension conflict(s). "

        if high_tension > 0:
            summary += "Immediate attention recommended for high-tension trade-offs. "

        summary += "Review resolutions and implement recommended monitoring metrics."

        return summary


# Export
__all__ = [
    'TradeOffEngine',
    'EthicalPrinciple',
    'TradeOffType',
    'TradeOffDetection',
    'TradeOffResolution'
]
