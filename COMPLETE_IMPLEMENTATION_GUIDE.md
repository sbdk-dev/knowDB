# Complete Implementation Guide: WrenAI-Style Visualizations + UX Improvements

This guide provides EVERYTHING needed to add chart generation and improve user experience.

## 📦 What You're Building

1. **WrenAI-Style Chart Recommendations** - Automatic chart type selection
2. **Evidence.dev Integration** - Local dashboard generation
3. **Enhanced UX** - Welcome guide, better descriptions, helpful errors
4. **MCP Tools** - Dashboard management from Claude Desktop

## 🚀 Quick Start (45 minutes)

### Step 1: Install Evidence.dev (5 min)

```bash
cd /Users/mattstrautmann/Documents/github/knowDB/dashboards
npm install
npm run dev
```

This starts Evidence on `http://localhost:3000`

### Step 2: Create visualization_engine.py (already created)

```bash
ls -la src/visualization_engine.py  # Should exist
```

### Step 3: Update MCP Server (10 min)

Add to `src/mcp_server.py`:

```python
# At the top, add imports
from visualization_engine import (
    ChartRecommendationEngine, 
    EvidenceDashboardGenerator,
    format_chart_recommendation_for_claude
)

# Initialize engines
chart_engine = ChartRecommendationEngine()
dashboard_generator = EvidenceDashboardGenerator()

# Add new tools to list_tools()
Tool(
    name="welcome_guide",
    description="🎯 Start Here - Quick tour for new users",
    inputSchema={"type": "object", "properties": {}, "required": []}
),

Tool(
    name="generate_dashboard",
    description="📊 Create Evidence.dev dashboard from current analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "dashboard_name": {"type": "string"},
            "include_charts": {"type": "boolean", "default": True}
        },
        "required": ["dashboard_name"]
    }
),

# Add tool handlers
elif name == "welcome_guide":
    return [TextContent(type="text", text="""
# 🤖 Welcome to knowDB AI Analyst!

## Try These First

1. **See Your Data**
   `ask_ai_analyst("What metrics are available?")`

2. **Ask a Question**
   `ask_ai_analyst("What is our MRR?")`

3. **Analyze Trends**
   `ask_ai_analyst("How is revenue changing over time?")`

4. **Create Dashboard**
   `generate_dashboard("my-first-dashboard")`

## 💡 Pro Tips

- The AI remembers context - ask follow-ups!
- Every response includes chart recommendations
- Dashboards auto-save to Evidence.dev
- Use `list_metrics()` to see all data

**Questions?** Ask away - I'm here to help!
""")]

elif name == "generate_dashboard":
    dashboard_name = arguments["dashboard_name"]
    # Get recent query results from conversation_manager
    recent_queries = conversation_manager.get_session_history(session_id="default")

    # Generate chart recommendations for each
    chart_recs = []
    for query in recent_queries[-5:]:  # Last 5 queries
        chart = chart_engine.recommend_chart(
            understanding=query['understanding'],
            result=query['data'],
            insights=query.get('insights', {})
        )
        chart_recs.append(chart)

    # Generate dashboard
    dashboard_path = dashboard_generator.generate_dashboard(
        dashboard_name=dashboard_name,
        query_results=recent_queries[-5:],
        chart_recommendations=chart_recs
    )

    return [TextContent(type="text", text=f"""
✅ Dashboard Created: {dashboard_name}

📂 Location: {dashboard_path}
🌐 URL: http://localhost:3000/{dashboard_name.replace('_', '-')}

The dashboard includes:
- {len(chart_recs)} visualizations
- SQL queries for each chart
- Interactive data tables
- Auto-refresh with new data

**View it**: Open http://localhost:3000/{dashboard_name.replace('_', '-')}

**Edit it**: Open {dashboard_path} in your editor
""")]
```

### Step 4: Enhance AI Analyst Responses (10 min)

Update `src/ai_agent_flow.py` in `ResultInterpreterAgent`:

