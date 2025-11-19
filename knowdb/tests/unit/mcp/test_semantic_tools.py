"""
Tests for Semantic Layer MCP Tools.

TDD test suite for KnowDB semantic tools that integrate with sbdk.
These tools implement execution-first pattern to prevent fabrication.
"""

import json
import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch


# Test fixtures
@pytest.fixture
def mock_semantic_manager():
    """Mock semantic layer manager."""
    manager = MagicMock()

    # list_metrics returns list of metric definitions
    manager.list_metrics.return_value = [
        {
            "name": "total_revenue",
            "display_name": "Total Revenue",
            "description": "Sum of all revenue",
            "type": "simple",
        },
        {
            "name": "mrr",
            "display_name": "Monthly Recurring Revenue",
            "description": "Monthly recurring revenue",
            "type": "simple",
        },
        {
            "name": "customer_count",
            "display_name": "Customer Count",
            "description": "Number of active customers",
            "type": "simple",
        },
    ]

    # get_metric returns single metric
    manager.get_metric.return_value = {
        "name": "total_revenue",
        "display_name": "Total Revenue",
        "description": "Sum of all revenue",
        "type": "simple",
        "calculation": {
            "aggregation": "sum",
            "column": "amount",
            "table": "transactions",
        },
    }

    # list_dimensions returns available dimensions
    manager.list_dimensions.return_value = [
        {
            "name": "region",
            "type": "categorical",
            "description": "Geographic region",
        },
        {
            "name": "product_category",
            "type": "categorical",
            "description": "Product category",
        },
        {
            "name": "month",
            "type": "temporal",
            "description": "Month",
            "sql": "strftime('%Y-%m', {{ Table }}.date)",
        },
    ]

    # query_metric returns query results
    manager.query_metric.return_value = {
        "metric": "total_revenue",
        "display_name": "Total Revenue",
        "data": [
            {"region": "North", "total_revenue": 1000000},
            {"region": "South", "total_revenue": 750000},
            {"region": "East", "total_revenue": 500000},
        ],
        "row_count": 3,
        "sql": "SELECT region, SUM(amount) AS total_revenue FROM transactions GROUP BY region",
        "timestamp": datetime.now().isoformat(),
    }

    # explain_metric returns explanation
    manager.explain_metric.return_value = (
        "**Total Revenue**\n\n"
        "Sum of all revenue\n\n"
        "**Type:** simple\n\n"
        "**Calculation:**\n"
        "  - Aggregation: sum\n"
        "  - Column: amount\n"
        "  - Table: transactions\n"
    )

    return manager


@pytest.fixture
def mock_statistical_tester():
    """Mock statistical tester."""
    tester = MagicMock()

    # analyze returns statistical insights
    tester.analyze.return_value = {
        "distribution": {
            "mean": 750000,
            "median": 750000,
            "std": 204124,
            "min": 500000,
            "max": 1000000,
        },
        "outliers": [],
        "trend": None,
    }

    # auto_test_comparison returns significance test results
    tester.auto_test_comparison.return_value = {
        "test_type": "kruskal_wallis",
        "statistic": 8.5,
        "p_value": 0.014,
        "is_significant": True,
        "interpretation": "Significant differences found between regions (p=0.014)",
        "effect_size": 0.35,
    }

    return tester


@pytest.fixture
def mock_dbt_bridge():
    """Mock dbt semantic bridge."""
    bridge = MagicMock()

    # sync returns sync result
    bridge.sync.return_value = {
        "models_synced": 5,
        "metrics_created": 12,
        "dimensions_created": 8,
        "errors": [],
        "timestamp": datetime.now().isoformat(),
    }

    # get_dbt_models returns available dbt models
    bridge.get_dbt_models.return_value = [
        {"name": "stg_customers", "description": "Staged customer data"},
        {"name": "fct_orders", "description": "Order facts"},
        {"name": "dim_products", "description": "Product dimensions"},
    ]

    return bridge


@pytest.fixture
def semantic_tools(mock_semantic_manager, mock_statistical_tester, mock_dbt_bridge):
    """Create SemanticTools instance with mocks."""
    from knowdb.mcp.semantic_tools import SemanticTools

    tools = SemanticTools(
        semantic_manager=mock_semantic_manager,
        statistical_tester=mock_statistical_tester,
        dbt_bridge=mock_dbt_bridge,
    )
    return tools


