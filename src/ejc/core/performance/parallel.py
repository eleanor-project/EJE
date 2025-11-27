"""
Parallel critic execution for performance optimization.

Executes critics in parallel using asyncio.
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
import time


class ParallelCriticExecutor:
    """
    Executes critics in parallel to reduce latency.

    Uses asyncio for concurrent execution of critic evaluations.
    """

    def __init__(
        self,
        max_workers: int = 5,
        timeout_seconds: float = 30.0
    ):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
            timeout_seconds: Timeout for individual critics
        """
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_critics_async(
        self,
        critics: List[Callable],
        input_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute critics in parallel asynchronously.

        Args:
            critics: List of critic callables
            input_data: Input to evaluate
            config: Configuration dict

        Returns:
            List of critic results (in same order as critics)
        """
        # Create tasks for each critic
        tasks = [
            self._execute_critic_async(critic, input_data, config)
            for critic in critics
        ]

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                critic_name = getattr(critics[i], '__name__', f'critic_{i}')
                processed_results.append({
                    "critic": critic_name,
                    "verdict": "REVIEW",
                    "confidence": 0.0,
                    "error": str(result),
                    "execution_time_ms": 0,
                })
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_critic_async(
        self,
        critic: Callable,
        input_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single critic asynchronously.

        Args:
            critic: Critic callable
            input_data: Input to evaluate
            config: Configuration

        Returns:
            Critic result dict
        """
        start_time = time.time()

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    critic,
                    input_data,
                    config
                ),
                timeout=self.timeout_seconds
            )

            execution_time = (time.time() - start_time) * 1000  # ms

            # Add execution time to result
            if isinstance(result, dict):
                result["execution_time_ms"] = execution_time
                return result
            else:
                return {
                    "result": result,
                    "execution_time_ms": execution_time,
                }

        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            critic_name = getattr(critic, '__name__', 'unknown')
            return {
                "critic": critic_name,
                "verdict": "REVIEW",
                "confidence": 0.0,
                "error": f"Timeout after {self.timeout_seconds}s",
                "execution_time_ms": execution_time,
            }

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            critic_name = getattr(critic, '__name__', 'unknown')
            return {
                "critic": critic_name,
                "verdict": "REVIEW",
                "confidence": 0.0,
                "error": str(e),
                "execution_time_ms": execution_time,
            }

    def execute_critics_parallel(
        self,
        critics: List[Callable],
        input_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute critics in parallel (synchronous wrapper).

        Args:
            critics: List of critic callables
            input_data: Input to evaluate
            config: Configuration

        Returns:
            List of critic results
        """
        # Create or get event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async execution
        results = loop.run_until_complete(
            self.execute_critics_async(critics, input_data, config)
        )

        return results

    def get_performance_metrics(self, results: List[Dict]) -> Dict:
        """
        Calculate performance metrics from parallel execution.

        Args:
            results: List of critic results with execution_time_ms

        Returns:
            Performance metrics dict
        """
        execution_times = [
            r.get("execution_time_ms", 0)
            for r in results
            if "execution_time_ms" in r
        ]

        if not execution_times:
            return {
                "total_critics": len(results),
                "avg_time_ms": 0,
                "max_time_ms": 0,
                "total_parallel_time_ms": 0,
                "sequential_time_ms": 0,
                "speedup": 0,
            }

        total_critics = len(results)
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        total_sequential = sum(execution_times)

        # Parallel time is approximately the maximum (longest critic)
        parallel_time = max_time
        speedup = total_sequential / parallel_time if parallel_time > 0 else 0

        return {
            "total_critics": total_critics,
            "avg_time_ms": round(avg_time, 2),
            "max_time_ms": round(max_time, 2),
            "total_parallel_time_ms": round(parallel_time, 2),
            "sequential_time_ms": round(total_sequential, 2),
            "speedup": round(speedup, 2),
        }

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self.executor.shutdown(wait=True)
