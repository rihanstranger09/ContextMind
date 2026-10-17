#!/bin/sh
# Run the complete local stack after cp .env.example .env and adding your API key.
set -eu
if [ ! -f .env ]; then echo 'Copy .env.example to .env and configure OPENAI_API_KEY first.' >&2; exit 1; fi
docker compose up --build -d
echo 'Backend + frontend: http://localhost:8000  |  database: localhost:6380'
echo 'Check /api/health for graph_mode=falkordb and synthesis=openai_tool_calling.'
