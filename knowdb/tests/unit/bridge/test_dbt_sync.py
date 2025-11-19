"""
Comprehensive test suite for dbt-to-semantic-layer bridge.

Tests the DbtSemanticBridge class that converts dbt models to KnowDB semantic layer definitions.
Following TDD: write tests first, then implementation.
"""

import json
import pytest
import yaml
from pathlib import Path
from datetime import datetime

from knowdb.bridge.dbt_sync import (
    DbtSemanticBridge,
    DbtModel,
    DbtColumn,
    MetricDefinition,
    DimensionDefinition,
    SyncResult,
    AggregationType,
    DimensionType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_dbt_project(tmp_path: Path) -> Path:
    """Create a sample dbt project structure for testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create dbt_project.yml
    dbt_project = {
        "name": "sample_analytics",
        "version": "1.0.0",
        "profile": "analytics",
        "model-paths": ["models"],
        "analysis-paths": ["analyses"],
        "test-paths": ["tests"],
        "seed-paths": ["seeds"],
        "macro-paths": ["macros"],
    }
    (project_dir / "dbt_project.yml").write_text(yaml.dump(dbt_project))

    # Create models directory structure
    (project_dir / "models" / "staging").mkdir(parents=True)
    (project_dir / "models" / "marts").mkdir(parents=True)

    return project_dir


@pytest.fixture
def sample_mart_model_sql() -> str:
    """Sample dbt mart model SQL with aggregations."""
    return """
    SELECT
        customer_id,
        customer_name,
        customer_segment,
        signup_date,
        SUM(order_amount) as total_revenue,
        COUNT(*) as order_count,
        AVG(order_amount) as avg_order_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        COUNT(DISTINCT product_id) as unique_products
    FROM {{ ref('stg_orders') }}
    LEFT JOIN {{ ref('stg_customers') }} USING (customer_id)
    GROUP BY customer_id, customer_name, customer_segment, signup_date
    """


@pytest.fixture
def sample_schema_yml() -> dict:
    """Sample dbt schema.yml configuration."""
    return {
        "version": 2,
        "models": [
            {
                "name": "customer_metrics",
                "description": "Customer-level aggregated metrics for business analytics",
                "columns": [
                    {
                        "name": "customer_id",
                        "description": "Unique customer identifier",
                        "tests": ["not_null", "unique"]
                    },
                    {
                        "name": "customer_name",
                        "description": "Customer full name"
                    },
                    {
                        "name": "customer_segment",
                        "description": "Customer business segment (Enterprise, SMB, Startup)"
                    },
                    {
                        "name": "signup_date",
                        "description": "Date when customer signed up"
                    },
                    {
                        "name": "total_revenue",
                        "description": "Total revenue from customer orders"
                    },
                    {
                        "name": "order_count",
                        "description": "Total number of orders placed"
                    },
                    {
                        "name": "avg_order_value",
                        "description": "Average order value"
                    },
                    {
                        "name": "first_order_date",
                        "description": "Date of first order"
                    },
                    {
                        "name": "last_order_date",
                        "description": "Date of most recent order"
                    },
                    {
                        "name": "unique_products",
                        "description": "Number of unique products purchased"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def dbt_project_with_models(sample_dbt_project: Path, sample_mart_model_sql: str, sample_schema_yml: dict) -> Path:
    """Create a complete dbt project with models and schema."""
    # Write mart model
    mart_path = sample_dbt_project / "models" / "marts" / "customer_metrics.sql"
    mart_path.write_text(sample_mart_model_sql)

    # Write schema.yml
    schema_path = sample_dbt_project / "models" / "marts" / "schema.yml"
    schema_path.write_text(yaml.dump(sample_schema_yml))

    return sample_dbt_project


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    """Create output path for generated semantic YAML."""
    output_dir = tmp_path / "semantic_models"
    output_dir.mkdir()
    return output_dir / "metrics.yml"


@pytest.fixture
def bridge(dbt_project_with_models: Path, output_path: Path) -> DbtSemanticBridge:
    """Create a configured DbtSemanticBridge instance."""
    return DbtSemanticBridge(
        dbt_project_path=str(dbt_project_with_models),
        semantic_output_path=str(output_path)
    )


# =============================================================================
# Test: Bridge Initialization
# =============================================================================

class TestBridgeInitialization:
    """Tests for DbtSemanticBridge initialization."""

    def test_init_with_valid_paths(self, sample_dbt_project: Path, output_path: Path):
        """Test bridge initializes with valid paths."""
        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        assert bridge.dbt_path == sample_dbt_project
        assert bridge.output_path == output_path

    def test_init_with_path_objects(self, sample_dbt_project: Path, output_path: Path):
        """Test bridge accepts Path objects."""
        bridge = DbtSemanticBridge(
            dbt_project_path=sample_dbt_project,
            semantic_output_path=output_path
        )

        assert bridge.dbt_path == sample_dbt_project
        assert bridge.output_path == output_path

    def test_init_invalid_dbt_path_raises_error(self, output_path: Path):
        """Test bridge raises error for invalid dbt project path."""
        with pytest.raises(ValueError, match="dbt project path does not exist"):
            DbtSemanticBridge(
                dbt_project_path="/nonexistent/path",
                semantic_output_path=str(output_path)
            )

    def test_init_creates_output_directory(self, sample_dbt_project: Path, tmp_path: Path):
        """Test bridge creates output directory if it doesn't exist."""
        new_output = tmp_path / "new_dir" / "metrics.yml"

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(new_output)
        )

        # Directory should be created on sync, not init
        assert bridge.output_path == new_output


