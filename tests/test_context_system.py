"""
Tests for advanced context system.

Tests jurisdiction awareness, cultural adaptation, and domain specialization.
"""

import pytest
from ejc.core.context import (
    ContextManager,
    JurisdictionRegistry,
    JurisdictionContext,
    PrivacyRegime,
    CulturalNormAdapter,
    CulturalContext,
    DomainSpecialization,
    DomainContext,
    EthicalPrinciple,
)


@pytest.fixture
def context_manager():
    """Create context manager instance."""
    return ContextManager()


@pytest.fixture
def jurisdiction_registry():
    """Create jurisdiction registry."""
    return JurisdictionRegistry()


@pytest.fixture
def cultural_adapter():
    """Create cultural adapter."""
    return CulturalNormAdapter()


@pytest.fixture
def domain_specialization():
    """Create domain specialization."""
    return DomainSpecialization()


class TestJurisdictionContext:
    """Test jurisdiction-aware reasoning."""

    def test_gdpr_compliance_requirements(self, jurisdiction_registry):
        """Test GDPR compliance requirements."""
        eu_jurisdiction = jurisdiction_registry.get("EU")
        assert eu_jurisdiction is not None
        assert eu_jurisdiction.privacy_regime == PrivacyRegime.GDPR

        requirements = eu_jurisdiction.get_compliance_requirements("data_collection")
        assert len(requirements) > 0
        assert any("consent" in req.lower() for req in requirements)

    def test_hipaa_compliance_requirements(self, jurisdiction_registry):
        """Test HIPAA healthcare requirements."""
        hipaa_jurisdiction = jurisdiction_registry.get("US-HIPAA")
        assert hipaa_jurisdiction is not None
        assert hipaa_jurisdiction.privacy_regime == PrivacyRegime.HIPAA

        # HIPAA should prohibit unauthorized PHI disclosure
        assert "unauthorized_phi_disclosure" in hipaa_jurisdiction.prohibited_actions

    def test_applicable_jurisdictions(self, jurisdiction_registry):
        """Test determining applicable jurisdictions."""
        # User in EU, data in US
        applicable = jurisdiction_registry.get_applicable_jurisdictions(
            user_location="EU",
            data_location="US-CA"
        )

        assert len(applicable) >= 1
        jurisdiction_ids = [j.jurisdiction_id for j in applicable]
        assert "EU" in jurisdiction_ids

    def test_strictest_requirements(self, jurisdiction_registry):
        """Test combining requirements from multiple jurisdictions."""
        eu = jurisdiction_registry.get("EU")
        ca = jurisdiction_registry.get("US-CA")

        requirements = jurisdiction_registry.get_strictest_requirements(
            [eu, ca],
            "data_collection"
        )

        # Should include requirements from both
        assert len(requirements) > 0

    def test_compliance_check(self, jurisdiction_registry):
        """Test compliance checking."""
        eu = jurisdiction_registry.get("EU")

        # Compliant action
        action = {
            "type": "data_collection",
            "compliance_measures": [
                "Obtain explicit user consent",
                "Provide purpose limitation and data minimization",
            ]
        }

        result = jurisdiction_registry.check_compliance(action, [eu])
        assert result["compliant"] is True

        # Non-compliant action
        bad_action = {
            "type": "data_collection",
            "compliance_measures": []
        }

        result = jurisdiction_registry.check_compliance(bad_action, [eu])
        assert len(result["warnings"]) > 0


class TestCulturalContext:
    """Test cultural norm adaptation."""

    def test_cultural_dimensions(self, cultural_adapter):
        """Test cultural dimensions are properly set."""
        us_culture = cultural_adapter.get("US")
        assert us_culture is not None
        assert us_culture.individualism > 70  # US is individualistic

        cn_culture = cultural_adapter.get("CN")
        assert cn_culture is not None
        assert cn_culture.individualism < 30  # China is collectivist

    def test_communication_style(self, cultural_adapter):
        """Test communication style recommendations."""
        us_culture = cultural_adapter.get("US")
        assert us_culture.get_communication_style() == "direct, fact-focused"

        cn_culture = cultural_adapter.get("CN")
        assert "implicit" in cn_culture.get_communication_style()

    def test_sensitive_topics(self, cultural_adapter):
        """Test sensitive topic detection."""
        mena_culture = cultural_adapter.get("MENA")
        assert mena_culture is not None

        # Religious criticism is taboo
        assert mena_culture.is_sensitive_topic("religious_criticism")

    def test_message_adaptation(self, cultural_adapter):
        """Test message adaptation for culture."""
        cn_culture = cultural_adapter.get("CN")

        adaptation = cultural_adapter.adapt_message(
            "We should do this immediately",
            cn_culture
        )

        assert adaptation["adapted"] is True
        assert len(adaptation["recommendations"]) > 0

    def test_cultural_sensitivity_check(self, cultural_adapter):
        """Test content sensitivity checking."""
        mena_culture = cultural_adapter.get("MENA")

        # Content with taboo topic
        result = cultural_adapter.check_cultural_sensitivity(
            "This contains religious criticism",
            [mena_culture]
        )

        assert result["culturally_appropriate"] is False
        assert len(result["issues"]) > 0

        # Appropriate content
        result = cultural_adapter.check_cultural_sensitivity(
            "This is general content about technology",
            [mena_culture]
        )

        assert result["culturally_appropriate"] is True

    def test_value_alignment(self, cultural_adapter):
        """Test value alignment checking."""
        us_culture = cultural_adapter.get("US")

        # Aligned values
        result = cultural_adapter.get_value_alignment(
            ["freedom", "individual rights"],
            us_culture
        )

        assert result["alignment_score"] > 0.5
        assert len(result["aligned_values"]) > 0


