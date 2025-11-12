# Dashboard Save UX - Best Practices for Claude Desktop

## The Challenge

Claude Desktop has no buttons, so we need **conversational commands** that feel natural.

---

## Option 1: Manual Save (Current)

**User Flow**:
```
User: "Show me MRR trend"
AI: [Shows results + chart recommendation]

User: "Save this to a dashboard"  ← Extra step required
AI: [Generates dashboard]
```

**Pros**:
- User has control
- Won't create unwanted dashboards

**Cons**:
- Extra step required
- Easy to forget
- Friction in workflow

---

## Option 2: Auto-Save with Smart Naming ⭐ RECOMMENDED

**User Flow**:
```
User: "Show me MRR trend"
AI: [Shows results + chart recommendation]

✅ Auto-saved to dashboard: "mrr-trend-2024-11-09"
📂 View: http://localhost:3000/mrr-trend-2024-11-09

Or customize the name:
- save_as("my-custom-name")
- add_to_dashboard("existing-dashboard")
```

**Pros**:
- Zero friction - works automatically
- Still allows customization
- Progressive disclosure (can ignore if not needed)

**Cons**:
- Creates many dashboard files (easily cleaned up)

---

## Option 3: Ask Before Saving

**User Flow**:
```
User: "Show me MRR trend"
AI: [Shows results + chart recommendation]

💾 Save this visualization to a dashboard?
- save_dashboard("mrr-trends")  ← Suggested name
- skip  ← Don't save
```

**Pros**:
- Explicit consent
- Suggests good names

**Cons**:
- Interrupts flow
- Requires response from user

---

## Recommended Implementation: Smart Auto-Save

### How It Works

**Every AI analyst response automatically**:
1. Generates the chart recommendation
2. Creates a dashboard file (non-intrusive)
3. Tells user where it is
4. Provides options to rename/customize

**Code Changes Needed**:

```python
# In src/mcp_server.py

elif name == "ask_ai_analyst":
    # ... existing AI analyst code ...

    # After generating response
    response = conversation_manager.process_query(question, session_id)

    # Auto-generate dashboard
    if response.get('status') == 'success':
        # Create auto-saved dashboard
        auto_dashboard_name = f"{metric_name}-{intent}-{timestamp}"
        dashboard_path = dashboard_generator.generate_dashboard(
            dashboard_name=auto_dashboard_name,
            query_results=[response],
            chart_recommendations=[response['chart_recommendation']]
        )

        # Add to response
        response['text'] += f"""

---

## 💾 Auto-Saved to Dashboard

📂 **Location**: {dashboard_path}
🌐 **View**: http://localhost:3000/{auto_dashboard_name}

**Customize**:
- `rename_dashboard("{auto_dashboard_name}", "my-custom-name")`
- `add_to_dashboard("existing-dashboard")` - Add to existing
- `delete_dashboard("{auto_dashboard_name}")` - Remove
"""
```

### User Experience

**Simple Case**:
```
User: "Show me MRR trend"
AI: [Shows data + chart]

💾 Auto-saved: http://localhost:3000/mrr-trend-20241109

User: [Can click link OR ignore and continue]
```

**Power User Case**:
```
User: "Show me MRR trend"
AI: [Shows data + chart]
    Auto-saved: mrr-trend-20241109

User: "Rename that to 'executive-summary'"
AI: ✅ Renamed to 'executive-summary'
    http://localhost:3000/executive-summary
```

**Multi-Chart Dashboard**:
```
User: "Show me MRR trend"
AI: [Chart 1] Auto-saved: mrr-trend-20241109

User: "Now show customer count"
AI: [Chart 2] Auto-saved: customer-count-20241109

User: "Combine these into one dashboard called 'overview'"
AI: ✅ Created 'overview' dashboard with 2 charts
    http://localhost:3000/overview
```

---

## Implementation: Three New MCP Tools

### 1. Auto-Save (Built into ask_ai_analyst)

Every query automatically saves. User doesn't need to do anything.

