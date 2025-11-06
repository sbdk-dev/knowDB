# PRD #2: MCP-Based Conversational Data Modeling Agent

**Version:** 1.0
**Date:** 2025-11-06
**Status:** Research Phase

---

## Executive Summary

Data teams don't want "Cursor for data" (as evidenced by Nao's positioning) — they want something **native to their workflow** that understands data context, runs data quality checks, previews diffs, and maintains governance. Manual SQL modeling is slow not because writing SQL is hard, but because the **iteration cycle** is broken: write → run → test → diff → fix → repeat.

**Vision:** Build a Claude Desktop-native MCP (Model Context Protocol) agent that turns data modeling into a **conversation**, where you describe what you want, the agent generates dbt models with full context awareness, previews diffs, runs tests, and iteratively refines until it's production-ready.

**Inspiration:** Rasmus's MCP server + Nao's instant diff preview + Claude Code's native workflow integration

---

## Problem Statement

### The Real Pain: Broken Iteration Cycles

Data teams don't struggle with SQL syntax. They struggle with:

1. **Context Switching Hell**
   - Write SQL in one tool (IDE)
   - Run dbt in terminal
   - Check diffs in git
   - Run tests in dbt
   - View results in warehouse
   - Check downstream impact in BI tool
   - Repeat 10-20x per model

2. **No Intelligent Assistance**
   - AI code editors (Cursor, Copilot) lack data warehouse context
   - They don't know your existing models, schemas, or business logic
   - Can't run dbt commands or validate SQL
   - No awareness of data quality implications

3. **Manual Quality Assurance**
   - Did my change break downstream models?
   - Did row counts change unexpectedly?
   - Are there new nulls in critical columns?
   - Analytics engineers manually check all of this

4. **Slow Feedback Loops**
   - Wait for dbt run to complete (minutes to hours)
   - Wait for tests to run
   - Wait for BI dashboards to refresh
   - Only then discover issues

### What Data Teams Actually Want

Based on Nao's positioning ("Cursor for data teams") and features:

✅ **Native data connection** → Query warehouse directly
✅ **Instant diff preview** → See impact before committing
✅ **Agent for data quality checks** → Automated validation
✅ **Agent to run tests** → No manual test execution
✅ **Column-level lineage** → Understand dependencies
✅ **BI lineage** → See dashboard impact

**But:** Nao is still an IDE. Users want this native in their AI assistant (Claude Desktop).

### Why MCP Changes Everything

Rasmus demonstrated that exposing semantic layers via MCP enables:
- Natural language queries → Claude translates to semantic layer queries
- No SQL writing required
- Consistent business logic
- Direct integration with Claude Desktop

**Logical Extension:** Why stop at querying? Use MCP to enable conversational DATA MODELING.

---

## Solution Overview

### Core Concept

A **Claude Desktop MCP server** that provides:

1. **Data warehouse context** (schemas, existing models, relationships)
2. **dbt project awareness** (models, tests, dependencies, docs)
3. **Execution capabilities** (run models, tests, diff preview)
4. **Quality validation** (row count checks, null analysis, distribution comparison)
5. **Conversational workflow** (describe intent → agent builds → review → iterate)

**User Experience:**
```
User: "Create a mart model that calculates monthly recurring revenue
       by customer segment, using the subscription events table"

Agent: [Analyzes warehouse schema and existing dbt models]

       I found stg_subscription_events with columns: customer_id,
       event_type, mrr_amount, event_date. I also see you have
       dim_customers with customer_segment.

       I'll create mart_mrr_by_segment that:
       1. Filters to 'subscription_active' events
       2. Joins to dim_customers for segment
       3. Aggregates MRR by month and segment

       [Generates SQL]

       Would you like me to:
       - Preview the results on the last 30 days?
       - Run the full model and show row count diffs?
       - Add data quality tests?

User: "Run the full model and add tests"

Agent: [Executes dbt run for the model]
       [Analyzes results]

       ✅ Model built successfully
       - Previous row count: N/A (new model)
       - New row count: 3,847 rows
       - Time grain: Monthly (24 months of data)

       I've added tests:
       - unique on [month, customer_segment]
       - not_null on mrr_amount
       - relationships to dim_customers

       [Runs tests]

       ✅ All tests passed

       Ready to commit?
```

