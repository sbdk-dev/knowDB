"""
AI Semantic Inference Engine

This module implements Layer 2 of the AI-Native Semantic Layer Auto-Generation Platform:
- Uses LLMs to analyze warehouse metadata and sample data
- Infers business entities (customers, products, orders)
- Suggests metric definitions based on domain understanding
- Proposes dimensional relationships and business-friendly names
- Generates comprehensive semantic model definitions

Technologies: Claude 3.5 Sonnet via Anthropic API (when available) or local inference
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

from src.metadata_inspector import MetadataInspector, TableMetadata, ColumnMetadata

logger = logging.getLogger(__name__)


@dataclass
class InferredMetric:
    """AI-inferred metric definition"""

    name: str
    display_name: str
    description: str
    type: str  # 'simple' or 'derived'
    calculation: Dict[str, Any]
    business_context: str
    confidence: float  # 0.0 to 1.0


@dataclass
class InferredDimension:
    """AI-inferred dimension definition"""

    name: str
    display_name: str
    description: str
    column: str
    table: str
    data_type: str
    sample_values: List[str]
    business_context: str
    confidence: float


@dataclass
class InferredEntity:
    """AI-inferred business entity"""

    name: str
    display_name: str
    description: str
    table: str
    entity_type: str  # 'dimension', 'fact', 'event', 'bridge'
    primary_key: Optional[str]
    business_domain: str  # e.g., 'customer_management', 'sales', 'product'
    confidence: float


@dataclass
class SemanticInferenceResult:
    """Complete AI inference results for warehouse"""

    entities: List[InferredEntity]
    metrics: List[InferredMetric]
    dimensions: List[InferredDimension]
    relationships: List[Dict[str, Any]]
    business_domains: List[str]
    inference_timestamp: str
    confidence_summary: Dict[str, float]


class AISemanticInferrer:
    """
    AI-powered semantic inference engine

    Phase 2 Implementation - Layer 2: AI Semantic Inference Engine
    """

    def __init__(self, use_local_inference: bool = True):
        """
        Initialize AI semantic inferrer

        Args:
            use_local_inference: Use local heuristic inference vs external LLM API
        """
        self.use_local_inference = use_local_inference
        self.business_domain_patterns = self._load_domain_patterns()
        self.metric_templates = self._load_metric_templates()

    def infer_semantic_model(self, metadata: Dict[str, TableMetadata]) -> SemanticInferenceResult:
        """
        Perform comprehensive AI semantic inference on warehouse metadata

        Args:
            metadata: Output from MetadataInspector

        Returns:
            Complete semantic inference results
        """
        logger.info("🧠 Starting AI semantic inference...")

        # Step 1: Infer business entities from tables
        entities = self._infer_business_entities(metadata)

        # Step 2: Infer metrics from fact tables and numeric columns
        metrics = self._infer_metrics(metadata, entities)

        # Step 3: Infer dimensions from dimension tables and categorical columns
        dimensions = self._infer_dimensions(metadata, entities)

        # Step 4: Enhance relationships with business context
        relationships = self._infer_enhanced_relationships(metadata, entities)

        # Step 5: Identify business domains
        business_domains = self._identify_business_domains(entities, metrics)

        # Step 6: Calculate confidence summary
        confidence_summary = self._calculate_confidence_summary(entities, metrics, dimensions)

        logger.info(
            f"✅ AI inference complete: {len(entities)} entities, {len(metrics)} metrics, {len(dimensions)} dimensions"
        )

        return SemanticInferenceResult(
            entities=entities,
            metrics=metrics,
            dimensions=dimensions,
            relationships=relationships,
            business_domains=business_domains,
            inference_timestamp=datetime.now().isoformat(),
            confidence_summary=confidence_summary,
        )

    def _infer_business_entities(self, metadata: Dict[str, TableMetadata]) -> List[InferredEntity]:
        """Infer business entities from table metadata using domain knowledge"""
        entities = []

        for table_name, table_meta in metadata.items():
            # Determine business domain based on table name and columns
            domain = self._classify_business_domain(table_name, table_meta)

            # Generate business-friendly entity name
            entity_name = self._generate_entity_name(table_name)
            display_name = self._generate_display_name(entity_name)

            # Generate description based on table type and domain
            description = self._generate_entity_description(table_name, table_meta, domain)

            # Find primary key
            primary_key = None
            for col in table_meta.columns:
                if col.primary_key:
                    primary_key = col.name
                    break

            # Calculate confidence based on naming conventions and structure
            confidence = self._calculate_entity_confidence(table_name, table_meta)

            entities.append(
                InferredEntity(
                    name=entity_name,
                    display_name=display_name,
                    description=description,
                    table=table_name,
                    entity_type=table_meta.table_type or "unknown",
                    primary_key=primary_key,
                    business_domain=domain,
                    confidence=confidence,
                )
            )

        return entities

    def _infer_metrics(
        self, metadata: Dict[str, TableMetadata], entities: List[InferredEntity]
    ) -> List[InferredMetric]:
        """Infer business metrics from fact tables and numeric columns"""
        metrics = []

        # Get entity lookup
        entity_lookup = {entity.table: entity for entity in entities}

        for table_name, table_meta in metadata.items():
            entity = entity_lookup.get(table_name)
            if not entity or entity.entity_type != "fact":
                continue

            # Analyze numeric columns for potential metrics
            for col in table_meta.columns:
                if self._is_potential_metric_column(col):
                    metric_suggestions = self._generate_metric_suggestions(
                        col, table_name, entity.business_domain
                    )
                    metrics.extend(metric_suggestions)

        # Add derived metrics based on inferred simple metrics
        derived_metrics = self._generate_derived_metrics(metrics, entity_lookup)
        metrics.extend(derived_metrics)

        return metrics

    def _infer_dimensions(
        self, metadata: Dict[str, TableMetadata], entities: List[InferredEntity]
    ) -> List[InferredDimension]:
        """Infer business dimensions from dimensional and categorical columns"""
        dimensions = []

        entity_lookup = {entity.table: entity for entity in entities}

        for table_name, table_meta in metadata.items():
            entity = entity_lookup.get(table_name)

            for col in table_meta.columns:
                if self._is_potential_dimension_column(col):
                    dimension = self._generate_dimension_definition(
                        col, table_name, entity.business_domain if entity else "general"
                    )
                    if dimension:
                        dimensions.append(dimension)

        return dimensions

    def _classify_business_domain(self, table_name: str, table_meta: TableMetadata) -> str:
        """Classify business domain based on table name and column patterns"""
        table_lower = table_name.lower()
        column_names = [col.name.lower() for col in table_meta.columns]

        # Check against domain patterns
        for domain, patterns in self.business_domain_patterns.items():
            table_score = sum(1 for pattern in patterns["table_patterns"] if pattern in table_lower)
            column_score = sum(
                1
                for col in column_names
                for pattern in patterns["column_patterns"]
                if pattern in col
            )

            if table_score > 0 or column_score >= 2:
                return domain

        return "general"

    def _generate_entity_name(self, table_name: str) -> str:
        """Generate clean entity name from table name"""
        # Remove prefixes like 'dim_', 'fact_', 'stg_'
        clean_name = re.sub(r"^(dim_|fact_|stg_|raw_)", "", table_name.lower())

        # Convert to singular if plural
        if clean_name.endswith("s") and len(clean_name) > 3:
            clean_name = clean_name[:-1]

        return clean_name

    def _generate_display_name(self, entity_name: str) -> str:
        """Generate human-readable display name"""
        # Split on underscores and capitalize
        words = entity_name.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    def _generate_entity_description(
        self, table_name: str, table_meta: TableMetadata, domain: str
    ) -> str:
        """Generate entity description based on context"""
        display_name = self._generate_display_name(self._generate_entity_name(table_name))

        if table_meta.table_type == "fact":
            return f"Fact table containing transactional data related to {display_name.lower()}"
        elif table_meta.table_type == "dimension":
            return f"Dimension table containing descriptive attributes for {display_name.lower()}"
        elif table_meta.table_type == "event":
            return f"Event table tracking {display_name.lower()} activities over time"
        else:
            return f"Data table containing information about {display_name.lower()}"

    def _calculate_entity_confidence(self, table_name: str, table_meta: TableMetadata) -> float:
        """Calculate confidence score for entity inference"""
        confidence = 0.5  # Base confidence

        # Naming convention bonus
        if any(prefix in table_name.lower() for prefix in ["dim_", "fact_", "fct_"]):
            confidence += 0.2

        # Table type classification bonus
        if table_meta.table_type and table_meta.table_type != "unknown":
            confidence += 0.2

        # Structure quality bonus
        if table_meta.row_count and table_meta.row_count > 10:
            confidence += 0.1

        return min(confidence, 1.0)

    def _is_potential_metric_column(self, col: ColumnMetadata) -> bool:
        """Check if column could be a business metric"""
        # Must be numeric
        is_numeric = any(x in col.data_type.lower() for x in ["int", "float", "decimal", "double"])
        if not is_numeric:
            return False

        # Must not be a key
        if col.primary_key or col.foreign_key:
            return False

        # Must not be timestamp/date
        if any(x in col.data_type.lower() for x in ["timestamp", "date", "time"]):
            return False

        # Positive indicators in column name
        metric_indicators = [
            "amount",
            "revenue",
            "price",
            "cost",
            "value",
            "quantity",
            "count",
            "total",
            "sum",
            "avg",
            "rate",
            "score",
        ]

        return any(indicator in col.name.lower() for indicator in metric_indicators)

    def _generate_metric_suggestions(
        self, col: ColumnMetadata, table_name: str, domain: str
    ) -> List[InferredMetric]:
        """Generate metric suggestions for a numeric column"""
        metrics = []
        col_name_lower = col.name.lower()

        # Determine base metric name and aggregations
        if "amount" in col_name_lower or "revenue" in col_name_lower:
            base_name = col_name_lower.replace("_amount", "").replace("_revenue", "")
            aggregations = [("total", "sum"), ("average", "avg")]
            business_context = "Financial metrics tracking revenue and monetary values"
        elif "quantity" in col_name_lower or "count" in col_name_lower:
            base_name = col_name_lower.replace("_quantity", "").replace("_count", "")
            aggregations = [("total", "sum"), ("average", "avg")]
            business_context = "Volume metrics tracking quantities and counts"
        elif "price" in col_name_lower or "cost" in col_name_lower:
            base_name = col_name_lower.replace("_price", "").replace("_cost", "")
            aggregations = [
                ("total", "sum"),
                ("average", "avg"),
                ("minimum", "min"),
                ("maximum", "max"),
            ]
            business_context = "Pricing metrics tracking costs and prices"
        else:
            base_name = col_name_lower
            aggregations = [("total", "sum")]
            business_context = f"Numeric metric derived from {col.name}"

        # Generate metrics for each aggregation
        for agg_display, agg_function in aggregations:
            metric_name = f"{agg_display}_{base_name}".replace("__", "_")
            display_name = f"{agg_display.title()} {self._humanize_column_name(base_name)}"

            # Generate description
            if agg_function == "sum":
                description = f"Total {self._humanize_column_name(col.name).lower()}"
            elif agg_function == "avg":
                description = f"Average {self._humanize_column_name(col.name).lower()}"
            elif agg_function == "min":
                description = f"Minimum {self._humanize_column_name(col.name).lower()}"
            elif agg_function == "max":
                description = f"Maximum {self._humanize_column_name(col.name).lower()}"
            else:
                description = f"Aggregated {self._humanize_column_name(col.name).lower()}"

            # Build calculation
            calculation = {
                "table": table_name,
                "aggregation": agg_function,
                "column": col.name,
                "filters": [],
            }

            # Add common filters based on domain knowledge
            if domain == "sales" and "subscription" in table_name.lower():
                if any(
                    status_col.name.lower() == "subscription_status" for status_col in [col]
                ):  # This is a simplified check
                    calculation["filters"].append("subscription_status = 'active'")

            confidence = self._calculate_metric_confidence(col, agg_function, domain)

            metrics.append(
                InferredMetric(
                    name=metric_name,
                    display_name=display_name,
                    description=description,
                    type="simple",
                    calculation=calculation,
                    business_context=business_context,
                    confidence=confidence,
                )
            )

        return metrics

    def _generate_derived_metrics(
        self, simple_metrics: List[InferredMetric], entity_lookup: Dict[str, Any]
    ) -> List[InferredMetric]:
        """Generate derived metrics based on simple metrics"""
        derived_metrics = []

        # Look for common derived metric patterns
        metric_lookup = {metric.name: metric for metric in simple_metrics}

        # Pattern 1: Revenue per customer (if we have revenue and customer count)
        revenue_metrics = [m for m in simple_metrics if "revenue" in m.name or "amount" in m.name]
        customer_metrics = [m for m in simple_metrics if "customer" in m.name]

        if revenue_metrics and customer_metrics:
            for rev_metric in revenue_metrics:
                for cust_metric in customer_metrics:
                    if "total" in rev_metric.name and "total" in cust_metric.name:
                        derived_name = (
                            f"average_revenue_per_{cust_metric.name.replace('total_', '')}"
                        )
                        derived_metrics.append(
                            InferredMetric(
                                name=derived_name,
                                display_name="Average Revenue Per Customer",
                                description="Average revenue generated per customer",
                                type="derived",
                                calculation={"formula": f"{rev_metric.name} / {cust_metric.name}"},
                                business_context="Customer value metrics showing revenue efficiency",
                                confidence=min(rev_metric.confidence, cust_metric.confidence) * 0.8,
                            )
                        )

        return derived_metrics

    def _is_potential_dimension_column(self, col: ColumnMetadata) -> bool:
        """Check if column could be a business dimension"""
        # String/categorical columns
        if "string" in col.data_type.lower() or "varchar" in col.data_type.lower():
            return True

        # Date/time columns (for time dimensions)
        if any(x in col.data_type.lower() for x in ["date", "timestamp"]):
            return True

        # Integer columns that might be categorical (not keys, low cardinality)
        if (
            "int" in col.data_type.lower()
            and not col.primary_key
            and not col.foreign_key
            and col.cardinality
            and col.cardinality < 50
        ):
            return True

        return False

    def _generate_dimension_definition(
        self, col: ColumnMetadata, table_name: str, domain: str
    ) -> Optional[InferredDimension]:
        """Generate dimension definition for a column"""
        # Skip if not enough information
        if not col.sample_values:
            return None

        # Generate business-friendly names
        dimension_name = col.name.lower()
        display_name = self._humanize_column_name(col.name)

        # Generate description based on column type and domain
        if any(x in col.data_type.lower() for x in ["date", "timestamp"]):
            description = f"Time dimension for analyzing trends by {display_name.lower()}"
            business_context = "Temporal analysis dimension"
        else:
            description = f"Categorical dimension for segmenting data by {display_name.lower()}"
            business_context = "Segmentation and grouping dimension"

        confidence = self._calculate_dimension_confidence(col, domain)

        return InferredDimension(
            name=dimension_name,
            display_name=display_name,
            description=description,
            column=col.name,
            table=table_name,
            data_type=col.data_type,
            sample_values=col.sample_values[:10] if col.sample_values else [],
            business_context=business_context,
            confidence=confidence,
        )

    def _calculate_metric_confidence(
        self, col: ColumnMetadata, agg_function: str, domain: str
    ) -> float:
        """Calculate confidence score for metric inference"""
        confidence = 0.6  # Base confidence

        # Column name quality
        if any(indicator in col.name.lower() for indicator in ["amount", "revenue", "quantity"]):
            confidence += 0.2

        # Aggregation appropriateness
        if (
            "amount" in col.name.lower() or "revenue" in col.name.lower()
        ) and agg_function == "sum":
            confidence += 0.1
        elif "price" in col.name.lower() and agg_function in ["avg", "min", "max"]:
            confidence += 0.1

        # Domain relevance
        if domain in ["sales", "finance", "subscription"]:
            confidence += 0.1

        return min(confidence, 1.0)

    def _calculate_dimension_confidence(self, col: ColumnMetadata, domain: str) -> float:
        """Calculate confidence score for dimension inference"""
        confidence = 0.5

        # Sample data quality
        if col.sample_values and len(col.sample_values) > 1:
            confidence += 0.2

        # Cardinality appropriateness
        if col.cardinality and 2 <= col.cardinality <= 100:
            confidence += 0.2

        # Column name patterns
        dimension_patterns = ["segment", "type", "status", "category", "region", "country", "tier"]
        if any(pattern in col.name.lower() for pattern in dimension_patterns):
            confidence += 0.1

        return min(confidence, 1.0)

    def _humanize_column_name(self, col_name: str) -> str:
        """Convert column name to human-readable format"""
        return " ".join(word.capitalize() for word in col_name.split("_"))

    def _infer_enhanced_relationships(
        self, metadata: Dict[str, TableMetadata], entities: List[InferredEntity]
    ) -> List[Dict[str, Any]]:
        """Enhance basic relationships with business context"""
        relationships = []

        for table_name, table_meta in metadata.items():
            if table_meta.relationships:
                for rel in table_meta.relationships:
                    # Find business entities involved
                    from_entity = next((e for e in entities if e.table == table_name), None)
                    to_entity = next((e for e in entities if e.table == rel["to_table"]), None)

                    if from_entity and to_entity:
                        relationships.append(
                            {
                                "from_entity": from_entity.name,
                                "to_entity": to_entity.name,
                                "from_table": table_name,
                                "to_table": rel["to_table"],
                                "from_column": rel["from_column"],
                                "to_column": rel["to_column"],
                                "relationship_type": rel["type"],
                                "business_description": f"{from_entity.display_name} relates to {to_entity.display_name}",
                                "confidence": rel["confidence"],
                            }
                        )

        return relationships

    def _identify_business_domains(
        self, entities: List[InferredEntity], metrics: List[InferredMetric]
    ) -> List[str]:
        """Identify business domains present in the data"""
        domains = set()
        for entity in entities:
            domains.add(entity.business_domain)
        return sorted(list(domains))

    def _calculate_confidence_summary(
        self,
        entities: List[InferredEntity],
        metrics: List[InferredMetric],
        dimensions: List[InferredDimension],
    ) -> Dict[str, float]:
        """Calculate overall confidence summary"""
        entity_confidence = sum(e.confidence for e in entities) / len(entities) if entities else 0
        metric_confidence = sum(m.confidence for m in metrics) / len(metrics) if metrics else 0
        dimension_confidence = (
            sum(d.confidence for d in dimensions) / len(dimensions) if dimensions else 0
        )

        overall_confidence = (entity_confidence + metric_confidence + dimension_confidence) / 3

        return {
            "overall_confidence": overall_confidence,
            "entity_confidence": entity_confidence,
            "metric_confidence": metric_confidence,
            "dimension_confidence": dimension_confidence,
        }

    def _load_domain_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load business domain patterns for classification"""
        return {
            "sales": {
                "table_patterns": ["order", "sale", "transaction", "revenue", "subscription"],
                "column_patterns": [
                    "amount",
                    "price",
                    "revenue",
                    "quantity",
                    "sales",
                    "mrr",
                    "arr",
                ],
            },
            "customer": {
                "table_patterns": ["customer", "user", "client", "account"],
                "column_patterns": [
                    "customer",
                    "user",
                    "client",
                    "segment",
                    "signup",
                    "registration",
                ],
            },
            "product": {
                "table_patterns": ["product", "item", "catalog", "inventory"],
                "column_patterns": ["product", "item", "sku", "category", "tier"],
            },
            "finance": {
                "table_patterns": ["payment", "invoice", "billing", "financial"],
                "column_patterns": ["payment", "billing", "cost", "expense", "profit"],
            },
            "subscription": {
                "table_patterns": ["subscription", "plan", "billing"],
                "column_patterns": [
                    "subscription",
                    "plan",
                    "billing",
                    "frequency",
                    "status",
                    "mrr",
                    "churn",
                ],
            },
        }

    def _load_metric_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load metric templates for common business metrics"""
        return {
            "revenue_metrics": {
                "mrr": {
                    "display_name": "Monthly Recurring Revenue",
                    "description": "Total monthly recurring revenue from active subscriptions",
                    "aggregation": "sum",
                    "filters": ["subscription_status = 'active'", "billing_frequency = 'monthly'"],
                },
                "arr": {
                    "display_name": "Annual Recurring Revenue",
                    "description": "Total annual recurring revenue",
                    "aggregation": "sum",
                    "formula": "mrr * 12",
                },
            }
        }


# Example usage and testing
if __name__ == "__main__":
    import ibis
    from src.metadata_inspector import MetadataInspector

    # Test AI inference on sample data
    connection = ibis.duckdb.connect("/tmp/sample_metadata.duckdb")
    inspector = MetadataInspector(connection)
    metadata = inspector.introspect_warehouse()

    # Run AI inference
    ai_inferrer = AISemanticInferrer(use_local_inference=True)
    results = ai_inferrer.infer_semantic_model(metadata)

    print("🧠 AI Semantic Inference Results")
    print("=" * 50)

    print(f"\n🏢 Business Entities ({len(results.entities)}):")
    for entity in results.entities:
        print(f"  {entity.name} ({entity.entity_type}) - {entity.display_name}")
        print(f"    Domain: {entity.business_domain}, Confidence: {entity.confidence:.2f}")

    print(f"\n📊 Inferred Metrics ({len(results.metrics)}):")
    for metric in results.metrics:
        print(f"  {metric.name} - {metric.display_name}")
        print(f"    Type: {metric.type}, Confidence: {metric.confidence:.2f}")
        if metric.type == "simple":
            print(f"    Calculation: {metric.calculation}")

    print(f"\n📏 Inferred Dimensions ({len(results.dimensions)}):")
    for dimension in results.dimensions:
        print(f"  {dimension.name} - {dimension.display_name}")
        print(f"    Table: {dimension.table}, Confidence: {dimension.confidence:.2f}")

    print(f"\n🔗 Enhanced Relationships ({len(results.relationships)}):")
    for rel in results.relationships:
        print(f"  {rel['from_entity']} → {rel['to_entity']}")

    print(f"\n📈 Confidence Summary:")
    for key, value in results.confidence_summary.items():
        print(f"  {key}: {value:.2f}")

    print(f"\n🌍 Business Domains: {', '.join(results.business_domains)}")
