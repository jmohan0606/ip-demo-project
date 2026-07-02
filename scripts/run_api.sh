#!/usr/bin/env bash
set -e
uv run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
