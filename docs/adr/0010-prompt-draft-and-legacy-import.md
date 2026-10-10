# ADR 0010 — Prompt Draft + Legacy Importer (v0.2 Sprint 3)

## Status

Accepted

## Context

Creators need to see and edit the prompt that will actually run, without mutating
Git-managed templates. Past attempt provenance must remain immutable after edits.
Legacy YAML from the previous studio must be imported once into SceneWeaver Domain,
not read at runtime.

## Decision

### PromptDraft (mutable)

- UUID primary key; logical uniqueness `(shot_id, template_id, template_version)`
- Shot stores `current_prompt_draft_id`
- Fields: rendered_base_*/edited_*, `context_hash`, `source_shot_revision`,
  `source_kind` (`jinja` | `compiler_rule`), `source_ref`
- `modified` / `stale` are **server-derived** (never trusted from the client)
- `stale` when `draft.context_hash != current_context_hash` — never silent overwrite
- APIs: ensure, get, put edits, `reset-edits`, `rebuild` (no server `/diff`)
- `rebuild` with user edits requires `confirm=true` — never silently discard edits

Past PromptDraft rows are not versioned in Sprint 3. Reproducibility of past
generations lives on GenerationAttempt snapshots. A future `PromptDraftRevision`
can be added if edit history itself is needed.

### context_hash inputs

Wire format today:

```text
shot_revision + render_spec + template_id + template_version
```

Canonical JSON: `sort_keys=True`, `separators=(",", ":")`, UTF-8, then sha256 hex.

**Resolved-context rule:** `render_spec` used for `context_hash` MUST be the
resolved prompt-affecting semantic context. Any Character, Outfit, Pose,
Expression, Style, or other state read by the prompt compiler must either be
represented in this resolved context or otherwise contribute to the hash.

Conceptually:

```text
ResolvedPromptContext
├ character visual identity
├ outfit state
├ expression
├ pose
├ camera
├ composition
├ style
├ shot revision
├ template/compiler rule
└ template/compiler version
        ↓
canonical JSON
        ↓
context_hash
```

If Character identity tags change but neither `shot_revision` nor the hashed
`render_spec` changes, the Draft will not go stale — that is a bug in how context
is resolved into the hash inputs, not an acceptable gap in this ADR.

### prompt_hash

```python
sha256(
    final_positive.encode("utf-8")
    + b"\x00"
    + final_negative.encode("utf-8")
).hexdigest()
```

`final_positive` and `final_negative` are hashed byte-for-byte as submitted to the
ImageBackend. No trimming, Unicode normalization, newline conversion, or tag
reordering is performed solely for hashing.

```text
PromptDraft
↓
final strings 確定
├─ prompt_hash
└─ ImageBackend へ送信
```

Both paths MUST use the same string values.

### Render source honesty

Anima Shot path uses `compiler_rule` / `anima_compiler_v1`. Template tab shows the
compiler rule description — not a decorative Jinja file. `GET .../prompt-template`
resolves from the current draft only (no user-supplied path).

UI may present this as “生成元 / Anima Compiler v1” plus a short explanation that
the prompt was produced by SceneWeaver’s Anima generation rule.

### GenerationAttempt

Stores an immutable snapshot: template_*, source_*, rendered_base_*, final_*,
prompt_hash, modified, prompt_draft_id (reference only). Later Draft edits must
not mutate past Attempts.

### Legacy importer

- Identity: `(source, source_file, legacy_key)`
- `source_file` is a normalized POSIX-style path relative to the import root
  (e.g. `characters/foo.yaml`, `dynamic/sfw_scene.yaml`). Host-specific absolute
  paths are never part of importer identity.
- Idempotent: create / unchanged / conflict / skip; never overwrite user edits
- One `--apply` run = one DB transaction
- Adult: explicit markers only; ambiguous → unsupported (never guess SFW)
- **Importer builds Prompt Library / seed entities — never runtime Default Prompt
  strings.** Default assembly is ADR 0011 (Sprint 4).
- Do not treat file-level SFW labels as sufficient; rating is per imported record.
- Do not inherit Character `preset: romance_soft_indoor` as SceneWeaver default.

## Responsibility flow

```text
Legacy YAML ──Importer──► Prompt Library (presets)     [Sprint 3]
                                 │
Git Template / Compiler Rule     │  (Sprint 4: Default Prompt Builder
          │ immutable            │   consumes Library + ResolvedPromptContext)
          ▼                      ▼
      Rendered Base ◄────────────┘
          │
          ▼
     PromptDraft
       mutable
          │
          ├─ reset-edits
          ├─ rebuild(confirm)
          └─ user edit
          │
          ▼
      Final Prompt
          │
          ├──────────→ ImageBackend
          │
          ▼
 GenerationAttempt
 immutable snapshot
```

Legacy:

```text
Legacy YAML → Importer (dry-run) → classification
  create / unchanged / conflict / skip → Prompt Library / Character seeds
  (not Final Prompt, not PromptDraft.rendered_base)
```

## UI split (Shot Studio vs Generation Review) — Sprint 3 scope

**Generation Review is in Sprint 3**, not deferred. Spec authority:
`docs/architecture/sceneweaver_prompt_generation_review_ui_spec_r1.html`

```text
Shot Studio          → 生成前: PromptDraft を編集・確認
Generation Review    → 生成後: GenerationAttempt の immutable snapshot を確認
```

Recommended routes (implemented):

```text
/shots/:shotId
/shots/:shotId/generations
/shots/:shotId/generations/:attemptId
```

Sprint 3 minimum Review surface:

- 4 candidates (+ large preview)
- Adopt / Reject
- Runtime Positive / Negative (Attempt snapshot only — never live Draft)
- Seed, Template/Compiler Rule, Prompt Hash, Workflow Hash
- 「このPromptを編集して再生成」→ copy finals into Draft → Shot Studio
- Shot-scoped Generation History (newest-first)

API aliases (UI Spec R1):

```text
GET /api/v1/shots/{id}/generations
GET /api/v1/generations/{attemptId}
```

## Consequences

- Shot Studio PromptEditor is the first consumer; Try-On / Dialogue follow later
- Fake / Comfy backends both receive edited final prompts via RenderPlanDTO slots
- Stale detection quality depends on keeping ResolvedPromptContext complete as
  new prompt-affecting inputs are added
- Generation Review is required for provenance UX; Draft alone is not enough
- Advanced compare / filters stay Sprint 4+
- Default Prompt Builder / PromptComponent / Conflict Resolver → [ADR 0011](0011-default-prompt-assembly.md)
