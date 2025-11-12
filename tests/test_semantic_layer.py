#!/usr/bin/env python3
"""
Test suite for the semantic layer

Tests metric definitions, querying, dimensions, and error handling
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_layer import SemanticLayer, SemanticLayerError


@pytest.fixture
def semantic_layer():
    """Create semantic layer instance for testing"""
    config_path = "semantic_models/metrics.yml"
    return SemanticLayer(config_path)


class TestInitialization:
    """Test semantic layer initialization"""

    def test_initialization_success(self, semantic_layer):
        """Test successful initialization"""
        assert semantic_layer is not None
        assert semantic_layer.config is not None
        assert semantic_layer.connection is not None

    def test_initialization_missing_file(self):
        """Test initialization with missing config file"""
        with pytest.raises(SemanticLayerError, match="Configuration file not found"):
            SemanticLayer("nonexistent.yml")

    def test_config_structure(self, semantic_layer):
        """Test configuration has required structure"""
        config = semantic_layer.config
        assert "semantic_model" in config
        model = config["semantic_model"]
        assert "name" in model
        assert "connection" in model
        assert "metrics" in model


class TestMetrics:
    """Test metric operations"""

    def test_list_metrics(self, semantic_layer):
        """Test listing all metrics"""
        metrics = semantic_layer.list_metrics()
        assert len(metrics) > 0

        # Check structure
        for metric in metrics:
            assert "name" in metric
            assert "display_name" in metric
            assert "type" in metric

    def test_get_metric(self, semantic_layer):
        """Test getting a specific metric"""
        metric = semantic_layer.get_metric("total_mrr")
        assert metric is not None
        assert metric["name"] == "total_mrr"
        assert "calculation" in metric

    def test_get_nonexistent_metric(self, semantic_layer):
        """Test getting a metric that doesn't exist"""
        with pytest.raises(SemanticLayerError, match="Metric .* not found"):
            semantic_layer.get_metric("nonexistent_metric")

    def test_explain_metric(self, semantic_layer):
        """Test metric explanation"""
        explanation = semantic_layer.explain_metric("total_mrr")
        assert explanation is not None
        assert "Monthly Recurring Revenue" in explanation
        assert "Calculation" in explanation


class TestDimensions:
    """Test dimension operations"""

    def test_list_dimensions(self, semantic_layer):
        """Test listing all dimensions"""
        dimensions = semantic_layer.list_dimensions()
        assert len(dimensions) > 0

        # Check structure
        for dim in dimensions:
            assert "name" in dim
            assert "type" in dim

    def test_get_dimension(self, semantic_layer):
        """Test getting a specific dimension"""
        dim = semantic_layer.get_dimension("customer_segment")
        assert dim is not None
        assert dim["name"] == "customer_segment"

    def test_get_nonexistent_dimension(self, semantic_layer):
        """Test getting a dimension that doesn't exist"""
        dim = semantic_layer.get_dimension("nonexistent_dimension")
        assert dim is None


