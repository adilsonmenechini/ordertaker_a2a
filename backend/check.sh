#!/bin/bash
# Run all checks: lint, format check, and tests
set -e

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🔍 Running ruff check..."
ruff check .

echo "🎨 Checking ruff format..."
ruff format --check .

echo "🧪 Running tests..."
python -m pytest tests/ -v --tb=short

echo ""
echo "✅ All checks passed!"
