# ADR 0011 — Default Prompt Assembly + Prompt Component Library (v0.2 Sprint 4)

## Status

Accepted (design); **implementation targets Sprint 4**, not Sprint 3.
This document is the Sprint 4 design authority. The six implementation
clarifications below do not change direction — they remove ambiguity.

## Context

Legacy `prompts.zip` (Character YAML, `dynamic/sfw_*.yaml`, `lighting_default.yaml`,
`comfy/stand_seiso_uniform.yaml`, `bustier_batch.yaml`, etc.) is rich enough to seed
SceneWeaver’s Prompt Library. It is **not** safe to paste old final strings as
“the default prompt”:

- Character `prompt.base` repeats shared style/quality (and sometimes adult tags)
- Many characters default to `romance_soft_indoor` from `presets_r18.yaml`
- `lighting_default.yaml` mixes general and mood lighting in one file
- `sfw_*.yaml` reuses old key names like `r18_seq_*` even when content is SFW
- Old system was `YAML + Python script` (see `bustier_batch.yaml` notes) — YAML alone
  does not fully reproduce finals

ADR 0010 already defines PromptDraft (mutable) and GenerationAttempt (immutable).
This ADR defines how **rendered_base** should eventually be built from Semantic Context
via components — and what Sprint 3 Importer must / must not do.

## Decision

### Hard boundary

```text
Legacy YAML
    ↓
Importer  →  Prompt Library (presets / components)   ← Sprint 3
    ↓
Default Prompt Builder (Profile + Resolver + Assembler)  ← Sprint 4
    ↓
Rendered Base → PromptDraft → Final → GenerationAttempt
```

- **Importer never builds Default Prompt strings for runtime.**
- **Only SceneWeaver Prompt Builder** produces `rendered_base_*` from context.
- `<lora:...>` prefers `ModelModifier` over embedding in identity text.
- `generate.width/height/...` → `RenderPreset` (not Prompt).
- Pixiv/Patreon settings → `ReleaseDefaults` (not Prompt).

### Pipeline (Sprint 4)

```text
Character / Scene / Outfit / Shot
              ↓
      ResolvedPromptContext
              ↓
       DefaultPromptProfile (versioned)
              ↓
       PromptComponent Resolver
              ↓
       Content Policy Filter     ← runtime enforce, do not trust Importer alone
              ↓
       Conflict Resolver
              ↓
       Deterministic Assembler
              ↓
       BuiltPrompt
         ├ positive
         ├ negative
         ├ components[]
         ├ model_modifiers[]
         └ warnings[]
              ↓
       PromptDraft.rendered_base_*
```

### DefaultPromptProfile (versioned, immutable)

Not one global default. Examples of logical ids:

```text
anima_story_panel
anima_character_fullbody
anima_portrait
anima_character_sheet
```

Identity is **versioned and immutable** (same idea as PromptTemplate):

```text
profile_id      = anima_story_panel
profile_version = v1
```

or opaque immutable ids `anima_story_panel_v1` / `_v2` — never mutate an existing
version in place. Changing assembly policy requires a new version.

GenerationAttempt must eventually snapshot:

```text
prompt_profile_id
prompt_profile_version
```

alongside existing final_* / prompt_hash fields (ADR 0010).

Each profile declares `positive_order` / `negative_order`, capability, model,
`content_rating`, and slot defaults (expression, camera, lighting, style, quality).

### PromptComponent (internal representation)

Keep structure until Assembler. Stable identity is required for provenance:

```text
component_id       e.g. lighting:soft_indoor
component_version  e.g. v1
kind
subkind            optional; required for merge-limited kinds
text
content_rating
model_scope
source
source_ref
priority
enabled
metadata
```

Canonical display / provenance key:

```text
{component_id}@{component_version}
# lighting:soft_indoor@v1
# style:legacy_fuzichoco@v2
# character_identity:fujita_kotone@v1
```

Prompt text snapshot alone can reproduce an image; **component id+version**
explains *why* that prompt was assembled.

Kinds map from legacy assets, e.g.:

| Legacy | Component / Preset |
|---|---|
| `characters/*.yaml` → `identity` | CharacterIdentityPreset |
| `prompt.base` | split → Style / Quality / BodyTrait / ModelModifier |
| `categories.costume` | OutfitPromptPreset |
| `categories.pose` | PosePromptPreset |
| `categories.expression` | ExpressionPromptPreset |
| `lighting_default.yaml` items | LightingPreset (+ per-item rating) |
| `sfw_*.yaml` | Scene / Location / Pose / Expression (normalize keys) |
| `stand_seiso_uniform` / `bustier_batch` outfits | Outfit / Pose / Expression seeds |
| `bustier_batch` situations | Background / ScenePreset |

### Content rating — runtime enforcement

Importer classification is necessary but **not sufficient**. Before Conflict
Resolver / Assembler, apply a Content Policy Filter:

```text
Profile.content_rating  ⨝  Component.content_rating
```

Example: Profile `general` + Component `adult` → exclude (or hard-error per
policy); adult components must never reach Assembler for a general profile.
Do not assume “Importer already filtered correctly.”

### Assembly order (positive)

```text
1 subject_count
2 character_identity
3 character_traits
4 outfit
5 expression
6 pose / gaze
7 camera / composition
8 scene / background
9 lighting
10 style
11 quality
12 user_additions
```

