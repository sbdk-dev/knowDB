"""
Warehouse Metadata Intelligence Engine

This module implements Layer 1 of the AI-Native Semantic Layer Auto-Generation Platform:
- Introspects warehouse metadata (tables, columns, types, keys, constraints)
- Extracts foreign key relationships and patterns
- Detects entity types (fact tables, dimension tables, event tables)
- Provides structured metadata for AI inference

Inspired by Droughty's approach but extended for semantic layer generation.
"""

import ibis
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class ColumnMetadata:
    """Metadata about a database column"""

    name: str
    data_type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: Optional[str] = None  # "table.column" if FK
    description: Optional[str] = None
    sample_values: List[Any] = None
    cardinality: Optional[int] = None  # Estimated unique values


@dataclass
class TableMetadata:
    """Metadata about a database table"""

    name: str
    schema: str
    columns: List[ColumnMetadata]
    row_count: Optional[int] = None
    table_type: Optional[str] = None  # 'fact', 'dimension', 'event', 'bridge'
    description: Optional[str] = None
    relationships: List[Dict] = None  # Inferred relationships to other tables
    suggested_metrics: List[Dict] = None  # AI-suggested metrics


@dataclass
class RelationshipMetadata:
    """Metadata about table relationships"""

    from_table: str
    to_table: str
    from_column: str
    to_column: str
    relationship_type: str  # 'one_to_one', 'one_to_many', 'many_to_many'
    confidence: float  # 0.0 to 1.0 - how confident we are in this relationship


