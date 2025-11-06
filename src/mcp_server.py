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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize semantic layer
SEMANTIC_MODELS_PATH = os.getenv(
    'SEMANTIC_MODELS_PATH',
    'semantic_models/metrics.yml'
)

try:
    semantic_layer = SemanticLayer(SEMANTIC_MODELS_PATH)
    logger.info(f"Semantic layer initialized with {len(semantic_layer.list_metrics())} metrics")
except Exception as e:
    logger.error(f"Failed to initialize semantic layer: {e}")
    raise


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
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
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
                        "description": "Name of the metric to explain"
                    }
                },
                "required": ["metric_name"]
            }
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
                    "metric_name": {
                        "type": "string",
                        "description": "Name of the metric to query"
                    },
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of dimensions to group by (e.g., ['customer_segment', 'country'])"
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional SQL WHERE conditions (e.g., ['customer_segment = \"Enterprise\"'])"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of rows to return"
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Optional column to sort by. Prefix with '-' for descending (e.g., '-total_mrr')"
                    }
                },
                "required": ["metric_name"]
            }
        ),
        Tool(
            name="list_dimensions",
            description=(
                "List all available dimensions for slicing and grouping data. "
                "Dimensions are categorical attributes like customer_segment, country, etc. "
                "Use this to discover how you can break down metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
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
                    "dimension_name": {
                        "type": "string",
                        "description": "Name of the dimension"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of values to return"
                    }
                },
                "required": ["dimension_name"]
            }
        ),
        Tool(
            name="list_canonical_datasets",
            description=(
                "List pre-defined canonical datasets for common analyses. "
                "Canonical datasets are 'golden' certified combinations of metrics and dimensions "
                "that ensure consistency across analyses."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
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
                        "description": "Name of the canonical dataset to query"
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional SQL WHERE conditions"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional maximum number of rows to return"
                    }
                },
                "required": ["dataset_name"]
            }
        )
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
                if metric['description']:
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

            result = semantic_layer.query_metric(
                metric_name=metric_name,
                dimensions=dimensions,
                filters=filters,
                limit=limit,
                order_by=order_by
            )

            # Format results nicely
            response = f"# {result['display_name']}\n\n"

            if result['description']:
                response += f"{result['description']}\n\n"

            # Show dimensions used
            if result['dimensions']:
                response += f"**Grouped by:** {', '.join(result['dimensions'])}\n\n"

            # Show data
            response += "## Results\n\n"

            if result['row_count'] == 0:
                response += "*No data found*\n"
            else:
                # Format as markdown table
                data = result['data']
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
                if dim.get('description'):
                    result += f"  - {dim['description']}\n"
                if dim.get('table'):
                    result += f"  - Table: {dim['table']}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_dimension_values":
            dimension_name = arguments["dimension_name"]
            limit = arguments.get("limit", 100)

            # Get dimension definition
            dim = semantic_layer.get_dimension(dimension_name)
            if not dim:
                return [TextContent(
                    type="text",
                    text=f"❌ Dimension '{dimension_name}' not found"
                )]

            # Query the dimension values
            table_name = dim['table']
            column_name = dim['column']

            # Build query to get distinct values
            table = semantic_layer.connection.table(table_name)
            result = table[column_name].distinct().limit(limit).execute()

            values = result[column_name].tolist()

            response = f"# Values for {dimension_name}\n\n"
            response += f"Found {len(values)} unique values:\n\n"
            for value in values:
                response += f"- {value}\n"

            return [TextContent(type="text", text=response)]

        elif name == "list_canonical_datasets":
            datasets = semantic_layer.config['semantic_model'].get('canonical_datasets', [])

            if not datasets:
                return [TextContent(
                    type="text",
                    text="No canonical datasets defined"
                )]

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
            datasets = semantic_layer.config['semantic_model'].get('canonical_datasets', [])
            dataset = None
            for ds in datasets:
                if ds['name'] == dataset_name:
                    dataset = ds
                    break

            if not dataset:
                return [TextContent(
                    type="text",
                    text=f"❌ Canonical dataset '{dataset_name}' not found"
                )]

            # Query each metric in the dataset
            response = f"# {dataset['display_name']}\n\n"
            response += f"{dataset['description']}\n\n"

            for metric_name in dataset['metrics']:
                try:
                    result = semantic_layer.query_metric(
                        metric_name=metric_name,
                        dimensions=dataset['dimensions'],
                        filters=filters,
                        limit=limit
                    )

                    response += f"## {result['display_name']}\n\n"

                    if result['row_count'] > 0:
                        data = result['data']
                        columns = list(data[0].keys())

                        # Create table
                        response += "| " + " | ".join(columns) + " |\n"
                        response += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                        for row in data[:10]:  # Limit to 10 rows per metric
                            values = [str(row[col]) for col in columns]
                            response += "| " + " | ".join(values) + " |\n"

                        if result['row_count'] > 10:
                            response += f"\n*Showing 10 of {result['row_count']} rows*\n"

                        response += "\n"
                    else:
                        response += "*No data*\n\n"

                except Exception as e:
                    response += f"❌ Error querying {metric_name}: {e}\n\n"

            return [TextContent(type="text", text=response)]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    except SemanticLayerError as e:
        logger.error(f"Semantic layer error in {name}: {e}")
        return [TextContent(
            type="text",
            text=f"❌ Error: {str(e)}"
        )]

    except Exception as e:
        logger.error(f"Unexpected error in {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"❌ Unexpected error: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    logger.info("Starting Semantic Layer MCP Server...")
    logger.info(f"Loaded {len(semantic_layer.list_metrics())} metrics")
    logger.info(f"Loaded {len(semantic_layer.list_dimensions())} dimensions")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
