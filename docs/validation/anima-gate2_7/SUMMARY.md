# Gate 2.7 — Anima Full Character Coverage

- status_auto: `PASS`
- status_human: `PENDING`（contact sheet を GT 採点）
- commit: `6cc7063`
- comfy: `0.42.5`
- recorded_at: `2026-10-31T15:40:28.740514+00:00`
- entry: `pnpm test:anima:gate2_7`

## Roster

| ID | Name | Seed | Prompt | W×H | Trigger | Auto |
|----|------|------|--------|-----|---------|------|
| C01 | リゼ・ヘルエスタ | 27001 | gate26_adopted | 768×1024 | yes | PASS |
| C02 | 栞葉るり | 27002 | compiled | 768×1024 | yes | PASS |
| C03 | 夜見れな | 27003 | compiled | 768×1024 | yes | PASS |
| C04 | 星川サラ | 27004 | gate26_adopted | 768×1024 | yes | PASS |
| C05 | イレイナ | 27005 | gate26_adopted | 768×1024 | yes | PASS |
| C06 | 春日未来 | 27006 | compiled | 768×1024 | yes | PASS |
| C07 | 伊吹翼 | 27007 | compiled | 768×1024 | yes | PASS |
| C08 | 暁美ほむら | 27008 | gate26_adopted | 768×1024 | yes | PASS |
| C09 | 鹿目まどか | 27009 | compiled | 768×1024 | yes | PASS |
| C10 | ホタル（Firefly） | 27010 | gate26_adopted | 768×1024 | yes | PASS |
| C11 | オリジナル成人実写系 | 27011 | compiled | 768×1024 | yes | PASS |

## Human PASS checklist

- [ ] catastrophic failure なし
- [ ] ≥9/11 が GT 主要項目で識別可能
- [ ] contact sheet で別人取り違えが支配的でない
- [ ] C11 が極端な anime 化で破綻しない

## Next

- Human scores → `human_scores.csv`
- PASS 後 → A3 Pose Live P01–P05
