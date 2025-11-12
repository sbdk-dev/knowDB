# Date Dimensions Quick Reference

## Quick Status Check

**Database:** `/Users/mattstrautmann/Documents/github/knowDB/data/sample.duckdb`
**Status:** ✅ READY FOR DATE DIMENSIONS
**Date:** 2025-11-09

---

## Available Temporal Columns

| Table | Column | Type | NULLs | Range |
|-------|--------|------|-------|-------|
| monthly_mrr_snapshots | month | DATE | No | Last 12 months |
| customers | signup_date | DATE | No | 2023-01-01 onwards |
| subscriptions | start_date | DATE | No | 2023-01-01 onwards |
| subscriptions | end_date | DATE | Yes | Only for cancelled |

---

## Copy-Paste YAML Configuration

Add these to `semantic_models/metrics.yml` under the `dimensions:` section:

```yaml
# Customer Temporal Dimensions
- name: "signup_year"
  display_name: "Signup Year"
  description: "Year when customer signed up"
  type: "temporal"
  table: "customers"
  column: "signup_date"
  sql_expression: "strftime(signup_date, '%Y')"

- name: "signup_quarter"
  display_name: "Signup Quarter"
  description: "Quarter when customer signed up"
  type: "temporal"
  table: "customers"
  column: "signup_date"
  sql_expression: "strftime(signup_date, '%Y-Q%q')"

- name: "signup_month"
  display_name: "Signup Month"
  description: "Month when customer signed up"
  type: "temporal"
  table: "customers"
  column: "signup_date"
  sql_expression: "strftime(signup_date, '%Y-%m')"

- name: "signup_month_name"
  display_name: "Signup Month Name"
  description: "Human-readable month when customer signed up"
  type: "temporal"
  table: "customers"
  column: "signup_date"
  sql_expression: "strftime(signup_date, '%B %Y')"

# Subscription Temporal Dimensions
- name: "subscription_start_year"
  display_name: "Subscription Start Year"
  description: "Year when subscription started"
  type: "temporal"
  table: "subscriptions"
  column: "start_date"
  sql_expression: "strftime(start_date, '%Y')"

- name: "subscription_start_quarter"
  display_name: "Subscription Start Quarter"
  description: "Quarter when subscription started"
  type: "temporal"
  table: "subscriptions"
  column: "start_date"
  sql_expression: "strftime(start_date, '%Y-Q%q')"

- name: "subscription_start_month"
  display_name: "Subscription Start Month"
  description: "Month when subscription started"
  type: "temporal"
  table: "subscriptions"
  column: "start_date"
  sql_expression: "strftime(start_date, '%Y-%m')"

# Time-Series Temporal Dimensions
- name: "snapshot_year"
  display_name: "Snapshot Year"
  description: "Year of MRR snapshot"
  type: "temporal"
  table: "monthly_mrr_snapshots"
  column: "month"
  sql_expression: "strftime(month, '%Y')"

- name: "snapshot_quarter"
  display_name: "Snapshot Quarter"
  description: "Quarter of MRR snapshot"
  type: "temporal"
  table: "monthly_mrr_snapshots"
  column: "month"
  sql_expression: "strftime(month, '%Y-Q%q')"

- name: "snapshot_month"
  display_name: "Snapshot Month"
  description: "Month of MRR snapshot"
  type: "temporal"
  table: "monthly_mrr_snapshots"
  column: "month"
  sql_expression: "strftime(month, '%Y-%m')"

- name: "snapshot_month_name"
  display_name: "Snapshot Month Name"
  description: "Human-readable snapshot month"
  type: "temporal"
  table: "monthly_mrr_snapshots"
  column: "month"
  sql_expression: "strftime(month, '%B %Y')"

# Advanced Temporal Dimensions
- name: "customer_age_days"
  display_name: "Customer Age (Days)"
  description: "Number of days since customer signup"
  type: "temporal"
  table: "customers"
  column: "signup_date"
  sql_expression: "CAST(julianday('now') - julianday(signup_date) AS INTEGER)"
```

---

## Test Queries

### Test 1: Verify strftime works
```sql
SELECT
  signup_date,
  strftime(signup_date, '%Y') as year,
  strftime(signup_date, '%Y-Q%q') as quarter,
  strftime(signup_date, '%B %Y') as month_name
FROM customers
LIMIT 5;
```

### Test 2: Customer count by signup year
```sql
SELECT
  strftime(signup_date, '%Y') as signup_year,
  COUNT(*) as customer_count
FROM customers
GROUP BY 1
ORDER BY 1;
```

### Test 3: MRR trend by month
```sql
SELECT
  strftime(month, '%Y-%m') as snapshot_month,
  SUM(mrr) as total_mrr
FROM monthly_mrr_snapshots
GROUP BY 1
ORDER BY 1;
```

