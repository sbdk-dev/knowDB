"""
Query Result Caching System

This module implements intelligent query result caching for the semantic layer:
- Multi-backend support (memory, Redis, file-based)
- Smart cache invalidation strategies
- Query fingerprinting and result serialization
- Performance metrics and monitoring
- Configurable TTL and cache policies

Technologies: Redis, JSON serialization, cache strategies
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import threading
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheBackend(Enum):
    """Available cache backends"""

    MEMORY = "memory"
    REDIS = "redis"
    FILE = "file"


@dataclass
class CacheConfig:
    """Configuration for query caching"""

    backend: CacheBackend = CacheBackend.MEMORY
    ttl_seconds: int = 3600  # 1 hour default
    max_memory_items: int = 1000
    redis_url: Optional[str] = "redis://localhost:6379/0"
    file_cache_dir: str = "/tmp/semantic_layer_cache"
    enable_metrics: bool = True
    compress_results: bool = True
    cache_key_prefix: str = "semantic_layer"


@dataclass
class CacheMetrics:
    """Cache performance metrics"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    cache_size: int = 0
    hit_rate: float = 0.0
    last_reset: datetime = None

    def update_hit_rate(self):
        """Update hit rate calculation"""
        if self.total_queries > 0:
            self.hit_rate = self.hits / self.total_queries
        else:
            self.hit_rate = 0.0


@dataclass
class CacheEntry:
    """Individual cache entry"""

    data: Any
    created_at: datetime
    expires_at: datetime
    query_hash: str
    metadata: Dict[str, Any]

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "query_hash": self.query_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        return cls(
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            query_hash=data["query_hash"],
            metadata=data["metadata"],
        )


class CacheBackendInterface(ABC):
    """Abstract interface for cache backends"""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key"""
        pass

    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries"""
        pass

    @abstractmethod
    def get_size(self) -> int:
        """Get current cache size"""
        pass


class MemoryCacheBackend(CacheBackendInterface):
    """In-memory cache backend with LRU eviction"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry, updating access order"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
                    return None

                # Update access order (LRU)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return entry
            return None

    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry with LRU eviction"""
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

            # Evict oldest entries if at capacity
            while len(self._cache) >= self.config.max_memory_items:
                if self._access_order:
                    oldest_key = self._access_order.pop(0)
                    if oldest_key in self._cache:
                        del self._cache[oldest_key]

            # Add new entry
            self._cache[key] = entry
            self._access_order.append(key)
            return True

    def delete(self, key: str) -> bool:
        """Delete specific cache entry"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False

    def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            return True

    def get_size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)


class RedisCacheBackend(CacheBackendInterface):
    """Redis cache backend"""

    def __init__(self, config: CacheConfig):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis package not installed. Install with: pip install redis")

        self.config = config
        self.client = redis.from_url(config.redis_url)
        self._test_connection()

    def _test_connection(self):
        """Test Redis connection"""
        try:
            self.client.ping()
            logger.info("✅ Redis cache backend connected")
        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key"""
        return f"{self.config.cache_key_prefix}:{key}"

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from Redis"""
        try:
            redis_key = self._make_key(key)
            data = self.client.get(redis_key)
            if data:
                entry_dict = json.loads(data.decode("utf-8"))
                entry = CacheEntry.from_dict(entry_dict)
                if entry.is_expired():
                    self.client.delete(redis_key)
                    return None
                return entry
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry in Redis with TTL"""
        try:
            redis_key = self._make_key(key)
            data = json.dumps(entry.to_dict()).encode("utf-8")

            # Calculate remaining TTL
            ttl_seconds = (entry.expires_at - datetime.now()).total_seconds()
            if ttl_seconds > 0:
                self.client.setex(redis_key, int(ttl_seconds), data)
                return True
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")
        return False

    def delete(self, key: str) -> bool:
        """Delete cache entry from Redis"""
        try:
            redis_key = self._make_key(key)
            result = self.client.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis cache delete error: {e}")
        return False

    def clear(self) -> bool:
        """Clear all cache entries with prefix"""
        try:
            pattern = f"{self.config.cache_key_prefix}:*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis cache clear error: {e}")
        return False

    def get_size(self) -> int:
        """Get current cache size"""
        try:
            pattern = f"{self.config.cache_key_prefix}:*"
            return len(self.client.keys(pattern))
        except Exception as e:
            logger.warning(f"Redis cache size error: {e}")
        return 0


