# Improving User Guidance in Claude Desktop

## The Challenge

Users in Claude Desktop don't see a traditional UI with:
- ❌ Navigation menus
- ❌ Tooltips
- ❌ Getting started wizards
- ❌ Visual cues about capabilities

They only see:
- ✅ Natural language chat interface
- ✅ Tool call responses
- ✅ Whatever you tell them

**Result**: Users don't know what's possible or how to ask questions effectively.

---

## Solution: Multi-Layered Guidance System

### Layer 1: Tool Descriptions (First Impression)

**Current State**:
```python
Tool(
    name="ask_ai_analyst",
    description="Ask the AI analyst a question in natural language",
    inputSchema={...}
)
```

**Improved State**:
```python
Tool(
    name="ask_ai_analyst",
    description="""🤖 Ask the AI Analyst - Your Natural Language Business Intelligence Assistant

**What it does**: Transforms your business questions into SQL queries and insights

**Try asking**:
  • "What is our MRR?" (simple metrics)
  • "How is revenue trending over time?" (time-series analysis)
  • "Compare MRR by customer segment" (categorical breakdown)
  • "Show me signup cohorts by month" (cohort analysis)

**Features**:
  ✓ 85-100% intent detection accuracy
  ✓ Automatic metric and dimension selection
  ✓ Conversation context (remembers last 10 queries)
  ✓ Suggested follow-up questions
  ✓ Key insights extraction

**Available Metrics**: 20 business metrics (MRR, ARR, churn, ARPU, LTV, etc.)
**Available Dimensions**: 11 temporal + categorical dimensions

**Pro Tips**:
  • Start broad, then narrow (e.g., "Show MRR" → "By segment")
  • Use natural language (no SQL needed)
  • Ask follow-ups to drill down
  • Request specific time periods

Type 'list_metrics()' to see all available metrics.
""",
    inputSchema={...}
)
```

### Layer 2: Welcome Message Tool

**Create a new MCP tool specifically for onboarding**:

```python
# In src/mcp_server.py

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="welcome_guide",
            description="🎯 Start Here - Get oriented with the AI Data Analyst",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        # ... other tools
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name == "welcome_guide":
        return format_welcome_guide()

def format_welcome_guide() -> str:
    return """
# 🤖 Welcome to knowDB AI Data Analyst!

## What This Can Do

Transform business questions into accurate SQL queries and insights using a 6-agent AI system inspired by WrenAI.

### 🎯 Quick Start

**1. Explore Your Data**
```
ask_ai_analyst("What metrics do I have available?")
```

**2. Ask a Simple Question**
```
ask_ai_analyst("What is our total MRR?")
```

**3. Analyze Trends**
```
ask_ai_analyst("How is customer count changing over time?")
```

**4. Compare Segments**
```
ask_ai_analyst("Compare MRR by customer segment")
```

---

## 📊 Available Data

### Metrics (20 total)
**Revenue**: total_mrr, arr, total_revenue, revenue_per_subscription
**Customers**: total_customers, active_customers, average_customer_age_days
**Subscriptions**: total_subscriptions, active_subscriptions, cancelled_subscriptions
**Derived**: churn_rate, arpu, subscriptions_per_customer, customer_ltv, activation_rate

### Dimensions (11 temporal + categorical)
**Time**: snapshot_month, snapshot_year, snapshot_quarter, customer_signup_month
**Categories**: customer_segment, country, industry, product_tier

### Sample Questions by Category

**📈 Trend Analysis**:
- "Show me MRR growth over the last 12 months"
- "How has customer count evolved?"
- "Track churn rate by quarter"

**🔍 Comparison**:
- "Compare revenue across customer segments"
- "Which country has the highest ARPU?"
- "Break down subscriptions by product tier"

**👥 Cohort Analysis**:
- "Show me customer cohorts by signup month"
- "Track retention by cohort"
- "Compare cohort MRR performance"

**🎯 Filtered Queries**:
- "What's the MRR for Enterprise customers?"
- "Show active subscriptions in the US"
- "Total customers in the Technology industry"

---

## 💡 Pro Tips

### 1. **Conversational Context**
The AI remembers your last 10 queries:
```
You: "What is our MRR?"
AI: [Shows MRR: $28,431]
You: "Show the trend"  ← Remembers you're asking about MRR!
```

### 2. **Start Simple, Then Drill Down**
```
Level 1: "What is our MRR?"
Level 2: "Compare by segment"
Level 3: "Show only Enterprise"
Level 4: "Trend over last 6 months"
```

### 3. **Use Suggested Follow-ups**
The AI provides smart next questions after each response.

### 4. **Trust the Intent Detection**
The AI shows what it understood:
```
Intent: trend_analysis (confidence: 95%)
Plan: Analyzing revenue trend over snapshot_month
```

---

## 🛠️ All Available Tools

1. **ask_ai_analyst** - Natural language queries (⭐ start here)
2. **list_metrics** - See all 20 business metrics
3. **list_dimensions** - See all temporal and categorical dimensions
4. **query_metric** - Direct metric query (advanced)
5. **get_metric_definition** - See how a metric is calculated
6. **list_canonical_datasets** - Available data tables
7. **explain_metric** - Understand metric formulas
8. **cache_stats** - Check query cache performance

---

## 📚 Examples

### Executive Dashboard Questions
```python
ask_ai_analyst("What are our key business metrics?")
ask_ai_analyst("How is the business performing this quarter?")
ask_ai_analyst("Show me a revenue summary")
```

### Sales Analysis
```python
ask_ai_analyst("Which customer segment generates the most revenue?")
ask_ai_analyst("What's our average deal size by industry?")
ask_ai_analyst("Show me customer acquisition trends")
```

### Churn Analysis
```python
ask_ai_analyst("What's our current churn rate?")
ask_ai_analyst("Which segment has the highest churn?")
ask_ai_analyst("Show churn trends over time")
```

---

## 🚀 Next Steps

1. Run: `ask_ai_analyst("What metrics do I have?")`
2. Pick a metric that interests you
3. Ask to see it: `ask_ai_analyst("What is our [metric]?")`
4. Follow the AI's suggested questions to explore deeper

---

## ❓ Getting Help

- **See all metrics**: `list_metrics()`
- **Understand a metric**: `explain_metric("metric_name")`
- **Check data sources**: `list_canonical_datasets()`
- **This guide**: `welcome_guide()`

**Documentation**: See AI_ANALYST_GUIDE.md in the project root

---

💡 **Remember**: This is a conversation! Ask follow-ups, refine queries, and explore your data naturally.
"""
```

