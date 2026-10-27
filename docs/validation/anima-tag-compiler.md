# Anima Tag Compiler — Character Semantic Spec 分岐

## 方針

| モデル | Prompt 形式 |
|--------|-------------|
| **Anima** | Danbooru / tag 列（自然文に寄せない） |
| **MOSS** | 自然文 caption |

同じ Character Semantic Spec を、それぞれのコンパイラが適した形へ変換する。  
→ **Production Fair** 比較（同一文字列を両モデルへ投げない）。

```text
Character Semantic Spec
        │
        ├── Anima Compiler  → tag sequence
        └── MOSS Compiler   → natural-language caption
```

---

## Anima 標準スロット順

```text
{quality_tags},
{rating_tags},
{subject_tags},
{character_name},
{franchise},
{artist_style_tags},
{identity_tags},
{body_tags},
{outfit_tags},
{expression_tags},
{pose_tags},
{camera_tags},
{background_tags},
{lighting_tags}
```

### リゼ（一般）例

```text
year 2025, newest, masterpiece, best quality, score_9, score_8, highres,
safe,
1girl,
lize helesta, nijisanji,
@fuzichoco, @rella,
long pale lavender hair, blue eyes, crown hair accessory,
royal blue and white outfit,
calm expression, standing,
medium full shot, eye level,
simple studio background,
soft lighting
```

### 標準キャラで入れないもの

- `nsfw` / `explicit` / `large breasts` 等の性的指定
- 成人向けは **成人と明示したオリジナル fixture** + adult rating profile のみ

| rating_profile | rating スロット |
|----------------|-----------------|
| general（標準） | `safe` |
| adult（成人 fixture） | `sensitive`（必要なら別途 nsfw/explicit を adult 専用プロファイルで） |

---

## 実装

- `src/creator_studio/application/prompt/anima_tags.py` — `compile_anima_positive`
- `PromptRenderer.render_anima` — 上記を使用
- `PromptRenderer.render_moss` — 自然文のまま（Anima artist/quality 禁止）
- VisualIdentity: `character_name`, `franchise`, `body_tags`, `saved_anima_positive`

---

## Prompt Editor

```text
Model / Compiler label
Base Prompt   … コンパイラ出力（読取専用）
Final Prompt  … ユーザー編集 → 生成に使用
[ベースへ戻す] [差分を見る] [キャラ用Promptとして保存] [生成]
```

「キャラ用Promptとして保存」→ `visual_identity.saved_anima_positive`（Gate 2.6 採用）。

---

## Gate 2.6

詳細は [`anima-gate2_6_prompt_refine.md`](./anima-gate2_6_prompt_refine.md)。
