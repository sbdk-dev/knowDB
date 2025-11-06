# Troubleshooting Guide

This guide helps you resolve common issues with the Semantic Layer MCP Server.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Connection Issues](#connection-issues)
- [Query Issues](#query-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'mcp'`

**Cause:** MCP package not installed or wrong Python environment

**Solution:**
```bash
# Install dependencies with uv
uv pip install -e ".[dev]"

# Verify installation
uv run python -c "import mcp; print('MCP installed successfully')"
```

### Issue: `ModuleNotFoundError: No module named 'ibis'`

**Cause:** Ibis package not installed

**Solution:**
```bash
uv pip install "ibis-framework[duckdb]>=9.0.0"

# Verify
uv run python -c "import ibis; print('Ibis installed')"
```

### Issue: Python version incompatibility

**Symptom:** Installation fails with typing or syntax errors

**Solution:**
```bash
# Check Python version (need 3.11+)
python --version

# If version is too old, install Python 3.11 or higher
# Then recreate virtual environment with uv
uv venv --python 3.11
uv pip install -e ".[dev]"
```

## Configuration Issues

### Issue: Claude Desktop doesn't show 🔌 icon

**Symptoms:**
- No MCP servers indicator in Claude Desktop
- Queries work but don't access semantic layer
- Claude doesn't have access to your metrics

**Solutions:**

**1. Check Configuration File Location:**

On macOS:
```bash
ls ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

On Windows:
```bash
dir %APPDATA%\Claude\claude_desktop_config.json
```

If file doesn't exist, create it.

**2. Verify Configuration Format:**

```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/src/mcp_server.py"
      ],
      "env": {
        "SEMANTIC_MODELS_PATH": "/ABSOLUTE/PATH/TO/semantic_models/metrics.yml"
      }
    }
  }
}
```

**Note:** uv creates `.venv` (not `venv`)

**3. Use Absolute Paths (Not Relative):**

❌ Wrong:
```json
"command": "./.venv/bin/python"
```

✅ Correct:
```json
"command": "/Users/yourname/knowDB/.venv/bin/python"
```

**4. Restart Claude Desktop:**
- Quit completely (Cmd+Q on Mac, Alt+F4 on Windows)
- Wait 5 seconds
- Reopen

### Issue: "Configuration file not found" error

**Error Message:**
```
SemanticLayerError: Configuration file not found: semantic_models/metrics.yml
```

**Solutions:**

**1. Verify File Exists:**
```bash
ls semantic_models/metrics.yml
```

**2. Use Absolute Path:**
```bash
# Get absolute path
cd knowDB
pwd

# Update claude_desktop_config.json with absolute path
"SEMANTIC_MODELS_PATH": "/full/path/to/knowDB/semantic_models/metrics.yml"
```

**3. Check File Permissions:**
```bash
# Make sure file is readable
chmod 644 semantic_models/metrics.yml
```

### Issue: Environment Variables Not Loading

**Symptom:** Connection fails with "missing credentials"

**Solution:**

Create `.env` file in project root:
```bash
# .env
DATABASE_TYPE=snowflake
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
```

Load in MCP config:
```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/mcp_server.py"],
      "env": {
        "SEMANTIC_MODELS_PATH": "/path/to/metrics.yml",
        "SNOWFLAKE_USER": "your_user",
        "SNOWFLAKE_PASSWORD": "your_password"
      }
    }
  }
}
```

## Connection Issues

### Issue: "Error connecting to database"

**For DuckDB:**

```bash
# Check if database file exists
ls data/sample.duckdb

# If missing, regenerate
python create_sample_data.py

# Check permissions
chmod 644 data/sample.duckdb
```

**For Snowflake:**

```python
# Test connection directly
python -c "
import ibis
conn = ibis.snowflake.connect(
    user='YOUR_USER',
    password='YOUR_PASSWORD',
    account='YOUR_ACCOUNT',
    database='YOUR_DATABASE'
)
print('Connected successfully')
"
```

Common issues:
- Wrong account identifier format (should be `orgname-account`, not `account.snowflakecomputing.com`)
- Expired password
- Network/firewall blocking connection
- Wrong warehouse name

**For BigQuery:**

```bash
# Check credentials
gcloud auth application-default login

# Test connection
python -c "
import ibis
conn = ibis.bigquery.connect(
    project_id='YOUR_PROJECT',
    dataset_id='YOUR_DATASET'
)
print('Connected')
"
```

**For PostgreSQL:**

```bash
# Test connection
psql -h HOST -U USER -d DATABASE