class MetadataInspector:
    """
    Introspects warehouse metadata to understand schema structure

    Phase 2 Implementation - Layer 1: Warehouse Metadata Intelligence Engine
    """

    def __init__(self, connection: ibis.BaseBackend):
        """
        Initialize metadata inspector

        Args:
            connection: Ibis connection to database
        """
        self.connection = connection
        self._cache = {}

    def introspect_warehouse(
        self, tables: Optional[List[str]] = None, sample_size: int = 1000
    ) -> Dict[str, TableMetadata]:
        """
        Comprehensive warehouse introspection

        Args:
            tables: Specific tables to inspect (if None, inspects all)
            sample_size: Number of sample rows to analyze per table

        Returns:
            Dict mapping table names to TableMetadata
        """
        logger.info("🔍 Starting warehouse metadata introspection...")

        # Get list of tables to inspect
        if tables is None:
            tables = self._get_all_tables()

        metadata = {}

        for table_name in tables:
            logger.info(f"Inspecting table: {table_name}")
            try:
                table_meta = self._introspect_table(table_name, sample_size)
                metadata[table_name] = table_meta
            except Exception as e:
                logger.warning(f"Failed to inspect table {table_name}: {e}")

        # Infer relationships between tables
        logger.info("🔗 Inferring table relationships...")
        relationships = self._infer_relationships(metadata)

        # Add relationships to table metadata
        for rel in relationships:
            if rel.from_table in metadata:
                if metadata[rel.from_table].relationships is None:
                    metadata[rel.from_table].relationships = []
                metadata[rel.from_table].relationships.append(
                    {
                        "to_table": rel.to_table,
                        "from_column": rel.from_column,
                        "to_column": rel.to_column,
                        "type": rel.relationship_type,
                        "confidence": rel.confidence,
                    }
                )

        # Classify table types (fact vs dimension)
        logger.info("📋 Classifying table types...")
        for table_name, table_meta in metadata.items():
            table_meta.table_type = self._classify_table_type(table_meta, metadata)

        logger.info(f"✅ Introspection complete: {len(metadata)} tables analyzed")
        return metadata

    def _get_all_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        try:
            # For DuckDB, list all tables
            tables = self.connection.list_tables()
            logger.info(f"Found {len(tables)} tables: {tables}")
            return tables
        except Exception as e:
            logger.error(f"Failed to get table list: {e}")
            return []

    def _introspect_table(self, table_name: str, sample_size: int) -> TableMetadata:
        """
        Introspect a specific table

        Args:
            table_name: Name of table to inspect
            sample_size: Number of sample rows to analyze

        Returns:
            TableMetadata object
        """
        table = self.connection.table(table_name)

        # Get table schema
        schema = table.schema()

        # Get row count
        try:
            row_count = table.count().execute()
        except:
            row_count = None

        # Analyze each column
        columns = []
        for col_name in schema.names:
            col_type = str(schema[col_name])

            # Determine if nullable (simplified - assume all nullable unless specified)
            nullable = True

            # Sample data for analysis
            sample_values = self._sample_column_values(table, col_name, sample_size)

            # Estimate cardinality
            cardinality = self._estimate_cardinality(table, col_name)

            # Check if appears to be primary key
            primary_key = self._is_likely_primary_key(col_name, col_type, cardinality, row_count)

            # Check if appears to be foreign key
            foreign_key = self._infer_foreign_key(col_name, col_type)

            columns.append(
                ColumnMetadata(
                    name=col_name,
                    data_type=col_type,
                    nullable=nullable,
                    primary_key=primary_key,
                    foreign_key=foreign_key,
                    sample_values=sample_values,
                    cardinality=cardinality,
                )
            )

        return TableMetadata(
            name=table_name,
            schema="main",  # Default schema for DuckDB
            columns=columns,
            row_count=row_count,
            relationships=[],
            suggested_metrics=[],
        )

    def _sample_column_values(
        self, table: ibis.Table, col_name: str, sample_size: int
    ) -> List[Any]:
        """Sample values from a column for analysis"""
        try:
            # Get sample of distinct values using proper Ibis syntax
            sample_query = table.select(col_name).distinct().limit(min(sample_size, 50))
            sample_df = sample_query.execute()
            return (
                sample_df[col_name].tolist()
                if hasattr(sample_df[col_name], "tolist")
                else list(sample_df[col_name])
            )
        except Exception as e:
            logger.warning(f"Failed to sample column {col_name}: {e}")
            return []

    def _estimate_cardinality(self, table: ibis.Table, col_name: str) -> Optional[int]:
        """Estimate number of distinct values in column"""
        try:
            cardinality_query = table.select(table[col_name].nunique().name("cardinality"))
            cardinality = cardinality_query.execute()["cardinality"].iloc[0]
            return int(cardinality) if cardinality is not None else None
        except Exception as e:
            logger.warning(f"Failed to estimate cardinality for {col_name}: {e}")
            return None

    def _is_likely_primary_key(
        self, col_name: str, col_type: str, cardinality: Optional[int], row_count: Optional[int]
    ) -> bool:
        """
        Heuristically determine if column is likely a primary key

        Conservative approach: Only consider columns named 'id' or ending with '_id'
        that also have appropriate data types and very high uniqueness
        """
        if not col_name or not col_type:
            return False

        # Conservative name patterns - only actual ID columns
        name_matches_pk = col_name.lower() == "id" or (
            col_name.lower().endswith("_id")
            and col_name.lower()
            in ["subscription_id", "customer_id", "user_id", "order_id", "product_id"]
        )

        # Must be integer or UUID type
        type_matches_pk = "int" in col_type.lower() or "uuid" in col_type.lower()

        # Very high cardinality (99%+ unique, not 95%)
        cardinality_indicator = False
        if cardinality and row_count and row_count > 10:  # Only for reasonable sample sizes
            uniqueness_ratio = cardinality / row_count
            cardinality_indicator = uniqueness_ratio > 0.99  # 99%+ unique

        # Must have name pattern AND type AND high cardinality
        return name_matches_pk and type_matches_pk and cardinality_indicator

    def _infer_foreign_key(self, col_name: str, col_type: str) -> Optional[str]:
        """
        Heuristically infer foreign key relationships

        Returns:
            String in format "table.column" if FK detected, None otherwise
        """
        if not col_name:
            return None

        # Pattern: customer_id likely references customers.id
        if col_name.lower().endswith("_id") and col_name.lower() != "id":
            referenced_table = col_name.lower()[:-3] + "s"  # customer_id -> customers
            return f"{referenced_table}.id"

        # Pattern: customer_key likely references customers.customer_key
        if col_name.lower().endswith("_key"):
            referenced_table = col_name.lower()[:-4] + "s"
            return f"{referenced_table}.{col_name.lower()}"

        return None

    def _infer_relationships(
        self, metadata: Dict[str, TableMetadata]
    ) -> List[RelationshipMetadata]:
        """
        Infer relationships between tables based on column patterns

        Args:
            metadata: Dict of table metadata

        Returns:
            List of inferred relationships
        """
        relationships = []

        for table_name, table_meta in metadata.items():
            for column in table_meta.columns:
                if column.foreign_key:
                    # Parse foreign key reference
                    try:
                        ref_table, ref_column = column.foreign_key.split(".")

                        # Check if referenced table exists
                        if ref_table in metadata:
                            # Determine relationship type based on cardinality
                            rel_type = self._determine_relationship_type(
                                table_meta, column, metadata[ref_table], ref_column
                            )

                            # Calculate confidence based on naming conventions
                            confidence = self._calculate_relationship_confidence(
                                column.name, ref_table, ref_column
                            )

                            relationships.append(
                                RelationshipMetadata(
                                    from_table=table_name,
                                    to_table=ref_table,
                                    from_column=column.name,
                                    to_column=ref_column,
                                    relationship_type=rel_type,
                                    confidence=confidence,
                                )
                            )
                    except ValueError:
                        logger.warning(f"Invalid foreign key format: {column.foreign_key}")

        return relationships

    def _determine_relationship_type(
        self,
        from_table: TableMetadata,
        from_column: ColumnMetadata,
        to_table: TableMetadata,
        to_column: str,
    ) -> str:
        """Determine relationship type based on cardinality"""
        # Simplified: assume most relationships are many-to-one
        # In practice, would analyze cardinality ratios
        return "many_to_one"

    def _calculate_relationship_confidence(
        self, column_name: str, ref_table: str, ref_column: str
    ) -> float:
        """Calculate confidence in relationship based on naming patterns"""
        confidence = 0.5  # Base confidence

        # Strong naming convention match
        if column_name.lower() == f"{ref_table.rstrip('s')}_id":
            confidence += 0.3

        # Column references 'id' column in target
        if ref_column == "id":
            confidence += 0.2

        return min(confidence, 1.0)

    def _classify_table_type(
        self, table_meta: TableMetadata, all_metadata: Dict[str, TableMetadata]
    ) -> str:
        """
        Classify table as fact, dimension, event, or bridge table

        Heuristics:
        - Fact tables: Many foreign keys, numeric measures, high row counts
        - Dimension tables: Primary key, descriptive attributes, lower row counts
        - Event tables: Timestamp columns, high row counts, often append-only
        - Bridge tables: Mostly foreign keys, resolve many-to-many relationships
        """
        if not table_meta.columns:
            return "unknown"

        # Count different column types
        fk_count = sum(1 for col in table_meta.columns if col.foreign_key)
        pk_count = sum(1 for col in table_meta.columns if col.primary_key)
        numeric_count = sum(
            1
            for col in table_meta.columns
            if "int" in col.data_type.lower()
            or "float" in col.data_type.lower()
            or "decimal" in col.data_type.lower()
        )
        timestamp_count = sum(
            1
            for col in table_meta.columns
            if "timestamp" in col.data_type.lower() or "date" in col.data_type.lower()
        )

        total_columns = len(table_meta.columns)
        fk_ratio = fk_count / total_columns if total_columns > 0 else 0

        # Bridge table: mostly foreign keys
        if fk_ratio > 0.6 and total_columns <= 5:
            return "bridge"

        # Fact table: multiple FKs + numeric measures OR just high row count with FKs
        if (fk_count >= 2 and numeric_count >= 1) or (
            fk_count >= 1
            and table_meta.row_count
            and table_meta.row_count > 100
            and numeric_count >= 1
        ):
            return "fact"

        # Event table: timestamps + high row count + append pattern
        if (
            timestamp_count >= 1
            and table_meta.row_count
            and table_meta.row_count > 10000
            and any(
                "created" in col.name.lower() or "occurred" in col.name.lower()
                for col in table_meta.columns
            )
        ):
            return "event"

        # Dimension table: primary key + descriptive attributes
        if pk_count >= 1 and fk_count <= 1:
            return "dimension"

        return "unknown"

    def generate_warehouse_summary(self, metadata: Dict[str, TableMetadata]) -> Dict[str, Any]:
        """
        Generate high-level summary of warehouse structure

        Returns:
            Summary dictionary with warehouse statistics and insights
        """
        total_tables = len(metadata)
        total_columns = sum(len(table.columns) for table in metadata.values())
        total_rows = sum(table.row_count or 0 for table in metadata.values())

        # Count table types
        table_types = {}
        for table in metadata.values():
            table_type = table.table_type or "unknown"
            table_types[table_type] = table_types.get(table_type, 0) + 1

        # Count relationships
        total_relationships = sum(len(table.relationships or []) for table in metadata.values())

        # Find potential metrics (numeric columns in fact tables)
        potential_metrics = []
        for table_name, table in metadata.items():
            if table.table_type == "fact":
                for col in table.columns:
                    # Look for numeric columns that aren't keys
                    is_numeric = any(
                        x in col.data_type.lower() for x in ["int", "float", "decimal", "double"]
                    )
                    is_not_key = not col.primary_key and not col.foreign_key

                    # Also exclude timestamp/date columns
                    is_not_timestamp = not any(
                        x in col.data_type.lower() for x in ["timestamp", "date", "time"]
                    )

                    if is_numeric and is_not_key and is_not_timestamp:
                        # Suggest aggregations based on column name patterns
                        suggested_aggregations = ["sum", "count"]
                        if "amount" in col.name.lower() or "revenue" in col.name.lower():
                            suggested_aggregations = ["sum", "avg"]
                        elif "quantity" in col.name.lower() or "count" in col.name.lower():
                            suggested_aggregations = ["sum", "avg", "count"]

                        potential_metrics.append(
                            {
                                "table": table_name,
                                "column": col.name,
                                "type": col.data_type,
                                "suggested_aggregations": suggested_aggregations,
                            }
                        )

        return {
            "warehouse_stats": {
                "total_tables": total_tables,
                "total_columns": total_columns,
                "total_rows": total_rows,
                "total_relationships": total_relationships,
            },
            "table_types": table_types,
            "potential_metrics": potential_metrics,
            "introspection_timestamp": datetime.now().isoformat(),
        }


