"""
Semantic Layer Implementation

This module provides a semantic layer that:
1. Loads metric definitions from YAML
2. Connects to data warehouses via Ibis
3. Translates metric queries to SQL
4. Returns results in a standard format
"""

import yaml
import ibis
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
import os
import re

from src.safe_expression_parser import safe_eval, SafeExpressionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticLayerError(Exception):
    """Custom exception for semantic layer errors"""

    pass


class SemanticLayer:
    """
    Semantic Layer that provides a business-friendly interface to query metrics
    """

    def __init__(self, config_path: str):
        """
        Initialize semantic layer with configuration

        Args:
            config_path: Path to semantic models YAML file
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise SemanticLayerError(f"Configuration file not found: {config_path}")

        self.config = self._load_config()
        self.connection = self._create_connection()
        self._cache = {}  # Simple query result cache

        # Load temporal dimensions if available
        self._load_temporal_dimensions()

        logger.info(f"Semantic layer initialized with {len(self.list_metrics())} metrics")

    def _load_temporal_dimensions(self):
        """Load temporal dimensions from date_dimensions_config.yaml if present"""
        temporal_config_path = Path(self.config_path).parent.parent / "date_dimensions_config.yaml"

        if temporal_config_path.exists():
            try:
                with open(temporal_config_path, "r") as f:
                    temporal_config = yaml.safe_load(f)

                if temporal_config and "temporal_dimensions" in temporal_config:
                    # Merge temporal dimensions into main config
                    if "dimensions" not in self.config["semantic_model"]:
                        self.config["semantic_model"]["dimensions"] = []

                    for temp_dim in temporal_config["temporal_dimensions"]:
                        # Add to dimensions list if not already present
                        existing_names = [d["name"] for d in self.config["semantic_model"]["dimensions"]]
                        if temp_dim["name"] not in existing_names:
                            self.config["semantic_model"]["dimensions"].append(temp_dim)

                    logger.info(f"Loaded {len(temporal_config['temporal_dimensions'])} temporal dimensions")
            except Exception as e:
                logger.warning(f"Could not load temporal dimensions config: {e}")

    def _load_config(self) -> Dict:
        """Load semantic model configuration from YAML with environment variable support"""
        try:
            with open(self.config_path, "r") as f:
                raw_content = f.read()

            # Expand environment variables
            expanded_content = self._expand_env_vars(raw_content)

            # Parse YAML
            config = yaml.safe_load(expanded_content)

            # Validate required sections
            if "semantic_model" not in config:
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
        """Expand environment variables in configuration content"""
        import re

        def replace_var(match):
            # Get the line containing this match to check if it's commented
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.start())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end]

            # Skip if line is commented out
            if line.strip().startswith("#"):
                return match.group(0)  # Return original ${VAR} unchanged

            var_expr = match.group(1)
            if ":" in var_expr:
                var_name, default = var_expr.split(":", 1)
                return os.environ.get(var_name.strip(), default.strip())
            else:
                var_name = var_expr.strip()
                if var_name not in os.environ:
                    # For non-commented lines, this is optional - just return original
                    logger.warning(f"Environment variable not set: {var_name}")
                    return match.group(0)  # Return original ${VAR}
                return os.environ[var_name]

        # Replace ${VAR} and ${VAR:default} patterns
        pattern = r"\$\{([^}]+)\}"
        return re.sub(pattern, replace_var, content)

    def _create_connection(self) -> ibis.BaseBackend:
        """Create Ibis connection to data warehouse"""
        conn_config = self.config["semantic_model"]["connection"]
        db_type = conn_config.get("type", "duckdb")

        try:
            if db_type == "duckdb":
                database = conn_config.get("database", "data/sample.duckdb")
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
                    project_id=conn_config["project_id"], dataset_id=conn_config.get("dataset_id")
                )

            elif db_type == "postgres":
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
        List all available metrics

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
        Get metric definition by name

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

        raise SemanticLayerError(
            f"Metric '{metric_name}' not found. "
            f"Available metrics: {', '.join([m['name'] for m in metrics])}"
        )

    def list_dimensions(self) -> List[Dict]:
        """List all available dimensions"""
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
        """Get dimension definition by name"""
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
        Query a metric with optional dimensions and filters

        Args:
            metric_name: Name of metric to query
            dimensions: List of dimension names to group by
            filters: List of SQL WHERE conditions
            limit: Maximum rows to return
            order_by: Column to sort by

        Returns:
            Dictionary containing:
                - metric: metric name
                - display_name: human-readable name
                - description: metric description
                - dimensions: dimensions used
                - data: query results as list of dicts
                - row_count: number of rows
                - sql: generated SQL (for transparency)

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

            # Handle case where aggregation returns single row with NaN/NULL
            # (happens when filters match no rows)
            data = result_df.to_dict("records")
            row_count = len(result_df)

            if row_count == 1 and len(data) == 1:
                # Check if the metric value is NaN/NULL
                import math

                metric_value = data[0].get(metric_name)
                if metric_value is not None and isinstance(metric_value, (int, float)):
                    if math.isnan(metric_value):
                        # Treat as empty result
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
        """
        Apply a filter expression to a table

        Parses simple SQL WHERE conditions like:
        - "column = 'value'"
        - "column > 100"
        - "column IN ('a', 'b')"

        Args:
            table: Ibis table expression
            filter_expr: SQL WHERE condition string

        Returns:
            Filtered table
        """
        import re

        # Simple parser for common filter expressions
        filter_expr = filter_expr.strip()

        # Handle equality: column = 'value' or column = "value"
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

        # Handle greater than: column > 100
        match = re.match(r"(\w+)\s*>\s*(\d+\.?\d*)", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] > float(value))

        # Handle less than: column < 100
        match = re.match(r"(\w+)\s*<\s*(\d+\.?\d*)", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] < float(value))

        # Handle >= and <=
        match = re.match(r"(\w+)\s*>=\s*(\d+\.?\d*)", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] >= float(value))

        match = re.match(r"(\w+)\s*<=\s*(\d+\.?\d*)", filter_expr)
        if match:
            column, value = match.groups()
            if column in table.columns:
                return table.filter(table[column] <= float(value))

        # If we can't parse it, log warning and return unfiltered table
        logger.warning(f"Could not parse filter expression: {filter_expr}")
        return table

    def _resolve_dimension_expression(
        self, dim: Dict, table, table_name: str, alias_name: str = None
    ) -> Any:
        """
        Resolve a dimension to an Ibis expression, handling both simple columns and SQL expressions.

        Args:
            dim: Dimension definition dictionary
            table: Ibis table object
            table_name: Name of the base table
            alias_name: Optional alias to use for the dimension

        Returns:
            Ibis expression for the dimension
        """
        dim_name = dim["name"]
        dim_type = dim.get("type", "categorical")

        # Check if dimension has SQL expression (temporal dimensions)
        if "sql" in dim and dim["sql"]:
            sql_expr = dim["sql"]

            # Replace {{ Table }} placeholder with actual table reference
            # Extract column reference pattern from SQL expression
            table_ref_pattern = r'\{\{\s*Table\s*\}\}\.(\w+)'

            # Find all column references in the SQL expression
            col_matches = re.findall(table_ref_pattern, sql_expr)

            if not col_matches:
                raise SemanticLayerError(
                    f"Temporal dimension '{dim_name}' SQL expression must contain {{{{ Table }}}}.column_name"
                )

            # For now, use the first column reference
            source_column = col_matches[0]

            # Verify the column exists in the table
            if source_column not in table.columns:
                raise SemanticLayerError(
                    f"Column '{source_column}' referenced in temporal dimension '{dim_name}' "
                    f"not found in table '{table_name}'"
                )

            # Parse SQL expression and convert to Ibis
            # Handle common temporal functions

            # Pattern: strftime('%Y-%m', column)
            strftime_pattern = r"strftime\(['\"]([^'\"]+)['\"]\s*,\s*\{\{\s*Table\s*\}\}\.(\w+)\)"
            strftime_match = re.search(strftime_pattern, sql_expr)

            if strftime_match:
                format_str, col_name = strftime_match.groups()

                # Map strftime formats to Ibis operations
                if format_str == '%Y-%m':
                    # Year-Month format
                    expr = table[col_name].strftime('%Y-%m')
                elif format_str == '%Y':
                    # Year only
                    expr = table[col_name].strftime('%Y')
                elif format_str == '%Y-%m-%d':
                    # Full date
                    expr = table[col_name].strftime('%Y-%m-%d')
                elif format_str == '%m':
                    # Month only
                    expr = table[col_name].strftime('%m')
                else:
                    # Generic strftime
                    expr = table[col_name].strftime(format_str)

                # Use alias if provided, otherwise use dimension name
                return expr.name(alias_name or dim_name)

            # Pattern: Complex quarter calculation
            # strftime('%Y', col) || '-Q' || CAST((CAST(strftime('%m', col) AS INTEGER) + 2) / 3 AS TEXT)
            quarter_pattern = r"strftime\(['\"]%Y['\"]\s*,\s*\{\{\s*Table\s*\}\}\.(\w+)\)\s*\|\|\s*['\"](-Q)['\"]"
            quarter_match = re.search(quarter_pattern, sql_expr)

            if quarter_match:
                col_name = quarter_match.group(1)
                # Compute quarter: (month + 2) / 3
                year_str = table[col_name].strftime('%Y')
                month_int = table[col_name].month()
                quarter_num = ((month_int + 2) / 3).cast('int').cast('string')
                expr = year_str + '-Q' + quarter_num
                return expr.name(alias_name or dim_name)

            # If we can't parse the SQL expression, raise an error
            raise SemanticLayerError(
                f"Could not parse SQL expression for temporal dimension '{dim_name}': {sql_expr}"
            )

        else:
            # Simple column reference (existing behavior)
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
        """Execute query for simple (aggregated) metric"""
        calc = metric["calculation"]
        table_name = calc["table"]

        # Get base table
        table = self.connection.table(table_name)

        # Apply metric-defined filters
        metric_filters = calc.get("filters", [])
        for filter_expr in metric_filters:
            # Parse simple filter expressions like "column = 'value'" or "column > 100"
            table = self._apply_filter(table, filter_expr)

        # Apply user-provided filters
        if filters:
            for filter_expr in filters:
                table = self._apply_filter(table, filter_expr)

        # Build aggregation expression
        agg_type = calc["aggregation"]
        column_name = calc["column"]
        agg_column = table[column_name]

        # Create aggregation based on type
        if agg_type == "sum":
            agg_expr = agg_column.sum().name(metric["name"])
        elif agg_type == "count":
            agg_expr = agg_column.count().name(metric["name"])
        elif agg_type == "count_distinct":
            agg_expr = agg_column.nunique().name(metric["name"])
        elif agg_type == "avg" or agg_type == "average" or agg_type == "mean":
            agg_expr = agg_column.mean().name(metric["name"])
        elif agg_type == "min":
            agg_expr = agg_column.min().name(metric["name"])
        elif agg_type == "max":
            agg_expr = agg_column.max().name(metric["name"])
        else:
            raise SemanticLayerError(f"Unknown aggregation type: {agg_type}")

        # Handle dimensions
        if dimensions:
            group_by_columns = []
            for dim_name in dimensions:
                dim = self.get_dimension(dim_name)
                if dim:
                    dim_table = dim.get("table")
                    dim_type = dim.get("type", "categorical")

                    # Check if dimension is from a different table
                    if dim_table and dim_table != table_name:
                        # Need to join with dimension table
                        logger.info(
                            f"Joining {table_name} with {dim_table} for dimension {dim_name}"
                        )

                        # Get the dimension table
                        dim_table_obj = self.connection.table(dim_table)

                        # Perform join (assuming common join key pattern: customer_id, product_id, etc.)
                        # Look for common columns between tables
                        common_cols = set(table.columns) & set(dim_table_obj.columns)

                        if common_cols:
                            # Use first common column as join key (typically customer_id, product_id, etc.)
                            join_key = list(common_cols)[0]
                            logger.info(f"Joining on {join_key}")
                            table = table.join(dim_table_obj, join_key, how="left")

                            # Resolve dimension expression (handles temporal SQL expressions)
                            dim_expr = self._resolve_dimension_expression(dim, table, dim_table, dim_name)
                            group_by_columns.append(dim_expr)
                        else:
                            logger.warning(
                                f"No common columns found between {table_name} and {dim_table}"
                            )
                            raise SemanticLayerError(
                                f"Cannot join {table_name} with {dim_table} - no common columns found"
                            )
                    else:
                        # Dimension is in the same table or table not specified
                        # Use _resolve_dimension_expression to handle both simple and temporal dimensions
                        dim_expr = self._resolve_dimension_expression(dim, table, table_name, dim_name)
                        group_by_columns.append(dim_expr)
                else:
                    # Try to use dimension name directly as column
                    if dim_name in table.columns:
                        group_by_columns.append(table[dim_name])
                    else:
                        raise SemanticLayerError(
                            f"Dimension '{dim_name}' not found and not a column in table"
                        )

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

        # Compile to SQL (for transparency)
        sql = ibis.to_sql(result)

        # Execute query
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
        """
        Execute query for derived metric (calculated from other metrics)

        Derived metrics are calculated using a formula that references other metrics.
        For example: arpc = mrr / customer_count

        Week 1 Implementation: Basic formula support for division/multiplication of simple metrics
        """
        calc = metric["calculation"]
        formula = calc.get("formula")

        if not formula:
            raise SemanticLayerError(f"Derived metric '{metric['name']}' missing formula")

        # Parse formula to find component metrics (simple implementation)
        # Support basic operations: +, -, *, /
        import re

        # Extract metric names from formula (assuming they're valid Python identifiers)
        component_metric_names = re.findall(r"\b([a-z_]+)\b", formula)

        # Remove duplicates and filter out numbers
        component_metric_names = [
            m for m in set(component_metric_names) if not m.replace("_", "").isdigit()
        ]

        logger.info(f"Derived metric '{metric['name']}' uses components: {component_metric_names}")

        # Query each component metric
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
                # Component might not be a metric, could be a constant or function
                pass

        if not component_data:
            raise SemanticLayerError(
                f"Derived metric '{metric['name']}' references no queryable metrics"
            )

        # Combine results using pandas
        import pandas as pd

        # Start with first component
        result_df = component_data[list(component_data.keys())[0]]

        # Merge in other components
        for comp_name, comp_df in list(component_data.items())[1:]:
            if dimensions:
                result_df = result_df.merge(comp_df, on=dimensions, how="outer")
            else:
                # Scalar values - just combine
                for col in comp_df.columns:
                    if col not in result_df.columns:
                        result_df[col] = comp_df[col].iloc[0] if len(comp_df) > 0 else 0

        # Evaluate formula
        # Create namespace with component metric values
        namespace = {}
        for col in result_df.columns:
            if col not in dimensions if dimensions else True:
                namespace[col] = result_df[col]

        try:
            # Evaluate formula safely using secure parser
            if len(result_df) > 0:
                # For DataFrames with data, evaluate per row
                results = []
                for _, row in result_df.iterrows():
                    row_namespace = {col: row[col] for col in namespace.keys()}
                    result = safe_eval(formula, row_namespace)
                    results.append(result)
                result_df[metric["name"]] = results
            else:
                # For empty DataFrames, just set default
                result_df[metric["name"]] = None
        except SafeExpressionError as e:
            raise SemanticLayerError(f"Invalid formula '{formula}': {e}")
        except Exception as e:
            raise SemanticLayerError(f"Error evaluating formula '{formula}': {e}")

        # Build SQL representation (simplified)
        sql = f"-- Derived metric: {metric['name']}\n-- Formula: {formula}\n"
        sql += "-- Computed from component metrics"

        return result_df, sql

    def explain_metric(self, metric_name: str) -> str:
        """
        Get a human-readable explanation of how a metric is calculated

        Args:
            metric_name: Name of the metric

        Returns:
            Formatted explanation string
        """
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

    def close(self):
        """Close database connection"""
        if hasattr(self.connection, "close"):
            self.connection.close()
            logger.info("Database connection closed")


# Example usage and testing
if __name__ == "__main__":
    import sys

    # Check if semantic models file exists
    config_path = "semantic_models/metrics.yml"
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("   Create semantic_models/metrics.yml first")
        sys.exit(1)

    # Initialize semantic layer
    try:
        sl = SemanticLayer(config_path)

        print("📊 Testing Semantic Layer\n")
        print("=" * 60)

        # List metrics
        print("\n1. Available Metrics:")
        for metric in sl.list_metrics():
            print(f"   - {metric['name']}: {metric['display_name']}")

        # List dimensions
        print("\n2. Available Dimensions:")
        dims = sl.list_dimensions()
        if dims:
            for dim in dims:
                dim_type = dim['type']
                sql_info = f" (SQL: {dim['sql'][:50]}...)" if dim.get('sql') else ""
                print(f"   - {dim['name']} ({dim_type}){sql_info}")
        else:
            print("   - No dimensions defined")

        # Test querying a metric
        if sl.list_metrics():
            test_metric = sl.list_metrics()[0]["name"]
            print(f"\n3. Testing Query: {test_metric}")

            result = sl.query_metric(test_metric)
            print(f"   Result: {result['data']}")

            # Try with dimensions if available
            if dims and len(dims) > 0:
                dim_name = dims[0]["name"]
                print(f"\n4. Testing Query with Dimension: {test_metric} by {dim_name}")
                result = sl.query_metric(test_metric, dimensions=[dim_name])
                print(f"   Results:")
                for row in result["data"][:5]:  # Show first 5
                    print(f"     {row}")
                if result["row_count"] > 5:
                    print(f"     ... and {result['row_count'] - 5} more rows")

        print("\n" + "=" * 60)
        print("✅ Semantic layer test completed successfully!")

    except SemanticLayerError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
