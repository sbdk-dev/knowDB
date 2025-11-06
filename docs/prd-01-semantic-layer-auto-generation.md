# PRD #1: AI-Native Semantic Layer Auto-Generation Platform

**Version:** 1.0
**Date:** 2025-11-06
**Status:** Research Phase

---

## Executive Summary

The modern data stack forces analytics engineers to manually write hundreds of SQL models (staging, intermediate, marts) and separately define semantic layer configurations (metrics, dimensions, relationships). This duplicates work, creates inconsistencies, and slows time-to-insight.

**Vision:** Build an AI-native platform that automatically generates both dbt models AND semantic layer definitions by introspecting warehouse metadata, inferring business context, and learning from usage patterns. The system eliminates 70-90% of manual SQL modeling work while maintaining governance and quality.

**Inspiration:** MindsDB's auto-generation + Droughty's metadata introspection + WrenAI's MDL semantic encoding

---

## Problem Statement

### Current Pain Points

1. **Duplicate Definition Hell**
   - Metric definitions scattered across dbt models, BI tools, semantic layers
   - Same calculation (e.g., "churn_rate") defined 5+ different ways across teams
   - No single source of truth → data trust issues

2. **Manual SQL Grind**
   - Analytics engineers spend 60-80% of time writing boilerplate staging models
   - Repetitive tasks: renaming columns, casting types, adding surrogate keys
   - Each new source requires 10-50 models to be production-ready

3. **Slow Semantic Layer Adoption**
   - Semantic layers (dbt Semantic Layer, Cube, Boring Semantic Layer) require extensive YAML configuration
   - Manually defining every metric, dimension, and relationship is tedious
   - Teams skip semantic layer setup → inconsistent metrics persist

4. **Lost Context**
   - Warehouse metadata contains valuable information (foreign keys, column descriptions, data types)
   - Current tools ignore this context → analysts rebuild it manually
   - Business logic lives in tribal knowledge, not code

### Evidence from Research

- **Droughty** shows that warehouse metadata CAN be automatically extracted and converted to semantic files (LookML, dbt, Cube, DBML)
- **MindsDB** demonstrates that knowledge bases can auto-chunk and semantically index data with SQL interface
- **WrenAI's MDL** proves that encoding schema + metrics + joins prevents LLM hallucinations
- **Rasmus's Boring Semantic Layer** shows that Ibis-based semantic models work across warehouses with consistent interface

**Key Insight:** The warehouse already contains 70% of what we need to build semantic models. We just need AI to extract, infer, and codify it.

---

## Solution Overview

### Core Concept

An **AI-native platform** that:

1. **Introspects** warehouse metadata (tables, columns, types, keys, constraints, descriptions)
2. **Infers** business context using LLMs (entity relationships, metric definitions, dimensional hierarchies)
3. **Generates** both dbt models AND semantic layer YAML automatically
4. **Learns** from user feedback, query patterns, and business outcomes
5. **Maintains** version-controlled, governed definitions as single source of truth

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Warehouse Metadata Intelligence Engine           │
│  - Introspect schema (via Droughty-like approach)          │
│  - Extract foreign keys, constraints, descriptions          │
│  - Detect patterns (SCD Type 2, event tables, dimension tables) │
│  - Map lineage from source to warehouse                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: AI Semantic Inference Engine                     │
│  - LLM analyzes metadata + sample data                     │
│  - Infers business entities (customers, products, orders)   │
│  - Suggests metric definitions (revenue, churn, LTV)        │
│  - Proposes dimensional relationships (star schema)         │
│  - Generates business-friendly names & descriptions         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Code Generation & Governance Engine              │
│  - Auto-generate dbt staging models (type casting, renaming) │
│  - Auto-generate dbt intermediate models (joins, business logic) │
│  - Auto-generate dbt mart models (fact/dimension tables)    │
│  - Auto-generate semantic layer YAML (Boring Semantic Layer) │
│  - Version control all outputs with git integration         │
│  - Enable human-in-the-loop review & approval               │
└─────────────────────────────────────────────────────────────┘
```

### Key Differentiators

| Feature | Traditional Approach | AI Auto-Generation Platform |
|---------|---------------------|----------------------------|
| Time to first metric | 2-4 weeks | 2-4 hours |
| Manual SQL writing | 100% | 10-30% (review only) |
| Semantic layer setup | Optional, manual | Automatic, enforced |
| Metric consistency | Fragmented across tools | Single source of truth |
| Learning from usage | None | Continuous improvement |

---

## Technical Architecture

### Component 1: Metadata Introspection Engine

**Technologies:**
- Extend **Droughty** approach to read warehouse metadata
- Support all major warehouses (Snowflake, BigQuery, Redshift, Databricks, DuckDB)
- Extract:
  - Table/column definitions
  - Primary/foreign key relationships
  - Column descriptions (if available)
  - Data types and constraints
  - Table statistics (row counts, data distribution)
  - Query history (for usage patterns)

**Output:** Normalized metadata graph representing warehouse structure

### Component 2: AI Semantic Inference Engine

**Technologies:**
- **LLM Models:** Claude 3.5 Sonnet, GPT-4, or Gemini Pro
- **Inference Pipeline:**
  1. Analyze metadata + sample rows to understand data domain
  2. Detect entity types (dimension vs. fact tables)
  3. Infer relationships (1:1, 1:many, many:many)
  4. Suggest metric formulas based on column names/types
  5. Generate business-friendly names using context

**Example Inference:**

```yaml
# Input: Raw table `fct_order_items`
# Columns: order_item_id, order_id, product_id, quantity, unit_price, created_at

