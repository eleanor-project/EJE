#!/usr/bin/env python3
"""
Comprehensive Evidence Bundle Test Suite

Task 1.5: Write EvidenceBundle Unit Tests

Tests normalization, serialization, schema compliance, and integration
between all evidence bundle components.
"""

import json
import time
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evidence_normalizer import EvidenceNormalizer, normalize_critic_output
from core.metadata_enricher import MetadataEnricher, ExecutionTimer, enrich_bundle_metadata
from core.evidence_serializer import (
    EvidenceSerializer,
    ValidationError,
    DeserializationError,
    to_json,
    from_json
)

# Test counters
tests_passed = 0
tests_failed = 0


def test_result(test_name: str, passed: bool, error: str = ""):
    """Track test result."""
    global tests_passed, tests_failed

    if passed:
        tests_passed += 1
        print(f"✅ {test_name}")
    else:
        tests_failed += 1
        print(f"❌ {test_name}")
        if error:
            print(f"   Error: {error}")


def test_schema_validation_positive():
    """Positive test: Valid bundle passes schema validation."""
    print("\n[Positive Tests - Schema Validation]")

    try:
        serializer = EvidenceSerializer()

        bundle = {
            "bundle_id": "test-schema-001",
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

        serializer.validate(bundle)
        test_result("Valid bundle passes validation", True)

    except Exception as e:
        test_result("Valid bundle passes validation", False, str(e))


def test_schema_validation_negative():
    """Negative tests: Invalid bundles fail schema validation."""
    print("\n[Negative Tests - Schema Validation]")

    serializer = EvidenceSerializer()

    # Test 1: Missing required field
    try:
        bundle = {"bundle_id": "test", "version": "1.0"}  # Missing other fields
        serializer.validate(bundle)
        test_result("Missing fields detected", False, "Should have raised ValidationError")
    except ValidationError:
        test_result("Missing fields detected", True)

    # Test 2: Invalid verdict
    try:
        bundle = {
            "bundle_id": "test",
            "version": "1.0",
            "critic_output": {
                "critic_name": "Test",
                "verdict": "INVALID",
                "confidence": 0.5,
                "justification": "Test"
            },
            "metadata": {
                "timestamp": "2025-12-04T10:00:00Z",
                "critic_name": "Test",
                "config_version": "1.0"
            },
            "input_snapshot": {"prompt": "Test"}
        }
        serializer.validate(bundle)
        test_result("Invalid verdict detected", False, "Should have raised ValidationError")
    except ValidationError:
        test_result("Invalid verdict detected", True)

    # Test 3: Confidence out of range
    try:
        bundle = {
            "bundle_id": "test",
            "version": "1.0",
            "critic_output": {
                "critic_name": "Test",
                "verdict": "ALLOW",
                "confidence": 2.0,  # Out of range
                "justification": "Test"
            },
            "metadata": {
                "timestamp": "2025-12-04T10:00:00Z",
                "critic_name": "Test",
                "config_version": "1.0"
            },
            "input_snapshot": {"prompt": "Test"}
        }
        serializer.validate(bundle)
        test_result("Confidence out of range detected", False, "Should have raised ValidationError")
    except ValidationError:
        test_result("Confidence out of range detected", True)


def test_normalization_edge_cases():
    """Test normalization with various edge cases."""
    print("\n[Edge Cases - Normalization]")

    normalizer = EvidenceNormalizer()

    # Test 1: Different field names
    try:
        raw = {
            "name": "TestCritic",  # Different from critic_name
            "decision": "APPROVE",  # Maps to ALLOW
            "score": 0.85,  # Different from confidence
            "reasoning": "Test reasoning"  # Different from justification
        }
        input_data = {"text": "Test input"}  # Different from prompt

        bundle = normalizer.normalize(raw, input_data)
        assert bundle["critic_output"]["critic_name"] == "TestCritic"
        assert bundle["critic_output"]["verdict"] == "ALLOW"
        assert bundle["critic_output"]["confidence"] == 0.85

        test_result("Alternative field names handled", True)
    except Exception as e:
        test_result("Alternative field names handled", False, str(e))

    # Test 2: Missing optional fields
    try:
        raw = {
            "critic_name": "MinimalCritic",
            "verdict": "DENY",
            # No confidence, no justification
        }
        input_data = {"prompt": "Minimal test"}

        bundle = normalizer.normalize(raw, input_data)
        assert "confidence" in bundle["critic_output"]  # Auto-filled
        assert "justification" in bundle["critic_output"]  # Auto-generated

        test_result("Missing fields auto-filled", True)
    except Exception as e:
        test_result("Missing fields auto-filled", False, str(e))

    # Test 3: Verdict normalization
    try:
        test_verdicts = {
            "APPROVE": "ALLOW",
            "reject": "DENY",
            "MANUAL_REVIEW": "ESCALATE",
            "skip": "ABSTAIN"
        }

        for raw_verdict, expected in test_verdicts.items():
            raw = {
                "critic_name": "Test",
                "verdict": raw_verdict,
                "confidence": 0.8,
                "justification": "Test"
            }
            bundle = normalizer.normalize(raw, {"prompt": "Test"})
            assert bundle["critic_output"]["verdict"] == expected

        test_result("Verdict normalization works", True)
    except Exception as e:
        test_result("Verdict normalization works", False, str(e))

    # Test 4: Confidence normalization (percentage to decimal)
    try:
        raw = {
            "critic_name": "Test",
            "verdict": "ALLOW",
            "confidence": 85,  # Percentage
            "justification": "Test"
        }
        bundle = normalizer.normalize(raw, {"prompt": "Test"})
        assert 0.0 <= bundle["critic_output"]["confidence"] <= 1.0

        test_result("Percentage confidence normalized", True)
    except Exception as e:
        test_result("Percentage confidence normalized", False, str(e))


def test_metadata_enrichment():
    """Test metadata enrichment functionality."""
    print("\n[Metadata Enrichment]")

    enricher = MetadataEnricher({"config_version": "2.0"})

    # Test 1: Basic enrichment
    try:
        bundle = {
            "bundle_id": "test",
            "version": "1.0",
            "critic_output": {
                "critic_name": "Test",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "Test"
            },
            "metadata": {},
            "input_snapshot": {"prompt": "Test"}
        }

        enricher.enrich(bundle)

        assert "timestamp" in bundle["metadata"]
        assert "config_version" in bundle["metadata"]
        assert "aggregator_run_id" in bundle["metadata"]
        assert "trace_id" in bundle["metadata"]
        assert "system_info" in bundle["metadata"]

        test_result("Basic metadata enrichment", True)
    except Exception as e:
        test_result("Basic metadata enrichment", False, str(e))

    # Test 2: Execution timing
    try:
        bundle = {
            "bundle_id": "test",
            "version": "1.0",
            "critic_output": {
                "critic_name": "Test",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "Test"
            },
            "metadata": {},
            "input_snapshot": {"prompt": "Test"}
        }

        start_time = time.time()
        time.sleep(0.01)  # 10ms

        enricher.enrich(bundle, execution_start_time=start_time)

        exec_time = bundle["metadata"]["execution_time_ms"]
        assert exec_time >= 10

        test_result("Execution timing works", True)
    except Exception as e:
        test_result("Execution timing works", False, str(e))

    # Test 3: Batch enrichment with shared run ID
    try:
        bundles = [
            {
                "bundle_id": f"test-{i}",
                "version": "1.0",
                "critic_output": {
                    "critic_name": f"Critic{i}",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test"
                },
                "metadata": {},
                "input_snapshot": {"prompt": "Test"}
            }
            for i in range(3)
        ]

        enricher.enrich_batch(bundles, aggregator_run_id="shared-run-123")

        run_ids = [b["metadata"]["aggregator_run_id"] for b in bundles]
        assert all(rid == "shared-run-123" for rid in run_ids)

        test_result("Batch enrichment with shared run ID", True)
    except Exception as e:
        test_result("Batch enrichment with shared run ID", False, str(e))


def test_serialization_round_trip():
    """Test full serialization round-trip."""
    print("\n[Serialization Round-Trip]")

    try:
        # Create bundle through full pipeline
        normalizer = EvidenceNormalizer()
        enricher = MetadataEnricher()
        serializer = EvidenceSerializer()

        # Normalize
        raw = {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.92,
            "justification": "Test case passes all security checks."
        }
        input_data = {"prompt": "Test security evaluation"}

        bundle = normalizer.normalize(raw, input_data)

        # Enrich
        start_time = time.time()
        enricher.enrich(bundle, execution_start_time=start_time, request_id="req-test-001")

        # Serialize
        json_str = serializer.to_json(bundle, validate=True)

        # Deserialize
        restored = serializer.from_json(json_str, validate=True)

        # Verify
        assert restored["bundle_id"] == bundle["bundle_id"]
        assert restored["critic_output"]["verdict"] == "ALLOW"
        assert restored["metadata"]["request_id"] == "req-test-001"

        test_result("Full normalization → enrichment → serialization → deserialization", True)
    except Exception as e:
        test_result("Full normalization → enrichment → serialization → deserialization", False, str(e))


def test_integration_workflow():
    """Test complete integration workflow."""
    print("\n[Integration Workflow]")

    try:
        # Simulate multi-critic evaluation
        critics_raw_output = [
            {
                "name": "PrivacyCritic",
                "decision": "ALLOW",
                "score": 0.95,
                "reasoning": "Privacy requirements met."
            },
            {
                "name": "SafetyCritic",
                "decision": "ESCALATE",
                "score": 0.75,
                "reasoning": "Requires human safety review."
            },
            {
                "name": "EquityCritic",
                "decision": "ALLOW",
                "score": 0.88,
                "reasoning": "No equity concerns detected."
            }
        ]

        input_data = {
            "prompt": "User requests to publish sensitive content",
            "context": {
                "jurisdiction": "EU",
                "domain": "social_media"
            }
        }

        normalizer = EvidenceNormalizer()
        enricher = MetadataEnricher()
        serializer = EvidenceSerializer()

        # Process each critic output
        bundles = []
        execution_times = {}

        for raw in critics_raw_output:
            # Time execution
            start = time.time()

            # Normalize
            bundle = normalizer.normalize(raw, input_data)

            execution_times[bundle["bundle_id"]] = start
            bundles.append(bundle)

        # Enrich all with shared run ID
        enricher.enrich_batch(
            bundles,
            execution_times=execution_times,
            aggregator_run_id="agg-integration-test",
            request_id="req-integration-001"
        )

        # Validate all
        for bundle in bundles:
            serializer.validate(bundle)

        # Serialize batch
        batch_json = serializer.batch_to_json(bundles, validate=True)

        # Deserialize batch
        restored_bundles = serializer.batch_from_json(batch_json, validate=True)

        assert len(restored_bundles) == 3
        assert all("execution_time_ms" in b["metadata"] for b in restored_bundles)

        test_result("Multi-critic integration workflow", True)
    except Exception as e:
        test_result("Multi-critic integration workflow", False, str(e))


def test_file_persistence():
    """Test file persistence across components."""
    print("\n[File Persistence]")

    try:
        normalizer = EvidenceNormalizer()
        enricher = MetadataEnricher()
        serializer = EvidenceSerializer()

        # Create bundle
        raw = {
            "critic_name": "FilePersistenceTest",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test file persistence"
        }
        bundle = normalizer.normalize(raw, {"prompt": "Test"})
        enricher.enrich(bundle)

        # Write to file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            serializer.to_file(bundle, temp_path, validate=True)

            # Read back
            restored = serializer.from_file(temp_path, validate=True)

            assert restored["bundle_id"] == bundle["bundle_id"]
            assert restored["critic_output"]["critic_name"] == "FilePersistenceTest"

            test_result("File write → read → validate", True)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    except Exception as e:
        test_result("File write → read → validate", False, str(e))


def main():
    """Run all tests."""
    global tests_passed, tests_failed

    print("=" * 60)
    print("Comprehensive Evidence Bundle Test Suite")
    print("=" * 60)

    try:
        # Run all test suites
        test_schema_validation_positive()
        test_schema_validation_negative()
        test_normalization_edge_cases()
        test_metadata_enrichment()
        test_serialization_round_trip()
        test_integration_workflow()
        test_file_persistence()

        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"✅ Passed: {tests_passed}")
        print(f"❌ Failed: {tests_failed}")
        print(f"Total: {tests_passed + tests_failed}")

        if tests_failed == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n⚠️  {tests_failed} test(s) failed")
            return False

    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
