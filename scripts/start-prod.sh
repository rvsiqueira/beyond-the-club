#!/bin/bash
# Start production environment with Nginx

set -e

echo "=== Beyond The Club - Production Environment ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and configure."
    exit 1
fi

# Check for SSL certificates
if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
    echo "Warning: SSL certificates not found in nginx/ssl/"
    echo "  For HTTPS, add fullchain.pem and privkey.pem"
    echo "  Starting without HTTPS..."
fi

# Build and start all services including Nginx
echo "Building and starting services..."
docker-compose --profile production build
docker-compose --profile production up -d

echo ""
echo "Production services started!"
echo "  - API: http://localhost:8000 (internal)"
echo "  - Web: http://localhost:3000 (internal)"
echo "  - Nginx: http://localhost:80"
echo ""
echo "View logs: docker-compose --profile production logs -f"
echo "Stop: docker-compose --profile production down"
