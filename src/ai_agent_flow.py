"""
AI Agent Flow - WrenAI-Inspired Multi-Agent Architecture

This module implements a multi-agent system for conversational business intelligence:
1. Query Understanding Agent - Parse natural language intent
2. Semantic Retriever Agent - Find relevant metrics/dimensions using RAG
3. Query Planning Agent - Plan the semantic query
4. SQL Generator Agent - Generate SQL from semantic plan
5. Result Interpreter Agent - Format and explain results
6. Conversation Manager - Maintain context across queries

Architecture inspired by WrenAI: https://github.com/Canner/WrenAI
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re

from src.semantic_layer import SemanticLayer, SemanticLayerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the multi-agent system"""
    QUERY_UNDERSTANDING = "query_understanding"
    SEMANTIC_RETRIEVER = "semantic_retriever"
    QUERY_PLANNER = "query_planner"
    SQL_GENERATOR = "sql_generator"
    RESULT_INTERPRETER = "result_interpreter"
    CONVERSATION_MANAGER = "conversation_manager"


class QueryIntent(Enum):
    """Detected query intents"""
    METRIC_QUERY = "metric_query"  # "What is our MRR?"
    TREND_ANALYSIS = "trend_analysis"  # "How is MRR changing over time?"
    COMPARISON = "comparison"  # "Compare MRR by segment"
    COHORT_ANALYSIS = "cohort_analysis"  # "Show signup cohorts"
    AGGREGATION = "aggregation"  # "Sum of all revenue"
    FILTERING = "filtering"  # "Show customers in USA"
    TOP_N = "top_n"  # "Top 10 customers"
    UNKNOWN = "unknown"


@dataclass
class ConversationContext:
    """Maintains context across multiple queries"""
    session_id: str
    query_history: List[Dict] = field(default_factory=list)
    semantic_context: Dict[str, Any] = field(default_factory=dict)
    last_metrics: List[str] = field(default_factory=list)
    last_dimensions: List[str] = field(default_factory=list)
    last_intent: Optional[QueryIntent] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QueryUnderstanding:
    """Parsed understanding of user query"""
    raw_query: str
    intent: QueryIntent
    entities: Dict[str, List[str]]  # metrics, dimensions, filters
    temporal_scope: Optional[str] = None  # "last month", "this year", etc.
    confidence: float = 0.0


@dataclass
class SemanticPlan:
    """Semantic query plan before SQL generation"""
    metrics: List[str]
    dimensions: List[str]
    filters: List[str]
    order_by: Optional[str] = None
    limit: Optional[int] = None
    time_range: Optional[Dict] = None
    explanation: str = ""