---

## Technical Architecture

### MCP Server Architecture

Following Rasmus's pattern from his semantic layer MCP server, extended for data modeling:

```python
# mcp_data_modeling_server.py

from boring_mcp import MCPServer, Tool
from dbt_context import DBTProject
from warehouse_context import WarehouseConnection
from diff_analyzer import DiffAnalyzer
from test_runner import TestRunner

class DataModelingMCPServer(MCPServer):
    def __init__(self):
        self.dbt = DBTProject()
        self.warehouse = WarehouseConnection()
        self.diff_analyzer = DiffAnalyzer()
        self.test_runner = TestRunner()

        self.register_tools([
            self.get_warehouse_schema,
            self.get_existing_models,
            self.generate_dbt_model,
            self.preview_model_results,
            self.run_model,
            self.diff_model_results,
            self.generate_tests,
            self.run_tests,
            self.analyze_lineage,
            self.check_data_quality,
        ])

    @tool
    def get_warehouse_schema(self, schema_name: str) -> dict:
        """Get complete schema metadata including tables, columns, types"""
        return self.warehouse.introspect_schema(schema_name)

    @tool
    def get_existing_models(self, pattern: str = None) -> list:
        """Get list of existing dbt models with metadata"""
        return self.dbt.list_models(pattern)

    @tool
    def generate_dbt_model(self, intent: str, model_name: str) -> str:
        """Generate dbt model SQL based on natural language intent"""
        # Use LLM with warehouse + dbt context to generate SQL
        context = {
            "warehouse_schema": self.warehouse.get_relevant_tables(intent),
            "existing_models": self.dbt.get_similar_models(intent),
            "naming_conventions": self.dbt.get_conventions()
        }
        return self.llm_generate_model(intent, model_name, context)

    @tool
    def preview_model_results(self, model_name: str, limit: int = 100) -> pd.DataFrame:
        """Run model with LIMIT clause to preview results"""
        return self.dbt.compile_and_preview(model_name, limit)

    @tool
    def run_model(self, model_name: str) -> dict:
        """Execute dbt run for specific model"""
        result = self.dbt.run_model(model_name)
        return {
            "status": result.status,
            "rows_affected": result.rows_affected,
            "execution_time": result.execution_time,
            "compiled_sql": result.compiled_sql
        }

    @tool
    def diff_model_results(self, model_name: str) -> dict:
        """Compare current vs. new version of model results"""
        return self.diff_analyzer.compare_versions(
            model_name,
            metrics=["row_count", "null_rate", "distinct_values", "distributions"]
        )

    @tool
    def generate_tests(self, model_name: str) -> list:
        """Auto-generate appropriate dbt tests for model"""
        model_metadata = self.dbt.get_model_metadata(model_name)
        return self.test_runner.suggest_tests(model_metadata)

    @tool
    def run_tests(self, model_name: str) -> dict:
        """Execute dbt tests for specific model"""
        return self.test_runner.run_tests(model_name)

    @tool
    def analyze_lineage(self, model_name: str) -> dict:
        """Get upstream and downstream dependencies"""
        return self.dbt.get_lineage(model_name, include_bi=True)

    @tool
    def check_data_quality(self, model_name: str, baseline: str = "prod") -> dict:
        """Compare data quality metrics against baseline"""
        return self.diff_analyzer.quality_check(model_name, baseline)

if __name__ == "__main__":
    server = DataModelingMCPServer()
    server.run()
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "data-modeling-agent": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp_data_modeling_server.py"],
      "env": {
        "DBT_PROJECT_DIR": "/path/to/dbt_project",
        "WAREHOUSE_CONNECTION": "snowflake://account/database/schema",
        "WAREHOUSE_CREDENTIALS": "/path/to/credentials.json"
      }
    }
  }
}
```

### Integration with Existing Tools

