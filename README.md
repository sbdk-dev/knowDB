# KnowDB - Local-First Agentic Analytics Platform

> **📦 Public Archive - November 2025**
>
> This project is being archived as a complete reference implementation of a local-first semantic layer for AI-powered analytics. It demonstrates best practices for MCP integration, dbt semantic bridging, and extending data pipeline infrastructure.

## Overview

KnowDB is an **AI semantic layer** that extends [sbdk-dev](./sbdk-dev) to enable natural language queries against your data through AI assistants like **Claude Desktop** and **ChatGPT Desktop** via the Model Context Protocol (MCP).

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   KnowDB                            │
│   Semantic Layer • AI Analysis • Statistics         │
│   Natural Language → Metrics → Insights            │
└───────────────────────┬─────────────────────────────┘
                        │ extends
┌───────────────────────┴─────────────────────────────┐
│                   sbdk-dev                          │
│   dlt → DuckDB → dbt → Quality → CLI               │
│   Data Ingestion → Transform → Validation          │
└─────────────────────────────────────────────────────┘
```

## Projects

### [knowdb/](./knowdb)

The semantic layer and AI interface:
- **Semantic Layer**: YAML metric definitions, Ibis query generation
- **Intelligence Engine**: Statistical testing, confidence intervals, NLG
- **MCP Tools**: Integration with Claude Desktop, ChatGPT Desktop
- **dbt Bridge**: Auto-sync dbt models to semantic definitions

### [sbdk-dev/](./sbdk-dev)

The data pipeline infrastructure:
- **dlt**: Data ingestion from APIs, databases, SaaS
- **DuckDB**: Local OLAP database
- **dbt**: SQL transformations (staging → marts)
- **Quality Framework**: 6 validators with auto-fix
- **CLI**: Full pipeline orchestration

## Quick Start

```bash
# Clone repository
git clone https://github.com/matt-strautmann/knowdb.git
cd knowdb

# Install both packages
pip install -e ./sbdk-dev
pip install -e ./knowdb

# Initialize project and run pipeline
sbdk init my-analytics && cd my-analytics
sbdk run

# Sync dbt to semantic layer and query
knowdb sync
knowdb query mrr -d segment

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

Use similar MCP configuration format for ChatGPT Desktop.

## Features

- **Multi-AI Support**: Works with any MCP-compatible AI assistant
- **Statistical Rigor**: Automatic confidence intervals and significance testing
- **dbt Integration**: Sync dbt models to semantic layer automatically
- **Local-First**: Runs entirely on your machine with DuckDB
- **Open Source**: MIT License - free for personal and commercial use

## Test Coverage

- **KnowDB**: 109 tests (semantic layer, AI, statistics)
- **sbdk-dev**: 371 tests (pipelines, quality, CLI)
- **Total**: 480 tests

## Open Source

**License**: MIT License

This project is free to use, modify, and distribute for both personal and commercial purposes. See [LICENSE](./LICENSE) for full terms.

## Author

**Matt Strautmann** - November 2025

## Acknowledgments

- Built on patterns from dbt Semantic Layer, Cube.js, and WrenAI
- Uses Model Context Protocol for AI assistant integration
- Inspired by the local-first data movement

---

*This repository is archived as a reference implementation. For questions or to fork for your own use, see the LICENSE file.*
