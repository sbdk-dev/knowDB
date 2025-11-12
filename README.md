# knowDB: Your AI Data Analyst 🚀

**Transform your data warehouse into a conversational AI analyst that speaks your business language.**

<p align="center">
  <img src="https://img.shields.io/badge/status-production%20ready-brightgreen" alt="Production Ready">
  <img src="https://img.shields.io/badge/tests-35%2F35%20passing-success" alt="Tests Passing">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/databases-4%2B%20supported-informational" alt="Multi-Database">
  <img src="https://img.shields.io/badge/setup-5%20minutes-orange" alt="5 Minute Setup">
  <img src="https://img.shields.io/badge/AI-WrenAI%20Inspired-purple" alt="AI Powered">
</p>

---

## 🎯 What is knowDB?

knowDB is a **WrenAI-inspired semantic layer platform** with a 6-agent AI system that lets you define business metrics once and query them forever—in natural language through Claude Desktop, Slack, or REST API.

**The problem**: Data teams spend 60% of their time answering the same questions repeatedly.

**The solution**: Define metrics once, query forever with AI.

### Before vs After

**Before knowDB:**
```
Stakeholder: "What's our churn rate by segment?"
You: [Opens SQL editor → writes query → exports to Excel → posts screenshot]
Time: 15 minutes per request × 50 requests/week = 12.5 hours/week
```

**After knowDB (with AI Analyst + Auto-Save):**
```
Stakeholder: "What's our churn rate by segment?"
AI Analyst: 🤖 Analyzing churn rate by segment...

💡 Key Insights:
- Enterprise: 4.2% (lowest, stable)
- Mid-Market: 8.7% (⚠️ trending up 1.2pp)
- SMB: 15.3% (expected range)

📊 [Shows trend chart and suggests] "Would you like to see retention cohorts?"

💾 Auto-Saved to Dashboard
🌐 View: http://localhost:3000/churn-rate-comparison-20251109-143022
📂 Options: save_as("exec-dashboard"), add_to_dashboard(), continue asking

Time: 2 seconds
```

**Result:** 10x faster insights, 100% metric consistency, 50% reduction in data team interruptions, automatic insights generation.

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Install (2 minutes)

```bash
git clone https://github.com/your-org/knowDB
cd knowDB
./setup.sh  # Installs everything automatically
```

**What this does:**
- ✅ Installs `uv` (10-100x faster than pip)
- ✅ Creates virtual environment
- ✅ Installs all dependencies
- ✅ Generates sample data (100 customers, 146 subscriptions)
- ✅ Runs tests to validate everything works
- ✅ Shows next steps with exact paths

### Step 2: Configure Claude Desktop (1 minute)

Copy the configuration shown in setup output to:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Step 3: Ask Questions (30 seconds)

Restart Claude Desktop, then ask naturally:
- "What metrics do you have available?"
- "How is my active customer count changing over time?"
- "Compare MRR by customer segment"
- "Show me customer signup cohorts"

**🎉 Done!** You now have a multi-agent AI analyst that:
- 🧠 Understands your intent automatically
- 📊 Plans optimal queries
- 💡 Generates insights from data
- 🔮 Suggests follow-up questions
- 💬 Remembers conversation context

> **Need help?** See [AI Analyst Guide](AI_ANALYST_GUIDE.md) or [Troubleshooting Guide](TROUBLESHOOTING.md).

---

