#!/usr/bin/env bash
# exit on error
set -o errexit

# Install uv
pip install uv

# Install dependencies using uv
uv sync --no-dev

# Add psycopg2-binary for PostgreSQL support
uv pip install psycopg2-binary

echo "Build completed successfully!"
