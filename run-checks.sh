#!/bin/bash
set -e

# Run checks inside the execution container where dependencies are installed
# If Docker is not running or the container is not active, fall back to running on the host.

if docker compose -f docker/docker-compose.yml ps execution 2>/dev/null | grep -q "Up\|running"; then
  echo "Using Docker container 'execution' for Python checks..."
  
  echo "Running formatting checks (Ruff Format)..."
  docker compose -f docker/docker-compose.yml exec execution ruff format --check .

  echo "Running linter checks (Ruff)..."
  docker compose -f docker/docker-compose.yml exec execution ruff check .

  echo "Running tests (Pytest)..."
  docker compose -f docker/docker-compose.yml exec execution pytest
else
  echo "Docker container 'execution' is not running. Running Python checks locally on the host..."
  
  echo "Running formatting checks (Ruff Format)..."
  uv run ruff format --check .

  echo "Running linter checks (Ruff)..."
  uv run ruff check .

  echo "Running tests (Pytest)..."
  uv run --all-extras pytest
fi

echo "Running frontend checks..."
pnpm install
pnpm check

echo "Running markdown link verification..."
node scripts/check-links.js

echo "Running ADR validation..."
python3 scripts/validate_adrs.py

echo "Running Markdown validation..."
python3 scripts/validate_markdown.py
