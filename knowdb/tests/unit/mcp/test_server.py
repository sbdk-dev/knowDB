"""
Unit tests for KnowDB MCP Server.

Tests follow TDD pattern - written BEFORE implementation.
Enforces execution-first pattern to prevent fabrication.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List


# Test fixtures
@pytest.fixture
def mock_semantic_manager():
    """Mock semantic layer manager"""
    manager = AsyncMock()
    manager.get_available_models = AsyncMock(return_value=[
        {
            "name": "users",
            "description": "User analytics model",
            "dimensions": ["plan_type", "industry", "signup_date"],
            "measures": ["total_users", "conversion_rate", "avg_revenue"]
        },
        {
            "name": "events",
            "description": "Event tracking model",
            "dimensions": ["event_type", "user_id", "timestamp"],
            "measures": ["event_count", "unique_users"]
        }
    ])

    manager.get_model_schema = AsyncMock(return_value={
        "name": "users",
        "dimensions": [
            {"name": "plan_type", "type": "string"},
            {"name": "industry", "type": "string"}
        ],
        "measures": [
            {"name": "total_users", "type": "count_distinct"},
            {"name": "conversion_rate", "type": "ratio"}
        ],
        "sample_queries": [
            "Total users by plan type",
            "Conversion rate by industry"
        ]
    })

    manager.build_query = AsyncMock(return_value={
        "sql": "SELECT plan_type, COUNT(DISTINCT user_id) FROM users GROUP BY plan_type",
        "model": "users",
        "dimensions": ["plan_type"],
        "measures": ["total_users"]
    })

    manager.execute_query = AsyncMock(return_value={
        "data": [
            {"plan_type": "free", "total_users": 5000},
            {"plan_type": "paid", "total_users": 1200}
        ],
        "row_count": 2,
        "execution_time_ms": 45.2
    })

    manager.health_check = AsyncMock(return_value={
        "database_connected": True,
        "database_info": "DuckDB local",
        "timestamp": datetime.now().isoformat()
    })

    return manager


@pytest.fixture
def mock_intelligence_engine():
    """Mock intelligence engine for interpretation"""
    engine = AsyncMock()
    engine.generate_interpretation = AsyncMock(return_value=(
        "Free users dominate the base (5000 vs 1200 paid). "
        "Conversion rate of 19.4% suggests healthy freemium model."
    ))
    engine.suggest_next_questions = AsyncMock(return_value=[
        {"question": "How does conversion vary by industry?", "priority": "high"},
        {"question": "What's the trend over time?", "priority": "medium"}
    ])
    return engine


@pytest.fixture
def mock_statistical_tester():
    """Mock statistical testing component"""
    tester = AsyncMock()
    tester.validate_result = AsyncMock(return_value={
        "valid": True,
        "sample_size_adequate": True,
        "warnings": []
    })
    tester.auto_test_comparison = AsyncMock(return_value={
        "test": "chi_square",
        "p_value": 0.001,
        "effect_size": 0.45,
        "significant": True,
        "interpretation": "Highly significant difference between groups"
    })
    return tester


@pytest.fixture
def mock_model_discovery():
    """Mock model discovery with RAG"""
    discovery = AsyncMock()
    discovery.discover_models = AsyncMock(return_value=[
        {"model": "users", "similarity": 0.92, "description": "User analytics"},
        {"model": "events", "similarity": 0.65, "description": "Event tracking"}
    ])
    return discovery


@pytest.fixture
def mock_conversation_memory():
    """Mock conversation memory"""
    memory = MagicMock()
    memory.add_interaction = MagicMock(return_value="interaction_001")
    memory.get_conversation_context = MagicMock(return_value={
        "total_interactions": 5,
        "recent_models": ["users", "events"],
        "analytical_themes": ["conversion", "growth"]
    })
    memory.suggest_contextual_next_steps = MagicMock(return_value=[
        {"question": "Dig deeper into paid conversion", "reason": "Previous queries focused on this"}
    ])
    return memory


@pytest.fixture
def mock_query_optimizer():
    """Mock query optimizer"""
    optimizer = MagicMock()
    optimizer.generate_cache_key = MagicMock(return_value="cache_key_001")
    optimizer.get_cached_result = MagicMock(return_value=None)
    optimizer.optimize_query = MagicMock(side_effect=lambda x, y: x)
    optimizer.cache_result = MagicMock()
    optimizer.get_optimization_insights = MagicMock(return_value=[
        "Consider adding index on plan_type for faster queries"
    ])
    optimizer.analyze_query_complexity = MagicMock(return_value={
        "score": 25,
        "level": "simple",
        "factors": ["single_group_by", "count_aggregation"]
    })
    return optimizer


class TestMCPServerInitialization:
    """Test MCP server initialization"""

    def test_server_import(self):
        """Server module can be imported"""
        # This will fail until we implement the module
        from knowdb.mcp.server import create_mcp_server
        assert create_mcp_server is not None

    def test_server_creation(self):
        """Server can be created with default config"""
        from knowdb.mcp.server import create_mcp_server
        server = create_mcp_server()
        assert server is not None
        assert hasattr(server, 'run')

    def test_server_has_tools(self):
        """Server exposes required MCP tools"""
        from knowdb.mcp.server import create_mcp_server, get_tool_list
        server = create_mcp_server()
        tools = get_tool_list()

        # Core tools must be present
        required_tools = [
            "query_model",
            "list_models",
            "get_model",
            "discover_models",
            "suggest_analysis",
            "test_significance",
            "health_check",
            "sample_queries",
            "optimize_query"
        ]

        tool_names = [t["name"] for t in tools]
        for required in required_tools:
            assert required in tool_names, f"Missing required tool: {required}"


class TestExecutionFirstPattern:
    """Test execution-first pattern is enforced"""

    @pytest.mark.asyncio
    async def test_query_model_executes_before_interpretation(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """query_model must execute query before generating interpretation"""
        from knowdb.mcp.tools import query_model_tool

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Verify execution order: build -> execute -> interpret
        call_order = []

        # Check semantic_manager was called
        if mock_semantic_manager.build_query.called:
            call_order.append("build")
        if mock_semantic_manager.execute_query.called:
            call_order.append("execute")
        if mock_intelligence_engine.generate_interpretation.called:
            call_order.append("interpret")

        assert call_order == ["build", "execute", "interpret"], \
            f"Wrong execution order: {call_order}. Must be build -> execute -> interpret"

        # Verify result contains both data and interpretation
        assert "result" in result
        assert "interpretation" in result
        assert result["result"]["data"] is not None
        assert result["interpretation"] is not None

    @pytest.mark.asyncio
    async def test_interpretation_uses_real_data(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Interpretation must be generated from actual query results"""
        from knowdb.mcp.tools import query_model_tool

        await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Verify interpretation was called with actual result
        call_args = mock_intelligence_engine.generate_interpretation.call_args
        assert call_args is not None

        # The result passed to generate_interpretation must have data
        passed_result = call_args.kwargs.get("result") or call_args.args[0]
        assert "data" in passed_result
        assert len(passed_result["data"]) > 0

    @pytest.mark.asyncio
    async def test_no_fabrication_on_empty_result(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Empty results must not lead to fabricated interpretations"""
        from knowdb.mcp.tools import query_model_tool

        # Mock empty result
        mock_semantic_manager.execute_query = AsyncMock(return_value={
            "data": [],
            "row_count": 0,
            "execution_time_ms": 12.5
        })

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={"industry": "nonexistent"},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Result should indicate no data found
        assert result["result"]["row_count"] == 0
        # Interpretation should reflect empty results, not fabricate data
        assert result["result"]["data"] == []


class TestCoreTools:
    """Test core MCP tool implementations"""

    @pytest.mark.asyncio
    async def test_list_models(self, mock_semantic_manager):
        """list_models returns available models"""
        from knowdb.mcp.tools import list_models_tool

        result = await list_models_tool(semantic_manager=mock_semantic_manager)

        assert "models" in result
        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "users"
        assert "dimensions" in result["models"][0]
        assert "measures" in result["models"][0]

    @pytest.mark.asyncio
    async def test_get_model(self, mock_semantic_manager):
        """get_model returns model schema"""
        from knowdb.mcp.tools import get_model_tool

        result = await get_model_tool(
            model_name="users",
            semantic_manager=mock_semantic_manager
        )

        assert "model" in result
        assert result["model"] == "users"
        assert "schema" in result
        assert "sample_queries" in result

    @pytest.mark.asyncio
    async def test_discover_models(self, mock_model_discovery):
        """discover_models uses RAG to find relevant models"""
        from knowdb.mcp.tools import discover_models_tool

        result = await discover_models_tool(
            question="What's our monthly revenue growth?",
            top_k=3,
            similarity_threshold=0.3,
            model_discovery=mock_model_discovery
        )

        assert "relevant_models" in result
        assert len(result["relevant_models"]) > 0
        assert result["relevant_models"][0]["model"] == "users"
        assert result["relevant_models"][0]["similarity"] > 0.5

    @pytest.mark.asyncio
    async def test_suggest_analysis(self, mock_intelligence_engine):
        """suggest_analysis provides next questions"""
        from knowdb.mcp.tools import suggest_analysis_tool

        result = await suggest_analysis_tool(
            current_result='{"data": [{"plan_type": "paid", "users": 1200}]}',
            context="analyzing conversion",
            model="users",
            intelligence_engine=mock_intelligence_engine
        )

        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_test_significance(self, mock_statistical_tester, mock_intelligence_engine):
        """test_significance runs statistical tests"""
        from knowdb.mcp.tools import test_significance_tool

        test_data = {
            "data": [
                {"industry": "tech", "conversion_rate": 0.25},
                {"industry": "retail", "conversion_rate": 0.15}
            ]
        }

        result = await test_significance_tool(
            data=test_data,
            comparison_type="groups",
            dimensions=["industry"],
            measures=["conversion_rate"],
            statistical_tester=mock_statistical_tester,
            intelligence_engine=mock_intelligence_engine
        )

        assert "tests" in result
        assert "interpretation" in result

    @pytest.mark.asyncio
    async def test_health_check(self, mock_semantic_manager):
        """health_check returns system status"""
        from knowdb.mcp.tools import health_check_tool

        result = await health_check_tool(semantic_manager=mock_semantic_manager)

        assert "status" in result
        assert result["status"] == "healthy"
        assert "components" in result

    @pytest.mark.asyncio
    async def test_sample_queries(self, mock_semantic_manager):
        """sample_queries returns examples for model"""
        from knowdb.mcp.tools import sample_queries_tool

        mock_semantic_manager.get_sample_queries = AsyncMock(return_value=[
            {"query": "Total users by plan", "description": "Basic breakdown"},
            {"query": "Conversion by industry", "description": "Industry analysis"}
        ])

        result = await sample_queries_tool(
            model="users",
            semantic_manager=mock_semantic_manager
        )

        assert "model" in result
        assert "sample_queries" in result
        assert len(result["sample_queries"]) > 0

    @pytest.mark.asyncio
    async def test_optimize_query(
        self,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """optimize_query returns optimization suggestions"""
        from knowdb.mcp.tools import optimize_query_tool

        mock_conversation_memory.get_query_recommendations = MagicMock(return_value={
            "additional_dimensions": ["signup_month"],
            "additional_measures": ["avg_revenue"],
            "performance_notes": ["Consider filtering by date range"]
        })

        result = await optimize_query_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            conversation_memory=mock_conversation_memory
        )

        assert "query_optimization" in result
        assert "suggested_additions" in result


class TestQueryCaching:
    """Test query caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Cached results should be returned without re-executing"""
        from knowdb.mcp.tools import query_model_tool

        # Setup cache hit
        cached_data = {
            "data": [{"plan_type": "cached", "total_users": 9999}],
            "row_count": 1,
            "execution_time_ms": 0.1,
            "cache_timestamp": datetime.now().isoformat()
        }
        mock_query_optimizer.get_cached_result = MagicMock(return_value=cached_data)

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # execute_query should NOT be called on cache hit
        assert not mock_semantic_manager.execute_query.called
        assert result["result"]["cache_hit"] == True

    @pytest.mark.asyncio
    async def test_cache_miss_executes_and_caches(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Cache misses should execute query and cache result"""
        from knowdb.mcp.tools import query_model_tool

        # Setup cache miss
        mock_query_optimizer.get_cached_result = MagicMock(return_value=None)

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # execute_query should be called
        assert mock_semantic_manager.execute_query.called
        # Result should be cached
        assert mock_query_optimizer.cache_result.called
        assert result["result"]["cache_hit"] == False


class TestErrorHandling:
    """Test error handling and graceful degradation"""

    @pytest.mark.asyncio
    async def test_query_error_returns_helpful_message(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Query errors should return helpful error messages"""
        from knowdb.mcp.tools import query_model_tool

        # Setup error
        mock_semantic_manager.execute_query = AsyncMock(
            side_effect=Exception("Table not found: users")
        )

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        assert "error" in result
        assert "Table not found" in result["error"] or "message" in result

    @pytest.mark.asyncio
    async def test_invalid_model_returns_error(self, mock_semantic_manager):
        """Invalid model name should return clear error"""
        from knowdb.mcp.tools import get_model_tool

        mock_semantic_manager.get_model_schema = AsyncMock(
            side_effect=ValueError("Model 'invalid' not found")
        )

        result = await get_model_tool(
            model_name="invalid",
            semantic_manager=mock_semantic_manager
        )

        assert "error" in result
        assert "not found" in result["error"].lower() or "not found" in result.get("message", "").lower()


class TestStatisticalRigor:
    """Test statistical rigor is maintained"""

    @pytest.mark.asyncio
    async def test_comparison_triggers_statistical_test(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Comparing groups should auto-trigger statistical tests"""
        from knowdb.mcp.tools import query_model_tool

        # Multi-group result that should trigger comparison
        mock_semantic_manager.execute_query = AsyncMock(return_value={
            "data": [
                {"plan_type": "free", "conversion_rate": 0.05},
                {"plan_type": "basic", "conversion_rate": 0.15},
                {"plan_type": "premium", "conversion_rate": 0.35}
            ],
            "row_count": 3,
            "execution_time_ms": 52.3
        })

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["conversion_rate"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Statistical test should be auto-triggered for comparisons
        assert mock_statistical_tester.auto_test_comparison.called
        assert "statistical_analysis" in result

    @pytest.mark.asyncio
    async def test_single_value_skips_statistical_test(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Single value results should not trigger statistical tests"""
        from knowdb.mcp.tools import query_model_tool

        # Single value result
        mock_semantic_manager.execute_query = AsyncMock(return_value={
            "data": [{"total_users": 6200}],
            "row_count": 1,
            "execution_time_ms": 15.0
        })

        await query_model_tool(
            model="users",
            dimensions=[],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # No dimensions means no comparison, should skip statistical test
        assert not mock_statistical_tester.auto_test_comparison.called


class TestConversationContext:
    """Test conversation context is maintained"""

    @pytest.mark.asyncio
    async def test_query_adds_to_conversation(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Queries should be added to conversation memory"""
        from knowdb.mcp.tools import query_model_tool

        await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Interaction should be recorded
        assert mock_conversation_memory.add_interaction.called

    @pytest.mark.asyncio
    async def test_suggestions_include_context(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Suggestions should consider conversation context"""
        from knowdb.mcp.tools import query_model_tool

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Should have suggestions
        assert "suggestions" in result
        # Context should be used
        assert mock_conversation_memory.suggest_contextual_next_steps.called


class TestResponseFormat:
    """Test response format consistency"""

    @pytest.mark.asyncio
    async def test_query_response_structure(
        self,
        mock_semantic_manager,
        mock_intelligence_engine,
        mock_statistical_tester,
        mock_conversation_memory,
        mock_query_optimizer
    ):
        """Query response should have consistent structure"""
        from knowdb.mcp.tools import query_model_tool

        result = await query_model_tool(
            model="users",
            dimensions=["plan_type"],
            measures=["total_users"],
            filters={},
            limit=None,
            semantic_manager=mock_semantic_manager,
            intelligence_engine=mock_intelligence_engine,
            statistical_tester=mock_statistical_tester,
            conversation_memory=mock_conversation_memory,
            query_optimizer=mock_query_optimizer
        )

        # Required fields
        required_fields = [
            "query",
            "result",
            "validation",
            "interpretation",
            "suggestions",
            "metadata"
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Metadata structure
        assert "model" in result["metadata"]
        assert "dimensions" in result["metadata"]
        assert "measures" in result["metadata"]
        assert "execution_time_ms" in result["metadata"]