class TestDomainContext:
    """Test domain-specific ethics."""

    def test_domain_principle_weights(self, domain_specialization):
        """Test domain principle prioritization."""
        healthcare = domain_specialization.get("healthcare")
        assert healthcare is not None

        principles = healthcare.get_prioritized_principles()
        # Non-maleficence should be highest in healthcare
        assert principles[0][0] == EthicalPrinciple.NON_MALEFICENCE

        finance = domain_specialization.get("finance")
        # Fidelity (fiduciary duty) should be highest in finance
        finance_principles = finance.get_prioritized_principles()
        assert finance_principles[0][0] == EthicalPrinciple.FIDELITY

    def test_prohibited_actions(self, domain_specialization):
        """Test domain prohibited actions."""
        healthcare = domain_specialization.get("healthcare")

        # Diagnosis without oversight should be prohibited
        assert "diagnosis_without_oversight" in healthcare.prohibited_actions

        finance = domain_specialization.get("finance")
        # Insider trading should be prohibited
        assert "insider_trading" in finance.prohibited_actions

    def test_high_risk_categories(self, domain_specialization):
        """Test high-risk category identification."""
        healthcare = domain_specialization.get("healthcare")

        assert healthcare.requires_special_handling("diagnosis")
        assert healthcare.requires_special_handling("treatment")
        assert not healthcare.requires_special_handling("general_info")

    def test_safeguards_for_action(self, domain_specialization):
        """Test safeguard requirements."""
        healthcare = domain_specialization.get("healthcare")

        safeguards = healthcare.get_safeguards_for("diagnosis")

        # Should include base safeguards plus high-risk extras
        assert len(safeguards) > 0
        assert any("monitoring" in s.lower() or "oversight" in s.lower() for s in safeguards)

    def test_domain_ethics_application(self, domain_specialization):
        """Test applying domain ethics to an action."""
        healthcare = domain_specialization.get("healthcare")

        # Compliant action
        action = {
            "type": "patient_care",
            "category": "general_info",
            "safeguards": ["Clinical validation required"],
            "checks_performed": healthcare.mandatory_checks,
            "principle_scores": {
                "non_maleficence": 0.9,
                "beneficence": 0.85,
            }
        }

        result = domain_specialization.apply_domain_ethics(action, healthcare)

        assert result["domain"] == "Healthcare"
        assert len(result["violations"]) == 0

        # Prohibited action
        bad_action = {
            "type": "diagnosis_without_oversight",
            "category": "diagnosis",
        }

        result = domain_specialization.apply_domain_ethics(bad_action, healthcare)
        assert len(result["violations"]) > 0


class TestContextManager:
    """Test integrated context management."""

    def test_contextualize_request(self, context_manager):
        """Test request contextualization."""
        action = {
            "type": "data_collection",
            "description": "Collect user health data"
        }

        contextualized = context_manager.contextualize_request(
            action,
            user_location="EU",
            culture_id="EU",
            domain_id="healthcare"
        )

        assert len(contextualized.jurisdictions) > 0
        assert len(contextualized.cultures) > 0
        assert contextualized.domain.domain_id == "healthcare"

    def test_analyze_with_context(self, context_manager):
        """Test comprehensive context analysis."""
        action = {
            "type": "data_collection",
            "category": "personal_data",
            "content": "Collecting health information",
            "compliance_measures": [
                "Obtain explicit user consent",
                "Provide purpose limitation and data minimization",
            ],
            "safeguards": [
                "Clinical validation required",
                "Licensed professional review",
            ],
            "checks_performed": [
                "Patient safety verification",
                "HIPAA compliance check",
            ],
            "principle_scores": {
                "non_maleficence": 0.9,
                "privacy": 0.85,
            }
        }

        contextualized = context_manager.contextualize_request(
            action,
            user_location="EU",
            domain_id="healthcare"
        )

        result = context_manager.analyze_with_context(contextualized)

        assert "overall_compliant" in result
        assert "risk_level" in result
        assert "jurisdiction_analysis" in result
        assert "cultural_analysis" in result
        assert "domain_analysis" in result
        assert "summary" in result

    def test_get_context_requirements(self, context_manager):
        """Test getting contextual requirements."""
        requirements = context_manager.get_context_requirements(
            action_type="data_collection",
            jurisdictions=["EU", "US-CA"],
            cultures=["US"],
            domain="healthcare"
        )

        assert "jurisdiction_requirements" in requirements
        assert "cultural_considerations" in requirements
        assert "domain_safeguards" in requirements
        assert "combined_requirements" in requirements

        # Should have requirements from all sources
        assert len(requirements["combined_requirements"]) > 0

    def test_risk_level_calculation(self, context_manager):
        """Test risk level calculation."""
        # High-risk action
        high_risk_action = {
            "type": "diagnosis",
            "category": "diagnosis",
        }

        contextualized = context_manager.contextualize_request(
            high_risk_action,
            domain_id="healthcare"
        )

        result = context_manager.analyze_with_context(contextualized)
        # Should be at least medium risk due to missing safeguards
        assert result["risk_level"] in ["medium", "high", "critical"]

        # Low-risk action
        low_risk_action = {
            "type": "general_info",
            "category": "information",
            "compliance_measures": ["Clear user notification"],
            "safeguards": ["Data protection"],
            "checks_performed": ["Basic safety check"],
        }

        contextualized = context_manager.contextualize_request(
            low_risk_action,
            domain_id="general"
        )

        result = context_manager.analyze_with_context(contextualized)
        # Should be low risk
        assert result["risk_level"] in ["low", "medium"]


