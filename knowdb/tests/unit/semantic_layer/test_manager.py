"""
Tests for SemanticLayerManager

TDD Red Phase: These tests define the expected behavior of the semantic layer.
Tests should fail initially until implementation is complete.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import types (to be implemented)
from knowdb.semantic_layer.types import (
    MetricDefinition,
    DimensionDefinition,
    ConnectionConfig,
    SemanticModelConfig,
    QueryResult,
    MetricType,
    DimensionType,
    AggregationType,
)

# Import manager (to be implemented)
from knowdb.semantic_layer.manager import SemanticLayerManager
from knowdb.semantic_layer.exceptions import SemanticLayerError


# Test fixtures
SAMPLE_CONFIG_YAML = """
semantic_model:
  name: "Test Model"
  version: "1.0"
  description: "Test semantic model for unit testing"

  connection:
    type: "duckdb"
    database: ":memory:"

  dimensions:
    - name: "customer_segment"
      display_name: "Customer Segment"
      description: "Customer tier"
      type: "categorical"
      table: "customers"
      column: "segment"

    - name: "signup_month"
      display_name: "Signup Month"
      description: "Month of signup"
      type: "temporal"
      table: "customers"
      column: "signup_date"
      sql: "strftime('%Y-%m', {{ Table }}.signup_date)"

  metrics:
    - name: "total_customers"
      display_name: "Total Customers"
      description: "Count of all customers"
      type: "simple"
      calculation:
        table: "customers"
        aggregation: "count"
        column: "customer_id"

    - name: "total_revenue"
      display_name: "Total Revenue"
      description: "Sum of all revenue"
      type: "simple"
      calculation:
        table: "orders"
        aggregation: "sum"
        column: "amount"

    - name: "arpu"
      display_name: "Average Revenue Per User"
      description: "Revenue divided by customers"
      type: "derived"
      calculation:
        formula: "total_revenue / total_customers"
