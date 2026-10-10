# ADR 0004 — Shot / RenderPlan / GenerationAttempt SQL persistence

## Status

Accepted (MVP Hardening)

## Context

ADR 0002 deferred Shot state to in-memory. That made M4 a separate world from
Project/Story/Wardrobe and would fix incorrect “works in one process” behavior
into Playwright E2E.

## Decision

1. Persist `shots`, `render_plans`, `generation_attempts` via Alembic 0004.
2. GenerationAttempt rows are append-only (no UPDATE of provenance).
3. Script revision / lock triggers `invalidate_for_script_change`: Shot + RenderPlan
   become stale; GenerationAttempt remains unchanged (`based_on_shot_revision` derived currentness).
4. FakeImageBackend and ComfyImageBackend both implement `ImageBackend` and share
   WorkflowCompiler validation.

## Consequences

- API restart preserves Shot/Plan/Attempt.
- Playwright E2E can rely on Real SQLite + Alembic without in-memory shortcuts.
- Mock E2E includes a **real process restart** smoke (kill API+Worker, keep DB/assets)
  in addition to `/api/test/reload` (in-memory only). See ADR 0006.
