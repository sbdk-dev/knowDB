# KnowDB Project - Archive November 2025

> **Public Archive Notice**: This project is being archived as a complete local-first agentic analytics platform. It demonstrates semantic layer design, MCP integration, and sbdk-dev extension patterns.

## Project Overview

KnowDB is an **AI semantic layer** that extends sbdk-dev for local-first analytics. It enables natural language queries through AI assistants (Claude Desktop, ChatGPT Desktop) via the Model Context Protocol.

### Architecture

```
KnowDB (Semantic Layer + AI)
        ↓ extends
sbdk-dev (dlt → DuckDB → dbt → Quality)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Semantic Layer | `knowdb/src/knowdb/semantic_layer/` | YAML metrics, Ibis queries |
| Intelligence | `knowdb/src/knowdb/intelligence/` | Statistical testing, NLG |
| MCP Tools | `knowdb/src/knowdb/mcp/` | AI assistant integration |
| dbt Bridge | `knowdb/src/knowdb/bridge/` | dbt → semantic sync |
| sbdk-dev | `sbdk-dev/` | Data pipeline infrastructure |

### Quick Commands

```bash
# Data pipeline (sbdk-dev)
sbdk run                    # Full pipeline
sbdk run --dbt-only         # Just transformations

# Semantic layer (knowdb)
knowdb sync                 # dbt → semantic
knowdb query mrr -d segment # Query metrics
knowdb analyze "What is MRR?" # AI analysis
knowdb serve                # Start MCP server
```

## Development Notes

### Test Coverage
- KnowDB unique: 109 tests
- sbdk-dev: 371 tests
- Total: 480 tests

### Dependencies
- KnowDB extends sbdk-dev (not duplicates)
- Uses sbdk for: CLI, quality, incremental, testing
- Adds: semantic layer, AI agents, statistics, dbt bridge

## Open Source

**License**: MIT - Free for personal and commercial use.

## Author

Matt Strautmann - November 2025
