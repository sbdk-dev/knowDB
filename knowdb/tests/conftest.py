"""
KnowDB Test Configuration and Shared Fixtures

This module provides comprehensive pytest fixtures for the KnowDB testing infrastructure.
All fixtures are designed for:
- Test isolation (each test gets a clean state)
- Performance (reuse connections where safe)
- Reproducibility (seeded random data)
- Realistic data (business-relevant sample data)
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

    from faker import Faker as FakerType
    from typer.testing import CliRunner

# =============================================================================
# Core Database Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary DuckDB database path.

    Returns:
        Path to a temporary .duckdb file that will be cleaned up after test.

    Example:
        def test_something(db_path):
            conn = duckdb.connect(str(db_path))
            # ... test code ...
    """
    return tmp_path / "test.duckdb"


@pytest.fixture
def temp_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Provide an in-memory DuckDB connection.

    Each test gets a fresh, isolated database connection.
    The connection is automatically closed after the test.

    Yields:
        A DuckDB connection to an in-memory database.

    Example:
        def test_query(temp_db):
            temp_db.execute("CREATE TABLE test AS SELECT 1 as id")
            result = temp_db.execute("SELECT * FROM test").fetchone()
            assert result == (1,)
    """
    conn = duckdb.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def temp_db_file(
    tmp_path: Path,
) -> Generator[tuple[Path, duckdb.DuckDBPyConnection], None, None]:
    """Provide a file-based DuckDB database with its path.

    Useful when you need to test persistence or file operations.

    Yields:
        Tuple of (database_path, connection).

    Example:
        def test_persistence(temp_db_file):
            db_path, conn = temp_db_file
            conn.execute("CREATE TABLE test AS SELECT 'data' as value")
            assert db_path.exists()
    """
    db_path = tmp_path / "test.db"
    conn = duckdb.connect(str(db_path))
    try:
        yield db_path, conn
    finally:
        conn.close()


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_users_df() -> pd.DataFrame:
    """Generate a reproducible sample users DataFrame.

    Uses Faker with a fixed seed for deterministic test data.
    Contains 100 users with realistic business data.

    Returns:
        DataFrame with columns: user_id, name, email, age, created_at, country, segment

    Example:
        def test_user_processing(sample_users_df):
            assert len(sample_users_df) == 100
            assert "email" in sample_users_df.columns
    """
    from faker import Faker

    fake = Faker()
    Faker.seed(42)

    users = []
    segments = ["Enterprise", "SMB", "Startup", "Individual"]
    countries = ["USA", "UK", "Germany", "France", "Canada", "Australia", "Japan"]

    for i in range(100):
        users.append(
            {
                "user_id": i + 1,
                "name": fake.name(),
                "email": fake.email(),
                "age": fake.random_int(min=18, max=80),
                "created_at": fake.date_time_between(
                    start_date="-2y", end_date="now"
                ).isoformat(),
                "country": fake.random_element(countries),
                "segment": fake.random_element(segments),
            }
        )

    return pd.DataFrame(users)


@pytest.fixture
def sample_orders_df(sample_users_df: pd.DataFrame) -> pd.DataFrame:
    """Generate sample orders DataFrame with foreign key to users.

    Creates 500 orders distributed across the sample users.

    Args:
        sample_users_df: Fixture that provides user data.

    Returns:
        DataFrame with columns: order_id, user_id, amount, status, order_date, product_category

    Example:
        def test_order_analysis(sample_orders_df):
            assert sample_orders_df["status"].isin(["completed", "pending", "cancelled", "refunded"]).all()
    """
    from faker import Faker

    fake = Faker()
    Faker.seed(42)

    orders = []
    statuses = ["completed", "pending", "cancelled", "refunded"]
    categories = ["Electronics", "Clothing", "Books", "Home", "Sports", "Beauty"]
    user_ids = sample_users_df["user_id"].tolist()

    for i in range(500):
        orders.append(
            {
                "order_id": i + 1,
                "user_id": fake.random_element(user_ids),
                "amount": round(fake.pyfloat(min_value=10.0, max_value=1000.0), 2),
                "status": fake.random_element(statuses),
                "order_date": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat(),
                "product_category": fake.random_element(categories),
            }
        )

    return pd.DataFrame(orders)


@pytest.fixture
def sample_events_df(sample_users_df: pd.DataFrame) -> pd.DataFrame:
    """Generate sample analytics events DataFrame.

    Creates 1000 events with various event types.

    Args:
        sample_users_df: Fixture that provides user data.

    Returns:
        DataFrame with columns: event_id, user_id, event_type, timestamp, properties

    Example:
        def test_event_tracking(sample_events_df):
            event_types = sample_events_df["event_type"].unique()
            assert "page_view" in event_types
    """
    from faker import Faker

    fake = Faker()
    Faker.seed(42)

    events = []
    event_types = ["page_view", "click", "purchase", "signup", "logout", "search", "add_to_cart"]
    user_ids = sample_users_df["user_id"].tolist()

    for i in range(1000):
        event_type = fake.random_element(event_types)
        properties = {
            "session_id": fake.uuid4(),
            "device": fake.random_element(["desktop", "mobile", "tablet"]),
            "browser": fake.random_element(["Chrome", "Firefox", "Safari", "Edge"]),
        }

        if event_type == "page_view":
            properties["page"] = fake.random_element(["/home", "/products", "/cart", "/checkout"])
        elif event_type == "search":
            properties["query"] = fake.word()

        events.append(
            {
                "event_id": i + 1,
                "user_id": fake.random_element(user_ids),
                "event_type": event_type,
                "timestamp": fake.date_time_between(
                    start_date="-30d", end_date="now"
                ).isoformat(),
                "properties": json.dumps(properties),
            }
        )

    return pd.DataFrame(events)


@pytest.fixture
def sample_mrr_df() -> pd.DataFrame:
    """Generate sample Monthly Recurring Revenue (MRR) data.

    Creates realistic MRR snapshots with various MRR types for business analytics.

    Returns:
        DataFrame with columns: month, mrr_type, amount, customer_count

    Example:
        def test_mrr_analysis(sample_mrr_df):
            total_mrr = sample_mrr_df.groupby("month")["amount"].sum()
            assert total_mrr.iloc[-1] > total_mrr.iloc[0]  # Growth trend
    """
    from faker import Faker

    fake = Faker()
    Faker.seed(42)

    mrr_data = []
    mrr_types = ["new", "expansion", "contraction", "churn", "reactivation"]

    # Generate 12 months of data
    base_date = datetime(2024, 1, 1)
    for month_offset in range(12):
        month = (base_date + timedelta(days=30 * month_offset)).strftime("%Y-%m")

        for mrr_type in mrr_types:
            # Realistic distribution based on MRR type
            if mrr_type == "new":
                amount = fake.pyfloat(min_value=5000, max_value=15000)
                count = fake.random_int(min=10, max=50)
            elif mrr_type == "expansion":
                amount = fake.pyfloat(min_value=2000, max_value=8000)
                count = fake.random_int(min=5, max=30)
            elif mrr_type == "contraction":
                amount = -fake.pyfloat(min_value=500, max_value=3000)
                count = fake.random_int(min=2, max=15)
            elif mrr_type == "churn":
                amount = -fake.pyfloat(min_value=2000, max_value=8000)
                count = fake.random_int(min=3, max=20)
            else:  # reactivation
                amount = fake.pyfloat(min_value=1000, max_value=5000)
                count = fake.random_int(min=1, max=10)

            mrr_data.append(
                {
                    "month": month,
                    "mrr_type": mrr_type,
                    "amount": round(amount, 2),
                    "customer_count": count,
                }
            )

    return pd.DataFrame(mrr_data)


@pytest.fixture
def time_series_data() -> pd.DataFrame:
    """Generate time series data for trend analysis testing.

    Creates 91 days (Q1) of daily metrics with realistic patterns.

    Returns:
        DataFrame with columns: date, daily_users, daily_revenue, daily_orders

    Example:
        def test_trend_analysis(time_series_data):
            assert len(time_series_data) == 91  # Q1 days
    """
    import numpy as np
    from faker import Faker

    fake = Faker()
    Faker.seed(42)
    np.random.seed(42)

    dates = pd.date_range(start="2024-01-01", end="2024-03-31", freq="D")
    n = len(dates)

    # Create data with weekly seasonality and growth trend
    trend = np.linspace(500, 800, n)
    weekly_pattern = 50 * np.sin(np.arange(n) * 2 * np.pi / 7)
    noise = np.random.normal(0, 30, n)

    daily_users = (trend + weekly_pattern + noise).astype(int)
    daily_users = np.clip(daily_users, 100, 1000)

    return pd.DataFrame(
        {
            "date": dates,
            "daily_users": daily_users,
            "daily_revenue": np.round(daily_users * np.random.uniform(8, 12, n), 2),
            "daily_orders": (daily_users * np.random.uniform(0.1, 0.15, n)).astype(int),
        }
    )


# =============================================================================
# Populated Database Fixtures
# =============================================================================


@pytest.fixture
def populated_db(
    temp_db: duckdb.DuckDBPyConnection,
    sample_users_df: pd.DataFrame,
    sample_orders_df: pd.DataFrame,
    sample_events_df: pd.DataFrame,
    sample_mrr_df: pd.DataFrame,
) -> duckdb.DuckDBPyConnection:
    """Provide a database pre-populated with all sample data.

    Combines multiple sample DataFrames into a queryable database.
    Useful for integration tests that need realistic data relationships.

    Args:
        temp_db: In-memory database connection.
        sample_users_df: Sample user data.
        sample_orders_df: Sample order data.
        sample_events_df: Sample event data.
        sample_mrr_df: Sample MRR data.

    Returns:
        DuckDB connection with populated tables.

    Example:
        def test_user_orders_join(populated_db):
            result = populated_db.execute('''
                SELECT u.name, SUM(o.amount) as total
                FROM users u JOIN orders o ON u.user_id = o.user_id
                GROUP BY u.name
            ''').df()
            assert len(result) > 0
    """
    temp_db.register("users", sample_users_df)
    temp_db.register("orders", sample_orders_df)
    temp_db.register("events", sample_events_df)
    temp_db.register("mrr_snapshots", sample_mrr_df)

    # Create permanent tables
    temp_db.execute("CREATE TABLE users AS SELECT * FROM users")
    temp_db.execute("CREATE TABLE orders AS SELECT * FROM orders")
    temp_db.execute("CREATE TABLE events AS SELECT * FROM events")
    temp_db.execute("CREATE TABLE mrr_snapshots AS SELECT * FROM mrr_snapshots")

    return temp_db


# =============================================================================
# Semantic Layer Fixtures
# =============================================================================


@pytest.fixture
def semantic_models_path(tmp_path: Path) -> Path:
    """Create a temporary semantic models YAML file.

    Provides a realistic metrics.yml configuration for testing
    the semantic layer manager.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to the created metrics.yml file.

    Example:
        def test_semantic_layer(semantic_models_path):
            manager = SemanticLayerManager(semantic_models_path)
            metrics = manager.list_metrics()
            assert "mrr" in [m.name for m in metrics]
    """
    metrics_config = {
        "version": "1.0",
        "metrics": [
            {
                "name": "mrr",
                "display_name": "Monthly Recurring Revenue",
                "type": "simple",
                "description": "Total monthly recurring revenue",
                "calculation": {
                    "table": "mrr_snapshots",
                    "aggregation": "sum",
                    "column": "amount",
                },
                "dimensions": ["month", "mrr_type"],
            },
            {
                "name": "active_users",
                "display_name": "Active Users",
                "type": "simple",
                "description": "Count of unique active users",
                "calculation": {
                    "table": "users",
                    "aggregation": "count_distinct",
                    "column": "user_id",
                },
                "dimensions": ["segment", "country"],
            },
            {
                "name": "total_orders",
                "display_name": "Total Orders",
                "type": "simple",
                "description": "Total number of orders",
                "calculation": {
                    "table": "orders",
                    "aggregation": "count",
                    "column": "order_id",
                },
                "dimensions": ["status", "product_category"],
            },
            {
                "name": "total_revenue",
                "display_name": "Total Revenue",
                "type": "simple",
                "description": "Sum of all order amounts",
                "calculation": {
                    "table": "orders",
                    "aggregation": "sum",
                    "column": "amount",
                },
                "dimensions": ["status", "product_category"],
            },
            {
                "name": "avg_order_value",
                "display_name": "Average Order Value",
                "type": "derived",
                "description": "Average value per order",
                "formula": "total_revenue / total_orders",
                "dimensions": ["status", "product_category"],
            },
        ],
        "dimensions": [
            {
                "name": "month",
                "type": "temporal",
                "table": "mrr_snapshots",
                "column": "month",
            },
            {
                "name": "mrr_type",
                "type": "categorical",
                "table": "mrr_snapshots",
                "column": "mrr_type",
            },
            {
                "name": "segment",
                "type": "categorical",
                "table": "users",
                "column": "segment",
            },
            {
                "name": "country",
                "type": "categorical",
                "table": "users",
                "column": "country",
            },
            {
                "name": "status",
                "type": "categorical",
                "table": "orders",
                "column": "status",
            },
            {
                "name": "product_category",
                "type": "categorical",
                "table": "orders",
                "column": "product_category",
            },
        ],
    }

    metrics_path = tmp_path / "metrics.yml"
    with open(metrics_path, "w") as f:
        yaml.dump(metrics_config, f, default_flow_style=False)

    return metrics_path


@pytest.fixture
def semantic_layer(
    populated_db: duckdb.DuckDBPyConnection, semantic_models_path: Path
) -> Any:
    """Provide a configured SemanticLayerManager for testing.

    This fixture provides a fully configured semantic layer that can
    execute metric queries against the populated database.

    Note: Returns Any type to avoid import errors when semantic_layer
    module is not yet implemented.

    Args:
        populated_db: Database with sample data.
        semantic_models_path: Path to metrics.yml.

    Returns:
        Configured SemanticLayerManager instance.

    Example:
        def test_metric_query(semantic_layer):
            result = semantic_layer.query_metric("mrr")
            assert "mrr" in result.columns
    """
    # Import here to allow tests to run even if module doesn't exist yet
    try:
        from knowdb.semantic_layer.manager import SemanticLayerManager

        return SemanticLayerManager(
            models_path=str(semantic_models_path),
            connection=populated_db,
        )
    except ImportError:
        pytest.skip("SemanticLayerManager not yet implemented")


# =============================================================================
# CLI Testing Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> "CliRunner":
    """Provide a Typer CLI test runner.

    Returns:
        CliRunner instance for testing CLI commands.

    Example:
        def test_cli_command(cli_runner):
            from knowdb.cli.main import app
            result = cli_runner.invoke(app, ["--help"])
            assert result.exit_code == 0
    """
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory structure.

    Sets up a minimal KnowDB project structure for testing
    project management and CLI commands.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to the project root directory.

    Example:
        def test_project_init(temp_project_dir):
            config_path = temp_project_dir / "knowdb.yml"
            assert config_path.exists()
    """
    # Create directory structure
    (tmp_path / "data").mkdir()
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "semantic").mkdir()
    (tmp_path / ".knowdb").mkdir()

    # Create basic config
    config = {
        "project": "test_project",
        "version": "1.0",
        "database": {
            "type": "duckdb",
            "path": "data/test.duckdb",
        },
        "semantic_models": "models/semantic/metrics.yml",
    }

    with open(tmp_path / "knowdb.yml", "w") as f:
        yaml.dump(config, f)

    return tmp_path