@dataclass
class AgentMessage:
    """Message passed between agents"""
    agent_type: AgentType
    content: Any
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class QueryUnderstandingAgent:
    """
    Agent 1: Parse natural language query to understand intent

    Uses pattern matching and keyword detection to identify:
    - Query intent (metric, trend, comparison, etc.)
    - Mentioned entities (metrics, dimensions, time periods)
    - Temporal scope (last month, this quarter, etc.)
    """

    def __init__(self, semantic_layer: SemanticLayer):
        self.semantic_layer = semantic_layer
        self.metrics = [m['name'] for m in semantic_layer.list_metrics()]
        self.dimensions = [d['name'] for d in semantic_layer.list_dimensions()]

        # Intent detection patterns
        self.intent_patterns = {
            QueryIntent.TREND_ANALYSIS: [
                r'\b(trend|trending|changing|change|over time|evolution|growth)\b',
                r'\b(how\s+(?:is|are|has|have).*(?:changing|changed|evolved|growing))\b',
                r'\b(track|monitor)\b',
            ],
            QueryIntent.COMPARISON: [
                r'\b(compare|comparison|versus|vs|by|across|between)\b',
                r'\b(breakdown|split|segment)\b',
            ],
            QueryIntent.COHORT_ANALYSIS: [
                r'\b(cohort|signup|retention|churn)\b',
            ],
            QueryIntent.TOP_N: [
                r'\b(top|bottom|best|worst|highest|lowest)\s+\d+\b',
                r'\b(leading|lagging)\b',
            ],
            QueryIntent.FILTERING: [
                r'\b(where|filter|only|specific|in\s+[A-Z]{2,})\b',
            ],
        }

    def process(self, query: str, context: ConversationContext) -> QueryUnderstanding:
        """Parse and understand the user query"""
        logger.info(f"[QueryUnderstandingAgent] Processing: {query}")

        # Detect intent
        intent = self._detect_intent(query)

        # Extract entities
        entities = self._extract_entities(query)

        # Detect temporal scope
        temporal_scope = self._detect_temporal_scope(query)

        # Calculate confidence based on entity matches
        confidence = self._calculate_confidence(entities)

        understanding = QueryUnderstanding(
            raw_query=query,
            intent=intent,
            entities=entities,
            temporal_scope=temporal_scope,
            confidence=confidence
        )

        logger.info(f"[QueryUnderstandingAgent] Intent: {intent.value}, "
                   f"Confidence: {confidence:.2f}, Entities: {entities}")

        return understanding

    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent using pattern matching"""
        query_lower = query.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        # Default to metric query if no specific intent detected
        return QueryIntent.METRIC_QUERY

    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract mentioned metrics, dimensions, and filters"""
        query_lower = query.lower()

        entities = {
            'metrics': [],
            'dimensions': [],
            'filters': []
        }

        # Match metrics using fuzzy matching
        for metric in self.metrics:
            metric_parts = metric.split('_')
            # Check if any significant part of metric name is in query
            for part in metric_parts:
                if len(part) > 3 and part in query_lower:
                    entities['metrics'].append(metric)
                    break

        # Match dimensions
        for dimension in self.dimensions:
            dimension_parts = dimension.split('_')
            for part in dimension_parts:
                if len(part) > 3 and part in query_lower:
                    entities['dimensions'].append(dimension)
                    break

        # Detect time dimensions if temporal words present
        temporal_keywords = ['time', 'month', 'year', 'quarter', 'trend', 'over', 'changing']
        if any(keyword in query_lower for keyword in temporal_keywords):
            temporal_dims = [d for d in self.dimensions if 'month' in d or 'year' in d or 'quarter' in d]
            for dim in temporal_dims:
                if dim not in entities['dimensions']:
                    entities['dimensions'].append(dim)

        return entities

    def _detect_temporal_scope(self, query: str) -> Optional[str]:
        """Detect temporal scope in query"""
        query_lower = query.lower()

        temporal_patterns = {
            'last_month': r'\b(last|previous)\s+month\b',
            'this_month': r'\bthis\s+month\b',
            'last_quarter': r'\b(last|previous)\s+quarter\b',
            'this_year': r'\bthis\s+year\b',
            'last_year': r'\b(last|previous)\s+year\b',
        }

        for scope, pattern in temporal_patterns.items():
            if re.search(pattern, query_lower):
                return scope

        return None

    def _calculate_confidence(self, entities: Dict[str, List[str]]) -> float:
        """Calculate confidence score based on entity matches"""
        total_entities = sum(len(v) for v in entities.values())
        if total_entities == 0:
            return 0.3  # Low confidence if no entities found

        # Higher confidence with more entity matches
        return min(0.5 + (total_entities * 0.1), 1.0)


