#!/bin/bash
# run.sh — Run the scraper via Docker, auto-removing the app container when done.
# The Postgres container stays running persistently.
#
# Usage:
#   ./run.sh           # normal run
#   ./run.sh --build   # rebuild the image first

set -e
cd "$(dirname "$0")"

# Ensure the Postgres DB is running
docker compose up -d db

# Run the app container (--rm removes it when done)
docker compose run --rm app "$@"

echo "✅ Done. App container removed. Postgres still running."
