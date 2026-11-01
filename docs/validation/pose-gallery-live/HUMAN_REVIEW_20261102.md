# A3 Pose Gallery — Visual GT Review (2026-11-02)

**Verdict: HUMAN FAIL.** Recorded Auto PASS for `ccc85c4` remains valid as routing, decode and provenance evidence. This is a visual review by the assistant rather than a separately recruited human rater. No new Comfy generation was executed.

| Case | Human verdict | Observations |
|---|---|---|
| P01 prompt-only | PARTIAL | One hand at hip; lower-body contrapposto and 3/4 view not verifiable due crop. |
| P02 reference/LLLite | FAIL | Actual source `sw-pose-0001/diag.webp` is a seated pose, one knee up, hands behind for support. C01 image is near-frontal upright standing and crops out posture cues. |
| P03 flipped reference | FAIL | Changed SHA confirms pixel-level flip, but generated output does not show mirrored seated limb/hip configuration. P02 seed 33002 differs from P03 seed 33003, confounding paired inference. |
| P04 C01/C07/C10 | PASS — identity isolation only | Lize, Tsubasa and Firefly retain separate hair, face, accessories and outfit signatures. No apparent reference-person or cross-sibling identity leak. Posture adherence is not established. |
| P05 outfit A/B | PARTIAL / full criterion FAIL | A (royal blue/white) vs B (red cardigan/plaid) switch visibly works; Lize remains recognizable, but A is upright near-frontal whereas B is overhead/leaning and closer framed. Pose not fixed; crown accessory persists in B. |

## Root-cause blocker: reference catalog does not match its assets

`data/reference/poses/shisei/sw-pose-0001/pose.json` claims `Standing pose 001`, category `standing`, and a diagonal prompt `standing three-quarter view, one hand on hip, contrapposto` (`qc_status=pass`). Its actual `front.webp`, `diag.webp`, and `side.webp` are *all seated poses with a knee raised*, so the asset representation does not match the declared semantic pose. The `diag.webp` SHA is `4461d85aa5d5291b78b69f491b7176e6ec3fc4501db63e42b4139a1e505f17b1`, the exact hash reported as P02 unflipped input. This is a data-identity/QC error; do not treat pose SHA differences as proof of visual pose adoption.

## Remediation and recheck requirements

1. Audit the full built-in pose pack for metadata-to-image correctness. Either describe the seated image honestly and test its seated posture, or replace it with a genuinely standing reference with new SHA/provenance. Block misleading QC pass for mismatched semantic/image pairs.
2. Use clearly asymmetric **full-body** poses for P02/P03, so limbs and body weight shift are measurable and not obscured by tight framing. Compare actual reference image and resulting pose—not description only.
3. For flip, keep seed, model, character, outfit, prompt, strength, framing, source pose fixed. Flip true/false is the only change. Include both source variants and generated variants in the contact sheet.
4. For outfit isolation, hold seed, pose, framing, model, and identity constant; change OutfitProfile only. Verify no unintended outfit/accessory bleed and both outputs visually preserve posture.
5. P04 identity isolation can remain a positive result, but recheck on corrected references. Reassess P01 3/4/contrapposto with a full-body crop if a complete pass is desired.
6. Keep A3 Human FAIL pending regenerated evidence and re-review. A4 depends on formal A3 PASS. Phase 2.1 UI remains an independent track.

**Evidence:** `docs/validation/pose-gallery-live/contact_sheet.png`, eight `image.png`, per-case manifests/checklists, and `data/reference/poses/shisei/sw-pose-0001/{pose.json,front.webp,diag.webp,side.webp}`.

**Preservation:** the live test rewrites individual `gt_checklist.md` files on rerun; this separate review file retains the audit history.
