"""
Production-ready Query Cache with LRU eviction and TTL support.

Features:
- LRU eviction with configurable max size
- TTL-based expiration
- Thread-safe operations
- Hit/miss metrics tracking
- Tag-based invalidation
- Pattern-based invalidation
- Cache key normalization

Target: 95%+ cache hit rate for production workloads.
"""

import fnmatch
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CacheBackend(Enum):
    """Available cache backends."""
    MEMORY = "memory"
    REDIS = "redis"
    FILE = "file"


@dataclass
class CacheConfig:
    """Configuration for QueryCache.

    Attributes:
        max_size: Maximum number of entries in cache
        ttl_seconds: Default time-to-live in seconds
        backend: Cache backend type
        enable_metrics: Whether to track metrics
        cache_key_prefix: Prefix for cache keys
    """
    max_size: int = 1000
    ttl_seconds: int = 3600
    backend: CacheBackend = CacheBackend.MEMORY
    enable_metrics: bool = True
    cache_key_prefix: str = "knowdb"

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_size <= 0:
            raise ValueError("max_size must be positive")
        if self.ttl_seconds < 0:
            raise ValueError("ttl_seconds must be non-negative")


@dataclass
class CacheEntry:
    """Individual cache entry with metadata.

    Attributes:
        value: Cached data
        created_at: When entry was created
        expires_at: When entry expires
        key: Cache key (hashed)
        access_count: Number of times accessed
        tags: Optional tags for invalidation
        original_key: Original key before hashing
    """
    value: Any
    created_at: datetime
    expires_at: datetime
    key: str
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    original_key: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to dictionary."""
        return {
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "key": self.key,
            "access_count": self.access_count,
            "tags": self.tags,
            "original_key": self.original_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Deserialize entry from dictionary."""
        return cls(
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            key=data["key"],
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
            original_key=data.get("original_key", ""),
        )


@dataclass
class CacheMetrics:
    """Cache performance metrics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of evicted entries
        total_queries: Total number of queries
    """
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    last_reset: datetime = field(default_factory=datetime.now)


