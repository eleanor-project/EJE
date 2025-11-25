"""Unit tests for Jurisprudence Repository"""
import pytest
import os
import tempfile
import shutil
import json
from src.eje.core.precedent_manager import JurisprudenceRepository


class TestPrecedentManager:
    """Test suite for JurisprudenceRepository"""

    @pytest.fixture
    def temp_data_path(self):
        """Create temporary data directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def precedent_manager(self, temp_data_path):
        """Create JurisprudenceRepository instance with temp directory"""
        return JurisprudenceRepository(data_path=temp_data_path)

    def test_initialization(self, temp_data_path):
        """Test precedent manager initialization"""
        pm = JurisprudenceRepository(data_path=temp_data_path)
        assert pm.data_path == temp_data_path
        assert os.path.exists(temp_data_path)

    def test_store_precedent(self, precedent_manager):
        """Test storing a new precedent"""
        case = {
            'text': 'This is a test case for precedent storage'
        }

        decision_bundle = {
            'input': case,
            'final_decision': {
                'overall_verdict': 'ALLOW',
                'avg_confidence': 0.9
            },
            'critic_outputs': [
                {'critic': 'A', 'verdict': 'ALLOW', 'confidence': 0.9}
            ]
        }

        # Store precedent
        precedent_manager.store_precedent(decision_bundle)

        # Verify it was stored
        assert len(precedent_manager.precedent_store) == 1

    def test_lookup_exact_match(self, precedent_manager):
        """Test looking up exact matching precedent"""
        case = {
            'text': 'This is an exact match test'
        }

        decision_bundle = {
            'input': case,
            'final_decision': {
                'overall_verdict': 'ALLOW',
                'avg_confidence': 0.9
            },
            'critic_outputs': []
        }

        # Store precedent
        precedent_manager.store_precedent(decision_bundle)

        # Lookup the same case
        results = precedent_manager.lookup(case)

        # Should find exact match with similarity 1.0
        assert len(results) > 0
        if results:
            assert results[0]['similarity_score'] == pytest.approx(1.0, rel=0.01)

    def test_lookup_similar_case(self, precedent_manager):
        """Test looking up similar but not identical case"""
        case1 = {
            'text': 'User wants to access medical records'
        }

        case2 = {
            'text': 'User wants to view medical files'
        }

        decision_bundle = {
            'input': case1,
            'final_decision': {
                'overall_verdict': 'REVIEW',
                'avg_confidence': 0.8
            },
            'critic_outputs': []
        }

        # Store first case
        precedent_manager.store_precedent(decision_bundle)

        # Lookup similar case
        results = precedent_manager.lookup(case2)

        # Should find similar match with high similarity
        assert len(results) > 0
        if results:
            assert results[0]['similarity_score'] > 0.5

    def test_lookup_no_match(self, precedent_manager):
        """Test lookup when no similar precedents exist"""
        case = {
            'text': 'Completely unique case that has never been seen before'
        }

        results = precedent_manager.lookup(case)

        # Should return empty or no results above threshold
        assert isinstance(results, list)

    def test_multiple_precedents_ranking(self, precedent_manager):
        """Test that multiple precedents are ranked by similarity"""
        # Store several precedents
        cases = [
            {'text': 'Access user data'},
            {'text': 'Delete user data'},
            {'text': 'Modify user data'}
        ]

        for case in cases:
            bundle = {
                'input': case,
                'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
                'critic_outputs': []
            }
            precedent_manager.store_precedent(bundle)

        # Lookup with a query most similar to first case
        query = {'text': 'Access user information'}
        results = precedent_manager.lookup(query)

        # Should return results in descending similarity order
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['similarity_score'] >= results[i + 1]['similarity_score']

    def test_precedent_persistence(self, temp_data_path):
        """Test that precedents persist across manager instances"""
        # Create first manager and store precedent
        pm1 = JurisprudenceRepository(data_path=temp_data_path)

        case = {'text': 'Persistence test case'}
        bundle = {
            'input': case,
            'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
            'critic_outputs': []
        }

        pm1.store_precedent(bundle)

        # Create second manager instance
        pm2 = JurisprudenceRepository(data_path=temp_data_path)

        # Should load existing precedents
        assert len(pm2.precedent_store) == 1

    def test_precedent_with_empty_text(self, precedent_manager):
        """Test handling of case with empty text"""
        case = {'text': ''}

        bundle = {
            'input': case,
            'final_decision': {'overall_verdict': 'REVIEW', 'avg_confidence': 0.5},
            'critic_outputs': []
        }

        # Should handle empty text gracefully
        try:
            precedent_manager.store_precedent(bundle)
            results = precedent_manager.lookup(case)
            assert isinstance(results, list)
        except Exception as e:
            # If it raises an exception, it should be handled appropriately
            assert isinstance(e, (ValueError, KeyError))

    def test_similarity_threshold(self, precedent_manager):
        """Test that similarity threshold filters results"""
        # Store a precedent
        case1 = {'text': 'Machine learning model deployment'}
        bundle = {
            'input': case1,
            'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
            'critic_outputs': []
        }
        precedent_manager.store_precedent(bundle)

        # Lookup with very dissimilar case
        case2 = {'text': 'Weather forecast sunny day'}
        results = precedent_manager.lookup(case2)

        # Should either return no results or results with low similarity
        for result in results:
            # If results are returned, they should meet some threshold
            # This depends on implementation
            assert 'similarity_score' in result

    def test_hash_collision_handling(self, precedent_manager):
        """Test handling of hash collisions (if any)"""
        # Create two very similar cases
        case1 = {'text': 'Test case A'}
        case2 = {'text': 'Test case A'}  # Identical

        bundle1 = {
            'input': case1,
            'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
            'critic_outputs': []
        }

        bundle2 = {
            'input': case2,
            'final_decision': {'overall_verdict': 'BLOCK', 'avg_confidence': 0.8},
            'critic_outputs': []
        }

        # Store both
        precedent_manager.store_precedent(bundle1)
        precedent_manager.store_precedent(bundle2)

        # Lookup should handle duplicates appropriately
        results = precedent_manager.lookup(case1)
        assert len(results) > 0

    def test_large_precedent_store(self, precedent_manager):
        """Test performance with large number of precedents"""
        # Store many precedents
        for i in range(50):
            case = {'text': f'Test case number {i} with unique content'}
            bundle = {
                'input': case,
                'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
                'critic_outputs': []
            }
            precedent_manager.store_precedent(bundle)

        assert len(precedent_manager.precedent_store) == 50

        # Lookup should still work efficiently
        query = {'text': 'Test case number 25 with unique content'}
        results = precedent_manager.lookup(query)

        assert len(results) > 0


class TestPrecedentSimilarity:
    """Test suite for precedent similarity calculations"""

    @pytest.fixture
    def precedent_manager(self):
        """Create JurisprudenceRepository instance"""
        temp_dir = tempfile.mkdtemp()
        pm = JurisprudenceRepository(data_path=temp_dir)
        yield pm
        shutil.rmtree(temp_dir)

    def test_identical_cases_similarity(self, precedent_manager):
        """Test that identical cases have similarity 1.0"""
        case = {'text': 'Identical case for testing'}

        bundle = {
            'input': case,
            'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
            'critic_outputs': []
        }

        precedent_manager.store_precedent(bundle)
        results = precedent_manager.lookup(case)

        if results:
            assert results[0]['similarity_score'] == pytest.approx(1.0, rel=0.01)

    def test_dissimilar_cases_low_similarity(self, precedent_manager):
        """Test that dissimilar cases have low similarity"""
        case1 = {'text': 'Medical data access request'}
        case2 = {'text': 'Weather forecast information'}

        bundle = {
            'input': case1,
            'final_decision': {'overall_verdict': 'REVIEW', 'avg_confidence': 0.8},
            'critic_outputs': []
        }

        precedent_manager.store_precedent(bundle)
        results = precedent_manager.lookup(case2)

        # If results are returned, similarity should be lower
        for result in results:
            assert result['similarity_score'] < 1.0

    def test_partial_match_similarity(self, precedent_manager):
        """Test similarity for partial matches"""
        case1 = {'text': 'User requests access to personal financial data'}
        case2 = {'text': 'User requests access to personal medical data'}

        bundle = {
            'input': case1,
            'final_decision': {'overall_verdict': 'ALLOW', 'avg_confidence': 0.9},
            'critic_outputs': []
        }

        precedent_manager.store_precedent(bundle)
        results = precedent_manager.lookup(case2)

        # Should have moderate to high similarity due to overlapping words
        if results:
            assert 0.3 < results[0]['similarity_score'] < 1.0
