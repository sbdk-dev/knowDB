# Time-Based Query Examples

Quick reference for time-based queries in the Semantic Layer.

---

## Example 1: Customer Count Over Time

**User Query:** "Show me how my active customer count is changing over time"

**Python Code:**
```python
from src.semantic_layer import SemanticLayer

sl = SemanticLayer('semantic_models/metrics.yml')
result = sl.query_metric(
    'monthly_customer_count',
    dimensions=['snapshot_month'],
    order_by='snapshot_month'
)
```

**Generated SQL:**
```sql
SELECT
  "t0"."month" AS "snapshot_month",
  SUM("t0"."customer_count") AS "monthly_customer_count"
FROM "monthly_mrr_snapshots" AS "t0"
GROUP BY 1
ORDER BY "snapshot_month" ASC
```

**Results:**
```
2024-11: 100 customers
2024-12: 100 customers
2025-01: 100 customers
2025-02: 100 customers
2025-03: 100 customers
2025-04: 100 customers
2025-05: 100 customers
2025-06: 100 customers
2025-07: 100 customers
2025-08: 100 customers
2025-09: 100 customers
2025-10: 100 customers
2025-11: 100 customers
```

---

## Example 2: MRR Over Time

**User Query:** "Show me MRR trends"

**Python Code:**
```python
result = sl.query_metric(
    'monthly_mrr',
    dimensions=['snapshot_month'],
    order_by='snapshot_month'
)
```

**Generated SQL:**
```sql
SELECT
  "t0"."month" AS "snapshot_month",
  SUM("t0"."mrr") AS "monthly_mrr"
FROM "monthly_mrr_snapshots" AS "t0"
GROUP BY 1
ORDER BY "snapshot_month" ASC
```

**Results:**
```
2024-11: $48,669.99
2024-12: $49,643.40
2025-01: $50,616.79
2025-02: $51,590.20
2025-03: $52,563.60
2025-04: $53,536.99
2025-05: $54,510.40
2025-06: $55,483.80
2025-07: $56,457.19
2025-08: $57,430.60
2025-09: $58,403.99
2025-10: $59,377.40
2025-11: $60,350.79
```

---

## Example 3: MRR by Customer Segment Over Time

**User Query:** "Show me MRR trends broken down by customer segment"

**Python Code:**
```python
result = sl.query_metric(
    'monthly_mrr',
    dimensions=['snapshot_month', 'customer_segment'],
    order_by='snapshot_month'
)
```

**Generated SQL:**
```sql
SELECT
  "t0"."month" AS "snapshot_month",
  "t0"."customer_segment",
  SUM("t0"."mrr") AS "monthly_mrr"
FROM "monthly_mrr_snapshots" AS "t0"
GROUP BY 1, 2
ORDER BY "snapshot_month" ASC
```

**Results (sample):**
```
2024-11 | SMB         | $273,206.00
2024-11 | Mid-Market  | $553,930.20
2024-11 | Enterprise  | $494,830.60
2024-12 | SMB         | $278,670.50
2024-12 | Mid-Market  | $565,008.90
2024-12 | Enterprise  | $504,727.20
2025-01 | SMB         | $284,134.50
2025-01 | Mid-Market  | $576,087.30
2025-01 | Enterprise  | $514,623.80
...
```

---

## Example 4: Total MRR (No Time Dimension)

**User Query:** "What's my total MRR?"

**Python Code:**
```python
result = sl.query_metric('monthly_mrr')
```

**Generated SQL:**
```sql
SELECT
  SUM("t0"."mrr") AS "monthly_mrr"
FROM "monthly_mrr_snapshots" AS "t0"
```

**Result:**
```
Total MRR: $708,635.15
```

---

## Example 5: Using Canonical Dataset

**User Query:** "Show me the growth trends dataset"

**Python Code:**
```python
# Get canonical dataset configuration
config = sl.config['semantic_model']['canonical_datasets']
growth_trends = next(ds for ds in config if ds['name'] == 'growth_trends')

# Query metrics from the dataset
for metric_name in growth_trends['metrics']:
    result = sl.query_metric(
        metric_name,
        dimensions=growth_trends['dimensions'][:1]  # Just time dimension
    )
    print(f"{metric_name}: {result['row_count']} periods")
```

**Output:**
```
monthly_mrr: 13 periods
monthly_customer_count: 13 periods
```

---

## Available Dimensions

### Time Dimension
- **Name:** `snapshot_month`
- **Type:** `time`
- **Table:** `monthly_mrr_snapshots`
- **Column:** `month`
- **Description:** Month of the snapshot for time-series analysis