# =============================================================================
# MCP Server Testing Fixtures
# =============================================================================


@pytest.fixture
def mock_mcp_server() -> Generator[MagicMock, None, None]:
    """Provide a mock MCP server for testing.

    Creates a mock FastMCP server that can be used to test
    MCP tool implementations without running a real server.

    Yields:
        MagicMock configured as an MCP server.

    Example:
        def test_mcp_tool(mock_mcp_server):
            result = await mock_mcp_server.call_tool("list_metrics", {})
            assert "metrics" in result
    """
    mock_server = MagicMock()
    mock_server.tools = {}
    mock_server.resources = {}

    async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
        if name in mock_server.tools:
            return await mock_server.tools[name](arguments)
        raise ValueError(f"Unknown tool: {name}")

    mock_server.call_tool = call_tool
    yield mock_server


@pytest.fixture
def mock_llm_response() -> Callable[[str], MagicMock]:
    """Factory fixture for mocking LLM responses.

    Returns a factory function that creates mocked LLM responses
    for testing AI agent components.

    Returns:
        Factory function that creates mock responses.

    Example:
        def test_ai_agent(mock_llm_response):
            mock = mock_llm_response("The MRR is $50,000")
            with patch("knowdb.intelligence.agent.call_llm", return_value=mock):
                result = agent.interpret_results(data)
    """

    def factory(response_text: str) -> MagicMock:
        mock = MagicMock()
        mock.content = response_text
        mock.usage = {"input_tokens": 100, "output_tokens": 50}
        return mock

    return factory


