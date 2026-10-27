# Gate 2.6 — Anima Prompt Quality Baseline（再現改善ゲート）

**ステータス:** automatic PASS / human PASS（2026-10-27・ANIMADEX GT 再採点後）  
**成果物:** [`anima-gate2_6/`](./anima-gate2_6/)  
**評価基準:** [`animadex-character-evaluation.md`](./animadex-character-evaluation.md)  
**主目的:** Prompt 編集 UI の有無ではなく、**編集によって正しいキャラ GT へ近づいたか**を確認する。

前提: Gate 2 / 2.5 PASS。Anima = tag 列、MOSS = 自然文（分離維持）。  
Pose Gallery の real validation は **本ゲート PASS の後**（キャラ崩れノイズを避けるため）。

---

## 1. 固定フロー（各キャラ同一）

```text
1. Semantic Spec
   ↓
2. Anima Base Prompt 自動コンパイル
   ↓
3. Base 画像生成（fixed seed）
   ↓
4. 人手で Prompt 編集（目色・髪・franchise・アクセ等を強化）
   ↓
5. 同じ seed で再生成
   ↓
6. Base vs Edited を横並び比較
   ↓
7. 改善した Prompt を Character Prompt（saved_anima_positive）として保存
```

---

## 2. Primary（5人）

| ID | Character | franchise | seed |
|----|-----------|-----------|------|
| C01 | リゼ・ヘルエスタ | nijisanji | 26001 |
| C04 | 星川サラ | nijisanji | 26004 |
| C05 | イレイナ | majo no tabitabi | 26005 |
| C08 | 暁美ほむら | mahou shoujo madoka magica | 26008 |
| C10 | ホタル | original | 26010 |

Semantic: `tests/live/anima_character_semantics.py`  
Edited 強化案: `tests/live/anima_gate2_6_edits.py`

---

## 3. 採点（Base / Edited 別々 → Δ）

各画像について 0–4 × 5 軸 = **0–20**:

| 軸 | 見るもの |
|----|----------|
| Identity | 顔立ち・髪・全体の別人度 |
| Outfit | 標準衣装の大枠 |
| Color | 髪色・目色・衣装基調色 |
| Accessories | 王冠・帽子・リボン等 |
| Overall likeness | 総合印象 |

重要なのは絶対点より **Δ = Edited Total − Base Total**。

例:

```text
C01 Base 12/20 → Edited 20/20 → Δ = +8
```

---

## 4. PASS 条件

### Automatic（hard）

```text
✅ 5/5 Base 生成成功（decode ≥512, provenance）
✅ 5/5 Edited 生成成功（same seed）
✅ 5/5 Base→Edited 比較可能（両 PNG + manifest）
✅ Final（Edited）Prompt が adopted として保存
✅ prompt_hash / model_id / workflow / seed が manifest に残る
✅ contact_sheet_base_vs_edited.png 生成
✅ SUMMARY.md + human_scores.csv
```

### Human（soft — 改善ゲート）

```text
✅ 5人中少なくとも 4人でスコア改善（Δ > 0）
✅ 明確な悪化例がない（Δ が大きく負でない）
✅ 編集意図（目色・franchise・アクセ等）が概ね追える
```

「5/5 生成成功」だけでは PASS にしない。

---

## 5. 成果物

```text
docs/validation/anima-gate2_6/
  C01/
    base.png
    edited.png
    base.manifest.json
    edited.manifest.json
    prompt_diff.txt
  C04/ C05/ C08/ C10/
  adopted_prompts/
    C01_lize.anima.txt
    …
  contact_sheet_base_vs_edited.png   # 2列: Base | Edited
  human_scores.csv
  SUMMARY.md
  REVIEW_GUIDE.md
```

contact sheet:

```text
C01 Base | C01 Edited
C04 Base | C04 Edited
…
```

---

## 6. 安全方針

- 標準キャラ Base/Edited は **general / safe** のみ
- `nsfw` / `explicit` / `large breasts` を標準検証に入れない
- 成人は C11 系 + adult rating profile

---

## 7. 実行順

```text
Gate 2.5  ✅ MOSS fixture smoke
Gate 2.6  ▶ Anima Prompt Quality Baseline（本ゲート）
           ↓ PASS 後、保存 Prompt を衣装検証へ流用可能
Gate 3    ✅ Outfit isolation（MOSS）／将来 Anima でも同構造
Pose Gallery → Apply → Generate → provenance
           （Gate 2.6 の後で real validation）
```

---

## 8. 実行

```bash
pnpm test:moss:gate2_6
# 実体は Anima BaseRender（SCENEWEAVER_MOSS_LIVE と同系統の live flag）
pnpm test:anima:gate2_6
```
