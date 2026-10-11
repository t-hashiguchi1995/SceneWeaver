# SceneWeaver

Character content production workspace that connects story, dialogue, wardrobe,
image generation, CLIP STUDIO handoff, and release preview into a single workflow.

**MVP v0.1.0: COMPLETE.** Next: **v0.2 Applicationization** (Setup / Settings / shell — see [ADR 0008](docs/adr/0008-applicationization-v02.md)).
Not `v1.0.0` while Eagle / Publish / Look Builder remain later phases.

## Stack

- **API / Worker**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 (`uv`)
- **Web**: Vite + React + TanStack Router + TanStack Query (`pnpm`)
- **Package**: `creator_studio` (Domain → Application → Ports ← Adapters / Infrastructure)

## Quick start (clean environment)

Schema is **Alembic-only**. API/Worker bootstrap does **not** call `create_all()`.

```bash
uv sync --extra dev
cp .env.example .env          # optional once Setup Wizard is used
mkdir -p runtime
uv run alembic upgrade head   # required before first start
pnpm --dir apps/web install

# Recommended: one command launches API + Worker + Web and opens the browser
uv run sceneweaver start

# Or run pieces separately:
# uv run sceneweaver-api
# uv run sceneweaver-worker
# pnpm --dir apps/web dev
```

First browser open: **Setup Wizard** (`/setup`) configures Comfy / LLM / CSP paths.
Secrets (API keys) go to OS keyring or a gitignored file under `runtime/` — never plaintext in SQLite.

**Shot Studio** (`/shots/:shotId`) edits the Prompt Draft before generate.
**Generation Review** (`/shots/:shotId/generations/:attemptId`) shows candidates plus
the immutable Attempt prompt snapshot (not the live Draft). Spec:
`docs/architecture/sceneweaver_prompt_generation_review_ui_spec_r1.html`.
Git templates / compiler rules stay immutable; finals are snapshotted on GenerationAttempt.

Legacy prompt library import (SFW, idempotent) seeds **Prompt Library / Character
assets** — it does **not** invent runtime Default Prompt strings (see ADR 0011):

```bash
uv run python scripts/import_legacy_prompts.py --source /path/to/prompts.zip --dry-run
uv run python scripts/import_legacy_prompts.py --source /path/to/prompts.zip --apply
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
| `uv run pytest` | Domain / Application / contracts (+ API integration) | No | 52 passed (2026-10-12) |
| `pnpm test:e2e` | Real app + Fake LLM/Image (`runtime-e2e/`) | No | 10 passed (2026-10-12) |
| `pnpm test:e2e:live` | Real app + Real Comfy (`runtime-live-test/`) | Yes | 4 passed (2026-10-11) |

Current local implementation and remaining integration work: [UI / Integration Design R2](docs/architecture/sceneweaver_ui_integration_design_r2.html).
Validation scope and the pinned code commit: [2026-10-12 code checkpoint](docs/validation/code_checkpoint_20261012.md).
External posting succeeded through dedicated-browser smoke scripts; application publishing remains a preview.

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
| Applicationization / v0.2 Sprint 1 | [0008](docs/adr/0008-applicationization-v02.md) |
| Japanese UI / i18n (ja default) | [0009](docs/adr/0009-japanese-ui-i18n.md) |
| Prompt Draft + Legacy Importer | [0010](docs/adr/0010-prompt-draft-and-legacy-import.md) |
| Default Prompt Assembly (Sprint 4) | [0011](docs/adr/0011-default-prompt-assembly.md) |

Design authority HTML: `docs/architecture/`.

## Runtime dirs (gitignored)

| Dir | Purpose |
|---|---|
| `runtime/` | Local development |
| `runtime-e2e/` | Mock Playwright |
| `runtime-live-test/` | Real Comfy Playwright (keep on failure for debug) |

Never commit `.env`, browser profiles, or secrets.