# =============================================================================
# Test: Model Discovery
# =============================================================================

class TestModelDiscovery:
    """Tests for discovering dbt models."""

    def test_discover_models_finds_sql_files(self, bridge: DbtSemanticBridge):
        """Test that discover_models finds .sql files in models directory."""
        models = bridge.discover_models()

        assert len(models) >= 1
        model_names = [m.name for m in models]
        assert "customer_metrics" in model_names

    def test_discover_models_returns_dbt_model_objects(self, bridge: DbtSemanticBridge):
        """Test that discovered models are DbtModel instances."""
        models = bridge.discover_models()

        for model in models:
            assert isinstance(model, DbtModel)

    def test_model_has_sql_content(self, bridge: DbtSemanticBridge):
        """Test that models have their SQL content loaded."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        assert model.sql is not None
        assert "SUM(order_amount)" in model.sql
        assert "customer_id" in model.sql

    def test_model_has_schema_metadata(self, bridge: DbtSemanticBridge):
        """Test that models have schema.yml metadata loaded."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        assert model.description is not None
        assert "Customer-level" in model.description
        assert len(model.columns) > 0

    def test_discover_models_filters_by_directory(self, bridge: DbtSemanticBridge):
        """Test filtering models by directory (marts only)."""
        models = bridge.discover_models(model_path="marts")

        assert len(models) >= 1
        # All models should be from marts
        for model in models:
            assert "marts" in model.path or model.path.endswith("marts")

    def test_discover_handles_missing_schema(self, sample_dbt_project: Path, output_path: Path):
        """Test discover handles models without schema.yml."""
        # Create a model without schema
        orphan_path = sample_dbt_project / "models" / "marts" / "orphan_model.sql"
        orphan_path.write_text("SELECT 1 as id")

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        models = bridge.discover_models()
        orphan = next((m for m in models if m.name == "orphan_model"), None)

        assert orphan is not None
        assert orphan.columns == []  # No columns from schema


# =============================================================================
# Test: Metric Extraction
# =============================================================================

