# knowDB Visualization Strategy

## Research Summary

### WrenAI Approach
- **AI-powered chart selection**: Automatically chooses best visualization type
- **One-click pinning**: Charts saved to dashboards instantly
- **Conversational refinement**: Users can iterate on charts with follow-up questions
- **Architecture**: 4-layer system (Data → Semantic → Agentic → Representation)

### Evidence.dev Approach (Rasmus Engelbrecht)
- **Code-based dashboards**: Markdown + SQL = Interactive dashboards
- **Direct DuckDB integration**: Queries analytical database directly
- **Local-first**: No cloud infrastructure needed
- **Single command deployment**: `./run.sh` runs entire pipeline

---

## Recommendation: Hybrid Approach

Combine the best of both worlds for knowDB:

### Phase 1: AI Chart Recommendations (2-3 days)
**Add to existing AI analyst** - Enhance `ResultInterpreterAgent` to suggest chart types

```python
class ChartRecommendationEngine:
    """Suggests optimal chart types based on query intent and data shape"""

    def recommend_chart(self, understanding: QueryUnderstanding,
                       result: pd.DataFrame) -> ChartRecommendation:

        # Pattern matching rules
        if understanding.intent == QueryIntent.TREND_ANALYSIS:
            return ChartRecommendation(
                type="line",
                x_axis=self._get_temporal_dimension(result),
                y_axis=self._get_metrics(result),
                title=f"{metric} over time"
            )

        elif understanding.intent == QueryIntent.COMPARISON:
            return ChartRecommendation(
                type="bar",
                x_axis=self._get_categorical_dimension(result),
                y_axis=self._get_metrics(result),
                title=f"{metric} by {dimension}"
            )

        # ... more patterns
```

**Output format**:
```markdown
## 📊 Suggested Visualization

**Chart Type**: Line Chart
**Best For**: Showing trend over time
**X-Axis**: snapshot_month
**Y-Axis**: monthly_mrr

**Plotly Code**:
```python
import plotly.express as px
df = # ... your data from knowDB
fig = px.line(df, x='snapshot_month', y='monthly_mrr')
fig.show()
```

**Evidence.dev Code**:
```sql
SELECT snapshot_month, monthly_mrr
FROM monthly_mrr_snapshots
ORDER BY snapshot_month
```
```
```

### Phase 2: Evidence.dev Integration (1 week)
**Add local dashboard layer**

#### Setup
```bash
# Install Evidence
npm install -g @evidence-dev/cli

# Initialize in knowDB project
cd /Users/mattstrautmann/Documents/github/knowDB
mkdir dashboards
cd dashboards
evidence init

# Configure DuckDB connection
# dashboards/sources/knowdb.yaml
name: knowdb
type: duckdb
filename: ../data/sample.duckdb
```

#### Dashboard Structure
```
dashboards/
├── pages/
│   ├── index.md              # Executive summary
│   ├── revenue-trends.md     # MRR/ARR trends
│   ├── customer-cohorts.md   # Cohort analysis
│   └── segment-analysis.md   # By segment breakdown
└── sources/
    └── knowdb.yaml           # DuckDB connection
```

#### Example Dashboard (dashboards/pages/revenue-trends.md)
```markdown
---
title: Revenue Trends
---

# Monthly Recurring Revenue Trends

## Overview

```sql mrr_by_month
SELECT
    snapshot_month,
    SUM(mrr) as total_mrr,
    SUM(customer_count) as customers
FROM monthly_mrr_snapshots
GROUP BY snapshot_month
ORDER BY snapshot_month
```

<LineChart
    data={mrr_by_month}
    x=snapshot_month
    y=total_mrr
    title="MRR Growth"
/>

## By Customer Segment

```sql mrr_by_segment
SELECT
    snapshot_month,
    customer_segment,
    SUM(mrr) as segment_mrr
FROM monthly_mrr_snapshots
GROUP BY snapshot_month, customer_segment
ORDER BY snapshot_month
```

<LineChart
    data={mrr_by_segment}
    x=snapshot_month
    y=segment_mrr
    series=customer_segment
    title="MRR by Segment"
/>

## Key Metrics

<BigValue
    data={mrr_by_month}
    value=total_mrr
    fmt='$#,##0'
/>
```

#### Run Evidence
```bash
cd dashboards
evidence dev  # Opens on localhost:3000
```

### Phase 3: Claude Desktop Integration (2-3 days)
**Add MCP tool for dashboard management**

```python
# In src/mcp_server.py

