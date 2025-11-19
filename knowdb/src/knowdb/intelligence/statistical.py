"""
Statistical Testing Module for KnowDB Intelligence

Implements automatic statistical testing, sample size validation, and effect size calculation
to provide rigorous analysis and prevent unreliable claims.
"""

import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


class StatisticalTester:
    """Handles statistical testing and validation for query results."""

    def __init__(self):
        self.min_sample_size = 30
        self.warning_threshold = 100
        self.default_alpha = 0.05

    async def validate_result(
        self, result: Dict[str, Any], dimensions: List[str]
    ) -> Dict[str, Any]:
        """
        Validate query results for statistical reliability.

        Checks sample sizes, data quality, and provides warnings.
        """

        validation = {
            "valid": True,
            "warnings": [],
            "sample_sizes": {},
            "data_quality": {},
        }

        data = result.get("data", [])
        if not data:
            validation["valid"] = False
            validation["warnings"].append("No data returned")
            return validation

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(data)

        # Check overall sample size
        total_rows = len(df)
        validation["sample_sizes"]["total"] = total_rows

        if total_rows < self.min_sample_size:
            validation["warnings"].append(
                f"Small sample size (n={total_rows}, recommend n>={self.min_sample_size})"
            )

        # Check sample sizes for grouped data
        if dimensions:
            dim = dimensions[0]  # Focus on primary dimension
            if dim in df.columns:
                group_sizes = df[dim].value_counts().to_dict()
                validation["sample_sizes"]["groups"] = group_sizes

                # Check for small groups
                small_groups = [
                    k for k, v in group_sizes.items() if v < self.min_sample_size
                ]
                if small_groups:
                    validation["warnings"].append(
                        f"Small groups: {small_groups} (n<{self.min_sample_size})"
                    )

                # Check for very unbalanced groups
                min_size = min(group_sizes.values())
                max_size = max(group_sizes.values())
                if max_size / min_size > 10:
                    validation["warnings"].append(
                        "Highly unbalanced groups - interpret comparisons carefully"
                    )

        # Check for missing values
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_pct = (missing_count / len(df)) * 100
                validation["data_quality"][col] = {
                    "missing_count": int(missing_count),
                    "missing_percent": round(missing_pct, 1),
                }
                if missing_pct > 10:
                    validation["warnings"].append(
                        f"High missing data: {col} ({missing_pct:.1f}% missing)"
                    )

        return validation

    async def auto_test_comparison(
        self, result: Dict[str, Any], dimensions: List[str], measures: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Automatically run appropriate statistical tests when comparing groups.

        Determines test type based on data structure and runs significance testing.
        """

        data = result.get("data", [])
        if not data or not dimensions or not measures:
            return None

        df = pd.DataFrame(data)
        dim = dimensions[0]
        measure = measures[0]

        # Check if we have the required columns
        if dim not in df.columns or measure not in df.columns:
            return None

        # Remove missing values
        clean_df = df.dropna(subset=[dim, measure])
        if len(clean_df) < self.min_sample_size:
            return None

        # Get unique groups
        groups = clean_df[dim].unique()
        if len(groups) < 2:
            return None  # Need at least 2 groups to compare

        # Extract values for each group
        group_data = []
        group_names = []
        sample_sizes = {}

        for group in groups:
            group_values = clean_df[clean_df[dim] == group][measure].values
            if len(group_values) >= 5:  # Minimum group size
                group_data.append(group_values)
                group_names.append(str(group))
                sample_sizes[str(group)] = len(group_values)

        if len(group_data) < 2:
            return None

        # Choose appropriate test
        if len(group_data) == 2:
            # Two groups: t-test or Mann-Whitney U
            test_result = await self._two_group_test(
                group_data[0], group_data[1], group_names
            )
        else:
            # Multiple groups: ANOVA or Kruskal-Wallis
            test_result = await self._multiple_group_test(group_data, group_names)

        if test_result:
            test_result["sample_sizes"] = sample_sizes
            test_result["dimension"] = dim
            test_result["measure"] = measure

        return test_result

    async def _two_group_test(
        self, group1: np.ndarray, group2: np.ndarray, group_names: List[str]
    ) -> Dict[str, Any]:
        """Run appropriate test for two groups."""

        # Check normality with Shapiro-Wilk (if sample size allows)
        normal1 = normal2 = True
        if len(group1) <= 5000:
            _, p1 = stats.shapiro(group1)
            normal1 = p1 > 0.05
        if len(group2) <= 5000:
            _, p2 = stats.shapiro(group2)
            normal2 = p2 > 0.05

        # Check equal variances
        _, p_var = stats.levene(group1, group2)
        equal_var = p_var > 0.05

        # Choose test
        if normal1 and normal2:
            # Use t-test
            if equal_var:
                statistic, p_value = stats.ttest_ind(group1, group2, equal_var=True)
                test_type = "independent_t_test"
            else:
                statistic, p_value = stats.ttest_ind(group1, group2, equal_var=False)
                test_type = "welch_t_test"
        else:
            # Use Mann-Whitney U test
            statistic, p_value = stats.mannwhitneyu(
                group1, group2, alternative="two-sided"
            )
            test_type = "mann_whitney_u"

        # Calculate effect size (Cohen's d for parametric, rank-biserial correlation for non-parametric)
        if normal1 and normal2:
            cohens_d = self._calculate_cohens_d(group1, group2)
            effect_size = abs(cohens_d)
            effect_size_interpretation = self._interpret_cohens_d(effect_size)
        else:
            # Rank-biserial correlation for Mann-Whitney U
            n1, n2 = len(group1), len(group2)
            r = (2 * statistic) / (n1 * n2) - 1
            effect_size = abs(r)
            effect_size_interpretation = self._interpret_rank_biserial(effect_size)

        return {
            "test_type": test_type,
            "statistic": float(statistic),
            "p_value": float(p_value),
            "effect_size": effect_size,
            "effect_size_interpretation": effect_size_interpretation,
            "significant": p_value < self.default_alpha,
            "group_names": group_names,
            "group_means": [float(np.mean(group1)), float(np.mean(group2))],
            "group_stds": [float(np.std(group1)), float(np.std(group2))],
            "assumptions": {
                "normality": normal1 and normal2,
                "equal_variance": equal_var,
            },
        }

    async def _multiple_group_test(
        self, group_data: List[np.ndarray], group_names: List[str]
    ) -> Dict[str, Any]:
        """Run appropriate test for multiple groups."""

        # Check normality for all groups
        all_normal = True
        for group in group_data:
            if len(group) <= 5000:
                _, p = stats.shapiro(group)
                if p <= 0.05:
                    all_normal = False
                    break

        # Check equal variances
        _, p_var = stats.levene(*group_data)
        equal_var = p_var > 0.05

        # Choose test
        if all_normal and equal_var:
            # Use ANOVA
            statistic, p_value = stats.f_oneway(*group_data)
            test_type = "one_way_anova"
        else:
            # Use Kruskal-Wallis
            statistic, p_value = stats.kruskal(*group_data)
            test_type = "kruskal_wallis"

        # Calculate eta-squared for effect size
        if all_normal:
            eta_squared = self._calculate_eta_squared(group_data)
            effect_size_interpretation = self._interpret_eta_squared(eta_squared)
        else:
            # For non-parametric, use epsilon-squared approximation
            total_n = sum(len(group) for group in group_data)
            eta_squared = (statistic - len(group_data) + 1) / (
                total_n - len(group_data)
            )
            eta_squared = max(0, eta_squared)  # Ensure non-negative
            effect_size_interpretation = self._interpret_eta_squared(eta_squared)

        return {
            "test_type": test_type,
            "statistic": float(statistic),
            "p_value": float(p_value),
            "effect_size": eta_squared,
            "effect_size_interpretation": effect_size_interpretation,
            "significant": p_value < self.default_alpha,
            "group_names": group_names,
            "group_means": [float(np.mean(group)) for group in group_data],
            "group_stds": [float(np.std(group)) for group in group_data],
            "assumptions": {"normality": all_normal, "equal_variance": equal_var},
        }

    async def run_significance_tests(
        self,
        data: Dict[str, Any],
        comparison_type: str = "groups",
        dimensions: List[str] = None,
        measures: List[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Run statistical significance tests on data.

        Args:
            data: Query result data
            comparison_type: Type of comparison (groups, correlation, trend)
            dimensions: Grouping variables
            measures: Outcome variables

        Returns:
            Statistical test results
        """
        if dimensions is None:
            dimensions = []
        if measures is None:
            measures = []

        if comparison_type == "groups":
            return await self.auto_test_comparison(data, dimensions, measures)
        elif comparison_type == "correlation":
            return await self._correlation_test(data, dimensions, measures)
        elif comparison_type == "trend":
            return await self._trend_test(data, dimensions, measures)
        else:
            return {"error": f"Unknown comparison type: {comparison_type}"}

    async def _correlation_test(
        self, data: Dict[str, Any], dimensions: List[str], measures: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Test correlation between variables."""

        if len(measures) < 2:
            return None

        df = pd.DataFrame(data.get("data", []))
        var1, var2 = measures[0], measures[1]

        if var1 not in df.columns or var2 not in df.columns:
            return None

        # Remove missing values
        clean_df = df[[var1, var2]].dropna()
        if len(clean_df) < self.min_sample_size:
            return None

        x, y = clean_df[var1].values, clean_df[var2].values

        # Pearson correlation
        r_pearson, p_pearson = stats.pearsonr(x, y)

        # Spearman correlation (rank-based)
        r_spearman, p_spearman = stats.spearmanr(x, y)

        return {
            "test_type": "correlation",
            "pearson_r": float(r_pearson),
            "pearson_p": float(p_pearson),
            "spearman_r": float(r_spearman),
            "spearman_p": float(p_spearman),
            "significant": min(p_pearson, p_spearman) < self.default_alpha,
            "sample_size": len(clean_df),
            "variables": [var1, var2],
        }

    async def _trend_test(
        self, data: Dict[str, Any], dimensions: List[str], measures: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Test for trend over time."""

        if not dimensions or not measures:
            return None

        df = pd.DataFrame(data.get("data", []))
        time_var, measure_var = dimensions[0], measures[0]

        if time_var not in df.columns or measure_var not in df.columns:
            return None

        # Sort by time variable
        df_sorted = df.sort_values(time_var).dropna(subset=[time_var, measure_var])
        if len(df_sorted) < 3:
            return None

        # Create time index for regression
        time_index = np.arange(len(df_sorted))
        values = df_sorted[measure_var].values

        # Linear regression for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            time_index, values
        )

        # Mann-Kendall test for monotonic trend
        def mann_kendall_test(x):
            n = len(x)
            s = 0
            for i in range(n - 1):
                for j in range(i + 1, n):
                    s += np.sign(x[j] - x[i])

            var_s = n * (n - 1) * (2 * n + 5) / 18
            if s > 0:
                z = (s - 1) / np.sqrt(var_s)
            elif s < 0:
                z = (s + 1) / np.sqrt(var_s)
            else:
                z = 0

            p_mk = 2 * (1 - stats.norm.cdf(abs(z)))
            return z, p_mk

        mk_z, mk_p = mann_kendall_test(values)

        return {
            "test_type": "trend",
            "linear_slope": float(slope),
            "linear_r_squared": float(r_value**2),
            "linear_p": float(p_value),
            "mann_kendall_z": float(mk_z),
            "mann_kendall_p": float(mk_p),
            "significant": min(p_value, mk_p) < self.default_alpha,
            "trend_direction": (
                "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
            ),
            "sample_size": len(df_sorted),
        }

    def _calculate_cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        s1, s2 = np.std(group1, ddof=1), np.std(group2, ddof=1)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))

        # Cohen's d
        if pooled_std == 0:
            return 0.0
        d = (np.mean(group1) - np.mean(group2)) / pooled_std
        return d

    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        d = abs(d)
        if d >= 0.8:
            return "large"
        elif d >= 0.5:
            return "medium"
        elif d >= 0.2:
            return "small"
        else:
            return "negligible"

    def _interpret_rank_biserial(self, r: float) -> str:
        """Interpret rank-biserial correlation effect size."""
        r = abs(r)
        if r >= 0.7:
            return "large"
        elif r >= 0.5:
            return "medium"
        elif r >= 0.3:
            return "small"
        else:
            return "negligible"

    def _calculate_eta_squared(self, group_data: List[np.ndarray]) -> float:
        """Calculate eta-squared effect size for ANOVA."""
        # Calculate sum of squares
        all_data = np.concatenate(group_data)
        grand_mean = np.mean(all_data)

        # Between-group sum of squares
        ss_between = sum(
            len(group) * (np.mean(group) - grand_mean) ** 2 for group in group_data
        )

        # Total sum of squares
        ss_total = np.sum((all_data - grand_mean) ** 2)

        # Eta-squared
        eta_squared = ss_between / ss_total if ss_total > 0 else 0
        return eta_squared

    def _interpret_eta_squared(self, eta_squared: float) -> str:
        """Interpret eta-squared effect size."""
        if eta_squared >= 0.14:
            return "large"
        elif eta_squared >= 0.06:
            return "medium"
        elif eta_squared >= 0.01:
            return "small"
        else:
            return "negligible"

    def interpret_p_value(self, p_value: float) -> str:
        """Interpret p-value significance level."""
        if p_value < 0.001:
            return "highly significant"
        elif p_value < 0.01:
            return "very significant"
        elif p_value < 0.05:
            return "significant"
        else:
            return "not significant"
