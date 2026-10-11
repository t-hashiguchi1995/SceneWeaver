# UI architecture R1 implementation

Design authority: [SceneWeaver UI / Application Architecture R1](sceneweaver_ui_architecture_design_r1.html).

Current implementation status, validation limits and the next integration design are consolidated in [SceneWeaver UI / Integration Design R2](sceneweaver_ui_integration_design_r2.html). R1 remains the historical design baseline; R2 records the local Sidebar and Project Dashboard as delivered, and distinguishes the external posting smoke scripts from the still-unimplemented Application publishing workflow.

The creator workflow uses `/projects/:projectId` as its dashboard, with project-scoped Story, Wardrobe, Shots, Generation Review, CSP and Release routes. These pages read domain state from the database. Legacy unscoped routes remain as compatibility entry points for existing workflows. The home page shows recent projects, unfinished jobs and setup guidance. Global navigation contains workspace and system items; project navigation appears within a project. Jobs open in a native dialog with keyboard focus containment and Escape handling.

## Delivered

- Asset content endpoint with ETag, private caching, MIME types and missing-content handling; image previews for generated assets, try-on candidates and garment plates.
- 700ms prompt and character autosave, serialized writes, explicit save status and prompt flush before generation/navigation. Unsaved prompts warn before browser unload.
- Editable Character Persona/VisualIdentity and voice examples; editable dialogue candidates before locking; persisted scene/beat selection and dialogue restored within projects.
- Semantic shot controls, random/fixed seeds, explicit stale-draft confirmation, token-based prompt diff and source/components views.
- Immutable render snapshots, replay with a new/same seed, and editing a historical prompt while preserving its controls. Backend/model/workflow configuration drift blocks replay rather than silently changing conditions. Older attempts without complete snapshots cannot replay.
- Comfy candidate-count slot bindings produce four candidates. Mock PNG fixtures have valid encoding for browser image decoding.
- Dashboard counts, actions, recent shots/generations, adopted images, try-on sessions and latest handoff. Project-scoped CSP reads adopted images and locked script events from DB, and respects the configured export directory.
- Image backend caching keyed by effective backend/URL, so changes take effect without restarting. Setup backend selection is separate from connectivity. Eagle is explicitly unavailable; production hides the stub-job button.
- New shots use Default Prompt Builder when an enabled imported library exists; it can also be selected explicitly with the `anima_story_panel@v1` profile. The existing compiler remains available. Component selection applies content policy, stable precedence/priority/id conflict resolution, expression subkinds and deterministic ordering. Draft assembly metadata is persisted by migration `20261011_0006` and copied into immutable attempts.
- ZIP import validates paths, file types, symlinks, entry counts and decompressed size, and uses temporary directories with cleanup.

## Operation

Run `uv run alembic upgrade head` before starting the API against an existing database. CSP output defaults to the runtime directory; a configured export folder contains project-specific immutable handoff revisions.

The builder extracts LoRA tags into model modifiers. Current approved workflows do not expose modifier slots, so modifier-bearing drafts are rejected at generation rather than silently dropping modifiers. Real ComfyUI/GPU validation passed on 2026-10-11; see [the live validation report](../validation/comfy_prompt_library_20261011.md).

Eagle integration, Blender providers, CSP round-trip and posting to platforms remain at the future milestones specified in R1. Publishing remains a preview.

Imported prompt components can be searched and selected in the shot editor. Save shot conditions and rebuild the prompt; modified drafts retain explicit replacement confirmation. Library component IDs and content hashes are included in context hashing, draft metadata and immutable generation provenance. The imported `soft_indoor` lighting is the profile fallback unless a shot lighting override or selected lighting wins. Legacy brace alternatives resolve to their first branch deterministically; legacy macro execution is not supported.
