#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS="$ROOT/scripts/e2e"

stop_pidfile() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "[e2e] stopping pid $pid ($f)"
      kill "$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}

stop_pidfile "$SCRIPTS/api.pid"
stop_pidfile "$SCRIPTS/worker.pid"
stop_pidfile "$SCRIPTS/web.pid"
# stray vite/uvicorn on e2e ports
fuser -k 8010/tcp 2>/dev/null || true
fuser -k 5174/tcp 2>/dev/null || true
echo "[e2e] stack stopped"