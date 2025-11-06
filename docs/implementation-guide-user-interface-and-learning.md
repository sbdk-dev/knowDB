# Implementation Guide: User Interface, Canonical Datasets & Reinforcement Learning

**Version:** 1.0
**Date:** 2025-11-06
**Status:** Technical Implementation Guide

---

## Executive Summary

This document answers the critical "how" questions:

1. **User Interface:** How do users interact with the system?
2. **Metric Definition:** Single source of truth for metrics
3. **Agent Generation:** How agents generate everything from metric definitions
4. **Canonical Datasets:** Building alignment for advanced analytics (attribution, lifecycle, cohorts)
5. **Knowledge Graph Feedback:** How KG tracks usage and updates semantic layer
6. **Reinforcement Learning:** Concrete implementation of RL training loop

---

## Part 1: User Interface - The Metric Explorer

### The Core UX: Metric-First, Not SQL-First

**Traditional Approach (SQL-First):**
```
User → Writes SQL → Runs query → Gets results
❌ Problems: Technical barrier, inconsistent definitions, no reuse
```

**New Approach (Metric-First):**
```
User → Browses metrics → Selects dimensions → Agent generates everything
✅ Benefits: No SQL needed, consistent definitions, automatic optimization
```

### The Metric Explorer Interface

#### Interface 1: Web UI (BI Tool-Like)

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Metric Explorer                          [User: Jane]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 All Metrics (234)      🔍 Search metrics...             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📈 Revenue Metrics (12)                             │   │
│  │   ├─ Monthly Recurring Revenue (MRR)                │   │
│  │   │   Definition: SUM of active subscription amounts│   │
│  │   │   Owner: Finance Team                           │   │
│  │   │   Last Updated: 2024-11-01                      │   │
│  │   │   Status: ✅ Certified                          │   │
│  │   │   Usage: 247 queries this month                 │   │
│  │   │   [View Details] [Query] [Edit]                 │   │
│  │   │                                                  │   │
│  │   ├─ Customer Lifetime Value (LTV)                  │   │
│  │   ├─ Annual Recurring Revenue (ARR)                 │   │
│  │   └─ ...                                            │   │
│  │                                                      │   │
│  │ 👥 Customer Metrics (18)                            │   │
│  │   ├─ Churn Rate                                     │   │
│  │   ├─ Net Revenue Retention (NRR)                    │   │
│  │   └─ ...                                            │   │
│  │                                                      │   │
│  │ 🎯 Product Metrics (34)                             │   │
│  │   ├─ Daily Active Users (DAU)                       │   │
│  │   └─ ...                                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [+ Define New Metric]  [Import from BI Tool]  [Settings]  │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Search & Browse:** Searchable catalog of all metrics
- **Metadata:** Definition, owner, certification status, usage stats
- **One-Click Query:** Click metric → agent generates query
- **Governance:** Approval workflows for new/changed metrics

#### Interface 2: Claude Desktop (Conversational)

```
User: "Show me all revenue metrics we have"

Agent: I found 12 revenue metrics in your catalog:

📈 Core Revenue Metrics:
1. Monthly Recurring Revenue (MRR)
   - Used 247 times this month
   - Certified ✅

2. Annual Recurring Revenue (ARR)
   - Derived from MRR × 12
   - Certified ✅

3. Customer Lifetime Value (LTV)
   - Complex calculation with cohort analysis
   - Last updated: 2024-11-01

Which would you like to explore?

User: "Show me MRR by customer segment for last quarter"

Agent: [Searches knowledge graph for optimal path]
       [Finds learned skill: "mrr_by_segment"]
       [Generates and executes query]

Q3 2024 MRR by Segment:
- Enterprise: $2.4M (↑12% vs Q2)
- Mid-Market: $1.8M (↑8%)
- SMB: $890K (↓3%)

Total MRR: $5.09M

Would you like me to:
- Show trend over time
- Break down by geography
- Compare to target
- Save as dashboard
```

#### Interface 3: Metric Definition UI

```
┌─────────────────────────────────────────────────────────────┐
│  Define New Metric                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Basic Information:                                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Name*: [Monthly Recurring Revenue                   ] │ │
│  │ Short Name: [MRR                                     ] │ │
│  │ Category: [Revenue Metrics ▼                         ] │ │
│  │ Owner: [Finance Team ▼                               ] │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Definition:                                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Simple Definition (for non-technical users):          │ │
│  │ [Total value of active subscriptions per month      ] │ │
│  │                                                        │ │
│  │ Technical Definition (optional - agent can infer):    │ │
│  │ ○ Let agent generate SQL                             │ │
│  │ ○ Provide SQL formula:                                │ │
│  │   [SELECT SUM(subscription_amount)                   ] │ │
│  │   [FROM fct_subscriptions                            ] │ │
│  │   [WHERE subscription_status = 'active'              ] │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Data Sources:                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Agent suggests:                                        │ │
│  │ ✅ fct_subscriptions (primary)                        │ │
│  │ ⚠️ dim_customers (for segmentation)                   │ │
│  │ ℹ️ fct_orders (alternative source - lower quality)    │ │
│  │                                                        │ │
│  │ [Accept Suggestions] [Modify] [Manual Selection]      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Dimensions Available:                                      │
│  ☑ Time (day, week, month, quarter, year)                  │
│  ☑ Customer Segment (Enterprise, Mid-Market, SMB)          │
│  ☑ Geography (Country, Region)                             │
│  ☑ Product Line                                             │
│  ☐ Sales Rep (not applicable for MRR)                      │
│                                                             │
│  Business Rules:                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Exclude trial subscriptions                         │ │
│  │ • Only count 'active' and 'past_due' status           │ │
│  │ • Convert annual contracts to monthly equivalent      │ │
│  │ [+ Add Rule]                                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Certification:                                             │
│  ○ Draft (testing)                                          │
│  ○ Published (available to team)                            │
│  ○ Certified (approved for company-wide use)                │
│                                                             │
│  [Cancel] [Save as Draft] [Preview] [Publish]              │
└─────────────────────────────────────────────────────────────┘
```

### What Happens When User Defines a Metric

#### Step 1: User Inputs Simple Definition

```yaml
# User provides minimal information:
name: "Monthly Recurring Revenue"
short_name: "MRR"
category: "Revenue"
simple_definition: "Total value of active subscriptions per month"
business_rules:
  - "Exclude trial subscriptions"
  - "Only count active and past_due status"
  - "Convert annual contracts to monthly equivalent"
```

#### Step 2: Agent Analyzes and Suggests