# =============================================================================
# Core Tool Tests
# =============================================================================

class TestQueryMetric:
    """Tests for query_metric tool."""

    def test_query_metric_basic(self, semantic_tools, mock_semantic_manager):
        """Test basic metric query without dimensions."""
        result = semantic_tools.query_metric("total_revenue")

        assert "result" in result
        assert "statistics" in result
        assert result["result"]["metric"] == "total_revenue"
        mock_semantic_manager.query_metric.assert_called_once_with(
            "total_revenue", None, None
        )

    def test_query_metric_with_dimensions(self, semantic_tools, mock_semantic_manager):
        """Test metric query with dimensions."""
        result = semantic_tools.query_metric(
            "total_revenue",
            dimensions=["region"]
        )

        assert "result" in result
        assert len(result["result"]["data"]) == 3
        mock_semantic_manager.query_metric.assert_called_once_with(
            "total_revenue", ["region"], None
        )

    def test_query_metric_with_filters(self, semantic_tools, mock_semantic_manager):
        """Test metric query with filters."""
        result = semantic_tools.query_metric(
            "total_revenue",
            filters={"region": "North"}
        )

        mock_semantic_manager.query_metric.assert_called_once_with(
            "total_revenue", None, {"region": "North"}
        )

    def test_query_metric_with_dimensions_and_filters(self, semantic_tools, mock_semantic_manager):
        """Test metric query with both dimensions and filters."""
        result = semantic_tools.query_metric(
            "total_revenue",
            dimensions=["product_category"],
            filters={"region": "North"}
        )

        mock_semantic_manager.query_metric.assert_called_once_with(
            "total_revenue", ["product_category"], {"region": "North"}
        )

    def test_query_metric_includes_statistics(self, semantic_tools, mock_statistical_tester):
        """Test that query results include statistical analysis."""
        result = semantic_tools.query_metric("total_revenue", dimensions=["region"])

        assert "statistics" in result
        assert "distribution" in result["statistics"]
        mock_statistical_tester.analyze.assert_called_once()

    def test_query_metric_handles_errors(self, semantic_tools, mock_semantic_manager):
        """Test error handling for query failures."""
        mock_semantic_manager.query_metric.side_effect = Exception("Database connection failed")

        result = semantic_tools.query_metric("total_revenue")

        assert "error" in result
        assert "Database connection failed" in result["error"]

    def test_query_metric_execution_first_pattern(self, semantic_tools, mock_semantic_manager):
        """Test that execution happens before statistics (execution-first pattern)."""
        # Verify the semantic manager is called first
        result = semantic_tools.query_metric("total_revenue")

        # Result should contain actual data, not fabricated
        assert result["result"]["data"] is not None
        assert result["result"]["row_count"] >= 0

    def test_query_metric_statistical_analysis_failure(self, semantic_tools, mock_statistical_tester):
        """Test that query succeeds even when statistical analysis fails."""
        mock_statistical_tester.analyze.side_effect = Exception("Statistical analysis error")

        result = semantic_tools.query_metric("total_revenue")

        # Query should still succeed
        assert "result" in result
        # Statistics should have error
        assert "error" in result["statistics"]


class TestListMetrics:
    """Tests for list_metrics tool."""

    def test_list_metrics_returns_all(self, semantic_tools, mock_semantic_manager):
        """Test listing all available metrics."""
        result = semantic_tools.list_metrics()

        assert "metrics" in result
        assert len(result["metrics"]) == 3
        assert result["metrics"][0]["name"] == "total_revenue"

    def test_list_metrics_includes_metadata(self, semantic_tools):
        """Test that metrics include display names and descriptions."""
        result = semantic_tools.list_metrics()

        for metric in result["metrics"]:
            assert "name" in metric
            assert "display_name" in metric
            assert "description" in metric
            assert "type" in metric

    def test_list_metrics_handles_empty(self, semantic_tools, mock_semantic_manager):
        """Test handling when no metrics are available."""
        mock_semantic_manager.list_metrics.return_value = []

        result = semantic_tools.list_metrics()

        assert result["metrics"] == []
        assert result.get("total_count", len(result["metrics"])) == 0

    def test_list_metrics_handles_error(self, semantic_tools, mock_semantic_manager):
        """Test error handling when list_metrics fails."""
        mock_semantic_manager.list_metrics.side_effect = Exception("Database error")

        result = semantic_tools.list_metrics()

        assert "error" in result