Negative uses the same component model with its own order.

### Selection priority + deterministic tie-break

Precedence tiers:

```text
User explicit selection
  → ShotSpec / EffectiveState
  → Character / Outfit defaults
  → Project DefaultPromptProfile
  → Model global defaults
```

Do **not** concatenate competing values (e.g. soft indoor + golden hour + studio).

**Default Prompt Builder MUST be deterministic.** Same ResolvedPromptContext +
same Profile version → byte-for-byte identical `BuiltPrompt.positive/negative`
(and stable `model_modifiers` / component lists), independent of DB fetch order.

When two candidates share the same precedence tier, resolve by:

```text
1. precedence tier
2. explicit component.priority  (higher wins)
3. stable component_id         (lexicographic)
```

Never use insertion order or query order as a tie-break.

### Conflict policy (category)

```text
subject_count   exclusive
outfit          replace
pose            replace
camera          replace
background      replace
expression      merge-limited   (see below)
lighting        replace
style           merge
quality         merge
```

#### `merge-limited` (expression) — fixed meaning

Expression components MAY declare `subkind`:

```text
mouth | eyes | emotion | blush | …
```

Policy:

```text
merge across different subkinds
replace within the same subkind   (using precedence + tie-break)
```

Allowed together:

```text
emotion = embarrassed
mouth   = soft smile
eyes    = warm eyes
```

Not allowed together (same subkind → one winner):

```text
mouth = closed mouth
mouth = open mouth
```

### ModelModifier — separate from prompt text

`BuiltPrompt` explicitly separates LoRA / similar from CLIP text:

```python
BuiltPrompt(
    positive="1girl, ...",
    negative="text, watermark, ...",
    components=[...],          # PromptComponents that contributed text
    model_modifiers=[
        ModelModifier(kind="lora", model="foo.safetensors", strength=0.8),
    ],
    warnings=[...],
)
```

Comfy path:

```text
positive / negative  →  CLIP / Text Encoder
model_modifiers      →  LoRA Loader / Workflow slot
```

Legacy `<lora:foo:0.8>` must not remain in Anima prompt body after migration.

### Application modules (Sprint 4)

```text
domain/prompt/     PromptComponent, PromptPreset, PromptAssemblyProfile (+ Draft)
application/prompt/
  ResolvePromptContext
  ResolvePromptComponents
  FilterByContentPolicy
  ResolvePromptConflicts
  BuildDefaultPrompt  → BuiltPrompt
```

`BuildDefaultPrompt` feeds `PromptDraft.rendered_base_*`.

### Migration from AnimaCompilerV1 (no big bang)

Sprint 3 path stays until Sprint 4 Builder is proven:

```text
RenderedPromptProvider  (Application Port)
        ↑
 ┌──────┴──────┐
 │             │
AnimaCompiler  DefaultPromptBuilder
legacy path    new path
```

Switch via feature flag / profile selection. Compare tests:

```text
same ResolvedPromptContext
  → old compiler output
  → new builder output
```

Deprecate `anima_compiler_v1` only after full cutover.

### Legacy import rules (Sprint 3 hardening / Sprint 4 input)

- Classify **per record**, not per file (`lighting_default` items get own ratings)
- Do **not** inherit Character `preset: romance_soft_indoor` as SceneWeaver default
- Character Identity may be reused; defaults come from SceneWeaver profiles
  (e.g. `anima_story_sfw_v1`)
- Normalize Domain names (`r18_seq_setup` → `scene_setup` / `sequence`, etc.)
- Promote repeated Character `base` blobs into shared Style/Quality presets once

## Sprint 4 test focus

| Case | Expected |
|---|---|
| Profile lighting + Shot lighting | Shot only |
| Character outfit + User outfit | User only |
| smile + embarrassed (different subkinds) | both if policy allows |
| open mouth + closed mouth (same subkind) | one winner |
| general Profile + adult Component | excluded / error before Assembler |
| Same Context built 100× | byte-for-byte identical finals |
| Change Component fetch order | Final Prompt unchanged |
| Legacy LoRA tag | ModelModifier, not prompt body |
| Profile v1 → v2 later | past Attempts stay immutable |

## Non-goals (Sprint 3)

- Full Default Prompt Builder / Conflict Resolver
- Auto-wiring Legacy Character `base` as rendered_base
- Try-On / Dialogue PromptEditors (Sprint 4+)

## Responsibility summary

```text
Legacy Assets → Importer → Prompt Library
  Identity / Outfit / Expression / Pose / Lighting / Style / Quality

Character / Scene / Outfit / Shot
  → ResolvedPromptContext
  → DefaultPromptProfile (id + version)
  → Component Resolver
  → Content Rating Filter
  → Conflict Resolver
  → Deterministic Assembler
  → BuiltPrompt { positive, negative, components, model_modifiers, warnings }
  → PromptDraft.rendered_base_*
  → User Edit
  → GenerationAttempt (finals + profile_id/version + component refs)
```

## Consequences

- Sprint 3 keeps PromptDraft + Generation Review + Importer normalization path
- Sprint 4 delivers “good first prompt” from Character / Outfit / Scene / Shot
- Provenance can show which `component_id@version` contributed which tags
- Existing compiler_rule Anima path remains behind the same Port until cutover
- Design direction is fixed; Sprint 4 implements this ADR without further redesign
