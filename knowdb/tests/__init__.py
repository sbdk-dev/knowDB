"""
KnowDB Test Suite

This package contains comprehensive tests for the KnowDB platform:
- Unit tests (tests/unit/): Fast, isolated component tests
- Integration tests (tests/integration/): Database and cross-component tests
- E2E tests (tests/e2e/): Full workflow tests

Run tests with:
    pytest tests/ -v                    # All tests
    pytest tests/unit/ -v               # Unit tests only
    pytest tests/ -m "not slow" -v      # Skip slow tests
    pytest tests/ --cov=src/knowdb -v   # With coverage
"""