class SemanticRetrieverAgent:
    """
    Agent 2: Use RAG to find relevant metrics and dimensions

    Uses semantic similarity to find the most relevant:
    - Metrics matching the query intent
    - Dimensions for grouping/filtering
    - Related canonical datasets
    """

    def __init__(self, semantic_layer: SemanticLayer):
        self.semantic_layer = semantic_layer
        self.metric_definitions = semantic_layer.list_metrics()
        self.dimension_definitions = semantic_layer.list_dimensions()

    def process(self, understanding: QueryUnderstanding,
                context: ConversationContext) -> Dict[str, Any]:
        """Retrieve relevant semantic information"""
        logger.info(f"[SemanticRetrieverAgent] Retrieving for intent: {understanding.intent}")

        # If entities already identified, use them
        if understanding.entities['metrics']:
            metrics = understanding.entities['metrics']
        else:
            # Fallback to intent-based retrieval
            metrics = self._retrieve_metrics_by_intent(understanding.intent)

        if understanding.entities['dimensions']:
            dimensions = understanding.entities['dimensions']
        else:
            dimensions = self._retrieve_dimensions_by_intent(understanding.intent)

        # Get canonical datasets that might be relevant
        relevant_datasets = self._find_relevant_datasets(metrics, dimensions)

        retrieval_result = {
            'metrics': metrics,
            'dimensions': dimensions,
            'datasets': relevant_datasets,
            'context': self._build_semantic_context(metrics, dimensions)
        }

        logger.info(f"[SemanticRetrieverAgent] Retrieved: {len(metrics)} metrics, "
                   f"{len(dimensions)} dimensions, {len(relevant_datasets)} datasets")

        return retrieval_result

    def _retrieve_metrics_by_intent(self, intent: QueryIntent) -> List[str]:
        """Retrieve relevant metrics based on query intent"""
        intent_metric_mapping = {
            QueryIntent.TREND_ANALYSIS: ['monthly_mrr', 'monthly_customer_count'],
            QueryIntent.METRIC_QUERY: ['total_mrr', 'active_customers'],
            QueryIntent.COHORT_ANALYSIS: ['active_customers', 'customer_ltv'],
            QueryIntent.COMPARISON: ['total_mrr', 'arpu'],
        }

        return intent_metric_mapping.get(intent, ['total_mrr'])

    def _retrieve_dimensions_by_intent(self, intent: QueryIntent) -> List[str]:
        """Retrieve relevant dimensions based on query intent"""
        intent_dimension_mapping = {
            QueryIntent.TREND_ANALYSIS: ['snapshot_month'],
            QueryIntent.COMPARISON: ['customer_segment'],
            QueryIntent.COHORT_ANALYSIS: ['customer_signup_month'],
        }

        return intent_dimension_mapping.get(intent, [])

    def _find_relevant_datasets(self, metrics: List[str],
                               dimensions: List[str]) -> List[str]:
        """Find canonical datasets that match the query"""
        # This would query the semantic layer for relevant canonical datasets
        # For now, return empty list
        return []

    def _build_semantic_context(self, metrics: List[str],
                                dimensions: List[str]) -> Dict:
        """Build rich semantic context for downstream agents"""
        context = {
            'metric_descriptions': {},
            'dimension_descriptions': {},
        }

        for metric in metrics:
            try:
                metric_def = self.semantic_layer.get_metric(metric)
                context['metric_descriptions'][metric] = {
                    'display_name': metric_def.get('display_name'),
                    'description': metric_def.get('description'),
                    'type': metric_def.get('type'),
                }
            except:
                pass

        for dimension in dimensions:
            dim_def = self.semantic_layer.get_dimension(dimension)
            if dim_def:
                context['dimension_descriptions'][dimension] = {
                    'display_name': dim_def.get('display_name'),
                    'description': dim_def.get('description'),
                    'type': dim_def.get('type'),
                }

        return context


