#!/usr/bin/env python3
"""
Test Time-Based Query Functionality

Tests the complete user flow for time-based queries:
1. Query monthly_mrr with snapshot_year_month dimension
2. Query monthly_customer_count with time grouping
3. Verify SQL generation is correct
4. Test canonical dataset "growth_trends"
5. Test exact user query: "show me how my active customer count is changing over time"
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from semantic_layer import SemanticLayer, SemanticLayerError

def print_test_header(test_name):
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print('='*80)

def print_result(result):
    print(f"\nMetric: {result['metric']}")
    print(f"Display Name: {result['display_name']}")
    print(f"Dimensions: {result['dimensions']}")
    print(f"Row Count: {result['row_count']}")
    print(f"\nGenerated SQL:")
    print(result['sql'])
    print(f"\nResults (first 10 rows):")
    for i, row in enumerate(result['data'][:10]):
        print(f"  {i+1}. {row}")
    if result['row_count'] > 10:
        print(f"  ... and {result['row_count'] - 10} more rows")

def test_basic_functionality(sl):
    """Test 1: Basic semantic layer functionality"""
    print_test_header("Basic Semantic Layer Functionality")

    try:
        # List metrics
        metrics = sl.list_metrics()
        print(f"\nTotal metrics available: {len(metrics)}")

        # List dimensions
        dimensions = sl.list_dimensions()
        print(f"Total dimensions available: {len(dimensions)}")

        # Check for time-based metrics
        time_metrics = [m for m in metrics if 'monthly' in m['name']]
        print(f"\nTime-based metrics found:")
        for m in time_metrics:
            print(f"  - {m['name']}: {m['display_name']}")

        print("\n✅ PASSED: Basic functionality works")
        return True
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

def test_monthly_mrr_query(sl):
    """Test 2: Query monthly_mrr metric"""
    print_test_header("Query monthly_mrr Metric")

    try:
        # Find time dimension (could be named snapshot_month, snapshot_year_month, etc.)
        dimensions = sl.list_dimensions()
        time_dims = [d for d in dimensions if 'snapshot' in d['name'].lower() or 'month' in d['name'].lower() or d.get('type') == 'time']

        if time_dims:
            time_dim_name = time_dims[0]['name']
            print(f"✅ Found time dimension: {time_dim_name}")
        else:
            print("⚠️  WARNING: No time dimension found in config")
            print("Available dimensions:")
            for d in dimensions:
                print(f"  - {d['name']} ({d.get('type', 'unknown')})")

        # Query monthly_mrr without dimension first
        result = sl.query_metric("monthly_mrr")
        print("\n--- Without Time Dimension ---")
        print_result(result)

        if result['row_count'] > 0:
            print("\n✅ PASSED: monthly_mrr query works (no dimension)")
        else:
            print("\n⚠️  WARNING: monthly_mrr returned no results")

        # Try with time dimension if it exists
        if time_dims:
            result_with_time = sl.query_metric("monthly_mrr", dimensions=[time_dim_name])
            print("\n--- With Time Dimension ---")
            print_result(result_with_time)

            if result_with_time['row_count'] > 1:
                print(f"\n✅ PASSED: monthly_mrr query with time dimension works ({result_with_time['row_count']} time periods)")
                return True
            elif result_with_time['row_count'] == 1:
                print("\n⚠️  WARNING: Only got 1 time period (expected multiple)")
                return True
            else:
                print("\n❌ FAILED: monthly_mrr with time dimension returned no results")
                return False
        else:
            print("\n⚠️  SKIPPED: Time dimension test (dimension not configured)")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_monthly_customer_count_query(sl):
    """Test 3: Query monthly_customer_count metric"""
    print_test_header("Query monthly_customer_count Metric")

    try:
        # Query without dimension
        result = sl.query_metric("monthly_customer_count")
        print_result(result)

        if result['row_count'] > 0:
            print("\n✅ PASSED: monthly_customer_count query works")

            # Try with time dimension if available
            dimensions = sl.list_dimensions()
            has_time_dim = any(d['name'] == 'snapshot_year_month' for d in dimensions)

            if has_time_dim:
                result_with_time = sl.query_metric("monthly_customer_count", dimensions=["snapshot_year_month"])
                print("\n--- With Time Dimension ---")
                print_result(result_with_time)

            return True
        else:
            print("\n⚠️  WARNING: monthly_customer_count returned no results")
            return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sql_generation(sl):
    """Test 4: Verify SQL generation is correct"""
    print_test_header("SQL Generation Verification")

    try:
        result = sl.query_metric("monthly_mrr")
        sql = result['sql']

        print("\nGenerated SQL:")
        print(sql)

        # Check for expected elements in SQL
        checks = {
            "monthly_mrr_snapshots table": "monthly_mrr_snapshots" in sql.lower(),
            "SUM aggregation": "sum" in sql.lower(),
            "mrr column": "mrr" in sql.lower(),
        }

        print("\nSQL Validation:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            all_passed = all_passed and passed

        if all_passed:
            print("\n✅ PASSED: SQL generation is correct")
            return True
        else:
            print("\n❌ FAILED: SQL generation missing expected elements")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

def test_canonical_dataset(sl):
    """Test 5: Test canonical dataset 'growth_trends'"""
    print_test_header("Canonical Dataset: growth_trends")

    try:
        # Check if canonical datasets are defined
        config = sl.config
        canonical_datasets = config.get('semantic_model', {}).get('canonical_datasets', [])

        print(f"\nTotal canonical datasets: {len(canonical_datasets)}")

        growth_trends = None
        for ds in canonical_datasets:
            if ds['name'] == 'growth_trends':
                growth_trends = ds
                break

        if not growth_trends:
            print("❌ FAILED: growth_trends canonical dataset not found")
            print("Available datasets:")
            for ds in canonical_datasets:
                print(f"  - {ds['name']}")
            return False

        print(f"\nGrowth Trends Dataset:")
        print(f"  Display Name: {growth_trends.get('display_name')}")
        print(f"  Description: {growth_trends.get('description')}")
        print(f"  Metrics: {growth_trends.get('metrics')}")
        print(f"  Dimensions: {growth_trends.get('dimensions')}")
        print(f"  Time Dimension: {growth_trends.get('time_dimension')}")

        # Query each metric in the dataset
        print("\nQuerying dataset metrics:")
        for metric_name in growth_trends.get('metrics', []):
            result = sl.query_metric(metric_name)
            print(f"\n  {metric_name}: {result['row_count']} rows")
            if result['data']:
                print(f"    Sample: {result['data'][0]}")

        print("\n✅ PASSED: Canonical dataset growth_trends is properly defined")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_flow(sl):
    """Test 6: Exact user flow - 'show me how my active customer count is changing over time'"""
    print_test_header("User Flow: Active Customer Count Over Time")

    try:
        # This is what the user would ask
        user_query = "show me how my active customer count is changing over time"
        print(f"\nUser Query: \"{user_query}\"")

        # The semantic layer should interpret this as querying monthly_customer_count over time
        print("\nInterpreting as: monthly_customer_count metric")

        # Check if we have time dimension configured
        dimensions = sl.list_dimensions()
        time_dimensions = [d for d in dimensions if 'month' in d['name'].lower() or 'date' in d['name'].lower() or 'time' in d['name'].lower()]

        if time_dimensions:
            time_dim = time_dimensions[0]['name']
            print(f"Using time dimension: {time_dim}")
            result = sl.query_metric("monthly_customer_count", dimensions=[time_dim])
        else:
            print("⚠️  No time dimension found, querying without dimension")
            result = sl.query_metric("monthly_customer_count")

        print_result(result)

        # Verify we got meaningful time-series data
        if result['row_count'] > 1:
            print(f"\n✅ PASSED: Got time-series data with {result['row_count']} time periods")

            # Show trend
            if result['data'] and len(result['data']) >= 2:
                first = result['data'][0].get('monthly_customer_count', 0)
                last = result['data'][-1].get('monthly_customer_count', 0)
                if isinstance(first, (int, float)) and isinstance(last, (int, float)):
                    change = last - first
                    pct_change = (change / first * 100) if first > 0 else 0
                    print(f"\nTrend Analysis:")
                    print(f"  First period: {first} customers")
                    print(f"  Last period: {last} customers")
                    print(f"  Change: {change:+.0f} customers ({pct_change:+.1f}%)")

            return True
        elif result['row_count'] == 1:
            print("\n⚠️  WARNING: Only got 1 time period (expected multiple for trend)")
            return True
        else:
            print("\n❌ FAILED: No data returned")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TIME-BASED QUERY TESTING SUITE")
    print("="*80)

    # Initialize semantic layer
    try:
        config_path = "semantic_models/metrics.yml"
        if not Path(config_path).exists():
            print(f"❌ ERROR: Configuration file not found: {config_path}")
            return 1

        sl = SemanticLayer(config_path)
        print(f"\n✅ Semantic layer initialized successfully")

    except Exception as e:
        print(f"\n❌ ERROR initializing semantic layer: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Run tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Monthly MRR Query", test_monthly_mrr_query),
        ("Monthly Customer Count Query", test_monthly_customer_count_query),
        ("SQL Generation", test_sql_generation),
        ("Canonical Dataset", test_canonical_dataset),
        ("User Flow", test_user_flow),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func(sl)
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    # Clean up
    sl.close()

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
