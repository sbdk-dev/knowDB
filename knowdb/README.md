# KnowDB

> **Archive Notice (November 2025)**: This project is being prepared for public archive. It represents a complete local-first agentic analytics platform built on sbdk-dev.

**Local-first semantic layer for AI-powered analytics.**

KnowDB enables natural language queries against your data through AI assistants like Claude Desktop and ChatGPT Desktop via the Model Context Protocol (MCP). Define metrics once in YAML, query them conversationally with automatic statistical rigor.

## Open Source

**License**: MIT License - Free for personal and commercial use.

See [LICENSE](LICENSE) for full terms.

## Features

- **Multi-AI Support**: Works with Claude Desktop, ChatGPT Desktop, and any MCP-compatible AI
- **Semantic Layer**: Define metrics once in YAML, use everywhere
- **Natural Language**: Query data conversationally
- **Statistical Rigor**: Automatic confidence intervals and significance testing
- **dbt Integration**: Auto-sync dbt models to semantic layer
- **Local-First**: DuckDB-based, runs entirely on your machine
- **Extends sbdk-dev**: Builds on proven data pipeline infrastructure

## Architecture

KnowDB is a semantic layer that **extends sbdk-dev**:

```
┌─────────────────────────────────────────────────────┐
│                   KnowDB                            │
│   Semantic Layer • AI Analysis • Statistics         │
└───────────────────────┬─────────────────────────────┘
                        │ extends
┌───────────────────────┴─────────────────────────────┐
│                   sbdk-dev                          │
│   dlt → DuckDB → dbt → Quality → CLI               │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
pip install knowdb

# Initialize sbdk project
sbdk init my-analytics && cd my-analytics

# Run data pipeline
sbdk run

# Sync dbt models to semantic layer
knowdb sync

# Query metrics
knowdb query mrr -d segment

# AI-powered analysis
knowdb analyze "What is our MRR by segment?"

# Start MCP server for AI assistants
knowdb serve
```

## AI Assistant Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowdb": {
      "command": "python",
      "args": ["-m", "knowdb.mcp.server"],
      "env": {
        "SEMANTIC_MODELS_PATH": "/path/to/semantic_models/metrics.yml"
      }
    }
  }
}
```

### ChatGPT Desktop

Add to ChatGPT Desktop's MCP configuration (similar format).

### Other MCP-Compatible AI

KnowDB works with any AI assistant that supports the Model Context Protocol.

## CLI Commands

```bash
# Semantic queries
knowdb query mrr                    # Simple query
knowdb query mrr -d segment         # With dimension
knowdb query mrr -f segment=Enterprise  # With filter

# AI analysis
knowdb analyze "Compare MRR by segment"

# dbt integration
knowdb sync                         # Sync dbt → semantic layer
knowdb dbt-models                   # List dbt models

# Utilities
knowdb list-metrics
knowdb explain mrr
knowdb serve                        # Start MCP server

# sbdk pipeline commands
knowdb pipeline run                 # Full data pipeline
knowdb pipeline query "SELECT *"    # Direct SQL
```

## Semantic Layer

Define metrics in YAML:

```yaml
# semantic_models/metrics.yml
metrics:
  - name: mrr
    display_name: "Monthly Recurring Revenue"
    type: simple
    calculation:
      table: marts.revenue
      aggregation: sum
      column: amount

dimensions:
  - name: segment
    type: categorical
    table: marts.revenue
    column: segment
```

## MCP Tools

KnowDB exposes these tools to AI assistants:

| Tool | Description |
|------|-------------|
| `query_metric` | Query metrics with dimensions/filters |
| `list_metrics` | List available metrics |
| `explain_metric` | Show calculation details |
| `sync_from_dbt` | Sync dbt models to semantic layer |
| `test_significance` | Statistical significance testing |
| `suggest_analysis` | AI-powered analysis suggestions |

## Requirements

- Python 3.11+
- sbdk-dev (data pipeline infrastructure)
- DuckDB (included)

## Installation

```bash
# From PyPI
pip install knowdb

# With sbdk-dev (recommended)
pip install knowdb sbdk-dev

# Development
git clone https://github.com/matt-strautmann/knowdb.git
cd knowdb
pip install -e ".[dev]"
```

## Project Structure

```
knowdb/
├── src/knowdb/
│   ├── semantic_layer/     # Metric definitions, Ibis queries
│   ├── intelligence/       # Statistical testing, NLG
│   ├── optimization/       # Query caching
│   ├── mcp/               # MCP tools for AI assistants
│   └── bridge/            # dbt → semantic sync
├── tests/                 # 109 tests
└── pyproject.toml
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests (TDD)
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Matt Strautmann

## Acknowledgments

- Built on [sbdk-dev](https://github.com/matt-strautmann/sbdk-dev) for data pipeline infrastructure
- Inspired by dbt Semantic Layer, Cube.js, and WrenAI
- Uses Model Context Protocol for AI assistant integration
