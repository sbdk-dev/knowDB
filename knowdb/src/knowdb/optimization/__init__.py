"""
KnowDB Optimization Module

Production-ready query caching and optimization tools.

Features:
- LRU cache with TTL support
- Thread-safe operations
- Query complexity analysis
- Cache recommendations
- Index suggestions

Target: 95%+ cache hit rate for production workloads.
"""

from knowdb.optimization.cache import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheMetrics,
    QueryCache,
    cached_query,
)
from knowdb.optimization.optimizer import (
    ComplexityLevel,
    IndexSuggestion,
    OptimizationSuggestion,
    QueryComplexity,
    QueryOptimizer,
)

__all__ = [
    # Cache
    "CacheBackend",
    "CacheConfig",
    "CacheEntry",
    "CacheMetrics",
    "QueryCache",
    "cached_query",
    # Optimizer
    "ComplexityLevel",
    "IndexSuggestion",
    "OptimizationSuggestion",
    "QueryComplexity",
    "QueryOptimizer",
]
