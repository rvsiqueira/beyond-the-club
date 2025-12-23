#!/bin/bash
# Build all Docker images

set -e

echo "=== Beyond The Club - Building Docker Images ==="

# Build API
echo ""
echo "Building API image..."
docker build -f Dockerfile.api -t btc-api:latest .

# Build Web
echo ""
echo "Building Web image..."
docker build -f Dockerfile.web -t btc-web:latest .

# Build MCP
echo ""
echo "Building MCP image..."
docker build -f Dockerfile.mcp -t btc-mcp:latest .

echo ""
echo "All images built successfully!"
echo ""
echo "Images:"
docker images | grep btc
