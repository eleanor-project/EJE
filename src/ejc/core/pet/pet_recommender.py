"""
PET Recommendation Engine - Phase 5B

Intelligent recommendation system for selecting appropriate
Privacy-Enhancing Technologies based on:
- Data sensitivity
- Use case requirements
- Performance constraints
- Compliance requirements

Aligned with World Bank Section 5.3 recommendations.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .pet_layer import PETType, DataSensitivity


class UseCaseType(Enum):
    """Common AI/ML use cases."""
    ANALYTICS = "analytics"
    ML_TRAINING = "ml_training"
    INFERENCE = "inference"
    DATA_SHARING = "data_sharing"
    AGGREGATION = "aggregation"
    GENERAL = "general"


class PerformanceRequirement(Enum):
    """Performance requirements for PET selection."""
    REAL_TIME = "real_time"         # < 100ms latency
    INTERACTIVE = "interactive"     # < 1s latency
    BATCH = "batch"                 # Minutes acceptable
    OFFLINE = "offline"             # Hours acceptable


@dataclass
class PETRecommendation:
    """Recommendation for Privacy-Enhancing Technology."""

    pet_type: PETType
    confidence: float  # 0.0 to 1.0
    rationale: str
    trade_offs: List[str]
    estimated_overhead: str  # "low", "medium", "high"
    compatible_with: List[PETType]  # Other PETs that can be combined
    requires_infrastructure: bool


class PETRecommender:
    """
    PET Recommendation Engine.

    Provides intelligent recommendations for Privacy-Enhancing Technologies
    based on data characteristics, use case, and constraints.
    """

    # Performance overhead estimates (relative)
    OVERHEAD_ESTIMATES = {
        PETType.DIFFERENTIAL_PRIVACY: "low",
        PETType.FEDERATED_LEARNING: "medium",
        PETType.HOMOMORPHIC_ENCRYPTION: "high",
        PETType.SECURE_MPC: "high",
        PETType.TEE: "low"
    }

    # Compatibility matrix (which PETs can be combined)
    COMPATIBILITY = {
        PETType.DIFFERENTIAL_PRIVACY: [
            PETType.FEDERATED_LEARNING,
            PETType.HOMOMORPHIC_ENCRYPTION,
            PETType.TEE
        ],
        PETType.FEDERATED_LEARNING: [
            PETType.DIFFERENTIAL_PRIVACY,
            PETType.SECURE_MPC
        ],
        PETType.HOMOMORPHIC_ENCRYPTION: [
            PETType.DIFFERENTIAL_PRIVACY,
            PETType.SECURE_MPC
        ],
        PETType.SECURE_MPC: [
            PETType.FEDERATED_LEARNING,
            PETType.HOMOMORPHIC_ENCRYPTION
        ],
        PETType.TEE: [
            PETType.DIFFERENTIAL_PRIVACY
        ]
    }

    # Infrastructure requirements
    INFRASTRUCTURE_REQUIRED = {
        PETType.DIFFERENTIAL_PRIVACY: False,
        PETType.FEDERATED_LEARNING: True,   # Requires multiple clients
        PETType.HOMOMORPHIC_ENCRYPTION: False,
        PETType.SECURE_MPC: True,           # Requires multiple parties
        PETType.TEE: True                   # Requires hardware support
    }

    def __init__(self):
        """Initialize PET Recommender."""
        pass

    def recommend(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType = UseCaseType.GENERAL,
        performance_req: PerformanceRequirement = PerformanceRequirement.BATCH,
        data_characteristics: Optional[Dict[str, Any]] = None,
        compliance_frameworks: Optional[List[str]] = None,
        max_recommendations: int = 3
    ) -> List[PETRecommendation]:
        """
        Recommend appropriate PETs based on requirements.

        Args:
            sensitivity: Data sensitivity level
            use_case: Type of use case
            performance_req: Performance requirements
            data_characteristics: Optional dict with:
                - size: Data size (bytes)
                - num_features: Number of features
                - data_type: Type of data (tabular, image, text)
            compliance_frameworks: List of compliance frameworks (GDPR, HIPAA, etc.)
            max_recommendations: Maximum number of recommendations

        Returns:
            List of PET recommendations, ordered by suitability
        """
        data_chars = data_characteristics or {}
        compliance = compliance_frameworks or []

        # Collect candidate PETs
        candidates = []

        # Differential Privacy - Universal recommendation for most cases
        if sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED,
                          DataSensitivity.HIGHLY_RESTRICTED]:
            candidates.append(self._recommend_differential_privacy(
                sensitivity, use_case, performance_req
            ))

        # Federated Learning - For distributed ML training
        if use_case == UseCaseType.ML_TRAINING and performance_req != PerformanceRequirement.REAL_TIME:
            candidates.append(self._recommend_federated_learning(
                sensitivity, use_case, performance_req
            ))

        # Homomorphic Encryption - For high sensitivity computation
        if sensitivity in [DataSensitivity.RESTRICTED, DataSensitivity.HIGHLY_RESTRICTED]:
            if use_case in [UseCaseType.ANALYTICS, UseCaseType.AGGREGATION]:
                candidates.append(self._recommend_homomorphic_encryption(
                    sensitivity, use_case, performance_req
                ))

        # Secure MPC - For multi-party scenarios
        if use_case == UseCaseType.DATA_SHARING or 'multi-party' in str(data_chars.get('notes', '')).lower():
            candidates.append(self._recommend_secure_mpc(
                sensitivity, use_case, performance_req
            ))

        # TEE - For high sensitivity with performance needs
        if sensitivity == DataSensitivity.HIGHLY_RESTRICTED:
            if performance_req in [PerformanceRequirement.REAL_TIME, PerformanceRequirement.INTERACTIVE]:
                candidates.append(self._recommend_tee(
                    sensitivity, use_case, performance_req
                ))

        # Sort by confidence and return top recommendations
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:max_recommendations]

    def _recommend_differential_privacy(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType,
        performance_req: PerformanceRequirement
    ) -> PETRecommendation:
        """Generate recommendation for Differential Privacy."""

        # Base confidence on sensitivity
        confidence_map = {
            DataSensitivity.PUBLIC: 0.3,
            DataSensitivity.INTERNAL: 0.5,
            DataSensitivity.CONFIDENTIAL: 0.8,
            DataSensitivity.RESTRICTED: 0.9,
            DataSensitivity.HIGHLY_RESTRICTED: 0.95
        }
        confidence = confidence_map.get(sensitivity, 0.7)

        # Adjust for use case
        if use_case in [UseCaseType.ANALYTICS, UseCaseType.AGGREGATION]:
            confidence += 0.05

        rationale = (
            f"Differential Privacy is recommended for {sensitivity.value} data. "
            "It provides strong mathematical privacy guarantees with minimal performance overhead. "
            "Suitable for statistical queries, ML training, and analytics."
        )

        trade_offs = [
            "Reduced accuracy due to noise addition",
            "Privacy budget must be carefully managed",
            "May require parameter tuning (epsilon, delta)"
        ]

        return PETRecommendation(
            pet_type=PETType.DIFFERENTIAL_PRIVACY,
            confidence=min(confidence, 1.0),
            rationale=rationale,
            trade_offs=trade_offs,
            estimated_overhead=self.OVERHEAD_ESTIMATES[PETType.DIFFERENTIAL_PRIVACY],
            compatible_with=self.COMPATIBILITY[PETType.DIFFERENTIAL_PRIVACY],
            requires_infrastructure=self.INFRASTRUCTURE_REQUIRED[PETType.DIFFERENTIAL_PRIVACY]
        )

    def _recommend_federated_learning(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType,
        performance_req: PerformanceRequirement
    ) -> PETRecommendation:
        """Generate recommendation for Federated Learning."""

        confidence = 0.85 if use_case == UseCaseType.ML_TRAINING else 0.5

        # Lower confidence for real-time requirements
        if performance_req == PerformanceRequirement.REAL_TIME:
            confidence -= 0.3

        rationale = (
            "Federated Learning enables model training without centralizing data. "
            "Particularly suitable for distributed datasets where data cannot be moved. "
            "Compatible with differential privacy for enhanced protection."
        )

        trade_offs = [
            "Requires multiple data sources/clients",
            "Communication overhead between parties",
            "Model convergence may be slower",
            "Requires coordination infrastructure"
        ]

        return PETRecommendation(
            pet_type=PETType.FEDERATED_LEARNING,
            confidence=min(confidence, 1.0),
            rationale=rationale,
            trade_offs=trade_offs,
            estimated_overhead=self.OVERHEAD_ESTIMATES[PETType.FEDERATED_LEARNING],
            compatible_with=self.COMPATIBILITY[PETType.FEDERATED_LEARNING],
            requires_infrastructure=self.INFRASTRUCTURE_REQUIRED[PETType.FEDERATED_LEARNING]
        )

    def _recommend_homomorphic_encryption(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType,
        performance_req: PerformanceRequirement
    ) -> PETRecommendation:
        """Generate recommendation for Homomorphic Encryption."""

        confidence = 0.9 if sensitivity == DataSensitivity.HIGHLY_RESTRICTED else 0.7

        # Much lower confidence for real-time use cases
        if performance_req in [PerformanceRequirement.REAL_TIME, PerformanceRequirement.INTERACTIVE]:
            confidence -= 0.4

        rationale = (
            "Homomorphic Encryption allows computation on encrypted data without decryption. "
            "Provides strongest security for sensitive computations. "
            "Best suited for analytics and aggregation on highly sensitive data."
        )

        trade_offs = [
            "Significant computational overhead (10-1000x)",
            "Limited operation support (depending on scheme)",
            "Requires careful implementation",
            "May need specialized hardware for acceptable performance"
        ]

        return PETRecommendation(
            pet_type=PETType.HOMOMORPHIC_ENCRYPTION,
            confidence=min(max(confidence, 0.0), 1.0),
            rationale=rationale,
            trade_offs=trade_offs,
            estimated_overhead=self.OVERHEAD_ESTIMATES[PETType.HOMOMORPHIC_ENCRYPTION],
            compatible_with=self.COMPATIBILITY[PETType.HOMOMORPHIC_ENCRYPTION],
            requires_infrastructure=self.INFRASTRUCTURE_REQUIRED[PETType.HOMOMORPHIC_ENCRYPTION]
        )

    def _recommend_secure_mpc(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType,
        performance_req: PerformanceRequirement
    ) -> PETRecommendation:
        """Generate recommendation for Secure Multi-Party Computation."""

        confidence = 0.8 if use_case == UseCaseType.DATA_SHARING else 0.6

        if performance_req == PerformanceRequirement.REAL_TIME:
            confidence -= 0.3

        rationale = (
            "Secure MPC enables computation across multiple parties without revealing individual inputs. "
            "Ideal for collaborative analytics where no single party should see all data. "
            "Provides cryptographic security guarantees."
        )

        trade_offs = [
            "Requires multiple participating parties",
            "Communication rounds increase latency",
            "Complexity in protocol implementation",
            "Vulnerable to collusion if threshold not met"
        ]

        return PETRecommendation(
            pet_type=PETType.SECURE_MPC,
            confidence=min(max(confidence, 0.0), 1.0),
            rationale=rationale,
            trade_offs=trade_offs,
            estimated_overhead=self.OVERHEAD_ESTIMATES[PETType.SECURE_MPC],
            compatible_with=self.COMPATIBILITY[PETType.SECURE_MPC],
            requires_infrastructure=self.INFRASTRUCTURE_REQUIRED[PETType.SECURE_MPC]
        )

    def _recommend_tee(
        self,
        sensitivity: DataSensitivity,
        use_case: UseCaseType,
        performance_req: PerformanceRequirement
    ) -> PETRecommendation:
        """Generate recommendation for Trusted Execution Environment."""

        confidence = 0.75

        # Higher confidence for real-time needs
        if performance_req in [PerformanceRequirement.REAL_TIME, PerformanceRequirement.INTERACTIVE]:
            confidence += 0.1

        # Higher confidence for highly sensitive data
        if sensitivity == DataSensitivity.HIGHLY_RESTRICTED:
            confidence += 0.1

        rationale = (
            "Trusted Execution Environment provides hardware-based isolation for sensitive computations. "
            "Offers strong security with minimal performance overhead. "
            "Suitable for real-time processing of highly sensitive data."
        )

        trade_offs = [
            "Requires specific hardware support (Intel SGX, ARM TrustZone, AMD SEV)",
            "Limited memory in secure enclave",
            "Side-channel attack considerations",
            "Platform-specific implementation"
        ]

        return PETRecommendation(
            pet_type=PETType.TEE,
            confidence=min(confidence, 1.0),
            rationale=rationale,
            trade_offs=trade_offs,
            estimated_overhead=self.OVERHEAD_ESTIMATES[PETType.TEE],
            compatible_with=self.COMPATIBILITY[PETType.TEE],
            requires_infrastructure=self.INFRASTRUCTURE_REQUIRED[PETType.TEE]
        )

    def explain_pet(self, pet_type: PETType) -> Dict[str, Any]:
        """
        Provide detailed explanation of a PET.

        Args:
            pet_type: PET to explain

        Returns:
            Dict with explanation, use cases, pros, cons
        """
        explanations = {
            PETType.DIFFERENTIAL_PRIVACY: {
                "name": "Differential Privacy",
                "description": "Adds calibrated statistical noise to query results or model training to protect individual privacy while maintaining overall data utility.",
                "how_it_works": "By adding carefully calibrated noise, DP ensures that the presence or absence of any single individual's data doesn't significantly affect the output.",
                "best_for": ["Statistical queries", "ML model training", "Data analytics", "Census and surveys"],
                "pros": ["Strong mathematical guarantees", "Low performance overhead", "Well-established theory"],
                "cons": ["Accuracy reduction", "Privacy budget management needed", "Parameter tuning required"],
                "world_bank_ref": "Section 5.3.1 - Primary recommendation for privacy preservation"
            },
            PETType.FEDERATED_LEARNING: {
                "name": "Federated Learning",
                "description": "Trains machine learning models across multiple decentralized devices or servers holding local data samples, without exchanging the data.",
                "how_it_works": "Model training happens locally on each device, only model updates (gradients) are shared and aggregated.",
                "best_for": ["Distributed ML training", "Mobile applications", "Healthcare collaboration", "Cross-organization learning"],
                "pros": ["Data stays local", "Scalable", "Enables collaboration"],
                "cons": ["Communication overhead", "Slower convergence", "Infrastructure complexity"],
                "world_bank_ref": "Section 5.3.2 - Recommended for distributed scenarios"
            },
            PETType.HOMOMORPHIC_ENCRYPTION: {
                "name": "Homomorphic Encryption",
                "description": "Allows computations to be performed on encrypted data without decrypting it first.",
                "how_it_works": "Special encryption schemes that preserve algebraic structure, enabling operations on ciphertexts that correspond to operations on plaintexts.",
                "best_for": ["Cloud computing on sensitive data", "Secure aggregation", "Privacy-preserving analytics"],
                "pros": ["Strongest security", "Data never decrypted", "Cryptographic guarantees"],
                "cons": ["Very high overhead (10-1000x)", "Limited operations", "Implementation complexity"],
                "world_bank_ref": "Section 5.3.3 - For highest sensitivity requirements"
            },
            PETType.SECURE_MPC: {
                "name": "Secure Multi-Party Computation",
                "description": "Enables multiple parties to jointly compute a function over their inputs while keeping those inputs private.",
                "how_it_works": "Uses cryptographic protocols (secret sharing, garbled circuits) to compute without revealing individual inputs.",
                "best_for": ["Multi-party analytics", "Auctions", "Voting", "Joint data analysis"],
                "pros": ["No trusted party needed", "Cryptographic security", "Precise computation"],
                "cons": ["Requires multiple parties", "Communication rounds", "Protocol complexity"],
                "world_bank_ref": "Section 5.3.4 - For collaborative scenarios"
            },
            PETType.TEE: {
                "name": "Trusted Execution Environment",
                "description": "Hardware-based secure area that guarantees code and data loaded inside are protected with respect to confidentiality and integrity.",
                "how_it_works": "Uses CPU features (Intel SGX, ARM TrustZone) to create isolated execution environments.",
                "best_for": ["Real-time processing", "Confidential computing", "Secure key management"],
                "pros": ["Low overhead", "Hardware security", "Real-time capable"],
                "cons": ["Hardware dependency", "Limited enclave memory", "Side-channel risks"],
                "world_bank_ref": "Section 5.3.5 - For performance-critical applications"
            }
        }

        return explanations.get(pet_type, {
            "name": pet_type.value,
            "description": "No detailed information available",
            "how_it_works": "N/A",
            "best_for": [],
            "pros": [],
            "cons": [],
            "world_bank_ref": "N/A"
        })


# Export
__all__ = [
    'PETRecommender',
    'PETRecommendation',
    'UseCaseType',
    'PerformanceRequirement'
]