```
┌──────────────────────────────────────────────────────────────┐
│                    Claude Desktop (User Interface)            │
└──────────────────────────────────────────────────────────────┘
                            ↕️ MCP Protocol
┌──────────────────────────────────────────────────────────────┐
│              Data Modeling MCP Server (Python)                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Tool 1: Warehouse Context (via Ibis/SQLAlchemy)       │  │
│  │ - Introspect schemas                                  │  │
│  │ - Query metadata                                      │  │
│  │ - Run preview queries                                 │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Tool 2: dbt Project Context                           │  │
│  │ - Parse manifest.json                                 │  │
│  │ - List models, tests, sources                         │  │
│  │ - Understand dependencies                             │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Tool 3: Execution Engine                              │  │
│  │ - Run dbt commands (compile, run, test)              │  │
│  │ - Stream logs to Claude                               │  │
│  │ - Handle errors gracefully                            │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Tool 4: Diff & Quality Engine                         │  │
│  │ - Compare row counts                                  │  │
│  │ - Detect schema changes                               │  │
│  │ - Analyze distributions                               │  │
│  │ - Flag anomalies                                      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↕️
┌──────────────────────────────────────────────────────────────┐
│                     Data Warehouse                            │
│              (Snowflake, BigQuery, DuckDB, etc.)              │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features

### Feature 1: Context-Aware Code Generation

**Problem:** AI code editors don't know your warehouse schema or existing dbt models

**Solution:** MCP server provides full context to Claude

**Example:**
```
User: "Add a revenue metric to the customer mart"

Agent: [Checks existing dim_customers model]
       [Checks warehouse for relevant tables]
       [Finds fct_orders with revenue column]

       I see dim_customers currently has customer_id, name, segment.
       I found revenue data in fct_orders.

       I'll add:
       - total_revenue (lifetime)
       - avg_order_value
       - order_count

       Should I use the existing intermediate model
       int_customer_orders or create a new one?
```

### Feature 2: Instant Diff Preview (à la Nao)

**Problem:** Can't see impact until model runs completely

**Solution:** Smart preview using compilation + sampling

**Implementation:**
```python
def preview_model_diff(model_name: str):
    # Compile new version
    new_sql = dbt.compile(model_name)

    # Run with LIMIT 10000 for speed
    new_sample = warehouse.query(f"{new_sql} LIMIT 10000")

    # Get existing model sample
    old_sample = warehouse.query(f"SELECT * FROM {model_name} LIMIT 10000")

    # Compare
    diff = {
        "schema_changes": compare_schemas(old_sample, new_sample),
        "row_count_estimate": extrapolate_row_count(old_sample, new_sample),
        "null_rate_changes": compare_null_rates(old_sample, new_sample),
        "value_distribution_changes": compare_distributions(old_sample, new_sample)
    }

    return diff
```

**User Experience:**
```
User: "Modify customer mart to exclude test accounts"

Agent: [Generates updated SQL with WHERE clause]
       [Runs instant diff preview]

       Preview (based on 10k sample):
       ⚠️ Row count: 125,847 → ~120,000 (est. -4.6%)
       ✅ Schema: No changes
       ✅ Null rates: No significant changes
       ℹ️ Filtered accounts: ~5,800 rows (matching email like '%@test.com')

       This looks safe. Run full model?
```

### Feature 3: Automated Quality Checks (à la Nao's Agent)

**Problem:** Manually verifying data quality after every change

**Solution:** Agent automatically runs quality checks

**Quality Check Framework:**
```python
class DataQualityChecker:
    def check_model_quality(self, model_name: str, baseline: str = "prod"):
        checks = []

        # Row count validation
        checks.append(self.validate_row_count(model_name, baseline))

        # Null rate validation
        checks.append(self.validate_null_rates(model_name, baseline))

        # Unique key validation
        checks.append(self.validate_uniqueness(model_name))

        # Referential integrity
        checks.append(self.validate_relationships(model_name))

        # Distribution comparison
        checks.append(self.validate_distributions(model_name, baseline))

        # Freshness check
        checks.append(self.validate_freshness(model_name))

        return QualityReport(checks)
```

**User Experience:**
```
Agent: Running quality checks on dim_customers...

       ✅ Row count: 125,234 (within 2% of baseline)
       ✅ Null rates: All required columns < 1% nulls
       ✅ Unique key: customer_id is unique
       ✅ Relationships: All foreign keys valid
       ⚠️ Distribution: customer_segment values shifted:
          - Enterprise: 15% → 18% (+3pp)
          - SMB: 60% → 58% (-2pp)
          Is this expected?

User: "Yes, we onboarded more enterprise customers this month"