class QueryPlannerAgent:
    """
    Agent 3: Create semantic query plan

    Translates understanding and retrieved semantics into a structured plan:
    - Which metrics to query
    - How to group (dimensions)
    - What filters to apply
    - Ordering and limits
    """

    def __init__(self, semantic_layer: SemanticLayer):
        self.semantic_layer = semantic_layer

    def process(self, understanding: QueryUnderstanding,
                retrieval: Dict[str, Any],
                context: ConversationContext) -> SemanticPlan:
        """Create a semantic query plan"""
        logger.info(f"[QueryPlannerAgent] Planning query for intent: {understanding.intent}")

        # Build the plan based on intent
        if understanding.intent == QueryIntent.TREND_ANALYSIS:
            plan = self._plan_trend_analysis(understanding, retrieval)
        elif understanding.intent == QueryIntent.COMPARISON:
            plan = self._plan_comparison(understanding, retrieval)
        elif understanding.intent == QueryIntent.COHORT_ANALYSIS:
            plan = self._plan_cohort_analysis(understanding, retrieval)
        else:
            plan = self._plan_metric_query(understanding, retrieval)

        logger.info(f"[QueryPlannerAgent] Plan: {plan.metrics} grouped by {plan.dimensions}")

        return plan

    def _plan_trend_analysis(self, understanding: QueryUnderstanding,
                            retrieval: Dict) -> SemanticPlan:
        """Plan a trend analysis query"""
        metrics = retrieval['metrics'][:1]  # Primary metric
        dimensions = [d for d in retrieval['dimensions'] if 'month' in d or 'quarter' in d]

        if not dimensions:
            dimensions = ['snapshot_month']  # Default time dimension

        return SemanticPlan(
            metrics=metrics,
            dimensions=dimensions[:1],  # Single time dimension
            filters=[],
            order_by=dimensions[0],
            limit=None,
            explanation=f"Analyzing {metrics[0]} trend over {dimensions[0]}"
        )

    def _plan_comparison(self, understanding: QueryUnderstanding,
                        retrieval: Dict) -> SemanticPlan:
        """Plan a comparison query"""
        metrics = retrieval['metrics'][:1]
        dimensions = [d for d in retrieval['dimensions'] if 'segment' in d or 'tier' in d or 'country' in d]

        if not dimensions:
            dimensions = ['customer_segment']  # Default categorical dimension

        return SemanticPlan(
            metrics=metrics,
            dimensions=dimensions[:2],  # Up to 2 dimensions
            filters=[],
            order_by=None,
            limit=None,
            explanation=f"Comparing {metrics[0]} across {dimensions[0]}"
        )

    def _plan_cohort_analysis(self, understanding: QueryUnderstanding,
                             retrieval: Dict) -> SemanticPlan:
        """Plan a cohort analysis query"""
        metrics = retrieval['metrics']
        dimensions = [d for d in retrieval['dimensions'] if 'signup' in d]

        if not dimensions:
            dimensions = ['customer_signup_month']

        return SemanticPlan(
            metrics=metrics,
            dimensions=dimensions,
            filters=[],
            order_by=f"-{dimensions[0]}",  # Descending by signup date
            limit=12,  # Last 12 cohorts
            explanation=f"Analyzing {metrics[0]} by signup cohort"
        )

    def _plan_metric_query(self, understanding: QueryUnderstanding,
                          retrieval: Dict) -> SemanticPlan:
        """Plan a simple metric query"""
        metrics = retrieval['metrics'][:1]
        dimensions = retrieval['dimensions'][:1] if retrieval['dimensions'] else []

        return SemanticPlan(
            metrics=metrics,
            dimensions=dimensions,
            filters=[],
            order_by=None,
            limit=None,
            explanation=f"Querying {metrics[0]}" + (f" by {dimensions[0]}" if dimensions else "")
        )


class SQLGeneratorAgent:
    """
    Agent 4: Generate and execute SQL from semantic plan

    Translates the semantic plan into:
    - Executable semantic layer query
    - SQL query (for transparency)
    - Query results
    """

    def __init__(self, semantic_layer: SemanticLayer):
        self.semantic_layer = semantic_layer

    def process(self, plan: SemanticPlan) -> Dict[str, Any]:
        """Generate and execute SQL from plan"""
        logger.info(f"[SQLGeneratorAgent] Generating SQL for: {plan.explanation}")

        try:
            # Execute through semantic layer
            result = self.semantic_layer.query_metric(
                metric_name=plan.metrics[0],
                dimensions=plan.dimensions if plan.dimensions else None,
                filters=plan.filters if plan.filters else None,
                order_by=plan.order_by,
                limit=plan.limit
            )

            logger.info(f"[SQLGeneratorAgent] Query successful: {result['row_count']} rows")

            return {
                'success': True,
                'result': result,
                'plan': plan,
                'error': None
            }

        except SemanticLayerError as e:
            logger.error(f"[SQLGeneratorAgent] Query failed: {e}")
            return {
                'success': False,
                'result': None,
                'plan': plan,
                'error': str(e)
            }


