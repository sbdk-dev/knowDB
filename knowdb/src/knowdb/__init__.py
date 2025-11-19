"""
KnowDB - AI-powered semantic layer platform.

A unified platform combining semantic layer, AI intelligence,
memory systems, and MCP integration for business intelligence.

Note: CLI, Quality, and Pipeline modules are provided by sbdk-dev.
Import them from sbdk directly:
    from sbdk.quality import QualityFramework
    from sbdk.pipeline import IncrementalProcessor
"""

__version__ = "0.1.0"
__author__ = "KnowDB Team"

# Unique KnowDB modules
from .semantic_layer import SemanticLayerManager, SemanticLayerError
from .intelligence import IntelligenceEngine, StatisticalTester
from .optimization import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheMetrics,
    QueryCache,
    cached_query,
    ComplexityLevel,
    IndexSuggestion,
    OptimizationSuggestion,
    QueryComplexity,
    QueryOptimizer,
)

__all__ = [
    # Semantic Layer
    "SemanticLayerManager",
    "SemanticLayerError",
    # Intelligence
    "IntelligenceEngine",
    "StatisticalTester",
    # Optimization / Cache
    "CacheBackend",
    "CacheConfig",
    "CacheEntry",
    "CacheMetrics",
    "QueryCache",
    "cached_query",
    "ComplexityLevel",
    "IndexSuggestion",
    "OptimizationSuggestion",
    "QueryComplexity",
    "QueryOptimizer",
    # Version
    "__version__",
]
