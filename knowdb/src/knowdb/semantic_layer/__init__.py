"""
Semantic Layer Module

Provides a unified interface for querying metrics through a semantic layer.
"""

from .exceptions import (
    SemanticLayerError,
    ConfigurationError,
    ConnectionError,
    QueryError,
    MetricNotFoundError,
    DimensionNotFoundError,
    ValidationError,
)
from .manager import SemanticLayerManager
from .types import (
    MetricDefinition,
    DimensionDefinition,
    ConnectionConfig,
    SemanticModelConfig,
    QueryResult,
    MetricType,
    DimensionType,
    AggregationType,
    CanonicalDataset,
    MetricQueryRequest,
    ModelInfo,
    CacheEntry,
    ValidationResult,
)

__all__ = [
    # Manager
    "SemanticLayerManager",
    # Exceptions
    "SemanticLayerError",
    "ConfigurationError",
    "ConnectionError",
    "QueryError",
    "MetricNotFoundError",
    "DimensionNotFoundError",
    "ValidationError",
    # Types
    "MetricDefinition",
    "DimensionDefinition",
    "ConnectionConfig",
    "SemanticModelConfig",
    "QueryResult",
    "MetricType",
    "DimensionType",
    "AggregationType",
    "CanonicalDataset",
    "MetricQueryRequest",
    "ModelInfo",
    "CacheEntry",
    "ValidationResult",
]
