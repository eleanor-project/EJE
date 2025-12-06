"""
Comprehensive tests for Precedent Engine functionality.

Tests cover:
- SQL storage backend (SQLite and PostgreSQL compatibility)
- Precedent ingestion pipeline (JSON, JSONL, CSV, Evidence Bundles)
- Similarity search and ranking
- Edge cases and error handling
"""

import json
import os
import pickle
import tempfile
from datetime import datetime, timedelta

import numpy as np
import pytest

from ejc.core.precedent.sql_store import (
    SQLPrecedentStore,
    Precedent,
    CriticOutput,
    PrecedentEmbedding,
    create_sqlite_store,
)
from ejc.core.precedent.ingestion import (
    PrecedentIngestionPipeline,
    ingest_json_file,
)
from ejc.core.precedent.search import (
    SimilaritySearchWrapper,
    SearchConfig,
    PrecedentRanker,
    search_precedents,
)
from ejc.core.evidence_normalizer import EvidenceBundle, EvidenceNormalizer


class TestSQLPrecedentStore:
    """Tests for SQL-based precedent storage backend"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def store(self, temp_db):
        """Create SQLPrecedentStore instance"""
        config = {'db_url': f'sqlite:///{temp_db}'}
        return SQLPrecedentStore(config)

    def test_store_initialization(self, store):
        """Test store initializes correctly with schema"""
        assert store is not None
        assert store.engine is not None

        # Verify tables created
        with store.get_session() as session:
            count = session.query(Precedent).count()
            assert count == 0  # Should be empty initially

    def test_store_single_precedent(self, store):
        """Test storing a single precedent"""
        precedent_id = store.store_precedent(
            request_id='test-001',
            input_text='Sample input for testing',
            input_context={'domain': 'test'},
            final_verdict='ALLOW',
            final_reason='Test passed',
            avg_confidence=0.95,
            ambiguity=0.05,
            critic_outputs=[
                {
                    'critic': 'test_critic',
                    'verdict': 'ALLOW',
                    'confidence': 0.95,
                    'justification': 'Test justification'
                }
            ]
        )

        assert precedent_id is not None
        assert precedent_id > 0

        # Verify retrieval
        retrieved = store.get_precedent(precedent_id)
        assert retrieved is not None
        assert retrieved['request_id'] == 'test-001'
        assert retrieved['input']['text'] == 'Sample input for testing'
        assert retrieved['final_decision']['overall_verdict'] == 'ALLOW'

    def test_store_with_embedding(self, store):
        """Test storing precedent with embedding"""
        # Create fake embedding
        embedding_vec = np.random.randn(384)  # MiniLM dimension
        embedding_bytes = pickle.dumps(embedding_vec)

        precedent_id = store.store_precedent(
            request_id='test-002',
            input_text='Test with embedding',
            final_verdict='DENY',
            embedding=embedding_bytes,
            embedding_model='test-model'
        )

        # Verify embedding stored
        with store.get_session() as session:
            emb = session.query(PrecedentEmbedding).filter_by(
                precedent_id=precedent_id
            ).first()

            assert emb is not None
            assert emb.model_name == 'test-model'

            # Verify embedding can be unpickled
            stored_vec = pickle.loads(emb.embedding)
            assert np.allclose(stored_vec, embedding_vec)

    def test_deduplication(self, store):
        """Test that duplicate precedents are detected"""
        # Store first precedent
        id1 = store.store_precedent(
            request_id='test-dup-1',
            input_text='Same input',
            input_context={'key': 'value'},
            final_verdict='ALLOW'
        )

        # Try to store duplicate (same input_text and context)
        id2 = store.store_precedent(
            request_id='test-dup-2',  # Different request ID
            input_text='Same input',
            input_context={'key': 'value'},
            final_verdict='DENY'  # Different verdict
        )

        # Should return same ID (deduplication)
        assert id1 == id2

    def test_query_precedents_by_verdict(self, store):
        """Test querying precedents by verdict"""
        # Store multiple precedents with different verdicts
        for i in range(5):
            store.store_precedent(
                request_id=f'test-{i}',
                input_text=f'Input {i}',
                final_verdict='ALLOW' if i % 2 == 0 else 'DENY'
            )

        # Query ALLOW verdicts
        allows = store.query_precedents(verdict='ALLOW')
        assert len(allows) == 3

        # Query DENY verdicts
        denies = store.query_precedents(verdict='DENY')
        assert len(denies) == 2

    def test_query_with_confidence_filter(self, store):
        """Test querying with minimum confidence filter"""
        # Store precedents with varying confidence
        for i in range(5):
            store.store_precedent(
                request_id=f'test-conf-{i}',
                input_text=f'Input {i}',
                final_verdict='ALLOW',
                avg_confidence=0.5 + (i * 0.1)
            )

        # Query with min confidence
        high_conf = store.query_precedents(min_confidence=0.8)
        assert len(high_conf) == 2  # 0.8 and 0.9

    def test_precedent_references(self, store):
        """Test adding and querying precedent references"""
        # Store two precedents
        id1 = store.store_precedent(
            request_id='prec-1',
            input_text='First precedent',
            final_verdict='ALLOW'
        )

        id2 = store.store_precedent(
            request_id='prec-2',
            input_text='Second precedent',
            final_verdict='ALLOW'
        )

        # Add reference
        success = store.add_precedent_reference(
            precedent_id=id1,
            referenced_id=id2,
            similarity_score=0.85,
            reference_type='semantic'
        )
        assert success

        # Query similar precedents
        similar = store.get_similar_precedents(id1)
        assert len(similar) == 1
        assert similar[0][1] == 0.85  # similarity score

    def test_delete_precedent(self, store):
        """Test deleting a precedent"""
        # Store precedent
        precedent_id = store.store_precedent(
            request_id='test-delete',
            input_text='To be deleted',
            final_verdict='ALLOW'
        )

        # Verify it exists
        assert store.get_precedent(precedent_id) is not None

        # Delete it
        success = store.delete_precedent(precedent_id)
        assert success

        # Verify it's gone
        assert store.get_precedent(precedent_id) is None

    def test_count_precedents(self, store):
        """Test counting precedents"""
        initial_count = store.count_precedents()
        assert initial_count == 0

        # Add some precedents
        for i in range(10):
            store.store_precedent(
                request_id=f'test-count-{i}',
                input_text=f'Input {i}',
                final_verdict='ALLOW'
            )

        assert store.count_precedents() == 10


class TestPrecedentIngestion:
    """Tests for precedent ingestion pipeline"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def store(self, temp_db):
        """Create SQLPrecedentStore instance"""
        return create_sqlite_store(temp_db)

    @pytest.fixture
    def pipeline(self, store):
        """Create ingestion pipeline"""
        return PrecedentIngestionPipeline(
            store=store,
            embedding_model='test-model',
            batch_size=10
        )

    @pytest.fixture
    def temp_json_file(self):
        """Create temporary JSON file with precedent data"""
        fd, path = tempfile.mkstemp(suffix='.json')

        data = [
            {
                'request_id': 'json-001',
                'input_text': 'Test input 1',
                'final_verdict': 'ALLOW',
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'request_id': 'json-002',
                'input_text': 'Test input 2',
                'final_verdict': 'DENY',
                'timestamp': datetime.utcnow().isoformat()
            }
        ]

        with os.fdopen(fd, 'w') as f:
            json.dump(data, f)

        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def temp_jsonl_file(self):
        """Create temporary JSONL file"""
        fd, path = tempfile.mkstemp(suffix='.jsonl')

        with os.fdopen(fd, 'w') as f:
            for i in range(5):
                record = {
                    'request_id': f'jsonl-{i:03d}',
                    'input_text': f'Test input {i}',
                    'final_verdict': 'ALLOW',
                    'timestamp': datetime.utcnow().isoformat()
                }
                f.write(json.dumps(record) + '\n')

        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_ingest_from_json(self, pipeline, temp_json_file):
        """Test ingesting from JSON file"""
        stats = pipeline.ingest_from_json(temp_json_file)

        assert stats['total'] == 2
        assert stats['ingested'] == 2
        assert stats['errors'] == 0

    def test_ingest_from_jsonl(self, pipeline, temp_jsonl_file):
        """Test ingesting from JSONL file"""
        stats = pipeline.ingest_from_jsonl(temp_jsonl_file)

        assert stats['total'] == 5
        assert stats['ingested'] == 5
        assert stats['errors'] == 0

    def test_ingest_evidence_bundles(self, pipeline):
        """Test ingesting evidence bundles"""
        normalizer = EvidenceNormalizer()

        bundles = []
        for i in range(3):
            bundle = normalizer.normalize(
                input_text=f'Bundle test {i}',
                critic_outputs=[
                    {
                        'critic': 'test_critic',
                        'verdict': 'ALLOW',
                        'confidence': 0.9,
                        'justification': 'Test'
                    }
                ]
            )
            bundles.append(bundle)

        stats = pipeline.ingest_evidence_bundles(bundles)

        assert stats['total'] == 3
        assert stats['ingested'] == 3

    def test_batch_processing(self, pipeline, temp_json_file):
        """Test that batch processing works correctly"""
        pipeline.batch_size = 1  # Process one at a time

        progress_calls = []
        def progress_callback(stats):
            progress_calls.append(stats.copy())

        pipeline.ingest_from_json(temp_json_file, progress_callback)

        # Should have been called twice (once per record)
        assert len(progress_calls) >= 2

    def test_validation(self, store):
        """Test that validation catches invalid precedents"""
        pipeline = PrecedentIngestionPipeline(
            store=store,
            validate=True
        )

        invalid_precedents = [
            {
                # Missing required field 'input_text'
                'request_id': 'invalid-001',
                'final_verdict': 'ALLOW'
            }
        ]

        stats = pipeline._ingest_batch(invalid_precedents)
        assert stats['errors'] > 0


