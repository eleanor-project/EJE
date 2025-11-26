"""
Governance Compliance Test Suite for EJE

Tests constitutional compliance, rights hierarchy enforcement, and
governance rule application according to ELEANOR specifications.

This suite ensures:
1. Critical rights (dignity, autonomy, non-discrimination) are NEVER violated
2. Safety violations trigger escalation
3. Rights hierarchy is properly enforced (lexicographic ordering)
4. Precedent consistency is maintained
5. Uncertainty triggers appropriate escalation
"""

import pytest
from typing import Dict, Any, List

from ejc.core.governance.rules import (
    apply_governance_rules,
    RightsViolation,
    _violates_right,
    _critic_uncertainty_high,
    _precedent_conflicts
)
from ejc.core.error_handling import GovernanceException


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def rights_config():
    """Standard rights hierarchy configuration."""
    return {
        "dignity": {
            "required": True,
            "severity": "critical"
        },
        "autonomy": {
            "required": True,
            "severity": "critical"
        },
        "non_discrimination": {
            "required": True,
            "severity": "critical"
        },
        "safety": {
            "required": True,
            "severity": "high"
        },
        "fairness": {
            "required": False,
            "severity": "moderate"
        },
        "transparency": {
            "required": False,
            "severity": "advisory"
        },
        "proportionality": {
            "required": False,
            "severity": "advisory"
        }
    }


@pytest.fixture
def base_aggregation():
    """Base aggregation result."""
    return {
        "verdict": "ALLOW",
        "confidence": 0.85,
        "justification": "Base decision"
    }


# =============================================================================
# Constitutional Compliance Tests (Critical Rights)
# =============================================================================

class TestConstitutionalCompliance:
    """Test that critical constitutional rights are enforced."""

    def test_dignity_violation_blocks_decision(self, base_aggregation, rights_config):
        """Dignity violations must block any decision."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "dignity",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.95,
                "justification": "This action degrades human dignity"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        with pytest.raises(RightsViolation) as exc_info:
            apply_governance_rules(base_aggregation, critic_reports, config)

        assert "dignity" in str(exc_info.value).lower()

    def test_autonomy_violation_blocks_decision(self, base_aggregation, rights_config):
        """Autonomy violations must block any decision."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "autonomy",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.92,
                "justification": "Removes user choice without consent"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        with pytest.raises(RightsViolation) as exc_info:
            apply_governance_rules(base_aggregation, critic_reports, config)

        assert "autonomy" in str(exc_info.value).lower()

    def test_non_discrimination_violation_blocks_decision(self, base_aggregation, rights_config):
        """Non-discrimination violations must block any decision."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "non_discrimination",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.98,
                "justification": "Discriminates against protected group"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        with pytest.raises(RightsViolation) as exc_info:
            apply_governance_rules(base_aggregation, critic_reports, config)

        assert "non_discrimination" in str(exc_info.value).lower()

    def test_no_critical_violations_allows_decision(self, base_aggregation, rights_config):
        """Decisions without critical violations should proceed."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "transparency",
                "violation": True,  # Advisory only, should not block
                "verdict": "REVIEW",
                "confidence": 0.7,
                "justification": "Could be more transparent"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result is not None
        assert "verdict" in result

    def test_multiple_critical_violations_blocks(self, base_aggregation, rights_config):
        """Multiple critical violations should still block (first one wins)."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "dignity",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.95
            },
            {
                "critic": "rights",
                "right": "autonomy",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.90
            }
        ]

        config = {"rights_hierarchy": rights_config}

        with pytest.raises(RightsViolation):
            apply_governance_rules(base_aggregation, critic_reports, config)


# =============================================================================
# Rights Hierarchy Enforcement Tests
# =============================================================================

class TestRightsHierarchy:
    """Test lexicographic rights hierarchy enforcement."""

    def test_safety_violation_triggers_escalation(self, base_aggregation, rights_config):
        """Safety violations should trigger escalation."""
        critic_reports = [
            {
                "critic": "safety",
                "right": "safety",
                "violation": True,
                "verdict": "REVIEW",
                "confidence": 0.88,
                "justification": "Potential harm detected"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result["escalate"] is True
        assert "safety" in result["safeguards_triggered"]

    def test_fairness_violation_adds_penalty(self, base_aggregation, rights_config):
        """Fairness violations should add penalty but not escalate."""
        critic_reports = [
            {
                "critic": "fairness",
                "right": "fairness",
                "violation": True,
                "verdict": "REVIEW",
                "confidence": 0.75,
                "justification": "Unequal treatment detected"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert "fairness" in result["safeguards_triggered"]
        assert result.get("fairness_penalty") is True
        # Should not escalate for fairness alone
        assert result.get("escalate") is False

    def test_advisory_rights_logged_not_blocking(self, base_aggregation, rights_config):
        """Advisory rights violations should be logged but not block."""
        critic_reports = [
            {
                "critic": "transparency",
                "right": "transparency",
                "violation": True,
                "verdict": "REVIEW",
                "confidence": 0.70,
                "justification": "Lacks transparency"
            },
            {
                "critic": "proportionality",
                "right": "proportionality",
                "violation": True,
                "verdict": "REVIEW",
                "confidence": 0.65,
                "justification": "Overly restrictive"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert "transparency" in result["safeguards_triggered"]
        assert "proportionality" in result["safeguards_triggered"]
        assert result.get("escalate") is False  # Advisory doesn't escalate

    def test_hierarchy_ordering_critical_over_safety(self, base_aggregation, rights_config):
        """Critical rights violations should block before safety checks."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "dignity",
                "violation": True,
                "verdict": "DENY",
                "confidence": 0.95
            },
            {
                "critic": "safety",
                "right": "safety",
                "violation": True,
                "verdict": "REVIEW",
                "confidence": 0.88
            }
        ]

        config = {"rights_hierarchy": rights_config}

        # Should raise RightsViolation, not proceed to safety check
        with pytest.raises(RightsViolation):
            apply_governance_rules(base_aggregation, critic_reports, config)


