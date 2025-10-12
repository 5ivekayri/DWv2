#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$PROJECT_ROOT"

if [[ -f requirements.txt ]]; then
  if ! python -m pip install --no-cache-dir -r requirements.txt >/dev/null; then
    echo "[mqtt-consumer] Warning: failed to install dependencies from requirements.txt" >&2
  fi
fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
python -m backend.ingest.mqtt_consumer
