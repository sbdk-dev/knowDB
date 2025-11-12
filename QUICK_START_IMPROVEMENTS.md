# Quick Start: Improve User Guidance TODAY

## 🎯 Goal
Make your AI analyst 10x more helpful in Claude Desktop by adding context and guidance to every response.

---

## Step 1: Enhance Tool Description (5 minutes)

**File**: `src/mcp_server.py`

**Find this** (around line 80):
```python
Tool(
    name="ask_ai_analyst",
    description="Ask the AI analyst a question in natural language...",
    inputSchema={...}
)
```

**Replace with**:
```python
Tool(
    name="ask_ai_analyst",
    description="""🤖 AI Analyst - Transform business questions into insights

**Try asking**:
  • "What is our MRR?" - Get instant metrics
  • "Show revenue trend over time" - Time-series analysis
  • "Compare MRR by segment" - Categorical breakdown
  • "Top 10 customers by revenue" - Ranked results

**Features**: Natural language queries, 85-100% intent detection, conversation memory (last 10 queries), automatic insights

**New user?** Ask: "What metrics can I analyze?" to see all 20 available metrics.

**Pro tip**: Start broad ("Show MRR"), then drill down ("by segment", "over time")
""",
    inputSchema={...}
)
```

---

## Step 2: Add Welcome Guide Tool (10 minutes)

**File**: `src/mcp_server.py`

**Add this new tool to your list_tools()**:

```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # Existing tools...

        Tool(
            name="welcome_guide",
            description="🎯 NEW USER? Start here for a quick tour of the AI analyst",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        Tool(
            name="ask_ai_analyst",
            # ... existing tool
        ),
    ]
```

**Add the handler**:

```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    # ... existing code ...

    elif name == "welcome_guide":
        welcome_text = """
# 🤖 Welcome to knowDB AI Data Analyst!

## Quick Start (30 seconds)

**Step 1**: See what data you have
```
ask_ai_analyst("What metrics are available?")
```

**Step 2**: Ask your first question
```
ask_ai_analyst("What is our total MRR?")
```

**Step 3**: Follow up naturally
```
ask_ai_analyst("Show the trend over time")
# The AI remembers you're talking about MRR!
```

---

## 💡 What You Can Ask

**📊 Business Metrics** (20 available):
- Revenue: MRR, ARR, revenue per subscription
- Customers: total, active, churn rate, ARPU, LTV
- Subscriptions: total, active, cancelled

**📈 Analysis Types**:
- **Trends**: "How is X changing over time?"
- **Comparisons**: "Compare X by segment/country/industry"
- **Cohorts**: "Show customer cohorts by signup month"
- **Rankings**: "Top 10 customers by revenue"

---

## 🎯 Example Conversations

**Executive Dashboard**:
```
You: "What is our MRR?"
AI: [Shows $28,431.34]

You: "Compare by segment"
AI: [Shows Enterprise: $15K, Mid-Market: $9K, SMB: $4K]

You: "Show trend for Enterprise"
AI: [Shows monthly trend with insights]
```

**Customer Analysis**:
```
You: "How many active customers do we have?"
AI: [Shows count with context]

You: "What's the churn rate?"
AI: [Shows 9.6% with segment breakdown]

You: "Which segment has highest churn?"
AI: [Analyzes and highlights SMB]
```

---

## 📚 All Available Tools

Run these commands:
- `list_metrics()` - See all 20 business metrics
- `list_dimensions()` - See time periods and categories
- `list_canonical_datasets()` - See raw data tables
- `explain_metric("mrr")` - Understand how metrics are calculated
- `cache_stats()` - Check query performance

---

## 🚀 Pro Tips

1. **The AI remembers context** - Ask follow-ups without repeating yourself
2. **Start simple** - "Show X" then add "by Y" or "over time"
3. **Trust the suggestions** - AI provides smart next questions
4. **Natural language works** - No SQL knowledge needed

---

**Ready?** Ask your first question!
"""
        return [TextContent(type="text", text=welcome_text)]
```

---