# AI Inference Output:
entity_type: fact_table
business_name: "Order Items"
grain: "One row per line item in an order"
relationships:
  - joins_to: dim_orders
    on: order_id
    type: many_to_one
  - joins_to: dim_products
    on: product_id
    type: many_to_one
metrics:
  - name: total_revenue
    formula: "SUM(quantity * unit_price)"
    description: "Total revenue from order items"
  - name: average_order_value
    formula: "SUM(quantity * unit_price) / COUNT(DISTINCT order_id)"
    description: "Average revenue per order"
dimensions:
  - name: order_date
    column: created_at
    time_grain: [day, week, month, quarter, year]
```

### Component 3: Code Generation Engine

**Generates:**

1. **dbt Staging Models** (CTE pattern, type casting, renaming)
2. **dbt Intermediate Models** (joins, business logic)
3. **dbt Mart Models** (dimensional models)
4. **Semantic Layer YAML** (Boring Semantic Layer format using Ibis)
5. **dbt Tests** (not null, unique, relationships)
6. **Documentation** (model descriptions, column docs)

**Example Generated dbt Model:**

```sql
-- models/staging/stg_orders.sql
-- Auto-generated by Semantic Layer AI Platform
-- Generated: 2025-11-06 10:30:00 UTC

WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'raw_orders') }}
),

renamed AS (
    SELECT
        -- IDs
        order_id::VARCHAR AS order_id,
        customer_id::VARCHAR AS customer_id,

        -- Timestamps
        created_at::TIMESTAMP AS order_created_at,

        -- Metrics
        total_amount::DECIMAL(10,2) AS order_total_amount,

        -- Metadata
        _loaded_at::TIMESTAMP AS _loaded_at

    FROM source
)

SELECT * FROM renamed
```

**Example Generated Semantic Layer YAML:**

```yaml
# semantic_models.yml
# Auto-generated by Semantic Layer AI Platform

semantic_model:
  name: ecommerce_orders
  connection:
    type: duckdb
    database: data.duckdb

  tables:
    - name: mart_orders
      description: "Order-level fact table with customer and product dimensions"

  dimensions:
    - name: order_date
      type: time
      column: order_created_at
      time_grains: [day, week, month, quarter, year]

    - name: customer_id
      type: categorical
      column: customer_id

  measures:
    - name: total_revenue
      description: "Sum of all order amounts"
      aggregation: sum
      column: order_total_amount

    - name: order_count
      description: "Count of distinct orders"
      aggregation: count_distinct
      column: order_id

    - name: average_order_value
      description: "Average revenue per order"
      aggregation: average
      column: order_total_amount
```

### Component 4: Learning & Feedback Loop

**Continuous Improvement:**
- Track which generated models are accepted/modified by users
- Monitor query patterns via warehouse query logs
- Learn from user edits to improve future generations
- A/B test different metric definitions
- Suggest optimizations based on actual usage

**Feedback Mechanism:**
```python
# User provides feedback on generated metric
platform.review_metric(
    metric_name="churn_rate",
    action="approve",  # or "edit", "reject"
    user_notes="Changed denominator to active users, not total users"
)

