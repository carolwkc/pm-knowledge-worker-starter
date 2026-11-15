#!/bin/sh
set -e

if [ -z "$PGPASSWORD" ]; then
    printf '%s\n' 'Set POSTGRES_PASSWORD in .env' >&2
    exit 1
fi

uv run --no-sync alembic upgrade head
exec uv run --no-sync uvicorn pmknowledge.main:app --host 0.0.0.0 --port 8000 --no-access-log
