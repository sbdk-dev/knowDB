# 🤖 AI Analyst Guide - WrenAI-Inspired Conversational BI

Complete guide to using the AI analyst in Claude Desktop for natural language business intelligence queries.

---

## 🎯 Overview

The AI Analyst is a **WrenAI-inspired multi-agent system** that transforms natural language questions into accurate SQL queries and insightful business answers. It works natively in Claude Desktop via the MCP protocol.

### Key Features

- 🗣️ **Natural Language Interface** - Ask questions like you would to a human analyst
- 🧠 **Intent Understanding** - Automatically detects what you're trying to ask
- 📊 **Smart Query Planning** - Finds the best metrics and dimensions for your question
- 💡 **Insight Generation** - Provides key insights and trends from your data
- 🔮 **Follow-up Suggestions** - Recommends related questions to explore
- 🔄 **Conversation Context** - Remembers previous queries in your session

---

## 🏗️ Architecture

The AI Analyst uses a **6-agent multi-agent architecture** inspired by WrenAI:

```
┌─────────────────────────────────────────────────────────────┐
│                   User's Natural Language Query             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  1. Query Understanding    │  Parse intent & entities
        │     Agent                  │  (What are they asking?)
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  2. Semantic Retriever     │  Find relevant metrics/dimensions
        │     Agent (RAG)            │  (Which data do they need?)
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  3. Query Planner          │  Create semantic query plan
        │     Agent                  │  (How to get the answer?)
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  4. SQL Generator          │  Execute query via semantic layer
        │     Agent                  │  (Run the query)
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  5. Result Interpreter     │  Format & explain results
        │     Agent                  │  (What does it mean?)
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  6. Conversation Manager   │  Maintain context & orchestrate
        │     (Orchestrator)         │  (Remember & coordinate)
        └────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Configure Claude Desktop

Add the semantic layer MCP server to your Claude Desktop configuration:

**File:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "knowdb-semantic-layer": {
      "command": "/Users/mattstrautmann/Documents/github/knowDB/.venv/bin/python",
      "args": [
        "/Users/mattstrautmann/Documents/github/knowDB/src/mcp_server.py"
      ],
      "env": {
        "SEMANTIC_MODELS_PATH": "/Users/mattstrautmann/Documents/github/knowDB/semantic_models/metrics.yml",
        "DATABASE_PATH": "/Users/mattstrautmann/Documents/github/knowDB/data/sample.duckdb"
      }
    }
  }
}
```

### 2. Restart Claude Desktop

After updating the configuration, completely quit and restart Claude Desktop for the changes to take effect.

### 3. Verify Connection

In Claude Desktop, you should see a 🔌 icon indicating MCP tools are connected. You can verify by asking:

```
Can you show me what MCP tools are available?
```

You should see the `ask_ai_analyst` tool listed.

---

## 💬 How to Use

### Basic Usage

Simply ask your business question in natural language:

```
What is our total MRR?
```

**Response:**
```
# 🤖 AI Analyst Response

**Intent Detected:** metric_query (confidence: 90%)

**Query Plan:** Querying total_mrr
  - Metrics: total_mrr

## Answer

The Monthly Recurring Revenue (MRR) is 28,431.34.

## Generated SQL

[SQL query shown for transparency]

*Query executed in 0.82s*
```

### Supported Question Types

#### 1. Metric Queries
Ask about specific metrics:

```
- What is our total MRR?
- How many active customers do we have?
- What's the churn rate?
- Show me ARPU
```

#### 2. Trend Analysis
Analyze how metrics change over time:

```
- How is my active customer count changing over time?
- Show me MRR trend
- What's the revenue growth this year?
- Track monthly customer growth
```

**AI Features:**
- Automatically selects time dimensions (month, quarter, year)
- Provides trend insights (% change, direction)
- Suggests time-based comparisons

#### 3. Comparison Queries
Compare metrics across categories:

```
- Compare MRR by customer segment
- Show revenue by country
- Break down subscriptions by product tier
- Compare ARPU across segments
```

**AI Features:**
- Selects appropriate categorical dimensions
- Shows range and distribution
- Suggests drill-down analyses

#### 4. Cohort Analysis
Analyze customer cohorts:

```
- Show me customer signup cohorts
- Track cohort retention
- Compare cohort performance
```

**AI Features:**
- Uses signup/subscription start dates
- Limits to reasonable number of cohorts
- Orders by recency

---

## 🎓 Example Conversations

### Example 1: Business Health Check

```
User: What is our total MRR?
AI: The Monthly Recurring Revenue (MRR) is $28,431.34

User: How does that compare by segment?
AI: [Shows MRR breakdown by Enterprise, Mid-Market, SMB]

User: Show the trend over time
AI: [Shows monthly MRR trend with insights]
```

### Example 2: Growth Analysis

```
User: How is my active customer count changing over time?
AI: Found 10 months of data showing customer growth
     💡 Insights: decreased by 10.0% from start to end

User: Which segment is churning?
AI: [Shows churn by customer segment]
```