@app.call_tool()
async def call_tool(name: str, arguments: Any):
    # ... existing tools

    elif name == "generate_dashboard":
        """Create Evidence.dev dashboard from AI analyst results"""
        query_results = arguments["query_results"]
        dashboard_name = arguments["dashboard_name"]

        # Generate Evidence markdown
        markdown = generate_evidence_dashboard(
            query_results=query_results,
            name=dashboard_name
        )

        # Write to dashboards/pages/
        dashboard_path = f"dashboards/pages/{dashboard_name}.md"
        with open(dashboard_path, 'w') as f:
            f.write(markdown)

        return {
            "status": "success",
            "path": dashboard_path,
            "url": f"http://localhost:3000/{dashboard_name}"
        }

    elif name == "list_dashboards":
        """List all Evidence dashboards"""
        dashboards = []
        for file in Path("dashboards/pages").glob("*.md"):
            dashboards.append({
                "name": file.stem,
                "url": f"http://localhost:3000/{file.stem}"
            })
        return dashboards
```

---

## User Experience Flow

### Before (Current State)
```
User: "Show me MRR trends"
AI: [Returns table with data]
User: "How do I visualize this?"
AI: ¯\_(ツ)_/¯
```

### After (Phase 1 - Chart Recommendations)
```
User: "Show me MRR trends"
AI: [Returns data + chart recommendation]

📊 Suggested Visualization: Line Chart
Here's the code to visualize this:

[Plotly/matplotlib code snippet]
```

### After (Phase 2 - Evidence Integration)
```
User: "Show me MRR trends"
AI: [Returns data + chart recommendation]

✨ I've created a dashboard for you:
http://localhost:3000/mrr-trends

You can also run: open http://localhost:3000/mrr-trends
```

### After (Phase 3 - Full Integration)
```
User: "Show me MRR trends and save to dashboard"
AI: [Generates dashboard automatically]

✅ Dashboard created: Revenue Trends
🌐 URL: http://localhost:3000/revenue-trends

The dashboard includes:
- MRR growth line chart
- Segment breakdown
- Key metrics summary
- Refresh automatically with new data
```

---

## Implementation Priority

### High Priority (Do First)
1. ✅ **Chart recommendations in AI responses** (Phase 1)
   - Low effort, high value
   - Works immediately in Claude Desktop
   - Educates users on best practices

### Medium Priority (Do Next)
2. ✅ **Evidence.dev setup** (Phase 2)
   - Local dashboard capability
   - No cloud costs
   - Production-ready

### Low Priority (Nice to Have)
3. ⏸️ **Full dashboard automation** (Phase 3)
   - Requires more engineering
   - Can be manual initially

---

## Technical Decisions

### Why Evidence.dev over Alternatives?

| Tool | Pros | Cons | Fit |
|------|------|------|-----|
| **Evidence.dev** | Local-first, code-based, DuckDB native | Limited chart types | ⭐⭐⭐⭐⭐ Perfect |
| **Streamlit** | Python native, fast prototyping | Not designed for BI | ⭐⭐⭐⭐ Good |
| **Metabase** | Full-featured BI tool | Heavy setup, UI-focused | ⭐⭐⭐ OK |
| **Superset** | Enterprise-grade | Complex deployment | ⭐⭐ Overkill |
| **Custom React** | Full control | High maintenance | ⭐ Too much work |

### Why Not Build Custom Visualization in MCP?
- Claude Desktop doesn't support rendering charts directly
- Users would still need external tool to view
- Evidence.dev solves this better

---

## Next Steps

1. **Week 1**: Implement chart recommendations (Phase 1)
   - Add `ChartRecommendationEngine` to `ai_agent_flow.py`
   - Update response formatting to include chart suggestions
   - Test with various query types

2. **Week 2**: Setup Evidence.dev (Phase 2)
   - Install and configure Evidence
   - Create 3-5 starter dashboards
   - Document setup process

3. **Week 3**: Add dashboard tools (Phase 3)
   - Add `generate_dashboard` MCP tool
   - Add `list_dashboards` MCP tool
   - Update user documentation

---

## Success Metrics

**Phase 1**:
- ✅ Every AI analyst response includes chart recommendation
- ✅ Users can copy-paste code and get working charts

**Phase 2**:
- ✅ Evidence dashboards running locally
- ✅ Auto-refresh with new data
- ✅ Non-technical users can view dashboards

**Phase 3**:
- ✅ Users can ask "save to dashboard" and it works
- ✅ Dashboards created without leaving Claude Desktop
- ✅ Dashboard URLs shareable with team

---

## Resources

- **Evidence.dev Docs**: https://docs.evidence.dev/
- **WrenAI Charting**: https://getwren.ai/post/announcing-wren-ais-new-ai-powered-charting-engine
- **Rasmus's Stack**: https://rasmusengelbrecht.substack.com/p/my-local-data-stack-duckdb-dlt-dbt
- **DuckDB + Evidence**: https://docs.evidence.dev/deployment/duckdb

---

**Status**: 📋 Ready for Implementation
**Est. Timeline**: 3 weeks (1 week per phase)
**Risk Level**: Low (incremental improvements)
