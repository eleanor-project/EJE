"""
Caching utilities for the EJE.
Provides LRU cache for decision results to avoid redundant API calls.
"""

import json
import hashlib
from functools import lru_cache
from typing import Dict, Any


def generate_case_hash(case: Dict[str, Any]) -> str:
    """
    Generate a deterministic hash for a case dictionary.

    Args:
        case: The case dictionary to hash

    Returns:
        SHA-256 hash string
    """
    # Sort keys to ensure deterministic hashing
    case_json = json.dumps(case, sort_keys=True)
    return hashlib.sha256(case_json.encode()).hexdigest()


class DecisionCache:
    """
    LRU cache for decision results.
    Caches decisions by case hash to avoid redundant evaluations.
    """

    def __init__(self, maxsize=1000):
        """
        Initialize the cache.

        Args:
            maxsize: Maximum number of cached decisions
        """
        self.maxsize = maxsize
        self._cache = {}
        self._access_order = []
        self.hits = 0
        self.misses = 0

    def get(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get cached decision for a case.

        Args:
            case: The case to lookup

        Returns:
            Cached decision or None if not found
        """
        case_hash = generate_case_hash(case)

        if case_hash in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(case_hash)
            self._access_order.append(case_hash)
            self.hits += 1
            return self._cache[case_hash]

        self.misses += 1
        return None

    def put(self, case: Dict[str, Any], decision: Dict[str, Any]):
        """
        Cache a decision result.

        Args:
            case: The case that was evaluated
            decision: The decision result to cache
        """
        case_hash = generate_case_hash(case)

        # If cache is full, remove least recently used
        if len(self._cache) >= self.maxsize and case_hash not in self._cache:
            lru_hash = self._access_order.pop(0)
            del self._cache[lru_hash]

        # Add or update cache
        if case_hash in self._cache:
            self._access_order.remove(case_hash)

        self._cache[case_hash] = decision
        self._access_order.append(case_hash)

    def clear(self):
        """Clear the entire cache."""
        self._cache.clear()
        self._access_order.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }
