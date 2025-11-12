# API Reference

Complete API documentation for knowDB REST API, MCP Server, and Slack integration.

## Table of Contents

- [REST API](#rest-api)
- [MCP Server Protocol](#mcp-server-protocol)
- [Slack Bot Commands](#slack-bot-commands)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)

---

## REST API

Base URL: `http://localhost:8000` (or your deployed URL)

### Authentication

All API endpoints (except `/health`) require authentication via API key:

```bash
curl -H "X-API-Key: REDACTED" http://localhost:8000/metrics
```

**Permission Levels:**
- **Admin:** Full access (clear cache, manage system)
- **Query:** Read metrics, execute queries, generate visualizations
- **Read:** List metrics and dimensions only

### Health Check

#### GET /health

Check if the service is running.

**Authentication:** None required

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-11-08T10:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### List Metrics

#### GET /metrics

Get all available metrics with their definitions.

**Authentication:** Query or Read permission

**Response:**
```json
{
  "metrics": [
    {
      "name": "total_mrr",
      "display_name": "Monthly Recurring Revenue (MRR)",
      "description": "Total monthly recurring revenue from all active subscriptions",
      "type": "simple",
      "calculation": {
        "table": "subscriptions",
        "aggregation": "sum",
        "column": "subscription_amount",
        "filters": [
          "subscription_status = 'active'",
          "billing_frequency = 'monthly'"
        ]
      }
    },
    {
      "name": "arr",
      "display_name": "Annual Recurring Revenue (ARR)",
      "description": "Total annual recurring revenue (MRR * 12)",
      "type": "derived",
      "calculation": {
        "formula": "total_mrr * 12"
      }
    }
  ]
}
```

**Example:**
```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/metrics
```

---

### Get Metric Details

#### GET /metrics/{metric_name}

Get detailed information about a specific metric.

**Authentication:** Query or Read permission

**Path Parameters:**
- `metric_name` (string, required): Name of the metric

**Response:**
```json
{
  "name": "total_mrr",
  "display_name": "Monthly Recurring Revenue (MRR)",
  "description": "Total monthly recurring revenue from all active subscriptions",
  "type": "simple",
  "calculation": {
    "table": "subscriptions",
    "aggregation": "sum",
    "column": "subscription_amount",
    "filters": [
      "subscription_status = 'active'",
      "billing_frequency = 'monthly'"
    ]
  },
  "dependencies": [],
  "dimensions": [
    "customer_segment",
    "country",
    "product_tier"
  ]
}
```

**Example:**
```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/metrics/total_mrr
```

**Error Response (404):**
```json
{
  "error": "Metric not found",
  "metric_name": "non_existent_metric"
}
```

---

### Query Metric

#### POST /query

Execute a query for a specific metric.

**Authentication:** Query permission

**Request Body:**
```json
{
  "metric_name": "total_mrr",
  "dimensions": ["customer_segment"],
  "filters": ["country = 'US'"],
  "limit": 100,
  "order_by": "total_mrr DESC"
}
```

**Request Fields:**
- `metric_name` (string, required): Metric to query
- `dimensions` (array[string], optional): Columns to group by
- `filters` (array[string], optional): WHERE conditions
- `limit` (integer, optional): Max rows (default: 1000)
- `order_by` (string, optional): ORDER BY clause

**Response:**
```json
{
  "success": true,
  "metric_name": "total_mrr",
  "data": [
    {
      "customer_segment": "Enterprise",
      "total_mrr": 24741.53
    },
    {
      "customer_segment": "Mid-Market",
      "total_mrr": 18464.34
    },
    {
      "customer_segment": "SMB",
      "total_mrr": 5464.12
    }
  ],
  "sql": "SELECT customers.customer_segment, SUM(subscriptions.subscription_amount) AS total_mrr FROM subscriptions LEFT JOIN customers ON subscriptions.customer_id = customers.customer_id WHERE subscriptions.subscription_status = 'active' AND subscriptions.billing_frequency = 'monthly' AND country = 'US' GROUP BY customers.customer_segment ORDER BY total_mrr DESC LIMIT 100",
  "execution_time_ms": 87,
  "row_count": 3,
  "cached": false
}
```

**Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{
    "metric_name": "total_mrr",
    "dimensions": ["customer_segment"],
    "filters": ["country = \"US\""],
    "limit": 100
  }' \
  http://localhost:8000/query
```

**Error Response (400):**
```json
{
  "error": "Invalid request",
  "details": "Metric 'unknown_metric' not found"
}
```

**Error Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

### List Dimensions

#### GET /dimensions

Get all available dimensions for grouping metrics.

**Authentication:** Query or Read permission

**Response:**
```json
{
  "dimensions": [
    {
      "name": "customer_segment",
      "display_name": "Customer Segment",
      "description": "Customer tier (Enterprise, Mid-Market, SMB)",
      "type": "categorical",
      "table": "customers",
      "column": "customer_segment"
    },
    {
      "name": "country",
      "display_name": "Country",
      "description": "Customer country",
      "type": "categorical",
      "table": "customers",
      "column": "country"
    }
  ]
}
```

**Example:**
```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/dimensions
```

---

### Generate Visualization

#### POST /visualize

Generate a visualization for a metric query.

**Authentication:** Query permission

**Request Body:**
```json
{
  "metric_name": "monthly_mrr",
  "chart_type": "line",
  "dimensions": ["month"],
  "filters": [],
  "width": 800,
  "height": 400
}
```

**Request Fields:**
- `metric_name` (string, required): Metric to visualize
- `chart_type` (string, required): Chart type (line, bar, pie, scatter)
- `dimensions` (array[string], optional): Grouping dimensions
- `filters` (array[string], optional): WHERE conditions
- `width` (integer, optional): Chart width in pixels (default: 800)
- `height` (integer, optional): Chart height in pixels (default: 400)

**Response:**
```json
{
  "success": true,
  "chart_type": "line",
  "data": {
    "labels": ["2024-06", "2024-07", "2024-08", "2024-09", "2024-10"],
    "datasets": [{
      "label": "MRR",
      "data": [42123.45, 44567.89, 45890.12, 47234.56, 48670.00]
    }]
  },
  "config": {
    "type": "line",
    "options": {
      "responsive": true,
      "title": {
        "display": true,
        "text": "MRR by Month"
      }
    }
  },
  "image_url": "/visualizations/abc123.png"
}
```

**Chart Types:**
- `line`: Time series, trends
- `bar`: Comparisons across categories
- `pie`: Composition, percentages
- `scatter`: Correlations, distributions

**Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{
    "metric_name": "monthly_mrr",
    "chart_type": "line",
    "dimensions": ["month"]
  }' \
  http://localhost:8000/visualize
```

---

### Cache Management

#### GET /cache/stats

Get cache statistics.

**Authentication:** Read permission

**Response:**
```json
{
  "backend": "redis",
  "stats": {
    "hits": 1247,
    "misses": 89,
    "hit_rate": 0.933,
    "size_bytes": 2457600,
    "keys_count": 156,
    "ttl_seconds": 1800
  }
}
```

**Example:**
```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/cache/stats
```

---

#### POST /cache/clear

Clear all cached queries.

**Authentication:** Admin permission

**Request Body (optional):**
```json
{
  "pattern": "total_mrr*"
}
```

**Response:**
```json
{
  "success": true,
  "cleared_keys": 42,
  "message": "Cache cleared successfully"
}
```

**Example:**
```bash
# Clear all cache
curl -X POST \
  -H "X-API-Key: REDACTED" \
  http://localhost:8000/cache/clear

# Clear specific pattern
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{"pattern": "total_mrr*"}' \
  http://localhost:8000/cache/clear
```

---

### System Status

#### GET /status

Get detailed system status and health metrics.

**Authentication:** Read permission

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "database": {
    "type": "duckdb",
    "connected": true,
    "latency_ms": 5
  },
  "cache": {
    "backend": "redis",
    "connected": true,
    "hit_rate": 0.933
  },
  "metrics": {
    "total_metrics": 14,
    "queries_today": 247,
    "avg_query_time_ms": 127
  }
}
```

**Example:**
```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/status
```

---

## MCP Server Protocol

The MCP (Model Context Protocol) server enables Claude Desktop to query the semantic layer.

### Available Tools

#### list_metrics

List all available metrics.

**Parameters:** None

**Returns:**
```json
{
  "metrics": [
    {
      "name": "total_mrr",
      "display_name": "Monthly Recurring Revenue (MRR)",
      "description": "Total monthly recurring revenue from all active subscriptions"
    }
  ]
}
```

**Example usage in Claude Desktop:**
```
You: "What metrics are available?"

Claude uses list_metrics tool and shows:
Available metrics:
1. Monthly Recurring Revenue (MRR)
2. Annual Recurring Revenue (ARR)
3. Churn Rate
...
```

---

#### query_metric

Query a specific metric with optional dimensions and filters.

**Parameters:**
- `metric_name` (string, required): Metric to query
- `dimensions` (array[string], optional): Grouping columns
- `filters` (array[string], optional): WHERE conditions
- `limit` (integer, optional): Max rows

**Returns:**
```json
{
  "data": [...],
  "sql": "...",
  "execution_time_ms": 87
}
```

**Example usage in Claude Desktop:**
```
You: "Show me MRR by customer segment"

Claude uses query_metric tool:
- metric_name: "total_mrr"
- dimensions: ["customer_segment"]

Results:
| Segment    | MRR        |
|------------|------------|
| Enterprise | $24,741.53 |
| Mid-Market | $18,464.34 |
| SMB        | $5,464.12  |
```

---

#### explain_metric

Get detailed explanation of how a metric is calculated.

**Parameters:**
- `metric_name` (string, required): Metric to explain

**Returns:**
```json
{
  "name": "total_mrr",
  "display_name": "Monthly Recurring Revenue (MRR)",
  "type": "simple",
  "calculation": {...},
  "dependencies": []
}
```

**Example usage in Claude Desktop:**
```
You: "How is MRR calculated?"

Claude uses explain_metric tool:
- metric_name: "total_mrr"

Shows:
MRR is calculated as:
- Type: Simple aggregation
- Table: subscriptions
- Aggregation: SUM
- Column: subscription_amount
- Filters:
  - subscription_status = 'active'
  - billing_frequency = 'monthly'
```

---

#### list_dimensions

List all available dimensions for grouping.

**Parameters:** None

**Returns:**
```json
{
  "dimensions": [
    {
      "name": "customer_segment",
      "display_name": "Customer Segment",
      "type": "categorical"
    }
  ]
}
```

**Example usage in Claude Desktop:**
```
You: "What dimensions can I group by?"

Claude uses list_dimensions tool and shows:
Available dimensions:
1. Customer Segment (categorical)
2. Country (categorical)
3. Product Tier (categorical)
...
```

---

## Slack Bot Commands

### Slash Commands

#### /metrics

List all available metrics.

**Usage:**
```
/metrics
```

**Response:**
```
Available Metrics:
1. Monthly Recurring Revenue (MRR)
2. Annual Recurring Revenue (ARR)
3. Churn Rate
4. Active Customers
...

Use /query <metric_name> to query a metric
```

---

#### /query

Query a metric with natural language.

**Usage:**
```
/query What's our total MRR?
/query Show me MRR by customer segment
/query What's the churn rate for enterprise customers?
```

**Response:**
```
Monthly Recurring Revenue: $48,670.00

Breakdown by customer_segment:
• Enterprise: $24,741.53
• Mid-Market: $18,464.34
• SMB: $5,464.12

Query executed in 87ms
```

---

#### /dimensions

List available dimensions for grouping.

**Usage:**
```
/dimensions
```

**Response:**
```
Available Dimensions:
• customer_segment - Customer tier
• country - Customer country
• product_tier - Product tier
• billing_frequency - Monthly or Annual
...
```

---

#### /cache

Manage query cache (admin only).

**Usage:**
```
/cache stats
/cache clear
```

**Response:**
```
Cache Statistics:
• Backend: Redis
• Hit Rate: 93.3%
• Cached Queries: 156
• Cache Size: 2.4 MB
• TTL: 30 minutes
```

---

### Bot Mentions

Mention the bot for conversational queries:

**Usage:**
```
@semantic-bot show me total revenue by product tier
@semantic-bot what's our churn rate?
@semantic-bot break down MRR by segment
```

**Response:**
```
Total Revenue by Product Tier:

| Product Tier  | Revenue      |
|---------------|--------------|
| Enterprise    | $25,456.78   |
| Professional  | $18,234.56   |
| Basic         | $4,978.66    |

Total: $48,670.00
```

---

## Authentication

### API Key Authentication

Include API key in request header:

```bash
curl -H "X-API-Key: REDACTED" \
  http://localhost:8000/metrics
```

### JWT Token Authentication

For service-to-service communication:

```bash
# Get JWT token
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}' \
  http://localhost:8000/auth/token

# Response
{
  "token": "REDACTED_JWT",
  "expires_at": "2024-11-08T18:30:00Z"
}

# Use JWT token
curl -H "Authorization: Bearer REDACTED" \
  http://localhost:8000/metrics
```

### Permission Levels

| Permission | Endpoints | Description |
|------------|-----------|-------------|
| **Admin** | All | Full system access |
| **Query** | GET /metrics, POST /query, POST /visualize | Query and visualize metrics |
| **Read** | GET /metrics, GET /dimensions, GET /cache/stats | Read-only access |

---

## Rate Limiting

### Default Limits

- **Per User:** 100 requests per minute
- **Per IP:** 1000 requests per minute
- **Query Endpoint:** 50 requests per minute

### Rate Limit Headers

Response includes rate limit headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1699458600
```

### Exceeding Rate Limits

**Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "limit": 100,
  "retry_after": 45
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error message",
  "details": "Detailed error information",
  "request_id": "abc123",
  "timestamp": "2024-11-08T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Errors

#### Metric Not Found
```json
{
  "error": "Metric not found",
  "metric_name": "unknown_metric",
  "available_metrics": ["total_mrr", "arr", "churn_rate", ...]
}
```

#### Invalid Filter
```json
{
  "error": "Invalid filter syntax",
  "filter": "invalid syntax here",
  "suggestion": "Use format: column = 'value'"
}
```

#### Query Execution Error
```json
{
  "error": "Query execution failed",
  "details": "Column 'unknown_column' not found in table",
  "sql": "SELECT ..."
}
```

#### Authentication Error
```json
{
  "error": "Authentication failed",
  "details": "Invalid API key"
}
```

---

## SDKs and Client Libraries

### Python SDK

```python
from knowdb import KnowDBClient

# Initialize client
client = KnowDBClient(
    api_url="http://localhost:8000",
    api_key="your-api-key"
)

# List metrics
metrics = client.list_metrics()

# Query metric
result = client.query_metric(
    metric_name="total_mrr",
    dimensions=["customer_segment"],
    filters=["country = 'US'"]
)

# Generate visualization
viz = client.visualize(
    metric_name="monthly_mrr",
    chart_type="line",
    dimensions=["month"]
)
```

### JavaScript SDK

```javascript
import { KnowDBClient } from 'knowdb-js';

// Initialize client
const client = new KnowDBClient({
  apiUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// List metrics
const metrics = await client.listMetrics();

// Query metric
const result = await client.queryMetric({
  metricName: 'total_mrr',
  dimensions: ['customer_segment'],
  filters: ['country = "US"']
});

// Generate visualization
const viz = await client.visualize({
  metricName: 'monthly_mrr',
  chartType: 'line',
  dimensions: ['month']
});
```

---

## Webhooks (Coming Soon)

### Register Webhook

Subscribe to events like cache clears, metric updates, etc.

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{
    "url": "https://your-app.com/webhooks/knowdb",
    "events": ["metric.updated", "cache.cleared"],
    "secret": "your-webhook-secret"
  }' \
  http://localhost:8000/webhooks
```

---

## Support

For API support:
- **Documentation:** [Full docs](docs/)
- **Issues:** [GitHub Issues](https://github.com/your-org/knowDB/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-org/knowDB/discussions)

---

**API Version:** 1.0.0
**Last Updated:** 2024-11-08
