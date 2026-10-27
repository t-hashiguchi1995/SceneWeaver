# Moss-SFT Gate 2.5 — Target fixture smoke

**設計固定:** [`../moss-sft-gate2_5_target_fixtures.md`](../moss-sft-gate2_5_target_fixtures.md)

## 前提

- Gate 1 PASS（neutral MOSS smoke）
- Gate 2 PASS（UI → MOSS → Review → Adopt）

## 実行

```bash
pnpm test:moss:gate2_5
```

Comfy ≥ 0.42.1 + MOSS weights。11 Primary × 1 枚（固定 seed）。所要約 20–40 分。

## 最新ラン（2026-10-27）

| 項目 | 結果 |
|------|------|
| automatic | **PASS** 11/11 PNG+manifest + contact sheet |
| human | **PASS** 11/11 / 平均 7.91/8 |
| 所要 | ~27m43s |
| 詳細 | [`SUMMARY.md`](./SUMMARY.md) / [`REVIEW_GUIDE.md`](./REVIEW_GUIDE.md) |

## 必須成果物

| 成果物 | 説明 |
|--------|------|
| `C01`–`C11` PNG + `.manifest.json` | Primary 11 fixture |
| `contact_sheet.png` | 11 枚グリッド（顔均一化検出用） |
| `SUMMARY.md` | 合否・所見・混同チェック |
| `human_scores.csv` | 8点スコア（人手記入） |

## PASS

### Automatic（hard）

- 11/11 PNG decode ≥512
- 11/11 manifest（fixture_id / seed / model / workflow）
- `contact_sheet.png` + `SUMMARY.md` + `human_scores.csv`

### Human（soft — likeness は automatic に入れない）

- catastrophic failure なし
- 各 fixture が最低限識別可能 / 主要特徴が概ね追える
- 全員同顔が支配的でない
- **参考ライン:** 11中 9以上 human pass / 平均 5/8 以上 / C11 が極端に崩れない

## Contact sheet の見方

1. **顔の均一化** — 特に C01/C04/C05/C08/C09
2. **色の潰れ** — 髪・目・衣装の基調色
3. **シルエット** — イレイナ帽子 / ほむら↔まどか / ホタル SF / C11 実写
4. **style drift** — C11 アニメ寄り / アニメ側の過剰写実