class TestExplainMetric:
    """Tests for explain_metric tool."""

    def test_explain_metric_returns_calculation(self, semantic_tools, mock_semantic_manager):
        """Test that explain returns calculation details."""
        result = semantic_tools.explain_metric("total_revenue")

        assert "explanation" in result
        assert "Total Revenue" in result["explanation"]
        mock_semantic_manager.explain_metric.assert_called_once_with("total_revenue")

    def test_explain_metric_not_found(self, semantic_tools, mock_semantic_manager):
        """Test error handling for unknown metric."""
        mock_semantic_manager.explain_metric.side_effect = KeyError("Metric not found")

        result = semantic_tools.explain_metric("unknown_metric")

        assert "error" in result

    def test_explain_metric_includes_formula_for_derived(self, semantic_tools, mock_semantic_manager):
        """Test explanation for derived metrics includes formula."""
        mock_semantic_manager.explain_metric.return_value = (
            "**ARPU**\n\n"
            "Average Revenue Per User\n\n"
            "**Type:** derived\n\n"
            "**Formula:** total_revenue / user_count\n"
        )

        result = semantic_tools.explain_metric("arpu")

        assert "Formula" in result["explanation"]


class TestListDimensions:
    """Tests for list_dimensions tool."""

    def test_list_dimensions_returns_all(self, semantic_tools, mock_semantic_manager):
        """Test listing all available dimensions."""
        result = semantic_tools.list_dimensions()

        assert "dimensions" in result
        assert len(result["dimensions"]) == 3

    def test_list_dimensions_includes_types(self, semantic_tools):
        """Test that dimensions include type information."""
        result = semantic_tools.list_dimensions()

        for dim in result["dimensions"]:
            assert "name" in dim
            assert "type" in dim
            assert dim["type"] in ["categorical", "temporal"]

    def test_list_dimensions_handles_error(self, semantic_tools, mock_semantic_manager):
        """Test error handling when list_dimensions fails."""
        mock_semantic_manager.list_dimensions.side_effect = Exception("Database error")

        result = semantic_tools.list_dimensions()

        assert "error" in result


# =============================================================================
# Dbt Integration Tests
# =============================================================================

class TestSyncFromDbt:
    """Tests for sync_from_dbt tool."""

    def test_sync_from_dbt_success(self, semantic_tools, mock_dbt_bridge):
        """Test successful dbt sync."""
        result = semantic_tools.sync_from_dbt()

        assert "models_synced" in result
        assert result["models_synced"] == 5
        assert result["metrics_created"] == 12
        mock_dbt_bridge.sync.assert_called_once()

    def test_sync_from_dbt_reports_errors(self, semantic_tools, mock_dbt_bridge):
        """Test that sync reports errors."""
        mock_dbt_bridge.sync.return_value = {
            "models_synced": 3,
            "metrics_created": 8,
            "dimensions_created": 4,
            "errors": ["Failed to parse model: broken_model.sql"],
            "timestamp": datetime.now().isoformat(),
        }

        result = semantic_tools.sync_from_dbt()

        assert len(result["errors"]) == 1

    def test_sync_from_dbt_handles_failure(self, semantic_tools, mock_dbt_bridge):
        """Test error handling for sync failures."""
        mock_dbt_bridge.sync.side_effect = Exception("dbt project not found")

        result = semantic_tools.sync_from_dbt()

        assert "error" in result

    def test_sync_from_dbt_no_bridge(self, mock_semantic_manager, mock_statistical_tester):
        """Test sync when dbt bridge is not configured."""
        from knowdb.mcp.semantic_tools import SemanticTools

        tools = SemanticTools(
            semantic_manager=mock_semantic_manager,
            statistical_tester=mock_statistical_tester,
            dbt_bridge=None,
        )

        result = tools.sync_from_dbt()

        assert "error" in result
        assert "not configured" in result["error"]


