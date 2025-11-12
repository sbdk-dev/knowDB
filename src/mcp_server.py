#!/usr/bin/env python3
"""
MCP Server for Semantic Layer

This server exposes the semantic layer to Claude Desktop via MCP protocol.
It provides tools for:
- Listing available metrics
- Querying metrics with dimensions and filters
- Explaining how metrics are calculated
- Exploring dimensions
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from semantic_layer import SemanticLayer, SemanticLayerError
from query_cache import QueryCache, CacheConfig, CacheBackend
from ai_agent_flow import ConversationManager
from dashboard_manager import (
    DashboardManager,
    format_auto_save_message
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize semantic layer
SEMANTIC_MODELS_PATH = os.getenv("SEMANTIC_MODELS_PATH", "semantic_models/metrics.yml")

try:
    semantic_layer = SemanticLayer(SEMANTIC_MODELS_PATH)
    logger.info(f"Semantic layer initialized with {len(semantic_layer.list_metrics())} metrics")
except Exception as e:
    logger.error(f"Failed to initialize semantic layer: {e}")
    raise

# Initialize query cache
try:
    cache_config = CacheConfig(
        backend=CacheBackend.MEMORY,  # Start with memory cache for simplicity
        ttl_seconds=1800,  # 30 minutes TTL
        max_memory_items=500,
        enable_metrics=True,
    )
    query_cache = QueryCache(cache_config)
    logger.info(f"Query cache initialized with {cache_config.backend.value} backend")
except Exception as e:
    logger.warning(f"Failed to initialize query cache: {e}")
    query_cache = None

# Initialize AI conversation manager
try:
    conversation_manager = ConversationManager(semantic_layer)
    logger.info("AI Conversation Manager initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize AI conversation manager: {e}")
    conversation_manager = None

# Initialize dashboard manager
try:
    dashboard_manager = DashboardManager()
    logger.info("Dashboard Manager initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize dashboard manager: {e}")
    dashboard_manager = None


# Create MCP server
app = Server("semantic-layer")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    List all available MCP tools

    Returns tools that Claude can use to interact with the semantic layer
    """
    return [
        Tool(
            name="list_metrics",
            description=(
                "List all available business metrics. "
                "Returns metric names, display names, descriptions, and types. "
                "Use this to discover what metrics are available to query."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="explain_metric",
            description=(
                "Get a detailed explanation of how a specific metric is calculated. "
                "Shows the aggregation type, source table, column, and any filters applied. "
                "Use this to understand the business logic behind a metric."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": "Name of the metric to explain",
                    }
                },
                "required": ["metric_name"],
            },
        ),
        Tool(
            name="query_metric",
            description=(
                "Query a metric and return results. "
                "Supports filtering, grouping by dimensions, ordering, and limiting results. "
                "Returns the data, row count, and generated SQL for transparency. "
                "This is the primary tool for answering data questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "description": "Name of the metric to query"},
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of dimensions to group by (e.g., ['customer_segment', 'country'])",
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional SQL WHERE conditions (e.g., ['customer_segment = \"Enterprise\"'])",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of rows to return",
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Optional column to sort by. Prefix with '-' for descending (e.g., '-total_mrr')",
                    },
                },
                "required": ["metric_name"],
            },
        ),
        Tool(
            name="list_dimensions",
            description=(
                "List all available dimensions for slicing and grouping data. "
                "Dimensions are categorical attributes like customer_segment, country, etc. "
                "Use this to discover how you can break down metrics."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_dimension_values",
            description=(
                "Get all unique values for a specific dimension. "
                "Useful for understanding what values are available for filtering. "
                "For example, get all customer segments or countries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension_name": {"type": "string", "description": "Name of the dimension"},
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of values to return",
                    },
                },
                "required": ["dimension_name"],
            },
        ),
        Tool(
            name="list_canonical_datasets",
            description=(
                "List pre-defined canonical datasets for common analyses. "
                "Canonical datasets are 'golden' certified combinations of metrics and dimensions "
                "that ensure consistency across analyses."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="query_canonical_dataset",
            description=(
                "Query a pre-defined canonical dataset. "
                "These are certified 'golden' datasets with consistent definitions "
                "used across the organization for specific analyses."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of the canonical dataset to query",
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional SQL WHERE conditions",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of rows to return",
                    },
                },
                "required": ["dataset_name"],
            },
        ),
        Tool(
            name="cache_stats",
            description=(
                "Get query cache performance statistics. "
                "Shows hit rate, cache size, and performance metrics. "
                "Useful for monitoring cache effectiveness and performance optimization."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="clear_cache",
            description=(
                "Clear all cached query results. "
                "Use this to force fresh data retrieval or when underlying data has changed. "
                "Cache will be rebuilt as new queries are executed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm that you want to clear all cached data",
                    }
                },
                "required": ["confirm"],
            },
        ),
        Tool(
            name="ask_ai_analyst",
            description=(
                "🤖 Ask the AI analyst a question in natural language. "
                "The AI analyst uses a WrenAI-inspired multi-agent flow to: "
                "1) Understand your question intent, "
                "2) Find relevant metrics and dimensions, "
                "3) Plan and execute the optimal query, "
                "4) Provide insights and explanations, "
                "5) Suggest follow-up questions. "
                "This is the most natural way to interact - just ask your business question!"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your business question in natural language (e.g., 'How is MRR trending?', 'Compare revenue by segment')",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for conversation context (defaults to 'default')",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="save_as",
            description="💾 Rename the last auto-saved dashboard to a custom name",
            inputSchema={
                "type": "object",
                "properties": {
                    "new_name": {
                        "type": "string",
                        "description": "Your custom dashboard name"
                    }
                },
                "required": ["new_name"]
            }
        ),
        Tool(
            name="add_to_dashboard",
            description="➕ Add current chart to an existing dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "dashboard_name": {
                        "type": "string",
                        "description": "Name of existing dashboard"
                    }
                },
                "required": ["dashboard_name"]
            }
        ),
        Tool(
            name="list_dashboards",
            description="📋 List all Evidence.dev dashboards",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="cleanup_dashboards",
            description="🧹 Remove auto-generated dashboards older than 7 days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_old": {
                        "type": "number",
                        "description": "Age threshold in days (default: 7)",
                        "default": 7
                    }
                },
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """
    Handle tool calls from Claude

    Args:
        name: Name of the tool being called
        arguments: Arguments passed to the tool

    Returns:
        List of TextContent responses
    """
    try:
        if name == "list_metrics":
            metrics = semantic_layer.list_metrics()

            # Format nicely for Claude
            result = "# Available Metrics\n\n"
            for metric in metrics:
                result += f"**{metric['display_name']}** (`{metric['name']}`)\n"
                result += f"  - Type: {metric['type']}\n"
                if metric["description"]:
                    result += f"  - {metric['description']}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "explain_metric":
            metric_name = arguments["metric_name"]
            explanation = semantic_layer.explain_metric(metric_name)

            return [TextContent(type="text", text=explanation)]

        elif name == "query_metric":
            metric_name = arguments["metric_name"]
            dimensions = arguments.get("dimensions")
            filters = arguments.get("filters")
            limit = arguments.get("limit")
            order_by = arguments.get("order_by")

            # Create cache key from all parameters
            cache_params = {
                "metric_name": metric_name,
                "dimensions": dimensions,
                "filters": filters,
                "limit": limit,
                "order_by": order_by,
            }

            # Try to get from cache first
            result = None
            if query_cache:
                cache_key = f"query_metric:{metric_name}"
                result = query_cache.get(cache_key, cache_params)

            # If not in cache, execute query and cache result
            if result is None:
                result = semantic_layer.query_metric(
                    metric_name=metric_name,
                    dimensions=dimensions,
                    filters=filters,
                    limit=limit,
                    order_by=order_by,
                )

                # Cache the result
                if query_cache:
                    query_cache.set(cache_key, result, cache_params)

            # Format results nicely
            response = f"# {result['display_name']}\n\n"

            if result["description"]:
                response += f"{result['description']}\n\n"

            # Show dimensions used
            if result["dimensions"]:
                response += f"**Grouped by:** {', '.join(result['dimensions'])}\n\n"

            # Show data
            response += "## Results\n\n"

            if result["row_count"] == 0:
                response += "*No data found*\n"
            else:
                # Format as markdown table
                data = result["data"]
                if data:
                    # Get column names
                    columns = list(data[0].keys())

                    # Create table header
                    response += "| " + " | ".join(columns) + " |\n"
                    response += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                    # Add rows
                    for row in data:
                        values = [str(row[col]) for col in columns]
                        response += "| " + " | ".join(values) + " |\n"

                    response += f"\n**Total rows:** {result['row_count']}\n"

            # Show SQL for transparency
            response += f"\n## Generated SQL\n\n```sql\n{result['sql']}\n```\n"

            return [TextContent(type="text", text=response)]

        elif name == "list_dimensions":
            dimensions = semantic_layer.list_dimensions()

            result = "# Available Dimensions\n\n"
            for dim in dimensions:
                result += f"**{dim['name']}**\n"
                result += f"  - Type: {dim['type']}\n"
                if dim.get("description"):
                    result += f"  - {dim['description']}\n"
                if dim.get("table"):
                    result += f"  - Table: {dim['table']}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_dimension_values":
            dimension_name = arguments["dimension_name"]
            limit = arguments.get("limit", 100)

            # Get dimension definition
            dim = semantic_layer.get_dimension(dimension_name)
            if not dim:
                return [TextContent(type="text", text=f"❌ Dimension '{dimension_name}' not found")]

            # Try cache first
            cache_params = {"dimension_name": dimension_name, "limit": limit}
            values = None

            if query_cache:
                cache_key = f"dimension_values:{dimension_name}"
                cached_result = query_cache.get(cache_key, cache_params)
                if cached_result:
                    values = cached_result

            # If not cached, query the dimension values
            if values is None:
                table_name = dim["table"]
                column_name = dim["column"]

                # Build query to get distinct values
                table = semantic_layer.connection.table(table_name)
                result = table[column_name].distinct().limit(limit).execute()

                values = result[column_name].tolist()

                # Cache the result
                if query_cache:
                    query_cache.set(cache_key, values, cache_params)

            response = f"# Values for {dimension_name}\n\n"
            response += f"Found {len(values)} unique values:\n\n"
            for value in values:
                response += f"- {value}\n"

            return [TextContent(type="text", text=response)]

        elif name == "list_canonical_datasets":
            datasets = semantic_layer.config["semantic_model"].get("canonical_datasets", [])

            if not datasets:
                return [TextContent(type="text", text="No canonical datasets defined")]

            result = "# Canonical Datasets\n\n"
            result += "These are pre-defined, certified 'golden' datasets for common analyses.\n\n"

            for dataset in datasets:
                result += f"**{dataset['display_name']}** (`{dataset['name']}`)\n"
                result += f"  - {dataset['description']}\n"
                result += f"  - Metrics: {', '.join(dataset['metrics'])}\n"
                result += f"  - Dimensions: {', '.join(dataset['dimensions'])}\n"
                result += f"  - Refresh: {dataset.get('refresh_schedule', 'manual')}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "query_canonical_dataset":
            dataset_name = arguments["dataset_name"]
            filters = arguments.get("filters")
            limit = arguments.get("limit")

            # Find dataset definition
            datasets = semantic_layer.config["semantic_model"].get("canonical_datasets", [])
            dataset = None
            for ds in datasets:
                if ds["name"] == dataset_name:
                    dataset = ds
                    break

            if not dataset:
                return [
                    TextContent(
                        type="text", text=f"❌ Canonical dataset '{dataset_name}' not found"
                    )
                ]

            # Query each metric in the dataset
            response = f"# {dataset['display_name']}\n\n"
            response += f"{dataset['description']}\n\n"

            for metric_name in dataset["metrics"]:
                try:
                    result = semantic_layer.query_metric(
                        metric_name=metric_name,
                        dimensions=dataset["dimensions"],
                        filters=filters,
                        limit=limit,
                    )

                    response += f"## {result['display_name']}\n\n"

                    if result["row_count"] > 0:
                        data = result["data"]
                        columns = list(data[0].keys())

                        # Create table
                        response += "| " + " | ".join(columns) + " |\n"
                        response += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                        for row in data[:10]:  # Limit to 10 rows per metric
                            values = [str(row[col]) for col in columns]
                            response += "| " + " | ".join(values) + " |\n"

                        if result["row_count"] > 10:
                            response += f"\n*Showing 10 of {result['row_count']} rows*\n"

                        response += "\n"
                    else:
                        response += "*No data*\n\n"

                except Exception as e:
                    response += f"❌ Error querying {metric_name}: {e}\n\n"

            return [TextContent(type="text", text=response)]

        elif name == "cache_stats":
            if not query_cache:
                return [TextContent(type="text", text="❌ Query cache is not enabled")]

            stats = query_cache.get_stats()

            response = "# Query Cache Statistics\n\n"
            response += f"**Backend:** {stats['backend']}\n"
            response += f"**Cache Size:** {stats['cache_size']} entries\n"
            response += f"**Hit Rate:** {stats['hit_rate']}\n"
            response += f"**Total Queries:** {stats['total_queries']}\n"
            response += f"**Cache Hits:** {stats['hits']}\n"
            response += f"**Cache Misses:** {stats['misses']}\n"
            response += f"**TTL:** {stats['ttl_seconds']} seconds\n"
            if stats["last_reset"]:
                response += f"**Last Reset:** {stats['last_reset']}\n"

            # Add performance insight
            if stats["total_queries"] > 0:
                response += "\n## Performance Insights\n\n"
                hit_rate = stats["hits"] / stats["total_queries"]
                if hit_rate >= 0.8:
                    response += (
                        "🟢 **Excellent** - High cache hit rate indicates good performance\n"
                    )
                elif hit_rate >= 0.5:
                    response += "🟡 **Good** - Moderate cache hit rate, consider increasing TTL\n"
                else:
                    response += (
                        "🔴 **Poor** - Low cache hit rate, data may be changing frequently\n"
                    )

            return [TextContent(type="text", text=response)]

        elif name == "clear_cache":
            if not query_cache:
                return [TextContent(type="text", text="❌ Query cache is not enabled")]

            confirm = arguments.get("confirm", False)
            if not confirm:
                return [
                    TextContent(type="text", text="❌ Please set confirm=true to clear the cache")
                ]

            # Get stats before clearing
            old_stats = query_cache.get_stats()

            success = query_cache.clear_all()
            if success:
                response = "✅ **Cache Cleared Successfully**\n\n"
                response += f"Cleared {old_stats['cache_size']} cached entries\n"
                response += "Fresh queries will now be executed and cached\n"
            else:
                response = "❌ Failed to clear cache"

            return [TextContent(type="text", text=response)]

        elif name == "ask_ai_analyst":
            if not conversation_manager:
                return [TextContent(type="text", text="❌ AI analyst is not available")]

            question = arguments["question"]
            session_id = arguments.get("session_id", "default")

            logger.info(f"AI Analyst processing: '{question}' (session: {session_id})")

            # Process through multi-agent flow
            ai_response = conversation_manager.process_query(question, session_id)

            # AUTO-SAVE: Save to Evidence.dev dashboard
            if dashboard_manager and ai_response['result']['success'] and ai_response['result'].get('data'):
                try:
                    # Prepare data for dashboard
                    import pandas as pd
                    result_df = pd.DataFrame(ai_response['result']['data'])

                    dashboard_info = dashboard_manager.auto_save_query(
                        query_text=question,
                        understanding=ai_response['understanding'],
                        result=result_df,
                        sql=ai_response['result'].get('sql', ''),
                        chart_recommendation={}  # Will be enhanced later
                    )

                    # Store for add_to_dashboard tool
                    conversation_manager.last_query_result = {
                        'query_text': question,
                        'understanding': ai_response['understanding'],
                        'data': result_df,
                        'sql': ai_response['result'].get('sql', ''),
                        'chart': {}
                    }

                    # Store dashboard info to add to response later
                    auto_save_info = dashboard_info

                except Exception as e:
                    logger.error(f"Auto-save failed: {e}")
                    auto_save_info = None
            else:
                auto_save_info = None

            # Format response for Claude Desktop
            response = "# 🤖 AI Analyst Response\n\n"

            # Show understanding
            response += f"**Intent Detected:** {ai_response['understanding']['intent']} "
            response += f"(confidence: {ai_response['understanding']['confidence']:.0%})\n\n"

            # Show query plan
            response += f"**Query Plan:** {ai_response['plan']['explanation']}\n"
            response += f"  - Metrics: {', '.join(ai_response['plan']['metrics'])}\n"
            if ai_response['plan']['dimensions']:
                response += f"  - Dimensions: {', '.join(ai_response['plan']['dimensions'])}\n"
            response += "\n"

            # Show narrative result
            response += f"## Answer\n\n{ai_response['result']['narrative']}\n\n"

            # Show insights if available
            if ai_response['result']['insights']:
                response += "## 💡 Key Insights\n\n"
                for insight in ai_response['result']['insights']:
                    response += f"- {insight}\n"
                response += "\n"

            # Show data if available
            if ai_response['result']['success'] and ai_response['result']['data']:
                response += "## 📊 Data\n\n"

                data = ai_response['result']['data']
                if data:
                    # Create markdown table
                    columns = list(data[0].keys())
                    response += "| " + " | ".join(columns) + " |\n"
                    response += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                    # Show up to 10 rows
                    for row in data[:10]:
                        values = [str(row[col]) for col in columns]
                        response += "| " + " | ".join(values) + " |\n"

                    if ai_response['result']['row_count'] > 10:
                        response += f"\n*Showing 10 of {ai_response['result']['row_count']} rows*\n"

                response += "\n"

            # Show SQL for transparency
            if ai_response['result'].get('sql'):
                response += "## Generated SQL\n\n"
                response += f"```sql\n{ai_response['result']['sql']}\n```\n\n"

            # Show follow-up suggestions
            if ai_response['suggestions']:
                response += "## 🔮 Suggested Follow-up Questions\n\n"
                for suggestion in ai_response['suggestions']:
                    response += f"- {suggestion}\n"
                response += "\n"

            response += f"*Query executed in {ai_response['execution_time']:.2f}s*\n"

            # Add auto-save message if dashboard was created
            if auto_save_info:
                response += format_auto_save_message(auto_save_info)

            return [TextContent(type="text", text=response)]

        elif name == "save_as":
            if not dashboard_manager:
                return [TextContent(type="text", text="❌ Dashboard manager is not available")]

            new_name = arguments["new_name"]

            try:
                result = dashboard_manager.save_as(new_name)
                return [TextContent(
                    type="text",
                    text=f"""✅ Dashboard Renamed

**New Name**: {result['dashboard_name']}
🌐 **View**: {result['url']}
📂 **Path**: `{result['path']}`

The dashboard is now saved with your custom name and won't be auto-cleaned up!
"""
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Error renaming dashboard: {str(e)}\n\nMake sure you've run a query first!"
                )]

        elif name == "add_to_dashboard":
            if not dashboard_manager:
                return [TextContent(type="text", text="❌ Dashboard manager is not available")]

            dashboard_name = arguments["dashboard_name"]

            # Get last query result from conversation manager
            last_query = getattr(conversation_manager, 'last_query_result', None)

            if not last_query:
                return [TextContent(
                    type="text",
                    text="❌ No recent query to add. Run a query first!"
                )]

            try:
                result = dashboard_manager.add_to_dashboard(
                    dashboard_name=dashboard_name,
                    query_text=last_query['query_text'],
                    understanding=last_query['understanding'],
                    result=last_query['data'],
                    sql=last_query['sql'],
                    chart_recommendation=last_query.get('chart', {})
                )

                return [TextContent(
                    type="text",
                    text=f"""✅ Added to Dashboard

📊 **Dashboard**: {result['dashboard_name']}
🌐 **View**: {result['url']}
🎯 **Charts**: Multiple visualizations now included

Keep asking questions to add more charts!
"""
                )]
            except FileNotFoundError:
                dashboards = dashboard_manager.list_dashboards()
                dashboard_list = '\n'.join(['- ' + d['name'] for d in dashboards])
                return [TextContent(
                    type="text",
                    text=f"""❌ Dashboard '{dashboard_name}' not found

**Available dashboards**:
{dashboard_list}

Or create a new one by asking a question!
"""
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}"
                )]

        elif name == "list_dashboards":
            if not dashboard_manager:
                return [TextContent(type="text", text="❌ Dashboard manager is not available")]

            dashboards = dashboard_manager.list_dashboards()

            if not dashboards:
                return [TextContent(
                    type="text",
                    text="""📊 No Dashboards Yet

Ask some questions to create your first dashboard!

Example: `ask_ai_analyst("What is our MRR?")`
"""
                )]

            # Format dashboard list
            dashboard_list = "# 📊 Your Evidence.dev Dashboards\n\n"

            auto_generated = [d for d in dashboards if d['is_auto_generated']]
            custom = [d for d in dashboards if not d['is_auto_generated']]

            if custom:
                dashboard_list += "## 📌 Custom Dashboards (Permanent)\n\n"
                for d in custom:
                    dashboard_list += f"""**{d['title']}**
- Charts: {d['num_charts']}
- Modified: {d['modified']}
- 🌐 [View]({d['url']})

"""

            if auto_generated:
                dashboard_list += "## ⏱️ Auto-Generated (7-day retention)\n\n"
                for d in auto_generated:
                    dashboard_list += f"""**{d['title']}**
- Charts: {d['num_charts']}
- Modified: {d['modified']}
- 🌐 [View]({d['url']})

"""

            dashboard_list += f"""
---

**Total**: {len(dashboards)} dashboards

**Tips**:
- Click URLs to view in Evidence.dev
- `save_as("name")` to keep auto-generated dashboards
- `cleanup_dashboards()` to remove old auto-generated ones
"""

            return [TextContent(type="text", text=dashboard_list)]

        elif name == "cleanup_dashboards":
            if not dashboard_manager:
                return [TextContent(type="text", text="❌ Dashboard manager is not available")]

            days_old = arguments.get("days_old", 7)
            cleaned = dashboard_manager.cleanup_old_dashboards(days_old)

            if cleaned:
                return [TextContent(
                    type="text",
                    text=f"""🧹 Cleanup Complete

Removed {len(cleaned)} old auto-generated dashboards:

{chr(10).join(['- ' + name for name in cleaned])}

Custom (renamed) dashboards were preserved!
"""
                )]
            else:
                total_dashboards = len(dashboard_manager.list_dashboards())
                return [TextContent(
                    type="text",
                    text=f"""✅ Already Clean!

No auto-generated dashboards older than {days_old} days found.

**Current dashboards**: {total_dashboards}
"""
                )]

        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    except SemanticLayerError as e:
        logger.error(f"Semantic layer error in {name}: {e}")
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

    except Exception as e:
        logger.error(f"Unexpected error in {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Unexpected error: {str(e)}")]


async def main():
    """Run the MCP server"""
    logger.info("Starting Semantic Layer MCP Server...")
    logger.info(f"Loaded {len(semantic_layer.list_metrics())} metrics")
    logger.info(f"Loaded {len(semantic_layer.list_dimensions())} dimensions")

    if query_cache:
        cache_stats = query_cache.get_stats()
        logger.info(
            f"Query cache enabled: {cache_stats['backend']} backend, {cache_stats['ttl_seconds']}s TTL"
        )
    else:
        logger.warning("Query cache is disabled")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