class TestIntegrationContextSystem:
    """Integration tests for context system."""

    def test_healthcare_in_eu_workflow(self, context_manager):
        """Test complete workflow for healthcare in EU."""
        # Healthcare action in EU with German culture
        action = {
            "type": "patient_assessment",
            "category": "diagnosis",
            "description": "AI-assisted diagnosis",
            "compliance_measures": [
                "Obtain explicit user consent",
                "Provide purpose limitation and data minimization",
            ],
            "safeguards": [
                "Clinical validation required",
                "Licensed professional review",
                "Patient privacy protection",
            ],
            "checks_performed": [
                "Patient safety verification",
                "Medical professional oversight",
            ],
            "principle_scores": {
                "non_maleficence": 0.95,
                "beneficence": 0.9,
                "privacy": 0.85,
            }
        }

        # Contextualize
        contextualized = context_manager.contextualize_request(
            action,
            user_location="EU",
            data_location="EU",
            culture_id="NORDIC",  # Using Nordic as proxy for EU
            domain_id="healthcare"
        )

        # Analyze
        result = context_manager.analyze_with_context(contextualized)

        # Verify comprehensive analysis
        assert result is not None
        assert "jurisdiction_analysis" in result
        assert "cultural_analysis" in result
        assert "domain_analysis" in result

        # Check GDPR compliance
        assert "EU" in result["jurisdiction_analysis"]["applicable_jurisdictions"]

        # Domain should be healthcare
        assert result["domain_analysis"]["domain"] == "Healthcare"

    def test_finance_in_us_workflow(self, context_manager):
        """Test financial services in US context."""
        action = {
            "type": "investment_advice",
            "category": "investment_advice",
            "description": "Algorithmic investment recommendation",
            "compliance_measures": ["Risk disclosure validation"],
            "safeguards": [
                "Transaction monitoring",
                "Risk assessment",
            ],
            "checks_performed": [
                "Fiduciary duty verification",
                "Regulatory compliance check",
            ],
            "principle_scores": {
                "fidelity": 0.95,
                "transparency": 0.9,
            }
        }

        contextualized = context_manager.contextualize_request(
            action,
            user_location="US-CA",
            culture_id="US",
            domain_id="finance"
        )

        result = context_manager.analyze_with_context(contextualized)

        # Should identify as high-risk financial action
        assert result["domain_analysis"]["is_high_risk"] is True
        assert result["domain_analysis"]["domain"] == "Financial Services"

    def test_cross_cultural_education(self, context_manager):
        """Test education across different cultures."""
        action = {
            "type": "student_assessment",
            "category": "student_assessment",
            "description": "AI grading system",
            "compliance_measures": [],
            "safeguards": [
                "Bias monitoring in assessments",
            ],
            "checks_performed": [
                "Age-appropriateness verification",
                "Educational value assessment",
            ],
        }

        # Test in individualistic culture (US)
        us_contextualized = context_manager.contextualize_request(
            action,
            culture_id="US",
            domain_id="education"
        )

        us_result = context_manager.analyze_with_context(us_contextualized)

        # Test in collectivist culture (China)
        cn_contextualized = context_manager.contextualize_request(
            action,
            culture_id="CN",
            domain_id="education"
        )

        cn_result = context_manager.analyze_with_context(cn_contextualized)

        # Both should require education domain safeguards
        assert us_result["domain_analysis"]["domain"] == "Education"
        assert cn_result["domain_analysis"]["domain"] == "Education"

        # Cultural considerations might differ
        # (In real implementation, would check specific differences)