```python
# Agent analyzes the definition

class MetricDefinitionAgent:
    def analyze_metric_definition(self, user_input: dict) -> dict:
        """
        Agent analyzes user's simple definition and generates
        complete technical specification
        """

        # Step 1: Semantic search in knowledge graph
        relevant_tables = self.knowledge_graph.semantic_search(
            query=user_input['simple_definition'],
            tags=['fact_table', 'subscription_data']
        )

        # Step 2: Find similar existing metrics
        similar_metrics = self.agentdb.vector.search(
            query=user_input['simple_definition'],
            tags=['certified_metric'],
            top_k=5
        )

        # Step 3: Search for learned skills
        relevant_skills = self.agentdb.skill.search(
            query="subscription revenue calculation",
            min_similarity=0.7
        )

        # Step 4: Generate suggestions
        suggestions = {
            "primary_table": relevant_tables[0],  # fct_subscriptions
            "join_paths": self.find_join_paths(relevant_tables),
            "similar_metrics": similar_metrics,
            "reusable_cte": relevant_skills[0] if relevant_skills else None,
            "suggested_sql": self.generate_sql_draft(user_input, relevant_tables),
            "available_dimensions": self.infer_dimensions(relevant_tables),
            "data_quality_checks": self.suggest_quality_checks(user_input)
        }

        return suggestions

    def generate_sql_draft(self, user_input: dict, tables: list) -> str:
        """
        Agent generates initial SQL based on simple definition
        """

        # Use LLM with context from knowledge graph + learned skills
        context = {
            "metric_definition": user_input['simple_definition'],
            "business_rules": user_input['business_rules'],
            "available_tables": tables,
            "similar_metrics": self.find_similar_sql_patterns(),
            "learned_skills": self.get_relevant_skills()
        }

        sql = self.llm.generate(
            prompt=f"""
            Generate dbt SQL model for metric: {user_input['name']}

            Definition: {user_input['simple_definition']}

            Business Rules:
            {yaml.dump(user_input['business_rules'])}

            Available tables:
            {yaml.dump([t.name for t in tables])}

            Similar successful patterns:
            {yaml.dump(context['similar_metrics'])}

            Requirements:
            - Use CTE pattern
            - Add comprehensive comments
            - Include data quality checks
            - Make it reusable for different time grains
            """,
            context=context
        )

        return sql
```

#### Step 3: Agent Generates Everything

```python
# Agent generates complete metric package

generated_assets = {
    # 1. dbt model (SQL)
    "dbt_model": "models/metrics/metric_mrr.sql",

    # 2. Semantic layer definition (YAML)
    "semantic_definition": "semantic_models/revenue_metrics.yml",

    # 3. Documentation
    "documentation": "models/metrics/metric_mrr.md",

    # 4. Tests
    "tests": [
        "tests/metrics/test_mrr_not_null.sql",
        "tests/metrics/test_mrr_positive.sql",
        "tests/metrics/test_mrr_reasonable_range.sql"
    ],

    # 5. Knowledge graph nodes
    "graph_nodes": {
        "metric_node": "(m:Metric {name: 'MRR', ...})",
        "relationships": [
            "(m)-[:COMPUTED_FROM]->(fct_subscriptions)",
            "(m)-[:HAS_DIMENSION]->(time)",
            "(m)-[:HAS_DIMENSION]->(customer_segment)"
        ]
    },

    # 6. AgentDB skill (if new pattern)
    "skill_entry": {
        "name": "subscription_revenue_calculation",
        "pattern": "...",
        "metadata": {...}
    }
}
```

#### Step 4: Generated dbt Model Example

```sql
-- models/metrics/metric_mrr.sql
-- Generated by MetricDefinitionAgent
-- Metric: Monthly Recurring Revenue (MRR)
-- Owner: Finance Team
-- Generated: 2025-11-06

{{
  config(
    materialized='table',
    partition_by={'field': 'month', 'data_type': 'date'},
    cluster_by=['customer_segment'],
    tags=['metric', 'revenue', 'certified']
  )
}}

WITH subscriptions_base AS (
  -- Get all active subscriptions
  -- Source: fct_subscriptions
  -- Learned from skill: subscription_revenue_calculation
  SELECT
    subscription_id,
    customer_id,
    subscription_amount,
    billing_frequency,
    subscription_status,
    start_date,
    end_date
  FROM {{ ref('fct_subscriptions') }}
  WHERE subscription_status IN ('active', 'past_due')
    AND subscription_type != 'trial'  -- Business rule: exclude trials
),

normalized_monthly AS (
  -- Convert all subscriptions to monthly equivalent
  -- Business rule: annual contracts → monthly equivalent
  SELECT
    subscription_id,
    customer_id,
    CASE
      WHEN billing_frequency = 'annual' THEN subscription_amount / 12.0
      WHEN billing_frequency = 'quarterly' THEN subscription_amount / 3.0
      WHEN billing_frequency = 'monthly' THEN subscription_amount
      ELSE subscription_amount  -- Default to as-is
    END AS monthly_amount,
    subscription_status
  FROM subscriptions_base
),

customer_enrichment AS (
  -- Join to customer dimensions for segmentation
  SELECT
    n.subscription_id,
    n.customer_id,
    n.monthly_amount,
    c.customer_segment,
    c.geography,
    c.signup_cohort
  FROM normalized_monthly n
  LEFT JOIN {{ ref('dim_customers') }} c
    ON n.customer_id = c.customer_id
),

mrr_aggregated AS (
  SELECT
    DATE_TRUNC('month', CURRENT_DATE) AS month,
    SUM(monthly_amount) AS mrr_total,
    COUNT(DISTINCT customer_id) AS paying_customers,
    AVG(monthly_amount) AS arpc  -- Average Revenue Per Customer
  FROM customer_enrichment
  GROUP BY 1
),

mrr_by_segment AS (
  SELECT
    DATE_TRUNC('month', CURRENT_DATE) AS month,
    customer_segment,
    SUM(monthly_amount) AS mrr,
    COUNT(DISTINCT customer_id) AS customers
  FROM customer_enrichment
  GROUP BY 1, 2
),

final AS (
  SELECT
    a.month,
    a.mrr_total,
    a.paying_customers,
    a.arpc,
    s.customer_segment,
    s.mrr AS segment_mrr,
    s.customers AS segment_customers,
    s.mrr / NULLIF(a.mrr_total, 0) AS segment_mrr_pct
  FROM mrr_aggregated a
  CROSS JOIN mrr_by_segment s
    ON a.month = s.month
)

SELECT * FROM final

-- Data Quality Checks (dbt tests will validate):
-- 1. MRR should never be negative
-- 2. MRR should be within expected range ($1M - $10M)
-- 3. Paying customers should be > 1000
-- 4. Segment MRR should sum to total MRR
```

#### Step 5: Generated Semantic Layer Definition

```yaml
# semantic_models/revenue_metrics.yml
# Generated by MetricDefinitionAgent

semantic_model:
  name: revenue_metrics

  model: metric_mrr

  entities:
    - name: subscription
      type: primary
      expr: subscription_id

    - name: customer
      type: foreign
      expr: customer_id

  dimensions:
    - name: month
      type: time
      type_params:
        time_granularity: month

    - name: customer_segment
      type: categorical
      expr: customer_segment

    - name: geography
      type: categorical
      expr: geography

  measures:
    - name: mrr_total
      description: "Total Monthly Recurring Revenue across all customers"
      agg: sum
      expr: mrr_total

    - name: paying_customers
      description: "Count of customers with active paid subscriptions"
      agg: sum
      expr: paying_customers

    - name: arpc
      description: "Average Revenue Per Customer"
      agg: average
      expr: arpc

  metrics:
    - name: mrr
      description: |
        Monthly Recurring Revenue (MRR): Total value of active subscriptions per month.
        Excludes trials. Normalizes annual/quarterly contracts to monthly equivalent.
      type: simple
      type_params:
        measure: mrr_total
      label: Monthly Recurring Revenue

    - name: mrr_growth_rate
      description: "Month-over-month MRR growth rate"
      type: derived
      type_params:
        expr: (mrr - LAG(mrr, 1) OVER (ORDER BY month)) / LAG(mrr, 1) OVER (ORDER BY month)
        metrics:
          - mrr
```