class FileCacheBackend(CacheBackendInterface):
    """File-based cache backend"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.file_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get cache file path for key"""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from file"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                with open(file_path, "r") as f:
                    entry_dict = json.load(f)
                entry = CacheEntry.from_dict(entry_dict)
                if entry.is_expired():
                    file_path.unlink(missing_ok=True)
                    return None
                return entry
        except Exception as e:
            logger.warning(f"File cache get error: {e}")
        return None

    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry to file"""
        try:
            file_path = self._get_file_path(key)
            with open(file_path, "w") as f:
                json.dump(entry.to_dict(), f)
            return True
        except Exception as e:
            logger.warning(f"File cache set error: {e}")
        return False

    def delete(self, key: str) -> bool:
        """Delete cache file"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            logger.warning(f"File cache delete error: {e}")
        return False

    def clear(self) -> bool:
        """Clear all cache files"""
        try:
            for file_path in self.cache_dir.glob("*.json"):
                file_path.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.warning(f"File cache clear error: {e}")
        return False

    def get_size(self) -> int:
        """Get current cache size"""
        try:
            return len(list(self.cache_dir.glob("*.json")))
        except Exception as e:
            logger.warning(f"File cache size error: {e}")
        return 0


class QueryCache:
    """
    Main query cache interface with multiple backend support

    Phase 2 Implementation - Scale & Polish: Performance Enhancement
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize query cache with configuration

        Args:
            config: Cache configuration options
        """
        self.config = config or CacheConfig()
        self.metrics = CacheMetrics(last_reset=datetime.now())

        # Initialize backend
        self.backend = self._create_backend()

        logger.info(f"🚀 Query cache initialized with {self.config.backend.value} backend")

    def _create_backend(self) -> CacheBackendInterface:
        """Create appropriate cache backend"""
        if self.config.backend == CacheBackend.MEMORY:
            return MemoryCacheBackend(self.config)
        elif self.config.backend == CacheBackend.REDIS:
            return RedisCacheBackend(self.config)
        elif self.config.backend == CacheBackend.FILE:
            return FileCacheBackend(self.config)
        else:
            raise ValueError(f"Unsupported cache backend: {self.config.backend}")

    def _generate_query_hash(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate unique hash for query and parameters"""
        # Normalize query (remove extra whitespace, convert to lowercase)
        normalized_query = " ".join(query.lower().split())

        # Include parameters in hash
        params_str = json.dumps(parameters or {}, sort_keys=True)

        # Create hash
        content = f"{normalized_query}|{params_str}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

    def get(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get cached query result

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Cached result data or None if not found/expired
        """
        if not self.config.enable_metrics:
            self.metrics = CacheMetrics(last_reset=datetime.now())

        query_hash = self._generate_query_hash(query, parameters)

        try:
            entry = self.backend.get(query_hash)

            # Update metrics
            if self.config.enable_metrics:
                self.metrics.total_queries += 1

            if entry:
                self.metrics.hits += 1
                logger.debug(f"📦 Cache HIT for query hash: {query_hash[:8]}...")
                return entry.data
            else:
                self.metrics.misses += 1
                logger.debug(f"❌ Cache MISS for query hash: {query_hash[:8]}...")
                return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            if self.config.enable_metrics:
                self.metrics.total_queries += 1
                self.metrics.misses += 1
            return None
        finally:
            if self.config.enable_metrics:
                self.metrics.update_hit_rate()
                self.metrics.cache_size = self.backend.get_size()

    def set(
        self,
        query: str,
        result: Any,
        parameters: Optional[Dict[str, Any]] = None,
        custom_ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Cache query result

        Args:
            query: SQL query string
            result: Query result data
            parameters: Query parameters
            custom_ttl: Custom TTL in seconds (overrides config)
            metadata: Additional metadata to store

        Returns:
            True if cached successfully
        """
        query_hash = self._generate_query_hash(query, parameters)

        try:
            # Calculate expiration
            ttl = custom_ttl or self.config.ttl_seconds
            expires_at = datetime.now() + timedelta(seconds=ttl)

            # Create cache entry
            entry = CacheEntry(
                data=result,
                created_at=datetime.now(),
                expires_at=expires_at,
                query_hash=query_hash,
                metadata=metadata or {},
            )

            success = self.backend.set(query_hash, entry)

            if success:
                logger.debug(f"💾 Cached query result: {query_hash[:8]}... (TTL: {ttl}s)")

            return success

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def invalidate(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Invalidate specific cached query

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            True if invalidated successfully
        """
        query_hash = self._generate_query_hash(query, parameters)

        try:
            success = self.backend.delete(query_hash)
            if success:
                logger.debug(f"🗑️ Invalidated cache for query: {query_hash[:8]}...")
            return success
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all cached entries"""
        try:
            success = self.backend.clear()
            if success:
                logger.info("🧹 Cleared all cached entries")
                if self.config.enable_metrics:
                    self.metrics = CacheMetrics(last_reset=datetime.now())
            return success
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return False

    def get_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics"""
        if self.config.enable_metrics:
            self.metrics.cache_size = self.backend.get_size()
            self.metrics.update_hit_rate()
        return self.metrics

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        metrics = self.get_metrics()
        return {
            "backend": self.config.backend.value,
            "cache_size": metrics.cache_size,
            "hits": metrics.hits,
            "misses": metrics.misses,
            "total_queries": metrics.total_queries,
            "hit_rate": f"{metrics.hit_rate:.2%}",
            "evictions": metrics.evictions,
            "ttl_seconds": self.config.ttl_seconds,
            "last_reset": metrics.last_reset.isoformat() if metrics.last_reset else None,
        }

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries (mainly for file/memory backends)"""
        # This is primarily handled by individual backends during get/set operations
        # But can be extended for periodic cleanup
        logger.info("🧹 Running cache cleanup for expired entries")
        return 0


# Decorator for easy caching of functions
def cached_query(cache_instance: QueryCache, ttl: Optional[int] = None):
    """
    Decorator to automatically cache query function results

    Args:
        cache_instance: QueryCache instance
        ttl: Custom TTL in seconds
    """

    def decorator(func):
        def wrapper(query: str, *args, **kwargs):
            # Extract parameters for cache key
            parameters = kwargs.get("parameters", {})

            # Try cache first
            result = cache_instance.get(query, parameters)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(query, *args, **kwargs)
            cache_instance.set(query, result, parameters, ttl)

            return result

        return wrapper

    return decorator


# Example usage and testing
if __name__ == "__main__":
    import time

    print("🚀 Testing Query Cache System")
    print("=" * 50)

    # Test different backends
    backends_to_test = [CacheBackend.MEMORY]
    if REDIS_AVAILABLE:
        backends_to_test.append(CacheBackend.REDIS)
    backends_to_test.append(CacheBackend.FILE)

    for backend in backends_to_test:
        print(f"\n📦 Testing {backend.value.upper()} Backend")
        print("-" * 30)

        try:
            config = CacheConfig(
                backend=backend, ttl_seconds=5, max_memory_items=100  # Short TTL for testing
            )

            cache = QueryCache(config)

            # Test cache miss
            result = cache.get("SELECT * FROM test", {"limit": 10})
            assert result is None
            print("✅ Cache miss test passed")

            # Test cache set and hit
            test_data = {"rows": [{"id": 1, "name": "test"}], "count": 1}
            success = cache.set("SELECT * FROM test", test_data, {"limit": 10})
            assert success
            print("✅ Cache set test passed")

            result = cache.get("SELECT * FROM test", {"limit": 10})
            assert result == test_data
            print("✅ Cache hit test passed")

            # Test different parameters create different cache entries
            cache.set("SELECT * FROM test", {"different": "data"}, {"limit": 20})
            result1 = cache.get("SELECT * FROM test", {"limit": 10})
            result2 = cache.get("SELECT * FROM test", {"limit": 20})
            assert result1 != result2
            print("✅ Parameter differentiation test passed")

            # Test stats
            stats = cache.get_stats()
            assert stats["hits"] > 0
            assert stats["total_queries"] > 0
            print(f"✅ Stats: {stats['hit_rate']} hit rate")

            # Test expiration
            print("⏳ Testing TTL expiration (waiting 6 seconds)...")
            time.sleep(6)
            result = cache.get("SELECT * FROM test", {"limit": 10})
            assert result is None  # Should be expired
            print("✅ TTL expiration test passed")

            # Test clear
            cache.set("SELECT * FROM test", test_data, {"limit": 10})
            success = cache.clear_all()
            assert success
            result = cache.get("SELECT * FROM test", {"limit": 10})
            assert result is None
            print("✅ Cache clear test passed")

        except Exception as e:
            print(f"❌ {backend.value} backend test failed: {e}")
            continue

    # Test decorator
    print(f"\n🎯 Testing Cache Decorator")
    print("-" * 30)

    cache = QueryCache(CacheConfig(backend=CacheBackend.MEMORY))

    @cached_query(cache)
    def mock_query_function(query: str, parameters: Dict[str, Any] = None):
        time.sleep(0.1)  # Simulate slow query
        return {"query": query, "timestamp": time.time()}

    # First call should execute
    start = time.time()
    result1 = mock_query_function("SELECT COUNT(*) FROM users", {"active": True})
    first_call_time = time.time() - start

    # Second call should use cache
    start = time.time()
    result2 = mock_query_function("SELECT COUNT(*) FROM users", {"active": True})
    second_call_time = time.time() - start

    assert result1 == result2
    assert second_call_time < first_call_time  # Should be much faster
    print(f"✅ Decorator test passed (speedup: {first_call_time/second_call_time:.1f}x)")

    print(f"\n🎉 Query Cache System Tests Complete!")
    print(f"📊 Final Stats: {cache.get_stats()}")
