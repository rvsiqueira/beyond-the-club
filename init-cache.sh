#!/bin/bash
# Initialize cache files for Docker deployment
# Run this script before 'docker-compose up' to ensure all cache files exist

set -e

echo "=== Initializing Beyond The Club cache files ==="

# Create directories
echo "Creating directories..."
mkdir -p cache
mkdir -p data

# Cache files in ./cache/ directory (mounted to /app/)
CACHE_FILES=(
    "cache/.beyondtheclub_tokens.json"
    "cache/.beyondtheclub_members.json"
    "cache/.beyondtheclub_availability.json"
    "cache/.beyondtheclub_preferences.json"
)

# Data files in ./data/ directory
DATA_FILES=(
    "data/users.json"
    "data/graph.json"
    "data/.beyondtheclub_user_tokens.json"
)

# Create cache files with empty JSON object if they don't exist
echo "Creating cache files..."
for file in "${CACHE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  Creating $file"
        echo '{}' > "$file"
    else
        echo "  $file already exists"
    fi
done

# Create data files with empty JSON object if they don't exist
echo "Creating data files..."
for file in "${DATA_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  Creating $file"
        echo '{}' > "$file"
    else
        echo "  $file already exists"
    fi
done

# Set permissions
echo "Setting permissions..."
chmod 666 cache/*.json 2>/dev/null || true
chmod 666 data/*.json 2>/dev/null || true

echo ""
echo "=== Cache initialization complete ==="
echo ""
echo "You can now run:"
echo "  docker-compose up -d"
echo ""
echo "Or with MCP server:"
echo "  docker-compose --profile mcp up -d"
