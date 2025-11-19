"""
Semantic Layer Manager

Provides a unified interface for querying metrics through a semantic layer.
Combines the best patterns from knowDB and claude-analyst implementations.

Features:
- YAML model loading with validation
- Multi-database support (DuckDB primary, Snowflake, BigQuery, PostgreSQL)
- Query building with Ibis
- Metric/dimension definitions with temporal support
- Cache integration hooks
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import ibis
import yaml

from .exceptions import SemanticLayerError
from .types import (
    AggregationType,
    DimensionType,
    MetricType,
)

logger = logging.getLogger(__name__)


class SemanticLayerManager:
    """
    Semantic Layer Manager that provides a business-friendly interface to query metrics.

    Combines patterns from:
    - knowDB: Temporal dimensions, derived metrics, filter parsing
    - claude-analyst: Model discovery, caching, async patterns
    """

    def __init__(self, config_path: str):
        """
        Initialize semantic layer manager with configuration.

        Args:
            config_path: Path to semantic models YAML file

        Raises:
            SemanticLayerError: If configuration file not found or invalid
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise SemanticLayerError(f"Configuration file not found: {config_path}")

        self.config = self._load_config()
        self.connection = self._create_connection()
        self._cache: Dict[str, Any] = {}
        self._models_list_cache: Optional[List[Dict[str, Any]]] = None

        # Load temporal dimensions if available
        self._load_temporal_dimensions()

        logger.info(f"Semantic layer initialized with {len(self.list_metrics())} metrics")

    def _load_config(self) -> Dict:
        """Load semantic model configuration from YAML with environment variable support."""
        try:
            with open(self.config_path, "r") as f:
                raw_content = f.read()

            # Expand environment variables
            expanded_content = self._expand_env_vars(raw_content)

            # Parse YAML
            config = yaml.safe_load(expanded_content)

            # Validate required sections
            if not config or "semantic_model" not in config:
                raise SemanticLayerError("Configuration must contain 'semantic_model' section")

            required_fields = ["name", "connection", "metrics"]
            model_config = config["semantic_model"]

            for field in required_fields:
                if field not in model_config:
                    raise SemanticLayerError(f"Missing required field: {field}")

            # Override database path with environment variable if set
            if "DATABASE_PATH" in os.environ:
                config["semantic_model"]["connection"]["database"] = os.environ["DATABASE_PATH"]

            return config

        except yaml.YAMLError as e:
            raise SemanticLayerError(f"Error parsing YAML configuration: {e}")

    def _expand_env_vars(self, content: str) -> str:
        """Expand environment variables in configuration content."""
        def replace_var(match):
            # Get the line containing this match to check if it's commented
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.start())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end]

            # Skip if line is commented out
            if line.strip().startswith("#"):
                return match.group(0)

            var_expr = match.group(1)
            if ":" in var_expr:
                var_name, default = var_expr.split(":", 1)
                return os.environ.get(var_name.strip(), default.strip())
            else:
                var_name = var_expr.strip()
                if var_name not in os.environ:
                    logger.warning(f"Environment variable not set: {var_name}")
                    return match.group(0)
                return os.environ[var_name]

        # Replace ${VAR} and ${VAR:default} patterns
        pattern = r"\$\{([^}]+)\}"
        return re.sub(pattern, replace_var, content)

    def _load_temporal_dimensions(self):
        """Load temporal dimensions from date_dimensions_config.yaml if present."""
        temporal_config_path = Path(self.config_path).parent.parent / "date_dimensions_config.yaml"

        if temporal_config_path.exists():
            try:
                with open(temporal_config_path, "r") as f:
                    temporal_config = yaml.safe_load(f)

                if temporal_config and "temporal_dimensions" in temporal_config:
                    if "dimensions" not in self.config["semantic_model"]:
                        self.config["semantic_model"]["dimensions"] = []

                    for temp_dim in temporal_config["temporal_dimensions"]:
                        existing_names = [d["name"] for d in self.config["semantic_model"]["dimensions"]]
                        if temp_dim["name"] not in existing_names:
                            self.config["semantic_model"]["dimensions"].append(temp_dim)

                    logger.info(f"Loaded {len(temporal_config['temporal_dimensions'])} temporal dimensions")
            except Exception as e:
                logger.warning(f"Could not load temporal dimensions config: {e}")

    def _create_connection(self) -> ibis.BaseBackend:
        """Create Ibis connection to data warehouse."""
        conn_config = self.config["semantic_model"]["connection"]
        db_type = conn_config.get("type", "duckdb")

        try:
            if db_type == "duckdb":
                database = conn_config.get("database", ":memory:")
                logger.info(f"Connecting to DuckDB: {database}")
                return ibis.duckdb.connect(database)

            elif db_type == "snowflake":
                logger.info("Connecting to Snowflake...")
                return ibis.snowflake.connect(
                    user=conn_config["user"],
                    password=conn_config["password"],
                    account=conn_config["account"],
                    database=conn_config["database"],
                    warehouse=conn_config.get("warehouse"),
                    schema=conn_config.get("schema", "public"),
                )

            elif db_type == "bigquery":
                logger.info("Connecting to BigQuery...")
                return ibis.bigquery.connect(
                    project_id=conn_config["project_id"],
                    dataset_id=conn_config.get("dataset_id")
                )

            elif db_type in ("postgres", "postgresql"):
                logger.info("Connecting to PostgreSQL...")
                return ibis.postgres.connect(
                    host=conn_config["host"],
                    port=conn_config.get("port", 5432),
                    database=conn_config["database"],
                    user=conn_config["user"],
                    password=conn_config["password"],
                )

            else:
                raise SemanticLayerError(f"Unsupported database type: {db_type}")

        except Exception as e:
            raise SemanticLayerError(f"Error connecting to database: {e}")

    def list_metrics(self) -> List[Dict]:
        """
        List all available metrics.

        Returns:
            List of metric definitions with metadata
        """
        metrics = self.config["semantic_model"].get("metrics", [])
        return [
            {
                "name": m["name"],
                "display_name": m.get("display_name", m["name"]),
                "description": m.get("description", ""),
                "type": m.get("type", "simple"),
            }
            for m in metrics
        ]

    def get_metric(self, metric_name: str) -> Dict:
        """
        Get metric definition by name.

        Args:
            metric_name: Name of the metric

        Returns:
            Metric definition dictionary

        Raises:
            SemanticLayerError: If metric not found
        """
        metrics = self.config["semantic_model"]["metrics"]
        for metric in metrics:
            if metric["name"] == metric_name:
                return metric

        available = [m["name"] for m in metrics]
        raise SemanticLayerError(
            f"Metric '{metric_name}' not found. Available metrics: {', '.join(available)}"
        )

    def list_dimensions(self) -> List[Dict]:
        """List all available dimensions."""
        dimensions = self.config["semantic_model"].get("dimensions", [])
        return [
            {
                "name": d["name"],
                "type": d.get("type", "categorical"),
                "description": d.get("description", ""),
                "table": d.get("table"),
                "column": d.get("column"),
                "sql": d.get("sql"),
            }
            for d in dimensions
        ]

    def get_dimension(self, dimension_name: str) -> Optional[Dict]:
        """Get dimension definition by name."""
        dimensions = self.config["semantic_model"].get("dimensions", [])
        for dim in dimensions:
            if dim["name"] == dimension_name:
                return dim
        return None

    def query_metric(
        self,
        metric_name: str,
        dimensions: Optional[List[str]] = None,
        filters: Optional[List[str]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> Dict:
        """
        Query a metric with optional dimensions and filters.

        Args:
            metric_name: Name of metric to query
            dimensions: List of dimension names to group by
            filters: List of SQL WHERE conditions
            limit: Maximum rows to return
            order_by: Column to sort by (prefix with - for descending)

        Returns:
            Dictionary containing query results and metadata

        Raises:
            SemanticLayerError: If query fails
        """
        try:
            metric = self.get_metric(metric_name)
            metric_type = metric.get("type", "simple")

            logger.info(f"Querying metric: {metric_name} (type: {metric_type})")

            if metric_type == "simple":
                result_df, sql = self._query_simple_metric(
                    metric, dimensions, filters, limit, order_by
                )
            elif metric_type == "derived":
                result_df, sql = self._query_derived_metric(
                    metric, dimensions, filters, limit, order_by
                )
            else:
                raise SemanticLayerError(f"Unknown metric type: {metric_type}")

            # Handle NaN results
            data = result_df.to_dict("records")
            row_count = len(result_df)

            if row_count == 1 and len(data) == 1:
                import math
                metric_value = data[0].get(metric_name)
                if metric_value is not None and isinstance(metric_value, (int, float)):
                    if math.isnan(metric_value):
                        data = []
                        row_count = 0

            return {
                "metric": metric_name,
                "display_name": metric.get("display_name", metric_name),
                "description": metric.get("description", ""),
                "dimensions": dimensions or [],
                "data": data,
                "row_count": row_count,
                "sql": sql,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error querying metric {metric_name}: {e}")
            raise SemanticLayerError(f"Query failed: {e}")

    def _apply_filter(self, table, filter_expr: str):
        """Apply a filter expression to a table."""
        filter_expr = filter_expr.strip()

        # Handle equality: column = 'value'
        match = re.match(r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] == value)

        # Handle equality with numbers: column = 123
        match = re.match(r"(\w+)\s*=\s*(\d+)", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] == int(value))

        # Handle inequality: column != 'value'
        match = re.match(r"(\w+)\s*!=\s*['\"]([^'\"]+)['\"]", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] != value)

        # Handle comparisons
        for op, op_func in [
            (r">=", lambda t, c, v: t.filter(t[c] >= float(v))),
            (r"<=", lambda t, c, v: t.filter(t[c] <= float(v))),
            (r">", lambda t, c, v: t.filter(t[c] > float(v))),
            (r"<", lambda t, c, v: t.filter(t[c] < float(v))),
        ]:
            match = re.match(rf"(\w+)\s*{op}\s*(\d+\.?\d*)", filter_expr)
            if match:
                column, value = match.groups()
                if column in table.columns:
                    return op_func(table, column, value)

        logger.warning(f"Could not parse filter expression: {filter_expr}")
        return table

    def _resolve_dimension_expression(
        self, dim: Dict, table, table_name: str, alias_name: str = None
    ) -> Any:
        """Resolve a dimension to an Ibis expression."""
        dim_name = dim["name"]

        if "sql" in dim and dim["sql"]:
            sql_expr = dim["sql"]
            table_ref_pattern = r'\{\{\s*Table\s*\}\}\.(\w+)'
            col_matches = re.findall(table_ref_pattern, sql_expr)

            if not col_matches:
                raise SemanticLayerError(
                    f"Temporal dimension '{dim_name}' SQL expression must contain {{{{ Table }}}}.column_name"
                )

            source_column = col_matches[0]
            if source_column not in table.columns:
                raise SemanticLayerError(
                    f"Column '{source_column}' referenced in temporal dimension '{dim_name}' "
                    f"not found in table '{table_name}'"
                )

            # Parse strftime pattern
            strftime_pattern = r"strftime\(['\"]([^'\"]+)['\"]\s*,\s*\{\{\s*Table\s*\}\}\.(\w+)\)"
            strftime_match = re.search(strftime_pattern, sql_expr)

            if strftime_match:
                format_str, col_name = strftime_match.groups()
                expr = table[col_name].strftime(format_str)
                return expr.name(alias_name or dim_name)

            # Handle quarter pattern
            quarter_pattern = r"strftime\(['\"]%Y['\"]\s*,\s*\{\{\s*Table\s*\}\}\.(\w+)\)\s*\|\|\s*['\"](-Q)['\"]"
            quarter_match = re.search(quarter_pattern, sql_expr)

            if quarter_match:
                col_name = quarter_match.group(1)
                year_str = table[col_name].strftime('%Y')
                month_int = table[col_name].month()
                quarter_num = ((month_int + 2) / 3).cast('int').cast('string')
                expr = year_str + '-Q' + quarter_num
                return expr.name(alias_name or dim_name)

            raise SemanticLayerError(
                f"Could not parse SQL expression for temporal dimension '{dim_name}': {sql_expr}"
            )

        else:
            col = dim.get("column", dim_name)
            if col in table.columns:
                if alias_name and alias_name != col:
                    return table[col].name(alias_name)
                return table[col]
            else:
                raise SemanticLayerError(
                    f"Column '{col}' for dimension '{dim_name}' not found in table '{table_name}'"
                )

    def _query_simple_metric(
        self,
        metric: Dict,
        dimensions: Optional[List[str]],
        filters: Optional[List[str]],
        limit: Optional[int],
        order_by: Optional[str],
    ) -> tuple:
        """Execute query for simple (aggregated) metric."""
        calc = metric["calculation"]
        table_name = calc["table"]
        table = self.connection.table(table_name)

        # Apply metric-defined filters
        for filter_expr in calc.get("filters", []):
            table = self._apply_filter(table, filter_expr)

        # Apply user-provided filters
        if filters:
            for filter_expr in filters:
                table = self._apply_filter(table, filter_expr)

        # Build aggregation
        agg_type = calc["aggregation"]
        column_name = calc["column"]
        agg_column = table[column_name]

        agg_map = {
            "sum": agg_column.sum,
            "count": agg_column.count,
            "count_distinct": agg_column.nunique,
            "avg": agg_column.mean,
            "average": agg_column.mean,
            "mean": agg_column.mean,
            "min": agg_column.min,
            "max": agg_column.max,
        }

        if agg_type not in agg_map:
            raise SemanticLayerError(f"Unknown aggregation type: {agg_type}")

        agg_expr = agg_map[agg_type]().name(metric["name"])

        # Handle dimensions
        if dimensions:
            group_by_columns = []
            for dim_name in dimensions:
                dim = self.get_dimension(dim_name)
                if dim:
                    dim_table = dim.get("table")
                    if dim_table and dim_table != table_name:
                        dim_table_obj = self.connection.table(dim_table)
                        common_cols = set(table.columns) & set(dim_table_obj.columns)
                        if common_cols:
                            join_key = list(common_cols)[0]
                            table = table.join(dim_table_obj, join_key, how="left")
                            dim_expr = self._resolve_dimension_expression(dim, table, dim_table, dim_name)
                            group_by_columns.append(dim_expr)
                        else:
                            raise SemanticLayerError(
                                f"Cannot join {table_name} with {dim_table} - no common columns"
                            )
                    else:
                        dim_expr = self._resolve_dimension_expression(dim, table, table_name, dim_name)
                        group_by_columns.append(dim_expr)
                elif dim_name in table.columns:
                    group_by_columns.append(table[dim_name])
                else:
                    raise SemanticLayerError(f"Dimension '{dim_name}' not found")

            result = table.group_by(group_by_columns).aggregate(agg_expr)
        else:
            result = table.aggregate(agg_expr)

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                result = result.order_by(ibis.desc(order_by[1:]))
            else:
                result = result.order_by(order_by)

        # Apply limit
        if limit:
            result = result.limit(limit)

        sql = ibis.to_sql(result)
        result_df = result.execute()

        return result_df, sql

    def _query_derived_metric(
        self,
        metric: Dict,
        dimensions: Optional[List[str]],
        filters: Optional[List[str]],
        limit: Optional[int],
        order_by: Optional[str],
    ) -> tuple:
        """Execute query for derived metric (calculated from other metrics)."""
        import pandas as pd

        calc = metric["calculation"]
        formula = calc.get("formula")

        if not formula:
            raise SemanticLayerError(f"Derived metric '{metric['name']}' missing formula")

        # Extract component metrics
        component_metric_names = re.findall(r"\b([a-z_]+)\b", formula)
        component_metric_names = [
            m for m in set(component_metric_names)
            if not m.replace("_", "").isdigit()
        ]

        logger.info(f"Derived metric '{metric['name']}' uses components: {component_metric_names}")

        # Query component metrics
        component_data = {}
        for comp_name in component_metric_names:
            try:
                comp_metric = self.get_metric(comp_name)
                comp_result, _ = self._query_simple_metric(
                    comp_metric, dimensions, filters, limit, order_by
                )
                component_data[comp_name] = comp_result
            except Exception as e:
                logger.warning(f"Could not query component metric '{comp_name}': {e}")

        if not component_data:
            raise SemanticLayerError(
                f"Derived metric '{metric['name']}' references no queryable metrics"
            )

        # Combine results
        result_df = component_data[list(component_data.keys())[0]]
        for comp_name, comp_df in list(component_data.items())[1:]:
            if dimensions:
                result_df = result_df.merge(comp_df, on=dimensions, how="outer")
            else:
                for col in comp_df.columns:
                    if col not in result_df.columns:
                        result_df[col] = comp_df[col].iloc[0] if len(comp_df) > 0 else 0

        # Evaluate formula
        namespace = {col: result_df[col] for col in result_df.columns}

        try:
            if len(result_df) > 0:
                results = []
                for _, row in result_df.iterrows():
                    row_namespace = {col: row[col] for col in namespace.keys()}
                    result = eval(formula, {"__builtins__": {}}, row_namespace)
                    results.append(result)
                result_df[metric["name"]] = results
            else:
                result_df[metric["name"]] = None
        except Exception as e:
            raise SemanticLayerError(f"Error evaluating formula '{formula}': {e}")

        sql = f"-- Derived metric: {metric['name']}\n-- Formula: {formula}"
        return result_df, sql

    def explain_metric(self, metric_name: str) -> str:
        """Get a human-readable explanation of how a metric is calculated."""
        metric = self.get_metric(metric_name)

        explanation = f"**{metric.get('display_name', metric_name)}**\n\n"
        explanation += f"{metric.get('description', 'No description provided')}\n\n"

        metric_type = metric.get("type", "simple")
        explanation += f"**Type:** {metric_type}\n\n"

        if metric_type == "simple":
            calc = metric["calculation"]
            explanation += f"**Calculation:**\n"
            explanation += f"  - Aggregation: {calc['aggregation']}\n"
            explanation += f"  - Column: {calc['column']}\n"
            explanation += f"  - Table: {calc['table']}\n"

            filters = calc.get("filters", [])
            if filters:
                explanation += f"\n**Filters:**\n"
                for f in filters:
                    explanation += f"  - {f}\n"

        elif metric_type == "derived":
            calc = metric["calculation"]
            explanation += f"**Formula:** {calc.get('formula', 'Not specified')}\n"

        return explanation

    def clear_cache(self):
        """Clear the query result cache."""
        self._cache = {}
        self._models_list_cache = None
        logger.info("Cache cleared")

    def close(self):
        """Close database connection."""
        if hasattr(self.connection, "close"):
            self.connection.close()
            logger.info("Database connection closed")
        elif hasattr(self.connection, "disconnect"):
            self.connection.disconnect()
            logger.info("Database connection disconnected")