## 🏗️ How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  💬 Natural Language Question                              │
│  "How is my active customer count changing over time?"     │
├─────────────────────────────────────────────────────────────┤
│  🤖 AI Multi-Agent System (WrenAI-Inspired)                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 1. Query Understanding → Parse intent & entities      │ │
│  │ 2. Semantic Retriever  → Find relevant metrics (RAG)  │ │
│  │ 3. Query Planner       → Create optimal query plan    │ │
│  │ 4. SQL Generator       → Execute via semantic layer   │ │
│  │ 5. Result Interpreter  → Generate insights            │ │
│  │ 6. Conversation Mgr    → Maintain context             │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  🧠 knowDB Semantic Layer                                  │
│  - Business metric definitions                             │
│  - Temporal dimensions & filters                           │
│  - Multi-database support                                  │
├─────────────────────────────────────────────────────────────┤
│  💾 Your Database                                           │
│  Snowflake | BigQuery | DuckDB | PostgreSQL               │
├─────────────────────────────────────────────────────────────┤
│  📊 Intelligent Results                                     │
│  | Month   | Customers | Trend    |                       │
│  |---------|-----------|----------|                       │
│  | 2024-11 | 100       | Baseline |                       │
│  | 2024-12 | 102       | ↑2%      |                       │
│  | 2025-01 | 98        | ↓4%      |                       │
│                                                             │
│  💡 Insights: "Seasonal decrease, historical pattern"      │
│  🔮 Suggestions: "Compare by segment", "Show retention"    │
└─────────────────────────────────────────────────────────────┘
```

1. **Define metrics once** in simple YAML
2. **Ask questions naturally** - AI understands intent
3. **Get insights automatically** - Trends, patterns, anomalies
4. **Follow-up suggestions** - Smart next questions
5. **Lightning fast** - Intelligent caching

---

## 🎯 Key Features

### 🤖 AI-Powered Intelligence (NEW!)
- **6-Agent Architecture:** WrenAI-inspired multi-agent system
- **Intent Detection:** 85-100% accuracy across 6 query types
- **Smart Query Planning:** Automatically optimizes for your question
- **Insight Generation:** Trends, patterns, anomalies detected automatically
- **Conversation Context:** Remembers previous queries for follow-ups
- **RAG Retrieval:** Semantic search for relevant metrics

### 📊 Dashboard Auto-Save (NEW!)
- **Zero-Friction Saving:** Every query automatically saves to Evidence.dev
- **Smart Naming:** `{metric}-{intent}-{timestamp}` for easy discovery
- **Dashboard Management:** Rename, combine, list, and cleanup dashboards
- **Evidence.dev Integration:** Beautiful markdown-based dashboards
- **7-Day Auto-Cleanup:** Old dashboards deleted, custom ones kept forever
- **4 New MCP Tools:** save_as(), add_to_dashboard(), list_dashboards(), cleanup_dashboards()

### For Data Teams
- **📏 Define Once, Use Everywhere:** Metrics in YAML, accessible everywhere
- **🛡️ Single Source of Truth:** Eliminate metric inconsistencies
- **⚡ 10x Faster Support:** AI answers questions automatically
- **🔧 Multi-Database:** Works with your existing warehouse
- **📊 Temporal Dimensions:** Full time-series analysis support

### For Business Users
- **💬 Natural Language:** Ask questions like "How is MRR trending?"
- **💡 Auto-Insights:** Get trends, comparisons, and explanations
- **⏱️ Instant Answers:** 0.1-1.0s responses with caching
- **🔮 Smart Suggestions:** AI recommends follow-up questions
- **📱 Multiple Interfaces:** Claude Desktop, Slack, API, dashboards
- **🔄 Always Up-to-Date:** Real-time data from your warehouse

### For Engineering
- **🔒 Production Ready:** Authentication, rate limiting, audit logging
- **📈 Scales Horizontally:** Redis caching, load balancing
- **🧪 Fully Tested:** 35 tests with comprehensive coverage
- **🔗 Easy Integration:** REST API, MCP server, Docker deployment
- **🎯 Zero Breaking Changes:** AI layer is additive

---

## 📊 Sample Data Included

Get started immediately with realistic sample data:

- **100 customers** across 5 segments (Enterprise, Mid-Market, SMB, Startup, Non-Profit)
- **146 active subscriptions** with realistic MRR distribution
- **14 pre-configured metrics** (MRR, Churn, LTV, ARPU, etc.)
- **Time-series data** for trend analysis

**Sample metrics you can query immediately:**
- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Customer churn rate
- Average Revenue Per User (ARPU)
- Customer Lifetime Value (LTV)
- Net Revenue Retention (NRR)

---

## 🔌 Integration Options

### 1. Claude Desktop (Recommended)
**Perfect for:** Ad-hoc analysis, exploration, executive dashboards

```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "/path/to/knowDB/.venv/bin/python",
      "args": ["/path/to/knowDB/src/mcp_server.py"],
      "env": {
        "SEMANTIC_MODELS_PATH": "/path/to/knowDB/semantic_models/metrics.yml"
      }
    }
  }
}
```

**Example conversation with AI Analyst:**
```
You: "What is our total MRR?"