class ResultInterpreterAgent:
    """
    Agent 5: Interpret and format results

    Transforms raw query results into:
    - Human-readable narrative
    - Key insights
    - Suggested follow-up questions
    """

    def __init__(self):
        pass

    def process(self, sql_result: Dict[str, Any],
                understanding: QueryUnderstanding) -> Dict[str, Any]:
        """Interpret and format query results"""
        logger.info(f"[ResultInterpreterAgent] Interpreting results")

        if not sql_result['success']:
            return {
                'narrative': f"I encountered an error: {sql_result['error']}",
                'insights': [],
                'suggestions': ["Try rephrasing your question", "Check if the metric name is correct"],
                'formatted_data': None
            }

        result_data = sql_result['result']
        plan = sql_result['plan']

        # Generate narrative
        narrative = self._generate_narrative(result_data, plan, understanding)

        # Extract insights
        insights = self._extract_insights(result_data, plan)

        # Suggest follow-ups
        suggestions = self._generate_suggestions(result_data, plan, understanding)

        return {
            'narrative': narrative,
            'insights': insights,
            'suggestions': suggestions,
            'formatted_data': result_data['data'],
            'sql': result_data.get('sql'),
            'row_count': result_data['row_count']
        }

    def _generate_narrative(self, result_data: Dict, plan: SemanticPlan,
                           understanding: QueryUnderstanding) -> str:
        """Generate human-readable narrative"""
        metric_name = result_data['display_name']
        row_count = result_data['row_count']

        if row_count == 0:
            return f"No data found for {metric_name}."

        if row_count == 1 and not plan.dimensions:
            # Single value result
            value = result_data['data'][0][plan.metrics[0]]
            return f"The {metric_name} is {value:,.2f}."

        if plan.dimensions:
            dim_name = plan.dimensions[0]
            return f"Found {row_count} {dim_name} values for {metric_name}."

        return f"Retrieved {row_count} results for {metric_name}."

    def _extract_insights(self, result_data: Dict, plan: SemanticPlan) -> List[str]:
        """Extract key insights from results"""
        insights = []
        data = result_data['data']

        if not data or len(data) < 2:
            return insights

        metric_key = plan.metrics[0]

        # Trend insights for time series
        if plan.dimensions and 'month' in plan.dimensions[0]:
            first_value = data[0][metric_key]
            last_value = data[-1][metric_key]

            if first_value and last_value:
                change = ((last_value - first_value) / first_value) * 100
                direction = "increased" if change > 0 else "decreased"
                insights.append(f"Trend: {direction} by {abs(change):.1f}% from start to end")

        # Comparison insights
        if plan.dimensions and len(data) > 1:
            values = [row[metric_key] for row in data if row.get(metric_key)]
            if values:
                max_value = max(values)
                min_value = min(values)
                insights.append(f"Range: {min_value:,.0f} to {max_value:,.0f}")

        return insights

    def _generate_suggestions(self, result_data: Dict, plan: SemanticPlan,
                             understanding: QueryUnderstanding) -> List[str]:
        """Generate follow-up question suggestions"""
        suggestions = []

        metric = result_data['metric']

        if understanding.intent == QueryIntent.TREND_ANALYSIS:
            suggestions.append(f"Break down {metric} by customer segment")
            suggestions.append(f"Compare {metric} to last year")
        elif understanding.intent == QueryIntent.COMPARISON:
            suggestions.append(f"Show {metric} trend over time")
            suggestions.append(f"Filter {metric} by top segments")
        else:
            suggestions.append(f"Show {metric} over time")
            suggestions.append(f"Compare {metric} by segment")

        return suggestions[:3]  # Limit to 3 suggestions


