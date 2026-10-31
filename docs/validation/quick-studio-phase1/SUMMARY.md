# Quick Studio Phase 1–2 live

- status: `PASS` — **Phase 1–2 formal close evidence**
- code baseline at run: `429bfcf`（artifacts committed with CSS polish follow-up）
- entry: `pnpm test:quick-studio:live`
- comfy: `0.42.5`
- character: リゼ・ヘルエスタ (C01)
- pose: `sw-pose-0001` / `diag`
- capability: PoseControlledRender / model `anima_pose`
- seed: `424242`
- PNG: `quick_studio_sw-pose-0001_diag_seed424242.png` (768x1024)
- pose_asset_sha256: `4461d85aa5d5291b78b69f491b7176e6ec3fc4501db63e42b4139a1e505f17b1`
- materialize: copy — formal `c5d9395a67344cffab539895d8` keeps same asset IDs

## Vertical slice

```text
/studio session
→ Character + OutfitProfile + Anima
→ Shisei Pose + angle
→ PoseControlledRender (Comfy)
→ PNG ≥512
→ provenance (model/seed/pose sha)
→ Adopt = copy (no rerender)
```
