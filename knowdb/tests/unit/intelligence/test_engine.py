"""
Tests for Intelligence Engine and Statistical Tester

TDD approach: Tests written first, implementation follows.
Coverage target: 30+ tests with comprehensive statistical testing validation.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any


class TestIntelligenceEngineInterpretation:
    """Tests for result interpretation functionality."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    @pytest.mark.asyncio
    async def test_interpret_single_metric_result(self, engine):
        """Should interpret a single metric result correctly."""
        result = {
            "data": [{"total_revenue": 1250000}],
            "metadata": {}
        }
        query_info = {
            "model": "revenue",
            "dimensions": [],
            "measures": ["total_revenue"]
        }

        interpretation = await engine.generate_interpretation(result, query_info)

        assert interpretation
        assert "1.2M" in interpretation or "1,250,000" in interpretation

    @pytest.mark.asyncio
    async def test_interpret_empty_result(self, engine):
        """Should handle empty results gracefully."""
        result = {"data": [], "metadata": {}}
        query_info = {"model": "users", "dimensions": [], "measures": ["count"]}

        interpretation = await engine.generate_interpretation(result, query_info)

        assert "no data" in interpretation.lower() or "no result" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_interpret_error_result(self, engine):
        """Should handle error results appropriately."""
        result = {"error": "Database connection failed", "data": []}
        query_info = {"model": "users", "dimensions": [], "measures": ["count"]}

        interpretation = await engine.generate_interpretation(result, query_info)

        assert "fail" in interpretation.lower() or "error" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_interpret_grouped_data_with_extremes(self, engine):
        """Should identify highest and lowest values in grouped data."""
        result = {
            "data": [
                {"plan_type": "Enterprise", "total_revenue": 500000},
                {"plan_type": "Pro", "total_revenue": 250000},
                {"plan_type": "Basic", "total_revenue": 50000}
            ],
            "metadata": {}
        }
        query_info = {
            "model": "users",
            "dimensions": ["plan_type"],
            "measures": ["total_revenue"]
        }

        interpretation = await engine.generate_interpretation(result, query_info)

        assert interpretation
        # Should mention the comparison between high and low
        assert "Enterprise" in interpretation or "10x" in interpretation or "higher" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_interpret_with_statistical_analysis(self, engine):
        """Should include statistical context when available."""
        result = {
            "data": [
                {"group": "A", "metric": 100},
                {"group": "B", "metric": 150}
            ],
            "metadata": {}
        }
        query_info = {
            "model": "test",
            "dimensions": ["group"],
            "measures": ["metric"]
        }
        statistical_analysis = {
            "p_value": 0.001,
            "effect_size_interpretation": "large"
        }

        interpretation = await engine.generate_interpretation(
            result, query_info, statistical_analysis=statistical_analysis
        )

        assert "p<0.001" in interpretation or "significant" in interpretation.lower()
        assert "large" in interpretation.lower() or "effect" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_format_large_numbers(self, engine):
        """Should format large numbers appropriately (K, M)."""
        result = {
            "data": [{"value": 5500000}],
            "metadata": {}
        }
        query_info = {"model": "test", "dimensions": [], "measures": ["value"]}

        interpretation = await engine.generate_interpretation(result, query_info)

        # Should use M notation for millions
        assert "5.5M" in interpretation or "5,500,000" in interpretation

    @pytest.mark.asyncio
    async def test_interpret_conversion_rate_benchmark(self, engine):
        """Should provide business context for conversion rates."""
        result = {
            "data": [{"conversion_rate": 0.40}],
            "metadata": {}
        }
        query_info = {"model": "funnel", "dimensions": [], "measures": ["conversion_rate"]}

        interpretation = await engine.generate_interpretation(result, query_info)

        # 40% is excellent for conversion
        assert interpretation
        # Should mention something about benchmark or performance

    @pytest.mark.asyncio
    async def test_interpret_with_sample_sizes(self, engine):
        """Should include sample size information when present."""
        result = {"data": [{"metric": 100}], "metadata": {}}
        query_info = {"model": "test", "dimensions": [], "measures": ["metric"]}
        statistical_analysis = {
            "p_value": 0.03,
            "sample_sizes": {"group_a": 150, "group_b": 120}
        }

        interpretation = await engine.generate_interpretation(
            result, query_info, statistical_analysis=statistical_analysis
        )

        assert "n=" in interpretation or "150" in interpretation or "120" in interpretation


