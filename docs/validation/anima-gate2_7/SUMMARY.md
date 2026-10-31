# Gate 2.7 — Anima Full Character Coverage

- status_auto: `PASS`
- status_human: `FAIL — remediation required`
- human_identifiable: `8/11`
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