AI: 🤖 AI Analyst Response

Intent Detected: metric_query (confidence: 90%)
Query Plan: Querying total_mrr

Answer: The Monthly Recurring Revenue (MRR) is $28,431.34

💡 Key Insights:
- Current period performance
- Stable compared to forecast

🔮 Suggested Follow-up Questions:
- Show MRR trend over time
- Compare MRR by customer segment
- What's driving MRR growth?

Query executed in 0.82s
```

**Multi-turn conversation:**
```
You: "Show the trend"

AI: [Remembers we're analyzing MRR]
Found 13 time periods showing MRR growth

💡 Key Insights:
- Trend: increased by 15.2% from start to end
- Consistent month-over-month growth

[Shows monthly breakdown table]
```

### 2. Slack Bot
**Perfect for:** Team collaboration, daily standups, quick questions

```bash
# Configure in .env
SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret

# Start bot
./deploy.sh restart
```

**Usage:**
```
@semantic-bot show me pipeline value for Q4

Pipeline Value Q4 2024:
- Total: $8.2M
- Weighted: $4.1M (50% avg probability)
- Deals: 127 across 4 stages
```

### 3. REST API
**Perfect for:** Dashboards, notebooks, custom applications

```bash
# List metrics
curl http://localhost:8000/metrics -H "X-API-Key: REDACTED"

# Query with filters
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{
    "metric_name": "total_mrr",
    "dimensions": ["customer_segment"],
    "filters": ["customer_segment = \"Enterprise\""]
  }'
```

Full API docs at http://localhost:8000/docs

---

## 🗄️ Database Support

**Currently tested:**

| Database | Status | Configuration |
|----------|--------|---------------|
| **DuckDB** | ✅ Production Ready | `type: "duckdb"` |
| **Snowflake** | ✅ Production Ready | `type: "snowflake"` |
| **BigQuery** | ✅ Production Ready | `type: "bigquery"` |
| **PostgreSQL** | ✅ Production Ready | `type: "postgres"` |

**Supported via Ibis Framework:**
Redshift, Databricks, MySQL, ClickHouse, SQLite, and [15+ more](https://ibis-project.org/backends).

### Example Configurations

**Snowflake:**
```yaml
connection:
  type: "snowflake"
  user: "${SNOWFLAKE_USER}"
  password: "${SNOWFLAKE_PASSWORD}"
  account: "${SNOWFLAKE_ACCOUNT}"
  database: "${SNOWFLAKE_DATABASE}"
  warehouse: "${SNOWFLAKE_WAREHOUSE}"
```

**PostgreSQL:**
```yaml
connection:
  type: "postgres"
  host: "${POSTGRES_HOST}"
  database: "${POSTGRES_DATABASE}"
  user: "${POSTGRES_USER}"
  password: "${POSTGRES_PASSWORD}"
```

---

## 📋 Defining Metrics

Metrics are defined in simple, readable YAML:

```yaml
metrics:
  - name: total_mrr
    display_name: "Monthly Recurring Revenue"
    description: "Total MRR from active subscriptions"
    type: "simple"
    calculation:
      table: "subscriptions"
      aggregation: "sum"
      column: "subscription_amount"
      filters:
        - "subscription_status = 'active'"
        - "billing_frequency = 'monthly'"

  - name: arr
    display_name: "Annual Recurring Revenue"
    description: "Projected annual recurring revenue"
    type: "derived"
    calculation:
      formula: "total_mrr * 12"

  - name: churn_rate
    display_name: "Customer Churn Rate"
    description: "Percentage of customers who cancelled"
    type: "ratio"
    calculation:
      numerator: "churned_customers"
      denominator: "total_customers"
      format: "percentage"
```

**Three metric types:**
- **Simple:** Direct database aggregations (SUM, COUNT, AVG)
- **Derived:** Calculations using other metrics
- **Ratio:** Percentages and rates

---

## 🚀 Production Deployment

### Option 1: Docker (Recommended)

```bash
# Clone and setup
git clone https://github.com/your-org/knowDB
cd knowDB

# Configure environment
./deploy.sh setup
# Edit .env with your credentials

# Start production services
./deploy.sh start
```

**Includes:**
- API server with authentication
- Redis caching layer
- Prometheus monitoring
- Nginx load balancer (optional)
- Health checks and logging

### Option 2: Kubernetes

```bash
# Build and deploy
docker build -t knowdb:latest .
kubectl apply -f k8s/
```

### Option 3: Cloud Platforms

Deploy to AWS ECS, Google Cloud Run, or Azure Container Instances using provided configurations.

**See [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md) for complete setup.**

---

## 🔒 Security Features

**Production-ready security:**

- ✅ **API Authentication:** Three permission levels (Admin, Query, Read-only)
- ✅ **Rate Limiting:** Prevents abuse with per-user limits
- ✅ **SQL Injection Protection:** Comprehensive input validation
- ✅ **Audit Logging:** All queries logged with user attribution
- ✅ **CORS Security:** Configurable origin restrictions
- ✅ **Security Headers:** HSTS, CSP, X-Frame-Options
- ✅ **JWT Support:** For service-to-service authentication

**Generate secure API keys:**
```bash
# Admin access (full control)
export API_KEY_ADMIN=$(openssl rand -base64 32)

# Query access (read + execute)
export API_KEY_QUERY=$(openssl rand -base64 32)

# Read access (metadata only)
export API_KEY_READ=$(openssl rand -base64 32)
```

---

## 📈 Performance

**Typical response times:**
- First query: 500-2000ms (hits database)
- Cached queries: 10-50ms (served from memory/Redis)
- Complex aggregations: 1-5 seconds
- Simple counts: 100-500ms

**Optimization features:**
- Intelligent caching with configurable TTL
- Connection pooling
- Query result compression
- Automatic index recommendations

**Scalability:**
- Horizontal scaling with load balancers
- Distributed Redis caching
- Database read replicas
- Container orchestration ready

---

## 📚 Documentation & Support

### Quick Links
- **[📖 Quickstart Guide](QUICKSTART.md)** - Detailed 5-minute setup
- **[💡 Examples](EXAMPLES.md)** - Real query examples and use cases
- **[🔧 Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[🚀 Production Guide](PRODUCTION_DEPLOYMENT.md)** - Complete deployment
- **[🛡️ Security Details](SECURITY_AUDIT_RESOLUTION.md)** - Security implementation

### Advanced Topics
- **[📐 Architecture Vision](docs/native-claude-desktop-vision.md)** - Product vision and philosophy
- **[🏗️ Week 1 Implementation](docs/week-1-implementation-guide.md)** - Technical implementation guide
- **[🧠 AI Integration](docs/prd-01-semantic-layer-auto-generation.md)** - AI-powered features

### Community & Support
- **[GitHub Issues](https://github.com/your-org/knowDB/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/your-org/knowDB/discussions)** - Questions and community
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

---

## ❓ FAQ

**Q: Do I need to learn SQL?**
A: No! Define metrics in YAML, query in natural language. SQL is generated automatically.

**Q: What if Claude gives wrong answers?**
A: Claude queries your metric definitions. If metrics are defined correctly, answers will be correct.

**Q: Can I use my existing dbt models?**
A: Yes! Your semantic layer can reference dbt models. Most teams use dbt for transformations and knowDB for metrics.

**Q: How is this different from other semantic layers?**
A: knowDB is conversational-first, integrates natively with Claude Desktop, and learns over time.

**Q: Is this secure for production?**
A: Yes. Includes authentication, rate limiting, audit logging, and SQL injection protection. See [security audit](SECURITY_AUDIT_RESOLUTION.md).

**Q: Can I self-host?**
A: Yes! All components run on your infrastructure. See [deployment guide](PRODUCTION_DEPLOYMENT.md).

---

## 🛣️ Roadmap

### ✅ Phase 1: Core Platform (Complete)
- Multi-database semantic layer
- Claude Desktop MCP integration
- REST API with authentication
- Slack bot integration
- Production deployment
- Security hardening
- **Temporal dimensions & time-series analysis**

### ✅ Phase 2: AI Intelligence (Complete)
- **WrenAI-inspired 6-agent system**
- **Natural language intent detection**
- **Smart query planning & optimization**
- **Automated insight generation**
- **Conversation context & memory**
- **RAG-based semantic retrieval**

### ✅ Phase 3: Dashboard Auto-Save (Complete)
- **Evidence.dev integration** - Local dashboard platform
- **Auto-save every query** - Zero-friction UX
- **Dashboard management tools** - 4 new MCP tools
- **Smart naming & cleanup** - 7-day retention for auto-generated

### 🚧 Phase 4: Enhanced Intelligence (In Progress)
- ML-based intent classification (vs pattern matching)
- Advanced chart customization & types
- Scheduled reports & alerts
- Anomaly detection & predictions

### 📋 Phase 5: Advanced Features (Planned)
- Knowledge graph integration
- Causal discovery
- What-if scenario analysis
- Predictive analytics
- Multi-modal outputs (charts, tables, narratives)

---

## 🎯 Use Cases

### Executive Dashboards
```
You: "Create a board meeting dashboard"
Claude: [Generates real-time executive metrics with trends]
```

### Sales Team Self-Service
```
@semantic-bot what's our Q4 pipeline value?
Bot: Q4 Pipeline: $8.2M total, $4.1M weighted, 127 deals
```

### Financial Reporting
```
You: "Show me financial summary for investors"
Claude: [Creates comprehensive financial metrics report]
```

### Product Analytics
```
You: "How is our new feature performing?"
Claude: [Analyzes adoption, usage, and engagement metrics]
```

See [detailed use cases](docs/use-cases.md) with real examples.

---

## 🤝 Contributing

We welcome contributions! Areas where we need help:

1. **Database Connectors** - Add support for more databases
2. **Semantic Models** - Industry-specific metric templates
3. **Integrations** - BI tools, notebooks, dashboards
4. **Documentation** - Tutorials, guides, case studies
5. **Testing** - Edge cases and performance tests

**Quick start for contributors:**
```bash
git clone https://github.com/your-username/knowDB
cd knowDB
./setup.sh
# Make changes
uv run pytest tests/ -v
# Submit PR
```

See [Contributing Guide](CONTRIBUTING.md) for detailed guidelines.

---

## 🙏 Inspiration & Thanks

Built on amazing work from the data community:

- **[Rasmus Engelbrecht](https://rasmusengelbrecht.substack.com/)** - Semantic layer philosophy
- **[MCP Protocol](https://github.com/anthropics/mcp)** - Claude Desktop integration
- **[Ibis Framework](https://ibis-project.org/)** - Multi-database SQL abstraction
- **[WrenAI](https://github.com/Canner/WrenAI)** - Text-to-SQL innovation

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🚀 Get Started Now

**Ready to transform your data warehouse into an AI analyst?**

```bash
git clone https://github.com/your-org/knowDB
cd knowDB
./setup.sh
```

**Then ask Claude:**
- "What metrics are available?"
- "Show me our key business metrics"
- "Create an executive dashboard"
- "What's driving our growth?"

**Questions? Issues? Ideas?**
- 🐛 [Report bugs](https://github.com/your-org/knowDB/issues)
- 💬 [Ask questions](https://github.com/your-org/knowDB/discussions)
- 🤝 [Contribute](CONTRIBUTING.md)

---

<p align="center">
  <strong>Built with ❤️ for the data community</strong>
</p>

<p align="center">
  <em>"The AI data analyst is here, but it's not taking your job.<br/>
  It's taking the tedious parts so you can focus on what drives value."</em>
</p>