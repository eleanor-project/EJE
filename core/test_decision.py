#!/usr/bin/env python3
"""
Test Final Decision Object and Compliance Flags.

Task 4.3: Test suite for compliance flag propagation.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.decision import (
    FinalDecision,
    DecisionMaker,
    AuditLog
)
from core.critic_aggregator import AggregationResult
from core.policy.rules import (
    PolicyEvaluationResult,
    ComplianceLevel,
    RuleViolation,
    RuleSeverity
)


def create_test_aggregation_result(verdict: str, confidence: float) -> AggregationResult:
    """Create a test aggregation result."""
    return AggregationResult(
        final_verdict=verdict,
        confidence=confidence,
        weighted_scores={verdict: confidence * 2},
        contributing_critics=["Critic1", "Critic2"],
        total_weight=2.0,
        conflicts_detected=[]
    )


def create_test_policy_result(
    compliance: ComplianceLevel,
    passed: int,
    total: int,
    violations: list = None
) -> PolicyEvaluationResult:
    """Create a test policy evaluation result."""
    return PolicyEvaluationResult(
        policy_id="test-policy-001",
        policy_name="Test Policy",
        overall_compliance=compliance,
        passed_rules=passed,
        total_rules=total,
        violations=violations or []
    )


def test_decision_creation_passes():
    """Test creating decision that passes policy."""
    print("\n[Test 1] FinalDecision creation (passes policy)...")

    aggregation = create_test_aggregation_result("ALLOW", 0.9)
    policy = create_test_policy_result(ComplianceLevel.PASSES, 3, 3)

    maker = DecisionMaker()
    decision = maker.make_decision(
        "Test query",
        aggregation,
        policy,
        metadata={"test": True}
    )

    assert decision.final_verdict == "ALLOW"
    assert decision.confidence == 0.9
    assert decision.compliance_level == ComplianceLevel.PASSES
    assert decision.passes_policy == True
    assert len(decision.policy_violations) == 0
    assert decision.decision_id.startswith("dec-")

    print(f"✅ Decision created: {decision.decision_id}")
    print(f"✅ Verdict: {decision.final_verdict}")
    print(f"✅ Compliance: {decision.compliance_level.value}")
    print(f"✅ Passes policy: {decision.passes_policy}")


def test_decision_creation_fails():
    """Test creating decision that fails policy."""
    print("\n[Test 2] FinalDecision creation (fails policy)...")

    aggregation = create_test_aggregation_result("ALLOW", 0.3)

    violation = RuleViolation(
        rule_id="min-conf-001",
        rule_name="Minimum Confidence",
        severity=RuleSeverity.HIGH,
        description="Confidence too low",
        expected=">=0.8",
        actual="0.3"
    )

    policy = create_test_policy_result(
        ComplianceLevel.FAILS,
        0,
        1,
        violations=[violation]
    )

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation, policy)

    assert decision.compliance_level == ComplianceLevel.FAILS
    assert decision.passes_policy == False
    assert len(decision.policy_violations) == 1
    assert decision.policy_violations[0].rule_id == "min-conf-001"

    print(f"✅ Decision created: {decision.decision_id}")
    print(f"✅ Compliance: {decision.compliance_level.value}")
    print(f"✅ Passes policy: {decision.passes_policy}")
    print(f"✅ Violations: {len(decision.policy_violations)}")


def test_decision_creation_borderline():
    """Test creating decision with borderline compliance."""
    print("\n[Test 3] FinalDecision creation (borderline)...")

    aggregation = create_test_aggregation_result("ALLOW", 0.75)
    policy = create_test_policy_result(ComplianceLevel.BORDERLINE, 2, 3)

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation, policy)

    assert decision.compliance_level == ComplianceLevel.BORDERLINE
    assert decision.passes_policy == False  # Borderline doesn't pass

    print(f"✅ Compliance: {decision.compliance_level.value}")
    print(f"✅ Passes policy: {decision.passes_policy}")


def test_decision_no_policy():
    """Test creating decision without policy evaluation."""
    print("\n[Test 4] FinalDecision without policy...")

    aggregation = create_test_aggregation_result("ALLOW", 0.9)

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation)

    # Without policy, should default to PASSES
    assert decision.compliance_level == ComplianceLevel.PASSES
    assert decision.passes_policy == True
    assert len(decision.policy_violations) == 0
    assert decision.policy_result is None

    print(f"✅ No policy evaluation: defaults to PASSES")
    print(f"✅ Passes policy: {decision.passes_policy}")


def test_decision_to_dict():
    """Test serialization to dict."""
    print("\n[Test 5] Decision to_dict()...")

    aggregation = create_test_aggregation_result("DENY", 0.88)

    violation = RuleViolation(
        rule_id="rule-001",
        rule_name="Test Rule",
        severity=RuleSeverity.MEDIUM,
        description="Test violation",
        expected="value1",
        actual="value2"
    )

    policy = create_test_policy_result(
        ComplianceLevel.FAILS,
        0,
        1,
        violations=[violation]
    )

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation, policy)

    decision_dict = decision.to_dict()

    assert "decision_id" in decision_dict
    assert decision_dict["final_verdict"] == "DENY"
    assert decision_dict["confidence"] == 0.88
    assert "compliance" in decision_dict
    assert decision_dict["compliance"]["level"] == "fails"
    assert decision_dict["compliance"]["passes_policy"] == False
    assert len(decision_dict["compliance"]["violations"]) == 1
    assert "aggregation" in decision_dict
    assert "policy_evaluation" in decision_dict

    print("✅ Dictionary serialization works")
    print(f"✅ Keys: {list(decision_dict.keys())}")


def test_decision_to_json():
    """Test serialization to JSON."""
    print("\n[Test 6] Decision to_json()...")

    aggregation = create_test_aggregation_result("ALLOW", 0.9)
    policy = create_test_policy_result(ComplianceLevel.PASSES, 2, 2)

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation, policy)

    json_str = decision.to_json()

    # Verify valid JSON
    parsed = json.loads(json_str)
    assert parsed["final_verdict"] == "ALLOW"
    assert parsed["compliance"]["level"] == "passes"

    print("✅ JSON serialization works")
    print(f"✅ JSON length: {len(json_str)} chars")


def test_audit_log_entry():
    """Test audit log entry format."""
    print("\n[Test 7] Audit log entry format...")

    aggregation = create_test_aggregation_result("ESCALATE", 0.85)

    violation1 = RuleViolation(
        rule_id="critical-001",
        rule_name="Critical Rule",
        severity=RuleSeverity.CRITICAL,
        description="Critical violation",
        expected="X",
        actual="Y"
    )

    violation2 = RuleViolation(
        rule_id="medium-001",
        rule_name="Medium Rule",
        severity=RuleSeverity.MEDIUM,
        description="Medium violation",
        expected="A",
        actual="B"
    )

    policy = create_test_policy_result(
        ComplianceLevel.FAILS,
        0,
        2,
        violations=[violation1, violation2]
    )

    maker = DecisionMaker()
    decision = maker.make_decision("Test query", aggregation, policy)

    audit_entry = decision.to_audit_log_entry()

    assert audit_entry["event_type"] == "decision"
    assert audit_entry["verdict"] == "ESCALATE"
    assert audit_entry["compliance_level"] == "fails"
    assert audit_entry["passes_policy"] == False
    assert audit_entry["violation_count"] == 2
    assert audit_entry["critical_violations"] == 1

    print("✅ Audit log entry format valid")
    print(f"✅ Violation count: {audit_entry['violation_count']}")
    print(f"✅ Critical violations: {audit_entry['critical_violations']}")


def test_audit_log():
    """Test AuditLog functionality."""
    print("\n[Test 8] AuditLog functionality...")

    with tempfile.NamedTemporaryFile(suffix='.log', delete=False, mode='w') as f:
        log_file = f.name

    try:
        audit = AuditLog(log_file)
        maker = DecisionMaker(audit_logger=audit.logger)

        # Log multiple decisions
        decisions = []
        for i in range(5):
            aggregation = create_test_aggregation_result("ALLOW", 0.8 + i * 0.02)
            compliance = ComplianceLevel.PASSES if i < 3 else ComplianceLevel.FAILS
            policy = create_test_policy_result(compliance, i, 5)

            decision = maker.make_decision(f"Query {i}", aggregation, policy)
            audit.log_decision(decision)
            decisions.append(decision)

        # Query decisions
        all_decisions = audit.get_decisions()
        assert len(all_decisions) == 5

        passing = audit.get_decisions(compliance_level=ComplianceLevel.PASSES)
        assert len(passing) == 3

        failing = audit.get_decisions(compliance_level=ComplianceLevel.FAILS)
        assert len(failing) == 2

        # Get stats
        stats = audit.get_compliance_stats()
        assert stats["total_decisions"] == 5
        assert stats["by_compliance_level"]["passes"]["count"] == 3
        assert stats["by_compliance_level"]["fails"]["count"] == 2

        print(f"✅ Logged {len(all_decisions)} decisions")
        print(f"✅ Passing: {len(passing)}, Failing: {len(failing)}")
        print(f"✅ Violation rate: {stats['violation_rate']:.1f}%")

    finally:
        Path(log_file).unlink(missing_ok=True)


def test_audit_log_export():
    """Test audit log export."""
    print("\n[Test 9] AuditLog export...")

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        export_file = f.name

    try:
        audit = AuditLog()
        maker = DecisionMaker(audit_logger=audit.logger)

        # Create and log decision
        aggregation = create_test_aggregation_result("DENY", 0.95)
        policy = create_test_policy_result(ComplianceLevel.PASSES, 5, 5)
        decision = maker.make_decision("Export test", aggregation, policy)
        audit.log_decision(decision)

        # Export
        audit.export_to_file(export_file)

        # Verify export
        with open(export_file, 'r') as f:
            export_data = json.load(f)

        assert "export_timestamp" in export_data
        assert export_data["total_decisions"] == 1
        assert len(export_data["decisions"]) == 1
        assert "compliance_stats" in export_data

        print("✅ Audit log exported")
        print(f"✅ Export file: {export_file}")
        print(f"✅ Decisions exported: {export_data['total_decisions']}")

    finally:
        Path(export_file).unlink(missing_ok=True)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Decision and Compliance Flags Tests (Task 4.3)")
    print("=" * 60)

    try:
        test_decision_creation_passes()
        test_decision_creation_fails()
        test_decision_creation_borderline()
        test_decision_no_policy()
        test_decision_to_dict()
        test_decision_to_json()
        test_audit_log_entry()
        test_audit_log()
        test_audit_log_export()

        print("\n" + "=" * 60)
        print("✅ All 9 tests passed!")
        print("=" * 60)

        print("\nCompliance Flags Validated:")
        print("  ✅ FinalDecision object with compliance flags")
        print("  ✅ Compliance level propagation (passes/borderline/fails)")
        print("  ✅ Policy violation tracking")
        print("  ✅ Audit log entry formatting")
        print("  ✅ AuditLog with filtering and statistics")
        print("  ✅ JSON serialization and export")

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
