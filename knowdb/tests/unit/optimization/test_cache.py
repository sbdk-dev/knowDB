"""
Comprehensive tests for QueryCache optimization module.

Tests cover:
- LRU eviction with TTL
- Cache key generation
- Hit/miss tracking and metrics
- Size management
- Thread-safe operations
- Invalidation support
- Multiple backend support
- Performance optimization for 95%+ hit rate target
"""

import hashlib
import json
import pytest
import time
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, Optional

# Import the modules we're testing (will be implemented)
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src" / "knowdb"
sys.path.insert(0, str(src_path))

from optimization.cache import (
    QueryCache,
    CacheEntry,
    CacheConfig,
    CacheMetrics,
    CacheBackend,
    cached_query,
)
from optimization.optimizer import (
    QueryOptimizer,
    QueryComplexity,
    OptimizationSuggestion,
)


class TestCacheEntry:
    """Test CacheEntry dataclass functionality."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry with required fields."""
        entry = CacheEntry(
            value={"data": [1, 2, 3]},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            key="test_key",
            access_count=0,
        )
        assert entry.value == {"data": [1, 2, 3]}
        assert entry.key == "test_key"
        assert entry.access_count == 0

    def test_cache_entry_is_expired_false(self):
        """Test that entry is not expired when within TTL."""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            key="test",
            access_count=0,
        )
        assert entry.is_expired is False

    def test_cache_entry_is_expired_true(self):
        """Test that entry is expired when past TTL."""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
            key="test",
            access_count=0,
        )
        assert entry.is_expired is True

    def test_cache_entry_serialization(self):
        """Test converting entry to dict and back."""
        original = CacheEntry(
            value={"result": "data"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            key="serialize_test",
            access_count=5,
        )
        serialized = original.to_dict()
        restored = CacheEntry.from_dict(serialized)
        assert restored.value == original.value
        assert restored.key == original.key
        assert restored.access_count == original.access_count


class TestCacheConfig:
    """Test CacheConfig settings."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CacheConfig()
        assert config.max_size == 1000
        assert config.ttl_seconds == 3600
        assert config.backend == CacheBackend.MEMORY
        assert config.enable_metrics is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CacheConfig(
            max_size=500,
            ttl_seconds=1800,
            backend=CacheBackend.MEMORY,
            enable_metrics=False,
        )
        assert config.max_size == 500
        assert config.ttl_seconds == 1800
        assert config.enable_metrics is False

    def test_config_validation_max_size(self):
        """Test that max_size must be positive."""
        with pytest.raises(ValueError):
            CacheConfig(max_size=0)

    def test_config_validation_ttl(self):
        """Test that ttl_seconds must be positive."""
        with pytest.raises(ValueError):
            CacheConfig(ttl_seconds=-1)


class TestQueryCacheBasicOperations:
    """Test basic cache operations."""

    def test_cache_initialization(self):
        """Test cache initializes with default config."""
        cache = QueryCache()
        assert cache.size == 0
        assert cache.hit_rate == 0.0

    def test_cache_set_and_get(self):
        """Test setting and getting a cache entry."""
        cache = QueryCache()
        cache.set("query1", {"result": "data"})
        result = cache.get("query1")
        assert result == {"result": "data"}

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        cache = QueryCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_overwrite(self):
        """Test overwriting existing cache entry."""
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        result = cache.get("key1")
        assert result == "value2"

    def test_cache_delete(self):
        """Test deleting a cache entry."""
        cache = QueryCache()
        cache.set("key1", "value1")
        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.get("key1") is None

    def test_cache_delete_nonexistent(self):
        """Test deleting nonexistent entry returns False."""
        cache = QueryCache()
        deleted = cache.delete("nonexistent")
        assert deleted is False

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCacheKeyGeneration:
    """Test cache key generation from query parameters."""

    def test_key_from_simple_query(self):
        """Test generating key from simple query string."""
        cache = QueryCache()
        key1 = cache._generate_key("SELECT * FROM users")
        key2 = cache._generate_key("SELECT * FROM users")
        assert key1 == key2

    def test_key_from_query_with_params(self):
        """Test generating key from query with parameters."""
        cache = QueryCache()
        key1 = cache._generate_key("SELECT * FROM users", {"limit": 10})
        key2 = cache._generate_key("SELECT * FROM users", {"limit": 10})
        assert key1 == key2

    def test_different_params_different_keys(self):
        """Test that different params generate different keys."""
        cache = QueryCache()
        key1 = cache._generate_key("SELECT * FROM users", {"limit": 10})
        key2 = cache._generate_key("SELECT * FROM users", {"limit": 20})
        assert key1 != key2

    def test_key_normalization(self):
        """Test that whitespace/case differences normalize to same key."""
        cache = QueryCache()
        key1 = cache._generate_key("SELECT * FROM users")
        key2 = cache._generate_key("  SELECT   *   FROM   users  ")
        key3 = cache._generate_key("select * from users")
        assert key1 == key2 == key3

    def test_key_deterministic(self):
        """Test that key generation is deterministic."""
        cache = QueryCache()
        keys = [cache._generate_key("SELECT 1") for _ in range(10)]
        assert len(set(keys)) == 1


class TestLRUEviction:
    """Test LRU eviction behavior."""

    def test_lru_eviction_at_capacity(self):
        """Test that oldest entry is evicted at capacity."""
        config = CacheConfig(max_size=3)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_access_updates_order(self):
        """Test that accessing entry updates its LRU position."""
        config = CacheConfig(max_size=3)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to move it to end
        cache.get("key1")

        # Add key4, should evict key2 (now oldest)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_eviction_count_tracking(self):
        """Test that evictions are tracked in metrics."""
        config = CacheConfig(max_size=2)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        metrics = cache.get_metrics()
        assert metrics.evictions >= 1


class TestTTLExpiration:
    """Test TTL-based expiration."""

    def test_entry_expires_after_ttl(self):
        """Test that entry expires after TTL."""
        config = CacheConfig(ttl_seconds=1)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        time.sleep(1.5)

        result = cache.get("key1")
        assert result is None

    def test_entry_valid_within_ttl(self):
        """Test that entry is valid within TTL."""
        config = CacheConfig(ttl_seconds=10)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        time.sleep(0.1)

        result = cache.get("key1")
        assert result == "value1"

    def test_custom_ttl_per_entry(self):
        """Test setting custom TTL for specific entry."""
        cache = QueryCache()

        cache.set("key1", "value1", ttl=1)
        time.sleep(1.5)

        result = cache.get("key1")
        assert result is None

    def test_expired_entry_evicted_on_access(self):
        """Test that accessing expired entry removes it."""
        config = CacheConfig(ttl_seconds=1)
        cache = QueryCache(config)

        cache.set("key1", "value1")
        initial_size = cache.size

        time.sleep(1.5)
        cache.get("key1")  # Should evict expired entry

        assert cache.size == initial_size - 1


class TestCacheMetrics:
    """Test cache metrics and hit rate tracking."""

    def test_hit_counter(self):
        """Test that hits are counted correctly."""
        cache = QueryCache()
        cache.set("key1", "value1")

        cache.get("key1")
        cache.get("key1")

        metrics = cache.get_metrics()
        assert metrics.hits == 2

    def test_miss_counter(self):
        """Test that misses are counted correctly."""
        cache = QueryCache()

        cache.get("nonexistent1")
        cache.get("nonexistent2")

        metrics = cache.get_metrics()
        assert metrics.misses == 2

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        cache = QueryCache()
        cache.set("key1", "value1")

        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        cache.get("key3")  # Miss

        assert cache.hit_rate == 0.5  # 2 hits / 4 total

    def test_hit_rate_zero_queries(self):
        """Test hit rate is 0 when no queries made."""
        cache = QueryCache()
        assert cache.hit_rate == 0.0

    def test_metrics_reset(self):
        """Test resetting metrics."""
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")

        cache.reset_metrics()

        metrics = cache.get_metrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.total_queries == 0

    def test_cache_size_tracking(self):
        """Test that cache size is tracked correctly."""
        cache = QueryCache()

        cache.set("key1", "value1")
        assert cache.size == 1

        cache.set("key2", "value2")
        assert cache.size == 2

        cache.delete("key1")
        assert cache.size == 1


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_writes(self):
        """Test concurrent writes don't corrupt cache."""
        cache = QueryCache()

        def write_entries(start: int, count: int):
            for i in range(start, start + count):
                cache.set(f"key{i}", f"value{i}")

        threads = [
            threading.Thread(target=write_entries, args=(0, 100)),
            threading.Thread(target=write_entries, args=(100, 100)),
            threading.Thread(target=write_entries, args=(200, 100)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All entries should be present
        assert cache.size == 300

    def test_concurrent_reads_writes(self):
        """Test concurrent reads and writes."""
        cache = QueryCache()
        results = []

        def writer():
            for i in range(50):
                cache.set(f"key{i}", f"value{i}")
                time.sleep(0.001)

        def reader():
            for i in range(50):
                result = cache.get(f"key{i}")
                if result:
                    results.append(result)
                time.sleep(0.001)

        write_thread = threading.Thread(target=writer)
        read_threads = [threading.Thread(target=reader) for _ in range(3)]

        write_thread.start()
        for t in read_threads:
            t.start()

        write_thread.join()
        for t in read_threads:
            t.join()

        # Should have some successful reads
        assert len(results) > 0

    def test_concurrent_metrics_update(self):
        """Test metrics are updated correctly under concurrency."""
        cache = QueryCache()
        cache.set("key1", "value1")

        def hit_cache():
            for _ in range(100):
                cache.get("key1")

        threads = [threading.Thread(target=hit_cache) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        metrics = cache.get_metrics()
        assert metrics.hits == 500


class TestCacheInvalidation:
    """Test cache invalidation support."""

    def test_invalidate_by_key(self):
        """Test invalidating specific key."""
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate_by_pattern(self):
        """Test invalidating keys by pattern."""
        cache = QueryCache()
        cache.set("users:1", "user1")
        cache.set("users:2", "user2")
        cache.set("products:1", "product1")

        cache.invalidate_pattern("users:*")

        assert cache.get("users:1") is None
        assert cache.get("users:2") is None
        assert cache.get("products:1") == "product1"

    def test_invalidate_by_tags(self):
        """Test invalidating by tags."""
        cache = QueryCache()
        cache.set("key1", "value1", tags=["user", "profile"])
        cache.set("key2", "value2", tags=["user", "settings"])
        cache.set("key3", "value3", tags=["product"])

        cache.invalidate_by_tag("user")

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"


class TestCachedQueryDecorator:
    """Test the cached_query decorator."""

    def test_decorator_caches_result(self):
        """Test that decorator caches function result."""
        cache = QueryCache()
        call_count = 0

        @cached_query(cache)
        def expensive_query(query: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": "data"}

        result1 = expensive_query("SELECT * FROM users")
        result2 = expensive_query("SELECT * FROM users")

        assert result1 == result2
        assert call_count == 1  # Only called once

    def test_decorator_different_queries(self):
        """Test that different queries are cached separately."""
        cache = QueryCache()

        @cached_query(cache)
        def query_func(query: str) -> str:
            return f"result for {query}"

        result1 = query_func("query1")
        result2 = query_func("query2")

        assert result1 != result2
        assert cache.size == 2

    def test_decorator_with_custom_ttl(self):
        """Test decorator with custom TTL."""
        cache = QueryCache()

        @cached_query(cache, ttl=1)
        def query_func(query: str) -> str:
            return "result"

        query_func("test")
        time.sleep(1.5)

        # Should call function again after TTL
        query_func("test")

        # Cache miss should have occurred
        metrics = cache.get_metrics()
        assert metrics.misses >= 1


class TestQueryOptimizer:
    """Test QueryOptimizer for complexity analysis."""

    def test_simple_query_complexity(self):
        """Test analyzing simple query complexity."""
        optimizer = QueryOptimizer()
        complexity = optimizer.analyze("SELECT * FROM users")

        assert complexity.level == "low"
        assert complexity.score < 50

    def test_complex_query_with_joins(self):
        """Test analyzing query with multiple joins."""
        optimizer = QueryOptimizer()
        query = """
            SELECT u.*, o.*, p.*
            FROM users u
            JOIN orders o ON u.id = o.user_id
            JOIN products p ON o.product_id = p.id
            WHERE u.active = true
        """
        complexity = optimizer.analyze(query)

        assert complexity.level in ["medium", "high"]
        assert complexity.score > 30

    def test_subquery_complexity(self):
        """Test analyzing query with subqueries."""
        optimizer = QueryOptimizer()
        query = """
            SELECT * FROM users
            WHERE id IN (SELECT user_id FROM orders WHERE total > 100)
        """
        complexity = optimizer.analyze(query)

        assert complexity.score > 40

    def test_cache_recommendation(self):
        """Test optimizer provides cache recommendations."""
        optimizer = QueryOptimizer()
        query = "SELECT COUNT(*) FROM users"

        suggestion = optimizer.suggest_cache_strategy(query)

        assert suggestion.should_cache is True
        assert suggestion.ttl_recommendation > 0

    def test_no_cache_for_volatile_query(self):
        """Test no cache recommended for volatile queries."""
        optimizer = QueryOptimizer()
        query = "SELECT * FROM real_time_events WHERE timestamp > NOW() - INTERVAL '1 minute'"

        suggestion = optimizer.suggest_cache_strategy(query)

        assert suggestion.should_cache is False or suggestion.ttl_recommendation < 60

    def test_index_suggestions(self):
        """Test optimizer suggests indexes."""
        optimizer = QueryOptimizer()
        query = "SELECT * FROM users WHERE email = 'test@example.com'"

        suggestions = optimizer.suggest_indexes(query)

        assert len(suggestions) > 0
        assert any("email" in s.column for s in suggestions)


class TestCachePerformance:
    """Test cache performance targets (95%+ hit rate)."""

    def test_high_hit_rate_with_repeated_queries(self):
        """Test achieving high hit rate with repeated queries."""
        cache = QueryCache()

        # Pre-populate cache
        queries = [f"SELECT * FROM table WHERE id = {i}" for i in range(10)]
        for q in queries:
            cache.set(q, f"result for {q}")

        # Simulate workload with 95% repeated queries
        import random
        for _ in range(1000):
            if random.random() < 0.95:
                q = random.choice(queries)
            else:
                q = f"SELECT * FROM table WHERE id = {random.randint(100, 200)}"
            cache.get(q)

        assert cache.hit_rate >= 0.90  # Should be close to 95%

    def test_cache_warmup(self):
        """Test cache warmup improves hit rate."""
        cache = QueryCache()

        # Warmup with common queries
        common_queries = [
            "SELECT COUNT(*) FROM users",
            "SELECT * FROM products LIMIT 10",
            "SELECT SUM(total) FROM orders",
        ]

        for q in common_queries:
            cache.set(q, "warmed result")

        # All warmed queries should hit
        hits = 0
        for q in common_queries:
            if cache.get(q):
                hits += 1

        assert hits == len(common_queries)


class TestIntegration:
    """Integration tests for cache and optimizer working together."""

    def test_optimizer_guided_caching(self):
        """Test using optimizer to guide caching decisions."""
        cache = QueryCache()
        optimizer = QueryOptimizer()

        query = "SELECT * FROM users WHERE status = 'active'"

        # Get cache recommendation
        suggestion = optimizer.suggest_cache_strategy(query)

        if suggestion.should_cache:
            cache.set(query, "result", ttl=suggestion.ttl_recommendation)
            result = cache.get(query)
            assert result == "result"

    def test_stats_export(self):
        """Test exporting comprehensive cache stats."""
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")

        stats = cache.get_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "size" in stats
        assert "evictions" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
