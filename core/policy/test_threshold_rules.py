#!/usr/bin/env python3
"""
Test Threshold-Based Policy Rules.

Task 4.2: Test suite for threshold rules.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.policy.threshold_rules import (
    MinimumConfidenceRule,
    CriticAgreementRule,
    MinimumCriticsRule,
    VerdictConsistencyRule
)
from core.policy.rules import (
    RuleSeverity,
    ComplianceLevel
)
from core.critic_aggregator import AggregationResult


def create_test_aggregation_result(
    verdict: str,
    confidence: float,
    critics: list,
    conflicts: int = 0,
    weighted_scores: dict = None
):
    """Create a test aggregation result."""
    conflicts_list = [
        {"description": f"Test conflict {i+1}"} for i in range(conflicts)
    ]

    if weighted_scores is None:
        weighted_scores = {verdict: confidence * len(critics)}

    return AggregationResult(
        final_verdict=verdict,
        confidence=confidence,
        weighted_scores=weighted_scores,
        contributing_critics=critics,
        total_weight=float(len(critics)),
        conflicts_detected=conflicts_list
    )


def test_minimum_confidence_pass():
    """Test MinimumConfidenceRule passing."""
    print("\n[Test 1] MinimumConfidenceRule (pass)...")

    rule = MinimumConfidenceRule("min-conf-001", 0.8, RuleSeverity.HIGH)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.9, ["Critic1", "Critic2"]
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass"
    assert result.compliance_level == ComplianceLevel.PASSES
    assert result.score == 1.0
    assert len(result.violations) == 0
    assert "confidence" in result.metadata
    assert result.metadata["confidence"] == 0.9

    print(f"✅ Rule passed: confidence 0.9 >= 0.8")
    print(f"✅ Compliance: {result.compliance_level.value}")
    print(f"✅ Score: {result.score}")


def test_minimum_confidence_fail():
    """Test MinimumConfidenceRule failing."""
    print("\n[Test 2] MinimumConfidenceRule (fail)...")

    rule = MinimumConfidenceRule("min-conf-002", 0.8, RuleSeverity.HIGH)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.3, ["Critic1"]
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    assert result.compliance_level == ComplianceLevel.FAILS
    assert result.score < 1.0
    assert len(result.violations) == 1

    violation = result.violations[0]
    assert "below minimum threshold" in violation.description
    assert violation.severity == RuleSeverity.HIGH
    assert violation.remediation is not None and len(violation.remediation) > 0

    print(f"✅ Rule failed (expected): confidence 0.3 < 0.8")
    print(f"✅ Compliance: {result.compliance_level.value}")
    print(f"✅ Violation: {violation.description}")


def test_minimum_confidence_borderline():
    """Test MinimumConfidenceRule borderline."""
    print("\n[Test 3] MinimumConfidenceRule (borderline)...")

    rule = MinimumConfidenceRule("min-conf-003", 0.8)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.65, ["Critic1", "Critic2"]
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should not pass"
    # Score = 0.65/0.8 = 0.8125, which is >= 0.5, so BORDERLINE
    assert result.compliance_level == ComplianceLevel.BORDERLINE
    assert 0.5 <= result.score < 1.0

    print(f"✅ Borderline case: confidence 0.65 vs threshold 0.8")
    print(f"✅ Compliance: {result.compliance_level.value}")
    print(f"✅ Score: {result.score:.2f}")


def test_critic_agreement_pass():
    """Test CriticAgreementRule passing."""
    print("\n[Test 4] CriticAgreementRule (pass)...")

    rule = CriticAgreementRule("agree-001", max_conflicts=0)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.9, ["Critic1", "Critic2"], conflicts=0
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass"
    assert result.compliance_level == ComplianceLevel.PASSES
    assert result.score == 1.0
    assert result.metadata["conflicts"] == 0

    print(f"✅ Rule passed: 0 conflicts")
    print(f"✅ Compliance: {result.compliance_level.value}")


def test_critic_agreement_fail():
    """Test CriticAgreementRule failing."""
    print("\n[Test 5] CriticAgreementRule (fail)...")

    rule = CriticAgreementRule("agree-002", max_conflicts=1)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.9, ["Critic1", "Critic2", "Critic3"], conflicts=3
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    assert len(result.violations) == 1

    violation = result.violations[0]
    assert "Too many critic conflicts" in violation.description
    assert "conflict_details" in violation.context

    print(f"✅ Rule failed (expected): 3 conflicts > 1 max")
    print(f"✅ Violation: {violation.description}")


def test_minimum_critics_pass():
    """Test MinimumCriticsRule passing."""
    print("\n[Test 6] MinimumCriticsRule (pass)...")

    rule = MinimumCriticsRule("critics-001", min_critics=2)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.9, ["Critic1", "Critic2", "Critic3"]
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass"
    assert result.compliance_level == ComplianceLevel.PASSES
    assert result.metadata["num_critics"] == 3
    assert result.metadata["min_critics"] == 2

    print(f"✅ Rule passed: 3 critics >= 2 required")
    print(f"✅ Critics: {result.metadata['critics']}")


def test_minimum_critics_fail():
    """Test MinimumCriticsRule failing."""
    print("\n[Test 7] MinimumCriticsRule (fail)...")

    rule = MinimumCriticsRule("critics-002", min_critics=3)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW", 0.9, ["Critic1"]
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    assert len(result.violations) == 1

    violation = result.violations[0]
    assert "Insufficient critics" in violation.description
    assert violation.context["deficit"] == 2

    print(f"✅ Rule failed (expected): 1 critic < 3 required")
    print(f"✅ Deficit: {violation.context['deficit']} critics")


def test_verdict_consistency_pass():
    """Test VerdictConsistencyRule passing."""
    print("\n[Test 8] VerdictConsistencyRule (pass)...")

    rule = VerdictConsistencyRule("consistency-001", min_margin=0.2)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW",
            0.9,
            ["Critic1", "Critic2"],
            weighted_scores={"ALLOW": 3.0, "DENY": 0.5}
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass"
    assert result.compliance_level == ComplianceLevel.PASSES
    # Margin = 3.0 - 0.5 = 2.5
    assert result.metadata["margin"] >= 0.2

    print(f"✅ Rule passed: margin {result.metadata['margin']:.2f} >= 0.2")
    print(f"✅ Top score: {result.metadata['top_score']}")


def test_verdict_consistency_fail():
    """Test VerdictConsistencyRule failing."""
    print("\n[Test 9] VerdictConsistencyRule (fail)...")

    rule = VerdictConsistencyRule("consistency-002", min_margin=0.5)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW",
            0.85,
            ["Critic1", "Critic2"],
            weighted_scores={"ALLOW": 1.8, "DENY": 1.7}
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    assert len(result.violations) == 1

    violation = result.violations[0]
    assert "margin too small" in violation.description
    assert "top_verdict" in violation.context
    assert "second_verdict" in violation.context

    print(f"✅ Rule failed (expected): margin {result.metadata['margin']:.2f} < 0.5")
    print(f"✅ Close race: {violation.context['top_verdict']} vs {violation.context['second_verdict']}")


def test_verdict_consistency_single_verdict():
    """Test VerdictConsistencyRule with single verdict."""
    print("\n[Test 10] VerdictConsistencyRule (single verdict)...")

    rule = VerdictConsistencyRule("consistency-003", min_margin=0.3)

    decision_context = {
        "aggregation_result": create_test_aggregation_result(
            "ALLOW",
            0.9,
            ["Critic1", "Critic2"],
            weighted_scores={"ALLOW": 2.5}  # Only one verdict
        ),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass (single verdict)"
    assert result.compliance_level == ComplianceLevel.PASSES
    assert result.metadata.get("single_verdict") == True

    print(f"✅ Rule passed: only one verdict (automatically consistent)")


def test_rule_validation():
    """Test rule parameter validation."""
    print("\n[Test 11] Rule parameter validation...")

    # Test invalid confidence threshold
    try:
        MinimumConfidenceRule("bad-1", 1.5)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "0.0-1.0" in str(e)
        print("✅ Invalid confidence threshold rejected")

    # Test invalid min_critics
    try:
        MinimumCriticsRule("bad-2", 0)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert ">= 1" in str(e)
        print("✅ Invalid min_critics rejected")

    # Test invalid margin
    try:
        VerdictConsistencyRule("bad-3", -0.1)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "0.0-1.0" in str(e)
        print("✅ Invalid margin rejected")


def test_missing_aggregation_result():
    """Test rules with missing aggregation result."""
    print("\n[Test 12] Missing aggregation result handling...")

    rule = MinimumConfidenceRule("missing-001", 0.8)

    decision_context = {
        "query": "Test query"
        # No aggregation_result
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    assert result.score == 0.0
    assert "error" in result.metadata

    print("✅ Missing aggregation_result handled")
    print(f"✅ Error: {result.metadata['error']}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Threshold Rules Tests (Task 4.2)")
    print("=" * 60)

    try:
        test_minimum_confidence_pass()
        test_minimum_confidence_fail()
        test_minimum_confidence_borderline()
        test_critic_agreement_pass()
        test_critic_agreement_fail()
        test_minimum_critics_pass()
        test_minimum_critics_fail()
        test_verdict_consistency_pass()
        test_verdict_consistency_fail()
        test_verdict_consistency_single_verdict()
        test_rule_validation()
        test_missing_aggregation_result()

        print("\n" + "=" * 60)
        print("✅ All 12 tests passed!")
        print("=" * 60)

        print("\nThreshold Rules Validated:")
        print("  ✅ MinimumConfidenceRule: Pass/Fail/Borderline cases")
        print("  ✅ CriticAgreementRule: Conflict detection")
        print("  ✅ MinimumCriticsRule: Critic count requirements")
        print("  ✅ VerdictConsistencyRule: Margin validation")
        print("  ✅ Parameter validation and error handling")

        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
