#!/bin/bash

# Create necessary directories
mkdir -p docs 

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

echo "Starting RAG System..."
echo "Make sure Ollama is running locally (ollama serve)"

# Change to backend directory and start the server
cd backend && uv run fastapi dev app.py