# Example usage and testing
if __name__ == "__main__":
    import ibis

    # Connect to sample database (use copy to avoid locks)
    connection = ibis.duckdb.connect("/tmp/sample_metadata.duckdb")

    # Initialize inspector
    inspector = MetadataInspector(connection)

    # Introspect warehouse
    metadata = inspector.introspect_warehouse()

    # Generate summary
    summary = inspector.generate_warehouse_summary(metadata)

    print("🔍 Warehouse Introspection Results")
    print("=" * 50)
    print(f"Tables: {summary['warehouse_stats']['total_tables']}")
    print(f"Columns: {summary['warehouse_stats']['total_columns']}")
    print(f"Rows: {summary['warehouse_stats']['total_rows']:,}")
    print(f"Relationships: {summary['warehouse_stats']['total_relationships']}")

    print(f"\n📋 Table Types:")
    for table_type, count in summary["table_types"].items():
        print(f"  {table_type}: {count}")

    print(f"\n📊 Potential Metrics Found: {len(summary['potential_metrics'])}")
    for metric in summary["potential_metrics"][:5]:  # Show first 5
        print(f"  {metric['table']}.{metric['column']} ({metric['type']})")

    print(f"\n🔗 Table Details:")
    for table_name, table_meta in metadata.items():
        print(f"\n{table_name} ({table_meta.table_type}):")
        print(f"  Columns: {len(table_meta.columns)}")
        print(f"  Rows: {table_meta.row_count:,}" if table_meta.row_count else "  Rows: Unknown")
        if table_meta.relationships:
            print(f"  Relationships: {len(table_meta.relationships)}")
            for rel in table_meta.relationships:
                print(f"    → {rel['to_table']} via {rel['from_column']}")