---

## Part 2: Canonical Datasets for Advanced Analytics

### The Problem: Advanced Analytics Needs Consistent Foundation

**Advanced analytics like attribution, lifecycle modeling, and cohort analysis require:**
- ✅ Canonical datasets (agreed-upon "golden" data models)
- ✅ Consistent grain (same level of detail across models)
- ✅ Aligned business logic (churn means the same everywhere)
- ✅ Dimensional conformity (same customer_id everywhere)

### Solution: Canonical Dataset Registry

#### Canonical Dataset Definition

```yaml
# canonical_datasets.yml
# The "golden" data models that power all advanced analytics

canonical_datasets:

  # Core Entity: Customer
  - name: dim_customers_canonical
    type: dimension
    grain: customer_id
    purpose: "Single source of truth for customer attributes"
    owner: Data Platform Team
    certification: certified
    sla:
      freshness: "1 hour"
      completeness: "> 99%"

    core_attributes:
      - customer_id (unique, not null)
      - email (unique, not null)
      - signup_date (not null)
      - customer_segment (Enterprise | Mid-Market | SMB)
      - geography
      - current_status (active | churned | dormant)

    usage_count: 1247  # Used by 1247 downstream models/queries

    lineage:
      sources:
        - raw.salesforce.accounts
        - raw.stripe.customers
        - raw.product.users
      transformation: models/core/dim_customers.sql
      downstream:
        - mart_customer_revenue
        - mart_customer_lifecycle
        - mart_attribution

  # Core Fact: User Events
  - name: fct_user_events_canonical
    type: fact
    grain: event_id (one row per event)
    purpose: "All user behavioral events for product analytics"
    owner: Product Analytics Team
    certification: certified

    core_attributes:
      - event_id (unique)
      - user_id
      - event_type (page_view | button_click | feature_used)
      - event_timestamp
      - session_id
      - page_url
      - event_properties (JSON)

    usage_count: 892

  # Advanced Mart: Customer Lifecycle
  - name: mart_customer_lifecycle_canonical
    type: mart
    grain: customer_id, month
    purpose: "Customer lifecycle states for cohort and retention analysis"
    owner: Growth Team
    certification: certified

    methodology: "Based on Rasmus Engelbrecht's user lifecycle framework"
    reference: "https://rasmusengelbrecht.substack.com/p/beyond-mau"

    lifecycle_states:
      - new (first month)
      - active (used product this month, used last month)
      - retained (active for 2+ consecutive months)
      - resurrected (inactive previously, active now)
      - churned (active previously, inactive now)

    core_attributes:
      - customer_id
      - month
      - lifecycle_state
      - months_since_signup
      - cohort_month
      - is_paying
      - mrr

    usage_count: 456
    downstream_analytics:
      - cohort_retention_analysis
      - churn_prediction_model
      - customer_health_scoring
```

### How Agents Use Canonical Datasets

```python
class AdvancedAnalyticsAgent:
    """
    Agent specialized in building advanced analytics on top of
    canonical datasets
    """

    def build_attribution_model(self, business_question: str) -> str:
        """
        Example: "Build multi-touch attribution model for marketing spend ROI"
        """

        # Step 1: Identify required canonical datasets
        required_datasets = self.identify_canonical_datasets(
            business_question
        )
        # Returns: ['dim_customers_canonical',
        #           'fct_user_events_canonical',
        #           'fct_marketing_touchpoints_canonical',
        #           'fct_subscriptions_canonical']

        # Step 2: Search for learned attribution patterns
        attribution_skills = self.agentdb.skill.search(
            query="multi-touch attribution marketing",
            top_k=3
        )

        # Step 3: Check knowledge graph for optimal join paths
        join_path = self.knowledge_graph.find_join_path(
            entities=required_datasets,
            optimization='minimize_fan_out'
        )

        # Step 4: Generate attribution model using canonical datasets
        dbt_model = self.generate_dbt_model(
            model_name="mart_marketing_attribution",
            canonical_datasets=required_datasets,
            join_path=join_path,
            learned_pattern=attribution_skills[0] if attribution_skills else None,
            attribution_method="shapley_value"  # or "first_touch", "linear", etc.
        )

        return dbt_model

    def generate_dbt_model(
        self,
        model_name: str,
        canonical_datasets: list,
        join_path: dict,
        learned_pattern: dict,
        attribution_method: str
    ) -> str:
        """
        Generate dbt model that builds on canonical datasets
        """

        # Generate SQL using LLM with strong constraints
        sql = self.llm.generate(
            prompt=f"""
            Generate dbt model: {model_name}

            Requirements:
            - MUST use these canonical datasets: {canonical_datasets}
            - MUST NOT recreate logic from canonical datasets
            - Use optimal join path: {join_path}
            - Apply {attribution_method} attribution

            Canonical dataset grain guarantees:
            - dim_customers_canonical: one row per customer_id
            - fct_user_events_canonical: one row per event_id
            - fct_marketing_touchpoints_canonical: one row per touchpoint_id

            Generate marts on top of these canonicals, don't rebuild them.
            """,
            constraints={
                "must_reference": canonical_datasets,
                "forbidden_patterns": ["LEFT JOIN raw."],  # Don't go to raw sources
                "required_patterns": ["{{ ref('dim_customers_canonical') }}"]
            }
        )

        return sql
```

### Generated Attribution Model Example

