#!/bin/bash
# Start MCP server for voice agents and remote clients

set -e

echo "=== Beyond The Club - MCP Server (SSE) ==="

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
echo "  - MCP: http://localhost:8001 (SSE mode)"
echo ""
echo "SSE Endpoints:"
echo "  - SSE Stream:  GET  http://localhost:8001/sse"
echo "  - Messages:    POST http://localhost:8001/messages/"
echo ""
echo "For voice agents (Twilio/etc), connect to the SSE endpoint:"
echo "  MCP_URL=http://your-server:8001/sse"
echo ""
echo "View logs: docker-compose --profile mcp logs -f"
echo "Stop: docker-compose --profile mcp down"
