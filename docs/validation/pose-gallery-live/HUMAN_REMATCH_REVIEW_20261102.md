# A3 Pose Gallery Live — Human GT rematch visual assessment

- Review date: 2026-11-02 (JST)
- Rematch input commit: `368171f58b0e855186bcc10a5316f3e4ca6a8522`
- Review type: assistant visual inspection of GitHub images, source `diag.webp`, reference/flip tiles, generated PNGs, checklists, and manifests; **not an independent recruited human rater**
- Auto: **PASS** (rematch), unchanged
- Human GT: **FAIL** — formal A3 PASS not granted
- Earlier review: `HUMAN_REVIEW_20261102.md` (retained)

| Case | Verdict | Evidence |
|---|---|---|
| P01 Prompt-only | PARTIAL | Output is seated with one prominent bent knee, other leg extended, whole body and foot visible, but hand rests near raised knee/face rather than on top of head. |
| P02 Reference / LLLite | PASS on coarse required cues | REF depicts seated, one knee raised, one arm/hand atop head, opposite leg extended; output reproduces these main cues and includes visible lower legs/feet rather than standing waist-up. Exact limb laterality and joints are not matched closely. |
| P03 Flip | FAIL | Seed `33102` matches P02; model/prompt/control strength match, `flipped=true` and SHA differs. REF-flip is shown in contact sheet. However, both generated P02 and P03 have prominent raised knees toward image-left and overhead arms toward image-left. Their differences are not a credible output-level left-right mirror. |
| P04 Character isolation (C01/C07/C10) | PASS | C01 remains white/aqua-haired and royal-blue, C07 short blonde and warm idol-colored, C10 silver/teal with black hairband; no obvious sibling/reference mannequin identity leakage. All seated. |
| P05 Outfit A/B | PARTIAL; full test FAIL | Lize identity is maintained; A blue/white royal dress vs B red cardigan + blue plaid skirt visible. Both seated with head arm. But A has two legs forward from a more frontal camera, while B raises a leg sharply in a side/diagonal view. Fixed pose, limb geometry, and shot framing are not achieved even at same seed and reference SHA. The crown in B comes from unchanged character prompt, not necessarily leakage from A. |

## Root cause repaired; residual failure

The previous `sw-pose-0001` metadata incorrectly described seated line-art as standing. New Shisei pose records `sw-pose-0001` through `0005` now declare seated descriptions, and the reviewed `sw-pose-0005/diag.webp` genuinely depicts a seated asymmetrical figure with knee up and one hand atop head. This **corrects catalog semantics** and improves reference adherence, but is not sufficient to prove output-side mirrored pose and stable garment-only changes.

P02/P03 remain distinguishable outputs at same seed and differing flipped input, but visual laterality still doesn't mirror. A changed input SHA is evidence of pixel transformation, not output success. P05 similarly holds seed and source SHA but output pose/framing is not identical, so clothing-only isolation fails.

## Narrow next rematch

1. **P03:** compare full-size same-seed P02/flip image with overlaid or manually annotated shoulders, hip, head arm, raised knee, extended leg. Match mirrored body-side landmarks against REF/REF-flip. If not followed, investigate actual pose-control injection, strength, image preprocessing/resize, and model adherence. Do not treat source flip SHA as PASS.
2. **P05:** keep character, seed, prompt except outfit, model, full-body framing and pose reference constant. Verify generated landmark/limb configuration actually remains stable and outfit B does not carry unwanted A wardrobe details. Optional paired reference masks/control refinement if current LLLite isn't sufficient.
3. **P01:** ensure hand-on-head cue appears on output to raise partial to PASS. Source pack and metadata need no further label change for this specific pose.
4. Re-render only failing/partial cases and repeat visual review. Preserve current and prior images/manifests/checklists in version history. A4 remains unstarted and Phase 2.1 UI remains independent.

## Evidence

- `docs/validation/pose-gallery-live/contact_sheet.png` (REF and REF flip in first two tiles)
- Eight `P*/image.png` files and `manifest.json`
- `data/reference/poses/shisei/sw-pose-0005/pose.json` and `diag.webp`

Current verdict is for the frozen single-seed examples, not a generalized pose accuracy rate.