class ConversationManager:
    """
    Agent 6: Manage conversation context and orchestrate agent flow

    Responsibilities:
    - Maintain conversation history
    - Coordinate agent execution flow
    - Handle follow-up questions with context
    - Provide session management
    """

    def __init__(self, semantic_layer: SemanticLayer):
        self.semantic_layer = semantic_layer
        self.contexts: Dict[str, ConversationContext] = {}

        # Initialize agents
        self.query_understanding = QueryUnderstandingAgent(semantic_layer)
        self.semantic_retriever = SemanticRetrieverAgent(semantic_layer)
        self.query_planner = QueryPlannerAgent(semantic_layer)
        self.sql_generator = SQLGeneratorAgent(semantic_layer)
        self.result_interpreter = ResultInterpreterAgent()

    def process_query(self, query: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Main entry point: Process a natural language query through the agent flow

        Flow:
        1. Query Understanding → Parse intent and entities
        2. Semantic Retriever → Find relevant metrics/dimensions
        3. Query Planner → Create semantic query plan
        4. SQL Generator → Execute query
        5. Result Interpreter → Format and explain results
        6. Update conversation context
        """
        logger.info(f"[ConversationManager] Processing query: '{query}' (session: {session_id})")

        # Get or create conversation context
        context = self._get_context(session_id)

        # Agent flow execution
        start_time = datetime.now()

        # Step 1: Understand the query
        understanding = self.query_understanding.process(query, context)

        # Step 2: Retrieve semantic information
        retrieval = self.semantic_retriever.process(understanding, context)

        # Step 3: Plan the query
        plan = self.query_planner.process(understanding, retrieval, context)

        # Step 4: Generate and execute SQL
        sql_result = self.sql_generator.process(plan)

        # Step 5: Interpret results
        interpretation = self.result_interpreter.process(sql_result, understanding)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Update context
        self._update_context(context, understanding, plan, sql_result)

        # Build final response
        response = {
            'query': query,
            'session_id': session_id,
            'understanding': {
                'intent': understanding.intent.value,
                'confidence': understanding.confidence,
                'entities': understanding.entities
            },
            'plan': {
                'metrics': plan.metrics,
                'dimensions': plan.dimensions,
                'explanation': plan.explanation
            },
            'result': {
                'success': sql_result['success'],
                'narrative': interpretation['narrative'],
                'insights': interpretation['insights'],
                'data': interpretation['formatted_data'],
                'row_count': interpretation.get('row_count', 0),
                'sql': interpretation.get('sql')
            },
            'suggestions': interpretation['suggestions'],
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"[ConversationManager] Query completed in {execution_time:.2f}s")

        return response

    def _get_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context for session"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(session_id=session_id)
        return self.contexts[session_id]

    def _update_context(self, context: ConversationContext,
                       understanding: QueryUnderstanding,
                       plan: SemanticPlan,
                       sql_result: Dict):
        """Update conversation context with query results"""
        context.query_history.append({
            'query': understanding.raw_query,
            'intent': understanding.intent.value,
            'timestamp': datetime.now().isoformat()
        })

        context.last_metrics = plan.metrics
        context.last_dimensions = plan.dimensions
        context.last_intent = understanding.intent
        context.timestamp = datetime.now()

        # Keep only last 10 queries
        if len(context.query_history) > 10:
            context.query_history = context.query_history[-10:]


# Example usage and testing
if __name__ == "__main__":
    from pathlib import Path

    # Initialize semantic layer
    config_path = "semantic_models/metrics.yml"
    if not Path(config_path).exists():
        print("❌ Configuration file not found")
        exit(1)

    # Create conversation manager
    sl = SemanticLayer(config_path)
    manager = ConversationManager(sl)

    # Test queries
    test_queries = [
        "What is our total MRR?",
        "How is my active customer count changing over time?",
        "Compare MRR by customer segment",
        "Show me customer signup cohorts",
    ]

    print("\n" + "="*80)
    print("AI AGENT FLOW - WrenAI-Inspired Multi-Agent System")
    print("="*80 + "\n")

    for query in test_queries:
        print(f"\n💬 Query: {query}")
        print("-" * 80)

        response = manager.process_query(query)

        print(f"🎯 Intent: {response['understanding']['intent']} "
              f"(confidence: {response['understanding']['confidence']:.2f})")
        print(f"📊 Plan: {response['plan']['explanation']}")
        print(f"✅ Result: {response['result']['narrative']}")

        if response['result']['insights']:
            print(f"💡 Insights:")
            for insight in response['result']['insights']:
                print(f"   • {insight}")

        print(f"⏱️  Execution time: {response['execution_time']:.2f}s")
        print()
