#!/bin/bash
# Setup script for Semantic Layer MCP Server
# This script automates the initial setup process

set -e  # Exit on error

echo "🚀 Semantic Layer MCP Server Setup"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${YELLOW}⚠️  Python 3.11+ required, found $PYTHON_VERSION${NC}"
    echo "   Please install Python 3.11 or higher"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Create virtual environment
echo ""
echo -e "${BLUE}Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  venv directory already exists${NC}"
    read -p "   Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment recreated"
    else
        echo "   Using existing virtual environment"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo ""
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Upgrade pip
echo ""
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✓${NC} pip upgraded"

# Install dependencies
echo ""
echo -e "${BLUE}Installing dependencies...${NC}"
echo "   This may take a few minutes..."
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create data directory
echo ""
echo -e "${BLUE}Creating data directory...${NC}"
mkdir -p data
echo -e "${GREEN}✓${NC} Data directory created"

# Generate sample data
echo ""
echo -e "${BLUE}Generating sample data...${NC}"
python create_sample_data.py
echo -e "${GREEN}✓${NC} Sample data generated"

# Run tests
echo ""
echo -e "${BLUE}Running tests...${NC}"
python -m pytest tests/test_semantic_layer.py -v --tb=short
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All tests passed"
else
    echo -e "${YELLOW}⚠️  Some tests failed${NC}"
    echo "   Please check the output above"
fi

# Get absolute paths
CURRENT_DIR=$(pwd)
PYTHON_PATH="$CURRENT_DIR/venv/bin/python"
MCP_SERVER_PATH="$CURRENT_DIR/src/mcp_server.py"
METRICS_PATH="$CURRENT_DIR/semantic_models/metrics.yml"

# Show configuration
echo ""
echo "===================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "===================================="
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
echo "For more information:"
echo "   - Quick Start: QUICKSTART.md"
echo "   - Examples: EXAMPLES.md"
echo "   - Troubleshooting: TROUBLESHOOTING.md"
echo ""
