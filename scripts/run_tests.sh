#!/bin/bash
# Run all tests with coverage report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}====================================${NC}"
echo -e "${YELLOW}  Beyond The Club - Test Suite     ${NC}"
echo -e "${YELLOW}====================================${NC}"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Install test dependencies if needed
echo -e "${YELLOW}Checking test dependencies...${NC}"
pip install -q pytest pytest-asyncio pytest-cov pytest-mock respx

# Run tests based on argument
case "$1" in
    "unit")
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest tests/unit -v --tb=short
        ;;
    "api")
        echo -e "${GREEN}Running API tests...${NC}"
        pytest tests/api -v --tb=short
        ;;
    "mcp")
        echo -e "${GREEN}Running MCP tests...${NC}"
        pytest tests/mcp -v --tb=short
        ;;
    "coverage")
        echo -e "${GREEN}Running all tests with coverage...${NC}"
        pytest tests/ \
            --cov=src \
            --cov=api \
            --cov=mcp_btc \
            --cov-report=html \
            --cov-report=term-missing \
            -v
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "fast")
        echo -e "${GREEN}Running fast tests (no slow markers)...${NC}"
        pytest tests/ -v --tb=short -m "not slow"
        ;;
    *)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest tests/ -v --tb=short
        ;;
esac

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  Tests completed!                  ${NC}"
echo -e "${GREEN}====================================${NC}"