### 2. save_as() - Rename Current Dashboard

```python
Tool(
    name="save_as",
    description="💾 Save/rename the last chart to a custom dashboard name",
    inputSchema={
        "type": "object",
        "properties": {
            "dashboard_name": {"type": "string", "description": "Your custom name"}
        },
        "required": ["dashboard_name"]
    }
)
```

**Usage**:
```
save_as("my-revenue-dashboard")
```

### 3. add_to_dashboard() - Append to Existing

```python
Tool(
    name="add_to_dashboard",
    description="➕ Add current chart to an existing dashboard",
    inputSchema={
        "type": "object",
        "properties": {
            "dashboard_name": {"type": "string", "description": "Existing dashboard name"}
        },
        "required": ["dashboard_name"]
    }
)
```

**Usage**:
```
add_to_dashboard("executive-overview")
```

### 4. list_dashboards() - See All Saved

```python
Tool(
    name="list_dashboards",
    description="📋 List all Evidence.dev dashboards",
    inputSchema={"type": "object", "properties": {}, "required": []}
)
```

**Usage**:
```
list_dashboards()

Output:
📊 Your Dashboards (5)
1. mrr-trend-20241109 (1 chart) - http://localhost:3000/mrr-trend-20241109
2. customer-analysis (3 charts) - http://localhost:3000/customer-analysis
3. executive-overview (5 charts) - http://localhost:3000/executive-overview
4. churn-analysis (2 charts) - http://localhost:3000/churn-analysis
5. revenue-breakdown (1 chart) - http://localhost:3000/revenue-breakdown
```

---

## Cleanup Strategy

Since auto-save creates many files:

### 1. Auto-Cleanup Old Dashboards

```python
# In dashboard_generator.py

def cleanup_old_dashboards(self, days_old=7):
    """Remove auto-generated dashboards older than N days"""

    for dashboard_file in self.dashboards_path.glob("*.md"):
        # Only cleanup auto-generated (timestamp in name)
        if re.match(r".*-\d{8}\.md$", dashboard_file.name):
            age_days = (datetime.now() - datetime.fromtimestamp(dashboard_file.stat().st_mtime)).days
            if age_days > days_old:
                dashboard_file.unlink()
                logging.info(f"Cleaned up old dashboard: {dashboard_file}")
```

### 2. User-Initiated Cleanup

```python
Tool(
    name="cleanup_dashboards",
    description="🧹 Remove auto-generated dashboards older than 7 days",
    inputSchema={"type": "object", "properties": {}, "required": []}
)
```

---

## Final Recommendation

### ✅ Use Auto-Save with Smart Defaults

**Why**:
1. **Zero friction** - Users don't think about saving
2. **Progressive disclosure** - Can ignore or customize
3. **Natural flow** - Ask questions, get results, dashboards exist
4. **Easy cleanup** - Auto-delete old ones
5. **Power user friendly** - Can organize later

**User Experience**:
```
User: "Show me MRR trend"
AI: [Shows chart]
    💾 Saved: http://localhost:3000/mrr-trend-20241109

User: [Clicks link OR continues asking questions]

User: "Show customer count over time"
AI: [Shows chart]
    💾 Saved: http://localhost:3000/customer-count-20241109

User: "Combine these into 'executive-dashboard'"
AI: ✅ Combined into http://localhost:3000/executive-dashboard
    (Contains: MRR trend + Customer count)
```

**Key Principle**:
> Make the default behavior "just work", then provide options for customization.

---

## Quick Implementation Checklist

- [ ] Enable auto-save in `ask_ai_analyst` tool
- [ ] Add `save_as()` tool for renaming
- [ ] Add `add_to_dashboard()` tool for combining
- [ ] Add `list_dashboards()` tool for browsing
- [ ] Add `cleanup_dashboards()` for maintenance
- [ ] Set 7-day auto-cleanup for old dashboards
- [ ] Update welcome guide with dashboard commands

---

**Estimated Time**: 30 minutes to implement
**User Impact**: Massive - removes all friction from creating dashboards