Agent: ✅ Quality checks passed. Ready to deploy.
```

### Feature 4: Conversational Iteration

**Problem:** Traditional workflow is linear (write → test → fix → repeat)

**Solution:** Conversational refinement with context retention

**Example Session:**
```
User: "Create a churn analysis mart"

Agent: I'll create mart_customer_churn. What churn definition
       should I use?

       Options I see in your existing models:
       1. No activity in 30 days (used in stg_user_events)
       2. Subscription cancelled (used in stg_subscriptions)
       3. Both?

User: "Use subscription cancelled, but only for paying customers"

Agent: [Generates model]

       I've created the model with:
       - Grain: One row per customer
       - Churn defined as: subscription_status = 'cancelled'
       - Filtered to: customer_type = 'paying'
       - Added churn_date, churn_reason, tenure_months

       [Runs preview]

       Results: 8,456 churned customers, average tenure 14.3 months

       Should I add churn rate calculations by segment?

User: "Yes, and add cohort analysis"

Agent: [Updates model with cohort logic]

       Added:
       - Cohort month (first subscription month)
       - Churn rate by cohort and month
       - Retention curves

       [Runs full model + tests]

       ✅ Model complete with 1.2M rows (cohort-month grain)
       ✅ Tests passed

       Want me to create a semantic layer on top for easy querying?

User: "Yes please"

Agent: [Generates semantic_models.yml]

       Created semantic model with metrics:
       - churn_rate (by segment, cohort, month)
       - retention_rate
       - average_tenure

       You can now query this in Claude with:
       "What's our churn rate by cohort for enterprise customers?"
```

### Feature 5: Column-Level Lineage Integration

**Problem:** Can't see downstream impact of changes

**Solution:** Integrate with dbt lineage + BI tool metadata

**Implementation:**
```python
def get_column_lineage(column_path: str):
    """
    Example: dim_customers.customer_segment
    Returns all downstream usage
    """
    lineage = {
        "dbt_models": dbt.find_column_usage(column_path),
        "bi_dashboards": bi_integration.find_dashboard_usage(column_path),
        "semantic_layer": semantic_layer.find_metric_usage(column_path)
    }
    return lineage

# Example output:
{
    "dbt_models": [
        "mart_revenue_by_segment (GROUP BY)",
        "mart_customer_ltv (JOIN key)",
    ],
    "bi_dashboards": [
        "Looker: Executive Dashboard > Revenue by Segment chart",
        "Tableau: Customer Analytics > Segmentation view"
    ],
    "semantic_layer": [
        "Metric: enterprise_revenue (WHERE filter)",
        "Dimension: customer_segment (dimension)"
    ]
}
```

**User Experience:**
```
User: "I want to rename customer_segment to customer_tier"

Agent: ⚠️ Column-level lineage analysis:

       This column is used in:
       - 12 downstream dbt models
       - 5 Looker dashboards (viewed by 247 users last month)
       - 3 semantic layer metrics

       I can:
       1. Rename and update all references (automated)
       2. Create an alias for backwards compatibility
       3. Show you detailed impact first

       What would you prefer?
```

---

## Workflow Examples

### Workflow 1: Build New Mart Model from Scratch

```
User: Create monthly revenue trend mart

Agent:
[Introspects warehouse]
Found revenue data in:
- fct_orders.order_amount
- fct_subscriptions.mrr_amount

Which should I use?

User: Orders

Agent:
[Generates SQL]
[Shows preview]
Preview for last 3 months:
2024-09: $1.2M
2024-10: $1.4M
2024-11: $1.5M

Looks good?

User: Yes, add year-over-year comparison

Agent:
[Updates SQL with LAG window function]
[Runs full model]
✅ Built: 36 months of data
✅ Added tests
✅ Quality checks passed

Created mart_revenue_trends with:
- month
- revenue
- revenue_yoy
- growth_rate_yoy

User: Add to semantic layer

Agent:
[Generates semantic YAML]
✅ Now queryable via MCP with:
"Show revenue trends YoY"
```

### Workflow 2: Refactor Existing Model

```
User: The customer mart is too slow, optimize it

Agent:
[Analyzes model]
[Checks query profile in warehouse]

Found issues:
1. Full table scan on large fact table (2B rows)
2. Non-incremental (rebuilds everything daily)
3. Multiple CTEs doing similar aggregations

