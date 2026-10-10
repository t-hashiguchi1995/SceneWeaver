# ADR 0001 — MVP v1.0 scope freeze

## Status

Accepted — **MVP v1.0 implementation COMPLETE** (Git product tag target: `v0.1.0`)

## Context

SceneWeaver is a scrap-and-rebuild of the prior Playwright verification app. Design authority is Core Architecture R2 + Wireframes R5 + Prompt Spec R1 + Integration Security R1.

## Decision

Implement against **SceneWeaver MVP implementation plan v1.0** without further design changes unless a blocking implementation issue arises (then record a new ADR).

Vertical slice completion criterion:

Home → Project → Character → Scene/Beat → Dialogue Pipeline → Lock → Wardrobe Market → Try-On → OutfitState → ShotSpec → Anima/LLLite → Review/Adopt → PagePlan/PanelSlot → CSP Handoff → Release Edition Preview.

### Completion gates (all met)

1. Empty DB → Alembic → app startup
2. Fake providers: Playwright vertical slice
3. Persistence across real API+Worker process restart
4. Real Comfy: Qwen / Anima Base / Anima LLLite once each via UseCases

### Explicitly out of MVP (Post-MVP)

Real social Publish, Eagle mandatory sync, Blender / CSP 3D, Look Builder multi-slot UI.

## Consequences

- New features land after README/ADR sync and product tag `v0.1.0` freeze.
- Hardening ADRs 0003–0007 record the architecture that made the gates real.