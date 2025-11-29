"""
Tests for Differential Privacy Implementation - Phase 5B

Tests differential privacy mechanisms and privacy budget management.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.pet.differential_privacy import (
    DifferentialPrivacy, PrivacyBudget, DPMechanism,
    laplace_noise, gaussian_noise
)


class TestPrivacyBudget:
    """Test privacy budget tracking."""

    def test_budget_initialization(self):
        """Test budget can be initialized."""
        budget = PrivacyBudget(epsilon=1.0, delta=1e-5)

        assert budget.epsilon == 1.0
        assert budget.delta == 1e-5
        assert budget.spent_epsilon == 0.0
        assert budget.spent_delta == 0.0

    def test_can_spend(self):
        """Test budget spending check."""
        budget = PrivacyBudget(epsilon=1.0, delta=1e-5)

        assert budget.can_spend(0.5, 0.0)
        assert budget.can_spend(1.0, 1e-5)
        assert not budget.can_spend(1.5, 0.0)

    def test_spend_budget(self):
        """Test budget spending."""
        budget = PrivacyBudget(epsilon=1.0, delta=1e-5)

        budget.spend(0.3, 0.0)
        assert budget.spent_epsilon == 0.3

        budget.spend(0.5, 0.0)
        assert budget.spent_epsilon == 0.8

    def test_overspending_raises_error(self):
        """Test that overspending raises error."""
        budget = PrivacyBudget(epsilon=1.0, delta=1e-5)

        with pytest.raises(ValueError):
            budget.spend(1.5, 0.0)

    def test_remaining_budget(self):
        """Test remaining budget calculation."""
        budget = PrivacyBudget(epsilon=1.0, delta=1e-5)
        budget.spend(0.3, 0.0)

        remaining_eps, remaining_delta = budget.remaining_budget()

        assert remaining_eps == 0.7
        assert remaining_delta == 1e-5


class TestDifferentialPrivacy:
    """Test differential privacy mechanisms."""

    def test_dp_initialization(self):
        """Test DP can be initialized."""
        dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)

        assert dp.budget.epsilon == 1.0
        assert dp.budget.delta == 1e-5
        assert dp.mechanism == DPMechanism.LAPLACE

    def test_invalid_epsilon_raises_error(self):
        """Test that invalid epsilon raises error."""
        with pytest.raises(ValueError):
            DifferentialPrivacy(epsilon=0.0)

        with pytest.raises(ValueError):
            DifferentialPrivacy(epsilon=-1.0)

    def test_add_noise_to_value(self):
        """Test adding noise to a single value."""
        dp = DifferentialPrivacy(epsilon=1.0)

        original = 100.0
        noisy = dp.add_noise_to_value(original, sensitivity=1.0, epsilon=1.0)

        # Noisy value should be different (with very high probability)
        assert noisy != original
        # But should be reasonably close for epsilon=1.0
        assert abs(noisy - original) < 50  # Within reasonable range

    def test_add_noise_to_vector(self):
        """Test adding noise to a vector."""
        dp = DifferentialPrivacy(epsilon=1.0)

        original = [10.0, 20.0, 30.0, 40.0]
        noisy = dp.add_noise_to_vector(original, sensitivity=1.0, epsilon=1.0)

        assert len(noisy) == len(original)
        # Values should be different
        assert noisy != original

    def test_add_noise_to_count(self):
        """Test adding noise to count query."""
        dp = DifferentialPrivacy(epsilon=1.0)

        count = 1000
        noisy_count = dp.add_noise_to_count(count, epsilon=1.0)

        # Should be close to original count
        assert abs(noisy_count - count) < 100

    def test_add_noise_to_sum(self):
        """Test adding noise to sum query."""
        dp = DifferentialPrivacy(epsilon=1.0)

        total = 5000.0
        max_value = 100.0  # Max individual contribution

        noisy_sum = dp.add_noise_to_sum(total, max_value, epsilon=1.0)

        # Should be different but close
        assert noisy_sum != total
        assert abs(noisy_sum - total) < 500

    def test_add_noise_to_average(self):
        """Test adding noise to average query."""
        dp = DifferentialPrivacy(epsilon=1.0)

        average = 50.0
        max_value = 100.0
        n = 1000

        noisy_avg = dp.add_noise_to_average(average, max_value, n, epsilon=1.0)

        # Should be close since sensitivity is small (max_value/n)
        assert abs(noisy_avg - average) < 5

    def test_gaussian_mechanism(self):
        """Test Gaussian mechanism."""
        dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5, mechanism=DPMechanism.GAUSSIAN)

        original = 100.0
        noisy = dp.add_noise_to_value(original, sensitivity=1.0, epsilon=1.0)

        assert noisy != original

    def test_exponential_mechanism(self):
        """Test exponential mechanism for non-numeric outputs."""
        dp = DifferentialPrivacy(epsilon=1.0)

        candidates = ['option_a', 'option_b', 'option_c']

        # Utility function that prefers 'option_b'
        def utility(option):
            if option == 'option_b':
                return 10.0
            return 1.0

        # Run multiple times to check it's probabilistic
        results = []
        for _ in range(50):
            dp_copy = DifferentialPrivacy(epsilon=1.0)
            selected = dp_copy.exponential_mechanism(
                candidates,
                utility,
                sensitivity=1.0,
                epsilon=1.0
            )
            results.append(selected)

        # Should mostly select 'option_b' due to higher utility
        assert results.count('option_b') > results.count('option_a')

    def test_budget_tracking(self):
        """Test that budget is tracked across operations."""
        dp = DifferentialPrivacy(epsilon=1.0)

        initial_remaining = dp.get_remaining_budget()[0]

        # Perform operation (uses default budget)
        dp.add_noise_to_count(100)

        remaining_after = dp.get_remaining_budget()[0]

        # Budget should have decreased
        assert remaining_after < initial_remaining

    def test_budget_reset(self):
        """Test budget reset functionality."""
        dp = DifferentialPrivacy(epsilon=1.0)

        dp.add_noise_to_count(100)
        assert dp.budget.spent_epsilon > 0

        dp.reset_budget()
        assert dp.budget.spent_epsilon == 0.0

    def test_get_privacy_parameters(self):
        """Test getting privacy parameters."""
        dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)

        params = dp.get_privacy_parameters()

        assert params['epsilon'] == 1.0
        assert params['delta'] == 1e-5
        assert params['mechanism'] == DPMechanism.LAPLACE.value
        assert 'spent_epsilon' in params
        assert 'remaining_epsilon' in params
        assert 'budget_exhausted' in params

    def test_privacy_tradeoff(self):
        """Test privacy-accuracy tradeoff."""
        # Lower epsilon = more privacy = more noise
        dp_high_privacy = DifferentialPrivacy(epsilon=0.1)
        dp_low_privacy = DifferentialPrivacy(epsilon=10.0)

        original = 1000.0
        sensitivity = 1.0

        # Run multiple times to get average noise
        noise_high_privacy = []
        noise_low_privacy = []

        for _ in range(100):
            noisy_high = dp_high_privacy.add_noise_to_value(
                original, sensitivity, epsilon=0.1
            )
            noisy_low = dp_low_privacy.add_noise_to_value(
                original, sensitivity, epsilon=10.0
            )

            noise_high_privacy.append(abs(noisy_high - original))
            noise_low_privacy.append(abs(noisy_low - original))

        avg_noise_high = sum(noise_high_privacy) / len(noise_high_privacy)
        avg_noise_low = sum(noise_low_privacy) / len(noise_low_privacy)

        # Higher privacy (lower epsilon) should have more noise
        assert avg_noise_high > avg_noise_low


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_laplace_noise_function(self):
        """Test laplace_noise convenience function."""
        value = 100.0
        noisy = laplace_noise(value, sensitivity=1.0, epsilon=1.0)

        assert noisy != value

    def test_gaussian_noise_function(self):
        """Test gaussian_noise convenience function."""
        value = 100.0
        noisy = gaussian_noise(value, sensitivity=1.0, epsilon=1.0, delta=1e-5)

        assert noisy != value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
