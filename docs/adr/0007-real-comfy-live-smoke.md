# ADR 0007 — Real Comfy live smoke via Application UseCases

## Status

Accepted (MVP Hardening #7 — MVP v1.0 complete)

## Context

FakeImageBackend proves contracts without GPU. MVP completion also required one real
path each for Qwen Try-On, Anima Base, and Anima LLLite — through Application UseCases,
not `ComfyImageBackend.submit()` alone.

## Decision

1. Live specs live under `tests/e2e/specs/live/` and call HTTP APIs that invoke UseCases
   (`RunTryOn`, `ShotPipeline.render`).
2. `ComfyImageBackend` shares WorkflowTemplateLoader → Validator → Compiler with Fake,
   then submit → poll/wait → collect → AssetStore + provenance.
3. Classified errors (never collapsed to opaque 500):
   `COMFY_UNREACHABLE`, `MODEL_NOT_FOUND`, `CUSTOM_NODE_MISSING`, `WORKFLOW_INVALID`,
   `SUBMIT_FAILED`, `GENERATION_FAILED`, `OUTPUT_NOT_FOUND`, `TIMEOUT`.
4. Provenance must retain at least: `provider`, `workflow_template_id`, `workflow_hash`,
   `seed`, `external_job_ref`, `model_id`. LLLite adds pose ref + `control_model` +
   `control_strength`.
5. Visual quality is **out of scope** for automated live smoke (human review separately).
6. Live poll timeout defaults to ~10 minutes (Qwen cold load); mock E2E stays short.

## Consequences

- `pnpm test:e2e:live` is the only entry that may touch real Comfy.
- Workflow API JSON under `workflows/comfy/` must be executable on the target Comfy install
  (approved registry models / custom nodes required).
