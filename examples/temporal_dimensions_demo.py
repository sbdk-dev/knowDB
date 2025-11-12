#!/usr/bin/env python3
"""
Temporal Dimensions Demonstration

This script demonstrates how temporal dimensions work with SQL expressions
like strftime() for time-based grouping and analysis.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_layer import SemanticLayer


def main():
    print("=" * 80)
    print("TEMPORAL DIMENSIONS DEMONSTRATION")
    print("=" * 80)

    # Initialize semantic layer
    sl = SemanticLayer("semantic_models/metrics.yml")

    print("\n1. AVAILABLE TEMPORAL DIMENSIONS")
    print("-" * 80)

    dimensions = sl.list_dimensions()
    temporal_dims = [d for d in dimensions if d.get("type") == "temporal"]

    for dim in temporal_dims:
        print(f"\n{dim['name']}")
        print(f"  Display: {dim.get('display_name', dim['name'])}")
        print(f"  Type: {dim.get('type')}")
        print(f"  SQL Expression: {dim.get('sql', 'N/A')}")
        print(f"  Description: {dim.get('description', 'N/A')}")

    print("\n\n2. QUERY EXAMPLES WITH TEMPORAL DIMENSIONS")
    print("-" * 80)

    # Example 1: Monthly MRR trend
    print("\n\nExample 1: Monthly MRR Trend")
    print("-" * 40)
    result = sl.query_metric("monthly_mrr", dimensions=["month"], limit=12)
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Results (showing first 5):")
    for row in result['data'][:5]:
        print(f"  {row}")

    # Example 2: Yearly aggregation
    print("\n\nExample 2: MRR by Year")
    print("-" * 40)
    result = sl.query_metric("monthly_mrr", dimensions=["year"])
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Results:")
    for row in result['data']:
        print(f"  {row}")

    # Example 3: Mixed categorical and temporal dimensions
    print("\n\nExample 3: Monthly MRR by Customer Segment")
    print("-" * 40)
    result = sl.query_metric(
        "monthly_mrr",
        dimensions=["month", "customer_segment"],
        limit=10
    )
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Results (showing first 5):")
    for row in result['data'][:5]:
        print(f"  {row}")

    # Example 4: Simple dimensions still work
    print("\n\nExample 4: Traditional Categorical Dimension (customer_segment)")
    print("-" * 40)
    result = sl.query_metric("total_mrr", dimensions=["customer_segment"])
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Results:")
    for row in result['data']:
        print(f"  {row}")

    print("\n\n3. HOW TEMPORAL DIMENSIONS WORK")
    print("-" * 80)
    print("""
Temporal dimensions extend the semantic layer with SQL expression support:

1. DEFINITION (in date_dimensions_config.yaml):
   - name: "month"
     type: "temporal"
     sql: "strftime('%Y-%m', {{ Table }}.month)"

2. PLACEHOLDER REPLACEMENT:
   - {{ Table }} gets replaced with the actual table alias
   - Example: {{ Table }}.month → monthly_mrr_snapshots.month

3. IBIS TRANSLATION:
   - SQL expressions are parsed and converted to Ibis operations
   - strftime('%Y-%m', column) → table[column].strftime('%Y-%m')

4. QUERY EXECUTION:
   - Ibis generates optimized SQL for the target database
   - Temporal grouping works like any other dimension

5. BACKWARD COMPATIBILITY:
   - Simple dimensions (column references) still work
   - No breaking changes to existing queries
   - Temporal dimensions are optional (loaded from separate config)

SUPPORTED SQL FUNCTIONS:
   - strftime() with various format strings (%Y, %Y-%m, %Y-%m-%d, etc.)
   - Quarter calculations using month arithmetic
   - Custom date expressions can be added

BENEFITS:
   - Business users can group by "month" without knowing SQL
   - Consistent date formatting across all queries
   - Supports complex temporal logic (quarters, fiscal years, etc.)
   - No code changes needed for new temporal dimensions
    """)

    print("\n" + "=" * 80)
    print("DEMO COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
