"""
Precedent Similarity Search and Ranking

Provides comprehensive similarity search and ranking functionality for precedent retrieval.
Supports multiple search strategies, hybrid ranking, and configurable filtering.

Features:
- Multiple similarity metrics (cosine, euclidean, dot product)
- Hybrid search (semantic + metadata filtering)
- Multi-factor ranking (similarity, recency, confidence, outcome alignment)
- Configurable weighting and thresholds
- Support for both SQL and vector backends
- Caching for performance
"""

import hashlib
import pickle
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import numpy as np

from .embeddings import embed_text
from .sql_store import SQLPrecedentStore
from .vector_manager import VectorPrecedentManager
from ...utils.logging import get_logger


logger = get_logger("ejc.precedent.search")


@dataclass
class SearchConfig:
    """Configuration for precedent search"""
    # Similarity settings
    similarity_metric: str = 'cosine'  # cosine, euclidean, dot_product
    min_similarity: float = 0.0
    max_results: int = 10

    # Ranking weights
    similarity_weight: float = 0.6
    recency_weight: float = 0.2
    confidence_weight: float = 0.15
    outcome_weight: float = 0.05

    # Filters
    filter_verdict: Optional[str] = None
    filter_min_confidence: Optional[float] = None
    filter_max_ambiguity: Optional[float] = None
    filter_timeframe_days: Optional[int] = None

    # Recency scoring
    recency_decay_days: int = 365  # Days until half value

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class ScoredPrecedent:
    """Precedent with similarity and ranking scores"""
    precedent: Dict[str, Any]
    similarity_score: float
    recency_score: float
    confidence_score: float
    outcome_score: float
    final_score: float
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with scores"""
        result = self.precedent.copy()
        result['scores'] = {
            'similarity': self.similarity_score,
            'recency': self.recency_score,
            'confidence': self.confidence_score,
            'outcome': self.outcome_score,
            'final': self.final_score
        }
        result['rank'] = self.rank
        return result


class SimilaritySearchWrapper:
    """
    Unified similarity search wrapper for precedent retrieval.

    Provides advanced search and ranking capabilities across different
    storage backends (SQL and vector databases).
    """

    def __init__(
        self,
        store: Any,  # SQLPrecedentStore or VectorPrecedentManager
        embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2',
        config: Optional[SearchConfig] = None
    ):
        """
        Initialize similarity search wrapper.

        Args:
            store: Precedent storage backend
            embedding_model: Model for generating embeddings
            config: Search configuration
        """
        self.store = store
        self.embedding_model = embedding_model
        self.config = config or SearchConfig()

        # Cache for embeddings and search results
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._search_cache: Dict[str, Tuple[List[ScoredPrecedent], float]] = {}

    def search(
        self,
        query_text: str,
        query_context: Optional[Dict[str, Any]] = None,
        config: Optional[SearchConfig] = None
    ) -> List[ScoredPrecedent]:
        """
        Search for similar precedents with advanced ranking.

        Args:
            query_text: Query text for similarity matching
            query_context: Additional context for filtering
            config: Override search configuration

        Returns:
            List of scored precedents, sorted by rank
        """
        config = config or self.config

        # Check cache
        cache_key = self._compute_cache_key(query_text, query_context, config)
        if config.cache_enabled:
            cached = self._get_cached_results(cache_key)
            if cached:
                logger.debug("Returning cached search results")
                return cached

        # Generate query embedding
        query_embedding = self._get_embedding(query_text)

        # Retrieve candidate precedents
        candidates = self._retrieve_candidates(query_embedding, query_context, config)

        # Score and rank
        scored = self._score_precedents(
            candidates,
            query_embedding,
            query_context,
            config
        )

        # Cache results
        if config.cache_enabled:
            self._cache_results(cache_key, scored)

        logger.info(f"Found {len(scored)} precedents for query")
        return scored

    def search_by_case(
        self,
        case_data: Dict[str, Any],
        config: Optional[SearchConfig] = None
    ) -> List[ScoredPrecedent]:
        """
        Search for precedents similar to a complete case.

        Args:
            case_data: Case data including input, context, and metadata
            config: Override search configuration

        Returns:
            List of scored precedents
        """
        query_text = case_data.get('input', {}).get('text', case_data.get('input_text', ''))
        query_context = case_data.get('input', {}).get('context', case_data.get('input_context', {}))

        return self.search(query_text, query_context, config)

    def _retrieve_candidates(
        self,
        query_embedding: np.ndarray,
        query_context: Optional[Dict[str, Any]],
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """Retrieve candidate precedents from storage"""
        # Vector database retrieval
        if isinstance(self.store, VectorPrecedentManager):
            return self._retrieve_from_vector_db(query_embedding, config)

        # SQL database retrieval
        elif isinstance(self.store, SQLPrecedentStore):
            return self._retrieve_from_sql(query_embedding, config)

        else:
            raise ValueError(f"Unsupported store type: {type(self.store)}")

    def _retrieve_from_vector_db(
        self,
        query_embedding: np.ndarray,
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """Retrieve from vector database"""
        try:
            # Use vector manager's search
            results = self.store.client.search(
                collection_name=self.store.collection_name,
                query_vector=query_embedding.tolist(),
                limit=config.max_results * 2,  # Get more for filtering
                score_threshold=config.min_similarity
            )

            precedents = []
            for result in results:
                precedent = result.payload
                precedent['similarity'] = result.score
                precedent['embedding'] = result.vector
                precedents.append(precedent)

            return precedents

        except Exception as e:
            logger.error(f"Vector DB retrieval failed: {str(e)}")
            return []

    def _retrieve_from_sql(
        self,
        query_embedding: np.ndarray,
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """Retrieve from SQL database with semantic similarity"""
        try:
            # Query precedents with basic filters
            precedents = self.store.query_precedents(
                verdict=config.filter_verdict,
                min_confidence=config.filter_min_confidence,
                max_ambiguity=config.filter_max_ambiguity,
                limit=config.max_results * 3  # Get more for similarity filtering
            )

            # Compute similarity scores
            scored_precedents = []
            for precedent in precedents:
                # Get stored embedding
                with self.store.get_session() as session:
                    from .sql_store import PrecedentEmbedding
                    emb_record = session.query(PrecedentEmbedding).filter_by(
                        precedent_id=precedent['id']
                    ).first()

                    if emb_record:
                        prec_embedding = pickle.loads(emb_record.embedding)
                        similarity = self._compute_similarity(
                            query_embedding,
                            prec_embedding,
                            config.similarity_metric
                        )

                        if similarity >= config.min_similarity:
                            precedent['similarity'] = similarity
                            scored_precedents.append(precedent)

            # Sort by similarity
            scored_precedents.sort(key=lambda x: x['similarity'], reverse=True)

            return scored_precedents[:config.max_results * 2]

        except Exception as e:
            logger.error(f"SQL retrieval failed: {str(e)}")
            return []

    def _score_precedents(
        self,
        candidates: List[Dict[str, Any]],
        query_embedding: np.ndarray,
        query_context: Optional[Dict[str, Any]],
        config: SearchConfig
    ) -> List[ScoredPrecedent]:
        """Score and rank precedents using multiple factors"""
        scored = []

        for precedent in candidates:
            # Similarity score (already computed)
            similarity_score = precedent.get('similarity', 0.0)

            # Recency score
            recency_score = self._compute_recency_score(
                precedent.get('timestamp'),
                config.recency_decay_days
            )

            # Confidence score
            confidence_score = precedent.get('final_decision', {}).get('avg_confidence', 0.5)
            if confidence_score is None:
                confidence_score = precedent.get('avg_confidence', 0.5) or 0.5

            # Outcome alignment score
            outcome_score = self._compute_outcome_score(
                precedent,
                query_context
            )

            # Compute weighted final score
            final_score = (
                similarity_score * config.similarity_weight +
                recency_score * config.recency_weight +
                confidence_score * config.confidence_weight +
                outcome_score * config.outcome_weight
            )

            scored.append(ScoredPrecedent(
                precedent=precedent,
                similarity_score=similarity_score,
                recency_score=recency_score,
                confidence_score=confidence_score,
                outcome_score=outcome_score,
                final_score=final_score
            ))

        # Sort by final score
        scored.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks
        for rank, item in enumerate(scored, 1):
            item.rank = rank

        # Limit to max results
        return scored[:config.max_results]

    def _compute_similarity(
        self,
        vec_a: np.ndarray,
        vec_b: np.ndarray,
        metric: str
    ) -> float:
        """Compute similarity between vectors"""
        if metric == 'cosine':
            return self._cosine_similarity(vec_a, vec_b)
        elif metric == 'euclidean':
            return self._euclidean_similarity(vec_a, vec_b)
        elif metric == 'dot_product':
            return self._dot_product_similarity(vec_a, vec_b)
        else:
            logger.warning(f"Unknown metric '{metric}', using cosine")
            return self._cosine_similarity(vec_a, vec_b)

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Cosine similarity"""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def _euclidean_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Euclidean distance converted to similarity"""
        distance = np.linalg.norm(vec_a - vec_b)
        # Convert to similarity (0-1 range, inverse of distance)
        return float(1.0 / (1.0 + distance))

    def _dot_product_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Dot product similarity (normalized)"""
        dot = np.dot(vec_a, vec_b)
        # Normalize to 0-1 range
        return float((dot + 1.0) / 2.0)

    def _compute_recency_score(
        self,
        timestamp: Any,
        decay_days: int
    ) -> float:
        """Compute recency score with exponential decay"""
        try:
            if isinstance(timestamp, str):
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                ts = timestamp
            else:
                return 0.5  # Default for missing timestamp

            age_days = (datetime.utcnow() - ts).days

            # Exponential decay: score = exp(-age / decay_constant)
            # Half-life at decay_days
            decay_constant = decay_days / np.log(2)
            score = np.exp(-age_days / decay_constant)

            return float(score)

        except Exception as e:
            logger.warning(f"Failed to compute recency score: {str(e)}")
            return 0.5

    def _compute_outcome_score(
        self,
        precedent: Dict[str, Any],
        query_context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Compute outcome alignment score.

        Checks if precedent outcome aligns with query expectations.
        """
        if not query_context or 'expected_verdict' not in query_context:
            return 0.5  # Neutral if no expectation

        expected = query_context['expected_verdict']
        actual = precedent.get('final_decision', {}).get('overall_verdict')
        if actual is None:
            actual = precedent.get('final_verdict')

        if actual == expected:
            return 1.0
        else:
            return 0.0

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding with caching"""
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        embedding = embed_text(text, self.embedding_model)
        self._embedding_cache[cache_key] = embedding

        return embedding

    def _compute_cache_key(
        self,
        query_text: str,
        query_context: Optional[Dict[str, Any]],
        config: SearchConfig
    ) -> str:
        """Compute cache key for search results"""
        import json

        key_data = {
            'query': query_text,
            'context': query_context or {},
            'config': {
                'similarity_metric': config.similarity_metric,
                'min_similarity': config.min_similarity,
                'max_results': config.max_results,
                'filter_verdict': config.filter_verdict,
                'filter_min_confidence': config.filter_min_confidence
            }
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_results(self, cache_key: str) -> Optional[List[ScoredPrecedent]]:
        """Get cached search results if still valid"""
        if cache_key not in self._search_cache:
            return None

        results, timestamp = self._search_cache[cache_key]
        age = datetime.utcnow().timestamp() - timestamp

        if age > self.config.cache_ttl_seconds:
            # Cache expired
            del self._search_cache[cache_key]
            return None

        return results

    def _cache_results(self, cache_key: str, results: List[ScoredPrecedent]):
        """Cache search results"""
        self._search_cache[cache_key] = (results, datetime.utcnow().timestamp())

        # Limit cache size (keep most recent 100 entries)
        if len(self._search_cache) > 100:
            # Remove oldest entry
            oldest_key = min(self._search_cache.keys(),
                           key=lambda k: self._search_cache[k][1])
            del self._search_cache[oldest_key]

    def clear_cache(self):
        """Clear all caches"""
        self._embedding_cache.clear()
        self._search_cache.clear()
        logger.info("Cleared search caches")


class PrecedentRanker:
    """
    Advanced precedent ranking with customizable strategies.

    Provides flexible ranking beyond simple similarity scoring.
    """

    def __init__(self):
        """Initialize precedent ranker"""
        self.ranking_strategies = {
            'similarity': self._rank_by_similarity,
            'recency': self._rank_by_recency,
            'confidence': self._rank_by_confidence,
            'hybrid': self._rank_hybrid
        }

    def rank(
        self,
        precedents: List[Dict[str, Any]],
        strategy: str = 'hybrid',
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank precedents using specified strategy.

        Args:
            precedents: List of precedent dictionaries
            strategy: Ranking strategy ('similarity', 'recency', 'confidence', 'hybrid')
            weights: Custom weights for hybrid ranking

        Returns:
            Ranked list of precedents
        """
        if strategy not in self.ranking_strategies:
            logger.warning(f"Unknown strategy '{strategy}', using 'hybrid'")
            strategy = 'hybrid'

        ranking_fn = self.ranking_strategies[strategy]
        return ranking_fn(precedents, weights)

    def _rank_by_similarity(
        self,
        precedents: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Rank purely by similarity score"""
        return sorted(precedents, key=lambda x: x.get('similarity', 0.0), reverse=True)

    def _rank_by_recency(
        self,
        precedents: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Rank by timestamp (newest first)"""
        def get_timestamp(p):
            ts = p.get('timestamp')
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    return datetime.min
            elif isinstance(ts, datetime):
                return ts
            return datetime.min

        return sorted(precedents, key=get_timestamp, reverse=True)

    def _rank_by_confidence(
        self,
        precedents: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Rank by average confidence"""
        def get_confidence(p):
            final_decision = p.get('final_decision', {})
            return final_decision.get('avg_confidence', p.get('avg_confidence', 0.0)) or 0.0

        return sorted(precedents, key=get_confidence, reverse=True)

    def _rank_hybrid(
        self,
        precedents: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Rank using weighted combination of factors"""
        if weights is None:
            weights = {
                'similarity': 0.5,
                'recency': 0.3,
                'confidence': 0.2
            }

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        # Compute scores
        for precedent in precedents:
            similarity = precedent.get('similarity', 0.0)

            # Recency score
            ts = precedent.get('timestamp')
            if ts:
                try:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    age_days = (datetime.utcnow() - ts).days
                    recency = np.exp(-age_days / 365.0)  # Decay over 1 year
                except:
                    recency = 0.5
            else:
                recency = 0.5

            # Confidence score
            final_decision = precedent.get('final_decision', {})
            confidence = final_decision.get('avg_confidence', precedent.get('avg_confidence', 0.5)) or 0.5

            # Weighted score
            score = (
                similarity * weights.get('similarity', 0.5) +
                recency * weights.get('recency', 0.3) +
                confidence * weights.get('confidence', 0.2)
            )

            precedent['rank_score'] = score

        return sorted(precedents, key=lambda x: x.get('rank_score', 0.0), reverse=True)


# Convenience functions

def search_precedents(
    query_text: str,
    store: Any,
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2',
    max_results: int = 10,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Convenience function for simple precedent search.

    Args:
        query_text: Query text
        store: Precedent storage backend
        embedding_model: Embedding model to use
        max_results: Maximum results to return
        min_similarity: Minimum similarity threshold

    Returns:
        List of ranked precedent dictionaries with scores
    """
    config = SearchConfig(
        max_results=max_results,
        min_similarity=min_similarity
    )

    searcher = SimilaritySearchWrapper(store, embedding_model, config)
    scored = searcher.search(query_text)

    return [s.to_dict() for s in scored]