# Check Python connection
python -c "
import ibis
conn = ibis.postgres.connect(
    host='HOST',
    port=5432,
    database='DATABASE',
    user='USER',
    password='PASSWORD'
)
print('Connected')
"
```

### Issue: Connection Timeout

**Symptoms:**
- Queries hang
- Timeout errors

**Solutions:**

1. **Check Network:**
```bash
# Test connectivity
ping your-database-host

# Check if port is open
nc -zv your-database-host 5432
```

2. **Increase Timeout:**
```python
# In semantic_layer.py, increase timeout
conn = ibis.snowflake.connect(
    ...,
    connect_timeout=60  # Increase from default 10s
)
```

3. **Check Firewall:**
- Whitelist your IP in database firewall
- Check VPN connection if required

## Query Issues

### Issue: "Metric not found"

**Error:** `SemanticLayerError: Metric 'revenue' not found`

**Solutions:**

1. **List Available Metrics:**
```bash
# Check what metrics exist
python -c "
from src.semantic_layer import SemanticLayer
sl = SemanticLayer('semantic_models/metrics.yml')
for m in sl.list_metrics():
    print(m['name'])
"
```

2. **Check Metric Name:**
- Metric names are case-sensitive
- Use exact name from YAML file

3. **Validate YAML:**
```bash
# Check YAML syntax
python -c "
import yaml
with open('semantic_models/metrics.yml') as f:
    config = yaml.safe_load(f)
    print(f\"Found {len(config['semantic_model']['metrics'])} metrics\")
"
```

### Issue: "Dimension not found"

**Error:** `SemanticLayerError: Dimension 'segment' not found and not a column in table`

**Solutions:**

1. **Check Dimension Name:**
```python
# List available dimensions
from src.semantic_layer import SemanticLayer
sl = SemanticLayer('semantic_models/metrics.yml')
for d in sl.list_dimensions():
    print(f"{d['name']} ({d['table']}.{d['column']})")
```

2. **Verify Table Join:**
- Dimension must have common column with metric table
- Example: Both need `customer_id`

3. **Add Missing Dimension:**
```yaml
dimensions:
  - name: "segment"
    display_name: "Customer Segment"
    type: "categorical"
    table: "customers"
    column: "customer_segment"
```

### Issue: "No common columns found" for Join

**Error:** `Cannot join subscriptions with customers - no common columns found`

**Solution:**

Ensure tables have common join keys:

```sql
-- Check table schemas
SELECT column_name FROM information_schema.columns
WHERE table_name IN ('subscriptions', 'customers');

-- Add join key if missing
ALTER TABLE subscriptions ADD COLUMN customer_id INT;
```

### Issue: Query Returns Empty Results

**Symptoms:**
- Query succeeds but returns 0 rows
- Expected data not showing up

**Debugging:**

1. **Check Filters:**
```python
# Test without filters
result = sl.query_metric('total_mrr')
print(result['data'])

# Then add filters one by one
result = sl.query_metric('total_mrr',
    filters=["subscription_status = 'active'"])
```

2. **Inspect SQL:**
```python
result = sl.query_metric('total_mrr')
print(result['sql'])  # Copy and run this in your database
```

3. **Check Data:**
```python
# Query raw table
import ibis
conn = ibis.duckdb.connect('data/sample.duckdb')
table = conn.table('subscriptions')
print(table.head().execute())
```

### Issue: "Could not parse filter expression"

**Warning:** `WARNING: Could not parse filter expression: complex_filter`

**Solution:**

Simplify filter or use supported syntax:

**Supported:**
```python
filters=[
    "column = 'value'",      # Equality
    "column = 123",           # Numeric
    "column > 100",           # Greater than
    "column < 50",            # Less than
    "column >= 100",          # Greater or equal
    "column <= 50"            # Less or equal
]
```

**Not Yet Supported:**
```python
"column IN ('a', 'b')"       # IN clause
"column LIKE '%pattern%'"    # LIKE
"col1 = 'a' AND col2 = 'b'"  # AND/OR
```

For complex filters, add them to metric definition in YAML.

## Performance Issues

### Issue: Queries Are Slow

**Symptoms:**
- Takes >5 seconds to return results
- Claude seems to hang

**Solutions:**

1. **Add Indexes:**
```sql
-- In your database
CREATE INDEX idx_subscription_status ON subscriptions(subscription_status);
CREATE INDEX idx_customer_id ON subscriptions(customer_id);
```

2. **Limit Results:**
```python
# In Claude, ask for:
"Show me top 10 customers by MRR"
# vs
"Show me all customers" (slower)
```

3. **Check Query Plan:**
```sql
-- Copy SQL from result and run EXPLAIN
EXPLAIN SELECT ...
```

4. **Enable Caching** (coming in Phase 2)

### Issue: High Memory Usage

**Symptom:** Python process uses excessive RAM

**Solutions:**

1. **Limit Result Size:**
```python
result = sl.query_metric('total_mrr', limit=1000)
```

2. **Stream Large Results** (for future enhancement)

3. **Increase System Resources**

## Data Issues

### Issue: Incorrect Metric Values

**Symptom:** Numbers don't match expected values

**Debugging:**

1. **Check Metric Definition:**
```yaml
metrics:
  - name: "total_mrr"
    calculation:
      aggregation: "sum"  # Check this is correct
      column: "subscription_amount"  # Check column name
      filters:
        - "subscription_status = 'active'"  # Check filters
```

2. **Inspect Raw Data:**
```python
import ibis
conn = ibis.duckdb.connect('data/sample.duckdb')

# Check what data looks like
df = conn.execute('SELECT * FROM subscriptions WHERE subscription_status = "active" LIMIT 10')
print(df)

# Manual calculation
df = conn.execute('SELECT SUM(subscription_amount) FROM subscriptions WHERE subscription_status = "active"')
print(df)
```

3. **Check Data Types:**
```python
# Ensure numeric columns are numeric
print(table.schema())
```

### Issue: Duplicate Results

**Symptom:** Getting duplicate rows or inflated numbers

**Cause:** Usually a join issue (many-to-many)

**Solution:**

1. **Check Join Cardinality:**
```sql
-- Count rows before and after join
SELECT COUNT(*) FROM subscriptions;  -- e.g., 150
SELECT COUNT(*) FROM subscriptions
JOIN customers ON subscriptions.customer_id = customers.customer_id;  -- Should still be 150
```

2. **Use DISTINCT if Needed:**
```python
# In metric definition, use count_distinct
calculation:
  aggregation: "count_distinct"
  column: "customer_id"
```

### Issue: NULL Values in Results

**Symptom:** Seeing NULL/None in results

**Solutions:**

1. **Handle NULLs in Query:**
```yaml
# In metric calculation, add filter
filters:
  - "column IS NOT NULL"
```

2. **Check Source Data:**
```sql
SELECT COUNT(*) FROM table WHERE important_column IS NULL;
```

3. **Use COALESCE:**
For future enhancement, add COALESCE support in semantic layer.

## Testing and Validation

### Run Test Suite

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_semantic_layer.py::TestQueries::test_query_simple_metric -v

# Run with verbose output
uv run pytest tests/ -v --tb=short
```

### Manual Testing

```bash
# Test semantic layer directly
uv run python src/semantic_layer.py

# Test MCP server
uv run python src/mcp_server.py
# (Server will start and wait for Claude Desktop to connect)
```

### Enable Debug Logging

```python
# In semantic_layer.py, change log level
logging.basicConfig(level=logging.DEBUG)
```

Or in Claude Desktop config:
```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "...",
      "args": ["..."],
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Getting More Help

### Check Logs

**Claude Desktop Logs:**
- macOS: `~/Library/Logs/Claude/`
- Windows: `%APPDATA%\Claude\logs\`

**MCP Server Logs:**
Check terminal output or Claude Desktop console

### Collect Diagnostics

```bash
# Run diagnostics script
uv run python -c "
import sys
print(f'Python: {sys.version}')

import mcp
print(f'MCP: {mcp.__version__}')

import ibis
print(f'Ibis: {ibis.__version__}')

from src.semantic_layer import SemanticLayer
sl = SemanticLayer('semantic_models/metrics.yml')
print(f'Metrics: {len(sl.list_metrics())}')
print(f'Dimensions: {len(sl.list_dimensions())}')
print('✅ All checks passed')
"
```

### Common Error Messages

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| `Configuration file not found` | Wrong path | Use absolute paths |
| `Metric 'X' not found` | Typo or not defined | Check YAML file |
| `No common columns found` | Missing join key | Add join column |
| `Connection refused` | Wrong port/host | Check connection config |
| `Permission denied` | File permissions | `chmod 644 file` |
| `ModuleNotFoundError` | Package not installed | `pip install package` |

### Report an Issue

When reporting issues, include:

1. **Environment:**
   - OS and version
   - Python version
   - Package versions (`pip list`)

2. **Configuration:**
   - `semantic_models/metrics.yml` (redact sensitive data)
   - MCP config (redact credentials)

3. **Error:**
   - Full error message
   - Stack trace
   - Steps to reproduce

4. **Logs:**
   - Claude Desktop logs
   - MCP server output

---

**Still stuck?** Open an issue on GitHub with the information above.
