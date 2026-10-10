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
      echo "[live] stopping pid $pid ($f)"
      kill "$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}

stop_pidfile "$SCRIPTS/live-api.pid"
stop_pidfile "$SCRIPTS/live-worker.pid"
stop_pidfile "$SCRIPTS/live-web.pid"
fuser -k 8020/tcp 2>/dev/null || true
fuser -k 5175/tcp 2>/dev/null || true
echo "[live] stack stopped"