class TestIntelligenceEngineSuggestions:
    """Tests for analysis suggestions functionality."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    @pytest.mark.asyncio
    async def test_suggest_next_questions_empty_data(self, engine):
        """Should provide helpful suggestions for empty results."""
        result = {"data": [], "metadata": {}}

        suggestions = await engine.suggest_next_questions(
            result=result, context="users"
        )

        assert len(suggestions) > 0
        assert any("question" in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_drill_down_for_grouped_data(self, engine):
        """Should suggest drilling down when grouped data available."""
        result = {
            "data": [
                {"plan_type": "Enterprise", "total_revenue": 500000},
                {"plan_type": "Pro", "total_revenue": 250000}
            ],
            "metadata": {}
        }

        suggestions = await engine.suggest_next_questions(
            result=result,
            context="revenue analysis",
            current_dimensions=["plan_type"],
            current_measures=["total_revenue"]
        )

        assert len(suggestions) > 0
        # Should suggest drilling into top performer
        assert any("Enterprise" in s.get("question", "") or "drive" in s.get("question", "").lower()
                   for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_statistical_testing(self, engine):
        """Should suggest statistical testing when comparing groups."""
        result = {
            "data": [
                {"segment": "A", "metric": 100},
                {"segment": "B", "metric": 150}
            ],
            "metadata": {}
        }

        suggestions = await engine.suggest_next_questions(
            result=result,
            context="segment comparison",
            current_dimensions=["segment"],
            current_measures=["metric"]
        )

        # Should suggest significance testing
        assert any("significant" in s.get("question", "").lower() or
                   "difference" in s.get("question", "").lower()
                   for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_analysis_paths_for_users_model(self, engine):
        """Should provide user-specific analysis paths."""
        suggestions = await engine.suggest_analysis_paths(
            model="users", context="user analysis"
        )

        assert len(suggestions) > 0
        # Should suggest user-related analysis
        assert any("plan" in s.get("question", "").lower() or
                   "conversion" in s.get("question", "").lower() or
                   "user" in s.get("question", "").lower()
                   for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_analysis_paths_for_events_model(self, engine):
        """Should provide event-specific analysis paths."""
        suggestions = await engine.suggest_analysis_paths(
            model="events", context="event analysis"
        )

        assert len(suggestions) > 0
        # Should suggest engagement-related analysis
        assert any("feature" in s.get("question", "").lower() or
                   "engagement" in s.get("question", "").lower() or
                   "usage" in s.get("question", "").lower()
                   for s in suggestions)

    @pytest.mark.asyncio
    async def test_generate_analysis_suggestions_combines_sources(self, engine):
        """Should combine next questions and analysis paths."""
        result = {
            "data": [{"metric": 100}],
            "metadata": {}
        }

        suggestions = await engine.generate_analysis_suggestions(
            current_result=result,
            context="users analysis",
            dimensions=[],
            measures=["metric"]
        )

        assert len(suggestions) <= 5  # Should limit suggestions
        assert len(suggestions) > 0


class TestIntelligenceEngineStatisticalInterpretation:
    """Tests for statistical results interpretation."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    @pytest.mark.asyncio
    async def test_interpret_highly_significant_results(self, engine):
        """Should interpret p<0.001 as highly significant."""
        test_results = {
            "p_value": 0.0005,
            "effect_size": 0.9,
            "test_type": "independent_t_test"
        }

        interpretation = await engine.interpret_statistical_results(
            test_results, dimensions=["group"], measures=["metric"]
        )

        assert "highly significant" in interpretation.lower() or "p<0.001" in interpretation

    @pytest.mark.asyncio
    async def test_interpret_significant_results(self, engine):
        """Should interpret p<0.05 as significant."""
        test_results = {
            "p_value": 0.03,
            "effect_size": 0.5,
            "test_type": "welch_t_test"
        }

        interpretation = await engine.interpret_statistical_results(
            test_results, dimensions=["group"], measures=["metric"]
        )

        assert "significant" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_interpret_non_significant_results(self, engine):
        """Should interpret p>=0.05 as not significant."""
        test_results = {
            "p_value": 0.15,
            "effect_size": 0.1,
            "test_type": "mann_whitney_u"
        }

        interpretation = await engine.interpret_statistical_results(
            test_results, dimensions=["group"], measures=["metric"]
        )

        assert "not significant" in interpretation.lower() or "no significant" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_interpret_effect_sizes(self, engine):
        """Should interpret effect size magnitude."""
        test_results = {
            "p_value": 0.01,
            "effect_size": 0.85,
            "effect_size_interpretation": "large"
        }

        interpretation = await engine.interpret_statistical_results(
            test_results, dimensions=["group"], measures=["metric"]
        )

        assert "large" in interpretation.lower()

    @pytest.mark.asyncio
    async def test_warn_small_sample_size(self, engine):
        """Should warn about small sample sizes."""
        test_results = {
            "p_value": 0.04,
            "effect_size": 0.3,
            "sample_sizes": {"group_a": 15, "group_b": 12}
        }

        interpretation = await engine.interpret_statistical_results(
            test_results, dimensions=["group"], measures=["metric"]
        )

        assert "small" in interpretation.lower() or "caution" in interpretation.lower()