Recommended optimizations:
1. Make incremental (dbt incremental strategy)
2. Add clustering/partitioning hint
3. Consolidate CTEs

Shall I implement these?

User: Yes

Agent:
[Refactors SQL]
[Runs side-by-side comparison]

Performance improvement:
- Old: 47 minutes
- New: 6 minutes (87% faster)
- Row count: Identical (125,234)
- Quality checks: ✅ All passed

Safe to deploy?

User: Yes

Agent:
✅ Deployed to production
✅ Updated documentation
ℹ️ Monitoring next run for validation
```

### Workflow 3: Debug Test Failure

```
User: My customer mart test is failing, help

Agent:
[Checks dbt test results]
[Runs diagnostics]

Test failure: unique_dim_customers_customer_id

Found 47 duplicate customer_ids:
- All created in last 24 hours
- All have source = 'shopify_import_2024_11_06'

This looks like a double-import issue.

Should I:
1. Show you the duplicates
2. Add deduplication logic
3. Investigate the source

User: Add deduplication logic

Agent:
[Updates model with ROW_NUMBER dedup]
[Re-runs test]

✅ Test now passes
✅ Row count: 125,234 → 125,187 (-47 duplicates removed)

Added logic:
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY created_at DESC
) = 1

Want me to add monitoring to catch future duplicates?
```

---

## Success Metrics

### Developer Experience
- **Model development time:** 2 hours → 20 minutes (83% reduction)
- **Context switches:** 15 per model → 0 (all in Claude)
- **Test coverage:** 40% → 90% (auto-generated tests)
- **Broken production deployments:** 5 per month → <1

### Data Quality
- **Pre-deployment quality checks:** 0% → 100%
- **Unexpected row count changes caught:** 70% → 95%
- **Downstream breakages:** 10 per quarter → 2 per quarter

### Business Impact
- **Time to insight:** 2 weeks → 2 days
- **Data team satisfaction:** Survey score improvement
- **Stakeholder trust:** Measured via metric consistency

---

## Technical Challenges & Solutions

### Challenge 1: MCP Server Performance
**Problem:** Running dbt commands is slow (minutes)

**Solutions:**
- Use `dbt compile` + warehouse `CREATE VIEW` for fast previews
- Cache compiled SQL
- Run async with progress streaming
- Implement smart sampling for diffs

### Challenge 2: Warehouse Credentials Security
**Problem:** MCP server needs warehouse access without exposing credentials

**Solutions:**
- Use environment variables (not in Claude config)
- Support OAuth/SSO flows
- Implement least-privilege access (read-only for preview, write for specific schema)
- Audit log all queries

### Challenge 3: Managing Long Conversations
**Problem:** Claude context window limits for complex modeling

**Solutions:**
- MCP server maintains conversation state
- Summarize previous steps
- Allow "checkpointing" (save conversation state, resume later)
- Implement "explain current model" tool

### Challenge 4: Handling Errors Gracefully
**Problem:** dbt/SQL errors can be cryptic

**Solutions:**
- Agent parses errors and explains in plain English
- Suggests fixes based on error type
- Offers to rollback if needed
- Provides relevant docs links

---

## Competitive Differentiation

| Feature | Cursor/Copilot | Nao | MCP Data Agent (This PRD) |
|---------|---------------|-----|---------------------------|
| **Data warehouse context** | ❌ | ✅ | ✅ |
| **dbt project awareness** | ❌ | ✅ | ✅ |
| **Run dbt commands** | ❌ | ✅ | ✅ |
| **Instant diff preview** | ❌ | ✅ | ✅ |
| **Auto quality checks** | ❌ | ✅ | ✅ |
| **Column lineage** | ❌ | ✅ | ✅ |
| **Conversational workflow** | ⚠️ (limited) | ⚠️ (IDE-based) | ✅ (Native in Claude) |
| **Semantic layer integration** | ❌ | ❌ | ✅ |
| **No IDE switching** | ❌ (is an IDE) | ❌ (is an IDE) | ✅ (Claude Desktop) |
| **MCP protocol** | ❌ | ❌ | ✅ |

**Key Differentiator:** Native Claude Desktop integration via MCP = conversational data modeling without IDE switching.

---

## Implementation Roadmap

### Phase 1: MCP Server MVP (Weeks 1-4)
**Goal:** Basic conversational dbt model generation

**Deliverables:**
- MCP server with 5 core tools:
  - get_warehouse_schema
  - get_existing_models
  - generate_dbt_model
  - run_model
  - run_tests
- Support DuckDB locally (like sbdk-dev)
- Claude Desktop integration
- Demo: "Create a customer mart" end-to-end

**Success:** 3 beta users successfully build 1 model each

### Phase 2: Diff & Quality Features (Weeks 5-8)
**Goal:** Add Nao-inspired features

**Deliverables:**
- Instant diff preview
- Automated quality checks
- Row count comparison
- Schema change detection
- Distribution analysis

**Success:** Catch 5+ quality issues before production

### Phase 3: Advanced Context & Lineage (Weeks 9-12)
**Goal:** Full context awareness

**Deliverables:**
- Column-level lineage
- BI tool integration (Looker, Tableau metadata)
- Semantic layer auto-generation
- Multi-warehouse support (Snowflake, BigQuery)

**Success:** 20 teams onboarded, 80% reduction in modeling time

### Phase 4: Production Hardening (Weeks 13-16)
**Goal:** Enterprise-ready

**Deliverables:**
- Security hardening (OAuth, audit logs)
- Error handling improvements
- Performance optimization
- Documentation and tutorials
- Open source release

**Success:** 100 teams using in production

---

## Go-to-Market Strategy

### Target Users
1. **Primary:** Analytics engineers at mid-market companies (50-500 employees)
2. **Secondary:** Data analysts learning dbt
3. **Tertiary:** Data scientists building pipelines

### Distribution
1. **Open source MCP server** (build community)
2. **Claude Desktop marketplace** (when available)
3. **dbt Community** (Slack, Discourse, conferences)
4. **Content marketing** (tutorials, demos, case studies)

### Pricing Strategy
- **Free tier:** Open source MCP server, local use (DuckDB)
- **Pro tier:** $50/user/month - Cloud warehouses, BI lineage, priority support
- **Enterprise tier:** Custom pricing - SSO, audit logs, SLAs

---

## Open Questions

1. **Should the MCP server run locally or as a cloud service?**
   - Local: More secure, no latency, works offline
   - Cloud: Easier setup, centralized state, team collaboration

2. **How to handle team collaboration?**
   - Multiple users working on same dbt project
   - Sharing conversation context
   - Code review workflows

3. **What's the right balance of automation vs. control?**
   - Auto-commit changes or require approval?
   - Auto-deploy to production or manual promotion?

4. **How to monetize without limiting functionality?**
   - Open core model?
   - SaaS only for cloud features?
   - Professional services?

---

## Conclusion

Data teams don't want another IDE (even an AI-powered one). They want their existing AI assistant (Claude) to **understand their data context** and **handle the tedious parts of data modeling** while maintaining quality and governance.

By combining:
- **MCP protocol** (Rasmus's approach to semantic layer querying)
- **Data warehouse context** (warehouse introspection + dbt awareness)
- **Quality-first features** (Nao's diff preview + quality checks)
- **Conversational workflow** (Claude Desktop native)

We can fix the broken iteration cycle and make data modeling feel like a conversation instead of a chore.

**Next Step:** Build Phase 1 MVP with DuckDB + dbt + Claude Desktop integration.

---

## References

1. Rasmus Engelbrecht - [MCP-Powered AI Analyst (Part 2)](https://rasmusengelbrecht.substack.com/p/practical-guide-to-semantic-layers-34d)
2. Rasmus Engelbrecht - [Practical Semantic Layers (Part 1)](https://rasmusengelbrecht.substack.com/p/practical-guide-to-semantic-layers)
3. [Nao - Cursor for Data Teams](https://getnao.io/)
4. [Model Context Protocol (MCP) Documentation](https://modelcontextprotocol.io/)
5. [dbt Documentation](https://docs.getdbt.com/)
6. [Boring Semantic Layer](https://github.com/boring-software/boring-semantic-layer)
7. [Ibis Project](https://ibis-project.org/)

---

**Document Status:** Draft for review
**Author:** AI Research Team
**Last Updated:** 2025-11-06
