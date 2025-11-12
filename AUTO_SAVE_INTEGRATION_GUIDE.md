# Auto-Save Integration Guide
## How to Add Automatic Dashboard Saving to knowDB

This guide shows you exactly how to integrate the auto-save dashboard functionality into your MCP server.

---

## ✅ What's Already Done

- ✅ `src/dashboard_manager.py` - Complete auto-save implementation
- ✅ `dashboards/` directory structure
- ✅ Evidence.dev package.json configured
- ✅ DuckDB connection configured

##  What You Need To Do (15 minutes)

### Step 1: Add Imports to MCP Server (2 min)

**File**: `src/mcp_server.py`

**Add at the top**:
```python
from dashboard_manager import (
    DashboardManager,
    format_auto_save_message
)

# Initialize dashboard manager (add after semantic_layer initialization)
dashboard_manager = DashboardManager()
```

### Step 2: Add New MCP Tools (5 min)

**In `list_tools()` function**, add these new tools:

```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools ...

        Tool(
            name="save_as",
            description="💾 Rename the last auto-saved dashboard to a custom name",
            inputSchema={
                "type": "object",
                "properties": {
                    "new_name": {
                        "type": "string",
                        "description": "Your custom dashboard name"
                    }
                },
                "required": ["new_name"]
            }
        ),

        Tool(
            name="add_to_dashboard",
            description="➕ Add current chart to an existing dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "dashboard_name": {
                        "type": "string",
                        "description": "Name of existing dashboard"
                    }
                },
                "required": ["dashboard_name"]
            }
        ),

        Tool(
            name="list_dashboards",
            description="📋 List all Evidence.dev dashboards",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        Tool(
            name="cleanup_dashboards",
            description="🧹 Remove auto-generated dashboards older than 7 days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_old": {
                        "type": "number",
                        "description": "Age threshold in days (default: 7)",
                        "default": 7
                    }
                },
                "required": []
            }
        ),
    ]
```

### Step 3: Add Tool Handlers (5 min)

**In `call_tool()` function**, add these handlers:

```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    # ... existing tool handlers ...

    elif name == "save_as":
        new_name = arguments["new_name"]

        try:
            result = dashboard_manager.save_as(new_name)
            return [TextContent(
                type="text",
                text=f"""✅ Dashboard Renamed

**New Name**: {result['dashboard_name']}
🌐 **View**: {result['url']}
📂 **Path**: `{result['path']}`

The dashboard is now saved with your custom name and won't be auto-cleaned up!
"""
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error renaming dashboard: {str(e)}\n\nMake sure you've run a query first!"
            )]

    elif name == "add_to_dashboard":
        dashboard_name = arguments["dashboard_name"]

        # Get last query result from conversation manager
        # (You'll need to store this when processing queries)
        last_query = getattr(conversation_manager, 'last_query_result', None)

        if not last_query:
            return [TextContent(
                type="text",
                text="❌ No recent query to add. Run a query first!"
            )]

        try:
            result = dashboard_manager.add_to_dashboard(
                dashboard_name=dashboard_name,
                query_text=last_query['query_text'],
                understanding=last_query['understanding'],
                result=last_query['data'],
                sql=last_query['sql'],
                chart_recommendation=last_query.get('chart', {})
            )

            return [TextContent(
                type="text",
                text=f"""✅ Added to Dashboard

📊 **Dashboard**: {result['dashboard_name']}
🌐 **View**: {result['url']}
🎯 **Charts**: Multiple visualizations now included

Keep asking questions to add more charts!
"""
            )]
        except FileNotFoundError:
            return [TextContent(
                type="text",
                text=f"""❌ Dashboard '{dashboard_name}' not found

**Available dashboards**:
{chr(10).join(['- ' + d['name'] for d in dashboard_manager.list_dashboards()])}

Or create a new one by asking a question!
"""
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]

    elif name == "list_dashboards":
        dashboards = dashboard_manager.list_dashboards()

        if not dashboards:
            return [TextContent(
                type="text",
                text="""📊 No Dashboards Yet

Ask some questions to create your first dashboard!

Example: `ask_ai_analyst("What is our MRR?")`
"""
            )]

        # Format dashboard list
        dashboard_list = "# 📊 Your Evidence.dev Dashboards\n\n"

        auto_generated = [d for d in dashboards if d['is_auto_generated']]
        custom = [d for d in dashboards if not d['is_auto_generated']]

        if custom:
            dashboard_list += "## 📌 Custom Dashboards (Permanent)\n\n"
            for d in custom:
                dashboard_list += f"""**{d['title']}**
- Charts: {d['num_charts']}
- Modified: {d['modified']}
- 🌐 [View]({d['url']})

"""

        if auto_generated:
            dashboard_list += "## ⏱️ Auto-Generated (7-day retention)\n\n"
            for d in auto_generated:
                dashboard_list += f"""**{d['title']}**
- Charts: {d['num_charts']}
- Modified: {d['modified']}
- 🌐 [View]({d['url']})

"""

        dashboard_list += f"""
---

**Total**: {len(dashboards)} dashboards

**Tips**:
- Click URLs to view in Evidence.dev
- `save_as("name")` to keep auto-generated dashboards
- `cleanup_dashboards()` to remove old auto-generated ones
"""

        return [TextContent(type="text", text=dashboard_list)]

    elif name == "cleanup_dashboards":
        days_old = arguments.get("days_old", 7)
        cleaned = dashboard_manager.cleanup_old_dashboards(days_old)

        if cleaned:
            return [TextContent(
                type="text",
                text=f"""🧹 Cleanup Complete

Removed {len(cleaned)} old auto-generated dashboards:

{chr(10).join(['- ' + name for name in cleaned])}

Custom (renamed) dashboards were preserved!
"""
            )]
        else:
            return [TextContent(
                type="text",
                text=f"""✅ Already Clean!

No auto-generated dashboards older than {days_old} days found.

**Current dashboards**: {len(dashboard_manager.list_dashboards())}
"""
            )]
```

