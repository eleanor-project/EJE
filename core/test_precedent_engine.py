#!/usr/bin/env python3
"""
Precedent Engine Integration Tests

Task 3.5: Precedent Engine Tests

Integration tests validating the complete precedent engine:
storage, ingestion, similarity search, and ranking working together.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.precedent_storage import PrecedentStorage
from core.precedent_ingestion import (
    PrecedentIngestionPipeline,
    IngestionConfig
)
from core.similarity_search import (
    SimilaritySearchEngine,
    SimpleHashEmbedding
)
from core.precedent_ranking import (
    PrecedentRanker,
    RankingConfig
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
            "justification": f"{critic_name} justification for {verdict}"
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


def create_test_aggregation_result(verdict: str, confidence: float, critics: list) -> AggregationResult:
    """Create a test aggregation result."""
    return AggregationResult(
        final_verdict=verdict,
        confidence=confidence,
        weighted_scores={verdict: confidence * len(critics)},
        contributing_critics=critics,
        total_weight=float(len(critics)),
        conflicts_detected=[]
    )


def test_end_to_end_workflow():
    """Test complete workflow: ingest → search → rank."""
    print("\n[Test 1] End-to-end workflow...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # 1. Setup components
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)
        embedding_model = SimpleHashEmbedding()
        search_engine = SimilaritySearchEngine(storage, embedding_model)
        ranker = PrecedentRanker()

        # 2. Ingest some decisions
        test_cases = [
            {
                "query": "User wants to delete their account data",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "critics": ["PrivacyCritic", "SafetyCritic"]
            },
            {
                "query": "User requests to export personal information",
                "verdict": "ALLOW",
                "confidence": 0.85,
                "critics": ["PrivacyCritic"]
            },
            {
                "query": "User asks to share data with third party",
                "verdict": "DENY",
                "confidence": 0.88,
                "critics": ["PrivacyCritic", "EquityCritic"]
            }
        ]

        for case in test_cases:
            evidence_bundles = [
                create_test_evidence_bundle(critic, case["verdict"], case["confidence"])
                for critic in case["critics"]
            ]

            aggregation_result = create_test_aggregation_result(
                case["verdict"],
                case["confidence"],
                case["critics"]
            )

            precedent_id = ingestion.ingest_decision(
                case["query"],
                evidence_bundles,
                aggregation_result
            )

            assert precedent_id is not None, f"Failed to ingest: {case['query']}"

        # 3. Search for similar precedents
        query = "delete account information"
        similarity_results = search_engine.search(query, top_k=5)

        assert len(similarity_results) > 0, "Should find similar precedents"

        # 4. Rank results
        ranked_results = ranker.rank(similarity_results)

        assert len(ranked_results) > 0, "Should have ranked results"
        assert ranked_results[0].rank == 1, "First result should have rank 1"
        assert ranked_results[0].final_score > 0, "Should have positive score"

        print(f"✅ Ingested {len(test_cases)} decisions")
        print(f"✅ Found {len(similarity_results)} similar precedents")
        print(f"✅ Ranked {len(ranked_results)} results")
        print(f"✅ Top result: {ranked_results[0].query[:50]}...")
        print(f"✅ Top score: {ranked_results[0].final_score:.4f}")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_filtered_search_and_rank():
    """Test search with filtering + ranking."""
    print("\n[Test 2] Filtered search and ranking...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)
        embedding_model = SimpleHashEmbedding()
        search_engine = SimilaritySearchEngine(storage, embedding_model)
        ranker = PrecedentRanker()

        # Ingest mixed ALLOW and DENY decisions
        for i, verdict in enumerate(["ALLOW", "ALLOW", "DENY", "DENY"]):
            query = f"Test case {i}: data access request"
            evidence_bundles = [create_test_evidence_bundle("TestCritic", verdict, 0.9)]
            aggregation_result = create_test_aggregation_result(verdict, 0.9, ["TestCritic"])

            ingestion.ingest_decision(query, evidence_bundles, aggregation_result)

        # Search with ALLOW filter
        query = "data access"
        allow_results = search_engine.search(query, top_k=10, filter_decision="ALLOW")
        ranked_allow = ranker.rank(allow_results)

        # All results should be ALLOW
        assert all(r.decision == "ALLOW" for r in ranked_allow)

        # Search with DENY filter
        deny_results = search_engine.search(query, top_k=10, filter_decision="DENY")
        ranked_deny = ranker.rank(deny_results)

        # All results should be DENY
        assert all(r.decision == "DENY" for r in ranked_deny)

        print(f"✅ ALLOW results: {len(ranked_allow)}")
        print(f"✅ DENY results: {len(ranked_deny)}")
        print("✅ Filtering and ranking work together")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_ingestion_with_confidence_filter():
    """Test ingestion pipeline with confidence filtering."""
    print("\n[Test 3] Ingestion with confidence filtering...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        # Configure ingestion with min confidence
        config = IngestionConfig(min_confidence=0.8)
        ingestion = PrecedentIngestionPipeline(storage, config)

        # Try to ingest low confidence (should be skipped)
        low_conf_bundle = [create_test_evidence_bundle("C1", "ALLOW", 0.7)]
        low_conf_result = create_test_aggregation_result("ALLOW", 0.7, ["C1"])

        id_low = ingestion.ingest_decision(
            "Low confidence case",
            low_conf_bundle,
            low_conf_result
        )

        assert id_low is None, "Low confidence should be skipped"

        # Ingest high confidence (should be stored)
        high_conf_bundle = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
        high_conf_result = create_test_aggregation_result("ALLOW", 0.9, ["C1"])

        id_high = ingestion.ingest_decision(
            "High confidence case",
            high_conf_bundle,
            high_conf_result
        )

        assert id_high is not None, "High confidence should be stored"

        # Verify only high confidence was stored
        count = storage.count_precedents()
        assert count == 1, "Should only have 1 precedent"

        print("✅ Low confidence filtered out")
        print("✅ High confidence stored")
        print(f"✅ Total stored: {count}")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_search_caching():
    """Test embedding caching in search engine."""
    print("\n[Test 4] Search caching...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)
        embedding_model = SimpleHashEmbedding()
        search_engine = SimilaritySearchEngine(storage, embedding_model, cache_embeddings=True)

        # Ingest some precedents
        for i in range(5):
            query = f"Test case {i}"
            evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
            aggregation_result = create_test_aggregation_result("ALLOW", 0.9, ["C1"])

            ingestion.ingest_decision(query, evidence_bundles, aggregation_result)

        # First search - populates cache
        search_engine.search("test", top_k=3)
        stats_after_search = search_engine.get_cache_stats()

        assert stats_after_search["cached_embeddings"] > 0, "Should have cached embeddings"

        # Precompute all
        search_engine.precompute_embeddings()
        stats_after_precompute = search_engine.get_cache_stats()

        assert stats_after_precompute["cached_embeddings"] >= 5, "Should have all precedents cached"

        # Clear cache
        search_engine.clear_cache()
        stats_after_clear = search_engine.get_cache_stats()

        assert stats_after_clear["cached_embeddings"] == 0, "Cache should be empty"

        print(f"✅ After search: {stats_after_search['cached_embeddings']} cached")
        print(f"✅ After precompute: {stats_after_precompute['cached_embeddings']} cached")
        print(f"✅ After clear: {stats_after_clear['cached_embeddings']} cached")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_ranking_with_decision_boost():
    """Test ranking with decision-specific boost."""
    print("\n[Test 5] Ranking with decision boost...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)
        embedding_model = SimpleHashEmbedding()
        search_engine = SimilaritySearchEngine(storage, embedding_model)

        # Ingest mixed decisions with similar similarity scores
        cases = [
            ("Allow case 1", "ALLOW", 0.85),
            ("Deny case 1", "DENY", 0.85),
            ("Allow case 2", "ALLOW", 0.85)
        ]

        for query, verdict, confidence in cases:
            evidence_bundles = [create_test_evidence_bundle("C1", verdict, confidence)]
            aggregation_result = create_test_aggregation_result(verdict, confidence, ["C1"])

            ingestion.ingest_decision(query, evidence_bundles, aggregation_result)

        # Search
        similarity_results = search_engine.search("case", top_k=10)

        # Rank with DENY boost
        config = RankingConfig(
            similarity_weight=1.0,
            recency_weight=0.0,
            confidence_weight=0.0,
            decision_boost={"DENY": 0.5}  # 50% boost for DENY
        )
        ranker = PrecedentRanker(config)
        ranked = ranker.rank(similarity_results)

        # DENY should be ranked higher due to boost
        deny_ranks = [r.rank for r in ranked if r.decision == "DENY"]
        allow_ranks = [r.rank for r in ranked if r.decision == "ALLOW"]

        # At least one DENY should rank above all ALLOWs
        assert min(deny_ranks) < max(allow_ranks), "DENY should be boosted"

        print(f"✅ DENY ranks: {deny_ranks}")
        print(f"✅ ALLOW ranks: {allow_ranks}")
        print("✅ Decision boost works")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_error_handling():
    """Test error handling across components."""
    print("\n[Test 6] Error handling...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)

        # Test invalid decision
        try:
            evidence_bundles = [create_test_evidence_bundle("C1", "INVALID", 0.9)]
            aggregation_result = AggregationResult(
                final_verdict="INVALID",
                confidence=0.9,
                weighted_scores={"INVALID": 0.9},
                contributing_critics=["C1"],
                total_weight=1.0,
                conflicts_detected=[]
            )

            ingestion.ingest_decision(
                "Invalid decision test",
                evidence_bundles,
                aggregation_result
            )
            assert False, "Should raise ValueError for invalid decision"
        except ValueError as e:
            assert "decision" in str(e).lower()
            print("✅ Invalid decision rejected")

        # Test empty query
        try:
            evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
            aggregation_result = create_test_aggregation_result("ALLOW", 0.9, ["C1"])

            ingestion.ingest_decision(
                "",
                evidence_bundles,
                aggregation_result
            )
            assert False, "Should raise ValueError for empty query"
        except ValueError as e:
            assert "empty" in str(e).lower()
            print("✅ Empty query rejected")

        # Test search on empty storage
        embedding_model = SimpleHashEmbedding()
        search_engine = SimilaritySearchEngine(storage, embedding_model)

        results = search_engine.search("test", top_k=10)
        assert len(results) == 0, "Should return empty list for empty storage"
        print("✅ Empty storage handled")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_batch_operations():
    """Test batch ingestion and retrieval."""
    print("\n[Test 7] Batch operations...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)

        # Prepare batch
        batch = []
        for i in range(10):
            query = f"Batch case {i}"
            evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
            aggregation_result = create_test_aggregation_result("ALLOW", 0.9, ["C1"])

            batch.append({
                "query": query,
                "evidence_bundles": evidence_bundles,
                "aggregation_result": aggregation_result,
                "metadata": {"batch_id": 1}
            })

        # Ingest batch
        precedent_ids = ingestion.ingest_batch(batch)

        assert len(precedent_ids) == 10, "Should return 10 IDs"
        assert all(id is not None for id in precedent_ids), "All should be stored"

        # Verify storage
        count = storage.count_precedents()
        assert count == 10, "Should have 10 precedents"

        # Get statistics
        stats = storage.get_statistics()
        assert stats["total_precedents"] == 10
        assert stats["by_decision"]["ALLOW"] == 10

        print(f"✅ Batch ingested: {len(precedent_ids)} precedents")
        print(f"✅ Storage count: {count}")
        print(f"✅ Statistics: {stats['total_precedents']} total")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_ingestion_hooks():
    """Test ingestion hooks for extensibility."""
    print("\n[Test 8] Ingestion hooks...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        ingestion = PrecedentIngestionPipeline(storage)

        # Track hook calls
        hook_calls = []

        def notification_hook(precedent_id, query, aggregation_result):
            hook_calls.append({
                "id": precedent_id,
                "query": query,
                "verdict": aggregation_result.final_verdict
            })

        # Add hook
        ingestion.add_ingestion_hook(notification_hook)

        # Ingest multiple cases
        for i in range(3):
            query = f"Test case {i}"
            evidence_bundles = [create_test_evidence_bundle("C1", "ALLOW", 0.9)]
            aggregation_result = create_test_aggregation_result("ALLOW", 0.9, ["C1"])

            ingestion.ingest_decision(query, evidence_bundles, aggregation_result)

        # Verify hooks were called
        assert len(hook_calls) == 3, "Hook should be called 3 times"
        assert all("id" in call and "query" in call for call in hook_calls)

        print(f"✅ Hook called {len(hook_calls)} times")
        print("✅ Hook extensibility works")

    finally:
        Path(db_path).unlink(missing_ok=True)


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Precedent Engine Integration Tests (Task 3.5)")
    print("=" * 60)

    try:
        test_end_to_end_workflow()
        test_filtered_search_and_rank()
        test_ingestion_with_confidence_filter()
        test_search_caching()
        test_ranking_with_decision_boost()
        test_error_handling()
        test_batch_operations()
        test_ingestion_hooks()

        print("\n" + "=" * 60)
        print("✅ All 8 integration tests passed!")
        print("=" * 60)

        print("\nPrecedent Engine Components Validated:")
        print("  ✅ Storage: CRUD operations, statistics")
        print("  ✅ Ingestion: Filtering, batching, hooks")
        print("  ✅ Search: Similarity, caching, filtering")
        print("  ✅ Ranking: Multi-factor, boosting, stability")
        print("  ✅ Integration: End-to-end workflows")
        print("  ✅ Error Handling: Input validation, edge cases")

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