### Example 3: Revenue Deep Dive

```
User: Compare MRR by customer segment
AI: [Shows MRR across Enterprise, Mid-Market, SMB]
     💡 Range: $X to $Y

User: Show me ARPU for each segment
AI: [Calculates and displays ARPU by segment]

User: What about customer lifetime value?
AI: [Shows LTV calculations with methodology]
```

---

## 🧠 AI Capabilities

### Intent Detection

The AI automatically detects your question intent with confidence scoring:

| Intent | Examples | Confidence Factors |
|--------|----------|-------------------|
| **metric_query** | "What is our MRR?" | Metric mentions |
| **trend_analysis** | "How is MRR changing?" | Time keywords (trend, changing, over time) |
| **comparison** | "Compare MRR by segment" | Comparison keywords (compare, by, across) |
| **cohort_analysis** | "Show signup cohorts" | Cohort keywords (cohort, retention, signup) |

### Entity Extraction

The AI extracts relevant entities from your question:

- **Metrics**: Detects mentioned business metrics (MRR, customers, ARPU, etc.)
- **Dimensions**: Identifies grouping dimensions (segment, country, time periods)
- **Filters**: Understands filtering intent (specific segments, countries, etc.)
- **Time Scope**: Detects temporal references (last month, this year, Q4)

### Semantic Retrieval

Using RAG (Retrieval-Augmented Generation) patterns:

1. Builds semantic understanding from metric/dimension definitions
2. Finds relevant metrics even with fuzzy matching
3. Suggests related metrics you didn't explicitly ask for
4. Understands business context from descriptions

### Query Planning

The planner optimizes queries based on intent:

- **Trend Analysis**: Selects time dimensions, orders chronologically
- **Comparison**: Picks categorical dimensions, shows full breakdown
- **Cohort**: Uses signup dates, limits to recent cohorts
- **Top-N**: Applies limits and ordering automatically

### Insight Generation

The AI provides actionable insights:

- **Trend Insights**: % change, direction (increasing/decreasing)
- **Range Insights**: Min/max values, distribution
- **Comparison Insights**: Leaders vs laggards
- **Anomaly Detection**: Outliers and unusual patterns (future)

### Follow-up Suggestions

Based on your query, the AI suggests logical next questions:

```
🔮 Suggested Follow-up Questions
- Break down total_mrr by customer segment
- Compare total_mrr to last year
- Show total_mrr trend over time
```

---

## 🔧 Advanced Usage

### Session Management

Maintain conversation context across multiple queries:

```python
# Default session
ask_ai_analyst(question="What is our MRR?")

# Named session for specific analysis
ask_ai_analyst(
    question="Show revenue trends",
    session_id="revenue_analysis_2024"
)
```

The conversation manager:
- Remembers your last 10 queries
- Tracks last used metrics and dimensions
- Maintains context for follow-up questions
- Stores conversation history per session

### Custom Temporal Scope

The AI understands temporal references:

```
- "Show MRR for last month"
- "Compare this year vs last year"
- "What was Q4 performance?"
- "Track the last 12 months"
```

### Multi-dimensional Analysis

Ask complex multi-dimensional questions:

```
- "Show MRR by segment and month"
- "Compare ARPU by country and product tier"
- "Track cohort performance over time"
```

---

## 📊 Output Format

### Response Structure

Every AI analyst response includes:

#### 1. Understanding
```
**Intent Detected:** trend_analysis (confidence: 100%)
```
Shows what the AI understood and confidence level.

#### 2. Query Plan
```
**Query Plan:** Analyzing monthly_customer_count trend over snapshot_month
  - Metrics: monthly_customer_count
  - Dimensions: snapshot_month
```
Explains the execution plan before running the query.

#### 3. Answer
```
## Answer

Found 13 time periods showing customer growth trends.
```
Natural language narrative of the result.

#### 4. Key Insights
```
## 💡 Key Insights

- Trend: increased by 15.2% from start to end
- Range: 85 to 98 customers
```
Automated insights extracted from the data.

#### 5. Data Table
```
## 📊 Data

| snapshot_month | monthly_customer_count |
| -------------- | --------------------- |
| 2024-11        | 100                   |
| 2024-12        | 100                   |
```
Raw data in markdown table format.

#### 6. SQL Transparency
```
## Generated SQL

SELECT
  STRFTIME(month, '%Y-%m') AS snapshot_month,
  SUM(customer_count) AS monthly_customer_count
FROM monthly_mrr_snapshots
GROUP BY 1
ORDER BY snapshot_month ASC
```
Shows the actual SQL for full transparency.

#### 7. Suggestions
```
## 🔮 Suggested Follow-up Questions

- Break down monthly_customer_count by customer segment
- Compare monthly_customer_count to last year
```
Smart follow-up question suggestions.

---

## 🎯 Best Practices

### 1. Start Broad, Then Narrow