```sql
-- models/marts/marketing/mart_marketing_attribution.sql
-- Generated by AdvancedAnalyticsAgent
-- Uses canonical datasets: dim_customers, fct_marketing_touchpoints, fct_subscriptions

{{
  config(
    materialized='incremental',
    unique_key='customer_id',
    partition_by={'field': 'conversion_date', 'data_type': 'date'}
  )
}}

WITH touchpoints AS (
  -- Get all marketing touchpoints from canonical dataset
  -- DO NOT rebuild touchpoint logic - it's already canonical
  SELECT
    customer_id,
    touchpoint_id,
    touchpoint_timestamp,
    channel,
    campaign,
    spend_allocated
  FROM {{ ref('fct_marketing_touchpoints_canonical') }}
  {% if is_incremental() %}
  WHERE touchpoint_timestamp > (SELECT MAX(conversion_date) FROM {{ this }})
  {% endif %}
),

conversions AS (
  -- Get conversion events (subscription starts) from canonical dataset
  SELECT
    customer_id,
    subscription_start_date AS conversion_date,
    first_payment_amount AS conversion_value
  FROM {{ ref('fct_subscriptions_canonical') }}
  WHERE subscription_type = 'paid'  -- Exclude trials
),

touchpoint_journey AS (
  -- Join touchpoints to conversions
  SELECT
    t.customer_id,
    t.touchpoint_id,
    t.touchpoint_timestamp,
    t.channel,
    t.campaign,
    t.spend_allocated,
    c.conversion_date,
    c.conversion_value,
    -- Calculate position in journey
    ROW_NUMBER() OVER (
      PARTITION BY t.customer_id
      ORDER BY t.touchpoint_timestamp
    ) AS touchpoint_position,
    COUNT(*) OVER (
      PARTITION BY t.customer_id
    ) AS total_touchpoints
  FROM touchpoints t
  INNER JOIN conversions c
    ON t.customer_id = c.customer_id
    AND t.touchpoint_timestamp <= c.conversion_date
    AND t.touchpoint_timestamp >= DATEADD(day, -90, c.conversion_date)
),

-- Apply Shapley value attribution (multi-touch)
shapley_attribution AS (
  SELECT
    customer_id,
    touchpoint_id,
    channel,
    campaign,
    conversion_value,
    -- Shapley value: equal credit to all touchpoints
    -- (This is simplified - real Shapley is more complex)
    conversion_value / NULLIF(total_touchpoints, 0) AS attributed_value,
    spend_allocated / NULLIF(total_touchpoints, 0) AS attributed_spend
  FROM touchpoint_journey
),

aggregated_by_campaign AS (
  SELECT
    campaign,
    channel,
    SUM(attributed_value) AS total_attributed_revenue,
    SUM(attributed_spend) AS total_attributed_spend,
    COUNT(DISTINCT customer_id) AS customers_influenced,
    SUM(attributed_value) / NULLIF(SUM(attributed_spend), 0) AS roi
  FROM shapley_attribution
  GROUP BY 1, 2
)

SELECT * FROM aggregated_by_campaign

-- This model builds ON TOP OF canonical datasets
-- It doesn't recreate customer logic, event tracking, or touchpoint capture
-- Those are already handled in the canonical layer
```

### Canonical Dataset Governance

```python
class CanonicalDatasetGovernance:
    """
    Enforces that all advanced analytics builds on canonical datasets
    """

    def validate_model(self, dbt_model_sql: str) -> dict:
        """
        Validate that model follows canonical dataset principles
        """

        validation_results = {
            "uses_canonical_datasets": False,
            "avoids_raw_sources": False,
            "consistent_grain": False,
            "errors": [],
            "warnings": []
        }

        # Parse SQL to extract referenced models
        referenced_models = self.parse_dbt_refs(dbt_model_sql)

        # Check 1: Must reference at least one canonical dataset
        canonical_refs = [
            ref for ref in referenced_models
            if ref.endswith('_canonical')
        ]

        if not canonical_refs:
            validation_results["errors"].append(
                "Model does not reference any canonical datasets. "
                "Advanced analytics should build on canonical layer."
            )
        else:
            validation_results["uses_canonical_datasets"] = True

        # Check 2: Should NOT reference raw sources directly
        raw_refs = [
            ref for ref in referenced_models
            if ref.startswith('raw.')
        ]

        if raw_refs:
            validation_results["warnings"].append(
                f"Model references raw sources: {raw_refs}. "
                f"Consider using canonical datasets instead."
            )
        else:
            validation_results["avoids_raw_sources"] = True

        # Check 3: Grain consistency check
        grain_check = self.validate_grain_consistency(
            dbt_model_sql,
            canonical_refs
        )
        validation_results["consistent_grain"] = grain_check["valid"]
        if not grain_check["valid"]:
            validation_results["errors"].append(grain_check["error"])

        return validation_results

    def suggest_canonical_dataset(self, user_intent: str) -> list:
        """
        Agent suggests which canonical datasets to use
        """

        # Semantic search in knowledge graph
        candidates = self.knowledge_graph.query("""
            MATCH (m:Model {canonical: true})
            RETURN m.name AS dataset_name,
                   m.purpose AS purpose,
                   m.usage_count AS popularity
            ORDER BY m.usage_count DESC
        """)

        # Semantic similarity search in AgentDB
        similar_usage = self.agentdb.vector.search(
            query=user_intent,
            tags=["canonical_dataset_usage"],
            top_k=5
        )

        # Combine and rank
        suggestions = self.rank_canonical_datasets(
            candidates,
            similar_usage,
            user_intent
        )

        return suggestions
```

---

## Part 3: Knowledge Graph Feedback Loop

### How the Knowledge Graph Tracks Usage and Updates Semantic Layer

#### Architecture: Continuous Feedback Loop

```
┌─────────────────────────────────────────────────────────────┐
│  1. User Queries Warehouse (via MCP)                       │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Query Execution Tracker                                 │
│     - Logs every query                                      │
│     - Records: SQL, user, timestamp, execution_time, result │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Query Pattern Analyzer (Real-Time)                      │
│     - Parses SQL to extract:                                │
│       • Tables accessed                                     │
│       • Join paths used                                     │
│       • Metrics calculated                                  │
│       • Filters applied                                     │
│       • Aggregations                                        │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Knowledge Graph Updater (Real-Time)                     │
│     - Creates/updates nodes:                                │
│       CREATE (q:Query {id, sql, timestamp, ...})            │
│     - Creates relationships:                                │
│       (q)-[:ACCESSES]->(table)                              │
│       (q)-[:USES_JOIN_PATH]->(path)                         │
│       (q)-[:CALCULATES]->(metric)                           │
│     - Updates edge weights:                                 │
│       SET relationship.weight += 1                          │
│       SET relationship.last_used = now()                    │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  5. Usage Statistics Aggregator (Batch - Hourly)            │
│     - Counts query patterns                                 │
│     - Identifies trending metrics                           │
│     - Detects new join patterns                             │
│     - Measures query performance                            │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  6. Semantic Layer Auto-Updater (Batch - Nightly)           │
│     - Proposes new metrics (if queried 10+ times)           │
│     - Suggests dimension additions                          │
│     - Updates metric popularity rankings                    │
│     - Flags deprecated metrics (not used in 90 days)        │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  7. Human Review & Approval                                 │
│     - Data team reviews proposed changes                    │
│     - Approves/rejects/modifies                             │
│     - Certifies new metrics                                 │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  8. Semantic Layer Deployment                               │
│     - Updates semantic_models.yml                           │
│     - Commits to git                                        │
│     - Triggers dbt run                                      │
│     - Updates metric catalog UI                             │
└─────────────────────────────────────────────────────────────┘
```

### Implementation: Query Execution Tracker