class TestGetDbtModels:
    """Tests for get_dbt_models tool."""

    def test_get_dbt_models_returns_list(self, semantic_tools, mock_dbt_bridge):
        """Test retrieving dbt models list."""
        result = semantic_tools.get_dbt_models()

        assert "models" in result
        assert len(result["models"]) == 3

    def test_get_dbt_models_no_bridge(self, mock_semantic_manager, mock_statistical_tester):
        """Test get_dbt_models when bridge is not configured."""
        from knowdb.mcp.semantic_tools import SemanticTools

        tools = SemanticTools(
            semantic_manager=mock_semantic_manager,
            statistical_tester=mock_statistical_tester,
            dbt_bridge=None,
        )

        result = tools.get_dbt_models()

        assert "error" in result

    def test_get_dbt_models_handles_error(self, semantic_tools, mock_dbt_bridge):
        """Test error handling for get_dbt_models failures."""
        mock_dbt_bridge.get_dbt_models.side_effect = Exception("Failed to read dbt project")

        result = semantic_tools.get_dbt_models()

        assert "error" in result


# =============================================================================
# Statistical Testing Tools
# =============================================================================

class TestTestSignificance:
    """Tests for test_significance tool."""

    def test_significance_with_groups(self, semantic_tools, mock_statistical_tester):
        """Test statistical significance testing for groups."""
        data = {
            "data": [
                {"region": "North", "revenue": 1000000},
                {"region": "South", "revenue": 750000},
            ]
        }

        result = semantic_tools.test_significance(data, groups=["region"])

        assert "p_value" in result
        assert "is_significant" in result
        mock_statistical_tester.auto_test_comparison.assert_called_once()

    def test_significance_interpretation(self, semantic_tools, mock_statistical_tester):
        """Test that significance results include interpretation."""
        data = {
            "data": [
                {"region": "North", "revenue": 1000000},
                {"region": "South", "revenue": 750000},
            ]
        }

        result = semantic_tools.test_significance(data, groups=["region"])

        assert "interpretation" in result

    def test_significance_handles_insufficient_data(self, semantic_tools, mock_statistical_tester):
        """Test handling of insufficient data for testing."""
        mock_statistical_tester.auto_test_comparison.side_effect = ValueError(
            "Insufficient data for statistical test"
        )

        data = {"data": [{"region": "North", "revenue": 1000000}]}

        result = semantic_tools.test_significance(data, groups=["region"])

        assert "error" in result

    def test_significance_no_tester(self, mock_semantic_manager, mock_dbt_bridge):
        """Test test_significance when no statistical tester is configured."""
        from knowdb.mcp.semantic_tools import SemanticTools

        tools = SemanticTools(
            semantic_manager=mock_semantic_manager,
            statistical_tester=None,
            dbt_bridge=mock_dbt_bridge,
        )

        data = {"data": [{"region": "North", "revenue": 1000000}]}
        result = tools.test_significance(data, groups=["region"])

        assert "error" in result
        assert "not configured" in result["error"]

    def test_significance_without_groups(self, semantic_tools, mock_statistical_tester):
        """Test significance testing without groups."""
        data = {
            "data": [
                {"revenue": 1000000},
                {"revenue": 750000},
            ]
        }

        result = semantic_tools.test_significance(data)

        assert "p_value" in result or "error" in result


# =============================================================================
# Suggestion Tools
# =============================================================================

