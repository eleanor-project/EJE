"""
Tests for performance optimizations.

Tests caching, parallel execution, and performance manager.
"""

import pytest
import time
from ejc.core.performance import (
    CriticCache,
    CacheConfig,
    ParallelCriticExecutor,
    PerformanceManager,
)


# Mock critic functions for testing
def mock_critic_fast(input_data, config):
    """Fast mock critic (10ms)."""
    time.sleep(0.01)
    return {
        "critic": "fast_critic",
        "verdict": "ALLOW",
        "confidence": 0.9,
    }


def mock_critic_slow(input_data, config):
    """Slow mock critic (100ms)."""
    time.sleep(0.1)
    return {
        "critic": "slow_critic",
        "verdict": "ALLOW",
        "confidence": 0.85,
    }


def mock_critic_error(input_data, config):
    """Critic that raises an error."""
    raise ValueError("Test error")


@pytest.fixture
def cache():
    """Create cache instance."""
    return CriticCache(CacheConfig(max_size=100, ttl_seconds=60))


@pytest.fixture
def parallel_executor():
    """Create parallel executor."""
    return ParallelCriticExecutor(max_workers=3, timeout_seconds=5.0)


@pytest.fixture
def performance_manager():
    """Create performance manager."""
    return PerformanceManager(
        cache_config=CacheConfig(max_size=100),
        max_parallel_workers=3,
        enable_caching=True,
        enable_parallel=True,
    )


class TestCriticCache:
    """Test critic result caching."""

    def test_cache_miss(self, cache):
        """Test cache miss on first access."""
        result = cache.get("test_critic", {"prompt": "test"})
        assert result is None
        assert cache.misses == 1

    def test_cache_hit(self, cache):
        """Test cache hit on second access."""
        input_data = {"prompt": "test"}
        result_data = {"verdict": "ALLOW", "confidence": 0.9}

        # Set cache
        cache.set("test_critic", input_data, result_data)

        # Get from cache
        cached = cache.get("test_critic", input_data)
        assert cached is not None
        assert cached["verdict"] == "ALLOW"
        assert cache.hits == 1

    def test_cache_invalidation(self, cache):
        """Test cache invalidation."""
        cache.set("critic1", {"test": 1}, {"result": 1})
        cache.set("critic2", {"test": 2}, {"result": 2})

        # Invalidate critic1
        cache.invalidate(critic_name="critic1")

        assert cache.get("critic1", {"test": 1}) is None
        assert cache.get("critic2", {"test": 2}) is not None

    def test_cache_eviction(self):
        """Test LRU eviction."""
        small_cache = CriticCache(CacheConfig(max_size=2))

        # Fill cache
        small_cache.set("c1", {"i": 1}, {"r": 1})
        small_cache.set("c2", {"i": 2}, {"r": 2})

        # Add third entry (should evict c1)
        small_cache.set("c3", {"i": 3}, {"r": 3})

        assert small_cache.get("c1", {"i": 1}) is None  # Evicted
        assert small_cache.get("c2", {"i": 2}) is not None
        assert small_cache.get("c3", {"i": 3}) is not None

    def test_cache_statistics(self, cache):
        """Test cache statistics."""
        cache.set("c1", {"i": 1}, {"r": 1})
        cache.get("c1", {"i": 1})  # Hit
        cache.get("c2", {"i": 2})  # Miss

        stats = cache.get_statistics()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert 0 <= stats["hit_rate"] <= 1


class TestParallelCriticExecutor:
    """Test parallel critic execution."""

    def test_parallel_execution(self, parallel_executor):
        """Test executing critics in parallel."""
        critics = [mock_critic_fast, mock_critic_slow]
        input_data = {"prompt": "test"}
        config = {}

        start = time.time()
        results = parallel_executor.execute_critics_parallel(
            critics, input_data, config
        )
        elapsed = time.time() - start

        # Should complete in ~100ms (slow critic time), not 110ms (sequential)
        assert elapsed < 0.15  # Allow some overhead
        assert len(results) == 2

    def test_error_handling(self, parallel_executor):
        """Test error handling in parallel execution."""
        critics = [mock_critic_fast, mock_critic_error]
        input_data = {"prompt": "test"}
        config = {}

        results = parallel_executor.execute_critics_parallel(
            critics, input_data, config
        )

        assert len(results) == 2
        # First should succeed
        assert results[0]["verdict"] == "ALLOW"
        # Second should have error
        assert "error" in results[1]

    def test_performance_metrics(self, parallel_executor):
        """Test performance metrics calculation."""
        critics = [mock_critic_fast, mock_critic_slow]
        input_data = {"prompt": "test"}
        config = {}

        results = parallel_executor.execute_critics_parallel(
            critics, input_data, config
        )

        metrics = parallel_executor.get_performance_metrics(results)

        assert metrics["total_critics"] == 2
        assert metrics["speedup"] > 1.0  # Should have speedup
        assert metrics["max_time_ms"] > 0