class QueryCache:
    """
    Production-ready query cache with LRU eviction and TTL support.

    Thread-safe implementation targeting 95%+ hit rate for repeated queries.

    Example:
        >>> cache = QueryCache()
        >>> cache.set("SELECT * FROM users", {"data": [...]})
        >>> result = cache.get("SELECT * FROM users")
        >>> print(cache.hit_rate)
        1.0
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize cache with configuration.

        Args:
            config: Optional cache configuration
        """
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._metrics = CacheMetrics()
        self._lock = threading.RLock()
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> set of keys

        logger.info(f"QueryCache initialized: max_size={self.config.max_size}, "
                   f"ttl={self.config.ttl_seconds}s")

    def _generate_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate deterministic cache key from query and parameters.

        Normalizes query by removing extra whitespace and converting to lowercase.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            SHA256 hash of normalized query and params
        """
        # Normalize query: lowercase, single spaces
        normalized = " ".join(query.lower().split())

        # Include sorted params in hash
        params_str = json.dumps(params or {}, sort_keys=True)

        content = f"{normalized}|{params_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, key: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached value by key.

        Updates LRU order on access. Returns None for misses or expired entries.

        Args:
            key: Query string or cache key
            params: Optional query parameters

        Returns:
            Cached value or None
        """
        cache_key = self._generate_key(key, params)

        with self._lock:
            if self.config.enable_metrics:
                self._metrics.total_queries += 1

            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check expiration
                if entry.is_expired:
                    self._remove_entry(cache_key)
                    if self.config.enable_metrics:
                        self._metrics.misses += 1
                    return None

                # Update LRU order
                self._cache.move_to_end(cache_key)
                entry.access_count += 1

                if self.config.enable_metrics:
                    self._metrics.hits += 1

                logger.debug(f"Cache HIT: {cache_key[:8]}...")
                return entry.value

            if self.config.enable_metrics:
                self._metrics.misses += 1

            logger.debug(f"Cache MISS: {cache_key[:8]}...")
            return None

    def set(
        self,
        key: str,
        value: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Set cache entry.

        Implements LRU eviction when at capacity.

        Args:
            key: Query string or cache key
            value: Value to cache
            params: Optional query parameters
            ttl: Optional custom TTL in seconds
            tags: Optional tags for invalidation

        Returns:
            True if cached successfully
        """
        cache_key = self._generate_key(key, params)
        ttl_seconds = ttl if ttl is not None else self.config.ttl_seconds

        with self._lock:
            # Remove if exists (for update)
            if cache_key in self._cache:
                self._remove_entry(cache_key)

            # Evict LRU entries if at capacity
            while len(self._cache) >= self.config.max_size:
                self._evict_lru()

            # Create entry
            now = datetime.now()
            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                key=cache_key,
                access_count=0,
                tags=tags or [],
                original_key=key,
            )

            # Add to cache
            self._cache[cache_key] = entry

            # Update tag index
            for tag in entry.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(cache_key)

            logger.debug(f"Cached: {cache_key[:8]}... (TTL: {ttl_seconds}s)")
            return True

    def delete(self, key: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Delete cache entry by key.

        Args:
            key: Query string or cache key
            params: Optional query parameters

        Returns:
            True if entry was deleted
        """
        cache_key = self._generate_key(key, params)

        with self._lock:
            if cache_key in self._cache:
                self._remove_entry(cache_key)
                return True
            return False

    def invalidate(self, key: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Invalidate cache entry (alias for delete).

        Args:
            key: Query string or cache key
            params: Optional query parameters

        Returns:
            True if entry was invalidated
        """
        return self.delete(key, params)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "users:*")

        Returns:
            Number of invalidated entries
        """
        with self._lock:
            keys_to_remove = [
                k for k, entry in self._cache.items()
                if fnmatch.fnmatch(entry.original_key, pattern)
            ]

            for key in keys_to_remove:
                self._remove_entry(key)

            return len(keys_to_remove)

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with given tag.

        Args:
            tag: Tag to match

        Returns:
            Number of invalidated entries
        """
        with self._lock:
            if tag not in self._tag_index:
                return 0

            keys_to_remove = list(self._tag_index[tag])

            for key in keys_to_remove:
                self._remove_entry(key)

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._tag_index.clear()
            logger.info("Cache cleared")

    def _remove_entry(self, key: str) -> None:
        """Remove entry and update indexes.

        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            entry = self._cache[key]

            # Remove from tag index
            for tag in entry.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(key)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]

            del self._cache[key]

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self._metrics.evictions += 1
            logger.debug(f"Evicted LRU: {oldest_key[:8]}...")

    @property
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._metrics.hits + self._metrics.misses
        if total == 0:
            return 0.0
        return self._metrics.hits / total

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        with self._lock:
            self._metrics = CacheMetrics()
            logger.info("Cache metrics reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "hits": self._metrics.hits,
                "misses": self._metrics.misses,
                "hit_rate": f"{self.hit_rate:.2%}",
                "evictions": self._metrics.evictions,
                "total_queries": self._metrics.total_queries,
                "ttl_seconds": self.config.ttl_seconds,
                "backend": self.config.backend.value,
            }


def cached_query(
    cache: QueryCache,
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None,
) -> Callable:
    """Decorator to cache query function results.

    Args:
        cache: QueryCache instance
        ttl: Optional custom TTL
        tags: Optional tags for invalidation

    Returns:
        Decorated function

    Example:
        >>> cache = QueryCache()
        >>> @cached_query(cache, ttl=300)
        ... def get_users(query: str):
        ...     return execute_query(query)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args, **kwargs) -> Any:
            # Check cache first
            result = cache.get(query)
            if result is not None:
                return result

            # Execute function
            result = func(query, *args, **kwargs)

            # Cache result
            cache.set(query, result, ttl=ttl, tags=tags)

            return result
        return wrapper
    return decorator
