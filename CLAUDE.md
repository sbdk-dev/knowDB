# knowDB Project Context for Claude

## Project Overview

knowDB is a **WrenAI-inspired AI data analyst** with a multi-agent architecture that enables natural language business intelligence queries through Claude Desktop.

### Current Status: ✅ PRODUCTION READY

- **35/35 tests passing** (24 core + 11 temporal)
- **Multi-agent AI system** fully implemented
- **Temporal dimensions** for time-series analysis
- **Complete documentation** for users and developers

## Core Architecture

### 1. Semantic Layer (`src/semantic_layer.py`)
- Multi-database support (DuckDB, Snowflake, BigQuery, PostgreSQL)
- Metric definitions in YAML (`semantic_models/metrics.yml`)
- Dimension support (categorical + temporal)
- Query caching with Redis
- Ibis framework for SQL generation

### 2. AI Agent Flow (`src/ai_agent_flow.py`) 🆕
**6-Agent Multi-Agent System:**

1. **Query Understanding Agent** - Parses natural language intent
2. **Semantic Retriever Agent** - RAG-based metric/dimension retrieval
3. **Query Planner Agent** - Creates optimal semantic query plans
4. **SQL Generator Agent** - Executes via semantic layer
5. **Result Interpreter Agent** - Generates insights and narratives
6. **Conversation Manager** - Orchestrates flow and maintains context

**Supported Intent Types:**
- `metric_query` - "What is our MRR?"
- `trend_analysis` - "How is MRR changing over time?"
- `comparison` - "Compare MRR by segment"
- `cohort_analysis` - "Show signup cohorts"
- `top_n` - "Top 10 customers"
- `filtering` - "Only Enterprise customers"

### 3. MCP Server (`src/mcp_server.py`)
**13 Tools exposed to Claude Desktop:**

**Core Tools (9):**
- `list_metrics` - List all available metrics
- `query_metric` - Query metrics with dimensions/filters
- `explain_metric` - Show how metrics are calculated
- `list_dimensions` - List available dimensions
- `get_dimension_values` - Get unique values for dimensions
- `list_canonical_datasets` - Pre-defined analysis templates
- `query_canonical_dataset` - Query canonical datasets
- `cache_stats` - Query cache performance
- `clear_cache` - Clear cached results

**AI Tools (1):**
- **`ask_ai_analyst`** 🆕 - Natural language AI analyst interface

**Dashboard Tools (4):** 🆕
- **`save_as("name")`** - Rename last dashboard to keep it permanently
- **`add_to_dashboard("name")`** - Add current chart to existing dashboard
- **`list_dashboards()`** - Browse all Evidence.dev dashboards
- **`cleanup_dashboards()`** - Remove old auto-generated dashboards

## Project Structure

```
knowDB/
├── src/
│   ├── semantic_layer.py           # Core semantic layer
│   ├── ai_agent_flow.py            # 🆕 AI multi-agent system
│   ├── dashboard_manager.py        # 🆕 Auto-save dashboard manager
│   ├── mcp_server.py               # MCP server with AI + dashboards
│   ├── query_cache.py              # Redis/memory caching
│   ├── safe_expression_parser.py   # Secure formula evaluation
│   └── [other modules]
├── dashboards/                      # 🆕 Evidence.dev dashboards
│   ├── pages/                      # Auto-generated dashboard markdown
│   ├── package.json                # Evidence.dev configuration
│   └── sources/                    # Database connections
│       └── knowdb.yaml             # DuckDB connection
├── semantic_models/
│   └── metrics.yml                 # Metric & dimension definitions
├── tests/
│   ├── test_semantic_layer.py      # Core tests (24)
│   └── [other test files]
├── data/
│   └── sample.duckdb               # Sample database
├── AI_ANALYST_GUIDE.md             # 🆕 User guide
├── AI_ANALYST_IMPLEMENTATION_SUMMARY.md  # 🆕 Technical docs
├── INTEGRATION_COMPLETE.md         # 🆕 Dashboard integration summary
└── README.md                        # Updated with AI + dashboard features
```

## Key Implementation Details

### Temporal Dimensions
All temporal dimensions use SQL expressions with `{{ Table }}` placeholders:

```yaml
dimensions:
  - name: snapshot_month
    type: temporal
    sql: "strftime('%Y-%m', {{ Table }}.month)"
    table: monthly_mrr_snapshots
```

The semantic layer's `_resolve_dimension_expression()` method handles:
- Placeholder replacement
- strftime() function parsing
- Ibis expression generation

### AI Agent Communication

Agents communicate via dataclasses:
```python
@dataclass
class QueryUnderstanding:
    raw_query: str
    intent: QueryIntent
    entities: Dict[str, List[str]]
    confidence: float

@dataclass
class SemanticPlan:
    metrics: List[str]
    dimensions: List[str]
    filters: List[str]
    explanation: str
```

### Conversation Context

Sessions maintain:
- Last 10 queries
- Last used metrics/dimensions
- Previous intent
- Timestamp

### Dashboard Auto-Save 🆕

Every successful `ask_ai_analyst` query automatically:
1. **Saves to Evidence.dev** - Creates markdown dashboard with chart
2. **Smart Naming** - `{metric}-{intent}-{timestamp}` pattern
3. **Returns URL** - Clickable link to view dashboard
4. **Stores Context** - Enables `add_to_dashboard()` tool

**Dashboard Lifecycle:**
- **Auto-generated** - Timestamp in name, 7-day retention
- **Custom** - Renamed with `save_as()`, kept permanently
- **Combined** - Multiple queries in one dashboard via `add_to_dashboard()`
- **Cleanup** - `cleanup_dashboards()` removes old auto-generated ones