## Step 3: Enhance AI Analyst Responses (15 minutes)

**File**: `src/ai_agent_flow.py`

**Find**: `ResultInterpreterAgent.format_response()` (around line 600)

**Add this at the end of every response**:

```python
class ResultInterpreterAgent:
    def format_response(self, ...):
        # ... existing formatting code ...

        # Add helpful context
        response += "\n\n" + self._add_contextual_guidance(
            understanding=understanding,
            result=result,
            insights=insights
        )

        return response

    def _add_contextual_guidance(self, understanding, result, insights):
        """Add helpful tips and suggestions based on the query"""

        guidance = []

        # Visualization suggestions
        if understanding.intent == QueryIntent.TREND_ANALYSIS:
            guidance.append("""
## 📊 Visualization Tip

This data is perfect for a **line chart**. Copy this code:

```python
import plotly.express as px
# Paste your data here as 'df'
fig = px.line(df, x='month_column', y='metric_column',
              title='Trend Over Time')
fig.show()
```
""")

        elif understanding.intent == QueryIntent.COMPARISON:
            guidance.append("""
## 📊 Visualization Tip

This data works great as a **bar chart**. Copy this code:

```python
import plotly.express as px
# Paste your data here as 'df'
fig = px.bar(df, x='category_column', y='value_column',
             title='Comparison Across Categories')
fig.show()
```
""")

        # Follow-up suggestions
        if len(insights.get("trends", [])) > 0:
            guidance.append("""
## 🔮 Suggested Next Questions

- "Why did this trend occur?"
- "Compare this metric by customer segment"
- "Show me the top 10 contributors"
- "Filter to only [specific segment/country]"
""")

        # Low confidence warning
        if understanding.confidence < 0.7:
            guidance.append(f"""
## ⚠️ Low Confidence ({understanding.confidence:.0%})

I'm not fully confident I understood correctly. For better results:
- Mention specific metric names (see `list_metrics()`)
- Be explicit about time periods ("over time", "this month")
- Specify dimensions ("by segment", "by country")

**Example**: Instead of "Show revenue stuff", try "What is our MRR by customer segment?"
""")

        # Educational content for new patterns
        if self._is_new_pattern(understanding):
            guidance.append("""
## 💡 Learn More

- **Understand this metric**: `explain_metric("{metric}")`
- **See raw SQL**: Check the SQL output above
- **Performance**: This query took {execution_time:.2f}s

**Cache**: Similar queries will be instant for 30 minutes!
""")

        return "\n".join(guidance)
```

---

## Step 4: Improve Error Messages (10 minutes)

**File**: `src/ai_agent_flow.py`

**Find**: Error handling in `ConversationManager.process_query()`

**Add**:

```python
def process_query(self, query: str, session_id: str = "default"):
    try:
        # ... existing code ...

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user_friendly_message": self._format_user_friendly_error(e, query),
            "recovery_suggestions": self._get_recovery_suggestions(e)
        }

def _format_user_friendly_error(self, error, query):
    """Convert technical errors into helpful messages"""

    error_str = str(error)

    if "Column" in error_str and "not found" in error_str:
        return f"""
❌ **Column Not Found**

The metric or dimension you mentioned doesn't exist in our data.

**Available metrics**: Run `list_metrics()` to see all 20 metrics
**Available dimensions**: Run `list_dimensions()` to see all dimensions

**Did you mean?**:
{self._suggest_similar_names(error, query)}

**Try this instead**: "What metrics are available?"
"""

    elif "Name collisions" in error_str:
        return f"""
❌ **Complex Query Limitation**

This combination of metrics and dimensions creates a technical issue (column name collision).

**Workaround**:
1. Query the metric without dimensions first
2. Then add one dimension at a time

**Example**:
```
ask_ai_analyst("{metric_name}")
# Then:
ask_ai_analyst("{metric_name} by customer_segment")
```

We're working on fixing this limitation!
"""

    elif "confidence" in error_str and "low" in error_str:
        return f"""
⚠️ **I'm Not Sure What You're Asking**

Your question was: "{query}"

**To help me understand better**:
- Use specific metric names from `list_metrics()`
- Add time context: "over time", "this month", "by quarter"
- Specify dimensions: "by segment", "by country"

**Examples of clear questions**:
- ✅ "What is our total MRR?"
- ✅ "Show customer count over time"
- ✅ "Compare ARPU by customer segment"

**Not sure?** Try: `welcome_guide()`
"""

    # Generic error with help
    return f"""
❌ **Something Went Wrong**

Error: {error_str}

**Quick fixes**:
- Check metric name: `list_metrics()`
- Simplify your question
- Try asking about one thing at a time

**Need help?** Run `welcome_guide()` for a tutorial

**Still stuck?** Check the documentation or report this issue.
"""

def _get_recovery_suggestions(self, error):
    """Provide actionable next steps"""

    error_str = str(error)

    if "Column" in error_str or "not found" in error_str:
        return [
            "Run `list_metrics()` to see available metrics",
            "Run `list_dimensions()` to see available dimensions",
            "Try a simpler question first",
        ]

    elif "Name collisions" in error_str:
        return [
            "Query the derived metric without dimensions",
            "Add dimensions one at a time",
            "Use simple metrics instead of derived ones",
        ]

    else:
        return [
            "Rephrase your question more specifically",
            "Start with `welcome_guide()` for examples",
            "Check available data with `list_canonical_datasets()`",
        ]
```