# =============================================================================
# Data Generation Fixtures
# =============================================================================


@pytest.fixture
def test_data_generator() -> "FakerType":
    """Provide a seeded Faker instance for test data generation.

    Uses a fixed seed for reproducible test data.

    Returns:
        Configured Faker instance.

    Example:
        def test_with_fake_data(test_data_generator):
            name = test_data_generator.name()
            email = test_data_generator.email()
    """
    from faker import Faker

    fake = Faker()
    Faker.seed(42)
    return fake


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    """Create a directory for snapshot testing.

    Useful for regression testing where you compare current
    output against saved snapshots.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to the .snapshots directory.

    Example:
        def test_output_snapshot(snapshot_dir):
            output = generate_report()
            snapshot_path = snapshot_dir / "report.json"
            # Compare or save snapshot
    """
    snapshot_path = tmp_path / ".snapshots"
    snapshot_path.mkdir()
    return snapshot_path


# =============================================================================
# Environment & Configuration Fixtures
# =============================================================================


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Provide a clean environment for testing.

    Removes KnowDB-specific environment variables to ensure
    tests run in a controlled environment.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        The monkeypatch fixture for further modifications.

    Example:
        def test_default_config(clean_env):
            # No KNOWDB_* env vars are set
            config = load_default_config()
    """
    # Remove any KnowDB environment variables
    env_vars = [
        "KNOWDB_DATABASE_PATH",
        "KNOWDB_MODELS_PATH",
        "KNOWDB_CACHE_DIR",
        "KNOWDB_LOG_LEVEL",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    return monkeypatch


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Provide a temporary cache directory.

    Useful for testing caching functionality.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to the cache directory.

    Example:
        def test_query_cache(temp_cache_dir):
            cache = QueryCache(cache_dir=temp_cache_dir)
            cache.set("key", "value")
            assert cache.get("key") == "value"
    """
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    return cache_dir