### Layer 3: Enhanced AI Analyst Responses

**Add contextual guidance to every response**:

```python
# In src/ai_agent_flow.py

class ResultInterpreterAgent:
    def format_response(self, result, understanding, insights):
        response = f"""
# 🤖 AI Analyst Response

**Intent Detected**: {understanding.intent.value} (confidence: {understanding.confidence:.0%})

**Query Plan**: {self._format_plan()}

---

## Answer

{self._format_natural_language_answer()}

---

## 💡 Key Insights

{self._format_insights(insights)}

---

## 📊 Data

{self._format_data_table(result)}

---

## 🔮 Suggested Follow-up Questions

{self._format_suggestions(understanding, result)}

---

## 📚 Learn More

- **Chart this data**: See VISUALIZATION_STRATEGY.md for chart recommendations
- **Understand the metric**: `explain_metric("{metric_name}")`
- **See raw SQL**: {self._format_sql()}
- **Save for later**: Copy this query for future reference

---

💡 **Tip**: You can combine analyses! Try: "Compare {metric} by segment AND show trend over time"
"""
        return response
```

### Layer 4: Smart Suggestions System

**Enhance the suggestion engine to guide exploration**:

```python
class SuggestionEngine:
    """Generates contextually relevant next questions"""

    def generate_suggestions(self, understanding, result, history):
        suggestions = []

        # Based on intent
        if understanding.intent == QueryIntent.METRIC_QUERY:
            suggestions.extend([
                f"📈 Show {metric} trend over time",
                f"🔍 Compare {metric} by customer segment",
                f"🌍 Break down {metric} by country",
            ])

        # Based on data insights
        if self._has_time_dimension(result):
            suggestions.append("📊 Create a line chart visualization")

        if self._has_multiple_values(result):
            suggestions.append("🏆 Which segment is the leader?")

        # Based on conversation history
        if len(history) > 2:
            suggestions.append("🔄 Summarize what we've learned so far")

        # Educational suggestions
        if understanding.confidence < 0.7:
            suggestions.append("💡 Rephrase your question for better results")

        # Exploration suggestions
        suggestions.extend([
            "🎯 Filter to specific segment/country/industry",
            "📅 Focus on a specific time period",
            "🔗 Combine with another metric",
        ])

        return suggestions[:5]  # Top 5 most relevant
```

### Layer 5: Error Recovery Guidance

**When things go wrong, help users fix it**:

```python
def format_error_response(error, understanding):
    """Turn errors into learning opportunities"""

    if "Column not found" in str(error):
        return f"""
❌ **Query Failed**: Column not found

**What happened**: The dimension/metric you requested doesn't exist in the data.

**Available Options**:
```
# See all metrics
list_metrics()

