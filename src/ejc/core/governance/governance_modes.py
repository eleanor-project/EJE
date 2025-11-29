"""
Governance Mode Layer - Phase 5B

Multi-framework governance support aligned with World Bank AI Governance Report (Section 6).

Supports 6 major global AI governance frameworks:
1. EU AI Act (Risk-based classification)
2. UN Global Governance (Human rights focus)
3. OECD Principles (5 principles + 5 recommendations)
4. NIST AI RMF (Risk management framework)
5. Korea AI Basic Act (Ethics & dignity)
6. Japan Society 5.0 (Human-centric AI)

Each mode configures:
- Thresholds for decisions
- Oversight levels
- Explainability depth
- Data requirements
- Compliance checks

References:
- World Bank Report Section 6.1: International Frameworks
- World Bank Report Section 6.2: National Regulations
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class GovernanceMode(Enum):
    """Supported AI governance frameworks."""
    EU_AI_ACT = "eu_ai_act"
    UN_GLOBAL = "un_global"
    OECD = "oecd"
    NIST_RMF = "nist_rmf"
    KOREA_BASIC = "korea_basic"
    JAPAN_SOCIETY5 = "japan_society5"
    DEFAULT = "default"


class RiskLevel(Enum):
    """Risk levels for AI systems (EU AI Act style)."""
    UNACCEPTABLE = "unacceptable"  # Prohibited
    HIGH = "high"                   # Strict requirements
    LIMITED = "limited"             # Transparency obligations
    MINIMAL = "minimal"             # No specific requirements


class OversightLevel(Enum):
    """Required oversight intensity."""
    NONE = "none"
    MINIMAL = "minimal"           # Periodic review
    MODERATE = "moderate"         # Regular monitoring
    HIGH = "high"                 # Continuous oversight
    HUMAN_IN_LOOP = "human_in_loop"  # Human decision required


@dataclass
class GovernanceModeConfig:
    """Configuration for a specific governance mode."""

    mode: GovernanceMode
    name: str
    description: str

    # Decision thresholds
    deny_threshold: float = 0.7      # Confidence needed to DENY
    review_threshold: float = 0.4    # Confidence needed to REVIEW
    allow_threshold: float = 0.3     # Minimum confidence to ALLOW

    # Oversight requirements
    oversight_level: OversightLevel = OversightLevel.MODERATE
    requires_human_review: bool = False
    audit_frequency: str = "monthly"

    # Explainability requirements
    explainability_required: bool = True
    explanation_depth: str = "standard"  # minimal, standard, comprehensive
    user_facing_explanations: bool = True

    # Data & Privacy requirements
    data_minimization_required: bool = True
    consent_required: bool = True
    pet_recommended: bool = False
    pet_required: bool = False

    # Compliance requirements
    risk_assessment_required: bool = True
    impact_assessment_required: bool = False
    third_party_audit_required: bool = False
    certification_required: bool = False

    # Framework-specific parameters
    specific_parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mode': self.mode.value,
            'name': self.name,
            'description': self.description,
            'thresholds': {
                'deny': self.deny_threshold,
                'review': self.review_threshold,
                'allow': self.allow_threshold
            },
            'oversight': {
                'level': self.oversight_level.value,
                'human_review_required': self.requires_human_review,
                'audit_frequency': self.audit_frequency
            },
            'explainability': {
                'required': self.explainability_required,
                'depth': self.explanation_depth,
                'user_facing': self.user_facing_explanations
            },
            'data_privacy': {
                'data_minimization': self.data_minimization_required,
                'consent_required': self.consent_required,
                'pet_recommended': self.pet_recommended,
                'pet_required': self.pet_required
            },
            'compliance': {
                'risk_assessment': self.risk_assessment_required,
                'impact_assessment': self.impact_assessment_required,
                'third_party_audit': self.third_party_audit_required,
                'certification': self.certification_required
            },
            'specific_parameters': self.specific_parameters
        }


class GovernanceModeLayer:
    """
    Governance Mode Layer implementing multi-framework compliance.

    Allows runtime switching between different governance frameworks
    to meet various regulatory requirements.
    """

    def __init__(self, default_mode: GovernanceMode = GovernanceMode.DEFAULT):
        """
        Initialize Governance Mode Layer.

        Args:
            default_mode: Default governance mode to use
        """
        self.current_mode = default_mode
        self.mode_configs = self._initialize_mode_configs()
        self.compliance_log: List[Dict[str, Any]] = []

    def _initialize_mode_configs(self) -> Dict[GovernanceMode, GovernanceModeConfig]:
        """Initialize configurations for all governance modes."""
        return {
            GovernanceMode.EU_AI_ACT: self._create_eu_ai_act_config(),
            GovernanceMode.UN_GLOBAL: self._create_un_global_config(),
            GovernanceMode.OECD: self._create_oecd_config(),
            GovernanceMode.NIST_RMF: self._create_nist_rmf_config(),
            GovernanceMode.KOREA_BASIC: self._create_korea_basic_config(),
            GovernanceMode.JAPAN_SOCIETY5: self._create_japan_society5_config(),
            GovernanceMode.DEFAULT: self._create_default_config()
        }

    def _create_eu_ai_act_config(self) -> GovernanceModeConfig:
        """
        Create EU AI Act mode configuration.

        Focus: Risk-based classification with 4 risk levels
        Reference: World Bank Report Section 6.2 (EU)
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.EU_AI_ACT,
            name="EU AI Act",
            description="Risk-based AI regulation with strict requirements for high-risk systems",
            deny_threshold=0.8,      # Stricter for high-risk systems
            review_threshold=0.5,
            allow_threshold=0.2,
            oversight_level=OversightLevel.HIGH,
            requires_human_review=True,  # Required for high-risk AI
            audit_frequency="quarterly",
            explainability_required=True,
            explanation_depth="comprehensive",  # Detailed explanations required
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=False,  # Recommended but not mandated
            risk_assessment_required=True,
            impact_assessment_required=True,  # Fundamental Rights Impact Assessment
            third_party_audit_required=True,  # Conformity assessment
            certification_required=True,      # CE marking
            specific_parameters={
                'risk_categories': ['unacceptable', 'high', 'limited', 'minimal'],
                'prohibited_uses': [
                    'social_scoring',
                    'real_time_biometric_identification',
                    'subliminal_manipulation',
                    'exploitation_of_vulnerabilities'
                ],
                'high_risk_areas': [
                    'critical_infrastructure',
                    'education',
                    'employment',
                    'law_enforcement',
                    'migration_asylum',
                    'justice',
                    'democratic_processes'
                ],
                'transparency_obligations': True,
                'human_oversight_mandatory': True,
                'post_market_monitoring': True
            }
        )

    def _create_un_global_config(self) -> GovernanceModeConfig:
        """
        Create UN Global Governance mode configuration.

        Focus: Human rights and sustainable development
        Reference: World Bank Report Section 6.1.1
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.UN_GLOBAL,
            name="UN Global AI Governance",
            description="Human rights-centered AI governance with focus on sustainable development",
            deny_threshold=0.75,
            review_threshold=0.45,
            allow_threshold=0.25,
            oversight_level=OversightLevel.HIGH,
            requires_human_review=True,
            audit_frequency="semi-annual",
            explainability_required=True,
            explanation_depth="comprehensive",
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=False,
            risk_assessment_required=True,
            impact_assessment_required=True,  # Human rights impact assessment
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={
                'core_principles': [
                    'human_rights_respect',
                    'sustainable_development',
                    'global_cooperation',
                    'inclusive_development',
                    'non_discrimination'
                ],
                'sdg_alignment': True,  # UN Sustainable Development Goals
                'vulnerable_groups_protection': True,
                'cross_border_cooperation': True,
                'capacity_building': True
            }
        )

    def _create_oecd_config(self) -> GovernanceModeConfig:
        """
        Create OECD Principles mode configuration.

        Focus: 5 core principles + 5 recommendations
        Reference: World Bank Report Section 6.1.3
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.OECD,
            name="OECD AI Principles",
            description="Values-based AI governance with focus on inclusive growth",
            deny_threshold=0.7,
            review_threshold=0.4,
            allow_threshold=0.3,
            oversight_level=OversightLevel.MODERATE,
            requires_human_review=False,
            audit_frequency="annual",
            explainability_required=True,
            explanation_depth="standard",
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=False,
            risk_assessment_required=True,
            impact_assessment_required=False,
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={
                'five_principles': [
                    'inclusive_growth_and_wellbeing',
                    'human_centered_values',
                    'transparency_and_explainability',
                    'robustness_security_safety',
                    'accountability'
                ],
                'five_recommendations': [
                    'invest_in_ai_rd',
                    'foster_digital_ecosystem',
                    'policy_environment_for_ai',
                    'build_human_capacity',
                    'international_cooperation'
                ],
                'multi_stakeholder_approach': True,
                'innovation_enabling': True
            }
        )

    def _create_nist_rmf_config(self) -> GovernanceModeConfig:
        """
        Create NIST AI Risk Management Framework mode configuration.

        Focus: Risk management framework with trustworthy AI characteristics
        Reference: World Bank Report Section 6.2 (US)
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.NIST_RMF,
            name="NIST AI RMF",
            description="Risk-based framework for trustworthy AI development and deployment",
            deny_threshold=0.75,
            review_threshold=0.45,
            allow_threshold=0.25,
            oversight_level=OversightLevel.MODERATE,
            requires_human_review=False,
            audit_frequency="quarterly",
            explainability_required=True,
            explanation_depth="comprehensive",
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=False,
            risk_assessment_required=True,
            impact_assessment_required=True,
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={
                'core_functions': ['govern', 'map', 'measure', 'manage'],
                'trustworthy_characteristics': [
                    'valid_and_reliable',
                    'safe',
                    'secure_and_resilient',
                    'accountable_and_transparent',
                    'explainable_and_interpretable',
                    'privacy_enhanced',
                    'fair_with_harmful_bias_managed'
                ],
                'risk_categories': ['low', 'medium', 'high'],
                'lifecycle_approach': True,
                'socio_technical_integration': True,
                'continuous_improvement': True
            }
        )

    def _create_korea_basic_config(self) -> GovernanceModeConfig:
        """
        Create Korea AI Basic Act mode configuration.

        Focus: AI ethics and human dignity
        Reference: World Bank Report Section 6.2 (Korea)
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.KOREA_BASIC,
            name="Korea AI Basic Act",
            description="Ethics-centered AI governance protecting human dignity and public interest",
            deny_threshold=0.75,
            review_threshold=0.4,
            allow_threshold=0.25,
            oversight_level=OversightLevel.HIGH,
            requires_human_review=True,
            audit_frequency="quarterly",
            explainability_required=True,
            explanation_depth="comprehensive",
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=True,  # Strong privacy focus (COVID-19 case study)
            risk_assessment_required=True,
            impact_assessment_required=True,
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={
                'core_values': [
                    'human_dignity',
                    'public_interest',
                    'fairness',
                    'transparency',
                    'safety'
                ],
                'ethical_principles': [
                    'respect_for_human_rights',
                    'diversity_and_inclusion',
                    'public_good',
                    'responsible_innovation'
                ],
                'privacy_emphasis': True,  # Informed by COVID-19 response
                'deidentification_required': True,
                'strict_data_access_controls': True,
                'ethics_review_board': True
            }
        )

    def _create_japan_society5_config(self) -> GovernanceModeConfig:
        """
        Create Japan Society 5.0 mode configuration.

        Focus: Human-centric society with technology integration
        Reference: World Bank Report Section 6.2 (Japan)
        """
        return GovernanceModeConfig(
            mode=GovernanceMode.JAPAN_SOCIETY5,
            name="Japan Society 5.0",
            description="Human-centric AI for solving social challenges and improving quality of life",
            deny_threshold=0.7,
            review_threshold=0.4,
            allow_threshold=0.3,
            oversight_level=OversightLevel.MODERATE,
            requires_human_review=False,
            audit_frequency="semi-annual",
            explainability_required=True,
            explanation_depth="standard",
            user_facing_explanations=True,
            data_minimization_required=True,
            consent_required=True,
            pet_recommended=True,
            pet_required=False,
            risk_assessment_required=True,
            impact_assessment_required=False,
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={
                'core_concepts': [
                    'human_centric',
                    'cyber_physical_integration',
                    'social_challenge_solving',
                    'quality_of_life_improvement',
                    'sustainable_development'
                ],
                'focus_areas': [
                    'aging_society',
                    'disaster_prevention',
                    'environmental_challenges',
                    'infrastructure_management',
                    'healthcare'
                ],
                'stakeholder_collaboration': True,
                'innovation_ecosystem': True,
                'global_contribution': True
            }
        )

    def _create_default_config(self) -> GovernanceModeConfig:
        """Create default/baseline governance configuration."""
        return GovernanceModeConfig(
            mode=GovernanceMode.DEFAULT,
            name="Default Governance",
            description="Baseline AI governance with general best practices",
            deny_threshold=0.7,
            review_threshold=0.4,
            allow_threshold=0.3,
            oversight_level=OversightLevel.MINIMAL,
            requires_human_review=False,
            audit_frequency="annual",
            explainability_required=False,
            explanation_depth="minimal",
            user_facing_explanations=False,
            data_minimization_required=False,
            consent_required=False,
            pet_recommended=False,
            pet_required=False,
            risk_assessment_required=False,
            impact_assessment_required=False,
            third_party_audit_required=False,
            certification_required=False,
            specific_parameters={}
        )

    def set_mode(self, mode: GovernanceMode) -> None:
        """
        Switch to a different governance mode.

        Args:
            mode: Governance mode to activate
        """
        if mode not in self.mode_configs:
            raise ValueError(f"Unknown governance mode: {mode}")

        self.current_mode = mode
        self.compliance_log.append({
            'action': 'mode_change',
            'new_mode': mode.value,
            'timestamp': self._get_timestamp()
        })

    def get_current_config(self) -> GovernanceModeConfig:
        """
        Get current governance mode configuration.

        Returns:
            Current mode configuration
        """
        return self.mode_configs[self.current_mode]

    def get_mode_config(self, mode: GovernanceMode) -> GovernanceModeConfig:
        """
        Get configuration for a specific mode.

        Args:
            mode: Mode to get configuration for

        Returns:
            Mode configuration
        """
        return self.mode_configs.get(mode)

    def check_compliance(
        self,
        decision: Dict[str, Any],
        mode: Optional[GovernanceMode] = None
    ) -> Dict[str, Any]:
        """
        Check if a decision complies with governance mode requirements.

        Args:
            decision: Decision dictionary with verdict, confidence, etc.
            mode: Governance mode to check against (uses current if not specified)

        Returns:
            Compliance report with status and gaps
        """
        check_mode = mode or self.current_mode
        config = self.mode_configs[check_mode]

        compliance_report = {
            'mode': check_mode.value,
            'compliant': True,
            'gaps': [],
            'warnings': [],
            'requirements_met': [],
            'requirements_not_met': []
        }

        # Check thresholds
        verdict = decision.get('verdict', 'REVIEW')
        confidence = decision.get('confidence', 0.0)

        if verdict == 'DENY' and confidence < config.deny_threshold:
            compliance_report['gaps'].append(
                f"DENY verdict confidence ({confidence:.2f}) below threshold ({config.deny_threshold})"
            )
            compliance_report['compliant'] = False

        # Check explainability
        if config.explainability_required:
            if 'justification' not in decision or not decision['justification']:
                compliance_report['gaps'].append("Explainability required but not provided")
                compliance_report['compliant'] = False
            else:
                compliance_report['requirements_met'].append("Explainability provided")

        # Check human review
        if config.requires_human_review:
            if not decision.get('human_reviewed', False):
                compliance_report['warnings'].append("Human review recommended but not performed")
            else:
                compliance_report['requirements_met'].append("Human review completed")

        # Check risk assessment
        if config.risk_assessment_required:
            if 'risk_assessment' not in decision:
                compliance_report['gaps'].append("Risk assessment required but not present")
                compliance_report['compliant'] = False
            else:
                compliance_report['requirements_met'].append("Risk assessment completed")

        # Check impact assessment
        if config.impact_assessment_required:
            if 'impact_assessment' not in decision:
                compliance_report['gaps'].append("Impact assessment required but not present")
                compliance_report['compliant'] = False
            else:
                compliance_report['requirements_met'].append("Impact assessment completed")

        # Log compliance check
        self.compliance_log.append({
            'action': 'compliance_check',
            'mode': check_mode.value,
            'compliant': compliance_report['compliant'],
            'timestamp': self._get_timestamp()
        })

        return compliance_report

    def get_applicable_modes(
        self,
        jurisdiction: Optional[str] = None,
        sector: Optional[str] = None
    ) -> List[GovernanceMode]:
        """
        Get applicable governance modes for jurisdiction/sector.

        Args:
            jurisdiction: Jurisdiction code (e.g., 'EU', 'US', 'KR', 'JP')
            sector: Sector (e.g., 'healthcare', 'finance', 'education')

        Returns:
            List of applicable governance modes
        """
        applicable = []

        # Jurisdiction-based recommendations
        jurisdiction_map = {
            'EU': [GovernanceMode.EU_AI_ACT, GovernanceMode.OECD],
            'US': [GovernanceMode.NIST_RMF, GovernanceMode.OECD],
            'KR': [GovernanceMode.KOREA_BASIC, GovernanceMode.OECD],
            'JP': [GovernanceMode.JAPAN_SOCIETY5, GovernanceMode.OECD],
            'GLOBAL': [GovernanceMode.UN_GLOBAL, GovernanceMode.OECD]
        }

        if jurisdiction and jurisdiction.upper() in jurisdiction_map:
            applicable.extend(jurisdiction_map[jurisdiction.upper()])
        else:
            # Default to OECD and UN for unknown jurisdictions
            applicable.extend([GovernanceMode.OECD, GovernanceMode.UN_GLOBAL])

        # Sector-specific additions
        if sector:
            sector_lower = sector.lower()
            if sector_lower in ['healthcare', 'finance', 'law_enforcement']:
                # High-risk sectors: recommend stricter frameworks
                if GovernanceMode.EU_AI_ACT not in applicable:
                    applicable.append(GovernanceMode.EU_AI_ACT)

        return list(set(applicable))  # Remove duplicates

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def get_compliance_log(self) -> List[Dict[str, Any]]:
        """
        Get compliance operation log.

        Returns:
            List of compliance operations
        """
        return self.compliance_log.copy()


# Export
__all__ = [
    'GovernanceModeLayer',
    'GovernanceModeConfig',
    'GovernanceMode',
    'RiskLevel',
    'OversightLevel'
]
