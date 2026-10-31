# Quick Image Studio

**Phase:** 1–2  
**Canonical master:** [`../architecture/sceneweaver-master-design-20261031.html`](../architecture/sceneweaver-master-design-20261031.html)

Story/Shot を必須入口にしない。Character / OutfitProfile / Pose(+angle) / Prompt / Model → Generate → Review → Adopt。

## Scratch Shot lifecycle

```text
CREATE → draft
  → Generate → generated
      ├ Regenerate → generated
      ├ Keep → generated (History)
      ├ Adopt → adopted → materialize to Story Shot (COPY state, no rerender)
      └ Delete → abandoned (deletable; auto-purge not required in Phase 1)
```

`render_spec._studio`: `{ source: quick_studio, hidden: true, lifecycle, formal_shot_id? }`

**materialize = copy generation state, not rerender** — adopted asset + prompt/pose/outfit snapshots + provenance を Formal Shot へ引き継ぐ。

## Phase 1 Outfit

既存 Character に紐づく **OutfitProfile 選択のみ**。Costume Gallery / Upload / Try-On は Phase 4。

## Pose

Backend `PoseDefinition` が正。`GET /references/poses` (Summary) / `{id}` (Detail)。Assets は `/api/v1/references/assets/...`。

## 5-stage PASS

See plan verify-slice（angle 選択必須）。