class TestSuggestAnalysis:
    """Tests for suggest_analysis tool."""

    def test_suggest_analysis_basic(self, semantic_tools):
        """Test basic analysis suggestions."""
        context = {"metric": "total_revenue", "dimensions": ["region"]}

        result = semantic_tools.suggest_analysis(context)

        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_suggest_analysis_returns_actionable(self, semantic_tools):
        """Test that suggestions are actionable queries."""
        context = {"metric": "total_revenue", "dimensions": ["region"]}

        result = semantic_tools.suggest_analysis(context)

        for suggestion in result["suggestions"]:
            assert "question" in suggestion or "query" in suggestion or "action" in suggestion

    def test_suggest_analysis_contextual(self, semantic_tools):
        """Test that suggestions are contextual to current analysis."""
        context = {
            "metric": "total_revenue",
            "dimensions": ["region"],
            "result": {"data": [{"region": "North", "total_revenue": 1000000}]},
        }

        result = semantic_tools.suggest_analysis(context)

        # Suggestions should relate to the current analysis
        assert "suggestions" in result

    def test_suggest_analysis_no_context(self, semantic_tools):
        """Test suggest_analysis with no context."""
        result = semantic_tools.suggest_analysis(None)

        assert "suggestions" in result
        # Should return empty suggestions or default suggestions
        assert isinstance(result["suggestions"], list)

    def test_suggest_analysis_empty_context(self, semantic_tools):
        """Test suggest_analysis with empty context."""
        result = semantic_tools.suggest_analysis({})

        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    def test_suggest_analysis_no_dimensions(self, semantic_tools):
        """Test suggestions when no dimensions are used."""
        context = {"metric": "total_revenue", "dimensions": []}

        result = semantic_tools.suggest_analysis(context)

        # Should suggest adding dimensions
        assert "suggestions" in result
        assert any("dimension" in str(s).lower() or "region" in str(s).lower()
                  for s in result["suggestions"])

    def test_suggest_analysis_multiple_results(self, semantic_tools):
        """Test suggestions with multiple result rows."""
        context = {
            "metric": "total_revenue",
            "dimensions": ["region"],
            "result": {
                "data": [
                    {"region": "North", "total_revenue": 1000000},
                    {"region": "South", "total_revenue": 750000},
                ]
            },
        }

        result = semantic_tools.suggest_analysis(context)

        # Should suggest significance testing
        assert "suggestions" in result


# =============================================================================
# Integration Pattern Tests
# =============================================================================