```python
# Real-time query tracking

from typing import Dict, Any
import sqlparse
from neo4j import GraphDatabase
from agentdb import AgentDB

class QueryExecutionTracker:
    """
    Tracks every query execution and updates knowledge graph in real-time
    """

    def __init__(self):
        self.neo4j = GraphDatabase.driver("bolt://localhost:7687")
        self.agentdb = AgentDB(path="./warehouse-memory.db")
        self.warehouse = WarehouseConnection()

    def track_query_execution(
        self,
        sql: str,
        user: str,
        execution_result: Dict[str, Any]
    ):
        """
        Called after every query execution
        """

        # Step 1: Parse SQL to extract patterns
        parsed = self.parse_sql(sql)

        query_metadata = {
            "query_id": generate_uuid(),
            "sql": sql,
            "user": user,
            "timestamp": datetime.now(),
            "execution_time_ms": execution_result['time_ms'],
            "rows_returned": execution_result['row_count'],
            "success": execution_result['success'],

            # Extracted patterns
            "tables_accessed": parsed['tables'],
            "joins_used": parsed['joins'],
            "metrics_calculated": parsed['metrics'],
            "dimensions_used": parsed['dimensions'],
            "filters": parsed['filters'],
            "time_grain": parsed['time_grain']
        }

        # Step 2: Update knowledge graph (real-time)
        self.update_knowledge_graph(query_metadata)

        # Step 3: Store in AgentDB for learning (real-time)
        self.store_in_agentdb(query_metadata)

        # Step 4: Check if this reveals a new pattern (real-time)
        self.detect_new_patterns(query_metadata)

    def parse_sql(self, sql: str) -> Dict[str, Any]:
        """
        Parse SQL to extract semantic patterns
        """

        parsed = sqlparse.parse(sql)[0]

        return {
            "tables": self.extract_tables(parsed),
            "joins": self.extract_join_paths(parsed),
            "metrics": self.extract_metrics(parsed),
            "dimensions": self.extract_dimensions(parsed),
            "filters": self.extract_filters(parsed),
            "time_grain": self.infer_time_grain(parsed)
        }

    def update_knowledge_graph(self, query_metadata: dict):
        """
        Update Neo4j knowledge graph with query execution data
        """

        with self.neo4j.session() as session:
            # Create query node
            session.run("""
                CREATE (q:Query {
                    id: $query_id,
                    user: $user,
                    timestamp: datetime($timestamp),
                    execution_time_ms: $execution_time_ms,
                    rows_returned: $rows_returned,
                    success: $success
                })
            """, **query_metadata)

            # Link to tables accessed
            for table in query_metadata['tables_accessed']:
                session.run("""
                    MATCH (q:Query {id: $query_id})
                    MATCH (t:Table {name: $table})
                    MERGE (q)-[r:ACCESSES]->(t)
                    SET r.count = coalesce(r.count, 0) + 1,
                        r.last_accessed = datetime()
                """, query_id=query_metadata['query_id'], table=table)

            # Link to metrics calculated
            for metric in query_metadata['metrics_calculated']:
                session.run("""
                    MATCH (q:Query {id: $query_id})
                    MERGE (m:Metric {name: $metric_name})
                    MERGE (q)-[r:CALCULATES]->(m)
                    SET r.count = coalesce(r.count, 0) + 1,
                        m.usage_count = coalesce(m.usage_count, 0) + 1,
                        m.last_used = datetime()
                """, query_id=query_metadata['query_id'], metric_name=metric)

            # Track join paths
            for join in query_metadata['joins_used']:
                session.run("""
                    MATCH (t1:Table {name: $from_table})
                    MATCH (t2:Table {name: $to_table})
                    MERGE (t1)-[r:JOIN_PATH {
                        via: $join_condition
                    }]->(t2)
                    SET r.usage_count = coalesce(r.usage_count, 0) + 1,
                        r.avg_execution_time_ms = (
                            coalesce(r.avg_execution_time_ms * r.usage_count, 0) + $execution_time_ms
                        ) / (r.usage_count + 1),
                        r.last_used = datetime()
                """,
                    from_table=join['from'],
                    to_table=join['to'],
                    join_condition=join['condition'],
                    execution_time_ms=query_metadata['execution_time_ms']
                )

    def detect_new_patterns(self, query_metadata: dict):
        """
        Detect if this query represents a new pattern that should become
        a metric or canonical dataset
        """

        # Search for similar past queries
        similar_queries = self.agentdb.vector.search(
            query=query_metadata['sql'],
            tags=["successful_query"],
            top_k=50
        )

        # If we've seen this pattern 10+ times but it's not a defined metric
        if len(similar_queries) >= 10:
            metric_name = self.infer_metric_name(query_metadata)

            # Check if metric already exists
            existing_metric = self.check_metric_exists(metric_name)

            if not existing_metric:
                # Propose new metric for human review
                self.propose_new_metric(
                    metric_name=metric_name,
                    query_pattern=query_metadata,
                    similar_queries=similar_queries,
                    usage_count=len(similar_queries)
                )
```

### Nightly Semantic Layer Auto-Update Process

```python
class SemanticLayerAutoUpdater:
    """
    Nightly batch process that analyzes usage patterns and proposes
    updates to the semantic layer
    """

    def run_nightly_update(self):
        """
        Main nightly update process
        """

        print("Starting nightly semantic layer update...")

        # Step 1: Analyze query patterns from last 30 days
        patterns = self.analyze_query_patterns(days=30)

        # Step 2: Identify new metric opportunities
        new_metrics = self.identify_new_metrics(patterns)

        # Step 3: Suggest dimension additions
        new_dimensions = self.suggest_new_dimensions(patterns)

        # Step 4: Flag deprecated metrics
        deprecated = self.flag_deprecated_metrics(days=90)

        # Step 5: Update metric popularity rankings
        self.update_popularity_rankings()

        # Step 6: Generate PR for human review
        pr = self.create_review_pr(
            new_metrics=new_metrics,
            new_dimensions=new_dimensions,
            deprecated=deprecated
        )

        print(f"Nightly update complete. Created PR: {pr.url}")

        return pr

    def identify_new_metrics(self, patterns: list) -> list:
        """
        Identify SQL patterns that should become defined metrics
        """

        new_metric_proposals = []

        # Query knowledge graph for frequently calculated but undefined metrics
        with self.neo4j.session() as session:
            results = session.run("""
                // Find queries that calculate the same thing repeatedly
                MATCH (q:Query)-[:CALCULATES]->(m:Metric)
                WHERE NOT EXISTS(m.definition)  // Not formally defined
                  AND m.usage_count > 10        // Used 10+ times
                  AND m.last_used > datetime() - duration({days: 30})
                WITH m, count(q) AS query_count
                RETURN m.name AS metric_name,
                       m.usage_count AS times_used,
                       collect(q.sql)[0..5] AS sample_queries
                ORDER BY m.usage_count DESC
                LIMIT 20
            """)

            for record in results:
                # Analyze SQL patterns to infer metric definition
                metric_definition = self.infer_metric_definition(
                    metric_name=record['metric_name'],
                    sample_queries=record['sample_queries']
                )

                new_metric_proposals.append({
                    "name": record['metric_name'],
                    "times_used": record['times_used'],
                    "proposed_definition": metric_definition,
                    "confidence": metric_definition['confidence'],
                    "sample_sql": record['sample_queries'][0]
                })

        return new_metric_proposals

    def create_review_pr(
        self,
        new_metrics: list,
        new_dimensions: list,
        deprecated: list
    ) -> object:
        """
        Create GitHub PR with proposed semantic layer changes
        """

        # Generate updated semantic_models.yml
        updated_yaml = self.generate_updated_semantic_yaml(
            new_metrics=new_metrics,
            new_dimensions=new_dimensions
        )

        # Generate PR description
        pr_description = f"""
        ## Automated Semantic Layer Update (Nightly Job)

        Based on usage patterns from the last 30 days, the system proposes
        the following changes to the semantic layer:

        ### New Metrics Proposed ({len(new_metrics)})

        """

        for metric in new_metrics:
            pr_description += f"""
            **{metric['name']}**
            - Used {metric['times_used']} times in last 30 days
            - Confidence: {metric['confidence']:.0%}
            - Proposed definition: `{metric['proposed_definition']['formula']}`
            - [View sample queries](#)

            """

        pr_description += f"""
        ### New Dimensions Suggested ({len(new_dimensions)})

        """

        for dim in new_dimensions:
            pr_description += f"- {dim['metric']}.{dim['dimension']} (used {dim['times']} times)\n"

        pr_description += f"""
        ### Deprecated Metrics Detected ({len(deprecated)})

        The following metrics haven't been used in 90+ days:
        """

        for metric in deprecated:
            pr_description += f"- {metric['name']} (last used: {metric['last_used']})\n"

        # Create PR using gh CLI
        pr = self.github.create_pull_request(
            title="[Auto] Semantic Layer Update - Nightly Job",
            body=pr_description,
            head="semantic-layer-auto-update-{date}",
            base="main",
            files={
                "semantic_models/metrics.yml": updated_yaml
            },
            labels=["automated", "semantic-layer", "needs-review"]
        )

        # Notify data team in Slack
        self.slack.post_message(
            channel="#data-platform",
            text=f"""
            🤖 Nightly semantic layer update complete!

            Proposed changes:
            - {len(new_metrics)} new metrics
            - {len(new_dimensions)} new dimensions
            - {len(deprecated)} deprecated metrics

            Review PR: {pr.url}
            """
        )

        return pr
```

