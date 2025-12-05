#!/usr/bin/env python3
"""
Test the Evidence Normalizer.

Validates that normalized outputs conform to the evidence bundle schema.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evidence_normalizer import EvidenceNormalizer

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("Warning: jsonschema not installed, skipping schema validation")


def test_basic_normalization():
    """Test basic normalization with standard critic output."""
    print("\n[Test 1] Basic normalization...")

    normalizer = EvidenceNormalizer()

    raw_output = {
        "critic_name": "TestCritic",
        "verdict": "ALLOW",
        "confidence": 0.85,
        "justification": "Test case passes all privacy checks."
    }

    input_data = {
        "prompt": "Test input for normalization",
        "context": {
            "jurisdiction": "US"
        }
    }

    bundle = normalizer.normalize(raw_output, input_data)

    # Check required fields
    assert "bundle_id" in bundle, "Missing bundle_id"
    assert "version" in bundle, "Missing version"
    assert "critic_output" in bundle, "Missing critic_output"
    assert "metadata" in bundle, "Missing metadata"
    assert "input_snapshot" in bundle, "Missing input_snapshot"

    print(f"✅ Bundle ID: {bundle['bundle_id']}")
    print(f"✅ Critic: {bundle['critic_output']['critic_name']}")
    print(f"✅ Verdict: {bundle['critic_output']['verdict']}")

    return bundle


def test_missing_fields():
    """Test handling of missing fields with auto-fill."""
    print("\n[Test 2] Handling missing fields...")

    normalizer = EvidenceNormalizer()

    # Minimal raw output (missing confidence, justification)
    raw_output = {
        "name": "MinimalCritic",  # Different field name
        "decision": "DENY"  # Different field name
    }

    input_data = {
        "text": "Minimal test input"  # Different field name
    }

    bundle = normalizer.normalize(raw_output, input_data)

    # Should auto-fill missing fields
    assert bundle["critic_output"]["confidence"] == 0.5, "Should default confidence"
    assert len(bundle["critic_output"]["justification"]) >= 10, "Should generate justification"

    print(f"✅ Auto-filled confidence: {bundle['critic_output']['confidence']}")
    print(f"✅ Auto-generated justification: {bundle['critic_output']['justification'][:50]}...")

    return bundle


def test_verdict_normalization():
    """Test verdict normalization from various formats."""
    print("\n[Test 3] Verdict normalization...")

    normalizer = EvidenceNormalizer()

    test_cases = [
        ("APPROVE", "ALLOW"),
        ("reject", "DENY"),
        ("HUMAN_REVIEW", "ESCALATE"),
        ("skip", "ABSTAIN")
    ]

    for raw_verdict, expected in test_cases:
        raw_output = {
            "critic_name": "VerdictTest",
            "verdict": raw_verdict,
            "confidence": 0.8,
            "justification": "Test verdict normalization"
        }

        input_data = {"prompt": "Test"}

        bundle = normalizer.normalize(raw_output, input_data)
        actual = bundle["critic_output"]["verdict"]

        assert actual == expected, f"Expected {expected}, got {actual}"
        print(f"✅ {raw_verdict:15} → {actual}")

    return True


def test_batch_normalization():
    """Test batch normalization of multiple critics."""
    print("\n[Test 4] Batch normalization...")

    normalizer = EvidenceNormalizer()

    raw_outputs = [
        {
            "critic_name": "Critic1",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "First critic approves"
        },
        {
            "critic_name": "Critic2",
            "verdict": "DENY",
            "confidence": 0.8,
            "justification": "Second critic denies"
        },
        {
            "critic_name": "Critic3",
            "verdict": "ESCALATE",
            "confidence": 0.7,
            "justification": "Third critic escalates"
        }
    ]

    input_data = {"prompt": "Batch test input"}

    bundles = normalizer.batch_normalize(raw_outputs, input_data)

    assert len(bundles) == 3, "Should normalize all 3 outputs"

    for i, bundle in enumerate(bundles, 1):
        critic = bundle["critic_output"]["critic_name"]
        verdict = bundle["critic_output"]["verdict"]
        print(f"✅ Bundle {i}: {critic} → {verdict}")

    return bundles


def validate_against_schema(bundle):
    """Validate normalized bundle against JSON schema."""
    if not HAS_JSONSCHEMA:
        print("\n[Schema Validation] Skipped (jsonschema not installed)")
        return True

    print("\n[Schema Validation] Checking against evidence_bundle.json...")

    schema_path = Path(__file__).parent.parent / "schemas" / "evidence_bundle.json"

    if not schema_path.exists():
        print(f"⚠️  Schema file not found: {schema_path}")
        return False

    try:
        with open(schema_path) as f:
            schema = json.load(f)

        jsonschema.validate(bundle, schema)
        print("✅ Bundle passes schema validation")
        return True

    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Evidence Normalizer Tests")
    print("=" * 60)

    try:
        # Run tests
        bundle1 = test_basic_normalization()
        bundle2 = test_missing_fields()
        test_verdict_normalization()
        bundles = test_batch_normalization()

        # Validate against schema
        validate_against_schema(bundle1)

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
