# MOSS-SFT Gate 3 — SUMMARY

## Run metadata

- date: `2026-10-27T12:39:00Z`（JST 21:39 完了）
- commit: `a9928dd`（Gate2/2.5/3 成果物は作業ツリー未 push）
- gate: **Single Character Outfit Isolation A→B→C→A**
- model_id: `moss_image_sft`
- workflow_template_id: `moss_sft_v1`
- capability: `LayoutGuidedRender`
- comfy_version: `0.42.5`
- resolution: `1024x1024`
- seed policy: same seed per character（C01=30101, C06=30106, C07=30107, C10=30110）
- sampling: OpenMOSS 50 / CFG 3 / euler / sgm_uniform / shift 5 / SLG 22
- runtime: ~39m46s（`pnpm test:moss:gate3`）
- protocol: `update_shot(outfit)` → `prompt_draft.rebuild(confirm=true)` → `render`

## Automatic gate

| 項目 | 結果 |
|------|------|
| 4 chars × 4 turns PNG ≥512 | **16/16** |
| same character_id per sequence | ✅ |
| A1 ≠ B ≠ C profile ids | ✅ |
| A1 profile == A2 profile | ✅ |
| model / workflow_hash / seed / prompt_hash | ✅ |
| wrong-owner OutfitProfile reject | ✅ |
| A2 prompt has A exclusive / no B\|C markers | ✅ |
| sequence.png ×4 + contact_sheet.png | ✅ |

**automatic: PASS**

## Human gate（sequence / contact sheet）

採点軸: Identity / Outfit / Leakage（各0–2）。**A2 Leakage=2 必須。**

| Fixture | A1 | B | C | A2 | Char total | A2 Leakage | Human |
|---------|----|---|---|-----|------------|------------|-------|
| C01 リゼ | 6 | 6 | 6 | 6 | 24/24 | **2** | PASS |
| C06 未来 | 6 | 6 | 6 | 6 | 24/24 | **2** | PASS |
| C07 翼 | 6 | 6 | 6 | 6 | 24/24 | **2** | PASS |
| C10 ホタル | 6 | 6 | 6 | 6 | 24/24 | **2** | PASS |

### sequence 所見

- **C01:** A 青白ロイヤル ↔ B 黒フーディ+デニム ↔ C 赤イブニング ↔ A2 復帰。A2 に B/C なし。B のみ1枚内マルチパネル気味（構図 quirk、漏洩ではない）。
- **C06:** アイドル ↔ スウェット ↔ スーツ ↔ アイドル復帰。カテゴリ差が大きく残留なし。
- **C07:** スポーティ ↔ セーラー ↔ 冬コート ↔ 復帰。ポーズが A1/A2 で一致（same seed 効果）。
- **C10:** SFスーツ ↔ パジャマ ↔ タキシード ↔ SF復帰。シルエット差が大きく漏洩判定しやすい。全滅クリーン。

### Aggregate

- auto passed turns: **16/16**
- human passed characters: **4/4**（全員 A2 Leakage=2）
- average score: **6/6 per turn**（参考）
- face/identity across turns: 良好（髪色帯は維持）

## Common failure patterns

- [ ] A attributes persist into B — なし
- [ ] B/C attributes persist into A2 — **なし（必須クリア）**
- [ ] identity drift across turns — 軽微〜なし
- [ ] outfit category collapse — なし
- [x] composition quirk — C01-B のマルチパネル（Leakage FAIL ではない）

## Status

- automatic: **PASS**
- human: **PASS**（A2 Leakage=2 × 4/4）

## 設計上の注意（実装で確認）

Outfit 切替後に `ensure_for_shot` だけでは **古い draft positive が残る**。Gate 3 は `rebuild(confirm=true)` を必須プロトコルとした。UI/製品側でも outfit_profile 変更時に draft rebuild が必要。

## Next

- Gate 4: multi-character × outfit（キャラ間分離）
- Gate 5: adult baseline（C11 系）
- Robustness（任意）: second fixed seed で A→B→C→A 再確認