---

## Part 4: Reinforcement Learning Implementation

### RL Training Loop for Query Optimization

#### Architecture: RL Agent for Data Modeling

```python
from agentdb import AgentDB
import numpy as np

class DataModelingRLAgent:
    """
    Reinforcement Learning agent that learns optimal data modeling decisions

    State: Current data modeling task context
    Action: Choose which approach to take (which skill, which join path, etc.)
    Reward: Based on query success, performance, and quality
    """

    def __init__(self):
        self.agentdb = AgentDB(path="./warehouse-memory.db")
        self.algorithm = "ppo"  # Proximal Policy Optimization

        # Initialize RL session
        self.session_id = self.agentdb.learning.start_session(
            algorithm=self.algorithm,
            config={
                "learning_rate": 0.001,
                "discount_factor": 0.95,  # γ (gamma)
                "exploration_rate": 0.1,  # ε (epsilon)
                "batch_size": 32,
                "epochs": 10
            }
        )

    def generate_query_with_rl(self, user_question: str) -> dict:
        """
        Generate query using RL agent that learns from experience
        """

        # Step 1: Define state (context for decision-making)
        state = self.build_state(user_question)

        # Step 2: Agent predicts best action (using learned policy)
        action = self.agentdb.learning.predict(
            session_id=self.session_id,
            state=state,
            epsilon=0.1  # 10% exploration, 90% exploitation
        )

        # Step 3: Execute action (generate and run query)
        result = self.execute_action(action, state)

        # Step 4: Calculate reward
        reward = self.calculate_reward(result)

        # Step 5: Provide feedback to RL system
        next_state = self.build_state_after_execution(result)

        self.agentdb.learning.feedback(
            session_id=self.session_id,
            reward=reward,
            next_state=next_state
        )

        # Step 6: Periodically train (every 32 experiences)
        if self.should_train():
            self.train_agent()

        return result

    def build_state(self, user_question: str) -> dict:
        """
        Build state representation for RL agent

        State includes:
        - User intent (embedded)
        - Available tables (embeddings)
        - Past similar queries (performance)
        - Current time/date (for seasonality)
        - User preferences
        """

        # Semantic embedding of user question
        question_embedding = self.embed(user_question)

        # Find relevant tables
        relevant_tables = self.knowledge_graph.find_relevant_tables(
            user_question
        )
        table_embeddings = [self.embed(t.name) for t in relevant_tables]

        # Get past performance on similar queries
        similar_queries = self.agentdb.vector.search(
            query=user_question,
            tags=["past_query"],
            top_k=10
        )
        avg_past_performance = np.mean([
            q.metadata['execution_time_ms'] for q in similar_queries
        ]) if similar_queries else 5000

        # Build state vector
        state = {
            "question_embedding": question_embedding,  # (768 dims)
            "table_embeddings": table_embeddings,      # (N x 768)
            "num_relevant_tables": len(relevant_tables),
            "avg_past_execution_time": avg_past_performance,
            "hour_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "user_id": self.current_user_id,
            "user_expertise_level": self.get_user_expertise(),  # 0-1
        }

        return state

    def execute_action(self, action: dict, state: dict) -> dict:
        """
        Execute the action chosen by RL agent

        Actions include:
        - Which skill to use (or generate fresh)
        - Which join path to take
        - Which optimizations to apply
        - Which materialization strategy
        """

        action_type = action['action_type']

        if action_type == "use_skill":
            # Use learned skill from library
            skill = self.agentdb.skill.get(action['skill_id'])
            sql = self.apply_skill(skill, state)

        elif action_type == "generate_fresh":
            # Generate fresh SQL (exploration)
            sql = self.generate_sql_with_llm(state)

        elif action_type == "optimize_existing":
            # Take existing query and optimize it
            base_sql = action['base_sql']
            optimizations = action['optimizations']  # e.g., ['add_partition', 'add_index']
            sql = self.apply_optimizations(base_sql, optimizations)

        # Execute query
        execution_result = self.warehouse.execute(sql)

        return {
            "sql": sql,
            "action": action,
            "execution_time_ms": execution_result.time_ms,
            "rows_returned": execution_result.row_count,
            "success": execution_result.success,
            "error": execution_result.error if not execution_result.success else None
        }

    def calculate_reward(self, result: dict) -> float:
        """
        Calculate reward for RL training

        Reward function combines multiple objectives:
        - Query success (did it work?)
        - Performance (how fast?)
        - Quality (correct results?)
        - User satisfaction (did they reuse it?)
        """

        reward = 0.0

        # Base reward for success
        if result['success']:
            reward += 10.0
        else:
            reward -= 5.0
            return reward  # Early return if failed

        # Performance reward (faster is better)
        execution_time = result['execution_time_ms']
        if execution_time < 1000:  # < 1 second
            reward += 5.0
        elif execution_time < 5000:  # < 5 seconds
            reward += 2.0
        elif execution_time > 60000:  # > 1 minute
            reward -= 3.0

        # Result quality reward
        rows_returned = result['rows_returned']
        if 1 <= rows_returned <= 10000:  # Reasonable result set
            reward += 2.0
        elif rows_returned == 0:
            reward -= 1.0  # Probably not what user wanted
        elif rows_returned > 1000000:  # Too many rows
            reward -= 2.0

        # Optimization bonus
        if 'optimization_applied' in result and result['optimization_applied']:
            reward += 3.0

        # Novel pattern discovery bonus
        if result.get('discovered_new_pattern'):
            reward += 5.0

        return reward

    def train_agent(self):
        """
        Train RL agent on collected experiences
        """

        print("Training RL agent...")

        # AgentDB handles training internally using PPO
        training_result = self.agentdb.learning.train(
            session_id=self.session_id,
            batch_size=32,
            epochs=10
        )

        # Log training metrics
        print(f"Training complete:")
        print(f"  - Loss: {training_result.loss}")
        print(f"  - Policy improvement: {training_result.policy_improvement}")
        print(f"  - Value function accuracy: {training_result.value_accuracy}")

        # Store training checkpoint
        self.agentdb.learning.save_checkpoint(
            session_id=self.session_id,
            checkpoint_name=f"checkpoint_{datetime.now().isoformat()}"
        )
```

