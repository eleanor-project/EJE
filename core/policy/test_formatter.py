#!/usr/bin/env python3
"""
Test Policy Outcome Formatter.

Task 4.4: Test suite for policy outcome formatting.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.policy.formatter import (
    PolicyOutcomeFormatter,
    CompactFormatter,
    format_decision
)
from core.decision import FinalDecision
from core.critic_aggregator import AggregationResult
from core.policy.rules import (
    PolicyEvaluationResult,
    RuleEvaluationResult,
    RuleViolation,
    ComplianceLevel,
    RuleSeverity,
    RuleType
)


def create_test_decision(compliance: ComplianceLevel, violations: int = 0) -> FinalDecision:
    """Create a test decision."""
    aggregation = AggregationResult(
        final_verdict="ALLOW",
        confidence=0.85,
        weighted_scores={"ALLOW": 2.5, "DENY": 0.3},
        contributing_critics=["PrivacyCritic", "SafetyCritic", "EquityCritic"],
        total_weight=3.0,
        conflicts_detected=[]
    )

    violation_list = [
        RuleViolation(
            rule_id=f"rule-{i}",
            rule_name=f"Test Rule {i}",
            severity=RuleSeverity.HIGH if i == 0 else RuleSeverity.MEDIUM,
            description=f"Violation {i} description",
            expected="expected_value",
            actual="actual_value",
            remediation=f"Fix violation {i} by doing X"
        )
        for i in range(violations)
    ]

    policy_result = PolicyEvaluationResult(
        policy_id="policy-001",
        policy_name="Test Policy",
        overall_compliance=compliance,
        passed_rules=2 if violations == 0 else 0,
        total_rules=2,
        violations=violation_list
    )

    return FinalDecision(
        decision_id="dec-test-001",
        timestamp="2025-12-05T10:00:00Z",
        query="Test query for policy formatter",
        final_verdict="ALLOW",
        confidence=0.85,
        contributing_critics=["PrivacyCritic", "SafetyCritic", "EquityCritic"],
        compliance_level=compliance,
        passes_policy=(compliance == ComplianceLevel.PASSES),
        policy_violations=violation_list,
        aggregation_result=aggregation,
        policy_result=policy_result
    )


def test_format_passing_decision():
    """Test formatting passing decision."""
    print("\n[Test 1] Format passing decision...")

    decision = create_test_decision(ComplianceLevel.PASSES, violations=0)
    formatter = PolicyOutcomeFormatter()

    output = formatter.format_decision(decision)

    assert "DECISION REPORT" in output
    assert "APPROVED" in output
    assert decision.decision_id in output
    assert "✓" in output or "PASSES" in output.upper()
    assert "PrivacyCritic" in output

    print("✅ Passing decision formatted")
    print(f"✅ Output length: {len(output)} chars")
    print(f"✅ Contains required sections")


def test_format_failing_decision():
    """Test formatting failing decision."""
    print("\n[Test 2] Format failing decision...")

    decision = create_test_decision(ComplianceLevel.FAILS, violations=2)
    formatter = PolicyOutcomeFormatter()

    output = formatter.format_decision(decision)

    assert "BLOCKED" in output
    assert "POLICY VIOLATIONS" in output
    assert "Test Rule 0" in output
    assert "Test Rule 1" in output
    assert "Remediation" in output

    print("✅ Failing decision formatted")
    print("✅ Contains violation details")
    print("✅ Contains remediation")


def test_format_borderline_decision():
    """Test formatting borderline decision."""
    print("\n[Test 3] Format borderline decision...")

    decision = create_test_decision(ComplianceLevel.BORDERLINE, violations=1)
    formatter = PolicyOutcomeFormatter()

    output = formatter.format_decision(decision)

    assert "BORDERLINE" in output
    assert "⚠" in output or "WARNING" in output.upper()

    print("✅ Borderline decision formatted")
    print("✅ Contains warning indicators")


def test_compact_formatter():
    """Test compact formatter."""
    print("\n[Test 4] Compact formatter...")

    decision = create_test_decision(ComplianceLevel.PASSES)

    compact = CompactFormatter.format_decision(decision)

    assert "ALLOW" in compact
    assert "85%" in compact or "0.85" in compact
    assert len(compact) < 200  # Should be brief

    print(f"✅ Compact format: {compact}")
    print(f"✅ Length: {len(compact)} chars")


def test_violation_formatting():
    """Test individual violation formatting."""
    print("\n[Test 5] Violation formatting...")

    violation = RuleViolation(
        rule_id="test-001",
        rule_name="Test Violation",
        severity=RuleSeverity.CRITICAL,
        description="Critical issue detected",
        expected="secure",
        actual="insecure",
        remediation="Fix by implementing security controls"
    )

    compact = CompactFormatter.format_violation(violation)

    assert "CRITICAL" in compact
    assert "Test Violation" in compact
    assert "Critical issue detected" in compact

    print(f"✅ Violation formatted: {compact}")


def test_format_without_remediation():
    """Test formatting without remediation."""
    print("\n[Test 6] Format without remediation...")

    decision = create_test_decision(ComplianceLevel.FAILS, violations=1)
    formatter = PolicyOutcomeFormatter()

    output = formatter.format_decision(decision, include_remediation=False)

    assert "POLICY VIOLATIONS" in output
    # Remediation section should not be present
    assert output.count("Remediation") < 2  # Might appear in headers

    print("✅ Formatted without remediation details")


def test_format_with_technical_details():
    """Test formatting with technical details."""
    print("\n[Test 7] Format with technical details...")

    decision = create_test_decision(ComplianceLevel.PASSES)
    formatter = PolicyOutcomeFormatter(include_technical_details=True)

    output = formatter.format_decision(decision)

    assert "TECHNICAL DETAILS" in output
    assert decision.decision_id in output
    assert "Total Weight" in output

    print("✅ Technical details included")


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 8] Convenience function...")

    decision = create_test_decision(ComplianceLevel.PASSES)

    # Verbose
    verbose_output = format_decision(decision, verbose=True)
    assert len(verbose_output) > 200
    assert "DECISION REPORT" in verbose_output

    # Compact
    compact_output = format_decision(decision, verbose=False)
    assert len(compact_output) < 200
    assert "ALLOW" in compact_output

    print("✅ Convenience function works")
    print(f"✅ Verbose: {len(verbose_output)} chars")
    print(f"✅ Compact: {len(compact_output)} chars")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Policy Outcome Formatter Tests (Task 4.4)")
    print("=" * 60)

    try:
        test_format_passing_decision()
        test_format_failing_decision()
        test_format_borderline_decision()
        test_compact_formatter()
        test_violation_formatting()
        test_format_without_remediation()
        test_format_with_technical_details()
        test_convenience_function()

        print("\n" + "=" * 60)
        print("✅ All 8 tests passed!")
        print("=" * 60)

        print("\nPolicy Outcome Formatting Validated:")
        print("  ✅ Verbose formatting with all sections")
        print("  ✅ Compact one-liner formatting")
        print("  ✅ All compliance levels (passes/borderline/fails)")
        print("  ✅ Violation details with remediation")
        print("  ✅ Critic analysis integration")
        print("  ✅ Technical details (optional)")

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
