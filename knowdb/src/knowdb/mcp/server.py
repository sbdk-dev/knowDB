"""
KnowDB MCP Server.

FastMCP server that connects Claude Desktop to semantic layer.
Implements execution-first pattern to prevent fabrication.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .tools import (
    query_model_tool,
    list_models_tool,
    get_model_tool,
    discover_models_tool,
    suggest_analysis_tool,
    test_significance_tool,
    health_check_tool,
    sample_queries_tool,
    optimize_query_tool,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("knowdb_mcp.log"), logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# Global component references (will be initialized on server startup)
_semantic_manager = None
_intelligence_engine = None
_statistical_tester = None
_conversation_memory = None
_query_optimizer = None
_model_discovery = None


def get_tool_list() -> List[Dict[str, Any]]:
    """
    Get list of available MCP tools.

    Returns:
        List of tool definitions
    """
    return [
        {
            "name": "query_model",
            "description": (
                "Query a semantic model with execution-first pattern. "
                "Returns data with statistical analysis and interpretation."
            ),
        },
        {
            "name": "list_models",
            "description": "List available semantic models with descriptions.",
        },
        {
            "name": "get_model",
            "description": "Get detailed schema for a specific model.",
        },
        {
            "name": "discover_models",
            "description": "Discover relevant models for a natural language question using RAG.",
        },
        {
            "name": "suggest_analysis",
            "description": "Suggest next analysis steps based on current results.",
        },
        {
            "name": "test_significance",
            "description": "Run statistical significance tests on data.",
        },
        {
            "name": "health_check",
            "description": "Check system health and database connections.",
        },
        {
            "name": "sample_queries",
            "description": "Get sample queries for a model to get started.",
        },
        {
            "name": "optimize_query",
            "description": "Get query optimization recommendations.",
        },
    ]


def create_mcp_server(
    semantic_manager=None,
    intelligence_engine=None,
    statistical_tester=None,
    conversation_memory=None,
    query_optimizer=None,
    model_discovery=None,
) -> FastMCP:
    """
    Create and configure the MCP server.

    Args:
        semantic_manager: Semantic layer manager instance
        intelligence_engine: Intelligence engine instance
        statistical_tester: Statistical testing component
        conversation_memory: Conversation memory instance
        query_optimizer: Query optimizer instance
        model_discovery: Model discovery instance

    Returns:
        Configured FastMCP server
    """
    global _semantic_manager, _intelligence_engine, _statistical_tester
    global _conversation_memory, _query_optimizer, _model_discovery

    # Store component references
    _semantic_manager = semantic_manager
    _intelligence_engine = intelligence_engine
    _statistical_tester = statistical_tester
    _conversation_memory = conversation_memory
    _query_optimizer = query_optimizer
    _model_discovery = model_discovery

    # Create FastMCP server
    mcp = FastMCP("knowdb-analyst")

    # Register tools
    @mcp.tool()
    async def list_models() -> Dict[str, Any]:
        """
        List available semantic models with their descriptions and key metrics.

        Returns available models that can be queried for data analysis.
        """
        return await list_models_tool(semantic_manager=_semantic_manager)

    @mcp.tool()
    async def get_model(model_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific semantic model.

        Args:
            model_name: Name of the model to inspect

        Returns:
            Model schema including dimensions, measures, and sample queries
        """
        return await get_model_tool(
            model_name=model_name,
            semantic_manager=_semantic_manager
        )

    @mcp.tool()
    async def discover_models(
        question: str,
        top_k: int = 3,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Discover relevant semantic models for a natural language question using vector similarity.

        Args:
            question: User's question in natural language
            top_k: Number of models to suggest (default: 3)
            similarity_threshold: Minimum similarity score 0-1 (default: 0.3)

        Returns:
            Ranked list of relevant models with similarity scores
        """
        return await discover_models_tool(
            question=question,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            model_discovery=_model_discovery
        )

    @mcp.tool()
    async def query_model(
        model: str,
        dimensions: List[str] = [],
        measures: List[str] = [],
        filters: Dict[str, Any] = {},
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Query a semantic model with execution-first pattern to prevent fabrication.

        IMPORTANT: This tool executes the query BEFORE generating any interpretation.
        All insights are based on REAL data, never fabricated.

        Args:
            model: Name of the semantic model to query
            dimensions: List of dimensions to group by
            measures: List of measures to calculate
            filters: Optional filters to apply
            limit: Optional limit on number of rows returned

        Returns:
            Query results with statistical analysis and natural language interpretation
        """
        return await query_model_tool(
            model=model,
            dimensions=dimensions,
            measures=measures,
            filters=filters,
            limit=limit,
            semantic_manager=_semantic_manager,
            intelligence_engine=_intelligence_engine,
            statistical_tester=_statistical_tester,
            conversation_memory=_conversation_memory,
            query_optimizer=_query_optimizer
        )

    @mcp.tool()
    async def suggest_analysis(
        current_result: Optional[str] = None,
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Suggest next analysis steps based on current results or context.

        Args:
            current_result: JSON string of current query result
            context: Description of current analysis context
            model: Current model being analyzed

        Returns:
            Suggested questions and analysis paths
        """
        return await suggest_analysis_tool(
            current_result=current_result,
            context=context,
            model=model,
            intelligence_engine=_intelligence_engine
        )

    @mcp.tool()
    async def test_significance(
        data: Dict[str, Any],
        comparison_type: str = "groups",
        dimensions: List[str] = [],
        measures: List[str] = [],
    ) -> Dict[str, Any]:
        """
        Run statistical significance tests on data.

        Args:
            data: Query result data to test
            comparison_type: Type of test (groups, correlation, trend)
            dimensions: Dimensions being compared
            measures: Measures being analyzed

        Returns:
            Statistical test results with interpretation
        """
        return await test_significance_tool(
            data=data,
            comparison_type=comparison_type,
            dimensions=dimensions,
            measures=measures,
            statistical_tester=_statistical_tester,
            intelligence_engine=_intelligence_engine
        )

    @mcp.tool()
    async def health_check() -> Dict[str, Any]:
        """
        Check health of semantic layer and database connections.

        Returns:
            Health status of all system components
        """
        return await health_check_tool(semantic_manager=_semantic_manager)

    @mcp.tool()
    async def sample_queries(model: str) -> Dict[str, Any]:
        """
        Get sample queries for a specific model to help users get started.

        Args:
            model: Name of the model

        Returns:
            Sample queries with descriptions
        """
        return await sample_queries_tool(
            model=model,
            semantic_manager=_semantic_manager
        )

    @mcp.tool()
    async def optimize_query(
        model: str,
        dimensions: List[str] = [],
        measures: List[str] = [],
        filters: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        """
        Get query optimization recommendations based on conversation history.

        Args:
            model: Name of the semantic model
            dimensions: Proposed dimensions
            measures: Proposed measures
            filters: Proposed filters

        Returns:
            Optimization suggestions and performance recommendations
        """
        return await optimize_query_tool(
            model=model,
            dimensions=dimensions,
            measures=measures,
            filters=filters,
            conversation_memory=_conversation_memory
        )

    logger.info("KnowDB MCP Server created with 9 tools")
    return mcp


async def initialize_components():
    """
    Initialize all server components.

    This should be called before starting the server to set up
    database connections and load semantic models.
    """
    global _semantic_manager, _intelligence_engine, _statistical_tester
    global _conversation_memory, _query_optimizer, _model_discovery

    # Import components (lazy import to avoid circular dependencies)
    # These will be implemented in other modules
    try:
        # TODO: Import from actual modules once they exist
        # from knowdb.semantic_layer import SemanticLayerManager
        # from knowdb.intelligence import IntelligenceEngine
        # from knowdb.testing import StatisticalTester
        # from knowdb.memory import ConversationMemory
        # from knowdb.optimization import QueryOptimizer
        # from knowdb.discovery import ModelDiscovery

        logger.info("Initializing KnowDB components...")

        # Initialize components (placeholder until modules exist)
        # _semantic_manager = SemanticLayerManager()
        # _intelligence_engine = IntelligenceEngine()
        # _statistical_tester = StatisticalTester()
        # _conversation_memory = ConversationMemory()
        # _query_optimizer = QueryOptimizer()
        # _model_discovery = ModelDiscovery()

        logger.info("KnowDB components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise


def main():
    """Main entry point for the MCP server."""
    # Startup messages to stderr to avoid MCP protocol interference
    print("Starting KnowDB MCP Server...", file=sys.stderr)
    print("Semantic Layer: Execution-first pattern enabled", file=sys.stderr)
    print("Statistical Rigor: Auto-significance testing enabled", file=sys.stderr)

    logger.info("Starting KnowDB MCP Server")

    # Initialize components
    asyncio.run(initialize_components())

    # Create and run server
    mcp = create_mcp_server(
        semantic_manager=_semantic_manager,
        intelligence_engine=_intelligence_engine,
        statistical_tester=_statistical_tester,
        conversation_memory=_conversation_memory,
        query_optimizer=_query_optimizer,
        model_discovery=_model_discovery,
    )

    # Run the server
    mcp.run()


if __name__ == "__main__":
    main()
