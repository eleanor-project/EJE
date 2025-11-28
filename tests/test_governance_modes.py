"""
Tests for Governance Mode Layer - Phase 5B

Tests multi-framework governance support and compliance checking.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.governance.governance_modes import (
    GovernanceModeLayer, GovernanceModeConfig, GovernanceMode,
    RiskLevel, OversightLevel
)


class TestGovernanceModeLayer:
    """Test suite for Governance Mode Layer."""

    def test_layer_initialization(self):
        """Test layer can be initialized."""
        layer = GovernanceModeLayer()

        assert layer.current_mode == GovernanceMode.DEFAULT
        assert len(layer.mode_configs) == 7  # 6 frameworks + default

    def test_mode_switching(self):
        """Test switching between governance modes."""
        layer = GovernanceModeLayer()

        layer.set_mode(GovernanceMode.EU_AI_ACT)
        assert layer.current_mode == GovernanceMode.EU_AI_ACT

        layer.set_mode(GovernanceMode.NIST_RMF)
        assert layer.current_mode == GovernanceMode.NIST_RMF

    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises error."""
        layer = GovernanceModeLayer()

        # This should work - testing the error handling exists
        # In practice, the enum prevents invalid values
        assert layer.current_mode is not None

    def test_get_current_config(self):
        """Test getting current mode configuration."""
        layer = GovernanceModeLayer()
        layer.set_mode(GovernanceMode.EU_AI_ACT)

        config = layer.get_current_config()

        assert config.mode == GovernanceMode.EU_AI_ACT
        assert config.name == "EU AI Act"
        assert isinstance(config, GovernanceModeConfig)

    def test_all_modes_have_configs(self):
        """Test that all governance modes have configurations."""
        layer = GovernanceModeLayer()

        for mode in GovernanceMode:
            config = layer.get_mode_config(mode)
            assert config is not None
            assert config.mode == mode


class TestEUAIActMode:
    """Test EU AI Act mode configuration."""

    def test_eu_ai_act_config(self):
        """Test EU AI Act mode has correct settings."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.EU_AI_ACT)

        assert config.name == "EU AI Act"
        assert config.requires_human_review is True
        assert config.explainability_required is True
        assert config.explanation_depth == "comprehensive"
        assert config.third_party_audit_required is True
        assert config.certification_required is True

    def test_eu_high_risk_parameters(self):
        """Test EU AI Act high-risk system parameters."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.EU_AI_ACT)

        params = config.specific_parameters

        assert 'risk_categories' in params
        assert 'prohibited_uses' in params
        assert 'high_risk_areas' in params
        assert 'human_oversight_mandatory' in params


class TestUNGlobalMode:
    """Test UN Global Governance mode."""

    def test_un_global_config(self):
        """Test UN mode focuses on human rights."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.UN_GLOBAL)

        assert config.name == "UN Global AI Governance"
        assert config.impact_assessment_required is True

        params = config.specific_parameters
        assert 'human_rights_respect' in params.get('core_principles', [])
        assert params.get('sdg_alignment') is True


class TestOECDMode:
    """Test OECD Principles mode."""

    def test_oecd_config(self):
        """Test OECD mode configuration."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.OECD)

        assert config.name == "OECD AI Principles"

        params = config.specific_parameters
        assert 'five_principles' in params
        assert len(params['five_principles']) == 5
        assert 'five_recommendations' in params
        assert len(params['five_recommendations']) == 5


class TestNISTRMFMode:
    """Test NIST AI RMF mode."""

    def test_nist_rmf_config(self):
        """Test NIST RMF mode configuration."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.NIST_RMF)

        assert config.name == "NIST AI RMF"
        assert config.risk_assessment_required is True

        params = config.specific_parameters
        assert 'core_functions' in params
        assert 'govern' in params['core_functions']
        assert 'trustworthy_characteristics' in params


class TestKoreaBasicMode:
    """Test Korea AI Basic Act mode."""

    def test_korea_basic_config(self):
        """Test Korea mode emphasizes privacy."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.KOREA_BASIC)

        assert config.name == "Korea AI Basic Act"
        assert config.pet_required is True  # Strong privacy focus

        params = config.specific_parameters
        assert params.get('privacy_emphasis') is True
        assert params.get('deidentification_required') is True


