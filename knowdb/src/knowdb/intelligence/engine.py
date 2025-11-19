"""
Intelligence Engine for KnowDB

Generates natural language interpretations, analysis suggestions, and insights
based on query results. Implements execution-first pattern to prevent fabrication.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class IntelligenceEngine:
    """Generates natural language interpretations and analysis suggestions."""

    def __init__(self):
        self.context_history: List[Dict[str, Any]] = []
        self.business_benchmarks: Dict[str, Any] = {}

    async def generate_interpretation(
        self,
        result: Dict[str, Any],
        query_info: Dict[str, Any],
        validation: Optional[Dict[str, Any]] = None,
        statistical_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate natural language interpretation based on REAL query results.

        CRITICAL: This method only operates on executed results to prevent fabrication.
        """

        if result.get("error"):
            return f"Query failed: {result['error']}"

        data = result.get("data", [])
        if not data:
            return "No data returned for this query."

        model = query_info.get("model", "")
        dimensions = query_info.get("dimensions", [])
        measures = query_info.get("measures", [])

        # Start with basic observations
        observations = []

        # Data shape observation
        row_count = len(data)
        if row_count == 1:
            observations.append("Single result")
        else:
            observations.append(f"{row_count} results")

        # Key findings from actual data
        if row_count > 0:
            first_row = data[0]

            # For single metrics (no dimensions)
            if not dimensions and measures:
                for measure in measures:
                    if measure in first_row:
                        value = first_row[measure]
                        formatted_value = self._format_number(value)
                        observations.append(f"{measure}: {formatted_value}")

            # For grouped data (with dimensions)
            elif dimensions and len(data) > 1:
                dimension = dimensions[0]  # Focus on first dimension

                # Find highest and lowest values
                if measures:
                    measure = measures[0]  # Focus on first measure

                    # Sort data by measure to find extremes
                    sorted_data = sorted(
                        data,
                        key=lambda x: (
                            x.get(measure, 0) if x.get(measure) is not None else 0
                        ),
                        reverse=True,
                    )

                    highest = sorted_data[0]
                    lowest = sorted_data[-1]

                    highest_val = highest.get(measure, 0)
                    lowest_val = lowest.get(measure, 0)

                    # Calculate ratio if both values are positive
                    if highest_val > 0 and lowest_val > 0:
                        ratio = highest_val / lowest_val
                        if ratio >= 2:
                            observations.append(
                                f"{highest.get(dimension)} {ratio:.1f}x higher {measure} than {lowest.get(dimension)}"
                            )
                        else:
                            diff_pct = ((highest_val - lowest_val) / lowest_val) * 100
                            observations.append(
                                f"{highest.get(dimension)} {diff_pct:.0f}% higher {measure}"
                            )
                    else:
                        observations.append(
                            f"Range: {highest.get(dimension)} ({self._format_number(highest_val)}) to {lowest.get(dimension)} ({self._format_number(lowest_val)})"
                        )

        # Add statistical context if available
        if statistical_analysis:
            p_value = statistical_analysis.get("p_value")
            if p_value is not None:
                if p_value < 0.001:
                    observations.append("(p<0.001, highly significant)")
                elif p_value < 0.01:
                    observations.append("(p<0.01, significant)")
                elif p_value < 0.05:
                    observations.append(f"(p={p_value:.3f}, significant)")
                else:
                    observations.append(f"(p={p_value:.3f}, not significant)")

            # Add effect size if available
            effect_size = statistical_analysis.get("effect_size_interpretation")
            if effect_size:
                observations.append(f"{effect_size} effect")

            # Add sample size context
            sample_sizes = statistical_analysis.get("sample_sizes")
            if sample_sizes:
                n_values = [f"n={n}" for n in sample_sizes.values()]
                observations.append(f"({', '.join(n_values)})")

        # Add validation warnings
        if validation:
            warnings = validation.get("warnings", [])
            for warning in warnings:
                observations.append(f"Warning: {warning}")

        # Add business context if available
        business_context = self._get_business_context(model, measures, data)
        if business_context:
            observations.append(business_context)

        return " | ".join(observations)

    def _format_number(self, value: Any) -> str:
        """Format numbers for display."""
        if not isinstance(value, (int, float)):
            return str(value)

        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        elif isinstance(value, float):
            if value == int(value):
                return f"{int(value):,}"
            elif value < 1:
                return f"{value:.2%}" if value <= 1 else f"{value:.2f}"
            else:
                return f"{value:,.1f}"
        else:
            return f"{value:,}"

    def _get_business_context(
        self, model: str, measures: List[str], data: List[Dict]
    ) -> str:
        """Add business context based on benchmarks and industry standards."""

        if not measures or not data:
            return ""

        context_parts = []

        # Conversion rate benchmarks
        if "conversion_rate" in measures:
            for row in data:
                rate = row.get("conversion_rate")
                if rate is not None:
                    rate_pct = rate * 100 if rate <= 1 else rate
                    if rate_pct > 35:
                        context_parts.append("(excellent vs 15% median)")
                    elif rate_pct > 20:
                        context_parts.append("(above average vs 15% median)")
                    elif rate_pct < 10:
                        context_parts.append("(below average vs 15% median)")
                    break

        # DAU/MAU stickiness benchmarks
        if "daily_stickiness" in measures:
            for row in data:
                stickiness = row.get("daily_stickiness")
                if stickiness is not None:
                    stickiness_pct = stickiness * 100 if stickiness <= 1 else stickiness
                    if stickiness_pct > 25:
                        context_parts.append("(excellent vs 13% median)")
                    elif stickiness_pct > 20:
                        context_parts.append("(above average)")
                    elif stickiness_pct < 10:
                        context_parts.append("(below 13% median)")
                    break

        # Events per user benchmarks
        if "events_per_user" in measures:
            for row in data:
                events = row.get("events_per_user")
                if events is not None and events > 50:
                    context_parts.append("(high engagement)")
                    break

        return " ".join(context_parts)

    async def suggest_next_questions(
        self,
        result: Dict[str, Any],
        context: str,
        current_dimensions: List[str] = None,
        current_measures: List[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Suggest logical next analysis questions based on current results.

        Uses actual result patterns to generate relevant follow-up questions.
        """
        if current_dimensions is None:
            current_dimensions = []
        if current_measures is None:
            current_measures = []

        suggestions = []
        data = result.get("data", [])

        if not data:
            return [
                {
                    "question": "Try a different time period or filter",
                    "reason": "No data returned",
                }
            ]

        # Suggest drilling down if we have grouped results
        if len(data) > 1 and current_dimensions:
            dim = current_dimensions[0]

            # Find interesting values to drill into
            if current_measures:
                measure = current_measures[0]
                sorted_data = sorted(
                    data,
                    key=lambda x: (
                        x.get(measure, 0) if x.get(measure) is not None else 0
                    ),
                    reverse=True,
                )

                if len(sorted_data) >= 2:
                    top_value = sorted_data[0].get(dim)
                    suggestions.append(
                        {
                            "question": f"What drives high {measure} in {top_value}?",
                            "reason": "Drill into top performer",
                        }
                    )

        # Suggest time-based analysis
        if "conversion_rate" in current_measures:
            suggestions.append(
                {
                    "question": "How has conversion rate changed over time?",
                    "reason": "Track trend of key metric",
                }
            )

        if "events_per_user" in current_measures:
            suggestions.append(
                {
                    "question": "Which features drive highest engagement?",
                    "reason": "Understand engagement drivers",
                }
            )

        # Suggest statistical testing if comparing groups
        if len(data) > 1 and current_dimensions:
            measure_name = current_measures[0] if current_measures else "metrics"
            suggestions.append(
                {
                    "question": f"Is this difference in {measure_name} by {current_dimensions[0]} statistically significant?",
                    "reason": "Validate observed differences",
                }
            )

        # Suggest cross-model analysis
        if context and "users" in context.lower():
            suggestions.append(
                {
                    "question": "How does feature usage vary by plan type?",
                    "reason": "Connect user segments to behavior",
                }
            )

        if context and "events" in context.lower():
            suggestions.append(
                {
                    "question": "What's the retention rate for high-engagement users?",
                    "reason": "Link engagement to retention",
                }
            )

        # Default suggestions if we have no specific patterns
        if not suggestions:
            suggestions.extend(
                [
                    {
                        "question": "What are the key trends over time?",
                        "reason": "Understand temporal patterns",
                    },
                    {
                        "question": "How do different user segments compare?",
                        "reason": "Identify segment differences",
                    },
                    {
                        "question": "Which factors correlate with this outcome?",
                        "reason": "Find potential drivers",
                    },
                ]
            )

        return suggestions[:4]  # Limit to 4 suggestions

    async def suggest_analysis_paths(
        self,
        current_result: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Suggest analysis paths based on current context and model.
        """

        suggestions = []

        # Model-specific starting questions
        if model == "users":
            suggestions.extend(
                [
                    {
                        "question": "What's our conversion rate by plan type?",
                        "reason": "Understand pricing tier performance",
                    },
                    {
                        "question": "How does user distribution vary by industry?",
                        "reason": "Identify target market concentration",
                    },
                    {
                        "question": "What's the signup trend over time?",
                        "reason": "Track growth patterns",
                    },
                ]
            )

        elif model == "events":
            suggestions.extend(
                [
                    {
                        "question": "Which features are most popular?",
                        "reason": "Identify core product usage",
                    },
                    {
                        "question": "How does engagement vary by plan type?",
                        "reason": "Connect usage to monetization",
                    },
                    {
                        "question": "What's the daily active user trend?",
                        "reason": "Monitor engagement health",
                    },
                ]
            )

        elif model == "engagement":
            suggestions.extend(
                [
                    {
                        "question": "What's our current DAU/MAU stickiness?",
                        "reason": "Measure engagement frequency",
                    },
                    {
                        "question": "How does retention vary by signup cohort?",
                        "reason": "Track cohort performance",
                    },
                    {
                        "question": "What's the 7-day retention rate?",
                        "reason": "Assess onboarding success",
                    },
                ]
            )

        # Context-based suggestions
        if current_result and current_result.get("data"):
            data = current_result["data"]
            if len(data) > 1:
                suggestions.append(
                    {
                        "question": "What explains these differences?",
                        "reason": "Understand variation drivers",
                    }
                )

        # General analytical approaches
        if not suggestions:
            suggestions.extend(
                [
                    {
                        "question": "What are our key performance indicators?",
                        "reason": "Establish baseline metrics",
                    },
                    {
                        "question": "Which user segments are most valuable?",
                        "reason": "Identify high-value cohorts",
                    },
                    {
                        "question": "What drives user engagement?",
                        "reason": "Find engagement levers",
                    },
                ]
            )

        return suggestions

    async def interpret_statistical_results(
        self, test_results: Dict[str, Any], dimensions: List[str], measures: List[str]
    ) -> str:
        """
        Generate natural language interpretation of statistical test results.
        """

        if not test_results:
            return "No statistical analysis available."

        interpretations = []

        # P-value interpretation
        p_value = test_results.get("p_value")
        if p_value is not None:
            if p_value < 0.001:
                interpretations.append("Highly significant difference (p<0.001)")
            elif p_value < 0.01:
                interpretations.append("Significant difference (p<0.01)")
            elif p_value < 0.05:
                interpretations.append(f"Significant difference (p={p_value:.3f})")
            else:
                interpretations.append(f"No significant difference (p={p_value:.3f})")

        # Effect size interpretation
        effect_size = test_results.get("effect_size")
        effect_interpretation = test_results.get("effect_size_interpretation")

        if effect_interpretation:
            interpretations.append(f"{effect_interpretation.lower()} effect size")
        elif effect_size is not None:
            if effect_size > 0.8:
                interpretations.append("large effect size")
            elif effect_size > 0.5:
                interpretations.append("medium effect size")
            elif effect_size > 0.2:
                interpretations.append("small effect size")
            else:
                interpretations.append("negligible effect size")

        # Sample size context
        sample_sizes = test_results.get("sample_sizes", {})
        if sample_sizes:
            total_n = sum(sample_sizes.values())
            min_n = min(sample_sizes.values())

            if min_n < 30:
                interpretations.append("Small sample size - interpret with caution")
            elif total_n > 1000:
                interpretations.append("Large sample size - high statistical power")

        # Test type context
        test_type = test_results.get("test_type", "")
        if test_type:
            interpretations.append(f"({test_type} test)")

        # Practical significance
        if dimensions and measures:
            dim_name = dimensions[0] if dimensions else "groups"
            measure_name = measures[0] if measures else "outcome"

            if p_value and p_value < 0.05 and effect_size and effect_size > 0.2:
                interpretations.append(
                    f"Meaningful difference in {measure_name} across {dim_name}"
                )
            elif p_value and p_value < 0.05 and effect_size and effect_size <= 0.2:
                interpretations.append(
                    "Statistically significant but small practical difference"
                )

        return " | ".join(interpretations)

    async def interpret_query_result(
        self,
        result: Dict[str, Any],
        dimensions: List[str] = None,
        measures: List[str] = None,
        statistical_analysis: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate natural language interpretation of query results.

        This is a simplified interface to generate_interpretation() that matches
        the expected signature from tests.
        """
        if dimensions is None:
            dimensions = []
        if measures is None:
            measures = []

        # Build query_info from parameters
        query_info = {
            "dimensions": dimensions,
            "measures": measures,
        }

        # Add context fields if provided
        if context:
            if "model" in context:
                query_info["model"] = context["model"]
            if "question" in context:
                query_info["question"] = context["question"]

        # Use existing generate_interpretation method
        return await self.generate_interpretation(
            result=result,
            query_info=query_info,
            statistical_analysis=statistical_analysis,
        )

    async def generate_analysis_suggestions(
        self,
        current_result: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        dimensions: List[str] = None,
        measures: List[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Generate analysis suggestions based on current context.

        This method combines suggest_next_questions() and suggest_analysis_paths()
        to provide a unified suggestion interface.
        """
        if dimensions is None:
            dimensions = []
        if measures is None:
            measures = []

        suggestions = []

        # If we have a current result, get next question suggestions
        if current_result and current_result.get("data"):
            next_questions = await self.suggest_next_questions(
                result=current_result,
                context=context or "",
                current_dimensions=dimensions,
                current_measures=measures,
            )
            suggestions.extend(next_questions)

        # If we don't have enough suggestions, add analysis path suggestions
        if len(suggestions) < 3:
            # Extract model from context if possible
            model = None
            if context:
                if "users" in context.lower():
                    model = "users"
                elif "events" in context.lower():
                    model = "events"
                elif "engagement" in context.lower():
                    model = "engagement"

            analysis_paths = await self.suggest_analysis_paths(
                current_result=current_result, context=context, model=model
            )

            # Add analysis paths that aren't duplicates
            existing_questions = {s.get("question", "").lower() for s in suggestions}
            for path in analysis_paths:
                if path.get("question", "").lower() not in existing_questions:
                    suggestions.append(path)
                    if len(suggestions) >= 5:  # Limit to 5 total suggestions
                        break

        return suggestions[:5]  # Return max 5 suggestions

    def add_context(self, context: Dict[str, Any]) -> None:
        """Add context to the conversation history."""
        context["timestamp"] = datetime.now().isoformat()
        self.context_history.append(context)

        # Keep only last 10 interactions
        if len(self.context_history) > 10:
            self.context_history = self.context_history[-10:]
