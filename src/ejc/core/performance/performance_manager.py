"""
Performance manager integrating cache and parallel execution.

Provides unified interface for performance optimizations.
"""

from typing import List, Dict, Any, Callable, Optional
import time

from .cache import CriticCache, CacheConfig
from .parallel import ParallelCriticExecutor
from ...utils.logging import get_logger

logger = get_logger("ejc.performance")


class PerformanceManager:
    """
    Unified performance management for EJC system.

    Integrates:
    - Critic result caching
    - Parallel execution
    - Performance monitoring
    """

    def __init__(
        self,
        cache_config: Optional[CacheConfig] = None,
        max_parallel_workers: int = 5,
        enable_caching: bool = True,
        enable_parallel: bool = True
    ):
        """
        Initialize performance manager.

        Args:
            cache_config: Cache configuration
            max_parallel_workers: Max parallel workers
            enable_caching: Enable caching
            enable_parallel: Enable parallel execution
        """
        self.cache = CriticCache(cache_config) if enable_caching else None
        self.parallel_executor = ParallelCriticExecutor(
            max_workers=max_parallel_workers
        ) if enable_parallel else None

        self.enable_caching = enable_caching
        self.enable_parallel = enable_parallel

        # Performance metrics
        self.total_requests = 0
        self.cache_saves_ms = 0  # Time saved by cache
        self.parallel_saves_ms = 0  # Time saved by parallelization

    def execute_critics(
        self,
        critics: List[Callable],
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        config_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute critics with performance optimizations.

        Args:
            critics: List of critic callables
            input_data: Input to evaluate
            config: Configuration dict
            config_version: Config version for cache invalidation

        Returns:
            Dict with results and performance metrics
        """
        self.total_requests += 1
        start_time = time.time()

        # Try to get results from cache
        cached_results = []
        critics_to_execute = []
        critic_names = []

        for critic in critics:
            critic_name = getattr(critic, '__name__', 'unknown_critic')
            critic_names.append(critic_name)

            if self.cache:
                cached_result = self.cache.get(critic_name, input_data, config_version)
                if cached_result:
                    cached_result["from_cache"] = True
                    cached_results.append((critic_name, cached_result))
                    logger.debug(f"Cache hit for {critic_name}")
                else:
                    critics_to_execute.append((critic_name, critic))
            else:
                critics_to_execute.append((critic_name, critic))

        # Execute remaining critics
        executed_results = []
        execution_metrics = {}

        if critics_to_execute:
            if self.enable_parallel and len(critics_to_execute) > 1:
                # Parallel execution
                logger.debug(f"Executing {len(critics_to_execute)} critics in parallel")
                exec_start = time.time()

                just_critics = [c[1] for c in critics_to_execute]
                results = self.parallel_executor.execute_critics_parallel(
                    just_critics, input_data, config
                )

                exec_time_ms = (time.time() - exec_start) * 1000

                # Calculate speedup
                execution_metrics = self.parallel_executor.get_performance_metrics(results)
                sequential_time = execution_metrics.get("sequential_time_ms", exec_time_ms)
                self.parallel_saves_ms += (sequential_time - exec_time_ms)

                # Store results and cache them
                for (critic_name, _), result in zip(critics_to_execute, results):
                    result["from_cache"] = False
                    executed_results.append((critic_name, result))

                    if self.cache:
                        self.cache.set(critic_name, input_data, result, config_version)

            else:
                # Sequential execution (fallback)
                logger.debug(f"Executing {len(critics_to_execute)} critics sequentially")

                for critic_name, critic in critics_to_execute:
                    try:
                        exec_start = time.time()
                        result = critic(input_data, config)
                        exec_time = (time.time() - exec_start) * 1000

                        if isinstance(result, dict):
                            result["execution_time_ms"] = exec_time
                            result["from_cache"] = False
                        else:
                            result = {
                                "result": result,
                                "execution_time_ms": exec_time,
                                "from_cache": False,
                            }

                        executed_results.append((critic_name, result))

                        if self.cache:
                            self.cache.set(critic_name, input_data, result, config_version)

                    except Exception as e:
                        logger.error(f"Error executing {critic_name}: {e}")
                        error_result = {
                            "critic": critic_name,
                            "verdict": "REVIEW",
                            "confidence": 0.0,
                            "error": str(e),
                            "from_cache": False,
                        }
                        executed_results.append((critic_name, error_result))

        # Combine cached and executed results in original order
        all_results = []
        cached_dict = dict(cached_results)
        executed_dict = dict(executed_results)

        for critic_name in critic_names:
            if critic_name in cached_dict:
                all_results.append(cached_dict[critic_name])
                # Estimate time saved (assume avg 100ms per critic)
                self.cache_saves_ms += 100
            elif critic_name in executed_dict:
                all_results.append(executed_dict[critic_name])

        total_time_ms = (time.time() - start_time) * 1000

        return {
            "results": all_results,
            "performance": {
                "total_time_ms": round(total_time_ms, 2),
                "critics_total": len(critics),
                "from_cache": len(cached_results),
                "executed": len(executed_results),
                "cache_hit_rate": len(cached_results) / len(critics) if critics else 0,
                "parallel_execution": self.enable_parallel and len(critics_to_execute) > 1,
                **execution_metrics,
            },
        }

    def get_overall_statistics(self) -> Dict:
        """Get overall performance statistics."""
        stats = {
            "total_requests": self.total_requests,
            "cache_enabled": self.enable_caching,
            "parallel_enabled": self.enable_parallel,
        }

        if self.cache:
            cache_stats = self.cache.get_statistics()
            stats["cache"] = cache_stats
            stats["total_cache_saves_ms"] = round(self.cache_saves_ms, 2)

        if self.parallel_executor:
            stats["parallel"] = {
                "max_workers": self.parallel_executor.max_workers,
                "total_parallel_saves_ms": round(self.parallel_saves_ms, 2),
            }

        return stats

    def cleanup(self):
        """Cleanup resources."""
        if self.cache:
            expired_count = self.cache.cleanup_expired()
            if expired_count > 0:
                logger.debug(f"Cleaned up {expired_count} expired cache entries")

        if self.parallel_executor:
            self.parallel_executor.shutdown()

    def invalidate_cache(
        self,
        critic_name: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            critic_name: Specific critic to invalidate
            pattern: Pattern to match for invalidation
        """
        if self.cache:
            self.cache.invalidate(critic_name, pattern)
            logger.info(f"Cache invalidated: critic={critic_name}, pattern={pattern}")