### Test 4: Multi-dimensional query
```sql
SELECT
  strftime(signup_date, '%Y-Q%q') as signup_quarter,
  customer_segment,
  COUNT(*) as customer_count
FROM customers
GROUP BY 1, 2
ORDER BY 1, 2;
```

---

## Common strftime Format Codes

| Code | Description | Example |
|------|-------------|---------|
| `%Y` | 4-digit year | 2024 |
| `%y` | 2-digit year | 24 |
| `%m` | Month (01-12) | 11 |
| `%B` | Full month name | November |
| `%b` | Abbreviated month | Nov |
| `%d` | Day of month | 09 |
| `%A` | Full weekday name | Saturday |
| `%a` | Abbreviated weekday | Sat |
| `%W` | Week number | 45 |
| `%q` | Quarter (1-4) | 4 |
| `%Y-%m` | Year-Month | 2024-11 |
| `%Y-%m-%d` | ISO date | 2024-11-09 |
| `%Y-Q%q` | Year-Quarter | 2024-Q4 |
| `%B %Y` | Month Year | November 2024 |

---

## Code Changes Required

### semantic_layer.py Enhancement

Current dimension handling (line ~460):
```python
# Dimension is in the same table
if col in table.columns:
    group_by_columns.append(table[col])
```

Needs to become:
```python
# Check if dimension has SQL expression
if dim.get('sql_expression'):
    # Use SQL expression for temporal/computed dimensions
    from ibis import literal
    expr_str = dim['sql_expression']
    # TODO: Safely evaluate SQL expression in Ibis
    # For now, this requires manual implementation per expression type
    group_by_columns.append(table[col])  # Fallback
elif col in table.columns:
    # Use direct column reference
    group_by_columns.append(table[col])
```

**Note:** Ibis doesn't directly support arbitrary SQL strings. You'll need to build the expression programmatically:

```python
# Example for strftime expressions
if 'strftime' in expr_str:
    # Parse the expression
    # Extract: strftime(column_name, 'format')
    import re
    match = re.search(r"strftime\((\w+),\s*'([^']+)'\)", expr_str)
    if match:
        col_name, fmt = match.groups()
        # Use Ibis strftime
        expr = table[col_name].strftime(fmt).name(dim['name'])
        group_by_columns.append(expr)
```

---

## Example Metric Queries with Date Dimensions

### Example 1: MRR by Month
```python
result = semantic_layer.query_metric(
    "monthly_mrr",
    dimensions=["snapshot_month", "customer_segment"],
    order_by="snapshot_month"
)
```

### Example 2: New Customers by Quarter
```python
result = semantic_layer.query_metric(
    "total_customers",
    dimensions=["signup_quarter"],
    order_by="signup_quarter"
)
```

### Example 3: Subscriptions by Start Month
```python
result = semantic_layer.query_metric(
    "active_subscriptions",
    dimensions=["subscription_start_month", "product_tier"],
    order_by="subscription_start_month"
)
```

---

## Troubleshooting

### Issue: "Column not found" error
**Solution:** Verify the `column` field in dimension YAML matches the actual table column name

### Issue: strftime returns NULL
**Solution:** Check for NULL values in the date column:
```sql
SELECT COUNT(*) FROM table_name WHERE date_column IS NULL;
```

### Issue: Date format doesn't match expected
**Solution:** Review strftime format codes above, test in raw SQL first

### Issue: Dimension not grouping correctly
**Solution:** Ensure `sql_expression` generates the same value for rows that should be grouped together

---

## Performance Tips

1. **Use DATE columns, not VARCHAR** - Already implemented ✓
2. **Filter before formatting** - Apply WHERE clauses before GROUP BY
3. **Avoid formatting in WHERE clauses** - Use raw date comparisons
4. **Consider indexes for large tables** - Add after 100K+ rows

Example of efficient query:
```sql
-- GOOD: Filter first, then format
SELECT
  strftime(signup_date, '%Y-%m') as month,
  COUNT(*) as customers
FROM customers
WHERE signup_date >= '2024-01-01'  -- Raw date comparison
GROUP BY strftime(signup_date, '%Y-%m');

-- AVOID: Formatting in WHERE clause
SELECT ...
WHERE strftime(signup_date, '%Y') = '2024'  -- Slower
```

---

## Next Steps

1. Add date dimensions to `semantic_models/metrics.yml`
2. Enhance `semantic_layer.py` to support `sql_expression` field
3. Test each dimension with sample queries
4. Update documentation with temporal analysis examples
5. Deploy and monitor performance

---

## Resources

- **Full Report:** `TEMPORAL_COLUMNS_VERIFICATION_REPORT.md`
- **Summary:** `TEMPORAL_VERIFICATION_SUMMARY.txt`
- **DuckDB Date Functions:** https://duckdb.org/docs/sql/functions/date
- **Ibis Date Functions:** https://ibis-project.org/reference/temporal

---

**Last Updated:** 2025-11-09
**Status:** Ready for implementation
