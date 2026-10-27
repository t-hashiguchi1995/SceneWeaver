# Anima キャラ評価基準 — ANIMADEX 優先

**ステータス:** 正式採用  
**参照:** [ANIMADEX Characters](https://animadex.net/?mode=characters)

---

## 優先順位

```text
1. ANIMADEX
   - trigger
   - character tags
   - visual reference
   - Anima LoRA availability（参考。fuzzy match 注意）

2. 公式プロフィール / 公式立ち絵
   - 正式な髪色・目色・標準衣装・固有アクセサリ

3. 必要に応じて Danbooru 系タグ
   - Anima 向けタグ表現の確認
```

**ANIMADEX だけを絶対正解にしない。** LoRA 紐付けは名前ベースの fuzzy matching で誤マッチしうるため、公式ビジュアルと突合する。

---

## Character Ground Truth チェックリスト

```text
Character Ground Truth
├─ Trigger
├─ Hair
├─ Eyes
├─ Hairstyle
├─ Signature accessory
├─ Default outfit
├─ Main colors
└─ Silhouette

      ↓ compare

Generated Image
```

採点は「似ている気がする」ではなく、上記項目の **照合** で行う。  
Gate 2.5 で起きた「別人なのに高得点」を防ぐ。

---

## `anima_tags.py` との対応

| ANIMADEX | SceneWeaver |
|----------|-------------|
| Trigger（character + franchise） | `character_name` + `franchise` |
| character tags | `identity_tags` / outfit / accessory slots |
| visual reference | 人手レビュー用（生成対象ではない） |
| Anima LoRA | 将来の Character LoRA ゲート |

---

## Gate 適用

| Gate | 使い方 |
|------|--------|
| 2.6 Prompt Quality | Base/Edited を GT 照合で Δ 採点（[`anima-gate2_6/`](./anima-gate2_6/)） |
| 3 Outfit isolation | 採用 Prompt は GT 整合済みのものを使う |
| Pose Live | キャラ固定に GT 準拠 Prompt を使い、Pose 混線だけを見る |

Primary 5 の GT 詳細: [`anima-gate2_6/ground_truth.md`](./anima-gate2_6/ground_truth.md)
