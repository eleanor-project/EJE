"""
Differential Privacy Implementation - Phase 5B

Implements differential privacy mechanisms for privacy-preserving data operations.

Supports:
- Laplace mechanism (for queries with L1 sensitivity)
- Gaussian mechanism (for queries with L2 sensitivity)
- Exponential mechanism (for non-numeric outputs)
- Privacy budget tracking
- Composition theorems

Reference: World Bank Report Section 5.3.1 - Differential Privacy
"""

import math
import random
from typing import Union, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class DPMechanism(Enum):
    """Differential Privacy mechanisms."""
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"


@dataclass
class PrivacyBudget:
    """Privacy budget tracker for differential privacy."""

    epsilon: float  # Privacy loss parameter
    delta: float = 1e-5  # Failure probability (for (ε,δ)-DP)
    spent_epsilon: float = 0.0
    spent_delta: float = 0.0

    def can_spend(self, epsilon_cost: float, delta_cost: float = 0.0) -> bool:
        """Check if budget allows spending."""
        return (
            self.spent_epsilon + epsilon_cost <= self.epsilon and
            self.spent_delta + delta_cost <= self.delta
        )

    def spend(self, epsilon_cost: float, delta_cost: float = 0.0) -> None:
        """Spend privacy budget."""
        if not self.can_spend(epsilon_cost, delta_cost):
            raise ValueError(
                f"Insufficient privacy budget. "
                f"Need ε={epsilon_cost}, δ={delta_cost}. "
                f"Have ε={self.epsilon - self.spent_epsilon}, δ={self.delta - self.spent_delta}"
            )
        self.spent_epsilon += epsilon_cost
        self.spent_delta += delta_cost

    def remaining_budget(self) -> tuple[float, float]:
        """Get remaining privacy budget."""
        return (
            self.epsilon - self.spent_epsilon,
            self.delta - self.spent_delta
        )


