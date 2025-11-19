"""
MCP Tool Implementations for KnowDB.

Implements execution-first pattern: Build -> Execute -> Annotate
All tools execute queries BEFORE generating interpretations to prevent fabrication.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def query_model_tool(
    model: str,
    dimensions: List[str],
    measures: List[str],
    filters: Dict[str, Any],
    limit: Optional[int],
    semantic_manager,
    intelligence_engine,
    statistical_tester,
    conversation_memory,
    query_optimizer,
) -> Dict[str, Any]:
    """
    Query a semantic model with execution-first pattern.

    CRITICAL: Follows Build -> Execute -> Annotate pattern to prevent fabrication.

    Args:
        model: Name of the semantic model to query
        dimensions: List of dimensions to group by
        measures: List of measures to calculate
        filters: Filters to apply
        limit: Optional row limit
        semantic_manager: Semantic layer manager instance
        intelligence_engine: Intelligence engine for interpretation
        statistical_tester: Statistical testing component
        conversation_memory: Conversation memory instance
        query_optimizer: Query optimizer instance

    Returns:
        Query results with interpretation and suggestions
    """
    try:
        # 1. BUILD: Generate query
        query_info = await semantic_manager.build_query(
            model=model,
            dimensions=dimensions,
            measures=measures,
            filters=filters,
            limit=limit,
        )

        # 2. OPTIMIZE: Check cache
        query_key = query_optimizer.generate_cache_key(query_info)
        cached_result = query_optimizer.get_cached_result(query_key)

        if cached_result:
            result = cached_result
            result["cache_hit"] = True
        else:
            # 3. EXECUTE: Run query to get REAL results
            optimized_query = query_optimizer.optimize_query(
                query_info, conversation_memory
            )
            result = await semantic_manager.execute_query(optimized_query)

            # Cache the result
            query_optimizer.cache_result(query_key, result, query_info)
            result["cache_hit"] = False

        # 4. VALIDATE: Check data quality
        validation = await statistical_tester.validate_result(result, dimensions)

        # 5. ANALYZE: Run statistical tests if comparing groups
        statistical_analysis = None
        if len(dimensions) > 0 and len(result.get("data", [])) > 1:
            statistical_analysis = await statistical_tester.auto_test_comparison(
                result, dimensions, measures
            )

        # 6. ANNOTATE: Generate interpretation based on REAL data
        interpretation = await intelligence_engine.generate_interpretation(
            result=result,
            query_info=query_info,
            validation=validation,
            statistical_analysis=statistical_analysis,
        )

        # 7. SUGGEST: Recommend next questions
        context_suggestions = await intelligence_engine.suggest_next_questions(
            result=result,
            context=f"querying {model} model",
            current_dimensions=dimensions,
            current_measures=measures,
        )

        # 8. MEMORY: Track interaction
        interaction_id = conversation_memory.add_interaction(
            user_question=f"Query {model} model: {dimensions} x {measures}",
            query_info=query_info,
            result=result,
            insights=[interpretation] if interpretation else [],
            statistical_analysis=statistical_analysis,
        )

        # 9. CONTEXTUAL SUGGESTIONS
        contextual_suggestions = conversation_memory.suggest_contextual_next_steps(result)

        # 10. OPTIMIZATION INSIGHTS
        optimization_insights = query_optimizer.get_optimization_insights(
            query_info, result, conversation_memory
        )

        # Combine suggestions
        all_suggestions = contextual_suggestions + context_suggestions
        unique_suggestions = []
        seen_questions = set()

        for suggestion in all_suggestions:
            question = suggestion.get("question", "")
            if question and question not in seen_questions:
                seen_questions.add(question)
                unique_suggestions.append(suggestion)

        return {
            "query": query_info.get("sql", ""),
            "result": result,
            "validation": validation,
            "statistical_analysis": statistical_analysis,
            "interpretation": interpretation,
            "suggestions": unique_suggestions[:5],
            "metadata": {
                "model": model,
                "dimensions": dimensions,
                "measures": measures,
                "filters": filters,
                "execution_time_ms": result.get("execution_time_ms", 0),
                "interaction_id": interaction_id,
                "conversation_context": conversation_memory.get_conversation_context(
                    hours_back=2
                ),
                "optimization": {
                    "cache_hit": result.get("cache_hit", False),
                    "insights": optimization_insights,
                    "query_complexity": query_optimizer.analyze_query_complexity(
                        query_info
                    ),
                },
            },
        }

    except Exception as e:
        logger.error(f"Query failed for model '{model}': {e}")
        return {
            "error": str(e),
            "message": f"Failed to query model '{model}'",
            "query_attempted": {
                "model": model,
                "dimensions": dimensions,
                "measures": measures,
                "filters": filters,
            },
        }


async def list_models_tool(semantic_manager) -> Dict[str, Any]:
    """
    List available semantic models.

    Args:
        semantic_manager: Semantic layer manager instance

    Returns:
        Available models with their descriptions
    """
    try:
        models = await semantic_manager.get_available_models()

        return {
            "models": models,
            "total_count": len(models),
            "description": "Available semantic models for analysis",
        }

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return {
            "error": str(e),
            "message": "Failed to retrieve available models"
        }


async def get_model_tool(model_name: str, semantic_manager) -> Dict[str, Any]:
    """
    Get detailed information about a specific semantic model.

    Args:
        model_name: Name of the model to inspect
        semantic_manager: Semantic layer manager instance

    Returns:
        Model schema including dimensions, measures, and sample queries
    """
    try:
        model_info = await semantic_manager.get_model_schema(model_name)

        return {
            "model": model_name,
            "schema": model_info,
            "sample_queries": model_info.get("sample_queries", []),
        }

    except Exception as e:
        logger.error(f"Failed to get model '{model_name}': {e}")
        return {
            "error": str(e),
            "message": f"Model '{model_name}' not found",
        }


async def discover_models_tool(
    question: str,
    top_k: int,
    similarity_threshold: float,
    model_discovery,
) -> Dict[str, Any]:
    """
    Discover relevant semantic models using RAG.

    Args:
        question: User's natural language question
        top_k: Number of models to return
        similarity_threshold: Minimum similarity score
        model_discovery: Model discovery instance

    Returns:
        Ranked list of relevant models
    """
    try:
        results = await model_discovery.discover_models(
            question, top_k=top_k, similarity_threshold=similarity_threshold
        )

        return {
            "question": question,
            "relevant_models": results,
            "top_model": results[0]["model"] if results else None,
            "status": "success",
            "suggestion": f"Use '{results[0]['model']}' model for this question"
            if results
            else "No models found above similarity threshold",
        }

    except Exception as e:
        logger.error(f"Model discovery failed: {e}")
        return {
            "error": str(e),
            "message": "Failed to discover models for question",
            "status": "error",
        }


async def suggest_analysis_tool(
    current_result: Optional[str],
    context: Optional[str],
    model: Optional[str],
    intelligence_engine,
) -> Dict[str, Any]:
    """
    Suggest next analysis steps based on current results.

    Args:
        current_result: JSON string of current query result
        context: Description of current analysis context
        model: Current model being analyzed
        intelligence_engine: Intelligence engine instance

    Returns:
        Suggested questions and analysis paths
    """
    try:
        # Parse current result if provided
        parsed_result = None
        if current_result:
            try:
                parsed_result = json.loads(current_result)
            except json.JSONDecodeError:
                context = current_result

        suggestions = await intelligence_engine.suggest_analysis_paths(
            current_result=parsed_result, context=context, model=model
        )

        return {
            "suggestions": suggestions,
            "context": context,
            "model": model
        }

    except Exception as e:
        logger.error(f"Failed to suggest analysis: {e}")
        return {
            "error": str(e),
            "message": "Failed to generate analysis suggestions"
        }


async def test_significance_tool(
    data: Dict[str, Any],
    comparison_type: str,
    dimensions: List[str],
    measures: List[str],
    statistical_tester,
    intelligence_engine,
) -> Dict[str, Any]:
    """
    Run statistical significance tests on data.

    Args:
        data: Query result data to test
        comparison_type: Type of test (groups, correlation, trend)
        dimensions: Dimensions being compared
        measures: Measures being analyzed
        statistical_tester: Statistical testing component
        intelligence_engine: Intelligence engine for interpretation

    Returns:
        Statistical test results with interpretation
    """
    try:
        test_results = await statistical_tester.run_significance_tests(
            data=data,
            comparison_type=comparison_type,
            dimensions=dimensions,
            measures=measures,
        )

        interpretation = await intelligence_engine.interpret_statistical_results(
            test_results=test_results, dimensions=dimensions, measures=measures
        )

        return {
            "tests": test_results,
            "interpretation": interpretation,
            "metadata": {
                "comparison_type": comparison_type,
                "dimensions": dimensions,
                "measures": measures,
            },
        }

    except Exception as e:
        logger.error(f"Statistical testing failed: {e}")
        return {
            "error": str(e),
            "message": "Failed to run statistical tests"
        }


async def health_check_tool(semantic_manager) -> Dict[str, Any]:
    """
    Check health of semantic layer and database connections.

    Args:
        semantic_manager: Semantic layer manager instance

    Returns:
        Health status of all system components
    """
    try:
        health_status = await semantic_manager.health_check()

        return {
            "status": "healthy" if health_status["database_connected"] else "unhealthy",
            "components": health_status,
            "timestamp": health_status.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Health check failed",
        }


async def sample_queries_tool(model: str, semantic_manager) -> Dict[str, Any]:
    """
    Get sample queries for a specific model.

    Args:
        model: Name of the model
        semantic_manager: Semantic layer manager instance

    Returns:
        Sample queries with descriptions
    """
    try:
        samples = await semantic_manager.get_sample_queries(model)

        return {
            "model": model,
            "sample_queries": samples
        }

    except Exception as e:
        logger.error(f"Failed to get sample queries for '{model}': {e}")
        return {
            "error": str(e),
            "message": f"Failed to get sample queries for model '{model}'",
        }


async def optimize_query_tool(
    model: str,
    dimensions: List[str],
    measures: List[str],
    filters: Dict[str, Any],
    conversation_memory,
) -> Dict[str, Any]:
    """
    Get query optimization recommendations.

    Args:
        model: Name of the semantic model
        dimensions: Proposed dimensions
        measures: Proposed measures
        filters: Proposed filters
        conversation_memory: Conversation memory instance

    Returns:
        Optimization suggestions and performance recommendations
    """
    try:
        query_info = {
            "model": model,
            "dimensions": dimensions,
            "measures": measures,
            "filters": filters,
        }

        recommendations = conversation_memory.get_query_recommendations(query_info)

        return {
            "query_optimization": recommendations,
            "suggested_additions": {
                "dimensions": recommendations.get("additional_dimensions", [])[:3],
                "measures": recommendations.get("additional_measures", [])[:3],
            },
            "performance_insights": recommendations.get("performance_notes", []),
            "alternative_approaches": recommendations.get("alternative_approaches", []),
        }

    except Exception as e:
        logger.error(f"Query optimization failed for '{model}': {e}")
        return {
            "error": str(e),
            "message": f"Failed to optimize query for model '{model}'",
        }
