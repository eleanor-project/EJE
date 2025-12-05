#!/usr/bin/env python3
"""
Test Policy Rule Interface.

Task 4.1: Test suite for policy rule interface and policy engine.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.policy.rules import (
    PolicyRule,
    PolicyEngine,
    RuleType,
    RuleSeverity,
    ComplianceLevel,
    RuleEvaluationResult,
    RuleViolation
)


class MinimumConfidenceRule(PolicyRule):
    """Example rule: Check minimum confidence threshold."""

    def __init__(self, rule_id: str, min_confidence: float):
        super().__init__(
            rule_id=rule_id,
            name="Minimum Confidence Threshold",
            rule_type=RuleType.THRESHOLD,
            severity=RuleSeverity.HIGH,
            description=f"Requires confidence >= {min_confidence}"
        )
        self.min_confidence = min_confidence

    def evaluate(self, decision_context: dict) -> RuleEvaluationResult:
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            return self._create_result(False, 0.0)

        confidence = aggregation_result.confidence

        if confidence >= self.min_confidence:
            return self._create_result(True, 1.0)
        else:
            violation = self._create_violation(
                description=f"Confidence {confidence:.2f} below threshold",
                expected=f">= {self.min_confidence}",
                actual=confidence,
                remediation="Gather more evidence or escalate to human review"
            )

            score = confidence / self.min_confidence
            return self._create_result(False, score, [violation])


class CriticAgreementRule(PolicyRule):
    """Example rule: Check critic agreement level."""

    def __init__(self, rule_id: str, min_agreement: float):
        super().__init__(
            rule_id=rule_id,
            name="Critic Agreement Threshold",
            rule_type=RuleType.THRESHOLD,
            severity=RuleSeverity.MEDIUM,
            description=f"Requires >= {min_agreement*100}% critic agreement"
        )
        self.min_agreement = min_agreement

    def evaluate(self, decision_context: dict) -> RuleEvaluationResult:
        aggregation_result = decision_context.get("aggregation_result")

        if not aggregation_result:
            return self._create_result(False, 0.0)

        # Check if all critics agree (no conflicts)
        has_conflicts = len(aggregation_result.conflicts_detected) > 0

        if not has_conflicts:
            return self._create_result(True, 1.0)
        else:
            violation = self._create_violation(
                description=f"Critics disagree ({len(aggregation_result.conflicts_detected)} conflicts)",
                expected="No conflicts",
                actual=f"{len(aggregation_result.conflicts_detected)} conflicts",
                remediation="Review conflicting critic outputs"
            )

            return self._create_result(False, 0.5, [violation])


def create_test_aggregation_result(verdict: str, confidence: float, conflicts: int = 0):
    """Create a test aggregation result."""
    from core.critic_aggregator import AggregationResult

    conflicts_list = [{"type": "test", "description": "Test conflict"} for _ in range(conflicts)]

    return AggregationResult(
        final_verdict=verdict,
        confidence=confidence,
        weighted_scores={verdict: confidence},
        contributing_critics=["Critic1", "Critic2"],
        total_weight=2.0,
        conflicts_detected=conflicts_list
    )


def test_rule_creation():
    """Test creating a policy rule."""
    print("\n[Test 1] Rule creation...")

    rule = MinimumConfidenceRule("min-conf-001", 0.8)

    assert rule.rule_id == "min-conf-001"
    assert rule.name == "Minimum Confidence Threshold"
    assert rule.rule_type == RuleType.THRESHOLD
    assert rule.severity == RuleSeverity.HIGH

    print(f"✅ Rule created: {rule.name}")
    print(f"✅ Type: {rule.rule_type.value}")
    print(f"✅ Severity: {rule.severity.value}")


def test_rule_evaluation_pass():
    """Test rule evaluation that passes."""
    print("\n[Test 2] Rule evaluation (pass)...")

    rule = MinimumConfidenceRule("min-conf-002", 0.8)

    decision_context = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.9),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert result.passed, "Rule should pass"
    assert result.compliance_level == ComplianceLevel.PASSES
    assert result.score == 1.0
    assert len(result.violations) == 0

    print(f"✅ Rule passed: {result.passed}")
    print(f"✅ Compliance: {result.compliance_level.value}")
    print(f"✅ Score: {result.score}")


def test_rule_evaluation_fail():
    """Test rule evaluation that fails."""
    print("\n[Test 3] Rule evaluation (fail)...")

    rule = MinimumConfidenceRule("min-conf-003", 0.8)

    decision_context = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.6),
        "query": "Test query"
    }

    result = rule.evaluate(decision_context)

    assert not result.passed, "Rule should fail"
    # Score is 0.6/0.8 = 0.75, which is >= 0.5, so it's BORDERLINE
    assert result.compliance_level in [ComplianceLevel.BORDERLINE, ComplianceLevel.FAILS]
    assert result.score < 1.0
    assert len(result.violations) > 0

    violation = result.violations[0]
    assert violation.rule_id == "min-conf-003"
    assert violation.severity == RuleSeverity.HIGH

    print(f"✅ Rule failed (expected): {not result.passed}")
    print(f"✅ Compliance: {result.compliance_level.value}")
    print(f"✅ Violations: {len(result.violations)}")
    print(f"✅ Violation: {violation.description}")


def test_policy_engine_empty():
    """Test policy engine with no rules."""
    print("\n[Test 4] Policy engine (no rules)...")

    engine = PolicyEngine("policy-001", "Test Policy")

    decision_context = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.9),
        "query": "Test query"
    }

    result = engine.evaluate(decision_context)

    assert result.overall_compliance == ComplianceLevel.PASSES
    assert result.total_rules == 0
    assert result.passed_rules == 0

    print(f"✅ Overall compliance: {result.overall_compliance.value}")
    print(f"✅ Total rules: {result.total_rules}")


def test_policy_engine_single_rule():
    """Test policy engine with single rule."""
    print("\n[Test 5] Policy engine (single rule)...")

    engine = PolicyEngine("policy-002", "Test Policy")
    rule = MinimumConfidenceRule("min-conf-004", 0.8)
    engine.add_rule(rule)

    # Test with passing confidence
    decision_context_pass = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.9),
        "query": "Test query"
    }

    result_pass = engine.evaluate(decision_context_pass)

    assert result_pass.overall_compliance == ComplianceLevel.PASSES
    assert result_pass.passed_rules == 1
    assert result_pass.total_rules == 1

    # Test with failing confidence (< 0.5 * threshold to get true FAILS)
    decision_context_fail = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.3),
        "query": "Test query"
    }

    result_fail = engine.evaluate(decision_context_fail)

    # With confidence 0.3 and threshold 0.8, score = 0.375 < 0.5, so FAILS
    assert result_fail.overall_compliance == ComplianceLevel.FAILS
    assert result_fail.passed_rules == 0
    assert result_fail.total_rules == 1

    print(f"✅ Pass case: {result_pass.overall_compliance.value}")
    print(f"✅ Fail case: {result_fail.overall_compliance.value}")


def test_policy_engine_multiple_rules():
    """Test policy engine with multiple rules."""
    print("\n[Test 6] Policy engine (multiple rules)...")

    engine = PolicyEngine("policy-003", "Test Policy")
    engine.add_rule(MinimumConfidenceRule("min-conf-005", 0.8))
    engine.add_rule(CriticAgreementRule("critic-agree-001", 0.5))

    # Test with all passing
    decision_context_pass = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.9, conflicts=0),
        "query": "Test query"
    }

    result_pass = engine.evaluate(decision_context_pass)

    assert result_pass.overall_compliance == ComplianceLevel.PASSES
    assert result_pass.passed_rules == 2
    assert result_pass.total_rules == 2

    # Test with one failing
    decision_context_partial = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.9, conflicts=2),
        "query": "Test query"
    }

    result_partial = engine.evaluate(decision_context_partial)

    assert result_partial.passed_rules == 1
    assert result_partial.total_rules == 2

    print(f"✅ All pass: {result_pass.passed_rules}/{result_pass.total_rules}")
    print(f"✅ Partial: {result_partial.passed_rules}/{result_partial.total_rules}")


def test_rule_management():
    """Test adding/removing rules."""
    print("\n[Test 7] Rule management...")

    engine = PolicyEngine("policy-004", "Test Policy")

    # Add rules
    engine.add_rule(MinimumConfidenceRule("rule-1", 0.8))
    engine.add_rule(MinimumConfidenceRule("rule-2", 0.7))

    assert len(engine.get_rules()) == 2

    # Get rule by ID
    rule = engine.get_rule_by_id("rule-1")
    assert rule is not None
    assert rule.rule_id == "rule-1"

    # Remove rule
    removed = engine.remove_rule("rule-1")
    assert removed, "Should return True"
    assert len(engine.get_rules()) == 1

    # Try to remove non-existent rule
    removed_again = engine.remove_rule("rule-1")
    assert not removed_again, "Should return False"

    print(f"✅ Rules added: 2")
    print(f"✅ Rule removed: 1")
    print(f"✅ Final count: {len(engine.get_rules())}")


def test_compliance_levels():
    """Test compliance level determination."""
    print("\n[Test 8] Compliance levels...")

    engine = PolicyEngine("policy-005", "Test Policy")
    engine.add_rule(MinimumConfidenceRule("rule-1", 0.8))

    # Full pass
    context_pass = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.95),
        "query": "Test"
    }
    result_pass = engine.evaluate(context_pass)
    assert result_pass.overall_compliance == ComplianceLevel.PASSES

    # Fail
    context_fail = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.3),
        "query": "Test"
    }
    result_fail = engine.evaluate(context_fail)
    assert result_fail.overall_compliance == ComplianceLevel.FAILS

    # Borderline (score between 0.5 and 1.0)
    context_borderline = {
        "aggregation_result": create_test_aggregation_result("ALLOW", 0.75),
        "query": "Test"
    }
    result_borderline = engine.evaluate(context_borderline)
    # Should be borderline or fails depending on threshold
    assert result_borderline.overall_compliance in [ComplianceLevel.BORDERLINE, ComplianceLevel.FAILS]

    print(f"✅ Pass: {result_pass.overall_compliance.value}")
    print(f"✅ Fail: {result_fail.overall_compliance.value}")
    print(f"✅ Borderline: {result_borderline.overall_compliance.value}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Policy Rule Interface Tests (Task 4.1)")
    print("=" * 60)

    try:
        test_rule_creation()
        test_rule_evaluation_pass()
        test_rule_evaluation_fail()
        test_policy_engine_empty()
        test_policy_engine_single_rule()
        test_policy_engine_multiple_rules()
        test_rule_management()
        test_compliance_levels()

        print("\n" + "=" * 60)
        print("✅ All 8 tests passed!")
        print("=" * 60)

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
