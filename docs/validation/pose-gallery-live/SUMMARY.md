# A3 — Pose Gallery Live (P01–P05)

- status_auto: `PASS`
- status_human: `FAIL — visual GT 2026-11-02 (source pose mismatch)`
- commit: `3f6e5f5`
- comfy: `0.42.5`
- pose: `sw-pose-0001` / `diag`
- recorded_at: `2026-11-01T08:43:46.996174+00:00`
- entry: `pnpm test:pose-gallery:live`

## Cases

| Case | Seed | Auto | Notes |
|------|------|------|-------|
| P01 Prompt Pose | 33001 | PASS | BaseRender + pose_prompt |
| P02 Reference / LLLite | 33002 | PASS | PoseControlledRender |
| P03 Flip | 33003 | PASS | flipped sha ≠ P02 |
| P04 Character isolation | 33004 | PASS | C01 / C07 / C10 shared pose |
| P05 Outfit isolation | 33005 | PASS | Outfit A/B shared pose |

## Human review (required for formal A3 PASS)

- [ ] P01 pose cues readable from prompt-only path
- [ ] P02 posture tracks reference
- [ ] P03 mirrored vs P02
- [x] **P04** no pose-thumbnail identity leak across C01/C07/C10 — identity only
- [ ] P05 pose fixed while outfit changes

Focus: **P04**. Gallery-first fails if reference person identity leaks.

### Local auto spot-check (not formal human PASS)

- **P04**: C01 / C07 / C10 read as distinct identities (Lize / Tsubasa / Firefly); no shared thumbnail person.
- Framing is often upper-body; hand-on-hip lean is secondary to isolation check — confirm pose tracking on P02/P03/P05 during human review.

## Human visual GT (2026-11-02)

**Human FAIL; A3 is not a formal PASS.** P01 PARTIAL (hand-on-hip, cropped body), P02 FAIL (reference seated, output standing), P03 FAIL (no visible mirrored pose; comparison seeds differ), P04 PASS on character separation only, P05 PARTIAL (outfit differs, pose and framing drift).

**Data integrity:** `data/reference/poses/shisei/sw-pose-0001/pose.json` declares `Standing pose 001`, `standing`, and `diag` text `standing three-quarter view, one hand on hip, contrapposto`, with `qc_status=pass`. Yet the actual `front.webp`, `diag.webp` and `side.webp` show a seated figure with one knee up. The reference image hash corresponds to the recorded P02 pose input. SHA/provenance correctness is not visual pose correctness. See `HUMAN_REVIEW_20261102.md` for detailed findings and retest requirements.

## Next

- Repair pose asset/semantic catalog inconsistency; rerun full-body posture tracking, paired same-seed flip, and outfit-isolation visual checks; then repeat Human GT
- Then A4 Gate 3 Outfit A→B→C→A
- Phase 2.1 UI/UX remains a separate track
