#!/usr/bin/env bash
# Runs database migrations (if needed) and starts the Streamlit dashboard —
# the manual-verification surface for dev_alm before merging to main
# (CLAUDE.md §9, docs/roadmap.md Phase 8). Optional convenience wrapper for:
#
#   alembic upgrade head
#   streamlit run src/real_estate/dashboard.py
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — copy .env.example to .env and fill in DATABASE_URL etc. first." >&2
  exit 1
fi

echo "=== Applying migrations ==="
alembic upgrade head

echo "=== Starting the dashboard (Ctrl+C to stop) ==="
streamlit run src/real_estate/dashboard.py
