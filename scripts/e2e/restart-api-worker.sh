#!/usr/bin/env bash
# Kill + restart API and Worker only (keep DB/assets/web). Used by process-restart smoke.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS="$ROOT/scripts/e2e"
RUNTIME="${SCENEWEAVER_RUNTIME_DIR:-$ROOT/runtime-e2e}"
API_PORT="${SCENEWEAVER_PORT:-8010}"
MODE="${1:-e2e}"  # e2e | live

if [[ "$MODE" == "live" ]]; then
  RUNTIME="${SCENEWEAVER_RUNTIME_DIR:-$ROOT/runtime-live-test}"
  API_PORT="${SCENEWEAVER_PORT:-8020}"
  API_PID="$SCRIPTS/live-api.pid"
  WORKER_PID="$SCRIPTS/live-worker.pid"
  API_LOG="$SCRIPTS/live-api.log"
  WORKER_LOG="$SCRIPTS/live-worker.log"
  ENV_NAME=live-test
  IMAGE_BACKEND=comfy
  COMFY_URL="${COMFY_BASE_URL:-${SCENEWEAVER_COMFY_URL:-http://127.0.0.1:8188}}"
else
  API_PID="$SCRIPTS/api.pid"
  WORKER_PID="$SCRIPTS/worker.pid"
  API_LOG="$SCRIPTS/api.log"
  WORKER_LOG="$SCRIPTS/worker.log"
  ENV_NAME=e2e
  IMAGE_BACKEND=fake
  COMFY_URL="${SCENEWEAVER_COMFY_URL:-http://127.0.0.1:8188}"
fi

stop_pidfile() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "[restart] killing $pid ($f)"
      kill "$pid" 2>/dev/null || true
      sleep 0.4
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}

stop_pidfile "$API_PID"
stop_pidfile "$WORKER_PID"
fuser -k "${API_PORT}/tcp" 2>/dev/null || true
sleep 0.5

cd "$ROOT"
CORS="${SCENEWEAVER_CORS_ORIGINS:-http://127.0.0.1:5174,http://localhost:5174}"
FAKE_DELAY="${SCENEWEAVER_FAKE_IMAGE_DELAY_MS:-400}"
POLL_TO="${SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS:-300}"

echo "[restart] starting API :$API_PORT ($ENV_NAME)"
nohup env \
  SCENEWEAVER_ENVIRONMENT="$ENV_NAME" \
  SCENEWEAVER_HOST=127.0.0.1 \
  SCENEWEAVER_PORT="$API_PORT" \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND="$IMAGE_BACKEND" \
  SCENEWEAVER_COMFY_URL="$COMFY_URL" \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID="${ENV_NAME}-worker-1" \
  SCENEWEAVER_CORS_ORIGINS="$CORS" \
  SCENEWEAVER_FAKE_IMAGE_DELAY_MS="$FAKE_DELAY" \
  SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS="$POLL_TO" \
  uv run sceneweaver-api >"$API_LOG" 2>&1 &
echo $! >"$API_PID"

echo "[restart] starting Worker"
nohup env \
  SCENEWEAVER_ENVIRONMENT="$ENV_NAME" \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND="$IMAGE_BACKEND" \
  SCENEWEAVER_COMFY_URL="$COMFY_URL" \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID="${ENV_NAME}-worker-1" \
  SCENEWEAVER_FAKE_IMAGE_DELAY_MS="$FAKE_DELAY" \
  SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS="$POLL_TO" \
  uv run sceneweaver-worker >"$WORKER_LOG" 2>&1 &
echo $! >"$WORKER_PID"

# Wait until health is stable across two consecutive probes
ok=0
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
    ok=$((ok + 1))
    if [[ "$ok" -ge 2 ]]; then
      echo "[restart] API ready"
      exit 0
    fi
  else
    ok=0
  fi
  sleep 0.5
done
echo "[restart] API failed to come back" >&2
tail -n 40 "$API_LOG" >&2 || true
exit 1