# See all dimensions
list_dimensions()
```

**Did you mean?**:
{suggest_similar_names(error, understanding)}

**Try asking**:
- "What metrics are available?"
- "Show me all customer-related metrics"
"""

    elif "Name collisions" in str(error):
        return f"""
❌ **Query Failed**: Complex multi-dimensional query

**What happened**: This combination of metrics and dimensions creates conflicting column names (a known limitation).

**Workaround**:
1. Query the derived metric separately:
   `ask_ai_analyst("{metric} without dimensions")`

2. Then break down by one dimension at a time:
   `ask_ai_analyst("{metric} by {dimension}")`

**Why this happens**: When joining multiple tables with derived metrics, column names can collide. We're working on a fix!

**Alternative**: Try simpler dimension combinations first.
"""

    elif understanding.confidence < 0.5:
        return f"""
⚠️ **Low Confidence**: I'm not sure what you're asking

**Confidence Score**: {understanding.confidence:.0%} (below 50% threshold)

**What I understood**:
- Intent: {understanding.intent.value}
- Metrics mentioned: {understanding.entities.get('metrics', 'none')}
- Dimensions mentioned: {understanding.entities.get('dimensions', 'none')}

**To get better results, try**:
1. Mention specific metrics: "What is our MRR?" (not "Show me revenue stuff")
2. Be explicit about time: "...over time" or "...this month"
3. Specify dimensions: "...by segment" or "...by country"

**Example good questions**:
- ✅ "What is our total MRR?"
- ✅ "How is customer count changing month by month?"
- ✅ "Compare ARPU across customer segments"

**Not sure what to ask?** Try: `welcome_guide()`
"""

    return format_generic_error(error)
```

### Layer 6: Onboarding Flow

**Guide brand new users through their first queries**:

```python
class OnboardingManager:
    """Tracks user progression and provides progressive guidance"""

    def __init__(self):
        self.session_queries = []

    def get_contextual_help(self, query_count, last_queries):
        if query_count == 0:
            return self._first_time_help()
        elif query_count == 1:
            return self._second_query_help(last_queries[0])
        elif query_count == 5:
            return self._intermediate_help()
        elif query_count == 20:
            return self._power_user_tips()
        return None

    def _first_time_help(self):
        return """
👋 **Welcome! This is your first query.**

The AI analyst understands natural language. Some examples:

**Simple**: "What is our MRR?"
**Trending**: "How is revenue changing over time?"
**Comparison**: "Compare customers by segment"

After your query, I'll suggest logical follow-ups!
"""

    def _second_query_help(self, first_query):
        return f"""
🎯 **Great! You're getting the hang of it.**

**What you just did**: {self._classify_query_type(first_query)}

**What's next?** Try these patterns:
- **Drill down**: Add "by segment" or "by country"
- **Time analysis**: Add "over time" or "by month"
- **Filter**: Add "for Enterprise customers"

**Pro tip**: The AI remembers your last query, so follow-ups are easy!
"""

    def _intermediate_help(self):
        return """
🚀 **You're becoming an AI analyst pro!**

**Advanced patterns you can try**:
- Combine analyses: "Show MRR by segment AND month"
- Complex filters: "Only Enterprise customers in the US"
- Cohort tracking: "Compare signup cohorts over time"
- Multi-metric: "Show MRR, ARR, and churn together"

**Visualization tip**: After any query, ask "How should I visualize this?"
"""

    def _power_user_tips(self):
        return """
⚡ **Power User Mode Unlocked!**

**Advanced capabilities**:
- Session management: Use `session_id` for isolated conversations
- Cache optimization: Check `cache_stats()` for performance
- Custom time ranges: "Last 6 months" or "Q4 2024"
- Metric definitions: `explain_metric()` shows formulas

**Performance tips**:
- Queries hit cache for 30 minutes
- Use `list_canonical_datasets()` to understand data structure
- Complex derived metrics may need simplified dimensions

Keep exploring! 🎉
"""
```

---

## Implementation Checklist

### Quick Wins (Do This Week)
- [ ] Update `ask_ai_analyst` tool description with examples
- [ ] Add `welcome_guide` tool
- [ ] Enhance error messages with recovery steps
- [ ] Add "Learn More" section to every response

### Medium Priority (Next Week)
- [ ] Implement smart suggestion engine
- [ ] Add onboarding progression system
- [ ] Create troubleshooting guide in responses
- [ ] Add visualization recommendations

### Long Term (Next Month)
- [ ] Session-based help (beginner vs. power user mode)
- [ ] Interactive tutorials
- [ ] Metric discovery wizard
- [ ] Dashboard creation guidance

---

## Measuring Success

**User Engagement Metrics**:
- Query success rate (target: >90%)
- Average confidence scores (target: >85%)
- Queries per session (target: 5+)
- Follow-up question usage (target: 50%+)

**User Feedback Signals**:
- "How do I...?" questions ↓ (good)
- Error recovery success ↑ (good)
- Use of `welcome_guide()` tool (normal for new users)
- Repeat users (target: 70%+)

---

## Key Principle

**Every interaction should teach users what's possible.**

Don't just answer the question - show them:
1. What you understood
2. How you solved it
3. What they could ask next
4. Why it matters

This transforms the AI from a "query tool" to a "business intelligence teacher."

---

**Status**: 📋 Implementation Ready
**Priority**: 🔥 High (directly impacts user adoption)
