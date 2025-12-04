#!/usr/bin/env python3
"""
Test Precedent Ingestion Pipeline.

Task 3.2: Test suite for automatic precedent ingestion.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.precedent_storage import PrecedentStorage
from core.precedent_ingestion import (
    PrecedentIngestionPipeline,
    IngestionConfig,
    create_ingestion_pipeline
)
from core.critic_aggregator import AggregationResult


def create_test_evidence_bundle(critic_name: str, verdict: str, confidence: float) -> dict:
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


def create_test_aggregation_result(verdict: str, confidence: float) -> AggregationResult:
    """Create a test aggregation result."""
    return AggregationResult(
        final_verdict=verdict,
        confidence=confidence,
        weighted_scores={verdict: confidence},
        contributing_critics=["TestCritic1", "TestCritic2"],
        total_weight=2.0,
        conflicts_detected=[]
    )


def test_basic_ingestion():
    """Test basic ingestion of a decision."""
    print("\n[Test 1] Basic ingestion...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        pipeline = PrecedentIngestionPipeline(storage)

        query = "User requests to delete their account"
        evidence_bundles = [
            create_test_evidence_bundle("PrivacyCritic", "ALLOW", 0.9),
            create_test_evidence_bundle("SafetyCritic", "ALLOW", 0.85)
        ]
        aggregation_result = create_test_aggregation_result("ALLOW", 0.9)

        precedent_id = pipeline.ingest_decision(
            query, evidence_bundles, aggregation_result
        )

        assert precedent_id is not None, "Should return precedent ID"
        assert precedent_id.startswith("prec-"), "ID should have prec- prefix"

        # Verify stored
        precedent = storage.get_precedent(precedent_id)
        assert precedent is not None, "Should be stored"
        assert precedent["query"] == query
        assert precedent["decision"] == "ALLOW"
        assert precedent["confidence"] == 0.9

        print(f"✅ Ingested precedent: {precedent_id}")
        print(f"✅ Query: {query[:50]}...")
        print(f"✅ Decision: {precedent['decision']}")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_confidence_filtering():
    """Test filtering by minimum confidence."""
    print("\n[Test 2] Confidence filtering...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        config = IngestionConfig(min_confidence=0.8)
        pipeline = PrecedentIngestionPipeline(storage, config)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("Critic1", "ALLOW", 0.7)]

        # Low confidence - should be skipped
        result_low = create_test_aggregation_result("ALLOW", 0.7)
        id_low = pipeline.ingest_decision(query, evidence_bundles, result_low)
        assert id_low is None, "Should skip low confidence"

        # High confidence - should be stored
        result_high = create_test_aggregation_result("ALLOW", 0.9)
        id_high = pipeline.ingest_decision(query, evidence_bundles, result_high)
        assert id_high is not None, "Should store high confidence"

        print("✅ Low confidence (0.7) skipped")
        print("✅ High confidence (0.9) stored")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_verdict_filtering():
    """Test filtering by verdict type."""
    print("\n[Test 3] Verdict filtering...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        config = IngestionConfig(allowed_verdicts=["ALLOW", "DENY"])
        pipeline = PrecedentIngestionPipeline(storage, config)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("Critic1", "ALLOW", 0.9)]

        # ALLOW - should be stored
        result_allow = create_test_aggregation_result("ALLOW", 0.9)
        id_allow = pipeline.ingest_decision(query, evidence_bundles, result_allow)
        assert id_allow is not None, "Should store ALLOW"

        # ESCALATE - should be skipped
        result_escalate = create_test_aggregation_result("ESCALATE", 0.9)
        id_escalate = pipeline.ingest_decision(query, evidence_bundles, result_escalate)
        assert id_escalate is None, "Should skip ESCALATE"

        print("✅ ALLOW verdict stored")
        print("✅ ESCALATE verdict skipped")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_skip_escalations():
    """Test skipping escalations."""
    print("\n[Test 4] Skip escalations...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        config = IngestionConfig(skip_escalations=True)
        pipeline = PrecedentIngestionPipeline(storage, config)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("Critic1", "ESCALATE", 0.9)]
        result = create_test_aggregation_result("ESCALATE", 0.9)

        precedent_id = pipeline.ingest_decision(query, evidence_bundles, result)
        assert precedent_id is None, "Should skip ESCALATE"

        print("✅ ESCALATE verdict skipped")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_composite_bundle():
    """Test composite bundle generation."""
    print("\n[Test 5] Composite bundle generation...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        pipeline = PrecedentIngestionPipeline(storage)

        query = "Multi-critic decision"
        evidence_bundles = [
            create_test_evidence_bundle("PrivacyCritic", "ALLOW", 0.9),
            create_test_evidence_bundle("SafetyCritic", "ALLOW", 0.85),
            create_test_evidence_bundle("EquityCritic", "ALLOW", 0.88)
        ]
        aggregation_result = AggregationResult(
            final_verdict="ALLOW",
            confidence=0.88,
            weighted_scores={"ALLOW": 2.63},
            contributing_critics=["PrivacyCritic", "SafetyCritic", "EquityCritic"],
            total_weight=3.0,
            conflicts_detected=[]
        )

        precedent_id = pipeline.ingest_decision(
            query, evidence_bundles, aggregation_result
        )

        # Retrieve and check composite bundle
        precedent = storage.get_precedent(precedent_id)
        assert precedent is not None

        composite = precedent["evidence_bundle"]
        assert composite["critic_output"]["critic_name"] == "AggregatedCritics"
        assert composite["critic_output"]["verdict"] == "ALLOW"
        assert "aggregation_metadata" in composite["critic_output"]

        metadata = composite["critic_output"]["aggregation_metadata"]
        assert len(metadata["contributing_critics"]) == 3
        assert len(metadata["individual_bundles"]) == 3
        assert metadata["total_weight"] == 3.0

        print("✅ Composite bundle created")
        print(f"✅ Aggregated {len(metadata['contributing_critics'])} critics")
        print(f"✅ Total weight: {metadata['total_weight']}")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_batch_ingestion():
    """Test batch ingestion of multiple decisions."""
    print("\n[Test 6] Batch ingestion...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        pipeline = PrecedentIngestionPipeline(storage)

        decisions = [
            {
                "query": "Query 1",
                "evidence_bundles": [create_test_evidence_bundle("C1", "ALLOW", 0.9)],
                "aggregation_result": create_test_aggregation_result("ALLOW", 0.9),
                "metadata": {"batch": 1}
            },
            {
                "query": "Query 2",
                "evidence_bundles": [create_test_evidence_bundle("C2", "DENY", 0.85)],
                "aggregation_result": create_test_aggregation_result("DENY", 0.85),
                "metadata": {"batch": 1}
            },
            {
                "query": "Query 3",
                "evidence_bundles": [create_test_evidence_bundle("C3", "ALLOW", 0.88)],
                "aggregation_result": create_test_aggregation_result("ALLOW", 0.88),
                "metadata": {"batch": 1}
            }
        ]

        precedent_ids = pipeline.ingest_batch(decisions)

        assert len(precedent_ids) == 3, "Should return 3 IDs"
        assert all(id is not None for id in precedent_ids), "All should be stored"

        # Verify all stored
        count = storage.count_precedents()
        assert count == 3, "Should have 3 precedents"

        print(f"✅ Batch ingested {len(precedent_ids)} decisions")
        print(f"✅ Total stored: {count}")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_ingestion_hooks():
    """Test ingestion hooks."""
    print("\n[Test 7] Ingestion hooks...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        pipeline = PrecedentIngestionPipeline(storage)

        # Track hook calls
        hook_calls = []

        def test_hook(precedent_id, query, aggregation_result):
            hook_calls.append({
                "id": precedent_id,
                "query": query,
                "verdict": aggregation_result.final_verdict
            })

        pipeline.add_ingestion_hook(test_hook)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
        result = create_test_aggregation_result("ALLOW", 0.9)

        pipeline.ingest_decision(query, evidence_bundles, result)

        assert len(hook_calls) == 1, "Hook should be called once"
        assert hook_calls[0]["query"] == query
        assert hook_calls[0]["verdict"] == "ALLOW"

        print("✅ Hook called successfully")
        print(f"✅ Hook received: {hook_calls[0]['id']}")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_disabled_ingestion():
    """Test disabled ingestion."""
    print("\n[Test 8] Disabled ingestion...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        config = IngestionConfig(enabled=False)
        pipeline = PrecedentIngestionPipeline(storage, config)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
        result = create_test_aggregation_result("ALLOW", 0.9)

        precedent_id = pipeline.ingest_decision(query, evidence_bundles, result)
        assert precedent_id is None, "Should return None when disabled"

        count = storage.count_precedents()
        assert count == 0, "Should not store anything"

        print("✅ Ingestion disabled, nothing stored")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_metadata_enrichment():
    """Test metadata enrichment."""
    print("\n[Test 9] Metadata enrichment...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        pipeline = PrecedentIngestionPipeline(storage)

        query = "Test query"
        evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
        result = create_test_aggregation_result("ALLOW", 0.9)
        additional_metadata = {
            "jurisdiction": "EU",
            "domain": "healthcare",
            "user_id": "user-123"
        }

        precedent_id = pipeline.ingest_decision(
            query, evidence_bundles, result, additional_metadata
        )

        # Retrieve and check metadata
        precedent = storage.get_precedent(precedent_id)
        metadata = precedent["metadata"]

        assert "jurisdiction" in metadata, "Should include additional metadata"
        assert metadata["jurisdiction"] == "EU"
        assert metadata["ingestion_source"] == "aggregator"
        assert metadata["num_critics"] == 2

        print("✅ Metadata enriched")
        print(f"✅ Jurisdiction: {metadata['jurisdiction']}")
        print(f"✅ Source: {metadata['ingestion_source']}")

        return pipeline
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 10] Convenience function...")

    pipeline = create_ingestion_pipeline()

    assert pipeline is not None, "Should create pipeline"
    assert pipeline.storage is not None, "Should have storage"
    assert pipeline.config is not None, "Should have config"

    print("✅ Convenience function works")

    return pipeline


def main():
    """Run all tests."""
    print("=" * 60)
    print("Precedent Ingestion Pipeline Tests (Task 3.2)")
    print("=" * 60)

    try:
        test_basic_ingestion()
        test_confidence_filtering()
        test_verdict_filtering()
        test_skip_escalations()
        test_composite_bundle()
        test_batch_ingestion()
        test_ingestion_hooks()
        test_disabled_ingestion()
        test_metadata_enrichment()
        test_convenience_function()

        print("\n" + "=" * 60)
        print("✅ All 10 tests passed!")
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
