#!/usr/bin/env python3
"""
Test Precedent Storage Backend.

Task 3.1: Test suite for precedent storage operations.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.precedent_storage import PrecedentStorage


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


def test_initialization():
    """Test storage initialization."""
    print("\n[Test 1] Storage initialization...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        # Check that DB was created
        assert Path(db_path).exists(), "Database file should exist"

        # Check count is 0
        count = storage.count_precedents()
        assert count == 0, "Should start with 0 precedents"

        print("✅ Storage initialized successfully")
        print(f"✅ Database path: {db_path}")
        print(f"✅ Initial count: {count}")

        return storage
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


def test_store_precedent():
    """Test storing a precedent."""
    print("\n[Test 2] Store precedent...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        query = "User requests to delete their account data"
        evidence_bundle = create_test_evidence_bundle("PrivacyCritic", "ALLOW", 0.9)
        decision = "ALLOW"
        confidence = 0.9
        metadata = {"jurisdiction": "EU", "domain": "privacy"}

        precedent_id = storage.store_precedent(
            query, evidence_bundle, decision, confidence, metadata
        )

        assert precedent_id.startswith("prec-"), "ID should have prec- prefix"
        assert len(precedent_id) > 10, "ID should be sufficiently long"

        print(f"✅ Stored precedent: {precedent_id}")
        print(f"✅ Query: {query[:50]}...")
        print(f"✅ Decision: {decision} ({confidence})")

        return storage, precedent_id
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_retrieve_precedent():
    """Test retrieving a stored precedent."""
    print("\n[Test 3] Retrieve precedent...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        # Store
        query = "User wants to export personal data"
        evidence_bundle = create_test_evidence_bundle("PrivacyCritic", "ALLOW", 0.88)
        precedent_id = storage.store_precedent(query, evidence_bundle, "ALLOW", 0.88)

        # Retrieve
        precedent = storage.get_precedent(precedent_id)

        assert precedent is not None, "Should retrieve precedent"
        assert precedent["precedent_id"] == precedent_id
        assert precedent["query"] == query
        assert precedent["decision"] == "ALLOW"
        assert precedent["confidence"] == 0.88
        assert "evidence_bundle" in precedent
        assert precedent["evidence_bundle"]["critic_output"]["critic_name"] == "PrivacyCritic"

        print(f"✅ Retrieved precedent: {precedent_id}")
        print(f"✅ Query matches: {precedent['query'] == query}")
        print(f"✅ Decision: {precedent['decision']}")
        print(f"✅ Confidence: {precedent['confidence']}")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_find_by_query_hash():
    """Test finding precedents by query hash (exact match)."""
    print("\n[Test 4] Find by query hash...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        query = "User requests data deletion"
        evidence_bundle = create_test_evidence_bundle("PrivacyCritic", "ALLOW", 0.9)

        # Store same query twice
        id1 = storage.store_precedent(query, evidence_bundle, "ALLOW", 0.9)
        id2 = storage.store_precedent(query, evidence_bundle, "ALLOW", 0.85)

        # Find by hash
        matches = storage.find_by_query_hash(query)

        assert len(matches) == 2, "Should find 2 matches"
        assert matches[0]["query"] == query
        assert matches[1]["query"] == query

        print(f"✅ Found {len(matches)} precedents with identical query")
        print(f"✅ IDs: {matches[0]['precedent_id']}, {matches[1]['precedent_id']}")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_find_by_decision():
    """Test finding precedents by decision type."""
    print("\n[Test 5] Find by decision...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)

        # Store multiple precedents with different decisions
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        storage.store_precedent("Query 1", evidence_bundle, "ALLOW", 0.9)
        storage.store_precedent("Query 2", evidence_bundle, "ALLOW", 0.85)
        storage.store_precedent("Query 3", evidence_bundle, "DENY", 0.8)
        storage.store_precedent("Query 4", evidence_bundle, "ESCALATE", 0.7)

        # Find ALLOW decisions
        allow_precs = storage.find_by_decision("ALLOW")
        assert len(allow_precs) == 2, "Should find 2 ALLOW precedents"

        # Find DENY decisions
        deny_precs = storage.find_by_decision("DENY")
        assert len(deny_precs) == 1, "Should find 1 DENY precedent"

        print(f"✅ Found {len(allow_precs)} ALLOW precedents")
        print(f"✅ Found {len(deny_precs)} DENY precedents")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_find_recent():
    """Test finding recent precedents."""
    print("\n[Test 6] Find recent precedents...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        # Store 5 precedents
        for i in range(5):
            storage.store_precedent(f"Query {i}", evidence_bundle, "ALLOW", 0.9 - i * 0.1)

        # Get recent (limit 3)
        recent = storage.find_recent(limit=3)
        assert len(recent) == 3, "Should return 3 most recent"

        # Get recent with min confidence
        high_conf = storage.find_recent(limit=10, min_confidence=0.8)
        assert len(high_conf) == 2, "Should find 2 with confidence >= 0.8"

        print(f"✅ Found {len(recent)} recent precedents (limit 3)")
        print(f"✅ Found {len(high_conf)} with confidence >= 0.8")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_search_by_text():
    """Test text search in queries."""
    print("\n[Test 7] Text search...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        # Store precedents with different queries
        storage.store_precedent("User wants to delete account", evidence_bundle, "ALLOW", 0.9)
        storage.store_precedent("User requests data export", evidence_bundle, "ALLOW", 0.85)
        storage.store_precedent("User asks for privacy policy", evidence_bundle, "ALLOW", 0.8)

        # Search for "delete"
        delete_results = storage.search_by_text("delete")
        assert len(delete_results) == 1, "Should find 1 match for 'delete'"
        assert "delete" in delete_results[0]["query"].lower()

        # Search for "user"
        user_results = storage.search_by_text("User")
        assert len(user_results) == 3, "Should find 3 matches for 'User'"

        print(f"✅ Found {len(delete_results)} matches for 'delete'")
        print(f"✅ Found {len(user_results)} matches for 'User'")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_statistics():
    """Test storage statistics."""
    print("\n[Test 8] Storage statistics...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        # Store multiple precedents
        storage.store_precedent("Query 1", evidence_bundle, "ALLOW", 0.9)
        storage.store_precedent("Query 2", evidence_bundle, "ALLOW", 0.8)
        storage.store_precedent("Query 3", evidence_bundle, "DENY", 0.85)

        stats = storage.get_statistics()

        assert stats["total_precedents"] == 3
        assert stats["by_decision"]["ALLOW"] == 2
        assert stats["by_decision"]["DENY"] == 1
        assert 0.8 <= stats["average_confidence"] <= 0.9

        print(f"✅ Total precedents: {stats['total_precedents']}")
        print(f"✅ By decision: {stats['by_decision']}")
        print(f"✅ Average confidence: {stats['average_confidence']:.2f}")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_delete_precedent():
    """Test deleting a precedent."""
    print("\n[Test 9] Delete precedent...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        # Store
        precedent_id = storage.store_precedent("Query", evidence_bundle, "ALLOW", 0.9)

        # Verify exists
        assert storage.get_precedent(precedent_id) is not None

        # Delete
        deleted = storage.delete_precedent(precedent_id)
        assert deleted, "Should return True"

        # Verify deleted
        assert storage.get_precedent(precedent_id) is None, "Should not exist after delete"

        # Try deleting again
        deleted_again = storage.delete_precedent(precedent_id)
        assert not deleted_again, "Should return False for non-existent ID"

        print("✅ Precedent deleted successfully")
        print("✅ Verified deletion")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_validation():
    """Test input validation."""
    print("\n[Test 10] Input validation...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        storage = PrecedentStorage(db_path)
        evidence_bundle = create_test_evidence_bundle("TestCritic", "ALLOW", 0.9)

        # Test empty query
        try:
            storage.store_precedent("", evidence_bundle, "ALLOW", 0.9)
            assert False, "Should raise ValueError for empty query"
        except ValueError as e:
            assert "empty" in str(e).lower()
            print("✅ Empty query validation works")

        # Test invalid decision
        try:
            storage.store_precedent("Query", evidence_bundle, "INVALID", 0.9)
            assert False, "Should raise ValueError for invalid decision"
        except ValueError as e:
            assert "decision" in str(e).lower()
            print("✅ Invalid decision validation works")

        # Test invalid confidence
        try:
            storage.store_precedent("Query", evidence_bundle, "ALLOW", 1.5)
            assert False, "Should raise ValueError for invalid confidence"
        except ValueError as e:
            assert "confidence" in str(e).lower()
            print("✅ Invalid confidence validation works")

        return storage
    finally:
        Path(db_path).unlink(missing_ok=True)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Precedent Storage Tests (Task 3.1)")
    print("=" * 60)

    try:
        test_initialization()
        test_store_precedent()
        test_retrieve_precedent()
        test_find_by_query_hash()
        test_find_by_decision()
        test_find_recent()
        test_search_by_text()
        test_statistics()
        test_delete_precedent()
        test_validation()

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
