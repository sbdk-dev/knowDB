"""
Semantic Layer MCP Tools for KnowDB.

Provides MCP tools that integrate with sbdk's existing infrastructure
while adding semantic layer, statistical testing, and dbt bridge capabilities.

Implements execution-first pattern: Build -> Execute -> Annotate
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SemanticTools:
    """
    MCP tools for KnowDB semantic layer.

    Integrates with sbdk tools and adds:
    - Semantic layer queries
    - Statistical testing
    - dbt model synchronization
    - Analysis suggestions
    """

    def __init__(
        self,
        semantic_manager=None,
        statistical_tester=None,
        dbt_bridge=None,
    ):
        """
        Initialize semantic tools.

        Args:
            semantic_manager: SemanticLayerManager instance
            statistical_tester: StatisticalTester instance
            dbt_bridge: DbtSemanticBridge instance
        """
        self.semantic_manager = semantic_manager
        self.statistical_tester = statistical_tester
        self.dbt_bridge = dbt_bridge

    def query_metric(
        self,
        metric_name: str,
        dimensions: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query semantic layer metric with execution-first pattern.

        Executes query FIRST, then annotates with statistics.
        This prevents fabrication by ensuring all insights are based on real data.

        Args:
            metric_name: Name of the metric to query
            dimensions: Optional list of dimensions to group by
            filters: Optional dict of filters to apply

        Returns:
            Dict containing:
                - result: Query results with data
                - statistics: Statistical analysis of results
                - metadata: Query metadata
        """
        # Validate input
        if not metric_name:
            return {
                "error": "Metric name is required",
                "message": "Please provide a valid metric name",
            }

        try:
            # 1. BUILD & EXECUTE: Get real data first (execution-first pattern)
            result = self.semantic_manager.query_metric(
                metric_name, dimensions, filters
            )

            # 2. ANNOTATE: Add statistical analysis based on real data
            statistics = {}
            if self.statistical_tester and result.get("data"):
                try:
                    statistics = self.statistical_tester.analyze(result)
                except Exception as e:
                    logger.warning(f"Statistical analysis failed: {e}")
                    statistics = {"error": str(e)}

            return {
                "result": result,
                "statistics": statistics,
                "metadata": {
                    "metric": metric_name,
                    "dimensions": dimensions or [],
                    "filters": filters or {},
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Query failed for metric '{metric_name}': {e}")
            return {
                "error": str(e),
                "message": f"Failed to query metric '{metric_name}'",
                "query_attempted": {
                    "metric": metric_name,
                    "dimensions": dimensions,
                    "filters": filters,
                },
            }

    def list_metrics(self) -> Dict[str, Any]:
        """
        List all available metrics.

        Returns:
            Dict containing:
                - metrics: List of metric definitions
                - total_count: Number of metrics
        """
        try:
            metrics = self.semantic_manager.list_metrics()

            return {
                "metrics": metrics,
                "total_count": len(metrics),
                "description": "Available semantic layer metrics",
            }

        except Exception as e:
            logger.error(f"Failed to list metrics: {e}")
            return {
                "error": str(e),
                "message": "Failed to retrieve available metrics",
            }

    def explain_metric(self, metric_name: str) -> Dict[str, Any]:
        """
        Get detailed explanation of how a metric is calculated.

        Args:
            metric_name: Name of the metric

        Returns:
            Dict containing:
                - explanation: Human-readable explanation
                - metric: Metric name
        """
        try:
            explanation = self.semantic_manager.explain_metric(metric_name)

            return {
                "metric": metric_name,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(f"Failed to explain metric '{metric_name}': {e}")
            return {
                "error": str(e),
                "message": f"Failed to explain metric '{metric_name}'",
            }

    def list_dimensions(self) -> Dict[str, Any]:
        """
        List all available dimensions.

        Returns:
            Dict containing:
                - dimensions: List of dimension definitions
                - total_count: Number of dimensions
        """
        try:
            dimensions = self.semantic_manager.list_dimensions()

            return {
                "dimensions": dimensions,
                "total_count": len(dimensions),
                "description": "Available dimensions for grouping and filtering",
            }

        except Exception as e:
            logger.error(f"Failed to list dimensions: {e}")
            return {
                "error": str(e),
                "message": "Failed to retrieve available dimensions",
            }

    def sync_from_dbt(self) -> Dict[str, Any]:
        """
        Synchronize dbt models to semantic layer.

        Imports dbt model definitions and creates corresponding
        semantic layer metrics and dimensions.

        Returns:
            Dict containing:
                - models_synced: Number of models synchronized
                - metrics_created: Number of metrics created
                - dimensions_created: Number of dimensions created
                - errors: Any errors encountered
        """
        if not self.dbt_bridge:
            return {
                "error": "dbt bridge not configured",
                "message": "No dbt bridge available for synchronization",
            }

        try:
            result = self.dbt_bridge.sync()

            return result

        except Exception as e:
            logger.error(f"dbt sync failed: {e}")
            return {
                "error": str(e),
                "message": "Failed to synchronize from dbt",
            }

    def get_dbt_models(self) -> Dict[str, Any]:
        """
        Get list of available dbt models.

        Returns:
            Dict containing:
                - models: List of dbt models
                - total_count: Number of models
        """
        if not self.dbt_bridge:
            return {
                "error": "dbt bridge not configured",
                "message": "No dbt bridge available",
            }

        try:
            models = self.dbt_bridge.get_dbt_models()

            return {
                "models": models,
                "total_count": len(models),
            }

        except Exception as e:
            logger.error(f"Failed to get dbt models: {e}")
            return {
                "error": str(e),
                "message": "Failed to retrieve dbt models",
            }

    def test_significance(
        self,
        data: Dict[str, Any],
        groups: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run statistical significance tests on data.

        Args:
            data: Query result data containing 'data' key with records
            groups: Dimension names for group comparison

        Returns:
            Dict containing:
                - p_value: Statistical p-value
                - is_significant: Whether difference is significant
                - interpretation: Human-readable interpretation
                - test_type: Type of statistical test used
        """
        if not self.statistical_tester:
            return {
                "error": "Statistical tester not configured",
                "message": "No statistical tester available",
            }

        try:
            result = self.statistical_tester.auto_test_comparison(data, groups or [])

            return {
                "test_type": result.get("test_type", "unknown"),
                "statistic": result.get("statistic"),
                "p_value": result.get("p_value"),
                "is_significant": result.get("is_significant", False),
                "effect_size": result.get("effect_size"),
                "interpretation": result.get("interpretation", ""),
            }

        except Exception as e:
            logger.error(f"Statistical testing failed: {e}")
            return {
                "error": str(e),
                "message": "Failed to run statistical significance test",
            }

    def suggest_analysis(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest next analysis steps based on current context.

        Args:
            context: Dict containing:
                - metric: Current metric being analyzed
                - dimensions: Current dimensions used
                - result: Current query result (optional)

        Returns:
            Dict containing:
                - suggestions: List of suggested next steps
        """
        if not context:
            context = {}

        suggestions = []

        # Generate suggestions based on context
        metric = context.get("metric")
        dimensions = context.get("dimensions", [])
        result = context.get("result")

        # Suggest adding dimensions if none used
        if not dimensions:
            suggestions.append({
                "question": f"How does {metric} break down by region?",
                "query": {
                    "metric": metric,
                    "dimensions": ["region"],
                },
                "rationale": "Add dimensions to understand distribution",
            })

        # Suggest trend analysis if not temporal
        if dimensions and not any(d in ["month", "quarter", "year"] for d in dimensions):
            suggestions.append({
                "question": f"What is the trend of {metric} over time?",
                "query": {
                    "metric": metric,
                    "dimensions": ["month"],
                },
                "rationale": "Analyze temporal trends",
            })

        # Suggest significance testing if groups present
        if dimensions and result:
            data = result.get("data", [])
            if len(data) > 1:
                suggestions.append({
                    "question": f"Are the differences in {metric} between {dimensions[0]} statistically significant?",
                    "action": "test_significance",
                    "rationale": "Validate observed differences",
                })

        # Suggest related metrics
        if metric:
            suggestions.append({
                "question": f"What other metrics are related to {metric}?",
                "action": "list_metrics",
                "rationale": "Explore related metrics",
            })

        return {
            "suggestions": suggestions,
            "context": context,
        }


def create_semantic_tools(
    semantic_manager=None,
    statistical_tester=None,
    dbt_bridge=None,
) -> SemanticTools:
    """
    Factory function to create SemanticTools instance.

    Args:
        semantic_manager: SemanticLayerManager instance
        statistical_tester: StatisticalTester instance
        dbt_bridge: DbtSemanticBridge instance

    Returns:
        Configured SemanticTools instance
    """
    return SemanticTools(
        semantic_manager=semantic_manager,
        statistical_tester=statistical_tester,
        dbt_bridge=dbt_bridge,
    )