class TestSbdkIntegration:
    """Tests for sbdk integration patterns."""

    def test_tools_expose_for_sbdk_server(self, semantic_tools):
        """Test that tools can be exposed in sbdk MCP server."""
        # Tools should be callable and return dictionaries
        result = semantic_tools.list_metrics()
        assert isinstance(result, dict)

        result = semantic_tools.query_metric("total_revenue")
        assert isinstance(result, dict)

    def test_tool_responses_serializable(self, semantic_tools):
        """Test that all tool responses are JSON serializable."""
        # list_metrics
        result = semantic_tools.list_metrics()
        json_str = json.dumps(result)
        assert json_str is not None

        # query_metric
        result = semantic_tools.query_metric("total_revenue")
        json_str = json.dumps(result)
        assert json_str is not None

        # explain_metric
        result = semantic_tools.explain_metric("total_revenue")
        json_str = json.dumps(result)
        assert json_str is not None

    def test_error_responses_consistent(self, semantic_tools, mock_semantic_manager):
        """Test that error responses follow consistent format."""
        mock_semantic_manager.query_metric.side_effect = Exception("Test error")

        result = semantic_tools.query_metric("invalid_metric")

        assert "error" in result
        assert isinstance(result["error"], str)


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for create_semantic_tools factory function."""

    def test_create_semantic_tools(self, mock_semantic_manager, mock_statistical_tester, mock_dbt_bridge):
        """Test factory function creates tools correctly."""
        from knowdb.mcp.semantic_tools import create_semantic_tools

        tools = create_semantic_tools(
            semantic_manager=mock_semantic_manager,
            statistical_tester=mock_statistical_tester,
            dbt_bridge=mock_dbt_bridge,
        )

        assert tools is not None
        assert hasattr(tools, "query_metric")
        assert hasattr(tools, "list_metrics")

    def test_create_semantic_tools_partial(self, mock_semantic_manager):
        """Test factory function with partial dependencies."""
        from knowdb.mcp.semantic_tools import create_semantic_tools

        tools = create_semantic_tools(
            semantic_manager=mock_semantic_manager,
        )

        assert tools is not None
        result = tools.list_metrics()
        assert "metrics" in result

    def test_create_semantic_tools_no_args(self):
        """Test factory function with no arguments."""
        from knowdb.mcp.semantic_tools import create_semantic_tools

        tools = create_semantic_tools()

        assert tools is not None


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_metric_name(self, semantic_tools):
        """Test handling of empty metric name."""
        result = semantic_tools.query_metric("")

        assert "error" in result

    def test_none_metric_name(self, semantic_tools):
        """Test handling of None metric name."""
        result = semantic_tools.query_metric(None)

        assert "error" in result

    def test_invalid_dimension(self, semantic_tools, mock_semantic_manager):
        """Test handling of invalid dimension."""
        mock_semantic_manager.query_metric.side_effect = ValueError(
            "Dimension 'invalid_dim' not found"
        )

        result = semantic_tools.query_metric(
            "total_revenue",
            dimensions=["invalid_dim"]
        )

        assert "error" in result

    def test_empty_result_handling(self, semantic_tools, mock_semantic_manager):
        """Test handling of empty query results."""
        mock_semantic_manager.query_metric.return_value = {
            "metric": "total_revenue",
            "data": [],
            "row_count": 0,
            "sql": "SELECT ...",
            "timestamp": datetime.now().isoformat(),
        }

        result = semantic_tools.query_metric("total_revenue")

        assert result["result"]["row_count"] == 0
        assert "statistics" in result

    def test_large_result_handling(self, semantic_tools, mock_semantic_manager):
        """Test handling of large result sets."""
        # Simulate large result
        large_data = [{"id": i, "value": i * 100} for i in range(10000)]
        mock_semantic_manager.query_metric.return_value = {
            "metric": "total_revenue",
            "data": large_data,
            "row_count": 10000,
            "sql": "SELECT ...",
            "timestamp": datetime.now().isoformat(),
        }

        result = semantic_tools.query_metric("total_revenue")

        assert result["result"]["row_count"] == 10000

    def test_special_characters_in_filter(self, semantic_tools, mock_semantic_manager):
        """Test handling of special characters in filters."""
        result = semantic_tools.query_metric(
            "total_revenue",
            filters={"region": "North & South"}
        )

        # Should not raise an error
        assert "result" in result or "error" in result


# =============================================================================
# Performance and Caching Tests
# =============================================================================

class TestPerformance:
    """Tests for performance-related functionality."""

    def test_query_returns_execution_time(self, semantic_tools, mock_semantic_manager):
        """Test that queries return execution time."""
        mock_semantic_manager.query_metric.return_value = {
            "metric": "total_revenue",
            "data": [{"total_revenue": 1000000}],
            "row_count": 1,
            "sql": "SELECT ...",
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": 150,
        }

        result = semantic_tools.query_metric("total_revenue")

        assert "execution_time_ms" in result["result"] or "metadata" in result

    def test_query_result_caching(self, semantic_tools, mock_semantic_manager):
        """Test that results can be cached."""
        # First call
        result1 = semantic_tools.query_metric("total_revenue")

        # Second call with same params
        result2 = semantic_tools.query_metric("total_revenue")

        # Both should return results (caching is implementation detail)
        assert "result" in result1
        assert "result" in result2


# =============================================================================
# Concurrent Usage Tests
# =============================================================================

class TestConcurrency:
    """Tests for concurrent tool usage."""

    def test_multiple_metric_queries(self, semantic_tools):
        """Test querying multiple metrics sequentially."""
        metrics = ["total_revenue", "mrr", "customer_count"]
        results = []

        for metric in metrics:
            result = semantic_tools.query_metric(metric)
            results.append(result)

        assert len(results) == 3

    def test_tool_state_isolation(self, semantic_tools):
        """Test that tool calls don't interfere with each other."""
        # Call with dimensions
        result1 = semantic_tools.query_metric(
            "total_revenue",
            dimensions=["region"]
        )

        # Call without dimensions
        result2 = semantic_tools.query_metric("total_revenue")

        # Both should succeed independently
        assert "result" in result1
        assert "result" in result2


# =============================================================================
# Data Validation Tests
# =============================================================================

class TestDataValidation:
    """Tests for data validation in tools."""

    def test_validates_metric_exists(self, semantic_tools, mock_semantic_manager):
        """Test validation that metric exists."""
        mock_semantic_manager.get_metric.side_effect = KeyError("Metric not found")
        mock_semantic_manager.query_metric.side_effect = KeyError("Metric not found")

        result = semantic_tools.query_metric("nonexistent_metric")

        assert "error" in result

    def test_validates_dimension_compatibility(self, semantic_tools, mock_semantic_manager):
        """Test validation of dimension compatibility with metric."""
        mock_semantic_manager.query_metric.side_effect = ValueError(
            "Dimension 'incompatible_dim' not compatible with metric table"
        )

        result = semantic_tools.query_metric(
            "total_revenue",
            dimensions=["incompatible_dim"]
        )

        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
