# A3 — Pose Gallery Live (P01–P05)

- status_auto: `PASS` (remediation rematch)
- status_human: `FAIL — 2026-11-02 rematch visual GT; P03 flip and P05 fixed-pose criteria unmet`
- prior_human: `FAIL @ e0b8f0f` (see HUMAN_REVIEW_20261102.md)
- rematch_artifact_commit: `368171f`
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

- [ ] P01 seated cues + full body — PARTIAL: seated/full-body yes, hand-on-head no
- [x] P02 tracks REF seated posture (not upright standing) — PASS for coarse cues; not exact joints
- [ ] P03 mirrored vs P02 at same seed — FAIL: outputs not clear mirror
- [x] P04 identities remain separated — PASS across C01/C07/C10
- [ ] P05 outfit changes with fixed posture/framing — PARTIAL: outfits distinct; framing/leg pose differs

### Local rematch spot-check (not formal PASS)

- **P02/P03**: both seated with raised knee + hand near head; P03 laterality differs from P02 at seed 33102.
- **P05**: A royal / B red cardigan+plaid both seated; crown still present on B (secondary).
- Prior FAIL review preserved in `HUMAN_REVIEW_20261102.md`.
- Prior contact sheet: `contact_sheet_pre_remediation.png` when present.

## Rematch visual GT (2026-11-02)

The semantic pack correction and rematch resolved the upright-standing failure: P02 now shows seated, one knee raised, hand on head and visible feet; P04 identity separation also PASS. P01 PARTIAL because the hand is not on top of the head. P03 remains FAIL: although reference SHA changes and P02/P03 now share seed 33102, the prominent knee and overhead arm remain on the same image side in both outputs; generated poses are not demonstrably mirrored. P05 PARTIAL: red cardigan / plaid skirt successfully replaces blue/white dress while Lize remains recognizable, but A/B leg configuration and camera framing do not remain fixed. **Therefore A3 Human FAIL; A4 stays blocked.** Old human records and generated PNGs are retained. See `HUMAN_REMATCH_REVIEW_20261102.md`.

## Next

- Remediate P03 actual output mirror and P05 image-level pose/framing lock; optionally P01 hand-on-head; rerun with identical controllable variables and repeat visual GT
- Formal A3 PASS only after visual GT; then A4

## Remediation r2 rematch

- status_auto: `PASS` (r2 rematch generated)
- status_human: `PENDING`
- commit: `acd8862`
- comfy: `0.42.5`
- control_strength: `1.85`
- prompt_mode: side-agnostic locked pose cues (no left/right words) for P02/P03/P05
- P02/P03 seed: `33102` (identical prompt+seed; flip only)
- P01 seed: `33201`
- P05 seed: `33105`
- recorded_at: `2026-11-01T17:09:00.545373+00:00`
- entry: `pnpm test:pose-gallery:live:r2`

### Hypothesis addressed

1. Prompt limb text with implied side competed with flipped refs → use side-agnostic
   but still specific locked cues + higher LLLite strength.
2. P05 pose drift from weak control / crown+outfit churn → strength 1.85,
   crown stripped on B, identical pose text.

### Local r2 spot-check (not formal PASS)

- **P01**: hand on crown/head + seated knee-up looks achieved (seed 33201).
- **P02**: seated, knee up, hands near/on head restored after strength/prompt tighten.
- **P03**: still seated with head-arm; **laterality vs P02 remains uncertain** — needs human mirror check.
- **P05**: outfits distinct; **pose/framing still diverge** (A knee-up+hands-on-head vs B different crouch).

### Human recheck focus

1. P03 vs P02: mirrored knee / head-arm laterality (not SHA alone)
2. P05 A vs B: joint layout + camera stay fixed
3. P01: hand clearly on top of head
4. P02 regression: still seated with REF cues after strength/prompt change

Prior reviews: `HUMAN_REVIEW_20261102.md`, `HUMAN_REMATCH_REVIEW_20261102.md`

## Remediation r3 rematch

- status_auto: `PASS` (r3 rematch generated)
- status_human: `PENDING`
- commit: `6d2c166`
- comfy: `0.42.5`
- control_strength: `2.0`
- P02/P03 seed: `33102` (identical prompt; flip only)
- P01 seed: `33301`
- P05 seed: `33105`
- recorded_at: `2026-11-02T15:25:11.007563+00:00`
- entry: `pnpm test:pose-gallery:live:r3`

### Auto evidence upgrades

1. `P02/control.png` and `P03/control.png` are the final bytes fed as `pose_image`
2. Pixel assert: P03 control == H-flip(P02 control)
3. Output laterality heuristic recorded in manifests (not Human PASS)
4. Crown is Outfit A only; `a3_outfit_b_marker` lives in manifest, never in prompt

### Human recheck focus

1. P03 vs P02 body laterality (use CTRL tiles + outputs)
2. P05 A vs B joint/camera lock with crown absent on B
3. P01 hand-on-head
4. P02 still tracks REF after strength 2.0

Prior: `HUMAN_REVIEW_20261102.md`, `HUMAN_REMATCH_REVIEW_20261102.md`
