#!/bin/bash
# Setup script for Semantic Layer MCP Server (using uv)
# This script automates the initial setup process

set -e  # Exit on error

echo "🚀 Semantic Layer MCP Server Setup (with uv)"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if uv is installed
echo -e "${BLUE}Checking for uv...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}✓${NC} uv installed"
else
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✓${NC} uv found: $UV_VERSION"
fi

# Check Python version
echo ""
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${YELLOW}⚠️  Python 3.11+ required, found $PYTHON_VERSION${NC}"
    echo "   Please install Python 3.11 or higher"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Remove old venv if exists
if [ -d "venv" ]; then
    echo ""
    echo -e "${BLUE}Removing old venv directory...${NC}"
    rm -rf venv
    echo -e "${GREEN}✓${NC} Old venv removed"
fi

# Remove old requirements.txt if exists (we use pyproject.toml now)
if [ -f "requirements.txt" ]; then
    echo ""
    echo -e "${BLUE}Archiving old requirements.txt...${NC}"
    mv requirements.txt requirements.txt.old
    echo -e "${GREEN}✓${NC} Old requirements.txt archived"
fi

# Initialize uv project (creates .venv)
echo ""
echo -e "${BLUE}Initializing uv environment...${NC}"
uv venv
echo -e "${GREEN}✓${NC} Virtual environment created"

# Install dependencies with uv (much faster than pip!)
echo ""
echo -e "${BLUE}Installing dependencies with uv...${NC}"
echo "   This is much faster than pip! ⚡"
uv pip install mcp ibis-framework[duckdb] pandas numpy duckdb pyyaml python-dotenv pydantic pytest pytest-asyncio black mypy
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create data directory
echo ""
echo -e "${BLUE}Creating data directory...${NC}"
mkdir -p data
echo -e "${GREEN}✓${NC} Data directory created"

# Generate sample data
echo ""
echo -e "${BLUE}Generating sample data...${NC}"
uv run python create_sample_data.py
echo -e "${GREEN}✓${NC} Sample data generated"

# Run tests
echo ""
echo -e "${BLUE}Running tests...${NC}"
uv run pytest tests/test_semantic_layer.py -v --tb=short
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All tests passed"
else
    echo -e "${YELLOW}⚠️  Some tests failed${NC}"
    echo "   Please check the output above"
fi

# Get absolute paths
CURRENT_DIR=$(pwd)
PYTHON_PATH="$CURRENT_DIR/.venv/bin/python"
MCP_SERVER_PATH="$CURRENT_DIR/src/mcp_server.py"
METRICS_PATH="$CURRENT_DIR/semantic_models/metrics.yml"

# Show configuration
echo ""
echo "=============================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}Using uv for fast Python package management ⚡${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure Claude Desktop with these paths:"
echo ""
echo "   File location (macOS):"
echo "   ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo "   File location (Windows):"
echo "   %APPDATA%\\Claude\\claude_desktop_config.json"
echo ""
echo "   Configuration:"
echo ""
echo "   {"
echo "     \"mcpServers\": {"
echo "       \"semantic-layer\": {"
echo "         \"command\": \"$PYTHON_PATH\","
echo "         \"args\": ["
echo "           \"$MCP_SERVER_PATH\""
echo "         ],"
echo "         \"env\": {"
echo "           \"SEMANTIC_MODELS_PATH\": \"$METRICS_PATH\""
echo "         }"
echo "       }"
echo "     }"
echo "   }"
echo ""
echo "2. Restart Claude Desktop"
echo ""
echo "3. Look for the 🔌 icon indicating MCP servers are connected"
echo ""
echo "4. Try asking Claude:"
echo "   - \"What metrics are available?\""
echo "   - \"Show me total MRR\""
echo "   - \"Break down MRR by customer segment\""
echo ""
echo "Useful uv commands:"
echo "   uv run python script.py    # Run a script"
echo "   uv run pytest              # Run tests"
echo "   uv pip install package     # Install a package"
echo "   uv pip list                # List installed packages"
echo ""
echo "For more information:"
echo "   - Quick Start: QUICKSTART.md"
echo "   - Examples: EXAMPLES.md"
echo "   - Troubleshooting: TROUBLESHOOTING.md"
echo ""
