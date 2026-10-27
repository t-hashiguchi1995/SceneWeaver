# Anima Gate 2.6 — Prompt Quality Baseline SUMMARY

## Run metadata

- date: `2026-10-27T14:30:00Z`（ANIMADEX GT 是正後の再 run）
- model_id: `anima_base` / workflow: `anima_base_v1` / capability: `BaseRender`
- comfy_version: `0.42.5`
- seed policy: C01=26001 … C10=26010（Base == Edited）
- evaluation: [`animadex-character-evaluation.md`](../animadex-character-evaluation.md) + [`ground_truth.md`](./ground_truth.md)

## Flow

```text
Semantic Spec (ANIMADEX Trigger/Tags)
  → Anima Base compile → Base gen
  → Prompt edit → same seed → Base|Edited compare → adopt Final Prompt
```

## Automatic gate

- ✅ 5/5 Base + 5/5 Edited（同 seed）
- ✅ contact_sheet_base_vs_edited.png（2列）
- ✅ adopted_prompts/（5× `.anima.txt` + provenance）
- ✅ prompt_hash / model / workflow / seed

## Human scores（GT 照合）

| ID | Name | Seed | Base | Edited | Δ | Verdict |
|----|------|------|------|--------|---|---------|
| C01 | リゼ・ヘルエスタ | 26001 | 15/20 | 20/20 | **+5** | improved |
| C04 | 星川サラ | 26004 | 11/20 | 20/20 | **+9** | improved |
| C05 | イレイナ | 26005 | 19/20 | 20/20 | **+1** | improved |
| C08 | 暁美ほむら | 26008 | 16/20 | 20/20 | **+4** | improved |
| C10 | Firefly | 26010 | 15/20 | 19/20 | **+4** | improved |

Axis detail: `human_scores.csv`

### Human PASS

- ✅ 5/5 Δ > 0（≥4/5 要求を超過）
- ✅ 明確な悪化なし
- ✅ 編集意図が GT 項目に追える

## 初回 run からの教訓

初回は雰囲気採点で human PASS を宣言したが、ANIMADEX GT 再採点で:

- C10 が **別人定義**（original android）だった → 旧 18/20 は無効
- C01/C04 の目色が GT と不一致
- C08 Edited が MG から外れて悪化

是正後の再 run で上記を解消。詳細: [`RESCORE_ANIMADEX.md`](./RESCORE_ANIMADEX.md)

## Status

- automatic: `PASS`
- human: `PASS`（ANIMADEX GT）

## Next

- Pose Gallery Live **P01–P05**（[`pose-gallery-live-validation.md`](../pose-gallery-live-validation.md)）
- その後 Gate 3 A→B→C→A（adopted prompts 使用）
- リモート push 後に Pose 実装差分レビュー可