"""


@pytest.fixture
def config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(SAMPLE_CONFIG_YAML)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def manager(config_file):
    """Create a SemanticLayerManager instance for testing."""
    return SemanticLayerManager(config_path=config_file)


class TestSemanticLayerManagerInit:
    """Tests for SemanticLayerManager initialization."""

    def test_init_with_valid_config(self, config_file):
        """Manager should initialize with valid config file."""
        manager = SemanticLayerManager(config_path=config_file)
        assert manager is not None
        assert manager.config is not None

    def test_init_with_missing_file(self):
        """Manager should raise error for missing config file."""
        with pytest.raises(SemanticLayerError) as excinfo:
            SemanticLayerManager(config_path="/nonexistent/path.yml")
        assert "not found" in str(excinfo.value).lower()

    def test_init_creates_connection(self, manager):
        """Manager should create database connection on init."""
        assert manager.connection is not None

    def test_init_loads_metrics(self, manager):
        """Manager should load metrics from config."""
        metrics = manager.list_metrics()
        assert len(metrics) == 3
        metric_names = [m["name"] for m in metrics]
        assert "total_customers" in metric_names
        assert "total_revenue" in metric_names
        assert "arpu" in metric_names

    def test_init_loads_dimensions(self, manager):
        """Manager should load dimensions from config."""
        dimensions = manager.list_dimensions()
        assert len(dimensions) == 2
        dim_names = [d["name"] for d in dimensions]
        assert "customer_segment" in dim_names
        assert "signup_month" in dim_names


class TestMetricOperations:
    """Tests for metric-related operations."""

    def test_list_metrics_returns_metadata(self, manager):
        """list_metrics should return metric metadata."""
        metrics = manager.list_metrics()

        # Check structure
        for metric in metrics:
            assert "name" in metric
            assert "display_name" in metric
            assert "description" in metric
            assert "type" in metric

    def test_get_metric_by_name(self, manager):
        """get_metric should return specific metric definition."""
        metric = manager.get_metric("total_customers")

        assert metric["name"] == "total_customers"
        assert metric["type"] == "simple"
        assert "calculation" in metric

    def test_get_metric_not_found(self, manager):
        """get_metric should raise error for unknown metric."""
        with pytest.raises(SemanticLayerError) as excinfo:
            manager.get_metric("nonexistent_metric")
        assert "not found" in str(excinfo.value).lower()

    def test_explain_metric_simple(self, manager):
        """explain_metric should return explanation for simple metric."""
        explanation = manager.explain_metric("total_customers")

        assert "Total Customers" in explanation
        assert "count" in explanation.lower()
        assert "customers" in explanation.lower()

    def test_explain_metric_derived(self, manager):
        """explain_metric should return explanation for derived metric."""
        explanation = manager.explain_metric("arpu")

        assert "Average Revenue Per User" in explanation
        assert "formula" in explanation.lower()


class TestDimensionOperations:
    """Tests for dimension-related operations."""

    def test_list_dimensions_returns_metadata(self, manager):
        """list_dimensions should return dimension metadata."""
        dimensions = manager.list_dimensions()

        for dim in dimensions:
            assert "name" in dim
            assert "type" in dim
            assert "description" in dim

    def test_get_dimension_by_name(self, manager):
        """get_dimension should return specific dimension."""
        dim = manager.get_dimension("customer_segment")

        assert dim is not None
        assert dim["name"] == "customer_segment"
        assert dim["type"] == "categorical"

    def test_get_dimension_not_found(self, manager):
        """get_dimension should return None for unknown dimension."""
        dim = manager.get_dimension("nonexistent_dimension")
        assert dim is None

    def test_temporal_dimension_has_sql(self, manager):
        """Temporal dimensions should have SQL expression."""
        dim = manager.get_dimension("signup_month")

        assert dim is not None
        assert dim["type"] == "temporal"
        assert "sql" in dim
        assert "strftime" in dim["sql"]


class TestQueryExecution:
    """Tests for query execution."""

    def test_query_metric_returns_result(self, manager):
        """query_metric should return QueryResult structure."""
        # This test will need a mock or actual data
        # For now, test the structure
        with patch.object(manager, '_query_simple_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (pd.DataFrame({"total_customers": [100]}), "SELECT COUNT(*)")

            result = manager.query_metric("total_customers")

            assert "metric" in result
            assert "data" in result
            assert "sql" in result
            assert "row_count" in result
            assert "timestamp" in result

    def test_query_metric_with_dimensions(self, manager):
        """query_metric should support dimensional grouping."""
        with patch.object(manager, '_query_simple_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (
                pd.DataFrame({
                    "customer_segment": ["SMB", "Enterprise"],
                    "total_customers": [50, 50]
                }),
                "SELECT segment, COUNT(*)"
            )

            result = manager.query_metric(
                "total_customers",
                dimensions=["customer_segment"]
            )

            assert result["dimensions"] == ["customer_segment"]
            assert len(result["data"]) == 2

    def test_query_metric_with_filters(self, manager):
        """query_metric should support filtering."""
        with patch.object(manager, '_query_simple_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (
                pd.DataFrame({"total_customers": [30]}),
                "SELECT COUNT(*) WHERE segment = 'SMB'"
            )

            result = manager.query_metric(
                "total_customers",
                filters=["customer_segment = 'SMB'"]
            )

            assert result["data"][0]["total_customers"] == 30

    def test_query_metric_with_limit(self, manager):
        """query_metric should support result limiting."""
        with patch.object(manager, '_query_simple_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (
                pd.DataFrame({
                    "customer_segment": ["A", "B", "C"],
                    "total_customers": [100, 90, 80]
                }),
                "SELECT * LIMIT 3"
            )

            result = manager.query_metric(
                "total_customers",
                dimensions=["customer_segment"],
                limit=3
            )

            assert result["row_count"] <= 3

    def test_query_metric_with_order_by(self, manager):
        """query_metric should support ordering."""
        with patch.object(manager, '_query_simple_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (
                pd.DataFrame({
                    "customer_segment": ["A", "B"],
                    "total_customers": [100, 50]
                }),
                "SELECT * ORDER BY count DESC"
            )

            result = manager.query_metric(
                "total_customers",
                dimensions=["customer_segment"],
                order_by="-total_customers"
            )

            # Result should be ordered
            assert result["data"][0]["total_customers"] >= result["data"][1]["total_customers"]


class TestDerivedMetrics:
    """Tests for derived metric calculation."""

    def test_query_derived_metric(self, manager):
        """Derived metrics should calculate from component metrics."""
        with patch.object(manager, '_query_derived_metric') as mock_query:
            import pandas as pd
            mock_query.return_value = (
                pd.DataFrame({"arpu": [50.0]}),
                "-- Derived metric"
            )

            result = manager.query_metric("arpu")

            assert "arpu" in result["data"][0]


class TestConnectionTypes:
    """Tests for different database connection types."""

    def test_duckdb_connection(self, config_file):
        """Manager should create DuckDB connection."""
        manager = SemanticLayerManager(config_path=config_file)
        assert manager.connection is not None

    def test_connection_close(self, manager):
        """Manager should close connection properly."""
        manager.close()
        # After closing, operations should fail or be unavailable


class TestEnvironmentVariables:
    """Tests for environment variable support."""

    def test_env_var_expansion(self):
        """Config should expand environment variables."""
        config_with_env = """
