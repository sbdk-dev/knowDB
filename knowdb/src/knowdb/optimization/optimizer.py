"""
Query Optimizer for complexity analysis and performance recommendations.

Features:
- Query complexity scoring
- Cache recommendation engine
- Index suggestions
- Query rewriting hints
- Execution plan analysis

Helps achieve optimal cache utilization and query performance.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Query complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class QueryComplexity:
    """Query complexity analysis result.

    Attributes:
        score: Complexity score (0-100)
        level: Complexity level
        factors: Contributing factors
        estimated_time_ms: Estimated execution time
    """
    score: int
    level: str
    factors: List[str] = field(default_factory=list)
    estimated_time_ms: float = 0.0

    @classmethod
    def from_score(cls, score: int, factors: List[str]) -> "QueryComplexity":
        """Create complexity from score."""
        if score < 25:
            level = ComplexityLevel.LOW.value
        elif score < 50:
            level = ComplexityLevel.MEDIUM.value
        elif score < 75:
            level = ComplexityLevel.HIGH.value
        else:
            level = ComplexityLevel.VERY_HIGH.value

        # Rough time estimate based on score
        estimated_time = 10 * (1.5 ** (score / 25))

        return cls(
            score=score,
            level=level,
            factors=factors,
            estimated_time_ms=estimated_time,
        )


@dataclass
class OptimizationSuggestion:
    """Cache optimization suggestion.

    Attributes:
        should_cache: Whether query should be cached
        ttl_recommendation: Recommended TTL in seconds
        reason: Explanation for recommendation
        priority: Suggestion priority (1-10)
    """
    should_cache: bool
    ttl_recommendation: int
    reason: str
    priority: int = 5


@dataclass
class IndexSuggestion:
    """Index suggestion for query optimization.

    Attributes:
        table: Table name
        column: Column to index
        index_type: Type of index
        reason: Why index is suggested
    """
    table: str
    column: str
    index_type: str = "btree"
    reason: str = ""


class QueryOptimizer:
    """
    Query optimizer for complexity analysis and recommendations.

    Analyzes SQL queries to provide:
    - Complexity scoring
    - Cache recommendations
    - Index suggestions
    - Performance hints

    Example:
        >>> optimizer = QueryOptimizer()
        >>> complexity = optimizer.analyze("SELECT * FROM users")
        >>> print(complexity.level)
        'low'
    """

    # Patterns that increase complexity
    COMPLEXITY_PATTERNS = {
        # Joins
        r'\bJOIN\b': 15,
        r'\bLEFT\s+JOIN\b': 15,
        r'\bRIGHT\s+JOIN\b': 15,
        r'\bFULL\s+JOIN\b': 20,
        r'\bCROSS\s+JOIN\b': 25,

        # Subqueries
        r'\(\s*SELECT\b': 20,
        r'\bIN\s*\(\s*SELECT\b': 25,
        r'\bEXISTS\s*\(\s*SELECT\b': 25,

        # Aggregations
        r'\bGROUP\s+BY\b': 10,
        r'\bHAVING\b': 10,
        r'\bCOUNT\s*\(': 5,
        r'\bSUM\s*\(': 5,
        r'\bAVG\s*\(': 5,
        r'\bMAX\s*\(': 5,
        r'\bMIN\s*\(': 5,

        # Window functions
        r'\bOVER\s*\(': 15,
        r'\bPARTITION\s+BY\b': 10,

        # Sorting and limits
        r'\bORDER\s+BY\b': 5,
        r'\bLIMIT\b': -5,  # Reduces complexity

        # Unions
        r'\bUNION\b': 20,
        r'\bINTERSECT\b': 20,
        r'\bEXCEPT\b': 20,

        # Case statements
        r'\bCASE\b': 5,

        # Distinct
        r'\bDISTINCT\b': 10,

        # CTEs
        r'\bWITH\b': 15,
    }

    # Patterns indicating volatile/real-time queries
    VOLATILE_PATTERNS = [
        r'\bNOW\s*\(\)',
        r'\bCURRENT_TIMESTAMP\b',
        r'\bCURRENT_DATE\b',
        r'\bRANDOM\s*\(\)',
        r'\bUUID\s*\(\)',
        r'\'1\s+minute\'',
        r'\'1\s+hour\'',
        r'\breal_time\b',
        r'\blive\b',
    ]

    # Patterns for index suggestions
    WHERE_COLUMN_PATTERN = re.compile(
        r'\bWHERE\b.*?(\w+)\.(\w+)\s*=',
        re.IGNORECASE | re.DOTALL
    )

    SIMPLE_WHERE_PATTERN = re.compile(
        r'\bWHERE\b.*?(\w+)\s*=',
        re.IGNORECASE | re.DOTALL
    )

    def __init__(self):
        """Initialize query optimizer."""
        logger.info("QueryOptimizer initialized")

    def analyze(self, query: str) -> QueryComplexity:
        """Analyze query complexity.

        Scores query based on SQL patterns that affect performance.

        Args:
            query: SQL query string

        Returns:
            QueryComplexity with score and factors
        """
        score = 0
        factors = []

        normalized = query.upper()

        # Check each complexity pattern
        for pattern, points in self.COMPLEXITY_PATTERNS.items():
            matches = len(re.findall(pattern, normalized, re.IGNORECASE))
            if matches > 0:
                score += points * matches
                pattern_name = pattern.replace(r'\b', '').replace(r'\s+', ' ')
                pattern_name = pattern_name.replace('\\', '').replace(r'\(', '')
                if points > 0:
                    factors.append(f"{pattern_name.strip()}: +{points * matches}")

        # Additional factors

        # Number of tables (rough estimate)
        from_matches = re.findall(r'\bFROM\s+(\w+)', normalized)
        join_matches = re.findall(r'\bJOIN\s+(\w+)', normalized)
        num_tables = len(from_matches) + len(join_matches)
        if num_tables > 2:
            table_cost = (num_tables - 2) * 5
            score += table_cost
            factors.append(f"Multiple tables ({num_tables}): +{table_cost}")

        # WHERE clause complexity
        where_conditions = len(re.findall(r'\bAND\b|\bOR\b', normalized))
        if where_conditions > 3:
            cond_cost = (where_conditions - 3) * 3
            score += cond_cost
            factors.append(f"Complex WHERE ({where_conditions} conditions): +{cond_cost}")

        # Ensure non-negative score
        score = max(0, score)

        # Cap at 100
        score = min(100, score)

        return QueryComplexity.from_score(score, factors)

    def suggest_cache_strategy(self, query: str) -> OptimizationSuggestion:
        """Suggest caching strategy for query.

        Analyzes query to determine if caching is beneficial and
        recommends appropriate TTL.

        Args:
            query: SQL query string

        Returns:
            OptimizationSuggestion with cache recommendation
        """
        normalized = query.upper()

        # Check for volatile patterns
        is_volatile = any(
            re.search(pattern, normalized, re.IGNORECASE)
            for pattern in self.VOLATILE_PATTERNS
        )

        if is_volatile:
            return OptimizationSuggestion(
                should_cache=False,
                ttl_recommendation=0,
                reason="Query contains volatile functions (NOW, RANDOM, etc.)",
                priority=1,
            )

        # Analyze complexity
        complexity = self.analyze(query)

        # Determine TTL based on query type
        ttl = 3600  # Default 1 hour

        # Read-only aggregations can be cached longer
        if re.search(r'\bCOUNT\b|\bSUM\b|\bAVG\b', normalized):
            ttl = 7200  # 2 hours
            reason = "Aggregation query - good cache candidate"
        elif re.search(r'\bSELECT\s+\*\s+FROM\b', normalized):
            ttl = 1800  # 30 minutes
            reason = "Full table scan - moderate cache duration"
        elif complexity.score < 25:
            ttl = 3600  # 1 hour
            reason = "Simple query - standard cache duration"
        elif complexity.score < 50:
            ttl = 1800  # 30 minutes
            reason = "Medium complexity - moderate cache duration"
        else:
            ttl = 900  # 15 minutes
            reason = "High complexity - shorter cache duration to reduce stale data"

        # Adjust for specific patterns
        if 'LIMIT' in normalized:
            ttl = max(300, ttl // 2)  # At least 5 minutes
            reason += " (reduced for limited result set)"

        return OptimizationSuggestion(
            should_cache=True,
            ttl_recommendation=ttl,
            reason=reason,
            priority=min(10, complexity.score // 10 + 1),
        )

    def suggest_indexes(self, query: str) -> List[IndexSuggestion]:
        """Suggest indexes for query optimization.

        Analyzes WHERE clauses and JOINs to identify columns
        that would benefit from indexing.

        Args:
            query: SQL query string

        Returns:
            List of IndexSuggestion objects
        """
        suggestions = []
        seen_columns: Set[Tuple[str, str]] = set()

        # Find columns in WHERE clauses with table prefix
        for match in self.WHERE_COLUMN_PATTERN.finditer(query):
            table = match.group(1)
            column = match.group(2)

            if (table, column) not in seen_columns:
                suggestions.append(IndexSuggestion(
                    table=table,
                    column=column,
                    index_type="btree",
                    reason=f"Used in WHERE clause equality condition",
                ))
                seen_columns.add((table, column))

        # Find columns in simple WHERE clauses
        for match in self.SIMPLE_WHERE_PATTERN.finditer(query):
            column = match.group(1)
            # Only add if we don't have a table-prefixed version
            if not any(col == column for _, col in seen_columns):
                suggestions.append(IndexSuggestion(
                    table="<unknown>",
                    column=column,
                    index_type="btree",
                    reason=f"Used in WHERE clause equality condition",
                ))
                seen_columns.add(("<unknown>", column))

        # Find columns in JOIN conditions
        join_pattern = re.compile(
            r'\bJOIN\s+(\w+)\s+\w*\s*ON\s+\w+\.(\w+)\s*=\s*\w+\.(\w+)',
            re.IGNORECASE
        )
        for match in join_pattern.finditer(query):
            table = match.group(1)
            col1 = match.group(2)
            col2 = match.group(3)

            if (table, col1) not in seen_columns:
                suggestions.append(IndexSuggestion(
                    table=table,
                    column=col1,
                    index_type="btree",
                    reason="Used in JOIN condition",
                ))
                seen_columns.add((table, col1))

        # Find ORDER BY columns
        order_pattern = re.compile(
            r'\bORDER\s+BY\s+(?:\w+\.)?(\w+)',
            re.IGNORECASE
        )
        for match in order_pattern.finditer(query):
            column = match.group(1)
            if not any(col == column for _, col in seen_columns):
                suggestions.append(IndexSuggestion(
                    table="<unknown>",
                    column=column,
                    index_type="btree",
                    reason="Used in ORDER BY clause",
                ))
                seen_columns.add(("<unknown>", column))

        return suggestions

    def get_optimization_hints(self, query: str) -> Dict[str, Any]:
        """Get comprehensive optimization hints for query.

        Combines complexity analysis, cache strategy, and index
        suggestions into a single report.

        Args:
            query: SQL query string

        Returns:
            Dictionary with optimization recommendations
        """
        complexity = self.analyze(query)
        cache_strategy = self.suggest_cache_strategy(query)
        index_suggestions = self.suggest_indexes(query)

        return {
            "complexity": {
                "score": complexity.score,
                "level": complexity.level,
                "factors": complexity.factors,
                "estimated_time_ms": complexity.estimated_time_ms,
            },
            "cache": {
                "should_cache": cache_strategy.should_cache,
                "ttl_seconds": cache_strategy.ttl_recommendation,
                "reason": cache_strategy.reason,
            },
            "indexes": [
                {
                    "table": s.table,
                    "column": s.column,
                    "type": s.index_type,
                    "reason": s.reason,
                }
                for s in index_suggestions
            ],
            "recommendations": self._generate_recommendations(
                complexity, cache_strategy, index_suggestions
            ),
        }

    def _generate_recommendations(
        self,
        complexity: QueryComplexity,
        cache_strategy: OptimizationSuggestion,
        index_suggestions: List[IndexSuggestion],
    ) -> List[str]:
        """Generate human-readable recommendations.

        Args:
            complexity: Query complexity analysis
            cache_strategy: Cache suggestion
            index_suggestions: Index suggestions

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Complexity recommendations
        if complexity.score > 50:
            recommendations.append(
                f"Consider breaking down this complex query "
                f"(score: {complexity.score}/100)"
            )

        # Cache recommendations
        if cache_strategy.should_cache:
            recommendations.append(
                f"Cache this query with TTL of {cache_strategy.ttl_recommendation}s: "
                f"{cache_strategy.reason}"
            )
        else:
            recommendations.append(
                f"Avoid caching: {cache_strategy.reason}"
            )

        # Index recommendations
        if index_suggestions:
            columns = [f"{s.table}.{s.column}" for s in index_suggestions]
            recommendations.append(
                f"Consider adding indexes on: {', '.join(columns)}"
            )

        return recommendations