# =============================================================================
# Async Testing Fixtures
# =============================================================================


@pytest.fixture
def event_loop_policy():
    """Configure the asyncio event loop policy for tests.

    This is automatically used by pytest-asyncio for async tests.
    """
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def large_dataset(sample_users_df: pd.DataFrame) -> pd.DataFrame:
    """Generate a large dataset for performance testing.

    Creates 100,000 rows for benchmarking query performance.

    Args:
        sample_users_df: Base user data to replicate.

    Returns:
        Large DataFrame with 100,000 rows.

    Example:
        @pytest.mark.performance
        def test_query_performance(large_dataset, temp_db):
            temp_db.register("large_users", large_dataset)
            start = time.time()
            result = temp_db.execute("SELECT COUNT(*) FROM large_users").fetchone()
            assert time.time() - start < 1.0  # Under 1 second
    """
    # Replicate data to get 100,000 rows
    return pd.concat([sample_users_df] * 1000, ignore_index=True)


# =============================================================================
# Pytest Configuration Hooks
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Modify test collection to add markers based on path."""
    for item in items:
        # Auto-mark tests based on directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


# =============================================================================
# Fixture Documentation
# =============================================================================

# This file provides the following fixture categories:
#
# 1. Core Database Fixtures:
#    - db_path: Temporary database file path
#    - temp_db: In-memory DuckDB connection
#    - temp_db_file: File-based database with path
#
# 2. Sample Data Fixtures:
#    - sample_users_df: 100 realistic user records
#    - sample_orders_df: 500 orders with foreign keys
#    - sample_events_df: 1000 analytics events
#    - sample_mrr_df: 12 months of MRR data
#    - time_series_data: 91 days of daily metrics
#
# 3. Populated Database:
#    - populated_db: Database with all sample tables
#
# 4. Semantic Layer:
#    - semantic_models_path: Metrics.yml configuration
#    - semantic_layer: Configured SemanticLayerManager
#
# 5. CLI Testing:
#    - cli_runner: Typer CliRunner
#    - temp_project_dir: Project directory structure
#
# 6. MCP Server:
#    - mock_mcp_server: Mock FastMCP server
#    - mock_llm_response: Factory for LLM response mocks
#
# 7. Data Generation:
#    - test_data_generator: Seeded Faker instance
#    - snapshot_dir: Directory for snapshot testing
#
# 8. Environment:
#    - clean_env: Clean environment variables
#    - temp_cache_dir: Temporary cache directory
#
# 9. Performance:
#    - large_dataset: 100,000 row dataset
