"""KnowDB CLI - Semantic layer commands extending sbdk-dev.

This CLI extends sbdk-dev with semantic layer and AI analytics capabilities.
Use sbdk commands for data pipelines: sbdk run, sbdk query, sbdk test
Use knowdb commands for semantic analysis: knowdb analyze, knowdb sync
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

# Import from sbdk-dev
try:
    from sbdk.cli import app as sbdk_app
    SBDK_AVAILABLE = True
except ImportError:
    SBDK_AVAILABLE = False

# Import knowdb modules
from knowdb.semantic_layer import SemanticLayerManager
from knowdb.intelligence import StatisticalTester, IntelligenceEngine
from knowdb.optimization import QueryCache
from knowdb.bridge import DbtSemanticBridge
from knowdb.mcp.semantic_tools import SemanticTools

# Create CLI app
app = typer.Typer(
    name="knowdb",
    help="AI semantic layer for local analytics - extends sbdk-dev",
    add_completion=True,
)

console = Console()

# Global state
_semantic_layer: Optional[SemanticLayerManager] = None
_tools: Optional[SemanticTools] = None


def get_semantic_layer() -> SemanticLayerManager:
    """Get or create semantic layer instance."""
    global _semantic_layer
    if _semantic_layer is None:
        config_path = Path("semantic_models/metrics.yml")
        if not config_path.exists():
            console.print("[red]Error:[/red] semantic_models/metrics.yml not found")
            console.print("Run 'knowdb sync' to generate from dbt models")
            raise typer.Exit(1)
        _semantic_layer = SemanticLayerManager(str(config_path))
    return _semantic_layer


def get_tools() -> SemanticTools:
    """Get or create semantic tools instance."""
    global _tools
    if _tools is None:
        sl = get_semantic_layer()
        _tools = SemanticTools(
            semantic_manager=sl,
            statistical_tester=StatisticalTester(),
            intelligence_engine=IntelligenceEngine(),
        )
    return _tools


# ============================================================================
# Semantic Layer Commands
# ============================================================================

@app.command()
def query(
    metric: str = typer.Argument(..., help="Metric name to query"),
    dimensions: Optional[list[str]] = typer.Option(None, "--dim", "-d", help="Dimensions to group by"),
    filters: Optional[list[str]] = typer.Option(None, "--filter", "-f", help="Filters (dim=value)"),
    format: str = typer.Option("table", "--format", "-o", help="Output format: table, json, csv"),
    stats: bool = typer.Option(True, "--stats/--no-stats", help="Include statistical analysis"),
):
    """Query a semantic layer metric with optional dimensions and filters.

    Examples:
        knowdb query mrr
        knowdb query mrr -d segment
        knowdb query mrr -d segment -d month -f segment=Enterprise
    """
    tools = get_tools()

    # Parse filters
    filter_dict = {}
    if filters:
        for f in filters:
            if "=" in f:
                key, value = f.split("=", 1)
                filter_dict[key.strip()] = value.strip()

    # Execute query
    result = tools.query_metric(
        metric,
        dimensions=dimensions,
        filters=filter_dict if filter_dict else None
    )

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    # Format output
    if format == "json":
        console.print(json.dumps(result, indent=2, default=str))
    elif format == "csv":
        data = result.get("result", [])
        if data:
            import csv
            import sys
            writer = csv.DictWriter(sys.stdout, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    else:  # table
        data = result.get("result", [])
        if data:
            table = Table(title=f"Metric: {metric}")
            for key in data[0].keys():
                table.add_column(key)
            for row in data:
                table.add_row(*[str(v) for v in row.values()])
            console.print(table)

        # Show statistics if requested
        if stats and "statistics" in result:
            stats_data = result["statistics"]
            console.print("\n[bold]Statistical Analysis:[/bold]")
            for key, value in stats_data.items():
                console.print(f"  {key}: {value}")


@app.command()
def list_metrics(
    format: str = typer.Option("table", "--format", "-o", help="Output format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
):
    """List all available metrics in the semantic layer."""
    tools = get_tools()
    metrics = tools.list_metrics()

    if format == "json":
        console.print(json.dumps(metrics, indent=2))
    else:
        table = Table(title="Available Metrics")
        table.add_column("Name")
        table.add_column("Type")
        if verbose:
            table.add_column("Description")
            table.add_column("Table")

        for metric in metrics:
            if verbose:
                table.add_row(
                    metric["name"],
                    metric.get("type", "simple"),
                    metric.get("description", ""),
                    metric.get("table", "")
                )
            else:
                table.add_row(metric["name"], metric.get("type", "simple"))

        console.print(table)


@app.command()
def explain(
    metric: str = typer.Argument(..., help="Metric name to explain"),
):
    """Explain how a metric is calculated."""
    tools = get_tools()
    explanation = tools.explain_metric(metric)

    if "error" in explanation:
        console.print(f"[red]Error:[/red] {explanation['error']}")
        raise typer.Exit(1)

    console.print(f"\n[bold]{explanation.get('name', metric)}[/bold]")
    console.print(f"Type: {explanation.get('type', 'unknown')}")
    console.print(f"Description: {explanation.get('description', 'No description')}")
    console.print(f"\nCalculation:")
    console.print(f"  Table: {explanation.get('table', 'unknown')}")
    console.print(f"  Column: {explanation.get('column', 'unknown')}")
    console.print(f"  Aggregation: {explanation.get('aggregation', 'unknown')}")

    if "dimensions" in explanation:
        console.print(f"\nCompatible Dimensions: {', '.join(explanation['dimensions'])}")


@app.command()
def analyze(
    question: str = typer.Argument(..., help="Natural language question"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed analysis"),
):
    """Analyze data using natural language (AI-powered).

    Examples:
        knowdb analyze "What is our MRR?"
        knowdb analyze "Compare MRR by segment"
        knowdb analyze "Show MRR trend over the last 6 months"
    """
    tools = get_tools()

    console.print(f"[dim]Analyzing: {question}[/dim]\n")

    # Get suggestions for the question
    suggestions = tools.suggest_analysis(question)

    if suggestions.get("metrics"):
        console.print("[bold]Suggested metrics:[/bold]")
        for metric in suggestions["metrics"]:
            console.print(f"  • {metric}")

    if suggestions.get("dimensions"):
        console.print("\n[bold]Suggested dimensions:[/bold]")
        for dim in suggestions["dimensions"]:
            console.print(f"  • {dim}")

    if suggestions.get("query"):
        console.print(f"\n[bold]Suggested query:[/bold]")
        console.print(f"  knowdb query {suggestions['query']}")


# ============================================================================
# dbt Integration Commands
# ============================================================================

@app.command()
def sync(
    dbt_path: Path = typer.Option(
        Path("dbt"),
        "--dbt-path",
        "-p",
        help="Path to dbt project"
    ),
    output: Path = typer.Option(
        Path("semantic_models/metrics.yml"),
        "--output",
        "-o",
        help="Output path for semantic models"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
):
    """Sync dbt models to semantic layer definitions.

    Extracts metrics and dimensions from dbt mart models and generates
    a semantic layer YAML file.
    """
    bridge = DbtSemanticBridge(str(dbt_path), str(output))

    console.print(f"[bold]Syncing dbt models to semantic layer[/bold]")
    console.print(f"  dbt path: {dbt_path}")
    console.print(f"  output: {output}\n")

    if dry_run:
        models = bridge.discover_models()
        console.print(f"[dim]Dry run - would process {len(models)} models[/dim]")
        for model in models:
            console.print(f"  • {model.name}")
        return

    result = bridge.sync()

    console.print(f"[green]✓[/green] Sync complete!")
    console.print(f"  Models processed: {result.models_processed}")
    console.print(f"  Metrics generated: {result.metrics_generated}")
    console.print(f"  Dimensions generated: {result.dimensions_generated}")
    console.print(f"\nSemantic layer written to: {output}")


@app.command()
def dbt_models(
    dbt_path: Path = typer.Option(Path("dbt"), "--dbt-path", "-p", help="Path to dbt project"),
):
    """List dbt models available for semantic layer sync."""
    bridge = DbtSemanticBridge(str(dbt_path), "")
    models = bridge.discover_models()

    table = Table(title="dbt Models")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Columns")

    for model in models:
        table.add_row(
            model.name,
            model.model_type,
            str(len(model.columns))
        )

    console.print(table)


# ============================================================================
# MCP Server Command
# ============================================================================

@app.command()
def serve(
    host: str = typer.Option("localhost", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
):
    """Start the MCP server for Claude Desktop integration."""
    console.print(f"[bold]Starting KnowDB MCP Server[/bold]")
    console.print(f"  Host: {host}")
    console.print(f"  Port: {port}")
    console.print("\nPress Ctrl+C to stop\n")

    from knowdb.mcp.server import run_server
    run_server(host=host, port=port)


# ============================================================================
# Utility Commands
# ============================================================================

@app.command()
def cache_stats():
    """Show query cache statistics."""
    sl = get_semantic_layer()
    stats = sl.cache_stats()

    console.print("[bold]Query Cache Statistics[/bold]")
    console.print(f"  Total queries: {stats.get('total', 0)}")
    console.print(f"  Cache hits: {stats.get('hits', 0)}")
    console.print(f"  Cache misses: {stats.get('misses', 0)}")
    console.print(f"  Hit rate: {stats.get('hit_rate', 0):.1%}")


@app.command()
def clear_cache():
    """Clear the query cache."""
    sl = get_semantic_layer()
    sl.clear_cache()
    console.print("[green]✓[/green] Cache cleared")


@app.command()
def version():
    """Show version information."""
    from knowdb import __version__
    console.print(f"KnowDB version: {__version__}")

    if SBDK_AVAILABLE:
        from sbdk import __version__ as sbdk_version
        console.print(f"sbdk-dev version: {sbdk_version}")
    else:
        console.print("[yellow]sbdk-dev: not installed[/yellow]")


# ============================================================================
# Add sbdk commands if available
# ============================================================================

if SBDK_AVAILABLE:
    # Add sbdk as a subcommand group for full pipeline access
    app.add_typer(sbdk_app, name="pipeline", help="sbdk-dev pipeline commands (run, test, query)")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
