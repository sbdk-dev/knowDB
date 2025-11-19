"""
KnowDB MCP Server Package.

Provides Model Context Protocol integration for semantic layer analytics.
Implements execution-first pattern to prevent fabrication.
"""

from .server import create_mcp_server, get_tool_list
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
from .semantic_tools import SemanticTools, create_semantic_tools

__all__ = [
    # Server
    "create_mcp_server",
    "get_tool_list",
    # Tools
    "query_model_tool",
    "list_models_tool",
    "get_model_tool",
    "discover_models_tool",
    "suggest_analysis_tool",
    "test_significance_tool",
    "health_check_tool",
    "sample_queries_tool",
    "optimize_query_tool",
    # Semantic Tools (for sbdk integration)
    "SemanticTools",
    "create_semantic_tools",
]
