#!/usr/bin/env python3
"""
Test Critic Aggregator with Weighting

Task 2.1: Add Critic Weighting - Test Suite
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.critic_aggregator import CriticAggregator, aggregate_critics


def create_evidence_bundle(critic_name: str, verdict: str, confidence: float) -> dict:
    """Create a test evidence bundle."""
    return {
        "bundle_id": f"test-{critic_name.lower()}",
        "version": "1.0",
        "critic_output": {
            "critic_name": critic_name,
            "verdict": verdict,
            "confidence": confidence,
            "justification": f"{critic_name} justification"
        },
        "metadata": {
            "timestamp": "2025-12-04T10:00:00Z",
            "critic_name": critic_name,
            "config_version": "1.0"
        },
        "input_snapshot": {
            "prompt": "Test case"
        }
    }


def test_basic_aggregation():
    """Test basic aggregation without weights."""
    print("\n[Test 1] Basic aggregation (no weights)...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "ALLOW", 0.8),
        create_evidence_bundle("Critic3", "ALLOW", 0.85)
    ]

    aggregator = CriticAggregator()
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    assert result.final_verdict == "ALLOW", f"Expected ALLOW, got {result.final_verdict}"
    assert result.confidence > 0.8, f"Expected high confidence, got {result.confidence}"
    assert len(result.contributing_critics) == 3

    print(f"✅ Final verdict: {result.final_verdict}")
    print(f"✅ Confidence: {result.confidence:.2f}")
    print(f"✅ Contributing critics: {len(result.contributing_critics)}")


def test_weighted_aggregation():
    """Test aggregation with different critic weights."""
    print("\n[Test 2] Weighted aggregation...")

    bundles = [
        create_evidence_bundle("HighWeight", "ALLOW", 0.8),
        create_evidence_bundle("LowWeight", "DENY", 0.9),
    ]

    # Give first critic 3x weight
    weights = {
        "HighWeight": 3.0,
        "LowWeight": 1.0
    }

    aggregator = CriticAggregator(weights=weights)
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    # HighWeight: 0.8 * 3.0 = 2.4 for ALLOW
    # LowWeight: 0.9 * 1.0 = 0.9 for DENY
    # ALLOW should win

    assert result.final_verdict == "ALLOW", f"Expected ALLOW, got {result.final_verdict}"
    assert abs(result.weighted_scores["ALLOW"] - 2.4) < 0.01, f"Expected ~2.4, got {result.weighted_scores['ALLOW']}"
    assert abs(result.weighted_scores["DENY"] - 0.9) < 0.01, f"Expected ~0.9, got {result.weighted_scores['DENY']}"

    print(f"✅ Final verdict: {result.final_verdict} (weighted scores: {result.weighted_scores})")
    print(f"✅ Total weight: {result.total_weight}")


def test_equal_weights_tie_breaking():
    """Test tie-breaking with equal weights."""
    print("\n[Test 3] Tie-breaking with equal weights...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "DENY", 0.9)
    ]

    aggregator = CriticAggregator()  # Equal weights (1.0)
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    # With equal weights and confidence, first one (alphabetically) usually wins
    # But confidence should be lowered due to close scores
    assert result.confidence < 0.9, "Confidence should be lowered for close scores"

    print(f"✅ Final verdict: {result.final_verdict}")
    print(f"✅ Confidence lowered to: {result.confidence:.2f} (due to close scores)")


def test_weight_override():
    """Test that higher weight overrides lower weight despite confidence."""
    print("\n[Test 4] Weight overrides confidence...")

    bundles = [
        create_evidence_bundle("LowConfHighWeight", "ALLOW", 0.6),
        create_evidence_bundle("HighConfLowWeight", "DENY", 0.95)
    ]

    weights = {
        "LowConfHighWeight": 5.0,  # 0.6 * 5.0 = 3.0
        "HighConfLowWeight": 1.0   # 0.95 * 1.0 = 0.95
    }

    aggregator = CriticAggregator(weights=weights)
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    assert result.final_verdict == "ALLOW", "High weight should override high confidence"

    print(f"✅ ALLOW wins: 0.6×5.0={result.weighted_scores['ALLOW']:.1f} > 0.95×1.0={result.weighted_scores['DENY']:.2f}")


def test_explicit_escalation():
    """Test that explicit ESCALATE verdict is respected."""
    print("\n[Test 5] Explicit escalation...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "ESCALATE", 0.8),
        create_evidence_bundle("Critic3", "ALLOW", 0.85)
    ]

    aggregator = CriticAggregator()
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    assert result.final_verdict == "ESCALATE", "Explicit ESCALATE should be respected"

    print(f"✅ Verdict: {result.final_verdict} (explicit escalation respected)")


def test_conflict_detection():
    """Test conflict detection between opposing critics."""
    print("\n[Test 6] Conflict detection...")

    bundles = [
        create_evidence_bundle("CriticAllow", "ALLOW", 0.9),
        create_evidence_bundle("CriticDeny", "DENY", 0.9)
    ]

    aggregator = CriticAggregator()
    result = aggregator.aggregate(bundles, escalate_on_conflict=True)

    # Should detect conflict and escalate
    assert len(result.conflicts_detected) > 0, "Should detect conflicts"
    assert result.final_verdict == "ESCALATE", "Should escalate on conflict"

    print(f"✅ Conflicts detected: {len(result.conflicts_detected)}")
    print(f"✅ Escalated due to: {result.conflicts_detected[0]['description']}")


def test_no_escalation_on_conflict():
    """Test proceeding without escalation despite conflicts."""
    print("\n[Test 7] No escalation on conflict (disabled)...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "DENY", 0.7)
    ]

    aggregator = CriticAggregator()
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    # Should detect conflict but not escalate
    assert len(result.conflicts_detected) > 0, "Should detect conflicts"
    assert result.final_verdict in ["ALLOW", "DENY"], "Should pick a verdict without escalating"

    print(f"✅ Conflict detected but not escalated")
    print(f"✅ Final verdict: {result.final_verdict}")


def test_unanimous_verdict():
    """Test unanimous verdict increases confidence."""
    print("\n[Test 8] Unanimous verdict...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "ALLOW", 0.85),
        create_evidence_bundle("Critic3", "ALLOW", 0.92),
        create_evidence_bundle("Critic4", "ALLOW", 0.88)
    ]

    aggregator = CriticAggregator()
    result = aggregator.aggregate(bundles, escalate_on_conflict=False)

    assert result.final_verdict == "ALLOW"
    assert result.confidence == 1.0, "Unanimous verdict should have 100% confidence"
    assert len(result.conflicts_detected) == 0, "Should have no conflicts"

    print(f"✅ Unanimous verdict with confidence: {result.confidence:.2f}")


def test_weight_management():
    """Test weight get/set/remove operations."""
    print("\n[Test 9] Weight management...")

    aggregator = CriticAggregator()

    # Set weights
    aggregator.set_weight("Critic1", 2.0)
    aggregator.set_weight("Critic2", 0.5)

    assert aggregator.get_weight("Critic1") == 2.0
    assert aggregator.get_weight("Critic2") == 0.5
    assert aggregator.get_weight("Critic3") == 1.0, "Default weight should be 1.0"

    # Get all weights
    all_weights = aggregator.get_all_weights()
    assert len(all_weights) == 2

    # Remove weight
    aggregator.remove_weight("Critic1")
    assert aggregator.get_weight("Critic1") == 1.0, "Should revert to default"

    print("✅ Weight management operations work correctly")


def test_aggregation_with_justification():
    """Test aggregation with synthesized justification."""
    print("\n[Test 10] Aggregation with justification...")

    bundles = [
        create_evidence_bundle("PrivacyCritic", "ALLOW", 0.9),
        create_evidence_bundle("SafetyCritic", "ALLOW", 0.85),
        create_evidence_bundle("EquityCritic", "ALLOW", 0.88)
    ]

    aggregator = CriticAggregator()
    result, justification = aggregator.aggregate_with_justification(bundles)

    assert result.final_verdict == "ALLOW"
    assert "PrivacyCritic" in justification
    assert "confidence" in justification.lower()
    assert len(justification) > 50, "Justification should be descriptive"

    print(f"✅ Justification: {justification[:100]}...")


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 11] Convenience function...")

    bundles = [
        create_evidence_bundle("Critic1", "ALLOW", 0.9),
        create_evidence_bundle("Critic2", "ALLOW", 0.8)
    ]

    weights = {"Critic1": 2.0, "Critic2": 1.0}
    result = aggregate_critics(bundles, weights=weights)

    assert result.final_verdict == "ALLOW"
    assert result.total_weight == 3.0

    print("✅ Convenience function works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Critic Aggregator Tests (Task 2.1)")
    print("=" * 60)

    try:
        test_basic_aggregation()
        test_weighted_aggregation()
        test_equal_weights_tie_breaking()
        test_weight_override()
        test_explicit_escalation()
        test_conflict_detection()
        test_no_escalation_on_conflict()
        test_unanimous_verdict()
        test_weight_management()
        test_aggregation_with_justification()
        test_convenience_function()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
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
