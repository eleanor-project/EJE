"""
Privacy-Enhancing Technologies (PET) Layer - Phase 5B

This module provides privacy-preserving data handling capabilities aligned
with World Bank AI Governance standards (Section 5.3).

Components:
- pet_layer.py: Main PET orchestration and data handling
- pet_recommender.py: PET recommendation engine
- differential_privacy.py: Differential Privacy implementation
- federated_learning.py: Federated Learning support (future)
- homomorphic_encryption.py: Homomorphic Encryption wrapper (future)
- secure_mpc.py: Secure Multi-Party Computation (future)
- tee.py: Trusted Execution Environment integration (future)
"""

from .pet_layer import PETLayer, PETConfig, PETType, DataSensitivity, DataPackage
from .pet_recommender import PETRecommender, PETRecommendation, UseCaseType, PerformanceRequirement
from .differential_privacy import DifferentialPrivacy, PrivacyBudget, DPMechanism, laplace_noise, gaussian_noise

__all__ = [
    'PETLayer',
    'PETConfig',
    'PETType',
    'DataSensitivity',
    'DataPackage',
    'PETRecommender',
    'PETRecommendation',
    'UseCaseType',
    'PerformanceRequirement',
    'DifferentialPrivacy',
    'PrivacyBudget',
    'DPMechanism',
    'laplace_noise',
    'gaussian_noise'
]
