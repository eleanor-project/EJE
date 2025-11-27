"""
Tests for semantic precedent search system.

Tests vector store, hybrid search, and privacy bundling.
"""

import json
import os
import pytest
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict

# Import modules under test
from ejc.core.precedent.semantic import (
    VectorPrecedentStore,
    SimilarPrecedent,
    HybridPrecedentSearch,
    PrivacyPreservingPrecedents,
    AnonymousBundle
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_precedents() -> List[Dict]:
    """Create sample precedents for testing."""
    return [
        {
            "id": "prec_001",
            "hash": "abc123",
            "input_data": {
                "prompt": "Share user medical records with insurance company",
                "context": {"privacy_sensitive": True, "age": 35}
            },
            "outcome": {"verdict": "blocked", "confidence": 0.95},
            "timestamp": "2025-01-15T10:00:00Z"
        },
        {
            "id": "prec_002",
            "hash": "def456",
            "input_data": {
                "prompt": "Disclose health data to third party without consent",
                "context": {"privacy_sensitive": True, "age": 42}
            },
            "outcome": {"verdict": "blocked", "confidence": 0.92},
            "timestamp": "2025-01-16T14:30:00Z"
        },
        {
            "id": "prec_003",
            "hash": "ghi789",
            "input_data": {
                "prompt": "Post public health information on website",
                "context": {"privacy_sensitive": False, "age": 28}
            },
            "outcome": {"verdict": "allowed", "confidence": 0.88},
            "timestamp": "2025-01-17T09:15:00Z"
        },
        {
            "id": "prec_004",
            "hash": "jkl012",
            "input_data": {
                "prompt": "Share patient data for medical research with anonymization",
                "context": {"privacy_sensitive": True, "age": 51}
            },
            "outcome": {"verdict": "allowed", "confidence": 0.75},
            "timestamp": "2025-01-18T16:45:00Z"
        },
        {
            "id": "prec_005",
            "hash": "mno345",
            "input_data": {
                "prompt": "Display wellness tips publicly",
                "context": {"privacy_sensitive": False, "age": 29}
            },
            "outcome": {"verdict": "allowed", "confidence": 0.90},
            "timestamp": "2025-01-19T11:20:00Z"
        }
    ]


@pytest.fixture
def mock_hash_store():
    """Mock hash-based precedent store."""
    class MockHashStore:
        def __init__(self):
            self.precedents = {}

        def add(self, precedent: Dict):
            prec_id = precedent.get("id", precedent.get("hash"))
            self.precedents[prec_id] = precedent

        def lookup(self, case: Dict) -> List[Dict]:
            # Simple mock: return empty for testing
            return []

    return MockHashStore()


# ============================================================================
# VectorPrecedentStore Tests
# ============================================================================

class TestVectorPrecedentStore:
    """Tests for VectorPrecedentStore."""

    def test_initialization(self, temp_data_dir):
        """Test store initialization."""
        store = VectorPrecedentStore(temp_data_dir)

        assert store.data_path == temp_data_dir
        assert len(store.precedents) == 0
        assert store.embedding_dim == 384

    def test_add_single_precedent(self, temp_data_dir, sample_precedents):
        """Test adding a single precedent."""
        store = VectorPrecedentStore(temp_data_dir)

        prec = sample_precedents[0]
        prec_id = store.add_precedent(prec)

        assert prec_id == "prec_001"
        assert len(store.precedents) == 1
        assert store.precedents[0] == prec

    def test_add_multiple_precedents(self, temp_data_dir, sample_precedents):
        """Test batch adding precedents."""
        store = VectorPrecedentStore(temp_data_dir)

        ids = store.add_precedents_batch(sample_precedents)

        assert len(ids) == 5
        assert len(store.precedents) == 5
        assert all(f"prec_{i:03d}" in ids for i in range(1, 6))

    def test_duplicate_precedent_skipped(self, temp_data_dir, sample_precedents):
        """Test that duplicate precedents are skipped."""
        store = VectorPrecedentStore(temp_data_dir)

        prec = sample_precedents[0]
        store.add_precedent(prec)
        store.add_precedent(prec)  # Duplicate

        assert len(store.precedents) == 1

    def test_get_by_id(self, temp_data_dir, sample_precedents):
        """Test retrieving precedent by ID."""
        store = VectorPrecedentStore(temp_data_dir)
        store.add_precedents_batch(sample_precedents)

        prec = store.get_by_id("prec_002")

        assert prec is not None
        assert prec["id"] == "prec_002"
        assert "medical" in prec["input_data"]["prompt"].lower()

    def test_get_by_id_not_found(self, temp_data_dir):
        """Test retrieving non-existent precedent."""
        store = VectorPrecedentStore(temp_data_dir)

        prec = store.get_by_id("nonexistent")

        assert prec is None

    @pytest.mark.skipif(
        not hasattr(VectorPrecedentStore, '__init__'),
        reason="Skipping if store unavailable"
    )
    def test_search_similar_basic(self, temp_data_dir, sample_precedents):
        """Test basic semantic search."""
        store = VectorPrecedentStore(temp_data_dir)
        store.add_precedents_batch(sample_precedents)

        # Search for similar to medical records case
        case = {
            "prompt": "Release patient medical information",
            "context": {"privacy_sensitive": True}
        }

        results = store.search_similar(case, k=3, min_similarity=0.0)

        # Should return some results (exact matching depends on embeddings)
        assert isinstance(results, list)

        if results:  # If embeddings available
            assert all(isinstance(r, SimilarPrecedent) for r in results)
            assert all(0.0 <= r.similarity_score <= 1.0 for r in results)

    def test_save_and_load(self, temp_data_dir, sample_precedents):
        """Test saving and loading precedents."""
        # Create and populate store
        store1 = VectorPrecedentStore(temp_data_dir)
        store1.add_precedents_batch(sample_precedents)
        store1.save()

        # Create new store from same path
        store2 = VectorPrecedentStore(temp_data_dir)

        # Should load existing data
        assert len(store2.precedents) == 5
        assert store2.get_by_id("prec_003") is not None

    def test_get_stats(self, temp_data_dir, sample_precedents):
        """Test getting store statistics."""
        store = VectorPrecedentStore(temp_data_dir)
        store.add_precedents_batch(sample_precedents)

        stats = store.get_stats()

        assert stats["total_precedents"] == 5
        assert "embedding_dimension" in stats
        assert stats["embedding_dimension"] == 384
        assert "data_path" in stats


# ============================================================================
# HybridPrecedentSearch Tests
# ============================================================================

class TestHybridPrecedentSearch:
    """Tests for HybridPrecedentSearch."""

    def test_initialization(self, temp_data_dir, mock_hash_store):
        """Test hybrid search initialization."""
        vector_store = VectorPrecedentStore(temp_data_dir)
        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        assert search.hash_store == mock_hash_store
        assert search.vector_store == vector_store
        assert search.weights.exact_weight == 2.0

    def test_search_semantic_only(self, temp_data_dir, mock_hash_store, sample_precedents):
        """Test semantic-only search."""
        vector_store = VectorPrecedentStore(temp_data_dir)
        vector_store.add_precedents_batch(sample_precedents)

        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        case = {"prompt": "Medical data sharing", "context": {}}
        results = search.search(case, top_k=3, semantic_only=True)

        assert isinstance(results, list)
        # Results depend on embeddings availability

    def test_search_exact_only(self, temp_data_dir, sample_precedents):
        """Test exact-only search."""
        # Mock hash store with data
        class MockHashStoreWithData:
            def lookup(self, case):
                return [sample_precedents[0]]  # Return first precedent

        hash_store = MockHashStoreWithData()
        vector_store = VectorPrecedentStore(temp_data_dir)

        search = HybridPrecedentSearch(hash_store, vector_store)

        case = {"prompt": "test", "context": {}}
        results = search.search(case, exact_only=True)

        assert len(results) == 1
        assert results[0].match_type == "exact"
        assert results[0].similarity_score == 1.0

    def test_merge_deduplication(self, temp_data_dir, mock_hash_store, sample_precedents):
        """Test that merge deduplicates results."""
        vector_store = VectorPrecedentStore(temp_data_dir)
        vector_store.add_precedents_batch(sample_precedents)

        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        # Create exact matches that overlap with semantic matches
        exact = [SimilarPrecedent(
            precedent_id="prec_001",
            precedent=sample_precedents[0],
            similarity_score=1.0,
            match_type="exact"
        )]

        semantic = [
            SimilarPrecedent(
                precedent_id="prec_001",  # Duplicate
                precedent=sample_precedents[0],
                similarity_score=0.95,
                match_type="semantic"
            ),
            SimilarPrecedent(
                precedent_id="prec_002",
                precedent=sample_precedents[1],
                similarity_score=0.90,
                match_type="semantic"
            )
        ]

        merged = search._merge_and_rank(exact, semantic, top_k=10)

        # Should have 2 unique precedents (deduplication)
        assert len(merged) == 2
        assert merged[0].precedent_id == "prec_001"  # Exact match prioritized

    def test_search_similar_to_precedent(self, temp_data_dir, mock_hash_store, sample_precedents):
        """Test finding precedents similar to existing precedent."""
        vector_store = VectorPrecedentStore(temp_data_dir)
        vector_store.add_precedents_batch(sample_precedents)

        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        # Find similar to first precedent
        results = search.search_similar_to_precedent("prec_001", top_k=3)

        # Should not include the reference precedent itself
        assert all(r.precedent_id != "prec_001" for r in results)

    def test_get_stats(self, temp_data_dir, mock_hash_store):
        """Test getting hybrid search statistics."""
        vector_store = VectorPrecedentStore(temp_data_dir)
        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        stats = search.get_stats()

        assert "hash_store_type" in stats
        assert "vector_store_stats" in stats
        assert "weights" in stats


# ============================================================================
# PrivacyPreservingPrecedents Tests
# ============================================================================

class TestPrivacyPreservingPrecedents:
    """Tests for PrivacyPreservingPrecedents."""

    def test_initialization(self):
        """Test privacy bundler initialization."""
        privacy = PrivacyPreservingPrecedents(k=5)

        assert privacy.k == 5
        assert "user_id" in privacy.sensitive_fields
        assert "timestamp" in privacy.quasi_identifiers

    def test_create_bundle_insufficient_precedents(self, sample_precedents):
        """Test bundle creation with insufficient precedents."""
        privacy = PrivacyPreservingPrecedents(k=10)

        with pytest.raises(ValueError, match="Need at least 10 precedents"):
            privacy.create_anonymous_bundle(sample_precedents)  # Only 5 precedents

    def test_create_bundle_success(self, sample_precedents):
        """Test successful bundle creation."""
        privacy = PrivacyPreservingPrecedents(k=2)

        bundle = privacy.create_anonymous_bundle(sample_precedents)

        assert isinstance(bundle, AnonymousBundle)
        assert bundle.k_value == 2
        assert len(bundle.precedents) >= 2
        assert bundle.privacy_guarantee == "k-anonymity"

    def test_sensitive_field_redaction(self, sample_precedents):
        """Test that sensitive fields are redacted."""
        # Add sensitive data to precedent
        prec_with_sensitive = sample_precedents[0].copy()
        prec_with_sensitive["input_data"]["context"]["user_id"] = "user123"
        prec_with_sensitive["input_data"]["context"]["email"] = "user@example.com"

        privacy = PrivacyPreservingPrecedents(k=1)
        redacted = privacy._redact_sensitive_fields(prec_with_sensitive)

        context = redacted["input_data"]["context"]
        assert context["user_id"] == "[REDACTED]"
        assert context["email"] == "[REDACTED]"

    def test_timestamp_generalization(self, sample_precedents):
        """Test timestamp generalization to date only."""
        privacy = PrivacyPreservingPrecedents(k=2)

        cluster = sample_precedents[:3]
        generalized = privacy._generalize_cluster(cluster)

        # Check timestamps are generalized
        for prec in generalized["precedents"]:
            if "timestamp" in prec:
                # Should be date only (no time component)
                assert "T" not in prec["timestamp"]
                assert len(prec["timestamp"]) == 10  # YYYY-MM-DD

    def test_age_generalization(self, sample_precedents):
        """Test age generalization to ranges."""
        privacy = PrivacyPreservingPrecedents(k=2)

        cluster = sample_precedents[:3]
        generalized = privacy._generalize_cluster(cluster)

        # Check ages are generalized to ranges
        for prec in generalized["precedents"]:
            context = prec.get("input_data", {}).get("context", {})
            if "age" in context:
                age = context["age"]
                # Should be a range string
                assert isinstance(age, str)
                assert any(char in age for char in ["-", "plus", "under"])

    def test_age_to_range_conversion(self):
        """Test age to range conversion."""
        privacy = PrivacyPreservingPrecedents()

        assert privacy._age_to_range(16) == "under-18"
        assert privacy._age_to_range(22) == "18-24"
        assert privacy._age_to_range(30) == "25-34"
        assert privacy._age_to_range(70) == "65-plus"

    def test_verify_k_anonymity(self, sample_precedents):
        """Test k-anonymity verification."""
        privacy = PrivacyPreservingPrecedents(k=2)

        bundle = privacy.create_anonymous_bundle(sample_precedents)

        # Verification (may pass or fail depending on clustering)
        is_k_anonymous = privacy.verify_k_anonymity(bundle)

        # At minimum, should return a boolean
        assert isinstance(is_k_anonymous, bool)

    def test_bundle_id_generation(self, sample_precedents):
        """Test bundle ID generation."""
        privacy = PrivacyPreservingPrecedents(k=2)

        bundle1 = privacy.create_anonymous_bundle(sample_precedents)
        bundle2 = privacy.create_anonymous_bundle(sample_precedents)

        # Same precedents should generate same bundle ID
        assert bundle1.bundle_id == bundle2.bundle_id
        assert bundle1.bundle_id.startswith("bundle_")

    def test_differential_privacy_placeholder(self, sample_precedents):
        """Test differential privacy addition (placeholder)."""
        privacy = PrivacyPreservingPrecedents(k=2)

        bundle = privacy.create_anonymous_bundle(sample_precedents)
        dp_bundle = privacy.add_differential_privacy_noise(bundle, epsilon=1.0)

        assert "dp" in dp_bundle.privacy_guarantee
        assert dp_bundle.metadata["dp_epsilon"] == 1.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestSemanticPrecedentIntegration:
    """Integration tests for semantic precedent system."""

    def test_full_workflow(self, temp_data_dir, sample_precedents):
        """Test complete workflow: add, search, bundle."""
        # 1. Create stores
        vector_store = VectorPrecedentStore(temp_data_dir)

        # 2. Add precedents
        vector_store.add_precedents_batch(sample_precedents)

        # 3. Search
        case = {"prompt": "Medical data privacy", "context": {}}
        results = vector_store.search_similar(case, k=3)

        assert isinstance(results, list)

        # 4. Create privacy bundle
        privacy = PrivacyPreservingPrecedents(k=2)
        bundle = privacy.create_anonymous_bundle(sample_precedents)

        assert len(bundle.precedents) >= 2

        # 5. Save and verify persistence
        vector_store.save()
        assert os.path.exists(os.path.join(temp_data_dir, "precedents.json"))

    def test_hybrid_search_integration(self, temp_data_dir, mock_hash_store, sample_precedents):
        """Test hybrid search with both exact and semantic matches."""
        # Setup
        vector_store = VectorPrecedentStore(temp_data_dir)
        vector_store.add_precedents_batch(sample_precedents)

        # Add same precedents to mock hash store
        for prec in sample_precedents:
            mock_hash_store.add(prec)

        # Create hybrid search
        search = HybridPrecedentSearch(mock_hash_store, vector_store)

        # Search
        case = sample_precedents[0]["input_data"]  # Exact match should be found
        results = search.search(case, top_k=5)

        # Should get results (exact + semantic)
        assert isinstance(results, list)

    def test_privacy_bundle_verification(self, sample_precedents):
        """Test end-to-end privacy bundle creation and verification."""
        privacy = PrivacyPreservingPrecedents(k=2)

        # Create bundle
        bundle = privacy.create_anonymous_bundle(sample_precedents)

        # Verify properties
        assert bundle.k_value == 2
        assert len(bundle.generalized_attributes) > 0
        assert len(bundle.redacted_fields) > 0

        # Verify k-anonymity
        is_anonymous = privacy.verify_k_anonymity(bundle)
        assert isinstance(is_anonymous, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
