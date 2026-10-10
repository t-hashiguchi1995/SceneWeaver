# SceneWeaver MVP v1.0 — Status

**Status: COMPLETE** (implementation plan v1.0). Product Git tag target: **`v0.1.0`**.

## Test baselines (freeze reference)

| Layer | Command | Count |
|---|---|---|
| Unit (`tests/unit`) | `uv run pytest tests/unit` | 24 |
| + Integration (`tests/integration`) | `uv run pytest` | **27** |
| Mock E2E | `pnpm test:e2e` | 7 |
| Live Comfy | `pnpm test:e2e:live` | 3 |

### Note on “26 → 24”

There was **no intentional deletion of two acceptance tests**.

- Reporting `24` referred to **`tests/unit` only**.
- Full pytest suite is **27** (= 24 unit + 3 integration).
- Relative to an earlier full-suite baseline of ~26, Hardening #7 **added**
  `test_classify_comfy_messages` (+1), so the full suite **increased**, not decreased.

## Completion gates

1. Empty DB → Alembic → startup
2. Fake Playwright vertical slice
3. Persistence across API+Worker process restart
4. Real Comfy Qwen / Anima / LLLite once each via UseCases

## Post-MVP (not blockers)

Eagle, real Publish, CSP round-trip watcher, Look Builder UI, Blender / CSP 3D, Video.
