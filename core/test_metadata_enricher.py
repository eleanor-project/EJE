#!/usr/bin/env python3
"""
Test the Metadata Enricher.

Validates metadata enrichment and timing functionality.
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.metadata_enricher import MetadataEnricher, ExecutionTimer, enrich_bundle_metadata


def test_basic_enrichment():
    """Test basic metadata enrichment."""
    print("\n[Test 1] Basic metadata enrichment...")

    enricher = MetadataEnricher({"config_version": "2.1.0"})

    bundle = {
        "bundle_id": "test-001",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test"
        },
        "metadata": {
            "critic_name": "TestCritic"
        },
        "input_snapshot": {
            "prompt": "Test"
        }
    }

    enricher.enrich(bundle)

    metadata = bundle["metadata"]

    # Check required metadata
    assert "timestamp" in metadata, "Missing timestamp"
    assert "config_version" in metadata, "Missing config_version"
    assert "aggregator_run_id" in metadata, "Missing aggregator_run_id"
    assert "trace_id" in metadata, "Missing trace_id"
    assert "system_info" in metadata, "Missing system_info"

    print(f"✅ Timestamp: {metadata['timestamp']}")
    print(f"✅ Config version: {metadata['config_version']}")
    print(f"✅ Aggregator run ID: {metadata['aggregator_run_id']}")
    print(f"✅ Trace ID: {metadata['trace_id'][:30]}...")
    print(f"✅ System info: {metadata['system_info']}")

    return bundle


def test_execution_timing():
    """Test execution timing enrichment."""
    print("\n[Test 2] Execution timing...")

    enricher = MetadataEnricher()

    bundle = {
        "bundle_id": "test-002",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test"
        },
        "metadata": {"critic_name": "TestCritic"},
        "input_snapshot": {"prompt": "Test"}
    }

    # Simulate execution time
    start_time = time.time()
    time.sleep(0.05)  # 50ms

    enricher.enrich(bundle, execution_start_time=start_time)

    execution_time = bundle["metadata"]["execution_time_ms"]
    assert execution_time > 0, "Execution time should be non-zero"
    assert execution_time >= 50, f"Execution time should be >= 50ms, got {execution_time}"

    print(f"✅ Execution time: {execution_time:.2f}ms")

    return bundle


def test_execution_timer_context():
    """Test ExecutionTimer context manager."""
    print("\n[Test 3] ExecutionTimer context manager...")

    with ExecutionTimer() as timer:
        time.sleep(0.03)  # 30ms

    elapsed = timer.elapsed_ms
    assert elapsed >= 30, f"Elapsed time should be >= 30ms, got {elapsed}"

    print(f"✅ Timer measured: {elapsed:.2f}ms")
    print(f"✅ Start timestamp: {timer.start_timestamp}")

    return True


def test_batch_enrichment():
    """Test batch enrichment with shared run ID."""
    print("\n[Test 4] Batch enrichment...")

    enricher = MetadataEnricher()

    bundles = [
        {
            "bundle_id": f"test-batch-{i}",
            "version": "1.0",
            "critic_output": {
                "critic_name": f"Critic{i}",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "Test"
            },
            "metadata": {"critic_name": f"Critic{i}"},
            "input_snapshot": {"prompt": "Test"}
        }
        for i in range(3)
    ]

    # Enrich with shared run ID
    enricher.enrich_batch(bundles, aggregator_run_id="test-run-123")

    # All should have same run ID
    run_ids = [b["metadata"]["aggregator_run_id"] for b in bundles]
    assert all(rid == "test-run-123" for rid in run_ids), "All should share run ID"

    # All should have timestamps
    timestamps = [b["metadata"]["timestamp"] for b in bundles]
    assert all(timestamps), "All should have timestamps"

    print(f"✅ Enriched {len(bundles)} bundles")
    print(f"✅ Shared run ID: {run_ids[0]}")
    print(f"✅ Timestamps: {len(timestamps)}")

    return bundles


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 5] Convenience function...")

    bundle = {
        "bundle_id": "test-005",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test"
        },
        "metadata": {"critic_name": "TestCritic"},
        "input_snapshot": {"prompt": "Test"}
    }

    start_time = time.time()
    time.sleep(0.02)

    enriched = enrich_bundle_metadata(
        bundle,
        execution_start=start_time,
        request_id="req-123",
        config={"config_version": "3.0"}
    )

    assert enriched["metadata"]["request_id"] == "req-123", "Should have request ID"
    assert enriched["metadata"]["config_version"] == "3.0", "Should have config version"
    assert enriched["metadata"]["execution_time_ms"] >= 20, "Should have timing"

    print(f"✅ Request ID: {enriched['metadata']['request_id']}")
    print(f"✅ Config version: {enriched['metadata']['config_version']}")
    print(f"✅ Execution time: {enriched['metadata']['execution_time_ms']:.2f}ms")

    return enriched


def test_timestamp_format():
    """Test timestamp format compliance."""
    print("\n[Test 6] Timestamp format...")

    enricher = MetadataEnricher()

    bundle = {
        "bundle_id": "test-006",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Test"
        },
        "metadata": {},
        "input_snapshot": {"prompt": "Test"}
    }

    enricher.enrich(bundle)

    timestamp = bundle["metadata"]["timestamp"]

    # Check format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    assert "T" in timestamp, "Should have T separator"
    assert timestamp.endswith("Z"), "Should end with Z"
    assert "." in timestamp, "Should have microseconds"

    print(f"✅ Timestamp format: {timestamp}")
    print(f"✅ Format validated: ISO 8601 with microseconds")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Metadata Enricher Tests")
    print("=" * 60)

    try:
        test_basic_enrichment()
        test_execution_timing()
        test_execution_timer_context()
        test_batch_enrichment()
        test_convenience_function()
        test_timestamp_format()

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
