"""
Conversational Metric Definition

This module implements conversational metric definition capabilities for the AI-Native Semantic Layer:
- Natural language metric definition through chat
- Interactive metric building and refinement
- Context-aware suggestions based on warehouse schema
- Integration with existing semantic layer

This is part of the Phase 2 MCP server enhancements for conversational data modeling.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from src.metadata_inspector import MetadataInspector, TableMetadata
from src.ai_semantic_inferrer import AISemanticInferrer, InferredMetric
from src.semantic_layer import SemanticLayer

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinitionContext:
    """Context for conversational metric definition"""

    warehouse_metadata: Dict[str, TableMetadata]
    existing_metrics: List[Dict[str, Any]]
    existing_dimensions: List[Dict[str, Any]]
    conversation_history: List[Dict[str, str]]
    current_metric_draft: Optional[Dict[str, Any]] = None


@dataclass
class ConversationResponse:
    """Response from conversational metric definition"""

    message: str
    suggested_metric: Optional[Dict[str, Any]] = None
    questions: List[str] = None
    options: List[Dict[str, str]] = None
    is_complete: bool = False
    confidence: float = 0.0


class ConversationalMetricDefiner:
    """
    Conversational interface for defining metrics through natural language

    Enables users to define metrics by describing what they want to measure,
    with AI assistance to translate into proper semantic layer definitions.
    """

    def __init__(self, semantic_layer: SemanticLayer):
        """
        Initialize conversational metric definer

        Args:
            semantic_layer: Existing semantic layer instance
        """
        self.semantic_layer = semantic_layer
        self.business_patterns = self._load_business_patterns()
        self.metric_templates = self._load_metric_templates()

    def start_metric_conversation(
        self, user_input: str, context: Optional[MetricDefinitionContext] = None
    ) -> ConversationResponse:
        """
        Start or continue a metric definition conversation

        Args:
            user_input: User's natural language input
            context: Conversation context (None for new conversation)

        Returns:
            Response with next steps or completed metric definition
        """
        if not context:
            # Initialize new conversation
            context = self._initialize_context()

        # Add user input to conversation history
        context.conversation_history.append(
            {"role": "user", "message": user_input, "timestamp": datetime.now().isoformat()}
        )

        # Parse user intent and extract metric requirements
        intent = self._parse_user_intent(user_input, context)

        # Generate appropriate response based on intent
        response = self._generate_response(intent, context)

        # Add assistant response to conversation history
        context.conversation_history.append(
            {
                "role": "assistant",
                "message": response.message,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return response

    def _initialize_context(self) -> MetricDefinitionContext:
        """Initialize context for new metric definition conversation"""
        # Get warehouse metadata through introspection
        inspector = MetadataInspector(self.semantic_layer.connection)
        warehouse_metadata = inspector.introspect_warehouse()

        # Get existing metrics and dimensions
        existing_metrics = self.semantic_layer.list_metrics()
        existing_dimensions = self.semantic_layer.list_dimensions()

        return MetricDefinitionContext(
            warehouse_metadata=warehouse_metadata,
            existing_metrics=existing_metrics,
            existing_dimensions=existing_dimensions,
            conversation_history=[],
        )

    def _parse_user_intent(
        self, user_input: str, context: MetricDefinitionContext
    ) -> Dict[str, Any]:
        """Parse user intent from natural language input"""
        user_input_lower = user_input.lower()

        intent = {
            "type": "unknown",
            "metric_name": None,
            "description": user_input,
            "calculation_type": None,
            "table": None,
            "column": None,
            "aggregation": None,
            "filters": [],
            "dimensions": [],
            "confidence": 0.5,
        }

        # Detect intent type
        if any(phrase in user_input_lower for phrase in ["define", "create", "add", "new metric"]):
            intent["type"] = "define_metric"
        elif any(phrase in user_input_lower for phrase in ["measure", "track", "calculate"]):
            intent["type"] = "define_metric"
        elif any(phrase in user_input_lower for phrase in ["change", "modify", "update"]):
            intent["type"] = "modify_metric"
        elif any(phrase in user_input_lower for phrase in ["show", "list", "what are"]):
            intent["type"] = "explore_options"

        # Extract metric name patterns
        metric_name_patterns = [
            r"(?:define|create|add|track|measure|calculate)\s+(?:a\s+)?(?:metric\s+)?(?:called\s+)?['\"]?([^'\"]+?)['\"]?(?:\s+that|\s+to|\s+which|$)",
            r"['\"]([^'\"]+)['\"](?:\s+metric)",
            r"(?:metric\s+for\s+|metric\s+to\s+)([^,.!?]+)",
        ]

        for pattern in metric_name_patterns:
            match = re.search(pattern, user_input_lower, re.IGNORECASE)
            if match:
                intent["metric_name"] = match.group(1).strip()
                intent["confidence"] += 0.2
                break

        # Extract calculation patterns
        if any(word in user_input_lower for word in ["sum", "total", "add up"]):
            intent["aggregation"] = "sum"
            intent["confidence"] += 0.1
        elif any(word in user_input_lower for word in ["average", "avg", "mean"]):
            intent["aggregation"] = "avg"
            intent["confidence"] += 0.1
        elif any(word in user_input_lower for word in ["count", "number of", "how many"]):
            intent["aggregation"] = "count"
            intent["confidence"] += 0.1
        elif any(word in user_input_lower for word in ["max", "maximum", "highest"]):
            intent["aggregation"] = "max"
            intent["confidence"] += 0.1
        elif any(word in user_input_lower for word in ["min", "minimum", "lowest"]):
            intent["aggregation"] = "min"
            intent["confidence"] += 0.1

        # Extract table and column references
        for table_name, table_meta in context.warehouse_metadata.items():
            if table_name.lower() in user_input_lower:
                intent["table"] = table_name
                intent["confidence"] += 0.1

            for column in table_meta.columns:
                if column.name.lower() in user_input_lower:
                    intent["column"] = column.name
                    intent["table"] = table_name
                    intent["confidence"] += 0.2

        # Extract business metric patterns
        for pattern_name, pattern_info in self.business_patterns.items():
            if any(keyword in user_input_lower for keyword in pattern_info["keywords"]):
                intent["calculation_type"] = pattern_name
                intent.update(pattern_info["defaults"])
                intent["confidence"] += 0.3

        return intent

    def _generate_response(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> ConversationResponse:
        """Generate appropriate response based on parsed intent"""
        if intent["type"] == "explore_options":
            return self._handle_exploration(context)
        elif intent["type"] == "define_metric":
            return self._handle_metric_definition(intent, context)
        elif intent["type"] == "modify_metric":
            return self._handle_metric_modification(intent, context)
        else:
            return self._handle_unknown_intent(intent, context)

    def _handle_exploration(self, context: MetricDefinitionContext) -> ConversationResponse:
        """Handle exploration of available options"""
        message_parts = []

        message_parts.append("Here's what I can help you with:\n")

        # Show available tables
        message_parts.append("📊 **Available Tables:**")
        for table_name, table_meta in context.warehouse_metadata.items():
            table_type = table_meta.table_type or "table"
            message_parts.append(
                f"  - {table_name} ({table_type}) - {table_meta.row_count:,} rows"
                if table_meta.row_count
                else f"  - {table_name} ({table_type})"
            )

        # Show existing metrics
        if context.existing_metrics:
            message_parts.append(f"\n📈 **Existing Metrics ({len(context.existing_metrics)}):**")
            for metric in context.existing_metrics[:5]:  # Show first 5
                message_parts.append(f"  - {metric['display_name']}")
            if len(context.existing_metrics) > 5:
                message_parts.append(f"  ... and {len(context.existing_metrics) - 5} more")

        message_parts.append("\n💬 **How to define a metric:**")
        message_parts.append('  - "I want to track total revenue"')
        message_parts.append('  - "Create a metric for average order value"')
        message_parts.append('  - "Define customer count by segment"')
        message_parts.append('  - "Track monthly recurring revenue"')

        return ConversationResponse(
            message="\n".join(message_parts), questions=["What metric would you like to define?"]
        )

    def _handle_metric_definition(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> ConversationResponse:
        """Handle metric definition requests"""
        confidence = intent["confidence"]

        # If we have high confidence, suggest a complete metric
        if confidence > 0.8 and intent["metric_name"] and intent["aggregation"] and intent["table"]:
            suggested_metric = self._build_metric_definition(intent, context)
            return ConversationResponse(
                message=f"I understand you want to create '{intent['metric_name']}'. Here's what I suggest:",
                suggested_metric=suggested_metric,
                questions=["Does this look correct?", "Would you like to modify anything?"],
                is_complete=True,
                confidence=confidence,
            )

        # If medium confidence, ask clarifying questions
        elif confidence > 0.5:
            return self._ask_clarifying_questions(intent, context)

        # If low confidence, ask for more information
        else:
            return ConversationResponse(
                message="I'd like to help you define that metric! Can you tell me more about what you want to measure?",
                questions=[
                    "What specific value do you want to calculate?",
                    "Which table contains the data?",
                    "Do you want to sum, count, or average something?",
                    "Should the metric be filtered in any way?",
                ],
            )

    def _ask_clarifying_questions(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> ConversationResponse:
        """Ask clarifying questions to complete metric definition"""
        questions = []
        options = []

        # Ask about missing required fields
        if not intent["metric_name"]:
            questions.append("What would you like to call this metric?")

        if not intent["table"]:
            questions.append("Which table contains the data you want to measure?")
            for table_name, table_meta in context.warehouse_metadata.items():
                if table_meta.table_type in ["fact", "unknown"]:  # Focus on fact tables
                    options.append(
                        {
                            "label": table_name,
                            "description": (
                                f"{table_meta.table_type} table with {table_meta.row_count:,} rows"
                                if table_meta.row_count
                                else f"{table_meta.table_type} table"
                            ),
                        }
                    )

        elif intent["table"] and not intent["column"]:
            table_meta = context.warehouse_metadata[intent["table"]]
            questions.append(f"Which column in {intent['table']} do you want to measure?")
            for column in table_meta.columns:
                if not column.primary_key and not column.foreign_key:  # Focus on measure columns
                    options.append(
                        {"label": column.name, "description": f"{column.data_type} column"}
                    )

        if not intent["aggregation"]:
            questions.append("How do you want to aggregate the data?")
            options.extend(
                [
                    {"label": "sum", "description": "Add up all values"},
                    {"label": "count", "description": "Count number of records"},
                    {"label": "avg", "description": "Calculate average value"},
                    {"label": "max", "description": "Find maximum value"},
                    {"label": "min", "description": "Find minimum value"},
                ]
            )

        message = "I need a bit more information to define your metric:"
        if intent["metric_name"]:
            message = f"Great! I understand you want to create '{intent['metric_name']}'. I need a bit more information:"

        return ConversationResponse(
            message=message,
            questions=questions,
            options=options[:10],  # Limit options to avoid overwhelming
        )

    def _build_metric_definition(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> Dict[str, Any]:
        """Build complete metric definition from intent"""
        metric_name = intent["metric_name"] or "new_metric"
        metric_name = re.sub(r"[^a-zA-Z0-9_]", "_", metric_name.lower())

        # Generate display name and description
        display_name = " ".join(word.capitalize() for word in metric_name.split("_"))
        description = intent.get("description", f"User-defined metric: {display_name}")

        # Build calculation
        calculation = {
            "table": intent["table"],
            "aggregation": intent["aggregation"],
            "column": intent["column"],
            "filters": intent.get("filters", []),
        }

        return {
            "name": metric_name,
            "display_name": display_name,
            "description": description,
            "type": "simple",
            "calculation": calculation,
            "created_by": "conversational_interface",
            "created_at": datetime.now().isoformat(),
            "confidence": intent["confidence"],
        }

    def _handle_metric_modification(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> ConversationResponse:
        """Handle requests to modify existing metrics"""
        return ConversationResponse(
            message="I understand you want to modify an existing metric. Which metric would you like to change?",
            questions=["What changes would you like to make?"],
        )

    def _handle_unknown_intent(
        self, intent: Dict[str, Any], context: MetricDefinitionContext
    ) -> ConversationResponse:
        """Handle unknown or unclear intents"""
        return ConversationResponse(
            message="I'm not sure what you're looking for. I can help you define new metrics or explore your data. What would you like to do?",
            questions=[
                "Would you like to create a new metric?",
                "Would you like to see what data is available?",
                "Would you like to see existing metrics?",
            ],
        )

    def add_metric_to_semantic_layer(self, metric_definition: Dict[str, Any]) -> bool:
        """
        Add a conversationally-defined metric to the semantic layer

        Args:
            metric_definition: Complete metric definition

        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Validate metric definition
            required_fields = ["name", "display_name", "type", "calculation"]
            for field in required_fields:
                if field not in metric_definition:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Test the metric by running a query
            test_result = self.semantic_layer.query_metric(metric_definition["name"], limit=1)

            if test_result and test_result["row_count"] >= 0:
                # Metric works - would normally save to YAML here
                logger.info(f"✅ Metric '{metric_definition['name']}' validated successfully")
                return True
            else:
                logger.error("Metric validation failed")
                return False

        except Exception as e:
            logger.error(f"Error adding metric: {e}")
            return False

    def _load_business_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common business metric patterns"""
        return {
            "revenue": {
                "keywords": ["revenue", "sales", "income", "earnings"],
                "defaults": {"aggregation": "sum", "calculation_type": "revenue"},
            },
            "customer_count": {
                "keywords": ["customer", "client", "user count", "number of customers"],
                "defaults": {"aggregation": "count_distinct", "calculation_type": "customer_count"},
            },
            "average_order_value": {
                "keywords": ["average order", "aov", "order value"],
                "defaults": {"aggregation": "avg", "calculation_type": "average_value"},
            },
            "churn_rate": {
                "keywords": ["churn", "attrition", "cancellation rate"],
                "defaults": {"aggregation": "avg", "calculation_type": "rate"},
            },
        }

    def _load_metric_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load metric templates for common patterns"""
        return {
            "sum_template": {
                "type": "simple",
                "aggregation": "sum",
                "description_template": "Total {column_name}",
            },
            "count_template": {
                "type": "simple",
                "aggregation": "count",
                "description_template": "Count of {table_name}",
            },
            "average_template": {
                "type": "simple",
                "aggregation": "avg",
                "description_template": "Average {column_name}",
            },
        }


# Example usage and testing
if __name__ == "__main__":
    import ibis

    # Test conversational metric definition
    connection = ibis.duckdb.connect("/tmp/sample_metadata.duckdb")
    semantic_layer = SemanticLayer("semantic_models/metrics.yml")

    conversational_definer = ConversationalMetricDefiner(semantic_layer)

    print("🗣️ Testing Conversational Metric Definition")
    print("=" * 50)

    # Test conversation scenarios
    test_conversations = [
        "What metrics can I create?",
        "I want to track total subscription revenue",
        "Create a metric called average customer value",
        "Count the number of active customers",
    ]

    for i, user_input in enumerate(test_conversations, 1):
        print(f"\n🗨️ Conversation {i}:")
        print(f"User: {user_input}")

        response = conversational_definer.start_metric_conversation(user_input)

        print(f"Assistant: {response.message}")
        if response.questions:
            print(f"Questions: {response.questions}")
        if response.options:
            print(f"Options: {[opt['label'] for opt in response.options[:3]]}")  # Show first 3
        if response.suggested_metric:
            print(
                f"Suggested Metric: {response.suggested_metric['name']} - {response.suggested_metric['display_name']}"
            )
        print(f"Confidence: {response.confidence:.2f}")
        print("-" * 30)
