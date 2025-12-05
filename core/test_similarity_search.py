#!/usr/bin/env python3
"""
Test Similarity Search Engine.

Task 3.3: Test suite for embedding-based similarity search.
"""

import sys
import tempfile
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.precedent_storage import PrecedentStorage
from core.similarity_search import (
    SimilaritySearchEngine,
    SimpleHashEmbedding,
    create_search_engine,
    EmbeddingModel
)


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


def setup_test_storage():
    """Set up storage with test precedents."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    storage = PrecedentStorage(db_path)

    # Store some test precedents
    queries = [
        "User wants to delete their account data",
        "User requests to export personal information",
        "User asks about privacy policy details",
        "User wants to share data with third party",
        "User requests account deletion permanently"
    ]

    evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

    for i, query in enumerate(queries):
        decision = "ALLOW" if i < 3 else "DENY"
        confidence = 0.9 - i * 0.05

        storage.store_precedent(
            query, evidence_bundle, decision, confidence
        )

    return storage, db_path


def test_embedding_model():
    """Test hash-based embedding model."""
    print("\n[Test 1] Embedding model...")

    model = SimpleHashEmbedding(dim=128)

    text1 = "This is a test"
    text2 = "This is also a test"
    text3 = "Completely different text"

    # Generate embeddings
    emb1 = model.embed(text1)
    emb2 = model.embed(text2)
    emb3 = model.embed(text3)

    # Check dimensions
    assert emb1.shape == (128,), "Should have correct dimension"
    assert emb2.shape == (128,), "Should have correct dimension"

    # Check normalization
    norm1 = np.linalg.norm(emb1)
    assert abs(norm1 - 1.0) < 0.01, "Should be normalized"

    # Check deterministic
    emb1_again = model.embed(text1)
    assert np.allclose(emb1, emb1_again), "Should be deterministic"

    # Check batch embedding
    batch_embs = model.embed_batch([text1, text2, text3])
    assert len(batch_embs) == 3, "Should return 3 embeddings"
    assert np.allclose(batch_embs[0], emb1), "Batch should match single"

    print(f"✅ Embedding dimension: {model.embedding_dim}")
    print(f"✅ Embeddings normalized: {abs(norm1 - 1.0) < 0.01}")
    print(f"✅ Deterministic: True")
    print(f"✅ Batch embedding works")


def test_basic_search():
    """Test basic similarity search."""
    print("\n[Test 2] Basic similarity search...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        query = "User wants to delete account"
        results = engine.search(query, top_k=3)

        assert len(results) <= 3, "Should return at most 3 results"
        assert len(results) > 0, "Should return at least 1 result"

        # Check result structure
        result = results[0]
        assert hasattr(result, 'precedent_id')
        assert hasattr(result, 'query')
        assert hasattr(result, 'decision')
        assert hasattr(result, 'similarity_score')

        # Check sorted by similarity
        if len(results) > 1:
            assert results[0].similarity_score >= results[1].similarity_score

        print(f"✅ Found {len(results)} results")
        print(f"✅ Top result similarity: {results[0].similarity_score:.4f}")
        print(f"✅ Top result: {results[0].query[:50]}...")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_top_k_retrieval():
    """Test top-k retrieval."""
    print("\n[Test 3] Top-k retrieval...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        query = "delete account data"

        # Test different k values
        results_k1 = engine.search(query, top_k=1)
        results_k3 = engine.search(query, top_k=3)
        results_k10 = engine.search(query, top_k=10)

        assert len(results_k1) == 1, "Should return 1 result"
        assert len(results_k3) <= 3, "Should return at most 3 results"
        assert len(results_k10) <= 10, "Should return at most 10 results"

        # Check that k=1 is the top result from k=3
        assert results_k1[0].precedent_id == results_k3[0].precedent_id

        print(f"✅ k=1: {len(results_k1)} results")
        print(f"✅ k=3: {len(results_k3)} results")
        print(f"✅ k=10: {len(results_k10)} results")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_similarity_threshold():
    """Test minimum similarity threshold."""
    print("\n[Test 4] Similarity threshold...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        query = "delete account"

        # Test with different thresholds
        results_all = engine.search(query, top_k=10, min_similarity=0.0)
        results_high = engine.search(query, top_k=10, min_similarity=0.9)

        # High threshold should return fewer or equal results
        assert len(results_high) <= len(results_all)

        # All results should meet threshold
        for result in results_high:
            assert result.similarity_score >= 0.9

        print(f"✅ No threshold: {len(results_all)} results")
        print(f"✅ Min 0.9: {len(results_high)} results")
        if results_high:
            print(f"✅ All results >= 0.9: True")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_decision_filtering():
    """Test filtering by decision type."""
    print("\n[Test 5] Decision filtering...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        query = "user account data"

        # Search without filter
        results_all = engine.search(query, top_k=10)

        # Search with ALLOW filter
        results_allow = engine.search(query, top_k=10, filter_decision="ALLOW")

        # Search with DENY filter
        results_deny = engine.search(query, top_k=10, filter_decision="DENY")

        # Check all results have correct decision
        for result in results_allow:
            assert result.decision == "ALLOW"

        for result in results_deny:
            assert result.decision == "DENY"

        print(f"✅ All results: {len(results_all)}")
        print(f"✅ ALLOW only: {len(results_allow)}")
        print(f"✅ DENY only: {len(results_deny)}")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_search_by_id():
    """Test searching for similar precedents by ID."""
    print("\n[Test 6] Search by precedent ID...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        # Get first precedent
        recent = storage.find_recent(limit=1)
        source_id = recent[0]["precedent_id"]

        # Find similar
        results = engine.search_by_id(source_id, top_k=3)

        # Should not include source itself
        for result in results:
            assert result.precedent_id != source_id

        print(f"✅ Found {len(results)} similar precedents")
        print(f"✅ Source excluded: True")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_embedding_cache():
    """Test embedding caching."""
    print("\n[Test 7] Embedding cache...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()

        # Test with caching enabled
        engine_cached = SimilaritySearchEngine(storage, model, cache_embeddings=True)
        query = "delete account"

        # First search - populates cache
        engine_cached.search(query, top_k=3)
        stats1 = engine_cached.get_cache_stats()

        # Second search - uses cache
        engine_cached.search(query, top_k=3)
        stats2 = engine_cached.get_cache_stats()

        assert stats1["cache_enabled"], "Cache should be enabled"
        assert stats2["cached_embeddings"] >= stats1["cached_embeddings"]

        # Test precompute
        engine_cached.precompute_embeddings()
        stats3 = engine_cached.get_cache_stats()
        assert stats3["cached_embeddings"] > 0

        # Test clear cache
        engine_cached.clear_cache()
        stats4 = engine_cached.get_cache_stats()
        assert stats4["cached_embeddings"] == 0

        print(f"✅ Cache enabled: {stats1['cache_enabled']}")
        print(f"✅ After 1st search: {stats1['cached_embeddings']} cached")
        print(f"✅ After precompute: {stats3['cached_embeddings']} cached")
        print(f"✅ After clear: {stats4['cached_embeddings']} cached")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    print("\n[Test 8] Cosine similarity...")

    storage, db_path = setup_test_storage()

    try:
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        # Test identical vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        sim_identical = engine._cosine_similarity(vec1, vec2)
        assert abs(sim_identical - 1.0) < 0.01, "Identical should be ~1.0"

        # Test orthogonal vectors
        vec3 = np.array([1.0, 0.0, 0.0])
        vec4 = np.array([0.0, 1.0, 0.0])
        sim_orthogonal = engine._cosine_similarity(vec3, vec4)
        assert abs(sim_orthogonal) < 0.01, "Orthogonal should be ~0.0"

        # Test opposite vectors
        vec5 = np.array([1.0, 0.0, 0.0])
        vec6 = np.array([-1.0, 0.0, 0.0])
        sim_opposite = engine._cosine_similarity(vec5, vec6)
        assert abs(sim_opposite - (-1.0)) < 0.01, "Opposite should be ~-1.0"

        print(f"✅ Identical vectors: {sim_identical:.4f} (expected 1.0)")
        print(f"✅ Orthogonal vectors: {sim_orthogonal:.4f} (expected 0.0)")
        print(f"✅ Opposite vectors: {sim_opposite:.4f} (expected -1.0)")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_empty_storage():
    """Test search with empty storage."""
    print("\n[Test 9] Empty storage handling...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        model = SimpleHashEmbedding()
        engine = SimilaritySearchEngine(storage, model)

        query = "test query"
        results = engine.search(query, top_k=10)

        assert len(results) == 0, "Should return empty list"

        print("✅ Empty storage handled gracefully")
        print(f"✅ Results: {len(results)}")

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 10] Convenience function...")

    engine = create_search_engine()

    assert engine is not None, "Should create engine"
    assert engine.storage is not None, "Should have storage"
    assert engine.embedding_model is not None, "Should have embedding model"

    # Check embedding model type
    assert isinstance(engine.embedding_model, SimpleHashEmbedding)

    print("✅ Convenience function works")
    print(f"✅ Embedding dim: {engine.embedding_model.embedding_dim}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Similarity Search Engine Tests (Task 3.3)")
    print("=" * 60)

    try:
        test_embedding_model()
        test_basic_search()
        test_top_k_retrieval()
        test_similarity_threshold()
        test_decision_filtering()
        test_search_by_id()
        test_embedding_cache()
        test_cosine_similarity()
        test_empty_storage()
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
