"""
Performance optimizations for EJC system.

Provides:
- Critic result caching with LRU and TTL
- Parallel critic execution
- Performance monitoring
"""

from .cache import CriticCache, CacheConfig
from .parallel import ParallelCriticExecutor
from .performance_manager import PerformanceManager

__all__ = [
    "CriticCache",
    "CacheConfig",
    "ParallelCriticExecutor",
    "PerformanceManager",
]