# =============================================================================
# Precedent Consistency Tests
# =============================================================================

class TestPrecedentConsistency:
    """Test precedent consistency validation."""

    def test_precedent_conflict_triggers_escalation(self, base_aggregation, rights_config):
        """Precedent conflicts should trigger escalation."""
        critic_reports = [
            {
                "critic": "precedent",
                "conflict": True,
                "verdict": "REVIEW",
                "confidence": 0.60,
                "justification": "Conflicts with established precedent"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result["escalate"] is True
        assert "precedent_conflict" in result["safeguards_triggered"]

    def test_precedent_alignment_no_escalation(self, base_aggregation, rights_config):
        """Aligned precedents should not trigger escalation."""
        critic_reports = [
            {
                "critic": "precedent",
                "conflict": False,
                "verdict": "ALLOW",
                "confidence": 0.92,
                "justification": "Consistent with precedent"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result.get("escalate") is False
        assert "precedent_conflict" not in result.get("safeguards_triggered", [])

    def test_precedent_conflict_detection_helper(self):
        """Test _precedent_conflicts helper function."""
        # With conflict
        reports_conflict = [
            {"critic": "precedent", "conflict": True}
        ]
        assert _precedent_conflicts(reports_conflict) is True

        # Without conflict
        reports_no_conflict = [
            {"critic": "precedent", "conflict": False}
        ]
        assert _precedent_conflicts(reports_no_conflict) is False

        # No precedent critic
        reports_none = [
            {"critic": "other"}
        ]
        assert _precedent_conflicts(reports_none) is False


# =============================================================================
# Uncertainty Threshold Tests
# =============================================================================

class TestUncertaintyEscalation:
    """Test uncertainty-based escalation logic."""

    def test_high_uncertainty_triggers_escalation(self, base_aggregation, rights_config):
        """High uncertainty (confidence < 0.4) should trigger escalation."""
        critic_reports = [
            {
                "critic": "uncertainty",
                "confidence_score": 0.35,
                "verdict": "REVIEW",
                "justification": "Low confidence in decision"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result["escalate"] is True
        assert "uncertainty" in result["safeguards_triggered"]

    def test_low_uncertainty_no_escalation(self, base_aggregation, rights_config):
        """Low uncertainty (confidence >= 0.4) should not trigger escalation."""
        critic_reports = [
            {
                "critic": "uncertainty",
                "confidence_score": 0.85,
                "verdict": "ALLOW",
                "justification": "High confidence"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result.get("escalate") is False
        assert "uncertainty" not in result.get("safeguards_triggered", [])

    def test_uncertainty_helper_threshold(self):
        """Test _critic_uncertainty_high helper with various thresholds."""
        # Below threshold (0.35 < 0.4)
        reports_high = [
            {"critic": "uncertainty", "confidence_score": 0.35}
        ]
        assert _critic_uncertainty_high(reports_high) is True

        # At threshold (0.4 = 0.4, not less than)
        reports_at = [
            {"critic": "uncertainty", "confidence_score": 0.4}
        ]
        assert _critic_uncertainty_high(reports_at) is False

        # Above threshold
        reports_low = [
            {"critic": "uncertainty", "confidence_score": 0.85}
        ]
        assert _critic_uncertainty_high(reports_low) is False


# =============================================================================
# Configuration Validation Tests
# =============================================================================

class TestGovernanceConfiguration:
    """Test governance configuration validation."""

    def test_missing_rights_hierarchy_raises_error(self, base_aggregation):
        """Missing rights hierarchy should raise GovernanceException."""
        critic_reports = []
        config = {}  # Missing rights_hierarchy

        with pytest.raises(GovernanceException) as exc_info:
            apply_governance_rules(base_aggregation, critic_reports, config)

        assert "rights hierarchy" in str(exc_info.value).lower()

    def test_empty_critic_reports_allowed(self, base_aggregation, rights_config):
        """Empty critic reports should be handled gracefully."""
        critic_reports = []
        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result is not None
        assert result["escalate"] is False
        assert result["safeguards_triggered"] == []


# =============================================================================
# Integration Tests
# =============================================================================

class TestGovernanceIntegration:
    """Test complete governance pipeline integration."""

    def test_multiple_safeguards_accumulate(self, base_aggregation, rights_config):
        """Multiple safeguards should accumulate in results."""
        critic_reports = [
            {
                "critic": "safety",
                "right": "safety",
                "violation": True,
                "verdict": "REVIEW"
            },
            {
                "critic": "fairness",
                "right": "fairness",
                "violation": True,
                "verdict": "REVIEW"
            },
            {
                "critic": "transparency",
                "right": "transparency",
                "violation": True,
                "verdict": "REVIEW"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert len(result["safeguards_triggered"]) >= 3
        assert "safety" in result["safeguards_triggered"]
        assert "fairness" in result["safeguards_triggered"]
        assert "transparency" in result["safeguards_triggered"]
        assert result["escalate"] is True  # Safety triggers escalation

    def test_critical_violation_prevents_other_checks(self, base_aggregation, rights_config):
        """Critical violations should halt processing immediately."""
        critic_reports = [
            {
                "critic": "rights",
                "right": "dignity",
                "violation": True,
                "verdict": "DENY"
            },
            {
                "critic": "safety",
                "right": "safety",
                "violation": True,
                "verdict": "REVIEW"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        # Should raise before processing safety
        with pytest.raises(RightsViolation):
            apply_governance_rules(base_aggregation, critic_reports, config)

    def test_escalation_reasons_tracked(self, base_aggregation, rights_config):
        """All escalation reasons should be tracked."""
        critic_reports = [
            {
                "critic": "uncertainty",
                "confidence_score": 0.25,
                "verdict": "REVIEW"
            },
            {
                "critic": "precedent",
                "conflict": True,
                "verdict": "REVIEW"
            }
        ]

        config = {"rights_hierarchy": rights_config}

        result = apply_governance_rules(base_aggregation, critic_reports, config)

        assert result["escalate"] is True
        assert "uncertainty" in result["safeguards_triggered"]
        assert "precedent_conflict" in result["safeguards_triggered"]


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestGovernanceHelpers:
    """Test internal helper functions."""

    def test_violates_right_detection(self):
        """Test _violates_right helper function."""
        reports = [
            {"right": "dignity", "violation": True},
            {"right": "safety", "violation": False},
            {"right": "fairness", "violation": True}
        ]

        assert _violates_right(reports, "dignity") is True
        assert _violates_right(reports, "safety") is False
        assert _violates_right(reports, "fairness") is True
        assert _violates_right(reports, "nonexistent") is False

    def test_violates_right_missing_fields(self):
        """Test _violates_right with missing fields."""
        reports = [
            {"right": "dignity"},  # Missing violation field
            {"violation": True}     # Missing right field
        ]

        assert _violates_right(reports, "dignity") is False
        assert _violates_right(reports, "any") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
