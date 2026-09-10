#!/bin/sh
# Container entrypoint: bring the schema up to date, then start the server.
#
# POSIX sh for portability across Unraid, Docker, plain Linux hosts and AWS.
# Migrations run here rather than inside the application so that they execute
# exactly once per container start, before any request is served.
set -eu

echo "Running database migrations..."
alembic upgrade head

echo "Ensuring an owner account exists..."
python -m app.bootstrap

echo "Starting application..."
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
