# Gate 2.7 — Anima Full Character Coverage

- status_auto: `PASS`
- status_human: `FAIL — remediation rematch generated; awaiting human rematch`
- human_identifiable: `8/11` (pre-rematch)
- commit_auto: `053800f6`
- comfy: `0.42.5`
- recorded_at: `2026-10-31T15:40:28.740514+00:00`
- entry: `pnpm test:anima:gate2_7`

## Roster

| ID | Name | Seed | Prompt | W×H | Trigger | Auto | Human |
|----|------|------|--------|-----|---------|------|-------|
| C01 | リゼ・ヘルエスタ | 27001 | gate26_adopted | 768×1024 | yes | PASS | 6/8 identifiable |
| C02 | 栞葉るり | 27002 | compiled | 768×1024 | yes | PASS | 3/8 **not identifiable** |
| C03 | 夜見れな | 27003 | compiled | 768×1024 | yes | PASS | 7/8 identifiable |
| C04 | 星川サラ | 27004 | gate26_adopted | 768×1024 | yes | PASS | 5/8 identifiable, drift |
| C05 | イレイナ | 27005 | gate26_adopted | 768×1024 | yes | PASS | 8/8 identifiable |
| C06 | 春日未来 | 27006 | compiled | 768×1024 | yes | PASS | 4/8 **not confidently identifiable** |
| C07 | 伊吹翼 | 27007 | compiled | 768×1024 | yes | PASS | 7/8 identifiable |
| C08 | 暁美ほむら | 27008 | gate26_adopted | 768×1024 | yes | PASS | 7/8 identifiable |
| C09 | 鹿目まどか | 27009 | compiled | 768×1024 | yes | PASS | 8/8 identifiable |
| C10 | ホタル（Firefly） | 27010 | gate26_adopted | 768×1024 | yes | PASS | 8/8 identifiable |
| C11 | オリジナル成人実写系 | 27011 | compiled | 768×1024 | yes | PASS | 4/8 **anime bias; photoreal criterion FAIL** |

## Human review

- [x] catastrophic image failure なし
- [ ] ≥9/11 が GT 主要項目で識別可能 — **8/11**
- [x] contact sheet で別人取り違えが支配的でない
- [ ] C11 が極端な anime 化で破綻しない — **FAIL: strongly anime/illustrated**

### Main remediation targets

1. **C02 栞葉るり** — restore canonical police/canine identity: silver hair, characteristic eyes, police cap/poncho, tail and silhouette.
2. **C06 春日未来** — strengthen Mirai-specific hair/eye/outfit cues; current result is too generic for confident standalone identification.
3. **C11 original adult photoreal** — Anima output remains anime-styled despite photorealistic/realistic tags; requires a different model/profile or explicit decision to remove C11 from Anima character-coverage gate.
4. **C04 星川サラ** — identifiable but eye colors/default outfit drift; keep as secondary refinement target.

See `human_scores.csv` for per-fixture notes.

## Gate decision

**A2 is not yet a formal PASS.** Automatic execution coverage is PASS, but the frozen Human criteria are not met.  
Do not advance the quality claim to A3 as if A2 passed; first remediate/re-run C02/C06/C11 (and preferably C04), then rescore the affected rows.

## Next after A2 Human PASS

- A3 Pose Live P01–P05

## Remediation rematch

- status: `GENERATED — awaiting human rematch`
- commit: `6e6b3dc`
- comfy: `0.42.5`
- recorded_at: `2026-10-31T16:47:11.675838+00:00`
- entry: `pnpm test:anima:gate2_7:remediation`
- seeds unchanged: C02=27002, C04=27004, C06=27006, C11=27011

| ID | W×H | SHA256 (short) |
|----|-----|----------------|
| C02 | 768×1024 | `a398f574a4dd` |
| C04 | 768×1024 | `2dd47d0bac47` |
| C06 | 768×1024 | `ac0edad917e9` |
| C11 | 768×1024 | `17a066a58517` |

Pre-remediation PNGs kept as `image_pre_remediation.png` for side-by-side.

Local visual spot-check (not a substitute for human GT rematch):

- **C02**: police hat + blue flower, capelet, blue shorts, dog tail present (prior miss). Eye color still drifts toward amber/yellow vs GT green.
- **C04**: heterochromia (red / yellow-amber) and x-ornament clearer; outfit still stylized idol.
- **C06**: side ponytail + star clips + pink sailor idol cues stronger vs generic pink idol.
- **C11**: photoreal / live-action look achieved on this rematch seed (prior was anime). Confirm against C11 criterion on rematch.

### C11 policy note

Anima Base (`anima_baseV10`) is anime-tuned. Photoreal tags without a photoreal model/profile may still fail the C11 criterion. If rematch remains illustrated, exclude C11 from Anima identity PASS and track photoreal coverage under a separate model profile (Phase 2.1+).

### Next

1. Human rematch of C02 / C04 / C06 / C11 on updated `contact_sheet.png`
2. Fill `gt_checklist.md` per 8 GT items + update `human_scores.csv`
3. Require ≥9/11 identifiable and C11 photoreal criterion (or policy carve-out)
4. Only then proceed to A3 Pose Live
