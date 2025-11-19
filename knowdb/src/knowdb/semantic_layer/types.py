"""
Pydantic types for semantic layer models.

Provides type-safe definitions for metrics, dimensions, connections,
and query results with validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class MetricType(str, Enum):
    """Types of metrics supported."""
    SIMPLE = "simple"
    DERIVED = "derived"


class DimensionType(str, Enum):
    """Types of dimensions supported."""
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"


class AggregationType(str, Enum):
    """Supported aggregation types for simple metrics."""
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVG = "avg"
    AVERAGE = "average"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"


class CalculationConfig(BaseModel):
    """Configuration for metric calculation."""
    table: Optional[str] = None
    aggregation: Optional[str] = None
    column: Optional[str] = None
    formula: Optional[str] = None
    filters: Optional[List[str]] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    """Definition of a semantic layer metric."""
    name: str = Field(..., min_length=1, description="Unique metric identifier")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field("", description="Metric description")
    type: MetricType = Field(..., description="Metric type (simple or derived)")
    calculation: Dict[str, Any] = Field(..., description="Calculation configuration")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate metric name is not empty."""
        if not v or not v.strip():
            raise ValueError("Metric name cannot be empty")
        return v.strip()

    @property
    def effective_display_name(self) -> str:
        """Get display name, falling back to name if not set."""
        return self.display_name or self.name


class DimensionDefinition(BaseModel):
    """Definition of a semantic layer dimension."""
    name: str = Field(..., min_length=1, description="Unique dimension identifier")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field("", description="Dimension description")
    type: DimensionType = Field(DimensionType.CATEGORICAL, description="Dimension type")
    table: Optional[str] = Field(None, description="Source table name")
    column: Optional[str] = Field(None, description="Source column name")
    sql: Optional[str] = Field(None, description="SQL expression for computed dimensions")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dimension name is not empty."""
        if not v or not v.strip():
            raise ValueError("Dimension name cannot be empty")
        return v.strip()

    @property
    def effective_display_name(self) -> str:
        """Get display name, falling back to name if not set."""
        return self.display_name or self.name


class ConnectionConfig(BaseModel):
    """Database connection configuration."""
    type: str = Field(..., description="Database type (duckdb, snowflake, bigquery, postgres)")
    database: Optional[str] = Field(None, description="Database name or path")
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    user: Optional[str] = Field(None, description="Database user")
    password: Optional[str] = Field(None, description="Database password")
    account: Optional[str] = Field(None, description="Account (Snowflake)")
    warehouse: Optional[str] = Field(None, description="Warehouse (Snowflake)")
    schema_name: Optional[str] = Field(None, alias="schema", description="Schema name")
    project_id: Optional[str] = Field(None, description="Project ID (BigQuery)")
    dataset_id: Optional[str] = Field(None, description="Dataset ID (BigQuery)")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate database type."""
        valid_types = {'duckdb', 'snowflake', 'bigquery', 'postgres', 'postgresql'}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid database type: {v}. Must be one of {valid_types}")
        return v.lower()


class CanonicalDataset(BaseModel):
    """Pre-defined dataset configuration for common analyses."""
    name: str = Field(..., description="Dataset name")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field("", description="Dataset description")
    metrics: List[str] = Field(default_factory=list, description="List of metric names")
    dimensions: List[str] = Field(default_factory=list, description="List of dimension names")
    time_dimension: Optional[str] = Field(None, description="Time dimension for time-series")
    refresh_schedule: Optional[str] = Field(None, description="Refresh schedule")


class SemanticModelConfig(BaseModel):
    """Complete semantic model configuration."""
    name: str = Field(..., description="Model name")
    version: Optional[str] = Field("1.0", description="Model version")
    description: Optional[str] = Field("", description="Model description")
    connection: ConnectionConfig = Field(..., description="Database connection config")
    metrics: List[Dict[str, Any]] = Field(default_factory=list, description="Metric definitions")
    dimensions: List[Dict[str, Any]] = Field(default_factory=list, description="Dimension definitions")
    canonical_datasets: List[Dict[str, Any]] = Field(default_factory=list, description="Canonical datasets")


class QueryResult(BaseModel):
    """Result of a metric query."""
    metric: str = Field(..., description="Metric name that was queried")
    display_name: str = Field(..., description="Human-readable metric name")
    description: str = Field("", description="Metric description")
    dimensions: List[str] = Field(default_factory=list, description="Dimensions used in query")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    row_count: int = Field(0, description="Number of rows returned")
    sql: str = Field("", description="Generated SQL query")
    timestamp: str = Field(..., description="Query execution timestamp")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is ISO format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")
        return v


class MetricQueryRequest(BaseModel):
    """Request parameters for querying a metric."""
    metric_name: str = Field(..., description="Name of metric to query")
    dimensions: Optional[List[str]] = Field(None, description="Dimensions to group by")
    filters: Optional[List[str]] = Field(None, description="SQL WHERE conditions")
    limit: Optional[int] = Field(None, ge=1, description="Maximum rows to return")
    order_by: Optional[str] = Field(None, description="Column to sort by (prefix with - for desc)")


class ModelInfo(BaseModel):
    """Summary information about a semantic model."""
    name: str
    description: str
    dimensions: List[str]
    measures: List[str]
    relationships: List[str] = Field(default_factory=list)


class CacheEntry(BaseModel):
    """Cache entry for query results."""
    key: str
    result: Dict[str, Any]
    created_at: datetime
    ttl_seconds: int = 300


class ValidationResult(BaseModel):
    """Result of query validation."""
    valid: bool
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    complexity_score: float = 0.0
    estimated_rows: int = 0