### Step 4: Enable Auto-Save in AI Analyst (3 min)

**Modify the `ask_ai_analyst` tool handler** to auto-save results:

```python
elif name == "ask_ai_analyst":
    question = arguments["question"]
    session_id = arguments.get("session_id", "default")

    # Process query (existing code)
    response = conversation_manager.process_query(question, session_id)

    # AUTO-SAVE: Save to Evidence.dev dashboard
    if response.get('status') == 'success':
        try:
            dashboard_info = dashboard_manager.auto_save_query(
                query_text=question,
                understanding=response['understanding'],
                result=response['data'],
                sql=response.get('sql', ''),
                chart_recommendation=response.get('chart', {})
            )

            # Add auto-save message to response
            response['text'] += format_auto_save_message(dashboard_info)

            # Store for add_to_dashboard tool
            conversation_manager.last_query_result = {
                'query_text': question,
                'understanding': response['understanding'],
                'data': response['data'],
                'sql': response.get('sql', ''),
                'chart': response.get('chart', {})
            }

        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
            # Don't fail the whole query if auto-save fails

    # Return response (existing code)
    return [TextContent(type="text", text=response['text'])]
```

---

## 🧪 Testing (5 minutes)

### 1. Restart MCP Server

```bash
# Kill old server
pkill -f mcp_server.py

# Restart Claude Desktop (it will auto-start the server)
```

### 2. Test Auto-Save

In Claude Desktop:

```
ask_ai_analyst("What is our total MRR?")
```

**Expected**: Response includes:
```
💾 Auto-Saved to Dashboard
📊 Dashboard: total-mrr-20241109-143022
🌐 View: http://localhost:3000/total-mrr-20241109-143022
```

### 3. Test Rename

```
save_as("executive-summary")
```

**Expected**:
```
✅ Dashboard Renamed
New Name: executive-summary
🌐 View: http://localhost:3000/executive-summary
```

### 4. Test Multiple Charts

```
ask_ai_analyst("Show customer count over time")
add_to_dashboard("executive-summary")
```

**Expected**: Both MRR and customer charts now in one dashboard

### 5. Test List

```
list_dashboards()
```

**Expected**: Shows all dashboards with details

### 6. View in Evidence.dev

Make sure Evidence.dev is running:

```bash
cd dashboards
npm run dev
```

Then open: `http://localhost:3000`

---

## 🎯 Expected User Experience

**Query 1**:
```
User: "What is our MRR?"
AI: [Shows MRR: $28,431.34]

    💾 Auto-saved: http://localhost:3000/total-mrr-20241109-143022
```

**Query 2**:
```
User: "Show the trend"
AI: [Shows MRR trend chart]

    💾 Auto-saved: http://localhost:3000/total-mrr-trend-20241109-143045
```

**Combine**:
```
User: "Put both on one dashboard called 'revenue-overview'"
AI: ✅ Combined into: http://localhost:3000/revenue-overview
```

**View**:
```
User: [Clicks link]
Browser: Opens Evidence.dev with both charts!
```

---

## ✅ Success Checklist

- [ ] Auto-save works on every query
- [ ] Dashboard URLs are clickable in Claude Desktop
- [ ] `save_as()` renames dashboards
- [ ] `add_to_dashboard()` combines charts
- [ ] `list_dashboards()` shows all dashboards
- [ ] `cleanup_dashboards()` removes old ones
- [ ] Evidence.dev displays dashboards correctly

---

## 🐛 Troubleshooting

### Auto-save not working
```python
# Check dashboard_manager is initialized
print(dashboard_manager)  # Should not be None

# Check dashboards directory exists
ls dashboards/pages/
```

### Evidence.dev not showing dashboards
```bash
cd dashboards
npm install
npm run dev
# Open http://localhost:3000
```

### Dashboards empty or broken
- Check SQL query is valid
- Verify data has rows
- Look at generated markdown file

---

## 🎉 You're Done!

Every AI analyst query now:
1. ✅ Auto-saves to Evidence.dev
2. ✅ Provides clickable dashboard URL
3. ✅ Allows renaming and combining
4. ✅ Auto-cleans old dashboards
5. ✅ Works seamlessly in Claude Desktop

**Total Implementation Time**: ~15 minutes
**User Experience**: Frictionless dashboard creation!
