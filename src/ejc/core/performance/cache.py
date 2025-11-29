"""
Critic result caching for performance optimization.

Implements LRU cache with TTL for critic results.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
import hashlib
import json
from collections import OrderedDict


@dataclass
class CacheConfig:
    """Configuration for critic cache."""

    max_size: int = 1000  # Maximum cache entries
    ttl_seconds: int = 3600  # Time-to-live (1 hour)
    enabled: bool = True

    # Cache invalidation on configuration changes
    version_key: str = "v1"


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""

    key: str
    result: Dict[str, Any]
    timestamp: datetime
    hits: int = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry is expired."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > ttl_seconds

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "hits": self.hits,
        }


class CriticCache:
    """
    LRU cache for critic results with TTL.

    Caches critic evaluations to avoid redundant computations.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(
        self,
        critic_name: str,
        input_data: Dict[str, Any],
        config_version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached critic result.

        Args:
            critic_name: Name of critic
            input_data: Input that was evaluated
            config_version: Configuration version (for invalidation)

        Returns:
            Cached result or None if not found/expired
        """
        if not self.config.enabled:
            return None

        cache_key = self._generate_key(critic_name, input_data, config_version)

        if cache_key not in self._cache:
            self.misses += 1
            return None

        entry = self._cache[cache_key]

        # Check expiration
        if entry.is_expired(self.config.ttl_seconds):
            del self._cache[cache_key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(cache_key)
        entry.hits += 1
        self.hits += 1

        return entry.result.copy()

    def set(
        self,
        critic_name: str,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
        config_version: Optional[str] = None
    ):
        """
        Cache a critic result.

        Args:
            critic_name: Name of critic
            input_data: Input that was evaluated
            result: Critic result to cache
            config_version: Configuration version
        """
        if not self.config.enabled:
            return

        cache_key = self._generate_key(critic_name, input_data, config_version)

        # Evict oldest if at capacity
        if len(self._cache) >= self.config.max_size and cache_key not in self._cache:
            self._cache.popitem(last=False)  # Remove oldest
            self.evictions += 1

        # Add/update entry
        self._cache[cache_key] = CacheEntry(
            key=cache_key,
            result=result.copy(),
            timestamp=datetime.utcnow(),
        )

        # Move to end (most recently used)
        self._cache.move_to_end(cache_key)

    def invalidate(
        self,
        critic_name: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            critic_name: Invalidate specific critic (None = all)
            pattern: Invalidate keys matching pattern
        """
        if critic_name is None and pattern is None:
            # Clear all
            self._cache.clear()
            return

        # Remove matching entries
        keys_to_remove = []
        for key in self._cache:
            if critic_name and critic_name in key:
                keys_to_remove.append(key)
            elif pattern and pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    def _generate_key(
        self,
        critic_name: str,
        input_data: Dict[str, Any],
        config_version: Optional[str]
    ) -> str:
        """
        Generate cache key from inputs.

        Args:
            critic_name: Name of critic
            input_data: Input data
            config_version: Configuration version

        Returns:
            Cache key string
        """
        # Create deterministic representation
        data_str = json.dumps(input_data, sort_keys=True)
        version = config_version or self.config.version_key

        # Hash for compact key
        combined = f"{critic_name}:{version}:{data_str}"
        key_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

        return f"{critic_name}:{key_hash}"

    def get_statistics(self) -> Dict:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        # Calculate average age of cached entries
        now = datetime.utcnow()
        ages = [(now - entry.timestamp).total_seconds() for entry in self._cache.values()]
        avg_age = sum(ages) / len(ages) if ages else 0.0

        return {
            "enabled": self.config.enabled,
            "size": len(self._cache),
            "max_size": self.config.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
            "avg_age_seconds": avg_age,
            "ttl_seconds": self.config.ttl_seconds,
        }

    def cleanup_expired(self):
        """Remove all expired entries."""
        now = datetime.utcnow()
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if entry.is_expired(self.config.ttl_seconds)
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)
