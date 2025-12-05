#!/usr/bin/env python3
"""
Test Precedent Ranking Function.

Task 3.4: Test suite for precedent ranking with multiple factors.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.precedent_ranking import (
    PrecedentRanker,
    RankingConfig,
    rank_precedents
)
from core.similarity_search import SimilarityResult


def create_test_precedent(
    precedent_id: str,
    query: str,
    decision: str,
    confidence: float,
    days_old: int = 0
) -> dict:
    """Create a test precedent dict."""
    timestamp = (datetime.utcnow() - timedelta(days=days_old)).isoformat() + "Z"

    return {
        "precedent_id": precedent_id,
        "query": query,
        "decision": decision,
        "confidence": confidence,
        "timestamp": timestamp,
        "query_hash": "test-hash",
        "evidence_bundle": {},
        "metadata": {},
        "created_at": timestamp
    }


def create_test_similarity_result(
    precedent: dict,
    similarity_score: float
) -> SimilarityResult:
    """Create a test similarity result."""
    return SimilarityResult(
        precedent_id=precedent["precedent_id"],
        query=precedent["query"],
        decision=precedent["decision"],
        confidence=precedent["confidence"],
        similarity_score=similarity_score,
        precedent=precedent
    )


def test_basic_ranking():
    """Test basic ranking with default weights."""
    print("\n[Test 1] Basic ranking...")

    # Create test results
    precedents = [
        create_test_precedent("prec-1", "Query 1", "ALLOW", 0.9, days_old=10),
        create_test_precedent("prec-2", "Query 2", "ALLOW", 0.8, days_old=5),
        create_test_precedent("prec-3", "Query 3", "DENY", 0.85, days_old=20)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.95),
        create_test_similarity_result(precedents[1], 0.85),
        create_test_similarity_result(precedents[2], 0.90)
    ]

    ranker = PrecedentRanker()
    ranked = ranker.rank(similarity_results)

    # Check that all results are ranked
    assert len(ranked) == 3, "Should rank all 3 results"

    # Check ranks are assigned
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3

    # Check sorted by final score
    assert ranked[0].final_score >= ranked[1].final_score
    assert ranked[1].final_score >= ranked[2].final_score

    print(f"✅ Ranked {len(ranked)} precedents")
    print(f"✅ Top result: {ranked[0].precedent_id} (score: {ranked[0].final_score:.4f})")
    print(f"✅ Ranks assigned: 1, 2, 3")


def test_similarity_weight():
    """Test that similarity weight affects ranking."""
    print("\n[Test 2] Similarity weighting...")

    # Same precedent, different similarity scores
    precedents = [
        create_test_precedent("prec-high-sim", "High similarity", "ALLOW", 0.8, days_old=10),
        create_test_precedent("prec-low-sim", "Low similarity", "ALLOW", 0.8, days_old=10)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.95),
        create_test_similarity_result(precedents[1], 0.70)
    ]

    # High similarity weight
    config = RankingConfig(similarity_weight=1.0, recency_weight=0.0, confidence_weight=0.0)
    ranker = PrecedentRanker(config)
    ranked = ranker.rank(similarity_results)

    # High similarity should rank first
    assert ranked[0].precedent_id == "prec-high-sim"
    assert ranked[0].similarity_score > ranked[1].similarity_score

    print("✅ High similarity ranked first")
    print(f"✅ Similarity scores: {ranked[0].similarity_score:.2f} > {ranked[1].similarity_score:.2f}")


def test_recency_weight():
    """Test that recency weight affects ranking."""
    print("\n[Test 3] Recency weighting...")

    # Same similarity, different ages
    precedents = [
        create_test_precedent("prec-recent", "Recent", "ALLOW", 0.8, days_old=1),
        create_test_precedent("prec-old", "Old", "ALLOW", 0.8, days_old=180)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.85),
        create_test_similarity_result(precedents[1], 0.85)
    ]

    # High recency weight
    config = RankingConfig(similarity_weight=0.0, recency_weight=1.0, confidence_weight=0.0)
    ranker = PrecedentRanker(config)
    ranked = ranker.rank(similarity_results)

    # Recent should rank first
    assert ranked[0].precedent_id == "prec-recent"
    assert ranked[0].recency_score > ranked[1].recency_score

    print("✅ Recent precedent ranked first")
    print(f"✅ Recency scores: {ranked[0].recency_score:.4f} > {ranked[1].recency_score:.4f}")


def test_confidence_weight():
    """Test that confidence weight affects ranking."""
    print("\n[Test 4] Confidence weighting...")

    # Same similarity and age, different confidence
    precedents = [
        create_test_precedent("prec-high-conf", "High confidence", "ALLOW", 0.95, days_old=10),
        create_test_precedent("prec-low-conf", "Low confidence", "ALLOW", 0.70, days_old=10)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.85),
        create_test_similarity_result(precedents[1], 0.85)
    ]

    # High confidence weight
    config = RankingConfig(similarity_weight=0.0, recency_weight=0.0, confidence_weight=1.0)
    ranker = PrecedentRanker(config)
    ranked = ranker.rank(similarity_results)

    # High confidence should rank first
    assert ranked[0].precedent_id == "prec-high-conf"
    assert ranked[0].confidence_score > ranked[1].confidence_score

    print("✅ High confidence ranked first")
    print(f"✅ Confidence scores: {ranked[0].confidence_score:.2f} > {ranked[1].confidence_score:.2f}")


def test_combined_weights():
    """Test combined weighting."""
    print("\n[Test 5] Combined weighting...")

    precedents = [
        create_test_precedent("prec-1", "Balanced", "ALLOW", 0.85, days_old=30),
        create_test_precedent("prec-2", "High sim, old", "ALLOW", 0.80, days_old=180),
        create_test_precedent("prec-3", "Low sim, recent", "ALLOW", 0.90, days_old=5)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.85),
        create_test_similarity_result(precedents[1], 0.95),
        create_test_similarity_result(precedents[2], 0.70)
    ]

    # Balanced weights
    config = RankingConfig(similarity_weight=0.5, recency_weight=0.3, confidence_weight=0.2)
    ranker = PrecedentRanker(config)
    ranked = ranker.rank(similarity_results)

    # Check all component scores are computed
    for result in ranked:
        assert 0 <= result.similarity_score <= 1.0
        assert 0 <= result.recency_score <= 1.0
        assert 0 <= result.confidence_score <= 1.0
        assert result.final_score > 0

    print("✅ All component scores computed")
    print(f"✅ Top result final score: {ranked[0].final_score:.4f}")


def test_decision_boost():
    """Test decision-specific boost."""
    print("\n[Test 6] Decision boost...")

    precedents = [
        create_test_precedent("prec-allow", "ALLOW case", "ALLOW", 0.8, days_old=10),
        create_test_precedent("prec-deny", "DENY case", "DENY", 0.8, days_old=10)
    ]

    similarity_results = [
        create_test_similarity_result(precedents[0], 0.85),
        create_test_similarity_result(precedents[1], 0.85)
    ]

    # Boost DENY decisions by 50%
    config = RankingConfig(
        similarity_weight=1.0,
        recency_weight=0.0,
        confidence_weight=0.0,
        decision_boost={"DENY": 0.5}
    )
    ranker = PrecedentRanker(config)
    ranked = ranker.rank(similarity_results)

    # DENY should rank first due to boost
    assert ranked[0].decision == "DENY"

    print("✅ DENY decision boosted to rank 1")
    print(f"✅ Final scores: DENY={ranked[0].final_score:.4f}, ALLOW={ranked[1].final_score:.4f}")


def test_stable_ranking():
    """Test that ranking is stable (deterministic)."""
    print("\n[Test 7] Stable ranking...")

    precedents = [
        create_test_precedent(f"prec-{i}", f"Query {i}", "ALLOW", 0.8, days_old=10)
        for i in range(5)
    ]

    similarity_results = [
        create_test_similarity_result(p, 0.85) for p in precedents
    ]

    ranker = PrecedentRanker()

    # Rank multiple times
    ranked1 = ranker.rank(similarity_results.copy())
    ranked2 = ranker.rank(similarity_results.copy())

    # Should produce same order
    ids1 = [r.precedent_id for r in ranked1]
    ids2 = [r.precedent_id for r in ranked2]

    assert ids1 == ids2, "Rankings should be stable"

    print("✅ Rankings are deterministic")
    print(f"✅ Order: {', '.join(ids1[:3])}...")


def test_top_k():
    """Test top-k retrieval."""
    print("\n[Test 8] Top-k retrieval...")

    precedents = [
        create_test_precedent(f"prec-{i}", f"Query {i}", "ALLOW", 0.9 - i * 0.1, days_old=i * 10)
        for i in range(10)
    ]

    similarity_results = [
        create_test_similarity_result(p, 0.95 - i * 0.05) for i, p in enumerate(precedents)
    ]

    ranker = PrecedentRanker()
    ranked = ranker.rank(similarity_results)

    # Get top 3
    top3 = ranker.get_top_k(ranked, k=3)
    assert len(top3) == 3

    # Get top 5 with min score
    top5_filtered = ranker.get_top_k(ranked, k=5, min_score=0.5)
    assert all(r.final_score >= 0.5 for r in top5_filtered)

    print(f"✅ Top-3: {len(top3)} results")
    print(f"✅ Top-5 (min 0.5): {len(top5_filtered)} results")


def test_rerank():
    """Test re-ranking with custom scorer."""
    print("\n[Test 9] Re-ranking...")

    precedents = [
        create_test_precedent("prec-1", "Query 1", "ALLOW", 0.9, days_old=10),
        create_test_precedent("prec-2", "Query 2", "DENY", 0.8, days_old=5),
        create_test_precedent("prec-3", "Query 3", "ALLOW", 0.85, days_old=20)
    ]

    similarity_results = [
        create_test_similarity_result(p, 0.9 - i * 0.05) for i, p in enumerate(precedents)
    ]

    ranker = PrecedentRanker()
    ranked = ranker.rank(similarity_results)

    original_order = [r.precedent_id for r in ranked]

    # Re-rank: prioritize DENY decisions
    def custom_scorer(result):
        base_score = result.final_score
        if result.decision == "DENY":
            return base_score * 2.0
        return base_score

    reranked = ranker.rerank(ranked, custom_scorer)
    new_order = [r.precedent_id for r in reranked]

    # DENY should now be first
    assert reranked[0].decision == "DENY"
    assert original_order != new_order

    print("✅ Re-ranking successful")
    print(f"✅ Original: {', '.join(original_order)}")
    print(f"✅ Re-ranked: {', '.join(new_order)}")


def test_ranking_explanation():
    """Test ranking explanation."""
    print("\n[Test 10] Ranking explanation...")

    precedent = create_test_precedent("prec-1", "Test query", "ALLOW", 0.9, days_old=10)
    similarity_result = create_test_similarity_result(precedent, 0.95)

    ranker = PrecedentRanker()
    ranked = ranker.rank([similarity_result])

    explanation = ranker.explain_ranking(ranked[0])

    # Check explanation contains key information
    assert "Rank #1" in explanation
    assert "Final Score" in explanation
    assert "Similarity" in explanation
    assert "Recency" in explanation
    assert "Confidence" in explanation
    assert "prec-1" in explanation

    print("✅ Explanation generated")
    print("\nSample explanation:")
    print(explanation)


def test_convenience_function():
    """Test convenience function."""
    print("\n[Test 11] Convenience function...")

    precedent = create_test_precedent("prec-1", "Test", "ALLOW", 0.9, days_old=10)
    similarity_result = create_test_similarity_result(precedent, 0.95)

    ranked = rank_precedents([similarity_result], similarity_weight=0.7, recency_weight=0.2, confidence_weight=0.1)

    assert len(ranked) == 1
    assert ranked[0].rank == 1

    print("✅ Convenience function works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Precedent Ranking Tests (Task 3.4)")
    print("=" * 60)

    try:
        test_basic_ranking()
        test_similarity_weight()
        test_recency_weight()
        test_confidence_weight()
        test_combined_weights()
        test_decision_boost()
        test_stable_ranking()
        test_top_k()
        test_rerank()
        test_ranking_explanation()
        test_convenience_function()

        print("\n" + "=" * 60)
        print("✅ All 11 tests passed!")
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