class TestPerformanceManager:
    """Test integrated performance manager."""

    def test_cache_integration(self, performance_manager):
        """Test cache integration."""
        critics = [mock_critic_fast]
        input_data = {"prompt": "test"}
        config = {}

        # First call - should execute
        result1 = performance_manager.execute_critics(
            critics, input_data, config
        )
        assert result1["performance"]["from_cache"] == 0

        # Second call - should use cache
        result2 = performance_manager.execute_critics(
            critics, input_data, config
        )
        assert result2["performance"]["from_cache"] == 1
        assert result2["performance"]["cache_hit_rate"] == 1.0

    def test_parallel_integration(self, performance_manager):
        """Test parallel execution integration."""
        critics = [mock_critic_fast, mock_critic_slow]
        input_data = {"prompt": "test"}
        config = {}

        result = performance_manager.execute_critics(
            critics, input_data, config
        )

        assert result["performance"]["parallel_execution"] is True
        assert result["performance"]["critics_total"] == 2
        assert len(result["results"]) == 2

    def test_overall_statistics(self, performance_manager):
        """Test overall statistics."""
        critics = [mock_critic_fast]
        input_data = {"prompt": "test"}
        config = {}

        # Execute a few times
        for _ in range(3):
            performance_manager.execute_critics(critics, input_data, config)

        stats = performance_manager.get_overall_statistics()

        assert stats["total_requests"] == 3
        assert "cache" in stats
        assert stats["cache"]["hits"] >= 2  # Should have cache hits

    def test_cache_invalidation_integration(self, performance_manager):
        """Test cache invalidation through manager."""
        critics = [mock_critic_fast]
        input_data = {"prompt": "test"}
        config = {}

        # Cache result
        performance_manager.execute_critics(critics, input_data, config)

        # Invalidate
        performance_manager.invalidate_cache(critic_name="mock_critic_fast")

        # Next call should re-execute
        result = performance_manager.execute_critics(critics, input_data, config)
        assert result["performance"]["from_cache"] == 0


class TestIntegrationPerformance:
    """Integration tests for performance system."""

    def test_combined_optimizations(self):
        """Test cache + parallel working together."""
        manager = PerformanceManager(
            cache_config=CacheConfig(max_size=100),
            enable_caching=True,
            enable_parallel=True,
        )

        critics = [mock_critic_fast, mock_critic_slow]
        input_data = {"prompt": "test"}
        config = {}

        # First run: parallel execution, no cache
        result1 = manager.execute_critics(critics, input_data, config)
        time1 = result1["performance"]["total_time_ms"]
        assert result1["performance"]["from_cache"] == 0

        # Second run: should use cache for both
        result2 = manager.execute_critics(critics, input_data, config)
        time2 = result2["performance"]["total_time_ms"]
        assert result2["performance"]["from_cache"] == 2

        # Cache should be faster
        assert time2 < time1

    def test_performance_improvements(self):
        """Verify actual performance improvements."""
        # Without optimizations
        manager_slow = PerformanceManager(
            enable_caching=False,
            enable_parallel=False,
        )

        # With optimizations
        manager_fast = PerformanceManager(
            enable_caching=True,
            enable_parallel=True,
        )

        critics = [mock_critic_fast, mock_critic_slow]
        input_data = {"prompt": "test"}
        config = {}

        # Sequential without cache
        start = time.time()
        manager_slow.execute_critics(critics, input_data, config)
        sequential_time = time.time() - start

        # Parallel (first run, no cache benefit yet)
        start = time.time()
        result_fast = manager_fast.execute_critics(critics, input_data, config)
        parallel_time = time.time() - start

        # Parallel should be faster than sequential
        assert parallel_time < sequential_time

        # With cache (second run)
        start = time.time()
        result_cached = manager_fast.execute_critics(critics, input_data, config)
        cached_time = time.time() - start

        # Cache should be even faster
        assert cached_time < parallel_time
        assert result_cached["performance"]["cache_hit_rate"] == 1.0

        # Cleanup
        manager_slow.cleanup()
        manager_fast.cleanup()