### RL Action Space Design

```python
class ActionSpace:
    """
    Define all possible actions the RL agent can take
    """

    # Action 1: Skill Selection
    SKILL_ACTIONS = [
        "use_best_matching_skill",      # Use highest similarity skill
        "use_fastest_skill",             # Use skill with best avg performance
        "use_most_recent_skill",         # Use recently created skill
        "generate_fresh_no_skill"        # Don't use any skill (explore)
    ]

    # Action 2: Join Path Selection
    JOIN_PATH_ACTIONS = [
        "use_shortest_path",             # Fewest joins
        "use_fastest_path",              # Best historical performance
        "use_canonical_path",            # Go through canonical datasets
        "use_direct_path"                # Skip intermediate tables
    ]

    # Action 3: Optimization Decisions
    OPTIMIZATION_ACTIONS = [
        "add_partitioning",              # Add partition hint
        "add_clustering",                # Add cluster keys
        "make_incremental",              # Convert to incremental
        "add_caching",                   # Cache results
        "no_optimization"                # Run as-is
    ]

    # Action 4: Materialization Strategy
    MATERIALIZATION_ACTIONS = [
        "table",                         # Materialize as table
        "view",                          # Create view
        "incremental",                   # Incremental table
        "ephemeral"                      # Don't materialize
    ]

    @staticmethod
    def get_action_vector(action_dict: dict) -> np.ndarray:
        """
        Convert action dict to vector for RL training
        """

        action_vector = np.zeros(100)  # 100-dim action space

        # Encode each action dimension
        action_vector[0:4] = one_hot(
            action_dict['skill_action'],
            ActionSpace.SKILL_ACTIONS
        )
        action_vector[4:8] = one_hot(
            action_dict['join_path_action'],
            ActionSpace.JOIN_PATH_ACTIONS
        )
        action_vector[8:13] = one_hot(
            action_dict['optimization_action'],
            ActionSpace.OPTIMIZATION_ACTIONS
        )
        # ... etc

        return action_vector
```

### RL Training Metrics & Monitoring

```python
class RLTrainingMonitor:
    """
    Monitor RL agent training progress
    """

    def track_episode(
        self,
        episode_id: str,
        state: dict,
        action: dict,
        reward: float,
        next_state: dict
    ):
        """
        Track each RL episode for analysis
        """

        # Store in AgentDB for replay
        self.agentdb.experience_record(
            session_id=self.session_id,
            state=state,
            action=action,
            reward=reward,
            next_state=next_state
        )

        # Update metrics
        self.metrics['total_episodes'] += 1
        self.metrics['total_reward'] += reward
        self.metrics['avg_reward'] = (
            self.metrics['total_reward'] / self.metrics['total_episodes']
        )

        # Track reward over time (for learning curve)
        self.reward_history.append({
            "episode": self.metrics['total_episodes'],
            "reward": reward,
            "timestamp": datetime.now()
        })

        # Every 100 episodes, analyze learning progress
        if self.metrics['total_episodes'] % 100 == 0:
            self.analyze_learning_progress()

    def analyze_learning_progress(self):
        """
        Analyze if agent is improving over time
        """

        # Compare recent performance to baseline
        recent_rewards = [
            r['reward'] for r in self.reward_history[-100:]
        ]
        early_rewards = [
            r['reward'] for r in self.reward_history[:100]
        ]

        recent_avg = np.mean(recent_rewards)
        early_avg = np.mean(early_rewards)

        improvement = (recent_avg - early_avg) / abs(early_avg)

        print(f"""
        RL Training Progress (Episode {self.metrics['total_episodes']}):

        Early avg reward (first 100): {early_avg:.2f}
        Recent avg reward (last 100): {recent_avg:.2f}
        Improvement: {improvement:.1%}

        Success rate: {self.calculate_success_rate():.1%}
        Avg execution time: {self.calculate_avg_execution_time():.0f}ms

        Best action discovered: {self.find_best_action()}
        """)

        # Visualize learning curve
        self.plot_learning_curve()

    def plot_learning_curve(self):
        """
        Generate learning curve visualization
        """

        import matplotlib.pyplot as plt

        episodes = [r['episode'] for r in self.reward_history]
        rewards = [r['reward'] for r in self.reward_history]

        # Moving average (window=50)
        moving_avg = np.convolve(
            rewards,
            np.ones(50)/50,
            mode='valid'
        )

        plt.figure(figsize=(12, 6))
        plt.plot(episodes, rewards, alpha=0.3, label='Raw Reward')
        plt.plot(
            episodes[49:],
            moving_avg,
            linewidth=2,
            label='Moving Avg (50 episodes)'
        )
        plt.xlabel('Episode')
        plt.ylabel('Reward')
        plt.title('RL Agent Learning Curve')
        plt.legend()
        plt.grid(True)
        plt.savefig('rl_learning_curve.png')

        print("Learning curve saved to rl_learning_curve.png")
```

---

## Part 5: Complete End-to-End Example

### Scenario: User Wants Attribution Analysis

**User (via Claude Desktop):**
```
"I need to understand which marketing channels are driving the most revenue.
Can you build an attribution model?"
```

### What Happens (Step-by-Step):

#### Step 1: Intent Understanding

```python
# Agent parses intent
intent = {
    "type": "advanced_analytics",
    "analytics_type": "attribution",
    "goal": "understand channel effectiveness",
    "primary_metric": "revenue",
    "business_question": "which channels drive revenue"
}
```

#### Step 2: Check for Canonical Datasets

```python
# Agent searches for canonical datasets
canonical_suggestions = governance.suggest_canonical_dataset(
    "marketing attribution revenue channels"
)

# Returns:
# [
#   "fct_marketing_touchpoints_canonical" (confidence: 0.95),
#   "fct_subscriptions_canonical" (confidence: 0.89),
#   "dim_customers_canonical" (confidence: 0.87)
# ]
```

