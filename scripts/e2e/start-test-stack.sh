#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS="$ROOT/scripts/e2e"
RUNTIME="${SCENEWEAVER_RUNTIME_DIR:-$ROOT/runtime-e2e}"
API_PORT="${SCENEWEAVER_PORT:-8010}"
WEB_PORT="${SCENEWEAVER_WEB_PORT:-5174}"

export SCENEWEAVER_ENVIRONMENT=e2e
export SCENEWEAVER_HOST=127.0.0.1
export SCENEWEAVER_PORT="$API_PORT"
export SCENEWEAVER_RUNTIME_DIR="$RUNTIME"
export SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db"
export SCENEWEAVER_IMAGE_BACKEND=fake
export SCENEWEAVER_LLM_PROVIDER=stub
export SCENEWEAVER_WORKER_ID=e2e-worker-1
export SCENEWEAVER_FAKE_IMAGE_DELAY_MS="${SCENEWEAVER_FAKE_IMAGE_DELAY_MS:-400}"
export SCENEWEAVER_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"
export SCENEWEAVER_API_PROXY="http://127.0.0.1:${API_PORT}"
export SCENEWEAVER_WEB_PORT="$WEB_PORT"
export SCENEWEAVER_E2E_API="http://127.0.0.1:${API_PORT}"
export SCENEWEAVER_E2E_WEB="http://127.0.0.1:${WEB_PORT}"

bash "$SCRIPTS/stop-test-stack.sh" || true
bash "$SCRIPTS/reset-test-state.sh"

cd "$ROOT"
mkdir -p "$SCRIPTS"

echo "[e2e] starting API on :$API_PORT"
nohup env \
  SCENEWEAVER_ENVIRONMENT=e2e \
  SCENEWEAVER_HOST=127.0.0.1 \
  SCENEWEAVER_PORT="$API_PORT" \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND=fake \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID=e2e-worker-1 \
  SCENEWEAVER_FAKE_IMAGE_DELAY_MS="$SCENEWEAVER_FAKE_IMAGE_DELAY_MS" \
  SCENEWEAVER_CORS_ORIGINS="$SCENEWEAVER_CORS_ORIGINS" \
  uv run sceneweaver-api >"$SCRIPTS/api.log" 2>&1 &
echo $! >"$SCRIPTS/api.pid"

echo "[e2e] starting Worker"
nohup env \
  SCENEWEAVER_ENVIRONMENT=e2e \
  SCENEWEAVER_RUNTIME_DIR="$RUNTIME" \
  SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db" \
  SCENEWEAVER_IMAGE_BACKEND=fake \
  SCENEWEAVER_LLM_PROVIDER=stub \
  SCENEWEAVER_WORKER_ID=e2e-worker-1 \
  SCENEWEAVER_FAKE_IMAGE_DELAY_MS="$SCENEWEAVER_FAKE_IMAGE_DELAY_MS" \
  uv run sceneweaver-worker >"$SCRIPTS/worker.log" 2>&1 &
echo $! >"$SCRIPTS/worker.pid"

echo "[e2e] starting Web on :$WEB_PORT"
cd "$ROOT/apps/web"
nohup env \
  SCENEWEAVER_API_PROXY="$SCENEWEAVER_API_PROXY" \
  SCENEWEAVER_WEB_PORT="$WEB_PORT" \
  pnpm exec vite --host 127.0.0.1 --port "$WEB_PORT" >"$SCRIPTS/web.log" 2>&1 &
echo $! >"$SCRIPTS/web.pid"

echo "[e2e] waiting for health..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null \
    && curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null; then
    echo "[e2e] stack ready"
    echo "API=http://127.0.0.1:${API_PORT}"
    echo "WEB=http://127.0.0.1:${WEB_PORT}"
    echo "RUNTIME=$RUNTIME"
    exit 0
  fi
  sleep 0.5
done

echo "[e2e] stack failed to become healthy" >&2
tail -n 60 "$SCRIPTS/api.log" >&2 || true
tail -n 40 "$SCRIPTS/web.log" >&2 || true
tail -n 40 "$SCRIPTS/worker.log" >&2 || true
exit 1
