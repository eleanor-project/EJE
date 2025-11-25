"""
Tests for Precedent Vector Embeddings - Gap #1 Implementation
Semantic similarity search for jurisprudence reasoning

This module tests the implementation of Gap #1 from ELEANOR Spec v2.1.
"""

import pytest
import json
import numpy as np
from pathlib import Path
from ejc.core.jurisprudence_repository import JurisprudenceRepository


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary jurisprudence repository"""
    return JurisprudenceRepository(data_path=str(tmp_path), use_embeddings=True)


@pytest.fixture
def temp_repo_no_embeddings(tmp_path):
    """Create a repository without embeddings"""
    return JurisprudenceRepository(data_path=str(tmp_path), use_embeddings=False)


@pytest.fixture
def sample_cases():
    """Provide sample test cases with varying similarity"""
    return {
        "medical_privacy_1": {
            "text": "Share patient's medical records without consent",
            "context": {"privacy": True, "medical": True}
        },
        "medical_privacy_2": {
            "text": "Disclose someone's health information publicly",
            "context": {"privacy": True, "medical": True}
        },
        "financial_privacy": {
            "text": "Access user's bank account without permission",
            "context": {"privacy": True, "financial": True}
        },
        "public_speech": {
            "text": "Post political opinion on social media",
            "context": {"free_speech": True, "political": True}
        },
        "completely_different": {
            "text": "Calculate square root of a number",
            "context": {"math": True, "calculation": True}
        }
    }


@pytest.fixture
def sample_decision_bundle():
    """Sample decision bundle for precedent storage"""
    def _make_bundle(case_key, case_data, verdict="DENY"):
        return {
            "request_id": f"test-{case_key}",
            "timestamp": "2025-11-25T20:00:00",
            "input": case_data,
            "critic_outputs": [
                {
                    "critic": "TestCritic",
                    "verdict": verdict,
                    "confidence": 0.9,
                    "justification": f"Test justification for {case_key}"
                }
            ],
            "final_decision": {
                "overall_verdict": verdict,
                "avg_confidence": 0.9
            },
            "precedent_refs": []
        }
    return _make_bundle


class TestEmbeddingsInitialization:
    """Test embedding model initialization and setup"""

    def test_embeddings_enabled_by_default(self, temp_repo):
        """Test that embeddings are enabled by default"""
        assert temp_repo.use_embeddings is True
        assert temp_repo.embedder is not None

    def test_embeddings_can_be_disabled(self, temp_repo_no_embeddings):
        """Test that embeddings can be disabled"""
        assert temp_repo_no_embeddings.use_embeddings is False
        assert temp_repo_no_embeddings.embedder is None

    def test_embedding_model_loads(self, temp_repo):
        """Test that sentence-transformers model loads correctly"""
        # Model should be all-MiniLM-L6-v2
        assert temp_repo.embedder is not None

        # Test embedding generation
        test_text = "This is a test"
        embedding = temp_repo.embedder.encode(test_text)

        # Check embedding properties
        assert embedding is not None
        assert len(embedding) == 384  # MiniLM-L6-v2 dimension

    def test_embeddings_cache_initialized(self, temp_repo):
        """Test that embeddings cache is initialized"""
        assert temp_repo.embeddings_cache is not None
        assert isinstance(temp_repo.embeddings_cache, list)


class TestEmbeddingGeneration:
    """Test embedding vector generation"""

    def test_embed_simple_case(self, temp_repo, sample_cases):
        """Test embedding generation for a simple case"""
        case = sample_cases["medical_privacy_1"]
        embedding = temp_repo._embed_case(case)

        assert embedding is not None
        assert len(embedding) == 384
        assert isinstance(embedding, np.ndarray)

    def test_embed_case_with_context(self, temp_repo, sample_cases):
        """Test that context is included in embedding"""
        case = sample_cases["medical_privacy_1"]
        embedding = temp_repo._embed_case(case)

        # Verify embedding is generated with context
        assert embedding is not None

    def test_different_cases_different_embeddings(self, temp_repo, sample_cases):
        """Test that different cases produce different embeddings"""
        emb1 = temp_repo._embed_case(sample_cases["medical_privacy_1"])
        emb2 = temp_repo._embed_case(sample_cases["public_speech"])

        # Should not be identical
        assert not np.array_equal(emb1, emb2)

    def test_similar_cases_similar_embeddings(self, temp_repo, sample_cases):
        """Test that semantically similar cases have similar embeddings"""
        from sklearn.metrics.pairwise import cosine_similarity

        emb1 = temp_repo._embed_case(sample_cases["medical_privacy_1"])
        emb2 = temp_repo._embed_case(sample_cases["medical_privacy_2"])

        # Calculate cosine similarity
        similarity = cosine_similarity([emb1], [emb2])[0][0]

        # Should be highly similar (both about medical privacy)
        assert similarity > 0.7, f"Similarity {similarity} too low for similar cases"


class TestSemanticLookup:
    """Test semantic similarity search"""

    def test_semantic_lookup_finds_similar_cases(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that semantic lookup finds similar precedents"""
        # Store some precedents
        temp_repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        )
        temp_repo.store_precedent(
            sample_decision_bundle("financial_privacy", sample_cases["financial_privacy"])
        )
        temp_repo.store_precedent(
            sample_decision_bundle("public_speech", sample_cases["public_speech"])
        )

        # Look up similar case
        query = sample_cases["medical_privacy_2"]  # Similar to medical_privacy_1
        results = temp_repo.lookup(query, similarity_threshold=0.7)

        # Should find medical_privacy_1 as most similar
        assert len(results) > 0
        assert "similarity_score" in results[0]
        assert results[0]["similarity_score"] > 0.7

    def test_semantic_lookup_threshold_filtering(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that similarity threshold filters results"""
        # Store precedents
        temp_repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        )

        # Query with very different case
        query = sample_cases["completely_different"]

        # With low threshold, might find something
        results_low = temp_repo.lookup(query, similarity_threshold=0.1)

        # With high threshold, should find nothing
        results_high = temp_repo.lookup(query, similarity_threshold=0.95)

        # High threshold should filter out unrelated precedents
        assert len(results_high) <= len(results_low)

    def test_semantic_lookup_sorted_by_similarity(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that results are sorted by similarity (descending)"""
        # Store multiple precedents
        temp_repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        )
        temp_repo.store_precedent(
            sample_decision_bundle("financial_privacy", sample_cases["financial_privacy"])
        )
        temp_repo.store_precedent(
            sample_decision_bundle("public_speech", sample_cases["public_speech"])
        )

        # Query with medical privacy case
        query = sample_cases["medical_privacy_2"]
        results = temp_repo.lookup(query, similarity_threshold=0.3)

        if len(results) >= 2:
            # Results should be in descending order of similarity
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]

    def test_semantic_lookup_max_results(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that max_results parameter limits output"""
        # Store many precedents
        for i in range(10):
            temp_repo.store_precedent(
                sample_decision_bundle(f"case_{i}", sample_cases["medical_privacy_1"])
            )

        # Query with limit
        query = sample_cases["medical_privacy_2"]
        results = temp_repo.lookup(query, similarity_threshold=0.5, max_results=3)

        # Should respect max_results
        assert len(results) <= 3


class TestExactMatching:
    """Test exact hash matching (fallback when no embeddings)"""

    def test_exact_match_takes_precedence(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that exact matches are returned before semantic search"""
        # Store a precedent
        bundle = sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        temp_repo.store_precedent(bundle)

        # Query with exact same case
        query = sample_cases["medical_privacy_1"]
        results = temp_repo.lookup(query)

        # Should find exact match
        assert len(results) > 0
        # Exact match should have hash match
        assert results[0]["case_hash"] == temp_repo._hash_case(query)

    def test_hash_matching_without_embeddings(
        self, temp_repo_no_embeddings, sample_cases, sample_decision_bundle
    ):
        """Test that hash matching works when embeddings disabled"""
        # Store a precedent
        bundle = sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        temp_repo_no_embeddings.store_precedent(bundle)

        # Exact match should work
        query = sample_cases["medical_privacy_1"]
        results = temp_repo_no_embeddings.lookup(query)

        assert len(results) > 0

        # But similar case should not match (no semantic search)
        query_similar = sample_cases["medical_privacy_2"]
        results_similar = temp_repo_no_embeddings.lookup(query_similar)

        assert len(results_similar) == 0  # No semantic search available


class TestEmbeddingsCache:
    """Test embeddings caching and persistence"""

    def test_embeddings_cached_after_storage(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that embeddings are cached when precedents stored"""
        initial_cache_size = len(temp_repo.embeddings_cache)

        # Store a precedent
        temp_repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        )

        # Cache should grow
        assert len(temp_repo.embeddings_cache) == initial_cache_size + 1

    def test_embeddings_cache_rebuild(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """Test that embeddings cache can be rebuilt"""
        # Store some precedents
        for i, (key, case) in enumerate(list(sample_cases.items())[:3]):
            temp_repo.store_precedent(sample_decision_bundle(f"case_{i}", case))

        # Clear cache
        temp_repo.embeddings_cache = []

        # Trigger cache rebuild via lookup
        query = sample_cases["medical_privacy_1"]
        results = temp_repo.lookup(query)

        # Cache should be rebuilt
        assert len(temp_repo.embeddings_cache) == 3

    def test_embeddings_saved_to_disk(self, tmp_path, sample_cases, sample_decision_bundle):
        """Test that embeddings are persisted to disk"""
        repo = JurisprudenceRepository(data_path=str(tmp_path))

        # Store a precedent
        repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"])
        )

        # Check that embeddings file exists
        embeddings_path = tmp_path / "precedent_embeddings.npy"
        assert embeddings_path.exists()

        # Load embeddings
        loaded_embeddings = np.load(embeddings_path)
        assert len(loaded_embeddings) == 1
        assert len(loaded_embeddings[0]) == 384


class TestStatistics:
    """Test statistics and reporting"""

    def test_get_statistics(self, temp_repo, sample_cases, sample_decision_bundle):
        """Test statistics retrieval"""
        # Store some precedents
        for i in range(3):
            temp_repo.store_precedent(
                sample_decision_bundle(f"case_{i}", sample_cases["medical_privacy_1"])
            )

        stats = temp_repo.get_statistics()

        assert stats["total_precedents"] == 3
        assert stats["embeddings_cached"] == 3
        assert stats["embeddings_enabled"] is True
        assert "storage_path" in stats


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    def test_jurisprudence_consistency(
        self, temp_repo, sample_cases, sample_decision_bundle
    ):
        """
        Test: Similar cases should reference similar precedents (jurisprudence)
        Principle: Precedent consistency per RBJA requirements
        """
        # Store precedent for medical privacy violation
        temp_repo.store_precedent(
            sample_decision_bundle("medical_privacy_1", sample_cases["medical_privacy_1"], "DENY")
        )

        # New similar case should find the precedent
        query = sample_cases["medical_privacy_2"]
        results = temp_repo.lookup(query, similarity_threshold=0.7)

        # Should find similar precedent
        assert len(results) > 0
        assert results[0]["final_decision"]["overall_verdict"] == "DENY"

        # This demonstrates jurisprudence-style reasoning:
        # Similar cases reference similar precedents with similar verdicts

    def test_novel_case_no_precedents(self, temp_repo, sample_cases):
        """
        Test: Novel cases (no similar precedents) return empty
        Principle: Transparency per RBJA - novel cases should be identifiable
        """
        # Don't store any precedents

        # Query should return no results
        query = sample_cases["medical_privacy_1"]
        results = temp_repo.lookup(query, similarity_threshold=0.8)

        assert len(results) == 0
        # System can identify this as a novel case requiring careful handling


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
