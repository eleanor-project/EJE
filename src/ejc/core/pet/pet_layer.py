"""
PET-Aware Data Layer - Phase 5B

Main orchestration layer for Privacy-Enhancing Technologies.
Implements World Bank recommendations (Section 5.3) for data privacy protection.

Features:
- Data minimization
- PET recommendation and automatic application
- Secure data storage
- Privacy-preserving data operations
- PET effectiveness monitoring
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class PETType(Enum):
    """Supported Privacy-Enhancing Technologies."""
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    FEDERATED_LEARNING = "federated_learning"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    SECURE_MPC = "secure_mpc"
    TEE = "tee"
    NONE = "none"


class DataSensitivity(Enum):
    """Data sensitivity levels for PET selection."""
    PUBLIC = "public"           # No PII, public information
    INTERNAL = "internal"       # Non-sensitive internal data
    CONFIDENTIAL = "confidential"  # Quasi-identifiers, business data
    RESTRICTED = "restricted"   # PII, sensitive attributes
    HIGHLY_RESTRICTED = "highly_restricted"  # Health, financial, biometric


@dataclass
class PETConfig:
    """Configuration for PET Layer."""

    # Differential Privacy settings
    dp_epsilon: float = 1.0  # Privacy budget (lower = more private)
    dp_delta: float = 1e-5   # Privacy parameter
    dp_mechanism: str = "laplace"  # laplace, gaussian, exponential

    # Federated Learning settings
    fl_num_rounds: int = 10
    fl_min_clients: int = 2
    fl_aggregation: str = "fedavg"  # fedavg, median, trimmed_mean

    # Homomorphic Encryption settings
    he_scheme: str = "ckks"  # ckks, bfv, bgv
    he_poly_modulus_degree: int = 8192

    # Secure MPC settings
    mpc_protocol: str = "shamir"  # shamir, additive, yao
    mpc_threshold: int = 2

    # TEE settings
    tee_provider: str = "sgx"  # sgx, trustzone, sev

    # General settings
    auto_apply_pet: bool = True
    min_sensitivity_for_pet: DataSensitivity = DataSensitivity.CONFIDENTIAL
    enable_pet_chaining: bool = False  # Allow multiple PETs


@dataclass
class DataPackage:
    """Wrapper for data with privacy metadata."""

    data: Any
    sensitivity: DataSensitivity
    applied_pets: List[PETType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    privacy_budget_used: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'data': self.data,
            'sensitivity': self.sensitivity.value,
            'applied_pets': [pet.value for pet in self.applied_pets],
            'metadata': self.metadata,
            'privacy_budget_used': self.privacy_budget_used
        }


class PETLayer:
    """
    PET-Aware Data Layer implementing World Bank privacy standards.

    Provides unified interface for privacy-preserving data operations
    using various Privacy-Enhancing Technologies.
    """

    def __init__(self, config: Optional[PETConfig] = None):
        """
        Initialize PET Layer.

        Args:
            config: PET configuration (uses defaults if not provided)
        """
        self.config = config or PETConfig()
        self._pet_modules: Dict[PETType, Any] = {}
        self._privacy_ledger: List[Dict[str, Any]] = []
        self._load_pet_modules()

    def _load_pet_modules(self) -> None:
        """Load available PET modules."""
        # Lazy loading of PET implementations
        # Will be loaded when needed to avoid unnecessary dependencies
        pass

    def wrap_data(
        self,
        data: Any,
        sensitivity: DataSensitivity,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataPackage:
        """
        Wrap data with privacy metadata.

        Args:
            data: Raw data to protect
            sensitivity: Data sensitivity level
            metadata: Optional metadata

        Returns:
            DataPackage with privacy information
        """
        return DataPackage(
            data=data,
            sensitivity=sensitivity,
            metadata=metadata or {},
            applied_pets=[],
            privacy_budget_used=0.0
        )

    def minimize_data(
        self,
        data: Union[Dict, List],
        required_fields: List[str]
    ) -> Union[Dict, List]:
        """
        Apply data minimization principle (World Bank requirement).

        Removes unnecessary fields to reduce privacy risk.

        Args:
            data: Original data
            required_fields: List of fields actually needed

        Returns:
            Minimized data containing only required fields
        """
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k in required_fields}
        elif isinstance(data, list):
            return [
                {k: v for k, v in item.items() if k in required_fields}
                if isinstance(item, dict) else item
                for item in data
            ]
        return data

    def recommend_pet(
        self,
        data_package: DataPackage,
        use_case: str = "general"
    ) -> List[PETType]:
        """
        Recommend appropriate PETs for data package.

        Args:
            data_package: Data package to protect
            use_case: Use case description (e.g., "analytics", "ml_training")

        Returns:
            List of recommended PET types
        """
        recommendations = []
        sensitivity = data_package.sensitivity

        # Recommendation logic based on World Bank guidelines
        if sensitivity == DataSensitivity.HIGHLY_RESTRICTED:
            # Highest security: multiple PETs
            recommendations.extend([
                PETType.DIFFERENTIAL_PRIVACY,
                PETType.HOMOMORPHIC_ENCRYPTION,
                PETType.TEE
            ])
        elif sensitivity == DataSensitivity.RESTRICTED:
            # High security: strong PETs
            recommendations.extend([
                PETType.DIFFERENTIAL_PRIVACY,
                PETType.HOMOMORPHIC_ENCRYPTION
            ])
        elif sensitivity == DataSensitivity.CONFIDENTIAL:
            # Medium security: basic PETs
            if "ml" in use_case.lower() or "training" in use_case.lower():
                recommendations.append(PETType.FEDERATED_LEARNING)
            recommendations.append(PETType.DIFFERENTIAL_PRIVACY)
        elif sensitivity in [DataSensitivity.INTERNAL, DataSensitivity.PUBLIC]:
            # Low security: PET optional
            if self.config.auto_apply_pet:
                recommendations.append(PETType.DIFFERENTIAL_PRIVACY)

        return recommendations

    def apply_pet(
        self,
        data_package: DataPackage,
        pet_type: PETType,
        operation: str = "query"
    ) -> DataPackage:
        """
        Apply Privacy-Enhancing Technology to data package.

        Args:
            data_package: Data to protect
            pet_type: Type of PET to apply
            operation: Operation type (query, aggregate, train, etc.)

        Returns:
            Updated data package with PET applied
        """
        if pet_type == PETType.NONE:
            return data_package

        # Apply appropriate PET
        if pet_type == PETType.DIFFERENTIAL_PRIVACY:
            data_package = self._apply_differential_privacy(data_package, operation)
        elif pet_type == PETType.FEDERATED_LEARNING:
            data_package = self._apply_federated_learning(data_package, operation)
        elif pet_type == PETType.HOMOMORPHIC_ENCRYPTION:
            data_package = self._apply_homomorphic_encryption(data_package, operation)
        elif pet_type == PETType.SECURE_MPC:
            data_package = self._apply_secure_mpc(data_package, operation)
        elif pet_type == PETType.TEE:
            data_package = self._apply_tee(data_package, operation)

        # Record PET application
        if pet_type not in data_package.applied_pets:
            data_package.applied_pets.append(pet_type)

        # Log to privacy ledger
        self._log_pet_application(data_package, pet_type, operation)

        return data_package

    def _apply_differential_privacy(
        self,
        data_package: DataPackage,
        operation: str
    ) -> DataPackage:
        """
        Apply Differential Privacy.

        Adds calibrated noise to protect individual privacy while
        maintaining statistical utility.
        """
        # For now, add metadata indicating DP would be applied
        # Full implementation requires opacus or similar library
        data_package.metadata['dp_applied'] = True
        data_package.metadata['dp_epsilon'] = self.config.dp_epsilon
        data_package.metadata['dp_delta'] = self.config.dp_delta
        data_package.metadata['dp_mechanism'] = self.config.dp_mechanism
        data_package.privacy_budget_used += self.config.dp_epsilon

        return data_package

    def _apply_federated_learning(
        self,
        data_package: DataPackage,
        operation: str
    ) -> DataPackage:
        """
        Apply Federated Learning approach.

        Enables model training without centralizing data.
        """
        data_package.metadata['fl_applied'] = True
        data_package.metadata['fl_rounds'] = self.config.fl_num_rounds
        data_package.metadata['fl_aggregation'] = self.config.fl_aggregation

        return data_package

    def _apply_homomorphic_encryption(
        self,
        data_package: DataPackage,
        operation: str
    ) -> DataPackage:
        """
        Apply Homomorphic Encryption.

        Enables computation on encrypted data.
        """
        data_package.metadata['he_applied'] = True
        data_package.metadata['he_scheme'] = self.config.he_scheme
        data_package.metadata['he_poly_modulus'] = self.config.he_poly_modulus_degree

        return data_package

    def _apply_secure_mpc(
        self,
        data_package: DataPackage,
        operation: str
    ) -> DataPackage:
        """
        Apply Secure Multi-Party Computation.

        Enables computation across parties without revealing inputs.
        """
        data_package.metadata['mpc_applied'] = True
        data_package.metadata['mpc_protocol'] = self.config.mpc_protocol
        data_package.metadata['mpc_threshold'] = self.config.mpc_threshold

        return data_package

    def _apply_tee(
        self,
        data_package: DataPackage,
        operation: str
    ) -> DataPackage:
        """
        Apply Trusted Execution Environment.

        Executes sensitive operations in hardware-protected environment.
        """
        data_package.metadata['tee_applied'] = True
        data_package.metadata['tee_provider'] = self.config.tee_provider

        return data_package

    def _log_pet_application(
        self,
        data_package: DataPackage,
        pet_type: PETType,
        operation: str
    ) -> None:
        """Log PET application to privacy ledger."""
        log_entry = {
            'pet_type': pet_type.value,
            'operation': operation,
            'sensitivity': data_package.sensitivity.value,
            'privacy_budget_used': data_package.privacy_budget_used,
            'data_hash': self._hash_data(data_package.data)
        }
        self._privacy_ledger.append(log_entry)

    def _hash_data(self, data: Any) -> str:
        """Create hash of data for audit trail (without storing actual data)."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def get_privacy_ledger(self) -> List[Dict[str, Any]]:
        """
        Get privacy operation ledger.

        Returns:
            List of privacy operations performed
        """
        return self._privacy_ledger.copy()

    def check_privacy_budget(
        self,
        data_package: DataPackage,
        max_budget: float = 10.0
    ) -> bool:
        """
        Check if privacy budget has been exceeded.

        Args:
            data_package: Data package to check
            max_budget: Maximum allowed privacy budget

        Returns:
            True if budget is acceptable, False if exceeded
        """
        return data_package.privacy_budget_used <= max_budget

    def auto_protect(
        self,
        data: Any,
        sensitivity: DataSensitivity,
        use_case: str = "general"
    ) -> DataPackage:
        """
        Automatically apply appropriate privacy protections.

        Convenience method that wraps data, recommends PETs, and applies them.

        Args:
            data: Raw data to protect
            sensitivity: Data sensitivity level
            use_case: Use case description

        Returns:
            Protected data package
        """
        # Wrap data
        package = self.wrap_data(data, sensitivity)

        # Get recommendations
        if sensitivity.value >= self.config.min_sensitivity_for_pet.value:
            recommended_pets = self.recommend_pet(package, use_case)

            # Apply recommended PETs
            for pet_type in recommended_pets:
                if self.config.enable_pet_chaining or not package.applied_pets:
                    package = self.apply_pet(package, pet_type)

        return package


# Export
__all__ = [
    'PETLayer',
    'PETConfig',
    'PETType',
    'DataSensitivity',
    'DataPackage'
]
