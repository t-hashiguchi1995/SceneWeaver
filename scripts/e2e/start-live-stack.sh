#!/usr/bin/env bash
# Real Comfy live-test stack. Isolated from mock E2E (runtime-e2e / ports 8010).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS="$ROOT/scripts/e2e"
RUNTIME="${SCENEWEAVER_RUNTIME_DIR:-$ROOT/runtime-live-test}"
API_PORT="${SCENEWEAVER_PORT:-8020}"
WEB_PORT="${SCENEWEAVER_WEB_PORT:-5175}"
# Prefer COMFY_BASE_URL (user convention) then SCENEWEAVER_COMFY_URL
COMFY_URL="${COMFY_BASE_URL:-${SCENEWEAVER_COMFY_URL:-http://127.0.0.1:8188}}"

export SCENEWEAVER_ENVIRONMENT=live-test
export SCENEWEAVER_HOST=127.0.0.1
export SCENEWEAVER_PORT="$API_PORT"
export SCENEWEAVER_RUNTIME_DIR="$RUNTIME"
export SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db"
export SCENEWEAVER_IMAGE_BACKEND=comfy
export SCENEWEAVER_COMFY_URL="$COMFY_URL"
export SCENEWEAVER_LLM_PROVIDER=stub
export SCENEWEAVER_WORKER_ID=live-worker-1
export SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS="${SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS:-600}"
export SCENEWEAVER_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
export SCENEWEAVER_API_PROXY="http://127.0.0.1:${API_PORT}"
export SCENEWEAVER_WEB_PORT="$WEB_PORT"
export SCENEWEAVER_E2E_API="http://127.0.0.1:${API_PORT}"
export SCENEWEAVER_E2E_WEB="http://127.0.0.1:${WEB_PORT}"

bash "$SCRIPTS/stop-live-stack.sh" || true

# Soft reset: keep failed-run artifacts under runtime-live-test/debug/ if present.
mkdir -p "$RUNTIME"/{assets,projects,logs,jobs,csp_handoff,debug}
if [[ "${SCENEWEAVER_LIVE_WIPE:-0}" == "1" ]]; then
  echo "[live] wiping $RUNTIME (SCENEWEAVER_LIVE_WIPE=1)"
  rm -rf "$RUNTIME"
  mkdir -p "$RUNTIME"/{assets,projects,logs,jobs,csp_handoff,debug}
fi

cd "$ROOT"
export SCENEWEAVER_ENVIRONMENT=live-test
export SCENEWEAVER_RUNTIME_DIR="$RUNTIME"
export SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db"
uv run alembic upgrade head

echo "[live] Comfy URL=$COMFY_URL"
if ! curl -sf "$COMFY_URL/system_stats" >/dev/null; then
  echo "[live] WARNING: Comfy health unavailable at $COMFY_URL — live specs will skip" >&2
fi

echo "[live] starting API on :$API_PORT"
nohup env \
  SCENEWEAVER_ENVIRONMENT=live-test \
  SCENEWEAVER_HOST=127.0.0.1 \
  SCENEWEAVER_PORT="$API_PORT" \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND=comfy \
  SCENEWEAVER_COMFY_URL="$COMFY_URL" \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID=live-worker-1 \
  SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS="$SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS" \
  SCENEWEAVER_CORS_ORIGINS="$SCENEWEAVER_CORS_ORIGINS" \
  uv run sceneweaver-api >"$SCRIPTS/live-api.log" 2>&1 &
echo $! >"$SCRIPTS/live-api.pid"

echo "[live] starting Worker"
nohup env \
  SCENEWEAVER_ENVIRONMENT=live-test \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND=comfy \
  SCENEWEAVER_COMFY_URL="$COMFY_URL" \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID=live-worker-1 \
  SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS="$SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS" \
  uv run sceneweaver-worker >"$SCRIPTS/live-worker.log" 2>&1 &
echo $! >"$SCRIPTS/live-worker.pid"

echo "[live] starting Web on :$WEB_PORT"
cd "$ROOT/apps/web"
nohup env \
  SCENEWEAVER_API_PROXY="$SCENEWEAVER_API_PROXY" \
  SCENEWEAVER_WEB_PORT="$WEB_PORT" \
  pnpm exec vite --host 127.0.0.1 --port "$WEB_PORT" >"$SCRIPTS/live-web.log" 2>&1 &
echo $! >"$SCRIPTS/live-web.pid"

echo "[live] waiting for health..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null \
    && curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null; then
    echo "[live] stack ready"
    echo "API=http://127.0.0.1:${API_PORT}"
    echo "WEB=http://127.0.0.1:${WEB_PORT}"
    echo "RUNTIME=$RUNTIME"
    echo "COMFY=$COMFY_URL"
    exit 0
  fi
  sleep 0.5
done

echo "[live] stack failed to become healthy" >&2
tail -n 60 "$SCRIPTS/live-api.log" >&2 || true
tail -n 40 "$SCRIPTS/live-web.log" >&2 || true
exit 1