# Platform learns and adjusts future similar metrics
```

---

## User Experience

### Workflow: From Zero to Semantic Layer in 2 Hours

**Step 1: Connect Warehouse (5 minutes)**
```bash
# CLI or UI-based connection
semauto connect --warehouse snowflake \
  --account mycompany \
  --warehouse ANALYTICS_WH \
  --database PROD_DB
```

**Step 2: Auto-Discover & Infer (30 minutes)**
```bash
# Platform analyzes metadata + samples data
semauto discover --schemas ecommerce,marketing

# AI generates proposed semantic model
# Output:
# - 45 staging models
# - 12 intermediate models
# - 8 mart models
# - 1 semantic layer YAML with 25 metrics
```

**Step 3: Human Review & Approval (60 minutes)**
- Web UI shows generated models side-by-side with metadata
- User reviews, edits, approves/rejects each model
- Platform learns from edits

**Step 4: Deploy & Iterate (15 minutes)**
```bash
# Platform commits to git, runs dbt, deploys semantic layer
semauto deploy --environment production

# Start querying via MCP server (à la Rasmus's approach)
```

**Step 5: Continuous Learning (ongoing)**
- Platform monitors query patterns
- Suggests new metrics based on usage
- Alerts when metrics drift or break

---

## Integration Points

### Works With Existing Tools

1. **dbt Integration**
   - Generates dbt-compatible SQL models
   - Creates dbt_project.yml, sources.yml, schema.yml
   - Integrates with dbt Cloud or dbt Core

2. **Semantic Layer Support**
   - **Primary:** Boring Semantic Layer (Ibis-based)
   - **Export to:** dbt Semantic Layer, Cube, LookML, DBML

3. **MCP Server Integration**
   - Auto-generate MCP server for Claude Desktop (following Rasmus's pattern)
   - Expose metrics via Model Context Protocol
   - Enable natural language querying

4. **BI Tool Connections**
   - Pre-configure connections to Looker, Tableau, Power BI, Metabase
   - Push semantic definitions to BI tools

5. **Version Control**
   - Git-based workflow
   - PR reviews for generated code
   - Rollback capability

---

## Success Metrics

### Developer Productivity
- **Time to first metric:** 2-4 weeks → 2-4 hours (95% reduction)
- **Manual SQL written:** 100% → 10-30% (70-90% automation)
- **Semantic layer adoption:** 20% of teams → 90% of teams

### Data Quality
- **Metric consistency:** Track # of conflicting definitions (goal: 0)
- **Test coverage:** Auto-generate 80%+ test coverage
- **Documentation coverage:** 100% (all models auto-documented)

### Business Impact
- **Faster insights:** Business users get answers in hours, not weeks
- **Reduced analytics team size needed:** Same output with 50% fewer engineers
- **Increased trust in data:** Single source of truth for all metrics

---

## Technical Challenges & Mitigations

### Challenge 1: LLM Hallucination
**Risk:** AI suggests incorrect metric formulas

**Mitigation:**
- Constraint-based generation (only suggest valid SQL operations)
- Validation against sample data (test formula on subset)
- Human-in-the-loop approval required
- Learn from corrections

### Challenge 2: Complex Business Logic
**Risk:** Some domains require deep business context AI can't infer

**Mitigation:**
- Start with 80/20 rule (automate simple cases, manual for complex)
- Allow custom business logic injection
- Build domain-specific templates (e-commerce, SaaS, finance)
- Enable users to provide context via prompts

### Challenge 3: Performance
**Risk:** Generating 100+ models for large warehouses is slow

**Mitigation:**
- Incremental generation (only new/changed tables)
- Parallel processing with batching
- Cache inference results
- Allow selective generation (choose schemas/tables)

### Challenge 4: Data Warehouse Diversity
**Risk:** Each warehouse has different metadata schemas

**Mitigation:**
- Use **Ibis** as abstraction layer (proven by Boring Semantic Layer)
- Adapter pattern for each warehouse type
- Normalize metadata to common schema internally

---

## Phased Rollout Plan

### Phase 1: MVP (Months 1-3)
**Scope:** Auto-generate dbt staging models + basic semantic layer YAML

**Deliverables:**
- Support 1 warehouse (DuckDB for simplicity, like sbdk-dev)
- Introspect metadata using information_schema
- LLM generates staging models only
- Generate Boring Semantic Layer YAML with 5-10 metrics
- CLI-based workflow

**Success:** 10 beta users adopt, save 50% time on staging layer

### Phase 2: Production-Ready (Months 4-6)
**Scope:** Add intermediate/mart generation, multi-warehouse support, UI

**Deliverables:**
- Support Snowflake, BigQuery, Postgres
- Generate full dbt project (staging → intermediate → marts)
- Web UI for review/approval workflow
- Git integration for version control
- MCP server auto-generation

**Success:** 100 teams onboarded, 70% automation rate

### Phase 3: Learning & Optimization (Months 7-12)
**Scope:** Feedback loops, continuous learning, advanced features

**Deliverables:**
- Query pattern analysis
- Automatic metric suggestions
- Performance optimization recommendations
- Multi-tool semantic layer export (Cube, dbt SL, LookML)
- Enterprise features (RBAC, audit logs)

**Success:** 1000+ teams, 90% automation, measurable business impact

---

## Competitive Landscape

| Solution | Approach | Automation Level | Limitation |
|----------|----------|------------------|------------|
| **dbt** | Manual SQL + YAML | 0% (all manual) | No auto-generation |
| **Droughty** | Metadata → semantic files | 30% (templates only) | No business logic inference |
| **MindsDB** | AutoML + Knowledge Bases | 50% (ML-focused) | Not analytics-engineering focused |
| **WrenAI** | Text-to-SQL via semantic layer | 0% (semantic layer still manual) | Requires pre-built MDL |
| **Nao** | Cursor for data (AI code editor) | 40% (assisted, not automated) | Still requires SQL writing |
| **Our Solution** | Full auto-generation | 70-90% | Novel approach, unproven |

**Market Gap:** No existing solution fully automates BOTH dbt model generation AND semantic layer setup using AI + warehouse metadata.

---

## Open Questions & Next Steps

### Research Questions
1. Which LLM works best for semantic inference? (Test Claude 3.5, GPT-4, Gemini)
2. How to handle custom business logic that AI can't infer?
3. What's the optimal human-in-the-loop workflow?
4. Can we auto-detect dimensional modeling patterns (Kimball)?

### Technical Validation Needed
1. Build prototype with DuckDB + Boring Semantic Layer
2. Test on 3-5 real-world warehouses to measure accuracy
3. User test with 10 analytics engineers for feedback
4. Benchmark time savings vs. manual approach

### Go-to-Market Strategy
1. Open source core engine (build community like dbt)
2. Commercial features: multi-user, enterprise security, advanced learning
3. Target: Mid-market companies with 5-20 person data teams
4. Distribution: dbt Community, Data Engineering Slack groups, conferences

---

## Conclusion

The modern data stack's manual SQL modeling bottleneck is solvable with AI. By combining:

- **Warehouse metadata introspection** (Droughty approach)
- **AI semantic inference** (LLM-powered business context)
- **Automated code generation** (dbt models + semantic layer YAML)
- **Continuous learning** (feedback loops)

We can eliminate 70-90% of manual work while IMPROVING consistency, governance, and trust.

**Next Step:** Build MVP prototype using DuckDB + Boring Semantic Layer + Claude API to validate core hypothesis.

---

## References

1. Rasmus Engelbrecht - [Practical Guide to Semantic Layers](https://rasmusengelbrecht.substack.com/p/practical-guide-to-semantic-layers)
2. Rasmus Engelbrecht - [MCP-Powered AI Analyst (Part 2)](https://rasmusengelbrecht.substack.com/p/practical-guide-to-semantic-layers-34d)
3. Rasmus Engelbrecht - [Local Data Stack (DuckDB, dlt, dbt)](https://rasmusengelbrecht.substack.com/p/my-local-data-stack-duckdb-dlt-dbt)
4. [WrenAI - GenBI Platform](https://github.com/Canner/WrenAI)
5. [MindsDB - AI Layer for Databases](https://mindsdb.com/)
6. [Droughty - Warehouse Metadata Reader](https://github.com/rittmananalytics/droughty)
7. [sbdk-dev - Local-First Data Pipeline](https://github.com/sbdk-dev/sbdk-dev)
8. [Boring Semantic Layer](https://github.com/boring-software/boring-semantic-layer)

---

**Document Status:** Draft for review
**Author:** AI Research Team
**Last Updated:** 2025-11-06
