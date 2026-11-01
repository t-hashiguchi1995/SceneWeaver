# A3 — Pose Gallery Live (P01–P05)

- status_auto: `PASS`
- status_human: `PENDING`
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
- [ ] **P04** no pose-thumbnail identity leak across C01/C07/C10
- [ ] P05 pose fixed while outfit changes

Focus: **P04**. Gallery-first fails if reference person identity leaks.

### Local auto spot-check (not formal human PASS)

- **P04**: C01 / C07 / C10 read as distinct identities (Lize / Tsubasa / Firefly); no shared thumbnail person.
- Framing is often upper-body; hand-on-hip lean is secondary to isolation check — confirm pose tracking on P02/P03/P05 during human review.

## Next

- Human GT on `contact_sheet.png` + per-case checklists → formal A3 PASS
- Then A4 Gate 3 Outfit A→B→C→A
- Phase 2.1 UI/UX remains a separate track