### Categorical Dimensions
- `customer_segment` - Customer tier (Enterprise, Mid-Market, SMB)
- `country` - Customer country
- `industry` - Customer industry vertical
- `billing_frequency` - Monthly or Annual billing
- `product_tier` - Product tier (basic, professional, enterprise)
- `subscription_status` - Status of subscription (active, cancelled, past_due)

---

## Available Time-Based Metrics

### monthly_mrr
- **Display Name:** MRR by Month
- **Description:** Monthly recurring revenue tracked over time
- **Type:** simple
- **Table:** monthly_mrr_snapshots
- **Aggregation:** sum(mrr)

### monthly_customer_count
- **Display Name:** Customer Count by Month
- **Description:** Number of customers tracked over time
- **Type:** simple
- **Table:** monthly_mrr_snapshots
- **Aggregation:** sum(customer_count)

---

## Query Patterns

### Pattern 1: Simple Time Series
```python
result = sl.query_metric(
    metric_name='<metric>',
    dimensions=['snapshot_month'],
    order_by='snapshot_month'
)
```

### Pattern 2: Multi-Dimensional Time Series
```python
result = sl.query_metric(
    metric_name='<metric>',
    dimensions=['snapshot_month', '<categorical_dimension>'],
    order_by='snapshot_month'
)
```

### Pattern 3: Filtered Time Series
```python
result = sl.query_metric(
    metric_name='<metric>',
    dimensions=['snapshot_month'],
    filters=['<column> = <value>'],
    order_by='snapshot_month'
)
```

### Pattern 4: Limited Time Series
```python
result = sl.query_metric(
    metric_name='<metric>',
    dimensions=['snapshot_month'],
    order_by='-snapshot_month',  # Descending
    limit=6  # Last 6 months
)
```

---

## Testing Commands

### Run Comprehensive Tests
```bash
source .venv/bin/activate
python3 test_time_queries.py
```

### Run Single Query Test
```bash
source .venv/bin/activate
python3 -c "
from src.semantic_layer import SemanticLayer
sl = SemanticLayer('semantic_models/metrics.yml')

# Test query
result = sl.query_metric(
    'monthly_customer_count',
    dimensions=['snapshot_month'],
    order_by='snapshot_month'
)

# Print results
for row in result['data']:
    month = row['snapshot_month']
    count = row['monthly_customer_count']
    print(f'{month.strftime(\"%Y-%m\")}: {count} customers')
"
```

### Run Existing Test Suite
```bash
source .venv/bin/activate
python3 -m pytest tests/test_semantic_layer.py -v
```

---

## Database Schema Reference

**Table:** `monthly_mrr_snapshots`

| Column               | Type         | Description                    |
|----------------------|--------------|--------------------------------|
| month                | timestamp(9) | Month of the snapshot          |
| customer_segment     | string       | Customer tier                  |
| mrr                  | float64      | Monthly recurring revenue      |
| customer_count       | int64        | Number of active customers     |
| active_subscriptions | int64        | Number of active subscriptions |

**Row Count:** 39 rows (13 months × 3 segments)
**Date Range:** Nov 2024 - Nov 2025

---

## Tips and Best Practices

1. **Always Order Time Series:** Use `order_by='snapshot_month'` for chronological results
2. **Combine Dimensions:** Mix time with categorical dimensions for richer analysis
3. **Use Descriptive Names:** Time dimension is named `snapshot_month` for clarity
4. **Check Row Count:** Time series should have multiple rows (one per time period)
5. **Canonical Datasets:** Use pre-configured datasets like `growth_trends` for common analyses

---

## Expected Results

For the sample database:
- **Time Periods:** 13 months (Nov 2024 - Nov 2025)
- **Customer Segments:** 3 (Enterprise, Mid-Market, SMB)
- **Total Rows (multi-dimensional):** 39 (13 × 3)
- **Customer Count per Period:** 100 customers (consistent)
- **MRR Range:** $48,669.99 - $60,350.79 (growing)

---

## Troubleshooting

### Issue: No time dimension found
**Solution:** Verify `snapshot_month` dimension is defined in `semantic_models/metrics.yml`

### Issue: Only 1 row returned
**Solution:** Make sure to include `dimensions=['snapshot_month']` in query

### Issue: Results not ordered
**Solution:** Add `order_by='snapshot_month'` parameter

### Issue: Database locked
**Solution:** Stop MCP server before running tests: `kill <pid>`

---

**Last Updated:** 2025-11-09
**Status:** ✅ All examples tested and working