semantic_model:
  name: "Test"
  version: "1.0"
  description: "Test"

  connection:
    type: "duckdb"
    database: "${TEST_DB_PATH:memory:}"

  metrics: []
  dimensions: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_with_env)
            f.flush()

            # Should use default value when env var not set
            manager = SemanticLayerManager(config_path=f.name)
            assert manager is not None

            os.unlink(f.name)


class TestCaching:
    """Tests for query caching functionality."""

    def test_cache_initialization(self, manager):
        """Manager should initialize cache."""
        assert hasattr(manager, '_cache')

    def test_clear_cache(self, manager):
        """Manager should support cache clearing."""
        manager.clear_cache()
        assert len(manager._cache) == 0


class TestValidation:
    """Tests for configuration validation."""

    def test_invalid_yaml_raises_error(self):
        """Invalid YAML should raise SemanticLayerError."""
        invalid_yaml = "invalid: yaml: content:"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()

            with pytest.raises(SemanticLayerError):
                SemanticLayerManager(config_path=f.name)

            os.unlink(f.name)

    def test_missing_semantic_model_section(self):
        """Config without semantic_model section should raise error."""
        bad_config = """
name: "Missing section"
metrics: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(bad_config)
            f.flush()

            with pytest.raises(SemanticLayerError) as excinfo:
                SemanticLayerManager(config_path=f.name)

            assert "semantic_model" in str(excinfo.value).lower()
            os.unlink(f.name)

    def test_missing_required_fields(self):
        """Config missing required fields should raise error."""
        bad_config = """
semantic_model:
  name: "Test"
  # Missing connection, metrics
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(bad_config)
            f.flush()

            with pytest.raises(SemanticLayerError):
                SemanticLayerManager(config_path=f.name)

            os.unlink(f.name)


class TestPydanticTypes:
    """Tests for Pydantic type definitions."""

    def test_metric_definition_validation(self):
        """MetricDefinition should validate required fields."""
        # Valid metric
        metric = MetricDefinition(
            name="test_metric",
            display_name="Test Metric",
            type=MetricType.SIMPLE,
            calculation={
                "table": "test",
                "aggregation": "sum",
                "column": "value"
            }
        )
        assert metric.name == "test_metric"

    def test_metric_definition_invalid(self):
        """MetricDefinition should reject invalid data."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            MetricDefinition(
                name="",  # Empty name should fail
                type="invalid_type"  # Invalid enum
            )

    def test_dimension_definition_validation(self):
        """DimensionDefinition should validate required fields."""
        dim = DimensionDefinition(
            name="test_dim",
            type=DimensionType.CATEGORICAL,
            table="test_table",
            column="test_col"
        )
        assert dim.name == "test_dim"

    def test_connection_config_validation(self):
        """ConnectionConfig should validate database types."""
        config = ConnectionConfig(
            type="duckdb",
            database=":memory:"
        )
        assert config.type == "duckdb"

    def test_query_result_structure(self):
        """QueryResult should have expected structure."""
        from datetime import datetime

        result = QueryResult(
            metric="test",
            display_name="Test",
            description="",
            dimensions=[],
            data=[{"test": 1}],
            row_count=1,
            sql="SELECT 1",
            timestamp=datetime.now().isoformat()
        )
        assert result.row_count == 1


class TestAggregationTypes:
    """Tests for aggregation type support."""

    @pytest.mark.parametrize("agg_type", [
        "sum", "count", "count_distinct", "avg", "min", "max", "average", "mean"
    ])
    def test_aggregation_types_supported(self, agg_type):
        """Manager should support all standard aggregation types."""
        # This tests that AggregationType enum contains all expected values
        assert AggregationType(agg_type) is not None or hasattr(AggregationType, agg_type.upper())