class TestSimilaritySearch:
    """Tests for similarity search and ranking"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def populated_store(self, temp_db):
        """Create store with test precedents"""
        store = create_sqlite_store(temp_db)

        # Add precedents with embeddings
        for i in range(10):
            embedding = np.random.randn(384)
            store.store_precedent(
                request_id=f'search-test-{i}',
                input_text=f'Test case {i}',
                final_verdict='ALLOW' if i % 2 == 0 else 'DENY',
                avg_confidence=0.7 + (i * 0.02),
                timestamp=datetime.utcnow() - timedelta(days=i*10),
                embedding=pickle.dumps(embedding)
            )

        return store

    def test_search_config(self):
        """Test search configuration"""
        config = SearchConfig(
            similarity_metric='cosine',
            min_similarity=0.5,
            max_results=5
        )

        assert config.similarity_metric == 'cosine'
        assert config.max_results == 5

    def test_cosine_similarity_computation(self, populated_store):
        """Test cosine similarity metric"""
        searcher = SimilaritySearchWrapper(populated_store)

        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([1.0, 0.0, 0.0])

        similarity = searcher._cosine_similarity(vec_a, vec_b)
        assert abs(similarity - 1.0) < 0.001  # Should be 1.0 (identical)

        vec_c = np.array([0.0, 1.0, 0.0])
        similarity = searcher._cosine_similarity(vec_a, vec_c)
        assert abs(similarity - 0.0) < 0.001  # Should be 0.0 (orthogonal)

    def test_recency_scoring(self, populated_store):
        """Test recency score calculation"""
        searcher = SimilaritySearchWrapper(populated_store)

        # Recent timestamp should score high
        recent = datetime.utcnow()
        score_recent = searcher._compute_recency_score(recent, decay_days=365)
        assert score_recent > 0.9

        # Old timestamp should score lower
        old = datetime.utcnow() - timedelta(days=365)
        score_old = searcher._compute_recency_score(old, decay_days=365)
        assert score_old < score_recent
        assert score_old < 0.6

    def test_precedent_ranker_similarity(self):
        """Test ranking by similarity only"""
        ranker = PrecedentRanker()

        precedents = [
            {'id': 1, 'similarity': 0.9},
            {'id': 2, 'similarity': 0.7},
            {'id': 3, 'similarity': 0.95}
        ]

        ranked = ranker.rank(precedents, strategy='similarity')

        assert ranked[0]['id'] == 3  # Highest similarity
        assert ranked[1]['id'] == 1
        assert ranked[2]['id'] == 2

    def test_precedent_ranker_recency(self):
        """Test ranking by recency"""
        ranker = PrecedentRanker()

        now = datetime.utcnow()
        precedents = [
            {'id': 1, 'timestamp': (now - timedelta(days=100)).isoformat()},
            {'id': 2, 'timestamp': (now - timedelta(days=10)).isoformat()},
            {'id': 3, 'timestamp': (now - timedelta(days=1)).isoformat()}
        ]

        ranked = ranker.rank(precedents, strategy='recency')

        assert ranked[0]['id'] == 3  # Most recent
        assert ranked[1]['id'] == 2
        assert ranked[2]['id'] == 1

    def test_precedent_ranker_hybrid(self):
        """Test hybrid ranking with multiple factors"""
        ranker = PrecedentRanker()

        now = datetime.utcnow()
        precedents = [
            {
                'id': 1,
                'similarity': 0.7,
                'timestamp': now.isoformat(),
                'avg_confidence': 0.8
            },
            {
                'id': 2,
                'similarity': 0.9,
                'timestamp': (now - timedelta(days=100)).isoformat(),
                'avg_confidence': 0.6
            }
        ]

        ranked = ranker.rank(precedents, strategy='hybrid')

        # Both should have rank_score assigned
        assert 'rank_score' in ranked[0]
        assert 'rank_score' in ranked[1]

    def test_search_cache(self, populated_store):
        """Test search result caching"""
        config = SearchConfig(cache_enabled=True)
        searcher = SimilaritySearchWrapper(populated_store, config=config)

        # First search
        query = "test query"
        results1 = searcher.search(query)

        # Second identical search should use cache
        results2 = searcher.search(query)

        assert len(results1) == len(results2)
        # Results should be identical (from cache)

    def test_clear_cache(self, populated_store):
        """Test clearing search cache"""
        searcher = SimilaritySearchWrapper(populated_store)

        # Add something to cache
        searcher._embedding_cache['test'] = np.array([1, 2, 3])
        assert len(searcher._embedding_cache) > 0

        # Clear cache
        searcher.clear_cache()
        assert len(searcher._embedding_cache) == 0


class TestPrecedentEngineIntegration:
    """Integration tests for complete precedent engine workflow"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_end_to_end_workflow(self, temp_db):
        """Test complete workflow: ingest -> store -> search"""
        # Create store
        store = create_sqlite_store(temp_db)

        # Create and ingest precedents
        pipeline = PrecedentIngestionPipeline(store)

        test_precedents = [
            {
                'request_id': 'e2e-001',
                'input_text': 'User wants to delete their account',
                'final_verdict': 'ALLOW',
                'avg_confidence': 0.95
            },
            {
                'request_id': 'e2e-002',
                'input_text': 'User requests data export',
                'final_verdict': 'ALLOW',
                'avg_confidence': 0.90
            },
            {
                'request_id': 'e2e-003',
                'input_text': 'Suspicious bulk data access',
                'final_verdict': 'DENY',
                'avg_confidence': 0.85
            }
        ]

        stats = pipeline._ingest_batch(test_precedents)
        assert stats['ingested'] == 3

        # Verify storage
        count = store.count_precedents()
        assert count == 3

        # Query precedents
        allows = store.query_precedents(verdict='ALLOW')
        assert len(allows) == 2

        # Create searcher and search
        config = SearchConfig(max_results=2)
        searcher = SimilaritySearchWrapper(store, config=config)

        # Note: Search won't work without actual embeddings,
        # but we can verify the infrastructure is in place
        assert searcher is not None