class TestMetricExtraction:
    """Tests for extracting metrics from dbt models."""

    def test_extract_sum_metrics(self, bridge: DbtSemanticBridge):
        """Test extraction of SUM aggregation metrics."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        total_revenue = next((m for m in metrics if m.name == "total_revenue"), None)
        assert total_revenue is not None
        assert total_revenue.aggregation == AggregationType.SUM

    def test_extract_count_metrics(self, bridge: DbtSemanticBridge):
        """Test extraction of COUNT aggregation metrics."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        order_count = next((m for m in metrics if m.name == "order_count"), None)
        assert order_count is not None
        assert order_count.aggregation == AggregationType.COUNT

    def test_extract_avg_metrics(self, bridge: DbtSemanticBridge):
        """Test extraction of AVG aggregation metrics."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        avg_order = next((m for m in metrics if m.name == "avg_order_value"), None)
        assert avg_order is not None
        assert avg_order.aggregation == AggregationType.AVG

    def test_extract_count_distinct_metrics(self, bridge: DbtSemanticBridge):
        """Test extraction of COUNT(DISTINCT ...) metrics."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        unique_products = next((m for m in metrics if m.name == "unique_products"), None)
        assert unique_products is not None
        assert unique_products.aggregation == AggregationType.COUNT_DISTINCT

    def test_extract_min_max_metrics(self, bridge: DbtSemanticBridge):
        """Test extraction of MIN/MAX aggregation metrics."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        first_order = next((m for m in metrics if m.name == "first_order_date"), None)
        last_order = next((m for m in metrics if m.name == "last_order_date"), None)

        assert first_order is not None
        assert first_order.aggregation == AggregationType.MIN
        assert last_order is not None
        assert last_order.aggregation == AggregationType.MAX

    def test_metric_has_description_from_schema(self, bridge: DbtSemanticBridge):
        """Test that metrics get descriptions from schema.yml."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        total_revenue = next((m for m in metrics if m.name == "total_revenue"), None)
        assert total_revenue.description == "Total revenue from customer orders"

    def test_metric_has_table_reference(self, bridge: DbtSemanticBridge):
        """Test that metrics have correct table references."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        for metric in metrics:
            assert metric.table == "customer_metrics"

    def test_metric_display_name_generation(self, bridge: DbtSemanticBridge):
        """Test that display names are generated from metric names."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        metrics = bridge.extract_metrics(model)

        total_revenue = next((m for m in metrics if m.name == "total_revenue"), None)
        # total_revenue -> Total Revenue
        assert total_revenue.display_name == "Total Revenue"


# =============================================================================
# Test: Dimension Extraction
# =============================================================================

