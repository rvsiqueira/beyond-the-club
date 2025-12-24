#!/bin/bash
# Docker entrypoint script
# Creates required cache files if they don't exist

set -e

echo "Initializing cache files..."

# Root level cache files
CACHE_FILES=(
    "/app/.beyondtheclub_tokens.json"
    "/app/.beyondtheclub_members.json"
    "/app/.beyondtheclub_availability.json"
    "/app/.beyondtheclub_preferences.json"
)

# Data directory cache files
DATA_CACHE_FILES=(
    "/app/data/users.json"
    "/app/data/graph.json"
    "/app/data/.beyondtheclub_user_tokens.json"
)

# Ensure data directory exists
mkdir -p /app/data

# Create root cache files with empty JSON object if they don't exist
for file in "${CACHE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Creating $file"
        echo '{}' > "$file"
    fi
done

# Create data cache files with empty JSON object if they don't exist
for file in "${DATA_CACHE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Creating $file"
        echo '{}' > "$file"
    fi
done

echo "Cache files initialized."

# Execute the main command
exec "$@"
