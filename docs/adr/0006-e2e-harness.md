# ADR 0006 — SceneWeaver E2E Test Harness

## Status

Accepted (was temporarily numbered 0003; renumbered to avoid collision with Alembic ADR)

## Context

SceneWeaver spans React, FastAPI, Worker, SQLite, SSE, Asset Store, and optional ComfyUI.
Browser-only specs against development `runtime/` would be flaky and couple tests to GPU.

## Decision

1. Mock E2E uses isolated `runtime-e2e/` with `SCENEWEAVER_ENVIRONMENT=e2e`.
2. Live Comfy E2E uses isolated `runtime-live-test/` with `SCENEWEAVER_ENVIRONMENT=live-test`.
3. Mock stack: Real React + API + Worker + SQLite + SSE + Asset Store; Fake LLM + FakeImageBackend.
4. `/api/test/*` is registered only when `allows_test_control` (`e2e` | `live-test`). Never in production.
5. `/api/test/reset` wipes rows + asset dirs **in place** (does not replace `studio.db`) so the worker’s open SQLite handle stays valid.
6. `/api/test/reload` only drops in-memory Container/engine — **not** a substitute for process kill. Process restart smoke kills API+Worker and restarts against the same runtime DB (`scripts/e2e/restart-api-worker.sh`).
7. Split commands:
   - `pnpm test:e2e` — mock project only (`testIgnore: live/`)
   - `pnpm test:e2e:live` — live project only (`testMatch: live/`)
8. Live skip/fail: Comfy unreachable → **skip**; after connect, model/workflow/custom-node failures → **fail** with classified codes.
9. On Ubuntu 20.04 WSL, Playwright uses system Chrome (`channel: chrome`, `--no-sandbox`); video is off.

## Consequences

- Daily development never needs a GPU.
- Production never exposes test control routes.
- Live Comfy smoke is explicit and out of default CI.
