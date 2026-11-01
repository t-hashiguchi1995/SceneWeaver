# A3 — Pose Gallery Live (P01–P05)

- status_auto: `PASS` (remediation rematch)
- status_human: `PENDING — rematch awaiting visual GT`
- prior_human: `FAIL @ e0b8f0f` (see HUMAN_REVIEW_20261102.md)
- commit: `e0b8f0f`
- comfy: `0.42.5`
- pose: `sw-pose-0005` / `diag` (asymmetric seated; metadata remediated)
- recorded_at: `2026-11-01T15:30:09.468736+00:00`
- entry: `pnpm test:pose-gallery:live`

## Cases

| Case | Seed | Auto | Notes |
|------|------|------|-------|
| P01 Prompt Pose | 33101 | PASS | seated pose_prompt + full body |
| P02 Reference / LLLite | 33102 | PASS | PoseControlledRender |
| P03 Flip | 33102 | PASS | **same seed as P02**; flip only |
| P04 Character isolation | 33104 | PASS | C01 / C07 / C10 |
| P05 Outfit isolation | 33105 | PASS | same seed+pose; outfit A/B |

## Remediation vs prior FAIL

1. Shisei pack labels/prompts corrected from false `standing` → `sitting`
2. Switched to asymmetric `sw-pose-0005` (knee up + hand on head)
3. P03 uses identical seed to P02
4. Contact sheet includes REF and REF-flip tiles
5. Prompts force full-body framing; standing in negative

## Human review (required for formal A3 PASS)

- [ ] P01 seated cues + full body
- [ ] P02 tracks REF seated posture (not upright standing)
- [ ] P03 mirrored vs P02 at same seed
- [ ] P04 identities remain separated
- [ ] P05 outfit changes with fixed posture/framing

### Local rematch spot-check (not formal PASS)

- **P02/P03**: both seated with raised knee + hand near head; P03 laterality differs from P02 at seed 33102.
- **P05**: A royal / B red cardigan+plaid both seated; crown still present on B (secondary).
- Prior FAIL review preserved in `HUMAN_REVIEW_20261102.md`.
- Prior contact sheet: `contact_sheet_pre_remediation.png` when present.

## Next

- Human GT on updated `contact_sheet.png`
- Formal A3 PASS only after visual GT; then A4
