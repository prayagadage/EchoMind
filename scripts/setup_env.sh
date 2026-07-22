#!/usr/bin/env bash
# ==============================================================================
# EchoMind Environment & Dependency Setup Script
# Configures virtualenv and synchronizes dependencies using uv.
# ==============================================================================

set -euo pipefail

echo "============================================================"
echo "Initializing EchoMind Development Environment"
echo "============================================================"

# Check for uv binary
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' package manager is not installed."
    echo "Please install uv using: brew install uv or curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "1. Syncing dependencies with uv..."
uv sync --all-extras

echo "2. Ensuring configuration template..."
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
else
    echo ".env file already exists."
fi

echo "3. Creating local data directories..."
mkdir -p data/logs data/db data/cache

echo "============================================================"
echo "EchoMind environment setup complete!"
echo "Run 'uv run python -m app.main' to launch the application."
echo "============================================================"