```
✅ Good:
1. "What is our MRR?"
2. "Show that by segment"
3. "Focus on Enterprise"

❌ Less Effective:
"What is the MRR for Enterprise customers with annual billing
in the US who signed up in Q3 2024?"
```

### 2. Use Natural Language

```
✅ Good:
"How is revenue trending?"
"Compare customers by segment"

❌ Unnecessary:
"SELECT SUM(revenue) FROM..."
"query_metric(metric_name='revenue'...)"
```

### 3. Ask Follow-ups

The AI maintains context, so ask follow-ups:

```
1. "What is our MRR?"
2. "How does that trend?"
3. "Which segment is growing fastest?"
```

### 4. Trust the AI's Understanding

The AI will show you its understanding before executing:

```
**Intent Detected:** trend_analysis (confidence: 95%)
**Query Plan:** Analyzing revenue trend over month
```

If it misunderstands, just clarify in a follow-up.

---

## 🐛 Troubleshooting

### AI Analyst Not Available

```
Error: ❌ AI analyst is not available
```

**Solutions:**
1. Check MCP server is running in Claude Desktop
2. Verify configuration in `claude_desktop_config.json`
3. Restart Claude Desktop
4. Check logs for initialization errors

### Low Confidence Intent Detection

```
**Intent Detected:** unknown (confidence: 30%)
```

**Solutions:**
1. Rephrase your question more specifically
2. Mention specific metric or dimension names
3. Use keywords like "trend", "compare", "show"

### Query Execution Errors

```
Error: Query failed: Column 'X' not found
```

**Solutions:**
1. Check available metrics: `list_metrics()`
2. Check available dimensions: `list_dimensions()`
3. Verify metric/dimension names are correct

### Unexpected Results

```
The AI picked the wrong metric/dimension
```

**Solutions:**
1. Be more specific in your question
2. Mention the exact metric name you want
3. Ask follow-up to clarify or correct

---

## 📈 Performance

### Query Execution Times

Typical execution times:

| Query Type | Avg Time | Example |
|------------|----------|---------|
| Simple Metric | 0.5-1.0s | "What is our MRR?" |
| Trend Analysis | 0.1-0.3s | "Show MRR trend" |
| Comparison | 0.05-0.15s | "Compare by segment" |
| Complex Multi-dim | 0.2-0.5s | "MRR by segment and month" |

### Query Caching

The semantic layer includes intelligent caching:

- **TTL**: 30 minutes default
- **Cache Hits**: Instant response (<10ms)
- **Backend**: In-memory (can use Redis for production)

Check cache performance:
```
cache_stats()
```

---

## 🔒 Security & Privacy

### Data Access

- The AI analyst operates through the semantic layer
- All queries go through defined metrics and dimensions
- No direct database access
- Respects all semantic layer filters and permissions

### Query Logging

All queries are logged for:
- Performance monitoring
- Intent detection improvement
- Error tracking
- Audit trail

Logs include:
- Query text
- Session ID
- Intent detected
- Execution time
- Success/failure status

### Session Isolation

Each session ID maintains isolated context:
- No cross-session data leakage
- Conversation history per session
- Configurable session retention

---

## 🚀 What's Next

### Future Enhancements

1. **Enhanced Intent Detection**
   - ML-based intent classification
   - Support for more query types
   - Better entity extraction

2. **Advanced Insights**
   - Anomaly detection
   - Predictive analytics
   - Causal analysis

3. **Visualization**
   - Auto-generate charts
   - Interactive dashboards
   - Export capabilities

4. **Collaboration**
   - Share insights
   - Annotate results
   - Build reports

---

## 📚 Related Documentation

- **[WrenAI Architecture](https://github.com/Canner/WrenAI)** - Original inspiration
- **[Semantic Layer Guide](./SEMANTIC_LAYER_GUIDE.md)** - Underlying data layer
- **[Temporal Dimensions](./TEMPORAL_DIMENSIONS_GUIDE.md)** - Time-series analysis
- **[MCP Protocol](https://modelcontextprotocol.io)** - Claude Desktop integration

---

## 💡 Tips & Tricks

### 1. Explore Available Data

Start by asking:
```
- "What metrics do you have?"
- "What dimensions are available?"
- "Show me canonical datasets"
```

### 2. Use Suggested Follow-ups

The AI provides smart suggestions - use them to explore deeper:
```
After "What is our MRR?", try suggested:
- "Show MRR trend over time"
- "Compare MRR by segment"
```

### 3. Build on Previous Queries

Take advantage of conversation context:
```
1. "What is our MRR?"
2. "Show the trend"  ← References "MRR" from previous query
3. "Compare by segment"  ← Still knows we're analyzing MRR
```

### 4. Combine Analysis Types

Mix and match:
```
- "Show MRR trend by customer segment"  ← Trend + Comparison
- "Compare cohort retention over time"  ← Cohort + Trend
```

---

**Built with inspiration from WrenAI** 🙏
**Powered by Claude Desktop MCP** ⚡
**Made for data-driven teams** 📊

---

*For issues or questions, create an issue in the repository*
