# P03 Flip — GT checklist (remediation)

- [ ] Visually mirrored vs P02 (same seed 33102; only flip differs) — Rematch human GT: FAIL (visible mirror)
- [x] Compare REF flip tile on contact sheet
- [x] Auto: flipped=true, pose_asset_sha256 ≠ P02, seed==P02

Human visual verdict: **FAIL (visible mirror)** (2026-11-02)

Notes: REF and REF-flip tiles are included, same seed 33102/model/prompt/strength across P02/P03 and input pose SHA changes. Yet both outputs place the prominent raised knee on screen-left and overhead arm on screen-left. Other arm and extended-leg arrangements vary, but the generated pair is not a clear lateral mirror of the reference A/B.

Review source: `../HUMAN_REMATCH_REVIEW_20261102.md`. Auto checks retained and old human review kept as history.

