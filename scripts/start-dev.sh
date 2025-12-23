#!/bin/bash
# Start development environment

set -e

echo "=== Beyond The Club - Development Environment ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copy .env.example to .env and configure."
fi

# Start API and Web services
echo "Starting API and Web services..."
docker-compose up -d api web

echo ""
echo "Services started!"
echo "  - API: http://localhost:8000"
echo "  - Web: http://localhost:3000"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop: docker-compose down"
