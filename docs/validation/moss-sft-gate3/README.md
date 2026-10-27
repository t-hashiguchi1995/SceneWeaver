# Moss-SFT Gate 3 — Single Character Outfit Isolation A→B→C→A

**設計固定:** [`../moss-sft-gate3_outfit_isolation.md`](../moss-sft-gate3_outfit_isolation.md)

## 主目的

衣装の美しさではなく **状態分離**。同一キャラで `A1 → B → C → A2` と切り替え、特に **A-return に B/C が漏れない**こと。

## 実行

```bash
pnpm test:moss:gate3
```

Primary: C01 / C06 / C07 / C10 × 4 turns（same seed）。所要約 30–50 分。

## 最新ラン（2026-10-27）

| 項目 | 結果 |
|------|------|
| automatic | **PASS** 16/16 + prompt isolation + wrong-owner reject |
| human | **PASS** 4/4（全員 A2 Leakage=2） |
| 所要 | ~39m46s |
| 詳細 | [`SUMMARY.md`](./SUMMARY.md) / [`REVIEW_GUIDE.md`](./REVIEW_GUIDE.md) |

## Automatic PASS（要約）

- 4/4 PNG ≥512、same character_id、expected outfit_profile_id
- A1 ≠ B ≠ C、A1 profile == A2 profile
- wrong-owner OutfitProfile reject
- A2 prompt に A 排他語あり / B|C marker なし

## Human PASS

- Identity / Outfit / Leakage（各0–2）
- **A2 Leakage = 2 必須**

## 成果物

各 `C##/sequence.png`（横一列 A1→B→C→A2）+ `contact_sheet.png` + `SUMMARY.md` + `human_scores.csv`