class TestQueries:
    """Test metric querying"""

    def test_query_simple_metric(self, semantic_layer):
        """Test querying a simple metric"""
        result = semantic_layer.query_metric("total_customers")

        assert result is not None
        assert result["metric"] == "total_customers"
        assert "data" in result
        assert "row_count" in result
        assert "sql" in result
        assert isinstance(result["data"], list)

    def test_query_with_dimension(self, semantic_layer):
        """Test querying with a dimension"""
        result = semantic_layer.query_metric("total_mrr", dimensions=["customer_segment"])

        assert result is not None
        assert result["dimensions"] == ["customer_segment"]
        assert result["row_count"] > 0

        # Check that results include dimension
        if result["data"]:
            assert "customer_segment" in result["data"][0]

    def test_query_with_multiple_dimensions(self, semantic_layer):
        """Test querying with multiple dimensions"""
        result = semantic_layer.query_metric(
            "active_subscriptions", dimensions=["customer_segment", "product_tier"]
        )

        assert result is not None
        assert len(result["dimensions"]) == 2

    def test_query_with_limit(self, semantic_layer):
        """Test querying with limit"""
        result = semantic_layer.query_metric("total_mrr", dimensions=["customer_segment"], limit=2)

        assert result is not None
        assert result["row_count"] <= 2

    def test_query_with_order_by(self, semantic_layer):
        """Test querying with ordering"""
        result = semantic_layer.query_metric(
            "total_mrr", dimensions=["customer_segment"], order_by="-total_mrr"  # Descending
        )

        assert result is not None
        assert result["row_count"] > 0

    def test_query_nonexistent_metric(self, semantic_layer):
        """Test querying a metric that doesn't exist"""
        with pytest.raises(SemanticLayerError):
            semantic_layer.query_metric("nonexistent_metric")

    def test_query_aggregation_types(self, semantic_layer):
        """Test different aggregation types"""
        # Test sum
        result_sum = semantic_layer.query_metric("total_mrr")
        assert result_sum is not None

        # Test count
        result_count = semantic_layer.query_metric("total_customers")
        assert result_count is not None

        # Test count_distinct
        result_distinct = semantic_layer.query_metric("active_customers")
        assert result_distinct is not None

        # Test avg
        result_avg = semantic_layer.query_metric("average_subscription_value")
        assert result_avg is not None


class TestConnection:
    """Test database connection"""

    def test_duckdb_connection(self, semantic_layer):
        """Test DuckDB connection works"""
        # Query raw table to verify connection
        table = semantic_layer.connection.table("customers")
        assert table is not None

        # Execute simple query
        result = table.count().execute()
        assert result > 0

    def test_table_access(self, semantic_layer):
        """Test accessing all required tables"""
        tables = ["customers", "subscriptions", "monthly_mrr_snapshots"]

        for table_name in tables:
            table = semantic_layer.connection.table(table_name)
            assert table is not None
            count = table.count().execute()
            assert count > 0


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_dimension(self, semantic_layer):
        """Test querying with invalid dimension"""
        with pytest.raises(SemanticLayerError):
            semantic_layer.query_metric("total_mrr", dimensions=["nonexistent_dimension"])

    def test_empty_results(self, semantic_layer):
        """Test handling empty results"""
        # Query with filter that returns no results
        # Use a filter on a column that exists in the subscriptions table
        result = semantic_layer.query_metric(
            "total_mrr", filters=["subscription_status = 'nonexistent_status'"]
        )

        # Should not raise error, just return empty results
        assert result is not None
        assert result["row_count"] == 0


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_metric_discovery_workflow(self, semantic_layer):
        """Test discovering and querying metrics"""
        # 1. List all metrics
        metrics = semantic_layer.list_metrics()
        assert len(metrics) > 0

        # 2. Pick first metric
        metric_name = metrics[0]["name"]

        # 3. Explain metric
        explanation = semantic_layer.explain_metric(metric_name)
        assert explanation is not None

        # 4. Query metric
        result = semantic_layer.query_metric(metric_name)
        assert result is not None

    def test_dimensional_analysis_workflow(self, semantic_layer):
        """Test dimensional analysis workflow"""
        # 1. List dimensions
        dimensions = semantic_layer.list_dimensions()
        assert len(dimensions) > 0

        # 2. Query metric by dimension
        result = semantic_layer.query_metric("total_mrr", dimensions=["customer_segment"])
        assert result is not None
        assert result["row_count"] > 0

    def test_revenue_analysis_workflow(self, semantic_layer):
        """Test complete revenue analysis"""
        # Get MRR
        mrr_result = semantic_layer.query_metric("total_mrr")
        assert mrr_result is not None

        # Get MRR by segment
        mrr_by_segment = semantic_layer.query_metric(
            "total_mrr", dimensions=["customer_segment"], order_by="-total_mrr"
        )
        assert mrr_by_segment is not None
        assert mrr_by_segment["row_count"] > 0

        # Get customer count
        customer_result = semantic_layer.query_metric("active_customers")
        assert customer_result is not None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
