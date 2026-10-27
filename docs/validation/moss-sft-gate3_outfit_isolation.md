# Gate 3 — Single Character Outfit Isolation A→B→C→A

**ステータス:** 設計固定 / **実行 PASS**（`pnpm test:moss:gate3`, 2026-10-27, auto 16/16 + human 4/4 A2 Leakage=2）→ 成果物は `docs/validation/moss-sft-gate3/`  
**主目的:** 衣装の見た目品質ではなく **状態分離**（同一キャラで A→B→C→A 切替時に衣装属性が混線しないこと）

厳密 likeness / 衣装美観は Character LoRA lane および別ゲート。ここでは **入力状態・Prompt snapshot・画像** の3層で混線なしを確認する。

---

## 1. シーケンス

```text
A1 → B → C → A2(return)
```

| Turn | Character | Outfit | 主な確認 |
|------|-----------|--------|----------|
| 1 A1 | 同一 | A | baseline |
| 2 B | 同一 | B | A の特徴が残らない |
| 3 C | 同一 | C | A/B の特徴が残らない |
| 4 A2 | 同一 | A | B/C が残らず最初の A へ戻る |

**最重要判定対象 = A2（A-return）。**

---

## 2. Primary fixtures（初回は4人）

| Fixture | 理由 | same seed |
|---------|------|-----------|
| C01 リゼ・ヘルエスタ | 衣装・装飾の識別がしやすい | 30101 |
| C06 春日未来 | アイドル衣装の切替 | 30106 |
| C07 伊吹翼 | 活発系、衣装とポーズ混同を発見しやすい | 30107 |
| C10 ホタル | SF 系衣装の残留を発見しやすい | 30110 |

11キャラ全部はまだ不要。余裕があれば Robustness で second fixed seed。

---

## 3. 衣装 A/B/C（明確に離す）

色・形・カテゴリを全部変える。微妙な色違い禁止。

### C01 リゼ・ヘルエスタ

```text
A: canonical blue/white royal-style outfit（王冠・フリル青白）
B: casual black hoodie + denim skirt
C: elegant red evening dress
A-return: = A
```

### C06 春日未来

```text
A: canonical idol stage costume（ピンク系ステージ）
B: casual oversized sweatshirt + shorts
C: formal dark business suit
A-return: = A
```

### C07 伊吹翼

```text
A: canonical sporty-idol stage outfit（暖色スポーティ）
B: school sailor uniform（紺白セーラー）
C: winter coat + scarf + boots（冬コート）
A-return: = A
```

### C10 ホタル

```text
A: canonical SF tech bodysuit / neon trim
B: soft pastel pajama set（部屋着）
C: formal black tuxedo jacket + trousers
A-return: = A
```

各 outfit は **OutfitProfile（character 所有）** として作成し、turn ごとに `outfit_profile_id` を切り替える。  
切替時は `outfit_tags` を当該 profile の `garment_description` で明示上書きし、**前 turn の tags が render_spec に残留しない**こと。

**Prompt draft プロトコル（必須）:**  
`update_shot`（outfit 変更）のあと、render 前に `prompt_draft.rebuild(confirm=true)` する。  
`ensure_for_shot` だけでは同一 template の既存 draft を返し、**古い outfit の positive が残る**（状態混線の温床）。Gate 3 は rebuild 後の snapshot で非漏洩を証明する。

排他マーカー語（B-only / C-only）を garment に含め、A2 の prompt snapshot から検出する。

---

## 4. Fixed（共通）

| 項目 | 値 |
|------|-----|
| capability | `LayoutGuidedRender` |
| model_id | `moss_image_sft` |
| workflow | `moss_sft_v1` |
| sampling | OpenMOSS 50 / CFG 3 / euler / sgm_uniform / shift 5 / SLG 22 |
| resolution | 1024 × 1024 |
| pose / camera / bg / expression | Gate 2.5 §2 と同じ studio 固定 |
| seed | **同一キャラの A1/B/C/A2 は same seed**（構図差を抑え衣装差を見る） |
| content_rating | `general` |

Identity（髪・目・名前）は turn 間で固定。変わるのは outfit のみ。

---

## 5. Automatic PASS（hard）

見た目の良し悪しは入れない。状態と provenance:

```text
✅ 4/4 generation successful（各 Primary）
✅ 4/4 decoded PNG
✅ 4/4 >= 512
✅ same character_id across turns
✅ expected outfit_profile_id each turn
✅ A1 != B != C（profile id が互いに異なる）
✅ A1 outfit_profile_id == A2 outfit_profile_id
✅ prompt_hash recorded
✅ GenerationAttempt recorded
✅ model_id / workflow_hash / seed recorded
✅ no wrong-owner OutfitProfile（他キャラ profile を付けたら reject）
✅ A2 prompt snapshot contains A exclusive terms
✅ A2 prompt snapshot does not contain B/C-only outfit terms
```

最後の2つが特に重要。画像の前に **入力状態・Prompt 段階で B/C が A2 に残っていない**ことを証明する。

---

## 6. Human PASS（soft）

各生成を3軸（各 0–2）:

| 評価 | 0 | 1 | 2 |
|------|---|---|---|
| Identity | 大崩れ | 一部維持 | 良好 |
| Outfit | 指定不一致 | 部分一致 | 明確に一致 |
| Leakage | 強い混入 | 軽微 | なし |

- A1/B/C/A2 × 6点 = **1キャラ 24点**
- **A2 の Leakage = 2 を必須**（B/C 特徴が A2 に明確に残ったら他が良くても FAIL）
- 平均点は参考。本質は A-return の非漏洩

---

## 7. 成果物

```text
docs/validation/moss-sft-gate3/
  C01/
    A1.png  B.png  C.png  A2_return.png
    *.manifest.json
    sequence.png          # [A1]→[B]→[C]→[A2] 横一列
  C06/  C07/  C10/
  contact_sheet.png       # 全 Primary の sequence を縦に積む等
  human_scores.csv
  SUMMARY.md
  REVIEW_GUIDE.md
```

---

## 8. Seed 方針（2段階）

```text
Primary:
  A1/B/C/A2 = same seed（本試験）

Robustness（任意・後追い）:
  A/B/C/A = second fixed seed
  → seed が偶然良かっただけ、を切り分け
```

---

## 9. 実行順との関係

```text
Gate 1  ✅ 実MOSSが動く
Gate 2  ✅ サービスとして生成→採用できる
Gate 2.5 ✅ 対象キャラ群が fixture として成立
Gate 3  ▶ 同一キャラで衣装状態を安全に切替  ← NEXT
Gate 4    複数キャラ間でも状態を分離
Gate 5    Adult pipeline
Character LoRA / Pose
```

---

## 10. 意図的にやらないこと

- 11キャラ全部を初回必須にしない
- Automatic PASS に likeness / 衣装美観スコアを入れない
- A2 Leakage 必須を平均点で緩和しない
- wrong-owner OutfitProfile の黙認