#### Step 3: Search for Learned Skills

```python
# Check if we've built attribution before
attribution_skills = agentdb.skill.search(
    query="marketing attribution model",
    top_k=3
)

if attribution_skills and attribution_skills[0].similarity > 0.85:
    # We've done this before! Reuse the pattern
    use_existing_skill = True
else:
    # New pattern, generate from scratch
    use_existing_skill = False
```

#### Step 4: RL Agent Decides Approach

```python
# Build state for RL agent
state = {
    "user_question": "marketing attribution",
    "canonical_datasets_available": True,
    "existing_skills_found": len(attribution_skills),
    "complexity": "high",  # Attribution is complex
    "user_expertise": 0.7  # Intermediate user
}

# RL agent predicts best action
action = rl_agent.predict(state)

# Action chosen: "use_canonical_with_modification"
# (Use canonical datasets + apply learned attribution pattern + customize for this user)
```

#### Step 5: Generate dbt Model

```python
# Agent generates dbt model using canonical datasets
dbt_model = advanced_analytics_agent.build_attribution_model(
    canonical_datasets=[
        "fct_marketing_touchpoints_canonical",
        "fct_subscriptions_canonical",
        "dim_customers_canonical"
    ],
    attribution_method="shapley_value",  # Or first-touch, last-touch, linear
    learned_skill=attribution_skills[0] if attribution_skills else None
)

# Generated: models/marts/marketing/mart_marketing_attribution.sql
```

#### Step 6: Generate Semantic Layer Definition

```python
# Automatically add to semantic layer
semantic_layer.add_metric(
    name="attributed_revenue_by_channel",
    definition="Revenue attributed to each marketing channel using Shapley values",
    model="mart_marketing_attribution",
    dimensions=["channel", "campaign", "month"],
    aggregation="sum",
    column="attributed_revenue"
)
```

#### Step 7: Execute and Return Results

```python
# Run dbt model
dbt.run(model="mart_marketing_attribution")

# Query results
results = warehouse.query("""
    SELECT
        channel,
        SUM(attributed_revenue) AS total_attributed_revenue,
        COUNT(DISTINCT customer_id) AS customers_influenced,
        AVG(roi) AS avg_roi
    FROM mart_marketing_attribution
    WHERE month >= '2024-01-01'
    GROUP BY 1
    ORDER BY 2 DESC
""")
```

#### Step 8: Present to User

```
Agent response:

✅ Built marketing attribution model using Shapley value attribution.

📊 Results (Last 12 Months):

Channel Attribution Analysis:
1. Paid Search: $2.4M attributed revenue, ROI: 3.2x
2. Content Marketing: $1.8M attributed revenue, ROI: 5.1x
3. Paid Social: $1.2M attributed revenue, ROI: 2.1x
4. Email: $890K attributed revenue, ROI: 8.7x
5. Direct: $650K attributed revenue, ROI: N/A

💡 Insights:
- Email has highest ROI (8.7x) but lower absolute revenue
- Content marketing delivers strong ROI (5.1x) at scale
- Paid search drives most revenue but lower ROI (3.2x)

📝 What I created for you:
- dbt model: mart_marketing_attribution
- Added metric: "attributed_revenue_by_channel" to semantic layer
- You can now query this anytime with: "Show me attribution by channel"

Would you like me to:
- Break down by campaign
- Add time-based trends
- Create a dashboard
- Export to CSV
```

#### Step 9: Store Episode for Learning

```python
# Store entire interaction for RL training
agentdb.reflexion.store({
    "session_id": session_id,
    "task": "build_marketing_attribution_model",
    "success": True,
    "user_satisfaction": "positive",  # Inferred from follow-up questions
    "execution_time_ms": 3200,
    "approach": "used_canonical_datasets_with_learned_skill",
    "metrics": {
        "model_rows": 12847,
        "query_performance": "excellent",
        "accuracy": "validated_by_user"
    }
})

# Update knowledge graph
knowledge_graph.record_pattern({
    "pattern_type": "attribution_analysis",
    "canonical_datasets_used": [...],
    "success": True,
    "user": user_id
})

# Calculate reward for RL
reward = calculate_reward({
    "success": True,
    "fast_execution": True,
    "user_satisfied": True,
    "reused_canonical_datasets": True
})  # Reward: +22.0

# Train RL agent
rl_agent.provide_feedback(reward=22.0, next_state=...)
```

#### Step 10: Nightly Update

```python
# That night, the nightly learner runs

nightly_learner.analyze_day_usage()

# Discoveries:
# - "attribution_analysis" pattern used 3 times today with 100% success
# - Should consolidate into a reusable skill
# - Canonical datasets (fct_marketing_touchpoints) accessed 47 times

# Actions:
# 1. Create skill: "marketing_attribution_shapley"
# 2. Update metric catalog: mark "attributed_revenue_by_channel" as trending
# 3. Propose to data team: "Consider creating attribution dashboard template"
```

---

## Summary: Complete System

### User Workflow

```
1. User defines metrics (or browses metric catalog)
   ↓
2. Agent analyzes intent + searches for canonical datasets
   ↓
3. RL agent decides optimal approach
   ↓
4. Agent generates everything (dbt model + semantic layer + tests)
   ↓
5. User queries via natural language (Claude Desktop)
   ↓
6. System tracks usage in knowledge graph
   ↓
7. Nightly learner discovers patterns
   ↓
8. Semantic layer auto-updates (with human approval)
   ↓
9. System gets smarter over time
```

### Key Innovations

1. **Metric-First UX:** Users don't write SQL, they define/browse metrics
2. **Canonical Datasets:** Advanced analytics builds on agreed-upon foundation
3. **Knowledge Graph Feedback:** Every query updates the graph in real-time
4. **RL Optimization:** Agent learns optimal decisions from experience
5. **Self-Updating:** Semantic layer proposes updates based on usage

### What Gets Generated Automatically

- ✅ dbt models (staging, intermediate, marts)
- ✅ Semantic layer YAML (metrics, dimensions, relationships)
- ✅ Documentation (auto-generated from definitions)
- ✅ Tests (data quality checks)
- ✅ Knowledge graph nodes (metrics, relationships, usage)
- ✅ Skills (consolidated patterns for reuse)
- ✅ Nightly reports (proposed updates to semantic layer)

### What Humans Do

- ✅ Define high-level metric intent ("I want to track churn")
- ✅ Review/approve agent-generated models
- ✅ Certify canonical datasets
- ✅ Approve semantic layer updates
- ✅ Provide feedback (thumbs up/down on results)
- ✅ Handle edge cases agents can't solve

---

## Next Steps

Create implementation Phase 1 this week:

1. **Day 1-2:** Build metric explorer UI (simple web app)
2. **Day 3-4:** Implement metric definition → dbt generation flow
3. **Day 5:** Set up knowledge graph query tracking
4. **Week 2:** Add AgentDB + basic RL (start with simple reward function)
5. **Week 3:** Test with 3-5 real metrics end-to-end

Would you like me to create detailed implementation code for any specific component?
