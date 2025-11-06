# Practical Implementation Guide: Build Your MCP Semantic Layer (Week 1)

**Version:** 1.0
**Date:** 2025-11-06
**Goal:** Get Claude Desktop answering data questions by Friday

---

## Overview: What We're Building This Week

```
Claude Desktop (conversation interface)
    ↓ MCP Protocol
Semantic Layer MCP Server (Python script you'll write)
    ↓ Ibis (multi-database connector)
DuckDB / Your Warehouse
```

**End result:** Ask Claude "What's our MRR?" and get instant answers.

---

## Prerequisites

### Required
- ✅ Claude Desktop installed
- ✅ Python 3.10+ installed
- ✅ Basic familiarity with Python
- ✅ A data warehouse (we'll start with DuckDB for simplicity)

### Optional (for later)
- dbt project (we'll help you create one)
- Existing semantic layer definitions
- Production warehouse (Snowflake/BigQuery)

---

## Day 1: Setup Development Environment (2 hours)

### Step 1: Create Project Structure

```bash
# Create project directory
mkdir semantic-layer-mcp
cd semantic-layer-mcp

# Create directory structure
mkdir -p {src,data,semantic_models,tests}

# Project structure:
# semantic-layer-mcp/
# ├── src/
# │   └── mcp_server.py          # The MCP server
# ├── data/
# │   └── sample.duckdb          # Sample database
# ├── semantic_models/
# │   └── metrics.yml            # Metric definitions
# ├── tests/
# │   └── test_queries.py        # Test queries
# ├── requirements.txt           # Python dependencies
# └── README.md                  # Setup instructions
```

### Step 2: Install Dependencies

```bash
# Create requirements.txt
cat > requirements.txt <<EOF
# MCP SDK
mcp>=0.9.0

# Data libraries
ibis-framework[duckdb]>=9.0.0
pandas>=2.0.0
pyyaml>=6.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0
EOF

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Create Sample Database

```python
# create_sample_data.py

import duckdb
import pandas as pd
from datetime import datetime, timedelta

# Create connection
conn = duckdb.connect('data/sample.duckdb')

# Generate sample subscription data
def generate_sample_data():
    # Create customers table
    customers = pd.DataFrame({
        'customer_id': range(1, 101),
        'email': [f'customer{i}@example.com' for i in range(1, 101)],
        'customer_segment': ['Enterprise'] * 20 + ['Mid-Market'] * 30 + ['SMB'] * 50,
        'signup_date': pd.date_range(start='2023-01-01', periods=100, freq='3D')
    })

    # Create subscriptions table
    subscriptions = []
    for customer_id in range(1, 101):
        # Each customer has 1-3 subscriptions
        for _ in range(1 + (customer_id % 3)):
            subscriptions.append({
                'subscription_id': len(subscriptions) + 1,
                'customer_id': customer_id,
                'subscription_amount': 50 + (customer_id % 10) * 100,
                'subscription_status': 'active' if customer_id % 10 != 0 else 'cancelled',
                'billing_frequency': 'monthly',
                'start_date': datetime(2023, 1, 1) + timedelta(days=customer_id * 3),
            })

    subscriptions_df = pd.DataFrame(subscriptions)

    # Load into DuckDB
    conn.execute("CREATE TABLE customers AS SELECT * FROM customers")
    conn.execute("CREATE TABLE subscriptions AS SELECT * FROM subscriptions_df")

    print(f"✅ Created sample database with:")
    print(f"   - {len(customers)} customers")
    print(f"   - {len(subscriptions)} subscriptions")

if __name__ == '__main__':
    generate_sample_data()
```

```bash
# Run it
python create_sample_data.py
```

---

## Day 2: Define Your First Semantic Layer (3 hours)

### Step 1: Create Semantic Model YAML

```yaml
# semantic_models/metrics.yml

semantic_model:
  name: company_metrics
  description: Core business metrics for the company

  connection:
    type: duckdb
    database: data/sample.duckdb

  # Define your data sources
  tables:
    - name: customers
      description: Customer dimension table

    - name: subscriptions
      description: Subscription fact table

  # Define dimensions (how you can slice data)
  dimensions:
    - name: customer_segment
      type: categorical
      description: Customer segment (Enterprise, Mid-Market, SMB)
      column: customer_segment
      table: customers

    - name: signup_month
      type: time
      description: Month when customer signed up
      column: signup_date
      table: customers
      time_grain: month

    - name: subscription_status
      type: categorical
      description: Current subscription status
      column: subscription_status
      table: subscriptions

  # Define metrics (what you want to measure)
  metrics:
    - name: mrr
      display_name: Monthly Recurring Revenue
      description: Total monthly recurring revenue from all active subscriptions
      type: simple
      calculation:
        aggregation: sum
        column: subscription_amount
        table: subscriptions
        filters:
          - "subscription_status = 'active'"
          - "billing_frequency = 'monthly'"

    - name: customer_count
      display_name: Total Customers
      description: Count of unique customers
      type: simple
      calculation:
        aggregation: count_distinct
        column: customer_id
        table: customers

    - name: active_subscriptions
      display_name: Active Subscriptions
      description: Count of active subscriptions
      type: simple
      calculation:
        aggregation: count
        column: subscription_id
        table: subscriptions
        filters:
          - "subscription_status = 'active'"

    - name: arpc
      display_name: Average Revenue Per Customer
      description: Average MRR per customer
      type: derived
      calculation:
        formula: "mrr / customer_count"
```

### Step 2: Create Semantic Layer Parser

```python
# src/semantic_layer.py

import yaml
import ibis
from typing import Dict, List, Any
from pathlib import Path

class SemanticLayer:
    """
    Loads and queries semantic layer definitions
    """

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.connection = self._create_connection()

    def _load_config(self) -> Dict:
        """Load semantic model YAML"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_connection(self) -> ibis.BaseBackend:
        """Create Ibis connection to warehouse"""
        conn_config = self.config['semantic_model']['connection']

        if conn_config['type'] == 'duckdb':
            return ibis.duckdb.connect(conn_config['database'])
        elif conn_config['type'] == 'snowflake':
            return ibis.snowflake.connect(**conn_config['credentials'])
        elif conn_config['type'] == 'bigquery':
            return ibis.bigquery.connect(**conn_config['credentials'])
        else:
            raise ValueError(f"Unsupported connection type: {conn_config['type']}")

    def get_metric(self, metric_name: str) -> Dict:
        """Get metric definition by name"""
        metrics = self.config['semantic_model']['metrics']
        for metric in metrics:
            if metric['name'] == metric_name:
                return metric
        raise ValueError(f"Metric '{metric_name}' not found")

    def list_metrics(self) -> List[Dict]:
        """List all available metrics"""
        return self.config['semantic_model']['metrics']

    def query_metric(
        self,
        metric_name: str,
        dimensions: List[str] = None,
        filters: List[str] = None,
        limit: int = None
    ) -> Dict:
        """
        Query a metric with optional dimensions and filters

        Args:
            metric_name: Name of metric to query
            dimensions: List of dimension names to group by
            filters: List of SQL WHERE conditions
            limit: Max rows to return

        Returns:
            Dict with query results
        """
        metric = self.get_metric(metric_name)

        # Build query based on metric type
        if metric['type'] == 'simple':
            result = self._query_simple_metric(metric, dimensions, filters, limit)
        elif metric['type'] == 'derived':
            result = self._query_derived_metric(metric, dimensions, filters, limit)
        else:
            raise ValueError(f"Unknown metric type: {metric['type']}")

        return {
            'metric': metric_name,
            'display_name': metric['display_name'],
            'description': metric['description'],
            'dimensions': dimensions or [],
            'data': result.to_pandas().to_dict('records'),
            'row_count': len(result)
        }

    def _query_simple_metric(
        self,
        metric: Dict,
        dimensions: List[str],
        filters: List[str],
        limit: int
    ):
        """Execute query for simple metric"""
        calc = metric['calculation']
        table = self.connection.table(calc['table'])

        # Apply metric filters
        if 'filters' in calc:
            for filter_expr in calc['filters']:
                table = table.filter(ibis.literal(filter_expr))

        # Apply user filters
        if filters:
            for filter_expr in filters:
                table = table.filter(ibis.literal(filter_expr))

        # Build aggregation
        agg_column = table[calc['column']]

        if calc['aggregation'] == 'sum':
            agg_expr = agg_column.sum().name(metric['name'])
        elif calc['aggregation'] == 'count':
            agg_expr = agg_column.count().name(metric['name'])
        elif calc['aggregation'] == 'count_distinct':
            agg_expr = agg_column.nunique().name(metric['name'])
        elif calc['aggregation'] == 'avg':
            agg_expr = agg_column.mean().name(metric['name'])
        else:
            raise ValueError(f"Unknown aggregation: {calc['aggregation']}")

        # Group by dimensions if provided
        if dimensions:
            # TODO: Properly join dimension tables
            # For now, assume dimensions are in same table
            result = table.group_by(dimensions).aggregate(agg_expr)
        else:
            result = table.aggregate(agg_expr)

        if limit:
            result = result.limit(limit)

        return result.execute()

    def _query_derived_metric(self, metric: Dict, dimensions: List[str], filters: List[str], limit: int):
        """Execute query for derived metric (calculated from other metrics)"""
        # For derived metrics, we need to query component metrics and combine
        # This is simplified - production would be more sophisticated
        raise NotImplementedError("Derived metrics not yet implemented")


# Test it
if __name__ == '__main__':
    sl = SemanticLayer('semantic_models/metrics.yml')

    print("📊 Available Metrics:")
    for metric in sl.list_metrics():
        print(f"  - {metric['name']}: {metric['display_name']}")

    print("\n💰 Querying MRR:")
    result = sl.query_metric('mrr')
    print(f"  Total MRR: ${result['data'][0]['mrr']:,.2f}")

    print("\n📈 MRR by Segment:")
    result = sl.query_metric('mrr', dimensions=['customer_segment'])
    for row in result['data']:
        print(f"  {row['customer_segment']}: ${row['mrr']:,.2f}")
```

Test it:
```bash
python src/semantic_layer.py
```

---

## Day 3: Build the MCP Server (4 hours)

### Step 1: Create MCP Server

```python
# src/mcp_server.py

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from semantic_layer import SemanticLayer
import json

class SemanticLayerMCPServer:
    """
    MCP Server that exposes semantic layer to Claude Desktop
    """

    def __init__(self, semantic_layer_config: str):
        self.app = Server("semantic-layer-mcp")
        self.semantic_layer = SemanticLayer(semantic_layer_config)
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools"""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="list_metrics",
                    description="List all available metrics in the semantic layer",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="query_metric",
                    description="Query a specific metric with optional dimensions and filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric_name": {
                                "type": "string",
                                "description": "Name of the metric to query (e.g., 'mrr', 'customer_count')"
                            },
                            "dimensions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of dimensions to group by (e.g., ['customer_segment'])"
                            },
                            "filters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional SQL WHERE conditions"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of rows to return"
                            }
                        },
                        "required": ["metric_name"]
                    }
                ),
                Tool(
                    name="explain_metric",
                    description="Get detailed information about a metric definition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric_name": {
                                "type": "string",
                                "description": "Name of the metric to explain"
                            }
                        },
                        "required": ["metric_name"]
                    }
                ),
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls from Claude"""

            if name == "list_metrics":
                return await self._list_metrics()
            elif name == "query_metric":
                return await self._query_metric(arguments)
            elif name == "explain_metric":
                return await self._explain_metric(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _list_metrics(self) -> list[TextContent]:
        """List all available metrics"""
        metrics = self.semantic_layer.list_metrics()

        response = "📊 Available Metrics:\n\n"
        for metric in metrics:
            response += f"**{metric['name']}** - {metric['display_name']}\n"
            response += f"  {metric['description']}\n\n"

        return [TextContent(type="text", text=response)]

    async def _query_metric(self, arguments: dict) -> list[TextContent]:
        """Query a metric"""
        metric_name = arguments['metric_name']
        dimensions = arguments.get('dimensions', [])
        filters = arguments.get('filters', [])
        limit = arguments.get('limit', None)

        try:
            result = self.semantic_layer.query_metric(
                metric_name=metric_name,
                dimensions=dimensions,
                filters=filters,
                limit=limit
            )

            # Format response
            response = f"📈 {result['display_name']}\n\n"
            response += f"{result['description']}\n\n"

            if dimensions:
                response += "Results:\n"
                for row in result['data']:
                    dim_vals = [f"{d}: {row[d]}" for d in dimensions]
                    response += f"  {', '.join(dim_vals)} → {metric_name}: {row[metric_name]:,.2f}\n"
            else:
                value = result['data'][0][metric_name]
                response += f"**Value: {value:,.2f}**\n"

            response += f"\n📊 Rows returned: {result['row_count']}"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            error_msg = f"❌ Error querying metric '{metric_name}': {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def _explain_metric(self, arguments: dict) -> list[TextContent]:
        """Explain a metric definition"""
        metric_name = arguments['metric_name']

        try:
            metric = self.semantic_layer.get_metric(metric_name)

            response = f"📊 **{metric['display_name']}**\n\n"
            response += f"**Description:** {metric['description']}\n\n"
            response += f"**Type:** {metric['type']}\n\n"

            if metric['type'] == 'simple':
                calc = metric['calculation']
                response += f"**Calculation:**\n"
                response += f"  Aggregation: {calc['aggregation']}\n"
                response += f"  Column: {calc['column']}\n"
                response += f"  Table: {calc['table']}\n"

                if 'filters' in calc:
                    response += f"  Filters:\n"
                    for filter_expr in calc['filters']:
                        response += f"    - {filter_expr}\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            error_msg = f"❌ Error explaining metric '{metric_name}': {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream,
                write_stream,
                self.app.create_initialization_options()
            )


# Main entry point
async def main():
    server = SemanticLayerMCPServer('semantic_models/metrics.yml')
    await server.run()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Day 4: Connect to Claude Desktop (1 hour)

### Step 1: Configure Claude Desktop

```bash
# Find your Claude Desktop config file
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json

# Edit the config (or create if doesn't exist)
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<EOF
{
  "mcpServers": {
    "semantic-layer": {
      "command": "/absolute/path/to/semantic-layer-mcp/venv/bin/python",
      "args": ["/absolute/path/to/semantic-layer-mcp/src/mcp_server.py"]
    }
  }
}
EOF

# IMPORTANT: Replace /absolute/path/to/semantic-layer-mcp with your actual path!
# Get it with: pwd
```

### Step 2: Restart Claude Desktop

```bash
# Close Claude Desktop completely
# Reopen it

# You should see a "🔌" icon indicating MCP servers are connected
```

### Step 3: Test It!

Open Claude Desktop and try:

```
You: What metrics are available?

Claude: [calls list_metrics tool]
📊 Available Metrics:

**mrr** - Monthly Recurring Revenue
  Total monthly recurring revenue from all active subscriptions

**customer_count** - Total Customers
  Count of unique customers

**active_subscriptions** - Active Subscriptions
  Count of active subscriptions

**arpc** - Average Revenue Per Customer
  Average MRR per customer
```

```
You: What's our MRR?

Claude: [calls query_metric with metric_name="mrr"]
📈 Monthly Recurring Revenue

Total monthly recurring revenue from all active subscriptions

**Value: $45,000.00**

📊 Rows returned: 1
```

```
You: Show me MRR by customer segment

Claude: [calls query_metric with metric_name="mrr", dimensions=["customer_segment"]]
📈 Monthly Recurring Revenue

Total monthly recurring revenue from all active subscriptions

Results:
  customer_segment: Enterprise → mrr: 20,000.00
  customer_segment: Mid-Market → mrr: 15,000.00
  customer_segment: SMB → mrr: 10,000.00

📊 Rows returned: 3
```

**🎉 IT WORKS!**

---

## Day 5: Add More Metrics & Test (2 hours)

### Add More Metrics to Your Semantic Layer

```yaml
# semantic_models/metrics.yml (add these)

  metrics:
    # ... existing metrics ...

    - name: churn_rate
      display_name: Churn Rate
      description: Percentage of customers who cancelled subscriptions
      type: simple
      calculation:
        aggregation: avg
        column: |
          CASE WHEN subscription_status = 'cancelled' THEN 1.0 ELSE 0.0 END
        table: subscriptions

    - name: revenue_growth_rate
      display_name: Revenue Growth Rate
      description: Month-over-month revenue growth percentage
      type: derived
      calculation:
        formula: "(current_mrr - previous_mrr) / previous_mrr * 100"

    - name: ltv
      display_name: Customer Lifetime Value
      description: Estimated lifetime value per customer
      type: derived
      calculation:
        formula: "mrr / churn_rate * 12"  # Simplified LTV
```

### Test Queries in Claude Desktop

```
You: What's our churn rate?

You: Show me customer count by segment

You: What's the average revenue per customer?

You: Explain how MRR is calculated

You: List all available metrics
```

---

## Week 1 Complete! What You Built

### ✅ What Works
- Claude Desktop connected to your semantic layer
- 5-7 metrics defined and queryable
- Natural language interface to your data
- No SQL required for end users

### 📊 Metrics You Can Query
- Monthly Recurring Revenue (MRR)
- Customer Count
- Active Subscriptions
- Average Revenue Per Customer (ARPC)
- Churn Rate
- (And any others you defined)

### 🎯 Example Conversations
```
"What's our MRR?" → $45,000
"Show me by segment" → Enterprise: $20k, Mid-Market: $15k, SMB: $10k
"How many customers do we have?" → 100 customers
"What's the churn rate?" → 10%
```

---

## Next Week: Level Up

### Week 2 Goals

**Monday: Connect to Real Warehouse**
```yaml
# Update semantic_models/metrics.yml

connection:
  type: snowflake  # or bigquery
  credentials:
    account: your-account
    user: your-user
    password: ${SNOWFLAKE_PASSWORD}  # from environment
    database: PROD_DB
    warehouse: ANALYTICS_WH
```

**Tuesday: Add 10 More Metrics**
- Net Revenue Retention (NRR)
- Gross Revenue Retention (GRR)
- Customer Acquisition Cost (CAC)
- CAC Payback Period
- Monthly Active Users (MAU)
- Activation Rate
- Product Qualified Leads (PQL)
- Pipeline Value
- Win Rate
- Sales Cycle Length

**Wednesday: Enable Team Access**
```bash
# Set up Slack integration
# Install Claude app in Slack
# Team can now ask @Claude questions
```

**Thursday: Add Visualizations**
```python
# Add chart generation to MCP server
@tool
def create_chart(metric_name, chart_type, dimensions):
    # Generate chart data
    # Return as JSON for Claude to visualize
    pass
```

**Friday: Enable Auto-Discovery**
```python
# Add tool to suggest new metrics based on query patterns
@tool
def suggest_metrics():
    # Analyze query logs
    # Suggest commonly calculated but undefined metrics
    pass
```

---

## Troubleshooting

### Issue: Claude doesn't see the MCP server

**Check:**
```bash
# 1. Is the config file in the right place?
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 2. Are paths absolute (not relative)?
# ❌ Wrong: "venv/bin/python"
# ✅ Right: "/Users/you/semantic-layer-mcp/venv/bin/python"

# 3. Is the Python script executable?
chmod +x src/mcp_server.py

# 4. Test the MCP server directly
cd /path/to/semantic-layer-mcp
source venv/bin/activate
python src/mcp_server.py
# Should start without errors
```

### Issue: Metrics return wrong results

**Debug:**
```python
# Test semantic layer directly
python src/semantic_layer.py

# Check raw SQL
sl = SemanticLayer('semantic_models/metrics.yml')
table = sl.connection.table('subscriptions')
print(table.filter(ibis.literal("subscription_status = 'active'")).execute())
```

### Issue: Dimensions don't work

**Currently:** Simple implementation assumes dimensions are in same table as metric.

**Fix:** Implement proper joins:
```python
def _query_simple_metric(self, metric, dimensions, filters, limit):
    # Get main table
    table = self.connection.table(calc['table'])

    # Join dimension tables
    for dim_name in dimensions:
        dim_def = self._get_dimension(dim_name)
        if dim_def['table'] != calc['table']:
            dim_table = self.connection.table(dim_def['table'])
            # TODO: Implement join logic
            table = table.join(dim_table, ...)

    # ... rest of query
```

---

## Resources

### Documentation
- MCP SDK: https://github.com/anthropics/mcp
- Ibis Documentation: https://ibis-project.org/
- Boring Semantic Layer: https://github.com/boring-software/boring-semantic-layer

### Example Semantic Layers
- Rasmus's Example: https://github.com/rasmusengelbrecht/user_lifecycle_states
- dbt Semantic Layer Docs: https://docs.getdbt.com/docs/build/semantic-models

### Community
- MCP Discord: [link]
- dbt Community Slack: #semantic-layer channel

---

## Appendix: Full File Listings

### requirements.txt
```
mcp>=0.9.0
ibis-framework[duckdb]>=9.0.0
pandas>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### .env (for production)
```
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=PROD_DB
SNOWFLAKE_WAREHOUSE=ANALYTICS_WH
```

### .gitignore
```
venv/
__pycache__/
*.pyc
.env
data/*.duckdb
*.log
.DS_Store
```

---

## Success Criteria

By end of Week 1, you should be able to:

✅ Ask Claude "What's our MRR?" and get instant answer
✅ Query any defined metric with dimensions
✅ Add new metrics by editing YAML (no code changes)
✅ Share metrics with team (they ask Claude directly)
✅ Understand how the system works end-to-end

**If you can do all of these, you're ready for Week 2!**

---

**Next Steps:**
1. Clone starter template (if provided)
2. Follow Day 1-5 instructions
3. Test with Claude Desktop
4. Add your real metrics
5. Connect to production warehouse
6. Scale to team usage

**Questions?** Ask Claude! (Once you have it set up 😄)