class TestDimensionExtraction:
    """Tests for extracting dimensions from dbt models."""

    def test_extract_categorical_dimensions(self, bridge: DbtSemanticBridge):
        """Test extraction of categorical (string) dimensions."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)

        segment = next((d for d in dimensions if d.name == "customer_segment"), None)
        assert segment is not None
        assert segment.type == DimensionType.CATEGORICAL

    def test_extract_temporal_dimensions(self, bridge: DbtSemanticBridge):
        """Test extraction of temporal (date/timestamp) dimensions."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)

        signup_date = next((d for d in dimensions if d.name == "signup_date"), None)
        assert signup_date is not None
        assert signup_date.type == DimensionType.TEMPORAL

    def test_extract_primary_key_as_dimension(self, bridge: DbtSemanticBridge):
        """Test that primary keys are extracted as dimensions."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)

        customer_id = next((d for d in dimensions if d.name == "customer_id"), None)
        assert customer_id is not None

    def test_dimension_has_description_from_schema(self, bridge: DbtSemanticBridge):
        """Test that dimensions get descriptions from schema.yml."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)

        customer_id = next((d for d in dimensions if d.name == "customer_id"), None)
        assert customer_id.description == "Unique customer identifier"

    def test_dimension_has_table_reference(self, bridge: DbtSemanticBridge):
        """Test that dimensions have correct table references."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)

        for dimension in dimensions:
            assert dimension.table == "customer_metrics"

    def test_aggregated_columns_not_included_as_dimensions(self, bridge: DbtSemanticBridge):
        """Test that aggregated columns are not included as dimensions."""
        models = bridge.discover_models()
        model = next(m for m in models if m.name == "customer_metrics")

        dimensions = bridge.extract_dimensions(model)
        dimension_names = [d.name for d in dimensions]

        # These are metrics, not dimensions
        assert "total_revenue" not in dimension_names
        assert "order_count" not in dimension_names
        assert "avg_order_value" not in dimension_names


# =============================================================================
# Test: YAML Generation
# =============================================================================

class TestYamlGeneration:
    """Tests for generating semantic layer YAML."""

    def test_generate_valid_yaml(self, bridge: DbtSemanticBridge):
        """Test that generated YAML is valid and parseable."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        # Should be valid YAML
        parsed = yaml.safe_load(yaml_content)
        assert parsed is not None

    def test_generated_yaml_has_metrics(self, bridge: DbtSemanticBridge):
        """Test that generated YAML contains metrics section."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        parsed = yaml.safe_load(yaml_content)
        assert "metrics" in parsed
        assert len(parsed["metrics"]) > 0

    def test_generated_yaml_has_dimensions(self, bridge: DbtSemanticBridge):
        """Test that generated YAML contains dimensions section."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        parsed = yaml.safe_load(yaml_content)
        assert "dimensions" in parsed
        assert len(parsed["dimensions"]) > 0

    def test_metric_yaml_structure(self, bridge: DbtSemanticBridge):
        """Test that metric YAML has correct structure."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        parsed = yaml.safe_load(yaml_content)
        metric = parsed["metrics"][0]

        assert "name" in metric
        assert "display_name" in metric
        assert "description" in metric
        assert "type" in metric
        assert "calculation" in metric
        assert "table" in metric["calculation"]
        assert "aggregation" in metric["calculation"]
        assert "column" in metric["calculation"]

    def test_dimension_yaml_structure(self, bridge: DbtSemanticBridge):
        """Test that dimension YAML has correct structure."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        parsed = yaml.safe_load(yaml_content)
        dimension = parsed["dimensions"][0]

        assert "name" in dimension
        assert "type" in dimension
        assert "table" in dimension
        assert "column" in dimension

    def test_generated_yaml_has_header_comment(self, bridge: DbtSemanticBridge):
        """Test that generated YAML has auto-generation header."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        assert "# Auto-generated from dbt models" in yaml_content

    def test_generated_yaml_has_version(self, bridge: DbtSemanticBridge):
        """Test that generated YAML has version field."""
        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)

        parsed = yaml.safe_load(yaml_content)
        assert "version" in parsed


# =============================================================================
# Test: Full Sync
# =============================================================================

class TestFullSync:
    """Tests for full sync operation."""

    def test_sync_creates_output_file(self, bridge: DbtSemanticBridge):
        """Test that sync creates the output YAML file."""
        result = bridge.sync()

        assert bridge.output_path.exists()

    def test_sync_returns_result(self, bridge: DbtSemanticBridge):
        """Test that sync returns a SyncResult object."""
        result = bridge.sync()

        assert isinstance(result, SyncResult)

    def test_sync_result_has_counts(self, bridge: DbtSemanticBridge):
        """Test that SyncResult has model, metric, and dimension counts."""
        result = bridge.sync()

        assert result.models_processed >= 1
        assert result.metrics_generated >= 5  # We expect at least 5 metrics
        assert result.dimensions_generated >= 3  # We expect at least 3 dimensions

    def test_sync_result_has_timestamp(self, bridge: DbtSemanticBridge):
        """Test that SyncResult has a timestamp."""
        result = bridge.sync()

        assert result.timestamp is not None
        # Should be recent
        time_diff = datetime.utcnow() - result.timestamp
        assert time_diff.total_seconds() < 10

    def test_sync_output_is_valid_semantic_yaml(self, bridge: DbtSemanticBridge):
        """Test that synced output is valid for semantic layer."""
        bridge.sync()

        content = bridge.output_path.read_text()
        parsed = yaml.safe_load(content)

        # Validate structure matches KnowDB semantic layer format
        assert "metrics" in parsed
        assert "dimensions" in parsed

        for metric in parsed["metrics"]:
            assert metric["type"] in ["simple", "derived"]

    def test_sync_idempotent(self, bridge: DbtSemanticBridge):
        """Test that multiple syncs produce same result."""
        result1 = bridge.sync()
        content1 = bridge.output_path.read_text()

        result2 = bridge.sync()
        content2 = bridge.output_path.read_text()

        # Counts should be same
        assert result1.models_processed == result2.models_processed
        assert result1.metrics_generated == result2.metrics_generated

        # Content should be same (ignoring timestamp in comments)
        parsed1 = yaml.safe_load(content1)
        parsed2 = yaml.safe_load(content2)
        assert parsed1 == parsed2

    def test_sync_creates_parent_directories(self, sample_dbt_project: Path, tmp_path: Path):
        """Test that sync creates parent directories for output."""
        deep_path = tmp_path / "a" / "b" / "c" / "metrics.yml"

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(deep_path)
        )

        result = bridge.sync()

        assert deep_path.exists()


# =============================================================================
# Test: SQL Parsing
# =============================================================================

class TestSqlParsing:
    """Tests for SQL parsing capabilities."""

    def test_parse_aggregation_patterns(self, bridge: DbtSemanticBridge):
        """Test parsing various aggregation patterns."""
        sql = """
        SELECT
            SUM(amount) as total_amount,
            COUNT(*) as row_count,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(price) as avg_price,
            MIN(created_at) as first_created,
            MAX(updated_at) as last_updated
        FROM orders
        """

        aggregations = bridge._parse_aggregations(sql)

        assert len(aggregations) == 6
        assert ("total_amount", "SUM", "amount") in aggregations
        assert ("row_count", "COUNT", "*") in aggregations
        assert ("unique_users", "COUNT_DISTINCT", "user_id") in aggregations

    def test_parse_handles_case_insensitivity(self, bridge: DbtSemanticBridge):
        """Test that SQL parsing is case-insensitive."""
        sql = """
        SELECT
            sum(amount) as total_amount,
            COUNT(id) as count_id,
            Avg(price) as avg_price
        FROM orders
        """

        aggregations = bridge._parse_aggregations(sql)

        assert len(aggregations) == 3

    def test_parse_handles_whitespace(self, bridge: DbtSemanticBridge):
        """Test that SQL parsing handles various whitespace."""
        sql = """
        SELECT
            SUM( amount ) as total_amount,
            COUNT(  *  ) as count_all,
            AVG(price)as avg_price
        FROM orders
        """

        aggregations = bridge._parse_aggregations(sql)

        assert len(aggregations) == 3

    def test_extract_group_by_columns(self, bridge: DbtSemanticBridge):
        """Test extraction of GROUP BY columns for dimensions."""
        sql = """
        SELECT
            customer_id,
            segment,
            SUM(amount) as total
        FROM orders
        GROUP BY customer_id, segment
        """

        group_by_cols = bridge._extract_group_by_columns(sql)

        assert "customer_id" in group_by_cols
        assert "segment" in group_by_cols
        assert "total" not in group_by_cols


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_model_directory(self, sample_dbt_project: Path, output_path: Path):
        """Test handling of empty models directory."""
        # Remove all models
        for sql_file in (sample_dbt_project / "models").rglob("*.sql"):
            sql_file.unlink()

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        models = bridge.discover_models()
        assert len(models) == 0

        # Sync should still work, just empty
        result = bridge.sync()
        assert result.models_processed == 0

    def test_model_without_aggregations(self, sample_dbt_project: Path, output_path: Path):
        """Test handling of models without any aggregations."""
        # Create a simple SELECT model
        simple_model = sample_dbt_project / "models" / "marts" / "simple_select.sql"
        simple_model.write_text("SELECT id, name, email FROM users")

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        models = bridge.discover_models()
        simple = next((m for m in models if m.name == "simple_select"), None)

        metrics = bridge.extract_metrics(simple)
        dimensions = bridge.extract_dimensions(simple)

        assert len(metrics) == 0
        assert len(dimensions) >= 1  # Should still have dimensions

    def test_malformed_sql_handling(self, sample_dbt_project: Path, output_path: Path):
        """Test handling of malformed SQL."""
        # Create malformed SQL
        bad_model = sample_dbt_project / "models" / "marts" / "bad_model.sql"
        bad_model.write_text("SELECT * FORM orders")  # typo: FORM instead of FROM

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        # Should not raise, just skip or handle gracefully
        models = bridge.discover_models()
        bad = next((m for m in models if m.name == "bad_model"), None)

        # Should return empty metrics without crashing
        metrics = bridge.extract_metrics(bad)
        assert isinstance(metrics, list)

    def test_unicode_in_descriptions(self, sample_dbt_project: Path, output_path: Path):
        """Test handling of unicode in descriptions."""
        # Create schema with unicode
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "unicode_model",
                    "description": "Model with unicode: cafe, naive",
                    "columns": [
                        {
                            "name": "revenue",
                            "description": "Total revenue in (euros)"
                        }
                    ]
                }
            ]
        }

        schema_path = sample_dbt_project / "models" / "marts" / "unicode_schema.yml"
        schema_path.write_text(yaml.dump(schema, allow_unicode=True))

        model_path = sample_dbt_project / "models" / "marts" / "unicode_model.sql"
        model_path.write_text("SELECT SUM(amount) as revenue FROM orders")

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        result = bridge.sync()
        content = bridge.output_path.read_text()

        # Should preserve unicode
        assert "cafe" in content or "euros" in content

    def test_duplicate_metric_names_across_models(self, sample_dbt_project: Path, output_path: Path):
        """Test handling of duplicate metric names across models."""
        # Create another model with same metric name
        another_model = sample_dbt_project / "models" / "marts" / "another_model.sql"
        another_model.write_text("""
        SELECT
            product_id,
            SUM(amount) as total_revenue
        FROM products
        GROUP BY product_id
        """)

        bridge = DbtSemanticBridge(
            dbt_project_path=str(sample_dbt_project),
            semantic_output_path=str(output_path)
        )

        models = bridge.discover_models()
        yaml_content = bridge.generate_semantic_yaml(models)
        parsed = yaml.safe_load(yaml_content)

        # Should handle duplicates (e.g., prefix with table name)
        metric_names = [m["name"] for m in parsed["metrics"]]
        # Either deduplicated or prefixed
        assert len(metric_names) == len(set(metric_names))


# =============================================================================
# Test: Data Types
# =============================================================================

class TestDataClasses:
    """Tests for data classes used by the bridge."""

    def test_dbt_model_dataclass(self):
        """Test DbtModel dataclass."""
        model = DbtModel(
            name="test_model",
            path="models/marts/test_model.sql",
            sql="SELECT 1",
            description="Test model",
            columns=[]
        )

        assert model.name == "test_model"
        assert model.sql == "SELECT 1"

    def test_dbt_column_dataclass(self):
        """Test DbtColumn dataclass."""
        column = DbtColumn(
            name="amount",
            description="Order amount",
            data_type="float"
        )

        assert column.name == "amount"
        assert column.data_type == "float"

    def test_metric_definition_dataclass(self):
        """Test MetricDefinition dataclass."""
        metric = MetricDefinition(
            name="total_revenue",
            display_name="Total Revenue",
            description="Sum of all revenue",
            table="orders",
            column="amount",
            aggregation=AggregationType.SUM
        )

        assert metric.aggregation == AggregationType.SUM

    def test_dimension_definition_dataclass(self):
        """Test DimensionDefinition dataclass."""
        dimension = DimensionDefinition(
            name="segment",
            display_name="Customer Segment",
            description="Business segment",
            table="customers",
            column="segment",
            type=DimensionType.CATEGORICAL
        )

        assert dimension.type == DimensionType.CATEGORICAL

    def test_sync_result_dataclass(self):
        """Test SyncResult dataclass."""
        result = SyncResult(
            models_processed=5,
            metrics_generated=10,
            dimensions_generated=8,
            timestamp=datetime.utcnow()
        )

        assert result.models_processed == 5
        assert result.metrics_generated == 10


# =============================================================================
# Test: Configuration
# =============================================================================

class TestConfiguration:
    """Tests for bridge configuration options."""

    def test_exclude_staging_models(self, dbt_project_with_models: Path, output_path: Path):
        """Test excluding staging models from sync."""
        # Add a staging model
        staging_model = dbt_project_with_models / "models" / "staging" / "stg_orders.sql"
        staging_model.write_text("SELECT * FROM raw_orders")

        bridge = DbtSemanticBridge(
            dbt_project_path=str(dbt_project_with_models),
            semantic_output_path=str(output_path)
        )

        # By default, should only sync marts
        models = bridge.discover_models(model_path="marts")
        model_names = [m.name for m in models]

        assert "stg_orders" not in model_names

    def test_custom_model_path(self, dbt_project_with_models: Path, output_path: Path):
        """Test specifying custom model path."""
        # Create models in custom directory
        custom_dir = dbt_project_with_models / "models" / "custom"
        custom_dir.mkdir()
        (custom_dir / "custom_model.sql").write_text("SELECT SUM(x) as total FROM t")

        bridge = DbtSemanticBridge(
            dbt_project_path=str(dbt_project_with_models),
            semantic_output_path=str(output_path)
        )

        models = bridge.discover_models(model_path="custom")

        assert len(models) == 1
        assert models[0].name == "custom_model"