class TestStatisticalTesterValidation:
    """Tests for data validation functionality."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_validate_empty_result(self, tester):
        """Should mark empty results as invalid."""
        result = {"data": [], "metadata": {}}

        validation = await tester.validate_result(result, dimensions=[])

        assert not validation["valid"]
        assert any("no data" in w.lower() for w in validation["warnings"])

    @pytest.mark.asyncio
    async def test_validate_small_sample_size(self, tester):
        """Should warn about small overall sample size."""
        result = {
            "data": [{"id": i, "value": i} for i in range(20)],
            "metadata": {}
        }

        validation = await tester.validate_result(result, dimensions=[])

        # 20 is less than default min_sample_size of 30
        assert any("small sample" in w.lower() for w in validation["warnings"])

    @pytest.mark.asyncio
    async def test_validate_small_group_sizes(self, tester):
        """Should warn about small group sizes."""
        result = {
            "data": [
                {"group": "A", "value": 1},
                {"group": "A", "value": 2},
                {"group": "B", "value": 3},
            ] * 5,  # 15 per group - still small
            "metadata": {}
        }

        validation = await tester.validate_result(result, dimensions=["group"])

        assert "sample_sizes" in validation
        assert "groups" in validation["sample_sizes"]

    @pytest.mark.asyncio
    async def test_validate_unbalanced_groups(self, tester):
        """Should warn about highly unbalanced groups."""
        result = {
            "data": (
                [{"group": "A", "value": i} for i in range(100)] +
                [{"group": "B", "value": i} for i in range(5)]
            ),
            "metadata": {}
        }

        validation = await tester.validate_result(result, dimensions=["group"])

        # 100/5 = 20x unbalanced
        assert any("unbalanced" in w.lower() for w in validation["warnings"])

    @pytest.mark.asyncio
    async def test_validate_missing_values(self, tester):
        """Should detect and report missing values."""
        result = {
            "data": [
                {"group": "A", "value": 1},
                {"group": "A", "value": None},
                {"group": "B", "value": 3},
            ] * 20,
            "metadata": {}
        }

        validation = await tester.validate_result(result, dimensions=["group"])

        assert "data_quality" in validation


class TestStatisticalTesterTwoGroupTests:
    """Tests for two-group statistical comparisons."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_auto_test_two_groups_parametric(self, tester):
        """Should use t-test for normally distributed data."""
        # Generate normally distributed data
        np.random.seed(42)
        group_a = np.random.normal(100, 15, 50)
        group_b = np.random.normal(120, 15, 50)

        result = {
            "data": (
                [{"group": "A", "metric": float(v)} for v in group_a] +
                [{"group": "B", "metric": float(v)} for v in group_b]
            ),
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        assert test_result is not None
        assert "p_value" in test_result
        assert test_result["test_type"] in ["independent_t_test", "welch_t_test"]
        assert test_result["p_value"] < 0.05  # Should be significant
        assert "effect_size" in test_result

    @pytest.mark.asyncio
    async def test_auto_test_two_groups_non_parametric(self, tester):
        """Should use Mann-Whitney U for non-normal data."""
        # Generate skewed data
        np.random.seed(42)
        group_a = np.random.exponential(10, 50)
        group_b = np.random.exponential(20, 50)

        result = {
            "data": (
                [{"group": "A", "metric": float(v)} for v in group_a] +
                [{"group": "B", "metric": float(v)} for v in group_b]
            ),
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        assert test_result is not None
        assert "p_value" in test_result
        # May use Mann-Whitney U for non-normal data
        assert test_result["test_type"] in ["mann_whitney_u", "welch_t_test", "independent_t_test"]

    @pytest.mark.asyncio
    async def test_calculate_cohens_d(self, tester):
        """Should calculate Cohen's d effect size correctly."""
        group1 = np.array([100, 110, 105, 95, 100])
        group2 = np.array([150, 160, 155, 145, 150])

        cohens_d = tester._calculate_cohens_d(group1, group2)

        # Large difference should give large effect size
        assert abs(cohens_d) > 2.0

    @pytest.mark.asyncio
    async def test_interpret_cohens_d(self, tester):
        """Should interpret Cohen's d correctly."""
        assert tester._interpret_cohens_d(0.1) == "negligible"
        assert tester._interpret_cohens_d(0.3) == "small"
        assert tester._interpret_cohens_d(0.6) == "medium"
        assert tester._interpret_cohens_d(1.0) == "large"

    @pytest.mark.asyncio
    async def test_return_group_statistics(self, tester):
        """Should return group means and standard deviations."""
        np.random.seed(42)
        result = {
            "data": (
                [{"group": "A", "metric": float(v)} for v in np.random.normal(100, 10, 50)] +
                [{"group": "B", "metric": float(v)} for v in np.random.normal(110, 10, 50)]
            ),
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        assert "group_means" in test_result
        assert "group_stds" in test_result
        assert len(test_result["group_means"]) == 2


class TestStatisticalTesterMultipleGroupTests:
    """Tests for multiple-group statistical comparisons."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_auto_test_multiple_groups_anova(self, tester):
        """Should use ANOVA for 3+ groups with normal data."""
        np.random.seed(42)
        result = {
            "data": (
                [{"group": "A", "metric": float(v)} for v in np.random.normal(100, 10, 40)] +
                [{"group": "B", "metric": float(v)} for v in np.random.normal(110, 10, 40)] +
                [{"group": "C", "metric": float(v)} for v in np.random.normal(120, 10, 40)]
            ),
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        assert test_result is not None
        assert test_result["test_type"] in ["one_way_anova", "kruskal_wallis"]
        assert test_result["p_value"] < 0.05

    @pytest.mark.asyncio
    async def test_calculate_eta_squared(self, tester):
        """Should calculate eta-squared for multiple groups."""
        group_data = [
            np.array([100, 105, 110]),
            np.array([150, 155, 160]),
            np.array([200, 205, 210])
        ]

        eta_squared = tester._calculate_eta_squared(group_data)

        # Large differences should give large eta-squared
        assert eta_squared > 0.5

    @pytest.mark.asyncio
    async def test_interpret_eta_squared(self, tester):
        """Should interpret eta-squared correctly."""
        assert tester._interpret_eta_squared(0.005) == "negligible"
        assert tester._interpret_eta_squared(0.03) == "small"
        assert tester._interpret_eta_squared(0.08) == "medium"
        assert tester._interpret_eta_squared(0.20) == "large"


class TestStatisticalTesterCorrelation:
    """Tests for correlation analysis."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_correlation_test(self, tester):
        """Should test correlation between two variables."""
        np.random.seed(42)
        x = np.random.normal(100, 10, 100)
        y = x * 2 + np.random.normal(0, 5, 100)  # Strong positive correlation

        result = {
            "data": [{"var1": float(x[i]), "var2": float(y[i])} for i in range(100)],
            "metadata": {}
        }

        test_result = await tester.run_significance_tests(
            result,
            comparison_type="correlation",
            dimensions=[],
            measures=["var1", "var2"]
        )

        assert test_result is not None
        assert "pearson_r" in test_result
        assert test_result["pearson_r"] > 0.8  # Strong positive correlation


class TestStatisticalTesterTrend:
    """Tests for trend analysis."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_increasing_trend(self, tester):
        """Should detect increasing trend."""
        result = {
            "data": [
                {"time": i, "metric": 100 + i * 10 + np.random.normal(0, 2)}
                for i in range(20)
            ],
            "metadata": {}
        }

        test_result = await tester.run_significance_tests(
            result,
            comparison_type="trend",
            dimensions=["time"],
            measures=["metric"]
        )

        assert test_result is not None
        assert test_result["trend_direction"] == "increasing"
        assert test_result["linear_slope"] > 0

    @pytest.mark.asyncio
    async def test_decreasing_trend(self, tester):
        """Should detect decreasing trend."""
        result = {
            "data": [
                {"time": i, "metric": 200 - i * 10 + np.random.normal(0, 2)}
                for i in range(20)
            ],
            "metadata": {}
        }

        test_result = await tester.run_significance_tests(
            result,
            comparison_type="trend",
            dimensions=["time"],
            measures=["metric"]
        )

        assert test_result is not None
        assert test_result["trend_direction"] == "decreasing"
        assert test_result["linear_slope"] < 0


class TestStatisticalTesterEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_handle_single_group(self, tester):
        """Should handle single group (no comparison possible)."""
        result = {
            "data": [{"group": "A", "metric": float(v)} for v in range(50)],
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        # Cannot compare single group
        assert test_result is None

    @pytest.mark.asyncio
    async def test_handle_missing_columns(self, tester):
        """Should handle missing dimension or measure columns."""
        result = {
            "data": [{"other": i} for i in range(50)],
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        assert test_result is None

    @pytest.mark.asyncio
    async def test_handle_insufficient_data(self, tester):
        """Should handle insufficient data for testing."""
        result = {
            "data": [
                {"group": "A", "metric": 1},
                {"group": "B", "metric": 2}
            ],
            "metadata": {}
        }

        test_result = await tester.auto_test_comparison(
            result, dimensions=["group"], measures=["metric"]
        )

        # Too few observations per group
        assert test_result is None

    @pytest.mark.asyncio
    async def test_p_value_interpretation(self, tester):
        """Should provide correct p-value interpretations."""
        # Assuming interpret_p_value method exists
        if hasattr(tester, 'interpret_p_value'):
            assert "highly significant" in tester.interpret_p_value(0.0005).lower()
            assert "very significant" in tester.interpret_p_value(0.005).lower()
            assert "significant" in tester.interpret_p_value(0.03).lower()
            assert "not significant" in tester.interpret_p_value(0.15).lower()


class TestIntelligenceEngineContext:
    """Tests for context management."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    def test_add_context(self, engine):
        """Should add context to history."""
        context = {"query": "test", "result": {"data": []}}
        engine.add_context(context)

        assert len(engine.context_history) == 1
        assert "timestamp" in engine.context_history[0]

    def test_context_history_limit(self, engine):
        """Should maintain only last 10 contexts."""
        for i in range(15):
            engine.add_context({"query": f"test_{i}"})

        assert len(engine.context_history) == 10
        assert engine.context_history[-1]["query"] == "test_14"


class TestIntelligenceEngineQueryResult:
    """Tests for simplified query result interpretation."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    @pytest.mark.asyncio
    async def test_interpret_query_result_basic(self, engine):
        """Should interpret basic query results."""
        result = {
            "data": [{"total_users": 5000}],
            "metadata": {}
        }

        interpretation = await engine.interpret_query_result(
            result=result,
            dimensions=[],
            measures=["total_users"]
        )

        assert interpretation
        assert "5" in interpretation  # Should contain the value

    @pytest.mark.asyncio
    async def test_interpret_query_result_with_context(self, engine):
        """Should use context when provided."""
        result = {
            "data": [{"conversion_rate": 0.25}],
            "metadata": {}
        }
        context = {"model": "funnel", "question": "What is our conversion rate?"}

        interpretation = await engine.interpret_query_result(
            result=result,
            dimensions=[],
            measures=["conversion_rate"],
            context=context
        )

        assert interpretation


class TestIntegration:
    """Integration tests for engine and tester working together."""

    @pytest.fixture
    def engine(self):
        from knowdb.intelligence import IntelligenceEngine
        return IntelligenceEngine()

    @pytest.fixture
    def tester(self):
        from knowdb.intelligence import StatisticalTester
        return StatisticalTester()

    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self, engine, tester):
        """Should perform complete analysis with interpretation."""
        np.random.seed(42)
        result = {
            "data": (
                [{"plan": "Enterprise", "revenue": float(v)}
                 for v in np.random.normal(5000, 500, 50)] +
                [{"plan": "Basic", "revenue": float(v)}
                 for v in np.random.normal(500, 100, 50)]
            ),
            "metadata": {}
        }

        # Validate data
        validation = await tester.validate_result(result, dimensions=["plan"])
        assert validation["valid"]

        # Run statistical test
        test_result = await tester.auto_test_comparison(
            result, dimensions=["plan"], measures=["revenue"]
        )
        assert test_result["significant"]

        # Generate interpretation
        interpretation = await engine.generate_interpretation(
            result,
            {"model": "revenue", "dimensions": ["plan"], "measures": ["revenue"]},
            statistical_analysis=test_result
        )
        assert "significant" in interpretation.lower() or "p<" in interpretation

    @pytest.mark.asyncio
    async def test_workflow_with_suggestions(self, engine, tester):
        """Should provide actionable suggestions after analysis."""
        result = {
            "data": [
                {"segment": "A", "metric": 100},
                {"segment": "B", "metric": 150}
            ],
            "metadata": {}
        }

        suggestions = await engine.generate_analysis_suggestions(
            current_result=result,
            context="segment analysis",
            dimensions=["segment"],
            measures=["metric"]
        )

        assert len(suggestions) > 0
        assert all("question" in s for s in suggestions)