**Evidence.dev Integration:**
- Markdown-based dashboards
- SQL queries embedded
- LineChart, BarChart, DataTable components
- Real-time data from DuckDB
- Viewable at `http://localhost:3000`

## Development Commands

```bash
# Activate environment
source .venv/bin/activate

# Run tests
uv run pytest tests/ -v

# Run AI agent standalone
python src/ai_agent_flow.py

# Start MCP server (for testing)
python src/mcp_server.py

# Start Evidence.dev dashboard server 🆕
cd dashboards
npm install
npm run dev
# Opens http://localhost:3000

# Generate sample data
python create_sample_data.py
```

## Common Tasks

### Adding a New Metric

1. Edit `semantic_models/metrics.yml`
2. Add metric definition:
```yaml
- name: new_metric
  display_name: "New Metric"
  type: "simple"
  calculation:
    table: "table_name"
    aggregation: "sum"
    column: "column_name"
```
3. Restart MCP server
4. Test: "What is new_metric?"

### Adding a New Temporal Dimension

1. Edit `semantic_models/metrics.yml`
2. Add dimension with SQL expression:
```yaml
- name: new_time_dim
  type: temporal
  table: "source_table"
  column: "date_column"
  sql: "strftime('%Y-%m', {{ Table }}.date_column)"
```
3. Dimension will auto-load via `_load_temporal_dimensions()`

### Extending AI Agents

**Add new intent type:**
```python
# In ai_agent_flow.py
class QueryIntent(Enum):
    NEW_INTENT = "new_intent"

# Add patterns in QueryUnderstandingAgent
self.intent_patterns = {
    QueryIntent.NEW_INTENT: [
        r'\b(keyword1|keyword2)\b',
    ],
}

# Add planning logic in QueryPlannerAgent
def _plan_new_intent(self, understanding, retrieval):
    # Implementation
```

## Known Issues & Limitations

1. **Complex Multi-Dimensional Derived Metrics**
   - Issue: Column name collisions with multiple joins
   - Workaround: Query derived metrics separately
   - Priority: Medium

2. **Pattern-Based Intent Detection**
   - Current: Regex patterns
   - Future: ML-based classification
   - Priority: Low (current approach works well)

3. **DuckDB Locking**
   - Issue: Only one connection at a time
   - Solution: Kill stale processes or use read-only mode
   - Command: `lsof data/sample.duckdb`

## Performance Benchmarks

- Simple queries: 0.5-1.0s
- Trend analysis: 0.1-0.3s
- Comparisons: 0.05-0.15s
- Cache hits: <10ms
- Intent detection: <10ms
- Entity extraction: <50ms

## Testing

**Run all tests:**
```bash
uv run pytest tests/ -v
```

**Test AI agent:**
```bash
python src/ai_agent_flow.py
```

**Test MCP integration:**
1. Configure Claude Desktop
2. Restart Claude
3. Ask: "What metrics do you have?"

## Documentation

### Core Documentation
- **User Guide**: `AI_ANALYST_GUIDE.md` - How to use the AI analyst
- **Technical**: `AI_ANALYST_IMPLEMENTATION_SUMMARY.md` - Architecture details
- **Temporal**: `TEMPORAL_DIMENSIONS_GUIDE.md` - Time-series analysis
- **Security**: `SECURITY_AUDIT_RESOLUTION.md` - Security implementation

### Dashboard Documentation 🆕
- **Integration Guide**: `INTEGRATION_COMPLETE.md` - Dashboard integration summary
- **Implementation**: `IMPLEMENTATION_COMPLETE.md` - Complete feature overview
- **Auto-Save Guide**: `AUTO_SAVE_INTEGRATION_GUIDE.md` - Step-by-step integration
- **UX Design**: `DASHBOARD_SAVE_UX.md` - UX design rationale
- **Strategy**: `VISUALIZATION_STRATEGY.md` - Overall visualization roadmap

## Integration with Claude Desktop

**Configuration location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Required configuration:**
```json
{
  "mcpServers": {
    "knowdb-ai-analyst": {
      "command": "/path/to/knowDB/.venv/bin/python",
      "args": ["/path/to/knowDB/src/mcp_server.py"],
      "env": {
        "SEMANTIC_MODELS_PATH": "/path/to/knowDB/semantic_models/metrics.yml",
        "DATABASE_PATH": "/path/to/knowDB/data/sample.duckdb"
      }
    }
  }
}
```

## Next Development Priorities

### Phase 3 (In Progress)
- [x] **Dashboard auto-save** - Every query saves to Evidence.dev ✅
- [x] **Evidence.dev integration** - Local dashboard platform ✅
- [x] **Dashboard management** - 4 new MCP tools ✅
- [ ] ML-based intent classification
- [ ] Enhanced date parsing (specific dates, ranges)
- [ ] Better complex derived metric handling
- [ ] Advanced chart customization

### Phase 4 (1-3 months)
- [ ] Export capabilities (CSV, PDF)
- [ ] Scheduled reports
- [ ] Alert system for KPI thresholds
- [ ] Predictive analytics
- [ ] What-if scenarios

## Inspiration

Built with inspiration from:
- **WrenAI** - Multi-agent architecture for Text-to-SQL
- **Semantic Layer Philosophy** - Single source of truth for metrics
- **MCP Protocol** - Claude Desktop integration
- **RAG Patterns** - Retrieval-augmented generation

## Key Principles

1. **Evidence > Assumptions** - Always test, never guess
2. **Code > Documentation** - Working code is the truth
3. **Efficiency > Verbosity** - Fast iteration, clear communication
4. **Zero Breaking Changes** - AI layer is additive, not destructive
5. **Production Quality** - Tests, error handling, logging, security

---

**Last Updated:** 2025-11-09
**Version:** 2.1 (AI Analyst + Dashboard Auto-Save)
**Status:** Production Ready ✅