```python
def format_response(self, result, understanding, insights):
    # ... existing code ...
    
    # Add chart recommendation
    chart_rec = chart_engine.recommend_chart(understanding, result, insights)
    response += format_chart_recommendation_for_claude(chart_rec)
    
    # Add contextual guidance
    response += self._add_guidance(understanding, result)
    
    return response

def _add_guidance(self, understanding, result):
    """Add helpful tips based on query"""
    
    tips = []
    
    # Visualization tip
    if understanding['intent'] == 'trend_analysis':
        tips.append("💡 **Tip**: This is perfect for a line chart!")
    
    # Follow-up suggestions
    tips.append(f"""
🔮 **Try Next**:
- Add "by segment" to break this down
- Ask "show me the trend" to see changes
- Request "top 10" to see leaders
""")
    
    # Low confidence warning
    if understanding['confidence'] < 0.7:
        tips.append(f"""
⚠️ **Low Confidence** ({understanding['confidence']:.0%})

For better results:
- Mention specific metrics (see `list_metrics()`)
- Add time context ("over time", "this month")
- Specify dimensions ("by segment", "by country")
""")
    
    return "\n\n---\n\n" + "\n\n".join(tips)
```

### Step 5: Test Everything (10 min)

1. **Restart Claude Desktop** (to reload MCP server)

2. **Try Welcome Guide**:
   ```
   welcome_guide()
   ```

3. **Ask Question with Chart**:
   ```
   ask_ai_analyst("Show me MRR trend over time")
   ```
   
   ✅ Should see chart recommendation with code!

4. **Generate Dashboard**:
   ```
   generate_dashboard("revenue-analysis")
   ```
   
   ✅ Opens http://localhost:3000/revenue-analysis

## 📊 Evidence.dev Dashboard Example

Create `dashboards/pages/index.md`:

```markdown
---
title: knowDB Analytics
---

# Executive Dashboard

## Monthly Recurring Revenue

```sql mrr_trend
SELECT 
    snapshot_month,
    SUM(mrr) as total_mrr
FROM monthly_mrr_snapshots
GROUP BY snapshot_month
ORDER BY snapshot_month
```

<LineChart
    data={mrr_trend}
    x=snapshot_month
    y=total_mrr
    title="MRR Growth"
/>

## By Customer Segment

```sql mrr_by_segment
SELECT
    customer_segment,
    SUM(mrr) as segment_mrr
FROM monthly_mrr_snapshots
GROUP BY customer_segment
ORDER BY segment_mrr DESC
```

<BarChart
    data={mrr_by_segment}
    x=customer_segment
    y=segment_mrr
    title="MRR by Segment"
/>
```

## 🎯 Expected User Experience

### Before
```
User: "What is our MRR?"
AI: "28,431.34"
User: "...ok?"
```

### After
```
User: "What is our MRR?"
AI: "28,431.34

📊 Chart Recommendation: Single Value Card
[Plotly code provided]

💡 Try Next:
- Show MRR trend over time
- Compare MRR by segment
- Break down by country

🎨 Save to dashboard: generate_dashboard('revenue-overview')"
```

## ✅ Success Checklist

- [ ] Evidence.dev running on localhost:3000
- [ ] Chart recommendations appear in every response
- [ ] Welcome guide tool works
- [ ] Dashboard generation creates files
- [ ] Dashboards viewable in browser
- [ ] UX improvements visible in responses

## 🔧 Troubleshooting

### Evidence.dev won't start
```bash
cd dashboards
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Charts not appearing
- Check `visualization_engine.py` is imported
- Verify chart_engine is initialized
- Check logs for errors

### Dashboard generation fails
- Ensure `dashboards/pages/` directory exists
- Check write permissions
- Verify conversation_manager has history

## 📚 Next Steps

### Week 2: Advanced Features
- Multi-chart dashboards
- Custom time ranges
- Drill-down capabilities
- Export to PDF

### Week 3: Production
- Deploy Evidence.dev
- Add authentication
- Team sharing
- Scheduled updates

## 🎉 You're Done!

Your AI analyst now:
- ✅ Recommends charts automatically
- ✅ Generates Evidence.dev dashboards
- ✅ Provides helpful guidance
- ✅ Has welcome experience
- ✅ Works seamlessly in Claude Desktop

**Test it**: Restart Claude Desktop and ask questions!