class DifferentialPrivacy:
    """
    Differential Privacy implementation with multiple mechanisms.

    Provides privacy-preserving data transformations using
    calibrated noise addition.
    """

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        mechanism: DPMechanism = DPMechanism.LAPLACE
    ):
        """
        Initialize Differential Privacy handler.

        Args:
            epsilon: Privacy budget (lower = more privacy, less accuracy)
            delta: Failure probability for (ε,δ)-DP
            mechanism: DP mechanism to use
        """
        if epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        if not (0 <= delta < 1):
            raise ValueError("Delta must be in [0, 1)")

        self.budget = PrivacyBudget(epsilon=epsilon, delta=delta)
        self.mechanism = mechanism

    def add_noise_to_value(
        self,
        value: float,
        sensitivity: float,
        epsilon: Optional[float] = None
    ) -> float:
        """
        Add calibrated noise to a single numeric value.

        Args:
            value: Original value
            sensitivity: Global sensitivity of the query
            epsilon: Privacy budget to use (uses default if not specified)

        Returns:
            Noisy value
        """
        eps = epsilon or self.budget.epsilon

        if self.mechanism == DPMechanism.LAPLACE:
            noise = self._laplace_noise(sensitivity, eps)
        elif self.mechanism == DPMechanism.GAUSSIAN:
            noise = self._gaussian_noise(sensitivity, eps, self.budget.delta)
        else:
            raise ValueError(f"Mechanism {self.mechanism} not supported for numeric values")

        # Track budget usage
        if epsilon is None:  # Only track if using default budget
            self.budget.spend(eps)

        return value + noise

    def add_noise_to_vector(
        self,
        values: List[float],
        sensitivity: float,
        epsilon: Optional[float] = None
    ) -> List[float]:
        """
        Add calibrated noise to a vector of values.

        Args:
            values: Original values
            sensitivity: Global sensitivity of the query
            epsilon: Privacy budget to use (uses default if not specified)

        Returns:
            Noisy values
        """
        eps = epsilon or self.budget.epsilon

        if self.mechanism == DPMechanism.LAPLACE:
            noisy_values = [
                v + self._laplace_noise(sensitivity, eps)
                for v in values
            ]
        elif self.mechanism == DPMechanism.GAUSSIAN:
            noisy_values = [
                v + self._gaussian_noise(sensitivity, eps, self.budget.delta)
                for v in values
            ]
        else:
            raise ValueError(f"Mechanism {self.mechanism} not supported for vectors")

        # Track budget usage
        if epsilon is None:
            self.budget.spend(eps)

        return noisy_values

    def add_noise_to_count(
        self,
        count: int,
        epsilon: Optional[float] = None
    ) -> float:
        """
        Add noise to a count query (sensitivity = 1).

        Args:
            count: Original count
            epsilon: Privacy budget to use

        Returns:
            Noisy count
        """
        return self.add_noise_to_value(float(count), sensitivity=1.0, epsilon=epsilon)

    def add_noise_to_sum(
        self,
        total: float,
        max_value: float,
        epsilon: Optional[float] = None
    ) -> float:
        """
        Add noise to a sum query.

        Args:
            total: Original sum
            max_value: Maximum value any individual can contribute
            epsilon: Privacy budget to use

        Returns:
            Noisy sum
        """
        # Sensitivity of sum is max individual contribution
        return self.add_noise_to_value(total, sensitivity=max_value, epsilon=epsilon)

    def add_noise_to_average(
        self,
        average: float,
        max_value: float,
        n: int,
        epsilon: Optional[float] = None
    ) -> float:
        """
        Add noise to an average query.

        Args:
            average: Original average
            max_value: Maximum value any individual can have
            n: Number of individuals in dataset
            epsilon: Privacy budget to use

        Returns:
            Noisy average
        """
        # Sensitivity of average is max_value / n
        sensitivity = max_value / n if n > 0 else max_value
        return self.add_noise_to_value(average, sensitivity=sensitivity, epsilon=epsilon)

    def exponential_mechanism(
        self,
        candidates: List[Any],
        utility_fn: Callable[[Any], float],
        sensitivity: float,
        epsilon: Optional[float] = None
    ) -> Any:
        """
        Select from candidates using exponential mechanism.

        Used for non-numeric outputs where we want to select the "best"
        option while preserving privacy.

        Args:
            candidates: List of candidate outputs
            utility_fn: Function scoring each candidate (higher = better)
            sensitivity: Sensitivity of utility function
            epsilon: Privacy budget to use

        Returns:
            Selected candidate
        """
        eps = epsilon or self.budget.epsilon

        # Compute utilities
        utilities = [utility_fn(c) for c in candidates]

        # Compute probabilities proportional to exp(epsilon * utility / (2 * sensitivity))
        scaled_utilities = [
            math.exp(eps * u / (2 * sensitivity))
            for u in utilities
        ]

        total = sum(scaled_utilities)
        probabilities = [su / total for su in scaled_utilities]

        # Sample from distribution
        r = random.random()
        cumulative = 0.0
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if r <= cumulative:
                # Track budget usage
                if epsilon is None:
                    self.budget.spend(eps)
                return candidates[i]

        # Fallback (shouldn't happen due to floating point)
        return candidates[-1]

    def _laplace_noise(self, sensitivity: float, epsilon: float) -> float:
        """
        Generate Laplace noise.

        Scale = sensitivity / epsilon
        """
        scale = sensitivity / epsilon
        # Use two uniform random variables to generate Laplace
        u = random.random() - 0.5
        return -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))

    def _gaussian_noise(
        self,
        sensitivity: float,
        epsilon: float,
        delta: float
    ) -> float:
        """
        Generate Gaussian noise for (ε,δ)-differential privacy.

        Standard deviation = sensitivity * sqrt(2 * ln(1.25/δ)) / epsilon
        """
        if delta == 0:
            raise ValueError("Gaussian mechanism requires δ > 0")

        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
        return random.gauss(0, sigma)

    def reset_budget(self, epsilon: Optional[float] = None, delta: Optional[float] = None) -> None:
        """
        Reset privacy budget.

        Args:
            epsilon: New epsilon (keeps current if not specified)
            delta: New delta (keeps current if not specified)
        """
        if epsilon is not None:
            self.budget.epsilon = epsilon
        if delta is not None:
            self.budget.delta = delta

        self.budget.spent_epsilon = 0.0
        self.budget.spent_delta = 0.0

    def get_remaining_budget(self) -> tuple[float, float]:
        """Get remaining privacy budget."""
        return self.budget.remaining_budget()

    def get_privacy_parameters(self) -> dict:
        """
        Get current privacy parameters.

        Returns:
            Dict with epsilon, delta, mechanism, and budget usage
        """
        remaining_eps, remaining_delta = self.budget.remaining_budget()
        return {
            'epsilon': self.budget.epsilon,
            'delta': self.budget.delta,
            'mechanism': self.mechanism.value,
            'spent_epsilon': self.budget.spent_epsilon,
            'spent_delta': self.budget.spent_delta,
            'remaining_epsilon': remaining_eps,
            'remaining_delta': remaining_delta,
            'budget_exhausted': remaining_eps <= 0 or remaining_delta <= 0
        }


# Convenience functions
def laplace_noise(value: float, sensitivity: float, epsilon: float) -> float:
    """
    Add Laplace noise to a value (stateless).

    Args:
        value: Original value
        sensitivity: Query sensitivity
        epsilon: Privacy parameter

    Returns:
        Noisy value
    """
    dp = DifferentialPrivacy(epsilon=epsilon, mechanism=DPMechanism.LAPLACE)
    return dp.add_noise_to_value(value, sensitivity, epsilon)


def gaussian_noise(value: float, sensitivity: float, epsilon: float, delta: float = 1e-5) -> float:
    """
    Add Gaussian noise to a value (stateless).

    Args:
        value: Original value
        sensitivity: Query sensitivity
        epsilon: Privacy parameter
        delta: Failure probability

    Returns:
        Noisy value
    """
    dp = DifferentialPrivacy(epsilon=epsilon, delta=delta, mechanism=DPMechanism.GAUSSIAN)
    return dp.add_noise_to_value(value, sensitivity, epsilon)


# Export
__all__ = [
    'DifferentialPrivacy',
    'PrivacyBudget',
    'DPMechanism',
    'laplace_noise',
    'gaussian_noise'
]