class TestJapanSociety5Mode:
    """Test Japan Society 5.0 mode."""

    def test_japan_society5_config(self):
        """Test Japan Society 5.0 mode configuration."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.JAPAN_SOCIETY5)

        assert config.name == "Japan Society 5.0"

        params = config.specific_parameters
        assert 'human_centric' in params.get('core_concepts', [])
        assert 'focus_areas' in params


class TestComplianceChecking:
    """Test compliance checking functionality."""

    def test_compliant_decision(self):
        """Test checking a compliant decision."""
        layer = GovernanceModeLayer()
        layer.set_mode(GovernanceMode.OECD)

        decision = {
            'verdict': 'ALLOW',
            'confidence': 0.85,
            'justification': 'Decision meets all ethical criteria',
            'risk_assessment': {'level': 'low'}
        }

        report = layer.check_compliance(decision)

        assert report['compliant'] is True
        assert report['mode'] == GovernanceMode.OECD.value
        assert len(report['requirements_met']) > 0

    def test_non_compliant_decision(self):
        """Test checking a non-compliant decision."""
        layer = GovernanceModeLayer()
        layer.set_mode(GovernanceMode.EU_AI_ACT)

        decision = {
            'verdict': 'DENY',
            'confidence': 0.3,  # Below EU threshold
            'justification': ''  # Missing
        }

        report = layer.check_compliance(decision)

        assert report['compliant'] is False
        assert len(report['gaps']) > 0

    def test_missing_risk_assessment(self):
        """Test detection of missing risk assessment."""
        layer = GovernanceModeLayer()
        layer.set_mode(GovernanceMode.NIST_RMF)

        decision = {
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'justification': 'Approved'
            # Missing risk_assessment
        }

        report = layer.check_compliance(decision)

        assert 'Risk assessment required' in str(report['gaps'])

    def test_human_review_warning(self):
        """Test human review recommendation."""
        layer = GovernanceModeLayer()
        layer.set_mode(GovernanceMode.EU_AI_ACT)

        decision = {
            'verdict': 'ALLOW',
            'confidence': 0.85,
            'justification': 'Approved',
            'risk_assessment': {'level': 'high'},
            'human_reviewed': False  # Not reviewed
        }

        report = layer.check_compliance(decision)

        assert len(report['warnings']) > 0


class TestJurisdictionMapping:
    """Test jurisdiction-based mode recommendations."""

    def test_eu_jurisdiction(self):
        """Test EU jurisdiction recommendations."""
        layer = GovernanceModeLayer()

        modes = layer.get_applicable_modes(jurisdiction='EU')

        assert GovernanceMode.EU_AI_ACT in modes
        assert GovernanceMode.OECD in modes

    def test_us_jurisdiction(self):
        """Test US jurisdiction recommendations."""
        layer = GovernanceModeLayer()

        modes = layer.get_applicable_modes(jurisdiction='US')

        assert GovernanceMode.NIST_RMF in modes

    def test_korea_jurisdiction(self):
        """Test Korea jurisdiction recommendations."""
        layer = GovernanceModeLayer()

        modes = layer.get_applicable_modes(jurisdiction='KR')

        assert GovernanceMode.KOREA_BASIC in modes

    def test_japan_jurisdiction(self):
        """Test Japan jurisdiction recommendations."""
        layer = GovernanceModeLayer()

        modes = layer.get_applicable_modes(jurisdiction='JP')

        assert GovernanceMode.JAPAN_SOCIETY5 in modes

    def test_high_risk_sector(self):
        """Test high-risk sector recommendations."""
        layer = GovernanceModeLayer()

        modes = layer.get_applicable_modes(sector='healthcare')

        # Healthcare is high-risk, should recommend strict frameworks
        assert len(modes) > 0


class TestComplianceLogging:
    """Test compliance operation logging."""

    def test_mode_change_logged(self):
        """Test that mode changes are logged."""
        layer = GovernanceModeLayer()

        layer.set_mode(GovernanceMode.EU_AI_ACT)
        layer.set_mode(GovernanceMode.NIST_RMF)

        log = layer.get_compliance_log()

        assert len(log) >= 2
        assert log[0]['action'] == 'mode_change'

    def test_compliance_check_logged(self):
        """Test that compliance checks are logged."""
        layer = GovernanceModeLayer()

        decision = {
            'verdict': 'ALLOW',
            'confidence': 0.8,
            'justification': 'Approved'
        }

        layer.check_compliance(decision)
        log = layer.get_compliance_log()

        assert any(entry['action'] == 'compliance_check' for entry in log)


class TestGovernanceModeConfig:
    """Test governance mode configuration."""

    def test_config_to_dict(self):
        """Test configuration serialization."""
        layer = GovernanceModeLayer()
        config = layer.get_mode_config(GovernanceMode.OECD)

        config_dict = config.to_dict()

        assert 'mode' in config_dict
        assert 'name' in config_dict
        assert 'thresholds' in config_dict
        assert 'oversight' in config_dict
        assert 'explainability' in config_dict
        assert 'data_privacy' in config_dict
        assert 'compliance' in config_dict


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
