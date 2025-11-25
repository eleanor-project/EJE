"""
Performance benchmarks for the Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF).

Measures:
- Decision latency
- Throughput
- Cache hit rates
- Database query performance
- Embedding generation speed
"""

import time
import statistics
import json
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.eje.core.ethical_reasoning_engine import EthicalReasoningEngine
from src.eje.core.precedent_manager_sqlite import PrecedentManagerSQLite
from src.eje.utils.logging import get_logger

logger = get_logger("EJC.Benchmarks")


class BenchmarkSuite:
    """Performance benchmark suite for EJE."""

    def __init__(self, config_path: str = "config/global.yaml"):
        self.config_path = config_path
        self.results: Dict[str, Any] = {}

    def run_all(self) -> Dict[str, Any]:
        """Run all benchmarks and return results."""
        logger.info("=" * 60)
        logger.info("Starting EJE Performance Benchmarks")
        logger.info("=" * 60)

        self.benchmark_single_decision()
        self.benchmark_decision_throughput()
        self.benchmark_cache_performance()
        self.benchmark_precedent_lookup()
        self.benchmark_embedding_generation()
        self.benchmark_parallel_critics()

        logger.info("=" * 60)
        logger.info("Benchmark Summary")
        logger.info("=" * 60)
        self.print_summary()

        return self.results

    def benchmark_single_decision(self, iterations: int = 10):
        """Benchmark single decision latency."""
        logger.info("\n[1/6] Benchmarking single decision latency...")

        engine = EthicalReasoningEngine(self.config_path)

        test_case = {
            "text": "This is a test case for performance benchmarking. " * 10
        }

        latencies = []

        # Warmup
        engine.evaluate(test_case)

        # Actual benchmark
        for i in range(iterations):
            start = time.perf_counter()
            engine.evaluate(test_case)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        self.results['single_decision'] = {
            'mean_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'stdev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'iterations': iterations
        }

        logger.info(f"  Mean latency: {self.results['single_decision']['mean_latency_ms']:.2f}ms")
        logger.info(f"  Median latency: {self.results['single_decision']['median_latency_ms']:.2f}ms")

    def benchmark_decision_throughput(self, duration_seconds: int = 5):
        """Benchmark decision throughput (decisions per second)."""
        logger.info("\n[2/6] Benchmarking decision throughput...")

        engine = EthicalReasoningEngine(self.config_path)

        test_cases = [
            {"text": f"Test case {i} for throughput benchmarking. " * 10}
            for i in range(100)
        ]

        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        decisions = 0

        while time.perf_counter() < end_time:
            engine.evaluate(test_cases[decisions % len(test_cases)])
            decisions += 1

        elapsed = time.perf_counter() - start_time
        throughput = decisions / elapsed

        self.results['throughput'] = {
            'decisions_per_second': throughput,
            'total_decisions': decisions,
            'duration_seconds': elapsed
        }

        logger.info(f"  Throughput: {throughput:.2f} decisions/second")
        logger.info(f"  Total decisions: {decisions}")

    def benchmark_cache_performance(self, cache_size: int = 100):
        """Benchmark cache hit rates and performance."""
        logger.info("\n[3/6] Benchmarking cache performance...")

        engine = EthicalReasoningEngine(self.config_path)

        # Create test cases
        test_cases = [
            {"text": f"Unique case {i} for cache testing"}
            for i in range(cache_size)
        ]

        # Prime the cache
        for case in test_cases:
            engine.evaluate(case)

        # Benchmark cache hits
        cache_hits = 0
        total_lookups = cache_size * 2

        start = time.perf_counter()

        for _ in range(2):  # Run twice to test cache hits
            for case in test_cases:
                result = engine.evaluate(case)
                if result.get('from_cache'):
                    cache_hits += 1

        end = time.perf_counter()

        cache_hit_rate = cache_hits / total_lookups
        avg_lookup_time = ((end - start) / total_lookups) * 1000  # ms

        self.results['cache'] = {
            'cache_hit_rate': cache_hit_rate,
            'avg_lookup_time_ms': avg_lookup_time,
            'cache_size': cache_size,
            'total_lookups': total_lookups,
            'cache_hits': cache_hits
        }

        logger.info(f"  Cache hit rate: {cache_hit_rate * 100:.1f}%")
        logger.info(f"  Avg lookup time: {avg_lookup_time:.3f}ms")

    def benchmark_precedent_lookup(self, db_path: str = "./eleanor_data/precedents.db"):
        """Benchmark precedent lookup performance."""
        logger.info("\n[4/6] Benchmarking precedent lookup...")

        try:
            pm = PrecedentManagerSQLite(db_path)

            test_case = {"text": "Test case for precedent lookup benchmarking"}

            # Hash-based lookup
            start = time.perf_counter()
            for _ in range(100):
                pm.lookup(test_case, max_results=10)
            end = time.perf_counter()

            avg_lookup_time = ((end - start) / 100) * 1000  # ms

            # Get database stats
            stats = pm.get_statistics()

            self.results['precedent_lookup'] = {
                'avg_lookup_time_ms': avg_lookup_time,
                'total_precedents': stats.get('total_precedents', 0),
                'embeddings_enabled': stats.get('embeddings_enabled', False)
            }

            logger.info(f"  Avg lookup time: {avg_lookup_time:.2f}ms")
            logger.info(f"  Total precedents: {stats.get('total_precedents', 0)}")

        except Exception as e:
            logger.warning(f"  Precedent lookup benchmark skipped: {e}")
            self.results['precedent_lookup'] = {'error': str(e)}

    def benchmark_embedding_generation(self, iterations: int = 50):
        """Benchmark embedding generation speed."""
        logger.info("\n[5/6] Benchmarking embedding generation...")

        try:
            pm = PrecedentManagerSQLite("./eleanor_data/precedents.db", use_embeddings=True)

            if not pm.use_embeddings:
                logger.warning("  Embeddings disabled, skipping...")
                self.results['embedding_generation'] = {'skipped': True}
                return

            test_cases = [
                {"text": f"Test case {i} for embedding generation. " * 20}
                for i in range(iterations)
            ]

            times = []

            for case in test_cases:
                start = time.perf_counter()
                pm._embed_case(case)
                end = time.perf_counter()
                times.append((end - start) * 1000)

            self.results['embedding_generation'] = {
                'mean_time_ms': statistics.mean(times),
                'median_time_ms': statistics.median(times),
                'min_time_ms': min(times),
                'max_time_ms': max(times),
                'iterations': iterations
            }

            logger.info(f"  Mean generation time: {statistics.mean(times):.2f}ms")
            logger.info(f"  Median generation time: {statistics.median(times):.2f}ms")

        except Exception as e:
            logger.warning(f"  Embedding benchmark skipped: {e}")
            self.results['embedding_generation'] = {'error': str(e)}

    def benchmark_parallel_critics(self, num_critics: int = 3):
        """Benchmark parallel critic execution."""
        logger.info("\n[6/6] Benchmarking parallel critic execution...")

        engine = EthicalReasoningEngine(self.config_path)

        if len(engine.critics) == 0:
            logger.warning("  No critics loaded, skipping...")
            self.results['parallel_critics'] = {'skipped': True}
            return

        test_case = {
            "text": "Test case for parallel critic execution benchmarking. " * 10
        }

        # Measure with parallel execution
        start = time.perf_counter()
        for _ in range(10):
            engine.evaluate(test_case)
        parallel_time = time.perf_counter() - start

        self.results['parallel_critics'] = {
            'total_critics': len(engine.critics),
            'parallel_execution_time_s': parallel_time,
            'avg_decision_time_ms': (parallel_time / 10) * 1000,
            'max_workers': engine.max_workers
        }

        logger.info(f"  Total critics: {len(engine.critics)}")
        logger.info(f"  Avg decision time: {(parallel_time / 10) * 1000:.2f}ms")
        logger.info(f"  Max parallel workers: {engine.max_workers}")

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 60)

        if 'single_decision' in self.results:
            print(f"\n📊 Single Decision Performance:")
            print(f"   Mean Latency: {self.results['single_decision']['mean_latency_ms']:.2f}ms")
            print(f"   Std Dev: {self.results['single_decision']['stdev_ms']:.2f}ms")

        if 'throughput' in self.results:
            print(f"\n🚀 Throughput:")
            print(f"   {self.results['throughput']['decisions_per_second']:.2f} decisions/second")

        if 'cache' in self.results:
            print(f"\n💾 Cache Performance:")
            print(f"   Hit Rate: {self.results['cache']['cache_hit_rate'] * 100:.1f}%")
            print(f"   Lookup Time: {self.results['cache']['avg_lookup_time_ms']:.3f}ms")

        if 'precedent_lookup' in self.results and 'error' not in self.results['precedent_lookup']:
            print(f"\n🔍 Precedent Lookup:")
            print(f"   Avg Time: {self.results['precedent_lookup']['avg_lookup_time_ms']:.2f}ms")
            print(f"   Database Size: {self.results['precedent_lookup']['total_precedents']} precedents")

        print("\n" + "=" * 60)

    def save_results(self, filename: str = "benchmark_results.json"):
        """Save benchmark results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\n📝 Results saved to {filename}")


def main():
    """Run benchmarks."""
    import argparse

    parser = argparse.ArgumentParser(description="EJE Performance Benchmarks")
    parser.add_argument(
        "--config",
        default="config/global.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Output file for results"
    )

    args = parser.parse_args()

    suite = BenchmarkSuite(args.config)
    suite.run_all()
    suite.save_results(args.output)


if __name__ == "__main__":
    main()
