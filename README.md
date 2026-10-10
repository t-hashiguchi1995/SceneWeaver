# SceneWeaver

Character content production workspace that connects story, dialogue, wardrobe,
image generation, CLIP STUDIO handoff, and release preview into a single workflow.

**MVP implementation plan v1.0: COMPLETE** → product tag target **`v0.1.0`**
(Semantic Versioning: not `v1.0.0` while Eagle / Publish / Look Builder remain Post-MVP).

## Stack

- **API / Worker**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 (`uv`)
- **Web**: Vite + React + TanStack Router + TanStack Query (`pnpm`)
- **Package**: `creator_studio` (Domain → Application → Ports ← Adapters / Infrastructure)

## Quick start (clean environment)

Schema is **Alembic-only**. API/Worker bootstrap does **not** call `create_all()`.

```bash
uv sync --extra dev
cp .env.example .env
mkdir -p runtime
uv run alembic upgrade head     # required before first start
uv run sceneweaver-api          # http://127.0.0.1:8000
uv run sceneweaver-worker       # separate terminal

cd apps/web && pnpm install && pnpm dev   # http://127.0.0.1:5173
# Optional: regenerate OpenAPI types
pnpm openapi:gen
```

OpenAPI: `http://127.0.0.1:8000/docs`

Root `uv.lock` and `apps/web/pnpm-lock.yaml` / `tests/e2e/pnpm-lock.yaml` must be committed.

## MVP vertical slice

```text
Home → Project → Character → Scene/Beat → Dialogue → Lock
  → Market → Try-On → OutfitState → Shot → Anima/LLLite
  → Review/Adopt → PagePlan → CSP Handoff → Release Preview
```

Default image backend: `SCENEWEAVER_IMAGE_BACKEND=fake` (GPU-free).
Approved models only: `config/model_registry.yaml`.

## Tests (keep these three layers)

| Command | What | Needs GPU? | Baseline |
|---|---|---|---|
| `uv run pytest` | Domain / Application / contracts (+ API integration) | No | 27 passed |
| `pnpm test:e2e` | Real app + Fake LLM/Image (`runtime-e2e/`) | No | 7 passed |
| `pnpm test:e2e:live` | Real app + Real Comfy (`runtime-live-test/`) | Yes | 3 passed |

```bash
uv run pytest                 # unit + integration

# Mock E2E — never talks to Comfy
pnpm test:e2e

# Live Comfy — explicit only (skip if Comfy unreachable; fail after connect on model/workflow errors)
COMFY_BASE_URL=http://127.0.0.1:8188 pnpm test:e2e:live
```

- Mock control API (`/api/test/*`) only when `SCENEWEAVER_ENVIRONMENT` is `e2e` or `live-test`.
- Process-restart smoke (mock suite) kills API+Worker and restores Project/Shot/Generation/CSP from SQLite + Asset Store.
- Do **not** mix live specs into `pnpm test:e2e`.

### Live Comfy requirements

- ComfyUI reachable (`COMFY_BASE_URL` or `SCENEWEAVER_COMFY_URL`, default `http://127.0.0.1:8188`)
- Models / nodes used by `workflows/comfy/*.api.json` and `config/model_registry.yaml`, including:
  - Checkpoint: `anima_baseV10.safetensors`
  - UNET / CLIP / VAE for Qwen Image Edit 2509 (+ Lightning LoRA recommended)
  - Model patch: `anima-lllite-pose-1.safetensors` (ModelPatchLoader)
  - Node: `AnimaLLLiteApply` (and standard KSampler / LoadImage / SaveImage / Qwen encode nodes)

## Architecture notes (Hardening)

| Topic | ADR |
|---|---|
| MVP scope / complete | [0001](docs/adr/0001-mvp-v1-scope.md) |
| Shot in-memory (superseded) | [0002](docs/adr/0002-shot-pipeline-in-memory-mvp.md) |
| Alembic-only bootstrap | [0003](docs/adr/0003-alembic-only-bootstrap.md) |
| Shot SQL + immutable Generation | [0004](docs/adr/0004-shot-sql-persistence.md) |
| CSP adopted-byte handoff | [0005](docs/adr/0005-csp-handoff-adopted-bytes.md) |
| E2E harness (mock / live / restart) | [0006](docs/adr/0006-e2e-harness.md) |
| Real Comfy UseCase smoke | [0007](docs/adr/0007-real-comfy-live-smoke.md) |

Design authority HTML: `docs/architecture/`.

## Runtime dirs (gitignored)

| Dir | Purpose |
|---|---|
| `runtime/` | Local development |
| `runtime-e2e/` | Mock Playwright |
| `runtime-live-test/` | Real Comfy Playwright (keep on failure for debug) |

Never commit `.env`, browser profiles, or secrets.
