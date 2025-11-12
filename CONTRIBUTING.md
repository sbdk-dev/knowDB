# Contributing to knowDB

Thank you for your interest in contributing to knowDB! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Examples of behavior that contributes to a positive environment:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Examples of unacceptable behavior:**
- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by opening an issue or contacting the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## How Can I Contribute?

### Reporting Bugs

**Before submitting a bug report:**
- Check the [troubleshooting guide](TROUBLESHOOTING.md)
- Search [existing issues](https://github.com/your-org/knowDB/issues) to avoid duplicates
- Collect information about the bug:
  - Stack trace
  - Operating system and version
  - Python version
  - Database type and version
  - Steps to reproduce

**How to submit a good bug report:**
```markdown
### Description
[Clear description of the issue]

### Steps to Reproduce
1. Configure semantic layer with [specific config]
2. Run query [specific query]
3. See error

### Expected Behavior
[What you expected to happen]

### Actual Behavior
[What actually happened]

### Environment
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.5]
- knowDB version: [e.g., 1.0.0]
- Database: [e.g., DuckDB 0.9.2]

### Stack Trace
```
[Paste stack trace here]
```

### Additional Context
[Any other relevant information]
```

### Suggesting Enhancements

**Before submitting an enhancement:**
- Check if the feature already exists
- Search [existing issues](https://github.com/your-org/knowDB/issues)
- Consider if it fits the project's scope and vision

**How to submit a good enhancement:**
```markdown
### Feature Description
[Clear description of the enhancement]

### Use Case
[Why is this useful? Who benefits?]

### Proposed Solution
[How might this be implemented?]

### Alternatives Considered
[What other approaches did you consider?]

### Additional Context
[Mockups, examples, links to similar features]
```

### Your First Code Contribution

**Good first issues:**
- Look for issues labeled `good-first-issue`
- Documentation improvements
- Test coverage additions
- Bug fixes with clear reproduction steps

**Areas that need help:**
1. Database connector implementations
2. Metric template libraries
3. Integration guides
4. Test coverage
5. Documentation improvements

---

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- uv (will be installed automatically)

### Setup Steps

1. **Fork and clone the repository:**
```bash
git clone https://github.com/your-username/knowDB.git
cd knowDB
```

2. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

3. **Set up development environment:**
```bash
# Run automated setup
./setup.sh

# Or manually:
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
uv pip install -e ".[dev]"
```

4. **Verify setup:**
```bash
# Run tests
uv run pytest tests/ -v

# Test MCP server
uv run python src/mcp_server.py

# Create sample data
uv run python create_sample_data.py
```

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes
# ... edit files ...

# Run tests
uv run pytest tests/ -v

# Check code formatting
uv run black src/ tests/
uv run isort src/ tests/

# Run linter
uv run ruff check src/ tests/

# Commit changes
git add .
git commit -m "feat: add support for XYZ"

# Push to your fork
git push origin feature/your-feature

# Create pull request on GitHub
```

---

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code is formatted (black, isort)
- [ ] Code passes linting (ruff)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions
- [ ] PR description is clear and complete

### PR Title Format

Use conventional commits format:

```
<type>(<scope>): <description>

Examples:
feat(api): add support for BigQuery connector
fix(cache): resolve Redis connection timeout
docs(readme): improve quick start guide
test(metrics): add tests for derived metrics
refactor(semantic-layer): simplify metric resolution
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### PR Description Template

```markdown
## Description
[Clear description of what this PR does]

## Motivation
[Why is this change needed?]

## Changes
- [List of key changes]
- [Another change]

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Documentation
- [ ] README updated if needed
- [ ] Inline code comments added
- [ ] API documentation updated

## Breaking Changes
[List any breaking changes, or write "None"]

## Related Issues
Closes #[issue number]
```

### Review Process

1. **Automated checks:** CI/CD pipeline runs tests and linting
2. **Code review:** Maintainer reviews code
3. **Feedback:** Address any requested changes
4. **Approval:** Maintainer approves PR
5. **Merge:** Maintainer merges to main branch

**Expected timeline:**
- Initial review: Within 3 business days
- Follow-up reviews: Within 2 business days
- Merge after approval: Within 1 business day

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these tools:

**Formatter:**
```bash
# Format code
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/
```

**Import sorting:**
```bash
# Sort imports
uv run isort src/ tests/

# Check import sorting
uv run isort --check src/ tests/
```

**Linter:**
```bash
# Run linter
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/
```

### Code Conventions

**File naming:**
- Use snake_case: `semantic_layer.py`
- Test files: `test_semantic_layer.py`
- Modules: short, descriptive names

**Function/method naming:**
```python
# Good
def query_metric(metric_name: str) -> dict:
    """Query a metric by name."""
    pass

# Bad
def qm(m):
    pass
```

**Class naming:**
```python
# Good
class SemanticLayer:
    """Main semantic layer class."""
    pass

# Bad
class semantic_layer:
    pass
```

**Type hints:**
```python
# Always use type hints
def process_query(
    query: str,
    dimensions: list[str],
    filters: list[str] | None = None
) -> dict[str, Any]:
    """Process a query with dimensions and optional filters."""
    pass
```

**Docstrings:**
```python
def query_metric(metric_name: str, dimensions: list[str]) -> dict:
    """Query a metric with optional dimensions.

    Args:
        metric_name: Name of the metric to query
        dimensions: List of dimension names to group by

    Returns:
        Dictionary with query results and metadata

    Raises:
        MetricNotFoundError: If metric doesn't exist
        QueryExecutionError: If query fails

    Example:
        >>> results = query_metric("total_mrr", ["customer_segment"])
        >>> print(results["data"])
    """
    pass
```

### Error Handling

```python
# Good - specific exceptions
try:
    result = execute_query(sql)
except ConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    raise QueryExecutionError(f"Failed to connect: {e}") from e
except TimeoutError as e:
    logger.warning(f"Query timeout: {e}")
    raise QueryExecutionError(f"Query timed out: {e}") from e

# Bad - generic exceptions
try:
    result = execute_query(sql)
except Exception as e:
    print(f"Error: {e}")
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Good - structured logging
logger.info("Query executed", extra={
    "metric_name": "total_mrr",
    "execution_time_ms": 123,
    "rows_returned": 42
})

# Bad - string concatenation
logger.info(f"Query for {metric} returned {rows} rows")
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   ├── test_semantic_layer.py
│   ├── test_query_cache.py
│   └── test_metrics.py
├── integration/       # Integration tests (database, API)
│   ├── test_database_connectors.py
│   └── test_api_endpoints.py
└── fixtures/          # Test fixtures and data
    ├── sample_metrics.yml
    └── test_data.py
```

### Writing Tests

```python
import pytest
from semantic_layer import SemanticLayer

class TestSemanticLayer:
    """Tests for SemanticLayer class."""

    @pytest.fixture
    def semantic_layer(self):
        """Create a semantic layer instance for testing."""
        return SemanticLayer("tests/fixtures/sample_metrics.yml")

    def test_query_metric_success(self, semantic_layer):
        """Test successful metric query."""
        result = semantic_layer.query_metric("total_mrr")

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

    def test_query_metric_not_found(self, semantic_layer):
        """Test query for non-existent metric."""
        with pytest.raises(MetricNotFoundError):
            semantic_layer.query_metric("non_existent_metric")

    @pytest.mark.parametrize("metric_name,expected_type", [
        ("total_mrr", "simple"),
        ("arr", "derived"),
        ("churn_rate", "derived"),
    ])
    def test_metric_types(self, semantic_layer, metric_name, expected_type):
        """Test different metric types."""
        metric = semantic_layer.get_metric(metric_name)
        assert metric["type"] == expected_type
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_semantic_layer.py -v

# Run tests matching pattern
uv run pytest tests/ -k "test_query" -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run only fast tests
uv run pytest tests/unit/ -v

# Run integration tests
uv run pytest tests/integration/ -v
```

### Test Coverage Requirements

- **Minimum coverage:** 80%
- **New code coverage:** 90%+
- **Critical paths:** 100% coverage

```bash
# Generate coverage report
uv run pytest tests/ --cov=src --cov-report=term-missing

# View HTML report
uv run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Documentation Standards

### Code Documentation

**Module docstrings:**
```python
"""Semantic layer implementation for metric definitions.

This module provides the core semantic layer functionality for defining
and querying business metrics across multiple data warehouses.

Example:
    >>> from semantic_layer import SemanticLayer
    >>> sl = SemanticLayer("metrics.yml")
    >>> result = sl.query_metric("total_mrr")
"""
```

**Class docstrings:**
```python
class SemanticLayer:
    """Main semantic layer interface.

    Loads metric definitions from YAML and executes queries against
    the configured database using Ibis framework.

    Attributes:
        config_path: Path to metrics configuration file
        connection: Database connection instance
        metrics: Dictionary of loaded metric definitions

    Example:
        >>> sl = SemanticLayer("metrics.yml")
        >>> sl.query_metric("total_mrr", dimensions=["segment"])
    """
```

### Markdown Documentation

**Headers:**
```markdown
# Page Title (H1 - only one per page)

## Section (H2)

### Subsection (H3)

#### Detail (H4 - use sparingly)
```

**Code blocks:**
````markdown
```python
# Always specify language
def example():
    return "code example"
```
````

**Links:**
```markdown
[Link text](URL)
[Document link](DOCUMENT.md)
[Anchor link](#section-name)
```

**Images:**
```markdown
![Alt text](path/to/image.png)
```

### API Documentation

Document all public APIs:

```python
def query_metric(
    metric_name: str,
    dimensions: list[str] | None = None,
    filters: list[str] | None = None,
    limit: int = 1000
) -> dict[str, Any]:
    """Query a metric with optional dimensions and filters.

    Args:
        metric_name: Name of metric to query (required)
        dimensions: Column names to group by (optional)
        filters: SQL WHERE conditions (optional)
        limit: Maximum rows to return (default: 1000)

    Returns:
        Dictionary containing:
            - success (bool): Whether query succeeded
            - data (list[dict]): Query results
            - sql (str): Generated SQL
            - execution_time_ms (int): Query execution time

    Raises:
        MetricNotFoundError: Metric not found in configuration
        QueryExecutionError: Query failed to execute
        ValidationError: Invalid parameters

    Example:
        >>> sl = SemanticLayer("metrics.yml")
        >>> result = sl.query_metric(
        ...     "total_mrr",
        ...     dimensions=["customer_segment"],
        ...     filters=["country = 'US'"],
        ...     limit=100
        ... )
        >>> print(result["data"])
        [{"customer_segment": "Enterprise", "total_mrr": 24741.53}, ...]
    """
```

---

## Community

### Communication Channels

- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** Questions and community discussions
- **Discord:** [Coming soon] Real-time chat
- **Twitter:** [@knowDB](https://twitter.com/knowDB) Updates and announcements

### Getting Help

**For questions:**
1. Check documentation first
2. Search existing issues/discussions
3. Ask in GitHub Discussions
4. Join Discord for real-time help

**For bugs:**
1. Check troubleshooting guide
2. Search existing issues
3. Create detailed bug report

### Recognition

We recognize contributors in several ways:

- **Contributors list:** All contributors listed in README
- **Release notes:** Contributions acknowledged in release notes
- **Swag:** Active contributors receive knowDB swag
- **Maintainer status:** Consistent contributors invited to become maintainers

### Becoming a Maintainer

**Requirements:**
- 10+ merged PRs
- Consistent contributions over 3+ months
- Demonstrated knowledge of codebase
- Positive community interaction
- Commitment to project vision

**Responsibilities:**
- Review pull requests
- Triage issues
- Guide new contributors
- Maintain code quality
- Release management

---

## Questions?

If you have questions about contributing, feel free to:
- Open a [GitHub Discussion](https://github.com/your-org/knowDB/discussions)
- Comment on relevant issues
- Reach out to maintainers

Thank you for contributing to knowDB!
