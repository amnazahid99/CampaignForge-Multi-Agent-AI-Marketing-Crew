#!/bin/bash
set -e

echo "Starting CampaignForge..."

# Start Ollama in background if not running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Pull model if needed
echo "Ensuring model is available..."
ollama pull llama3.1:8b || true

# Start backend
echo "Starting backend..."
cd backend
uv run fastapi dev app.py
