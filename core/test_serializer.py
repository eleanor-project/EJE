#!/usr/bin/env python3
"""
Test Evidence Serializer.

Validates serialization, deserialization, and validation functionality.
"""

import json
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evidence_serializer import (
    EvidenceSerializer,
    ValidationError,
    DeserializationError,
    to_json,
    from_json,
    to_file,
    from_file
)


def create_valid_bundle() -> dict:
    """Create a valid test bundle."""
    return {
        "bundle_id": "test-001",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test case passes all checks."
        },
        "metadata": {
            "timestamp": "2025-12-04T10:00:00Z",
            "critic_name": "TestCritic",
            "config_version": "1.0"
        },
        "input_snapshot": {
            "prompt": "Test input"
        }
    }


def test_serialization():
    """Test to_json()."""
    print("\n[Test 1] Serialization (to_json)...")

    serializer = EvidenceSerializer()
    bundle = create_valid_bundle()

    json_str = serializer.to_json(bundle, validate=True)

    assert isinstance(json_str, str), "Should return string"
    assert "bundle_id" in json_str, "Should contain bundle_id"
    assert "TestCritic" in json_str, "Should contain critic name"

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["bundle_id"] == "test-001"

    print("✅ Bundle serialized to JSON")
    print(f"✅ JSON length: {len(json_str)} characters")

    return json_str


def test_deserialization():
    """Test from_json()."""
    print("\n[Test 2] Deserialization (from_json)...")

    serializer = EvidenceSerializer()
    bundle = create_valid_bundle()

    # Serialize then deserialize
    json_str = serializer.to_json(bundle)
    restored = serializer.from_json(json_str, validate=True)

    assert restored["bundle_id"] == bundle["bundle_id"]
    assert restored["critic_output"]["verdict"] == "ALLOW"
    assert restored["metadata"]["critic_name"] == "TestCritic"

    print("✅ Bundle deserialized from JSON")
    print(f"✅ Bundle ID: {restored['bundle_id']}")

    return restored


def test_file_operations():
    """Test to_file() and from_file()."""
    print("\n[Test 3] File operations...")

    serializer = EvidenceSerializer()
    bundle = create_valid_bundle()

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        serializer.to_file(bundle, temp_path, validate=True)
        print(f"✅ Wrote to file: {temp_path}")

        # Read back
        restored = serializer.from_file(temp_path, validate=True)
        assert restored["bundle_id"] == bundle["bundle_id"]

        print("✅ Read from file successfully")

        return restored
    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)


def test_validation_missing_field():
    """Test validation error for missing field."""
    print("\n[Test 4] Validation - missing field...")

    serializer = EvidenceSerializer()

    invalid_bundle = {
        "bundle_id": "test-invalid",
        "version": "1.0",
        # Missing critic_output
        "metadata": {
            "timestamp": "2025-12-04T10:00:00Z",
            "critic_name": "Test",
            "config_version": "1.0"
        },
        "input_snapshot": {
            "prompt": "Test"
        }
    }

    try:
        serializer.to_json(invalid_bundle, validate=True)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"✅ Caught expected error: {e}")
        assert "critic_output" in str(e)

    return True


def test_validation_invalid_verdict():
    """Test validation error for invalid verdict."""
    print("\n[Test 5] Validation - invalid verdict...")

    serializer = EvidenceSerializer()

    bundle = create_valid_bundle()
    bundle["critic_output"]["verdict"] = "INVALID_VERDICT"

    try:
        serializer.to_json(bundle, validate=True)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"✅ Caught expected error: {e}")
        assert "verdict" in str(e).lower()

    return True


def test_validation_invalid_confidence():
    """Test validation error for out-of-range confidence."""
    print("\n[Test 6] Validation - invalid confidence...")

    serializer = EvidenceSerializer()

    bundle = create_valid_bundle()
    bundle["critic_output"]["confidence"] = 1.5  # Out of range

    try:
        serializer.to_json(bundle, validate=True)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"✅ Caught expected error: {e}")
        assert "confidence" in str(e).lower()

    return True


def test_batch_serialization():
    """Test batch serialization."""
    print("\n[Test 7] Batch serialization...")

    serializer = EvidenceSerializer()

    bundles = [
        create_valid_bundle(),
        create_valid_bundle(),
        create_valid_bundle()
    ]

    # Update bundle IDs
    for i, bundle in enumerate(bundles):
        bundle["bundle_id"] = f"test-batch-{i+1}"

    json_str = serializer.batch_to_json(bundles, validate=True)
    assert "[" in json_str, "Should be JSON array"

    restored = serializer.batch_from_json(json_str, validate=True)
    assert len(restored) == 3, "Should have 3 bundles"

    print(f"✅ Serialized {len(bundles)} bundles to array")
    print(f"✅ Deserialized {len(restored)} bundles from array")

    return restored


def test_convenience_functions():
    """Test convenience functions."""
    print("\n[Test 8] Convenience functions...")

    bundle = create_valid_bundle()

    # Test to_json/from_json
    json_str = to_json(bundle, validate=True)
    restored = from_json(json_str, validate=True)
    assert restored["bundle_id"] == bundle["bundle_id"]

    print("✅ to_json() and from_json() work")

    # Test to_file/from_file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        to_file(bundle, temp_path, validate=True)
        restored = from_file(temp_path, validate=True)
        assert restored["bundle_id"] == bundle["bundle_id"]

        print("✅ to_file() and from_file() work")
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return True


def test_invalid_json():
    """Test deserialization of invalid JSON."""
    print("\n[Test 9] Invalid JSON handling...")

    serializer = EvidenceSerializer()

    invalid_json = "{ invalid json }"

    try:
        serializer.from_json(invalid_json)
        assert False, "Should have raised DeserializationError"
    except DeserializationError as e:
        print(f"✅ Caught expected error: {e}")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Evidence Serializer Tests")
    print("=" * 60)

    try:
        test_serialization()
        test_deserialization()
        test_file_operations()
        test_validation_missing_field()
        test_validation_invalid_verdict()
        test_validation_invalid_confidence()
        test_batch_serialization()
        test_convenience_functions()
        test_invalid_json()

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
