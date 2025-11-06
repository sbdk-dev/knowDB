# Quick Start Guide
## Get Running in 5 Minutes

This guide will get you up and running with the Semantic Layer MCP Server in just a few minutes.

## Prerequisites

- Python 3.11 or higher
- Claude Desktop app installed
- Basic understanding of your data warehouse

## Step 1: Clone and Setup (2 minutes)

```bash
# Clone the repository
cd knowDB

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Generate Sample Data (1 minute)

```bash
# Generate sample e-commerce data in DuckDB
python create_sample_data.py
```

You should see output like:
```
✅ Database created successfully!
   Location: data/sample.duckdb

📊 Data Summary:
   - Customers: 100
   - Subscriptions: 146
   - Monthly Snapshots: 39

📈 Sample Metrics:
   - Total MRR: $48,670.00
   - Active Subscriptions: 127
```

## Step 3: Test the Semantic Layer (30 seconds)

```bash
# Test that everything works
python src/semantic_layer.py
```

You should see:
```
📊 Testing Semantic Layer
============================================================
1. Available Metrics:
   - total_mrr: Monthly Recurring Revenue (MRR)
   - arr: Annual Recurring Revenue (ARR)
   ...
✅ Semantic layer test completed successfully!
```

## Step 4: Configure Claude Desktop (1 minute)

Edit your Claude Desktop MCP settings file:

**On macOS:**
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**On Windows:**
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

Add this configuration:

```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "/FULL/PATH/TO/knowDB/venv/bin/python",
      "args": [
        "/FULL/PATH/TO/knowDB/src/mcp_server.py"
      ],
      "env": {
        "SEMANTIC_MODELS_PATH": "/FULL/PATH/TO/knowDB/semantic_models/metrics.yml"
      }
    }
  }
}
```

**Important:** Replace `/FULL/PATH/TO/knowDB` with the actual absolute path to your knowDB directory.

To find your absolute path:
```bash
# Run this in your knowDB directory
pwd
```

## Step 5: Restart Claude Desktop (30 seconds)

1. Quit Claude Desktop completely
2. Reopen Claude Desktop
3. Look for the 🔌 icon indicating MCP servers are connected

## Step 6: Start Querying! (30 seconds)

In Claude Desktop, try these queries:

```
"What metrics are available?"

"Show me total MRR"

"Break down MRR by customer segment"

"Show me active customers by country"

"What's the churn rate?"
```

## Verify It's Working

You'll know it's working when:

1. Claude lists available metrics when you ask
2. Claude shows actual numbers from your data
3. You see formatted tables with results
4. You see the generated SQL at the bottom of responses

## Example Conversation

**You:** "What metrics are available?"

**Claude:** Here are the available metrics:
- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Total Customers
- Active Customers
- Churn Rate
...

**You:** "Show me MRR by customer segment"

**Claude:**

| customer_segment | total_mrr |
|-----------------|-----------|
| Enterprise      | $24,741.53|
| Mid-Market      | $18,464.34|
| SMB             | $5,464.12 |

Total rows: 3

Generated SQL:
```sql
SELECT customer_segment, SUM(subscription_amount) as total_mrr
FROM subscriptions
JOIN customers ON subscriptions.customer_id = customers.customer_id
WHERE subscription_status = 'active'
GROUP BY customer_segment
```

## Troubleshooting

### Claude Desktop doesn't show the 🔌 icon

1. Check that the paths in `claude_desktop_config.json` are absolute (not relative)
2. Check that Python path is correct: `/path/to/venv/bin/python`
3. Check logs in Claude Desktop (Help → View Logs)

### "Module not found" errors

Make sure you're using the Python from your virtual environment:
```bash
# Test this works:
/path/to/knowDB/venv/bin/python -c "import mcp; import ibis; print('OK')"
```

### "Configuration file not found" error

Make sure `SEMANTIC_MODELS_PATH` points to the absolute path of `metrics.yml`

### Tests failing

```bash
# Re-run setup
python create_sample_data.py

# Run tests
python -m pytest tests/ -v
```

## Next Steps

Once you have it running:

1. **Add Your Own Data:** Edit `semantic_models/metrics.yml` to point to your data warehouse
2. **Define Your Metrics:** Add your business metrics to the YAML file
3. **Explore Advanced Features:** Check out `docs/` for advanced usage
4. **Share with Team:** Everyone with Claude Desktop can use the same metrics

## Using Your Own Data

To connect to your own data warehouse:

### Option 1: Keep Using DuckDB

```yaml
connection:
  type: "duckdb"
  database: "/path/to/your/database.duckdb"
```

### Option 2: Connect to Snowflake

```yaml
connection:
  type: "snowflake"
  user: "${SNOWFLAKE_USER}"
  password: "${SNOWFLAKE_PASSWORD}"
  account: "${SNOWFLAKE_ACCOUNT}"
  database: "${SNOWFLAKE_DATABASE}"
  warehouse: "${SNOWFLAKE_WAREHOUSE}"
  schema: "public"
```

Set environment variables in `.env`:
```bash
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
...
```

### Option 3: Connect to BigQuery

```yaml
connection:
  type: "bigquery"
  project_id: "${GCP_PROJECT_ID}"
  dataset_id: "${BQ_DATASET_ID}"
```

### Option 4: Connect to PostgreSQL

```yaml
connection:
  type: "postgres"
  host: "${POSTGRES_HOST}"
  port: 5432
  database: "${POSTGRES_DATABASE}"
  user: "${POSTGRES_USER}"
  password: "${POSTGRES_PASSWORD}"
```

## Common Use Cases

### Business Analytics
```
"What's our MRR trend over time?"
"Show me customer acquisition by segment"
"Calculate customer lifetime value"
```

### Product Metrics
```
"What's our user engagement rate?"
"Show feature adoption by customer segment"
"What's the conversion funnel?"
```

### Financial Reporting
```
"Show revenue by product tier"
"What's our gross retention rate?"
"Calculate ARR by region"
```

## Getting Help

- 📖 **Full Documentation:** See `docs/` directory
- 🐛 **Issues:** Open an issue on GitHub
- 💬 **Discussions:** Join our community discussions
- 📧 **Support:** Check README for contact information

## What's Next?

After you're comfortable with basic queries:

1. **Week 1:** Master the semantic layer - define all your key metrics
2. **Month 1:** Add AgentDB for learning and memory (Phase 2)
3. **Month 3:** Add knowledge graphs for optimization (Phase 3)

See `docs/week-1-implementation-guide.md` for the complete roadmap.

---

🎉 **Congratulations!** You now have an AI-powered data analyst that understands your business metrics and can answer questions in plain English.
