#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME="${SCENEWEAVER_RUNTIME_DIR:-$ROOT/runtime-e2e}"

echo "[e2e] resetting $RUNTIME"
rm -rf "$RUNTIME"
mkdir -p "$RUNTIME"/{assets,projects,logs,jobs,csp_handoff}

export SCENEWEAVER_ENVIRONMENT=e2e
export SCENEWEAVER_RUNTIME_DIR="$RUNTIME"
export SCENEWEAVER_DATABASE_URL="sqlite:///$RUNTIME/studio.db"
export SCENEWEAVER_IMAGE_BACKEND=fake
export SCENEWEAVER_LLM_PROVIDER=stub

cd "$ROOT"
uv run alembic upgrade head
echo "[e2e] DB migrated at $SCENEWEAVER_DATABASE_URL"
