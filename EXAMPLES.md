# Example Queries and Use Cases

This document shows real examples of how to use the Semantic Layer MCP Server with Claude Desktop.

## Table of Contents

- [Basic Queries](#basic-queries)
- [Dimensional Analysis](#dimensional-analysis)
- [Filtering and Segmentation](#filtering-and-segmentation)
- [Trend Analysis](#trend-analysis)
- [Multi-Metric Analysis](#multi-metric-analysis)
- [Business Scenarios](#business-scenarios)
- [Advanced Queries](#advanced-queries)

## Basic Queries

### Discover Available Metrics

**You:** "What metrics are available?"

**Claude:** Lists all metrics with descriptions using the `list_metrics` tool.

### Get a Single Metric

**You:** "What's our total MRR?"

**Claude:** Uses `query_metric` to get the current MRR value.

**Result:**
```
Monthly Recurring Revenue: $48,670.00
```

### Understand a Metric

**You:** "How is MRR calculated?"

**Claude:** Uses `explain_metric` to show the calculation details.

**Result:**
```
**Monthly Recurring Revenue (MRR)**

Total monthly recurring revenue from all active subscriptions

**Type:** simple

**Calculation:**
  - Aggregation: sum
  - Column: subscription_amount
  - Table: subscriptions

**Filters:**
  - subscription_status = 'active'
  - billing_frequency = 'monthly'
```

## Dimensional Analysis

### Break Down by Segment

**You:** "Show me MRR by customer segment"

**Claude Response:**

| customer_segment | total_mrr   |
|------------------|-------------|
| Enterprise       | $24,741.53  |
| Mid-Market       | $18,464.34  |
| SMB              | $5,464.12   |

**Total rows:** 3

**Generated SQL:**
```sql
SELECT customers.customer_segment, SUM(subscriptions.subscription_amount) AS total_mrr
FROM subscriptions
LEFT JOIN customers ON subscriptions.customer_id = customers.customer_id
WHERE subscriptions.subscription_status = 'active'
  AND subscriptions.billing_frequency = 'monthly'
GROUP BY customers.customer_segment
```

### Multiple Dimensions

**You:** "Break down active subscriptions by segment and product tier"

**Result:**

| customer_segment | product_tier  | active_subscriptions |
|------------------|---------------|---------------------|
| Enterprise       | enterprise    | 15                  |
| Enterprise       | professional  | 8                   |
| Mid-Market       | professional  | 22                  |
| Mid-Market       | basic         | 10                  |
| SMB              | basic         | 45                  |
| SMB              | professional  | 7                   |

### Geographic Analysis

**You:** "Show me active customers by country"

**Result:**

| country | active_customers |
|---------|-----------------|
| US      | 35              |
| UK      | 24              |
| Canada  | 18              |
| Germany | 15              |
| France  | 12              |

## Filtering and Segmentation

### Filter by Segment

**You:** "What's the MRR for Enterprise customers only?"

**Claude:** Uses `query_metric` with filter.

**Result:**
```
Enterprise MRR: $24,741.53
(Filtered to: customer_segment = 'Enterprise')
```

### Filter by Country

**You:** "How many customers do we have in the US?"

**Result:**
```
US Customers: 35
```

### Complex Filtering

**You:** "Show me MRR for Enterprise customers in the US using annual billing"

**Result:**
```
Enterprise US Annual MRR: $8,234.50
```

## Trend Analysis

### Monthly Growth

**You:** "Show me MRR trend over the last 6 months"

**Result:**

| month      | monthly_mrr |
|------------|-------------|
| 2024-06-01 | $42,123.45  |
| 2024-07-01 | $44,567.89  |
| 2024-08-01 | $45,890.12  |
| 2024-09-01 | $47,234.56  |
| 2024-10-01 | $48,123.78  |
| 2024-11-01 | $48,670.00  |

**Insight:** MRR grew 15.5% over 6 months

### Segment Growth

**You:** "Compare MRR growth by segment over time"

**Result:**

| month      | customer_segment | monthly_mrr |
|------------|------------------|-------------|
| 2024-09-01 | Enterprise       | $23,456.78  |
| 2024-10-01 | Enterprise       | $24,123.45  |
| 2024-11-01 | Enterprise       | $24,741.53  |
| 2024-09-01 | Mid-Market       | $17,234.56  |
| 2024-10-01 | Mid-Market       | $17,890.12  |
| 2024-11-01 | Mid-Market       | $18,464.34  |

## Multi-Metric Analysis

### Customer Health Dashboard

**You:** "Show me a customer health dashboard"

**Claude:** Queries multiple metrics and presents them together.

**Result:**

**Customer Health Metrics**

- **Total MRR:** $48,670.00
- **Active Customers:** 104
- **ARPU:** $467.98
- **Churn Rate:** 9.6%
- **Total Subscriptions:** 146
- **Active Subscriptions:** 127

**By Segment:**

| Segment    | MRR        | Customers | ARPU     | Subs |
|------------|------------|-----------|----------|------|
| Enterprise | $24,741.53 | 20        | $1,237.08| 40   |
| Mid-Market | $18,464.34 | 30        | $615.48  | 45   |
| SMB        | $5,464.12  | 50        | $109.28  | 42   |

### Revenue Analysis

**You:** "Give me a complete revenue analysis"

**Metrics:**
- Total MRR: $48,670.00
- ARR (Projected): $584,040.00
- Average Subscription Value: $456.78
- Total Revenue (all billing types): $156,234.89

### Growth Metrics

**You:** "What are our key growth metrics?"

**Result:**
- New Customers (this month): 8
- Monthly Growth Rate: 3.2%
- Customer Acquisition by Segment: Enterprise (2), Mid-Market (3), SMB (3)
- Net Revenue Retention: 112%

## Business Scenarios

### Executive Dashboard

**Scenario:** CEO wants a quick overview

**You:** "Give me the executive summary of our subscription business"

**Claude Response:**

**Executive Summary - Subscription Business**

**Revenue:**
- Monthly Recurring Revenue: $48,670
- Annual Run Rate: $584,040
- Quarter-over-Quarter Growth: 12.3%

**Customers:**
- Active Customers: 104
- Average Revenue Per User: $467.98
- Customer Distribution: 20 Enterprise, 30 Mid-Market, 50 SMB

**Health Metrics:**
- Churn Rate: 9.6% (Within target <10%)
- Active Subscriptions: 127 of 146 total
- Subscription Growth: +15 this quarter

**Key Insights:**
- Enterprise segment drives 51% of revenue with only 19% of customers
- Strong ARPU in Enterprise ($1,237) vs SMB ($109)
- Opportunity to reduce churn in SMB segment

### Sales Team Analysis

**Scenario:** Sales manager needs segment performance

**You:** "Which customer segment is performing best?"

**Result:**

**Segment Performance Analysis**

| Metric          | Enterprise | Mid-Market | SMB     |
|-----------------|------------|------------|---------|
| MRR             | $24,741    | $18,464    | $5,464  |
| Customers       | 20         | 30         | 50      |
| ARPU            | $1,237     | $615       | $109    |
| Churn %         | 5.2%       | 8.1%       | 12.4%   |
| Revenue Share   | 51%        | 38%        | 11%     |

**Key Findings:**
- Enterprise has best retention (94.8%)
- Mid-Market offers best growth potential
- SMB needs churn reduction focus

### Finance Team Reporting

**Scenario:** CFO needs monthly board report

**You:** "Create a financial summary for the board meeting"

**Result:**

**Monthly Board Report - Financial Metrics**

**Revenue Metrics:**
- MRR: $48,670 (+3.2% MoM)
- ARR: $584,040
- New MRR: $1,845
- Churned MRR: $423
- Net New MRR: $1,422

**Customer Metrics:**
- Ending Customers: 104 (+8 net new)
- New Customers: 12
- Churned Customers: 4
- Logo Retention: 96.2%

**Unit Economics:**
- ARPU: $467.98
- Gross Margin: 82%
- LTV:CAC Ratio: 4.2:1

### Product Team Analysis

**Scenario:** Product manager analyzing feature adoption

**You:** "Which product tiers are customers choosing?"

**Result:**

| product_tier  | subscriptions | percentage | mrr_contribution |
|---------------|---------------|------------|------------------|
| enterprise    | 38            | 26%        | $25,456.78       |
| professional  | 54            | 37%        | $18,234.56       |
| basic         | 54            | 37%        | $4,978.66        |

**Insight:** Enterprise tier drives 52% of revenue from just 26% of subscriptions

## Advanced Queries

### Cohort Analysis

**You:** "Show me retention by signup cohort"

*Note: This requires additional time-based dimensions in your semantic model*

### Comparative Analysis

**You:** "Compare this quarter to last quarter"

**Result:**

| Metric              | Q3 2024    | Q4 2024    | Change  |
|---------------------|------------|------------|---------|
| MRR                 | $42,345    | $48,670    | +14.9%  |
| Active Customers    | 96         | 104        | +8.3%   |
| Churn Rate          | 11.2%      | 9.6%       | -1.6pp  |

### Forecasting

**You:** "If we maintain current growth rate, what will MRR be in 3 months?"

**Claude:** Uses historical data and calculates projection.

**Result:**
```
Current MRR: $48,670
Growth Rate (3-month avg): 3.2% per month
Projected MRR (3 months): $53,643

Projection assumes:
- Current growth rate continues
- Churn remains at ~10%
- No major customer additions/losses
```

### Anomaly Detection

**You:** "Are there any unusual patterns in our subscription data?"

**Claude Response:**

**Potential Anomalies Detected:**

1. **High Churn in SMB Segment**
   - SMB churn (12.4%) is 2.4x Enterprise rate (5.2%)
   - Recommendation: Investigate onboarding/support for SMB

2. **ARPU Variance**
   - Enterprise ARPU ($1,237) is 11x SMB ARPU ($109)
   - Opportunity: Upsell SMB to higher tiers

3. **Geography Concentration**
   - 34% of revenue from US only
   - Risk: Geographic concentration

### Custom Calculations

**You:** "Calculate the payback period if CAC is $500 and ARPU is $468"

**Result:**
```
CAC: $500
ARPU: $468
Gross Margin: 82%

Payback Period:
$500 / ($468 * 0.82) = 1.3 months

Very healthy! Typical SaaS target is <12 months.
```

## Tips for Effective Querying

### Be Specific

❌ "Show me revenue"
✅ "Show me MRR by customer segment"

### Use Business Language

❌ "SELECT SUM(amount) FROM subs"
✅ "What's our total MRR?"

### Ask Follow-ups

1. "What's our MRR?"
2. "Break that down by segment"
3. "Which segment has the best growth?"
4. "Show me the trend for Enterprise over 6 months"

### Explore Dimensions

- "What dimensions can I group by?"
- "List all countries"
- "Show me all product tiers"

### Validate Understanding

- "How do you calculate churn rate?"
- "What filters are applied to MRR?"
- "Show me the SQL for that query"

## Common Patterns

### Pattern 1: Explore → Analyze → Deep Dive

```
You: "What metrics are available?"
→   "Show me MRR"
→   "Break down by segment"
→   "Show Enterprise trend over time"
→   "Which countries are our Enterprise customers in?"
```

### Pattern 2: Dashboard → Insight → Action

```
You: "Show me customer health metrics"
→   "Why is SMB churn so high?"
→   "What's the ARPU difference between Basic and Professional tiers?"
→   "What would MRR look like if we converted 20% of Basic to Professional?"
```

### Pattern 3: Question → Validation → Decision

```
You: "Should we focus on Enterprise or SMB?"
→   "Compare revenue and churn by segment"
→   "What's the CAC by segment?" (needs additional data)
→   "Show growth potential for each"
→   "Recommendation: Focus on Enterprise (higher ARPU, lower churn)"
```

## Next Steps

- **Define Your Metrics:** Add your business-specific metrics to `semantic_models/metrics.yml`
- **Add Dimensions:** Include your key grouping dimensions
- **Create Canonical Datasets:** Define common analyses as reusable datasets
- **Train Your Team:** Share these examples with your team

---

**Remember:** The semantic layer ensures everyone uses the same metric definitions, so "MRR" means the same thing whether you ask Claude, write a SQL query, or build a dashboard.
