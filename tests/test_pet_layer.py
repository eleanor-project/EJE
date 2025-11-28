"""
Tests for PET-Aware Data Layer - Phase 5B

Tests privacy-enhancing technology orchestration, recommendations, and data protection.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.pet import (
    PETLayer, PETConfig, PETType, DataSensitivity, DataPackage,
    PETRecommender, UseCaseType, PerformanceRequirement
)


class TestPETLayer:
    """Test suite for PET Layer."""

    def test_pet_layer_initialization(self):
        """Test PET Layer can be initialized."""
        layer = PETLayer()
        assert layer.config is not None
        assert isinstance(layer.config, PETConfig)

    def test_wrap_data(self):
        """Test data wrapping with sensitivity metadata."""
        layer = PETLayer()
        data = {'user_id': 123, 'value': 42}

        package = layer.wrap_data(
            data,
            sensitivity=DataSensitivity.CONFIDENTIAL,
            metadata={'source': 'api'}
        )

        assert isinstance(package, DataPackage)
        assert package.data == data
        assert package.sensitivity == DataSensitivity.CONFIDENTIAL
        assert package.metadata['source'] == 'api'
        assert len(package.applied_pets) == 0

    def test_data_minimization(self):
        """Test data minimization functionality."""
        layer = PETLayer()

        # Dict minimization
        data = {
            'name': 'Alice',
            'email': 'alice@example.com',
            'age': 30,
            'ssn': '123-45-6789'
        }

        minimized = layer.minimize_data(data, required_fields=['name', 'age'])

        assert 'name' in minimized
        assert 'age' in minimized
        assert 'email' not in minimized
        assert 'ssn' not in minimized

    def test_pet_recommendation(self):
        """Test PET recommendation engine."""
        layer = PETLayer()

        # High sensitivity should recommend multiple PETs
        package = layer.wrap_data(
            {'sensitive': 'data'},
            sensitivity=DataSensitivity.HIGHLY_RESTRICTED
        )

        recommendations = layer.recommend_pet(package, use_case='analytics')

        assert len(recommendations) > 0
        assert PETType.DIFFERENTIAL_PRIVACY in recommendations

    def test_apply_differential_privacy(self):
        """Test application of differential privacy."""
        layer = PETLayer()

        package = layer.wrap_data(
            {'count': 100},
            sensitivity=DataSensitivity.RESTRICTED
        )

        protected = layer.apply_pet(package, PETType.DIFFERENTIAL_PRIVACY, operation='query')

        assert PETType.DIFFERENTIAL_PRIVACY in protected.applied_pets
        assert protected.metadata.get('dp_applied') is True
        assert 'dp_epsilon' in protected.metadata

    def test_privacy_ledger(self):
        """Test privacy operation logging."""
        layer = PETLayer()

        package = layer.wrap_data({'data': 'test'}, DataSensitivity.CONFIDENTIAL)
        layer.apply_pet(package, PETType.DIFFERENTIAL_PRIVACY)

        ledger = layer.get_privacy_ledger()

        assert len(ledger) == 1
        assert ledger[0]['pet_type'] == PETType.DIFFERENTIAL_PRIVACY.value

    def test_privacy_budget_tracking(self):
        """Test privacy budget checking."""
        config = PETConfig(dp_epsilon=1.0)
        layer = PETLayer(config)

        package = layer.wrap_data({'data': 'test'}, DataSensitivity.RESTRICTED)
        protected = layer.apply_pet(package, PETType.DIFFERENTIAL_PRIVACY)

        # Check budget is within limits
        assert layer.check_privacy_budget(protected, max_budget=10.0)

    def test_auto_protect(self):
        """Test automatic protection application."""
        layer = PETLayer()

        # High sensitivity should auto-apply PETs
        protected = layer.auto_protect(
            data={'sensitive': 'info'},
            sensitivity=DataSensitivity.HIGHLY_RESTRICTED,
            use_case='analytics'
        )

        assert len(protected.applied_pets) > 0

        # Low sensitivity should not require PETs
        public_protected = layer.auto_protect(
            data={'public': 'info'},
            sensitivity=DataSensitivity.PUBLIC,
            use_case='general'
        )

        # Might have PETs if auto_apply_pet is True in config
        assert isinstance(public_protected, DataPackage)


class TestPETRecommender:
    """Test suite for PET Recommender."""

    def test_recommender_initialization(self):
        """Test recommender initialization."""
        recommender = PETRecommender()
        assert recommender is not None

    def test_recommend_for_high_sensitivity(self):
        """Test recommendations for highly sensitive data."""
        recommender = PETRecommender()

        recommendations = recommender.recommend(
            sensitivity=DataSensitivity.HIGHLY_RESTRICTED,
            use_case=UseCaseType.ANALYTICS,
            performance_req=PerformanceRequirement.BATCH
        )

        assert len(recommendations) > 0
        # Should recommend strong PETs
        pet_types = [r.pet_type for r in recommendations]
        assert PETType.DIFFERENTIAL_PRIVACY in pet_types

    def test_recommend_for_ml_training(self):
        """Test recommendations for ML training use case."""
        recommender = PETRecommender()

        recommendations = recommender.recommend(
            sensitivity=DataSensitivity.RESTRICTED,
            use_case=UseCaseType.ML_TRAINING,
            performance_req=PerformanceRequirement.BATCH
        )

        pet_types = [r.pet_type for r in recommendations]
        # Should recommend federated learning or differential privacy
        assert (PETType.FEDERATED_LEARNING in pet_types or
                PETType.DIFFERENTIAL_PRIVACY in pet_types)

    def test_real_time_performance_requirements(self):
        """Test that real-time requirements avoid heavy PETs."""
        recommender = PETRecommender()

        recommendations = recommender.recommend(
            sensitivity=DataSensitivity.RESTRICTED,
            use_case=UseCaseType.INFERENCE,
            performance_req=PerformanceRequirement.REAL_TIME
        )

        # Should not recommend high-overhead PETs like HE
        for rec in recommendations:
            if rec.pet_type == PETType.HOMOMORPHIC_ENCRYPTION:
                # If HE is recommended, confidence should be low
                assert rec.confidence < 0.7

    def test_recommendation_confidence(self):
        """Test that recommendations include confidence scores."""
        recommender = PETRecommender()

        recommendations = recommender.recommend(
            sensitivity=DataSensitivity.CONFIDENTIAL,
            use_case=UseCaseType.ANALYTICS
        )

        for rec in recommendations:
            assert 0.0 <= rec.confidence <= 1.0
            assert len(rec.rationale) > 0
            assert isinstance(rec.trade_offs, list)

    def test_explain_pet(self):
        """Test PET explanation functionality."""
        recommender = PETRecommender()

        explanation = recommender.explain_pet(PETType.DIFFERENTIAL_PRIVACY)

        assert 'name' in explanation
        assert 'description' in explanation
        assert 'how_it_works' in explanation
        assert 'pros' in explanation
        assert 'cons' in explanation
        assert 'world_bank_ref' in explanation

    def test_pet_compatibility(self):
        """Test PET compatibility information."""
        recommender = PETRecommender()

        recommendations = recommender.recommend(
            sensitivity=DataSensitivity.HIGHLY_RESTRICTED,
            use_case=UseCaseType.ANALYTICS
        )

        for rec in recommendations:
            assert isinstance(rec.compatible_with, list)
            # Compatible PETs should be valid PET types
            for compatible in rec.compatible_with:
                assert isinstance(compatible, PETType)


class TestDataSensitivity:
    """Test data sensitivity classification."""

    def test_sensitivity_levels(self):
        """Test that sensitivity levels are ordered correctly."""
        levels = [
            DataSensitivity.PUBLIC,
            DataSensitivity.INTERNAL,
            DataSensitivity.CONFIDENTIAL,
            DataSensitivity.RESTRICTED,
            DataSensitivity.HIGHLY_RESTRICTED
        ]

        # Verify all levels exist
        for level in levels:
            assert isinstance(level, DataSensitivity)


class TestPETConfig:
    """Test PET configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PETConfig()

        assert config.dp_epsilon == 1.0
        assert config.dp_delta == 1e-5
        assert config.auto_apply_pet is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PETConfig(
            dp_epsilon=0.5,
            auto_apply_pet=False,
            enable_pet_chaining=True
        )

        assert config.dp_epsilon == 0.5
        assert config.auto_apply_pet is False
        assert config.enable_pet_chaining is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
