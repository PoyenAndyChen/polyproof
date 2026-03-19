#!/bin/bash
set -e
export PYTHONPATH=/app:${PYTHONPATH:-}
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