---

## Step 5: Test Your Changes (5 minutes)

**Restart the MCP server**:
```bash
# Kill old server
pkill -f mcp_server.py

# Start new server (Claude Desktop will auto-restart it)
# Or manually:
cd /Users/mattstrautmann/Documents/github/knowDB
.venv/bin/python src/mcp_server.py
```

**Test in Claude Desktop**:

1. **First, try the welcome guide**:
   ```
   welcome_guide()
   ```

2. **Ask a simple question**:
   ```
   ask_ai_analyst("What is our MRR?")
   ```

3. **Check the enhanced response** - you should now see:
   - Clear intent detection
   - Contextual guidance
   - Visualization suggestions
   - Follow-up questions
   - Learning tips

4. **Test error handling**:
   ```
   ask_ai_analyst("Show me the foobar metric")
   ```
   - Should give friendly error with recovery steps

---

## Expected Impact

### Before
```
User: "What is our MRR?"
AI: "28,431.34"
User: "...now what?"
```

### After
```
User: "What is our MRR?"
AI:
  "28,431.34

  💡 Key Insights:
  - Enterprise segment leads with 45%
  - 10% growth month-over-month

  📊 Visualization Tip:
  [Shows chart code]

  🔮 Suggested Next Questions:
  - Compare MRR by customer segment
  - Show MRR trend over time
  - Break down by country

  💡 Learn More:
  - Understand this metric: explain_metric('total_mrr')
  - See calculation: [SQL shown]

  Pro tip: Start broad, then drill down!"
```

---

## Measuring Success

**Before vs After**:

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Queries per session | 1-2 | 5+ |
| Follow-up questions | 10% | 50%+ |
| Error recovery | 20% | 80%+ |
| User satisfaction | ??? | High |

**User Feedback Signals**:
- ✅ More multi-turn conversations
- ✅ Fewer "how do I...?" questions
- ✅ Higher use of suggested follow-ups
- ✅ Repeat usage over time

---

## Timeline

- **Today** (45 min total): Implement Steps 1-4
- **This Week**: Monitor user feedback, iterate
- **Next Week**: Add visualization layer (see VISUALIZATION_STRATEGY.md)
- **Next Month**: Advanced features (dashboards, charts, exports)

---

## Next Steps

1. ✅ Implement these 5 steps (45 minutes)
2. ✅ Test in Claude Desktop
3. ✅ Gather user feedback
4. 📚 Read VISUALIZATION_STRATEGY.md for adding charts
5. 📚 Read CLAUDE_DESKTOP_UX_GUIDE.md for advanced patterns

---

**Remember**: Every response is a teaching opportunity. Don't just answer - guide users to discover what's possible!
