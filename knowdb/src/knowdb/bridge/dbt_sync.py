"""
dbt-to-Semantic-Layer Bridge

Converts dbt models to KnowDB semantic layer definitions.
Automatically extracts metrics and dimensions from dbt SQL and schema.yml files.
"""

import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union


class AggregationType(str, Enum):
    """Supported aggregation types for metrics."""
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class DimensionType(str, Enum):
    """Types of dimensions."""
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"


@dataclass
class DbtColumn:
    """Represents a column in a dbt model."""
    name: str
    description: str = ""
    data_type: str = ""
    tests: List[str] = field(default_factory=list)


@dataclass
class DbtModel:
    """Represents a dbt model with its metadata."""
    name: str
    path: str
    sql: str = ""
    description: str = ""
    columns: List[DbtColumn] = field(default_factory=list)


@dataclass
class MetricDefinition:
    """Definition of a metric extracted from dbt."""
    name: str
    display_name: str
    description: str
    table: str
    column: str
    aggregation: AggregationType


@dataclass
class DimensionDefinition:
    """Definition of a dimension extracted from dbt."""
    name: str
    display_name: str
    description: str
    table: str
    column: str
    type: DimensionType


@dataclass
class SyncResult:
    """Result of a sync operation."""
    models_processed: int
    metrics_generated: int
    dimensions_generated: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DbtSemanticBridge:
    """
    Converts dbt models to KnowDB semantic layer definitions.

    This bridge parses dbt SQL models and schema.yml files to automatically
    generate semantic layer metrics and dimensions.
    """

    def __init__(
        self,
        dbt_project_path: Union[str, Path],
        semantic_output_path: Union[str, Path]
    ):
        """
        Initialize the bridge.

        Args:
            dbt_project_path: Path to the dbt project root
            semantic_output_path: Path where the semantic YAML will be written

        Raises:
            ValueError: If dbt project path does not exist
        """
        self.dbt_path = Path(dbt_project_path) if isinstance(dbt_project_path, str) else dbt_project_path
        self.output_path = Path(semantic_output_path) if isinstance(semantic_output_path, str) else semantic_output_path

        if not self.dbt_path.exists():
            raise ValueError(f"dbt project path does not exist: {self.dbt_path}")

    def discover_models(self, model_path: str = "marts") -> List[DbtModel]:
        """
        Discover dbt models in the project.

        Args:
            model_path: Subdirectory under models/ to search (default: "marts")

        Returns:
            List of DbtModel objects
        """
        models = []
        models_dir = self.dbt_path / "models" / model_path

        if not models_dir.exists():
            return models

        # Load all schema.yml files in the directory
        schemas = self._load_schemas(models_dir)

        # Find all SQL files
        for sql_file in models_dir.rglob("*.sql"):
            model_name = sql_file.stem
            sql_content = sql_file.read_text()

            # Get metadata from schema if available
            schema_info = schemas.get(model_name, {})
            description = schema_info.get("description", "")
            columns = [
                DbtColumn(
                    name=col.get("name", ""),
                    description=col.get("description", ""),
                    data_type=col.get("data_type", ""),
                    tests=col.get("tests", [])
                )
                for col in schema_info.get("columns", [])
            ]

            model = DbtModel(
                name=model_name,
                path=str(sql_file.parent),
                sql=sql_content,
                description=description,
                columns=columns
            )
            models.append(model)

        return models

    def _load_schemas(self, models_dir: Path) -> dict:
        """Load all schema.yml files and build a lookup by model name."""
        schemas = {}

        for schema_file in models_dir.rglob("*.yml"):
            if schema_file.stem.startswith("_"):
                continue

            try:
                content = yaml.safe_load(schema_file.read_text())
                if not content or "models" not in content:
                    continue

                for model_info in content.get("models", []):
                    model_name = model_info.get("name")
                    if model_name:
                        schemas[model_name] = model_info
            except yaml.YAMLError:
                continue

        return schemas

    def extract_metrics(self, model: DbtModel) -> List[MetricDefinition]:
        """
        Extract metric definitions from a dbt model.

        Looks for aggregation patterns (SUM, COUNT, AVG, etc.) in the SQL.

        Args:
            model: The dbt model to extract from

        Returns:
            List of MetricDefinition objects
        """
        metrics = []
        aggregations = self._parse_aggregations(model.sql)

        # Create a lookup for column descriptions
        column_descs = {col.name: col.description for col in model.columns}

        for alias, agg_type, source_col in aggregations:
            aggregation = self._map_aggregation(agg_type)
            if not aggregation:
                continue

            metric = MetricDefinition(
                name=alias,
                display_name=self._to_display_name(alias),
                description=column_descs.get(alias, ""),
                table=model.name,
                column=alias,
                aggregation=aggregation
            )
            metrics.append(metric)

        return metrics

    def extract_dimensions(self, model: DbtModel) -> List[DimensionDefinition]:
        """
        Extract dimension definitions from a dbt model.

        Identifies GROUP BY columns and classifies them as categorical or temporal.

        Args:
            model: The dbt model to extract from

        Returns:
            List of DimensionDefinition objects
        """
        dimensions = []

        # Get columns that are NOT aggregations
        aggregations = self._parse_aggregations(model.sql)
        agg_aliases = {alias for alias, _, _ in aggregations}

        # Get GROUP BY columns or all SELECT columns for simple selects
        group_by_cols = self._extract_group_by_columns(model.sql)
        select_cols = self._extract_select_columns(model.sql)

        # Dimension candidates: GROUP BY columns, or SELECT columns that aren't aggregations
        dim_candidates = group_by_cols if group_by_cols else [c for c in select_cols if c not in agg_aliases]

        # Create a lookup for column descriptions
        column_descs = {col.name: col.description for col in model.columns}

        for col_name in dim_candidates:
            if col_name in agg_aliases:
                continue

            dim_type = self._infer_dimension_type(col_name)

            dimension = DimensionDefinition(
                name=col_name,
                display_name=self._to_display_name(col_name),
                description=column_descs.get(col_name, ""),
                table=model.name,
                column=col_name,
                type=dim_type
            )
            dimensions.append(dimension)

        return dimensions

    def _parse_aggregations(self, sql: str) -> List[Tuple[str, str, str]]:
        """
        Parse aggregation patterns from SQL.

        Returns list of (alias, aggregation_type, source_column) tuples.
        """
        aggregations = []

        # Pattern for standard aggregations: AGG_FUNC(col) as alias
        patterns = [
            # COUNT(DISTINCT col) as alias
            (r'COUNT\s*\(\s*DISTINCT\s+(\w+)\s*\)\s*(?:as\s+)?(\w+)', 'COUNT_DISTINCT'),
            # SUM/COUNT/AVG/MIN/MAX(col) as alias
            (r'(SUM|COUNT|AVG|MIN|MAX)\s*\(\s*(\*|\w+)\s*\)\s*(?:as\s+)?(\w+)', None),
        ]

        # Handle COUNT(DISTINCT)
        for match in re.finditer(patterns[0][0], sql, re.IGNORECASE):
            source_col = match.group(1)
            alias = match.group(2)
            aggregations.append((alias, 'COUNT_DISTINCT', source_col))

        # Handle standard aggregations
        for match in re.finditer(patterns[1][0], sql, re.IGNORECASE):
            agg_type = match.group(1).upper()
            source_col = match.group(2)
            alias = match.group(3)
            aggregations.append((alias, agg_type, source_col))

        return aggregations

    def _extract_group_by_columns(self, sql: str) -> List[str]:
        """Extract column names from GROUP BY clause."""
        # Find GROUP BY clause
        match = re.search(r'GROUP\s+BY\s+(.+?)(?:HAVING|ORDER|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return []

        group_by = match.group(1)

        # Split by comma and extract column names
        columns = []
        for part in group_by.split(','):
            # Clean up and extract just the column name
            part = part.strip()
            # Handle table.column format
            if '.' in part:
                part = part.split('.')[-1]
            # Remove any remaining SQL keywords or numbers
            col_match = re.match(r'^(\w+)', part)
            if col_match:
                columns.append(col_match.group(1))

        return columns

    def _extract_select_columns(self, sql: str) -> List[str]:
        """Extract column names/aliases from SELECT clause."""
        columns = []

        # Find SELECT ... FROM
        match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return columns

        select_part = match.group(1)

        # Split by comma (not inside parentheses)
        parts = []
        depth = 0
        current = []
        for char in select_part:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
        if current:
            parts.append(''.join(current).strip())

        for part in parts:
            # Get alias (after AS) or column name
            if ' as ' in part.lower():
                alias = re.search(r'\s+as\s+(\w+)\s*$', part, re.IGNORECASE)
                if alias:
                    columns.append(alias.group(1))
            else:
                # Just column name
                col_match = re.search(r'^(\w+)', part.strip())
                if col_match:
                    columns.append(col_match.group(1))

        return columns

    def _map_aggregation(self, agg_type: str) -> Optional[AggregationType]:
        """Map SQL aggregation to AggregationType enum."""
        mapping = {
            'SUM': AggregationType.SUM,
            'COUNT': AggregationType.COUNT,
            'COUNT_DISTINCT': AggregationType.COUNT_DISTINCT,
            'AVG': AggregationType.AVG,
            'AVERAGE': AggregationType.AVG,
            'MIN': AggregationType.MIN,
            'MAX': AggregationType.MAX,
        }
        return mapping.get(agg_type.upper())

    def _infer_dimension_type(self, column_name: str) -> DimensionType:
        """Infer dimension type from column name."""
        # Temporal patterns
        temporal_patterns = [
            'date', 'time', 'timestamp', 'month', 'year', 'day', 'week',
            'quarter', 'created', 'updated', 'signup', 'birth', 'order_date',
            'first_', 'last_'
        ]

        name_lower = column_name.lower()
        for pattern in temporal_patterns:
            if pattern in name_lower:
                return DimensionType.TEMPORAL

        return DimensionType.CATEGORICAL

    def _to_display_name(self, name: str) -> str:
        """Convert snake_case name to Title Case display name."""
        words = name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    def generate_semantic_yaml(self, models: List[DbtModel]) -> str:
        """
        Generate semantic layer YAML from dbt models.

        Args:
            models: List of dbt models to convert

        Returns:
            YAML string for the semantic layer
        """
        all_metrics = []
        all_dimensions = []
        seen_metric_names = set()
        seen_dimension_names = set()

        for model in models:
            metrics = self.extract_metrics(model)
            dimensions = self.extract_dimensions(model)

            # Handle duplicate metric names by prefixing with table name
            for metric in metrics:
                name = metric.name
                if name in seen_metric_names:
                    name = f"{model.name}_{metric.name}"
                seen_metric_names.add(name)

                all_metrics.append({
                    "name": name,
                    "display_name": metric.display_name,
                    "description": metric.description,
                    "type": "simple",
                    "calculation": {
                        "table": metric.table,
                        "aggregation": metric.aggregation.value,
                        "column": metric.column
                    }
                })

            # Handle duplicate dimension names
            for dimension in dimensions:
                name = dimension.name
                if name in seen_dimension_names:
                    name = f"{model.name}_{dimension.name}"
                seen_dimension_names.add(name)

                all_dimensions.append({
                    "name": name,
                    "type": dimension.type.value,
                    "table": dimension.table,
                    "column": dimension.column,
                    "description": dimension.description
                })

        # Build the semantic model structure
        semantic_model = {
            "version": "1.0",
            "metrics": all_metrics,
            "dimensions": all_dimensions
        }

        # Generate YAML with header comment
        header = f"""# Auto-generated from dbt models
# Generated at: {datetime.utcnow().isoformat()}
# Source: {self.dbt_path}
#
# WARNING: This file is auto-generated. Manual changes may be overwritten.

"""
        yaml_content = yaml.dump(
            semantic_model,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )

        return header + yaml_content

    def sync(self) -> SyncResult:
        """
        Perform a full sync from dbt models to semantic layer.

        Discovers models, extracts metrics/dimensions, and writes the YAML file.

        Returns:
            SyncResult with counts and timestamp
        """
        # Discover models
        models = self.discover_models()

        # Extract all metrics and dimensions for counting
        total_metrics = 0
        total_dimensions = 0

        for model in models:
            total_metrics += len(self.extract_metrics(model))
            total_dimensions += len(self.extract_dimensions(model))

        # Generate and write YAML
        yaml_content = self.generate_semantic_yaml(models)

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        self.output_path.write_text(yaml_content)

        return SyncResult(
            models_processed=len(models),
            metrics_generated=total_metrics,
            dimensions_generated=total_dimensions,
            timestamp=datetime.utcnow()
        )
