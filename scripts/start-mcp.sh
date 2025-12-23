#!/bin/bash
# Start MCP server for Claude integration

set -e

echo "=== Beyond The Club - MCP Server ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copy .env.example to .env and configure."
fi

# Start API (required) and MCP
echo "Starting API and MCP services..."
docker-compose --profile mcp up -d

echo ""
echo "MCP Server started!"
echo "  - API: http://localhost:8000"
echo "  - MCP: Running (stdio mode)"
echo ""
echo "To use with Claude Desktop, add to claude_desktop_config.json:"
echo '  "mcpServers": {'
echo '    "beyond-the-club": {'
echo '      "command": "docker",'
echo '      "args": ["exec", "-i", "btc-mcp", "python", "-m", "mcp.server"]'
echo '    }'
echo '  }'
echo ""
echo "View logs: docker-compose --profile mcp logs -f"
echo "Stop: docker-compose --profile mcp down"
