"""
Exceptions for the semantic layer module.
"""


class SemanticLayerError(Exception):
    """Base exception for semantic layer errors."""
    pass


class ConfigurationError(SemanticLayerError):
    """Error in configuration loading or validation."""
    pass


class ConnectionError(SemanticLayerError):
    """Error establishing database connection."""
    pass


class QueryError(SemanticLayerError):
    """Error executing a query."""
    pass


class MetricNotFoundError(SemanticLayerError):
    """Requested metric not found."""
    pass


class DimensionNotFoundError(SemanticLayerError):
    """Requested dimension not found."""
    pass


class ValidationError(SemanticLayerError):
    """Query validation failed."""
    pass
