# Gate 2.5 — Target fixture smoke（詳細設計・固定）

**ステータス:** 設計固定 / **実行 PASS**（`pnpm test:moss:gate2_5`, 2026-10-27, auto 11/11 + human 11/11）→ 成果物は `docs/validation/moss-sft-gate2_5/`  
**前提:** Gate 1（neutral smoke）PASS。Gate 2（UI → MOSS → Review → Adopt）PASS。  
**目的:** 合意済みキャラ fixture で「指定対象の生成検証」を開始する。厳密 likeness は Character LoRA lane。

Gate 1 の `gate1_seed_12345.png` は **中立人物スモーク**であり、本ゲートの対象キャラ検証完了を意味しない。

---

## 1. PASS 条件（固定）

### Automated（hard）

```text
✅ decode（PNG）
✅ >=512（width かつ height）
✅ provenance（provider=comfyui, capability=LayoutGuidedRender,
   model_id=moss_image_sft, workflow_template_id=moss_sft_v1,
   workflow_hash, seed, external_job_ref）
✅ correct fixture_id（manifest とファイル名）
✅ correct seed / model / workflow
✅ artifact saved（個別 PNG + .manifest.json）
✅ contact_sheet.png（Primary 11 枚を一画面）
✅ SUMMARY.md + human_scores.csv
```

### Human（soft — likeness score は automatic PASS に入れない）

```text
✅ catastrophic failure なし（黒・全面ノイズ・人体崩壊なし）
✅ 各 fixture が最低限識別可能
✅ 主要外見特徴を概ね反映（髪・目・衣装の大枠）
✅ contact sheet 上で fixture 同士を明らかに取り違えない
   （全員同一顔は FAIL 候補 → Notes）
```

**参考ライン（暫定・#B fixture smoke 用途）**

- 11 件中 **9 件以上** human pass
- 平均スコア **5/8 以上**
- C11 が極端に崩れない（anime bias 支配的でない）

厳しすぎる閾値は #B の目的を超える。ここでは「使い物になる fixture smoke か」を見る。

**8点採点は記録・比較用。Gate 2.5 automatic PASS には likeness 合計を入れない。**

---

## 2. 共通 Fixed（全 fixture）

| 項目 | 値 |
|------|-----|
| capability | `LayoutGuidedRender` |
| model_id | `moss_image_sft` |
| workflow | `moss_sft_v1` |
| sampling | OpenMOSS: 50 / CFG 3 / euler / `sgm_uniform` / shift 5 / SLG 22 |
| resolution | 1024 × 1024 |
| pose | standing, front or slight ¾, hands visible where practical |
| camera | medium or medium-full, eye_level |
| background | plain studio / low-complexity neutral backdrop |
| expression | neutral or slight smile |
| content_rating | `general`（C11 も general／成人外見のオリジナル。R-18 行為描写は Gate 5） |
| seed | `fixture_id` ごとに固定（下表）。再実行で同 seed |

Prompt 方針: **キャラクター名だけにしない。** `name + 明示的外見 + 標準衣装` をすべて書き、Stock MOSS の固有名知識と SceneWeaver 機能を混同しない。

MOSS caption 組み立ては `moss_caption_v1`（Anima `safe` / artist トークンなし）。fixture は `identity_tags` / `character_traits` / `outfit_tags` / `background` 等にマップする。

---

## 3. Roster

| ID | Fixture | 区分 | Seed |
|----|---------|------|------|
| C01 | リゼ・ヘルエスタ | Primary | 20101 |
| C02 | 栞葉るり | Primary | 20102 |
| C03 | 夜見れな | Primary | 20103 |
| C04 | 星川サラ | Primary | 20104 |
| C05 | イレイナ | Primary | 20105 |
| C06 | 春日未来 | Primary | 20106 |
| C07 | 伊吹翼 | Primary | 20107 |
| C08 | 暁美ほむら | Primary | 20108 |
| C09 | 鹿目まどか | Primary | 20109 |
| C10 | ホタル | Primary | 20110 |
| C11 | 実写系の成人女性コスプレイヤー（オリジナル） | Primary / style coverage | 20111 |
| S01 | 倉持めると | Secondary | 20201 |
| S02 | フレン・E・ルスタリオ | Secondary | 20202 |

初回 Gate 2.5 実行は **Primary C01–C11（11枚）必須**。Secondary は任意（時間があれば）。Secondary は追加枠の倉持めると + フレン・E・ルスタリオのみ。**夜見れなは Primary（C03）。**

---

## 4. Human scorecard（8点）

各画像について人手で記録（比較・回帰用。automatic gate には使わない）:

```text
[0/1] valid image
[0/1] correct broad hair characteristics
[0/1] correct eye/color impression
[0/1] outfit broadly follows specification
[0/1] requested pose/framing
[0/1] no major anatomy collapse
[0/2] recognizable identity / overall impression
       0 = 別人級, 1 = 雰囲気が追える, 2 = 特徴がはっきり追える
Notes:
- identity drift
- outfit leakage
- unexpected attributes
- prompt adherence
```

合計 **0–8**。

---

## 5. Fixture 詳細（実行前に固定）

実装時は下記要素を `identity_tags` / `character_traits` / `outfit_tags` / `expression` / `pose` / `camera` / `background` へ分解してよい。自然文1本にまとめてもよいが、**要素を欠かさないこと。**

---

### C01 リゼ・ヘルエスタ — seed `20101`

```text
Prompt identity
- character name: Lize Helesta (リゼ・ヘルエスタ)
- hair color / length / style: light-blue / icy aqua; long; soft waves with side locks
- eye color: clear blue
- signature accessories: small crown / tiara
- overall impression: elegant cool-cute royalty / VTuber idol

Default outfit
- frilly black-and-blue gothic-lolita-inspired dress, white blouse accents,
  ribbons, stockings; crown accessory on head

Pose
- standing; front or slight 3/4; hands visible where practical

Camera
- medium / medium-full; eye level

Background
- plain studio; low-complexity neutral backdrop

Expression
- neutral / slight smile

Fixed
- 1024x1024; seed 20101; OpenMOSS sampling preset (§2);
  LayoutGuidedRender; moss_image_sft; moss_sft_v1

Human evaluation
[0/1] valid image
[0/1] correct broad hair characteristics
[0/1] correct eye/color impression
[0/1] outfit broadly follows specification
[0/1] requested pose/framing
[0/1] no major anatomy collapse
[0/2] recognizable identity / overall impression
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C02 栞葉るり — seed `20102`

```text
Prompt identity
- character name: Shioriha Ruri (栞葉るり)
- hair color / length / style: soft lavender / light purple; long; gentle straight-to-soft-wave
- eye color: calm purple / violet
- signature accessories: modest hair ribbon or simple clip (subtle)
- overall impression: quiet scholarly beauty; reserved; gentle

Default outfit
- neat white blouse + soft pastel cardigan or sweater; long muted skirt;
  low-contrast pastel palette

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20102

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C03 夜見れな — seed `20103` （Primary）

```text
Prompt identity
- character name: Yorumi Rena (夜見れな)
- hair color / length / style: black to deep purple-black; long; distinctive fringe / bangs
- eye color: sharp red / crimson
- signature accessories: choker or dark ribbon; gothic lace accents
- overall impression: dark-cute; high-contrast night idol

Default outfit
- black gothic dress with red accents; lace details; choker or ribbon at neck

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20103

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C04 星川サラ — seed `20104`

```text
Prompt identity
- character name: Hoshikawa Sara (星川サラ)
- hair color / length / style: bright blonde / light golden; long; lively volume
- eye color: bright blue or aqua
- signature accessories: subtle star motif OK; cute idol hair accessory
- overall impression: cheerful sunny pop idol; high energy

Default outfit
- bright idol-style costume (white/pastel with blue or gold accents); cute stage accessories

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20104

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C05 イレイナ — seed `20105`

```text
Prompt identity
- character name: Elaina (イレイナ)
- hair color / length / style: ash-blonde / silver-blonde; long; often under wide-brim witch hat
- eye color: calm blue-gray
- signature accessories: pointed/wide-brim witch hat; travel satchel optional
- overall impression: composed wandering witch; slightly aloof traveler

Default outfit
- dark witch robe or travel cloak over blouse; pointed hat; soft travel mage silhouette

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20105

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C06 春日未来 — seed `20106`

```text
Prompt identity
- character name: Kasuga Mirai (春日未来)
- hair color / length / style: pink; long; twin-tails or half-up idol styling
- eye color: bright pink / magenta
- signature accessories: large hair ribbons / idol bows
- overall impression: bright earnest classic idol

Default outfit
- colorful pink-forward idol stage costume; frills; ribbon accents

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20106

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C07 伊吹翼 — seed `20107`

```text
Prompt identity
- character name: Ibuki Tsubasa (伊吹翼)
- hair color / length / style: blonde / light; short-to-medium; lively volume (tomboyish cut)
- eye color: warm orange / amber (or consistent warm bright tone)
- signature accessories: sporty hairband or small stage accent OK
- overall impression: energetic confident athletic idol

Default outfit
- sporty-idol or stage outfit with warm accent colors; shorts or active skirt

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20107

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C08 暁美ほむら — seed `20108`

```text
Prompt identity
- character name: Akemi Homura (暁美ほむら)
- hair color / length / style: black; long; straight
- eye color: deep purple
- signature accessories: hair ribbon / bow; cool restrained silhouette
- overall impression: stoic dark magical-girl; serious; restrained

Default outfit
- dark magical-girl uniform (black / deep purple with white shirt accents); skirt; ribbon

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20108

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C09 鹿目まどか — seed `20109`

```text
Prompt identity
- character name: Kaname Madoka (鹿目まどか)
- hair color / length / style: pink; twin tails
- eye color: pink / rose
- signature accessories: soft hair ribbons; gentle contrast to Homura
- overall impression: warm hopeful kind magical-girl

Default outfit
- pink-and-white magical-girl outfit with ribbons; short skirt; soft frills

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20109

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C10 ホタル — seed `20110`

```text
Prompt identity
- character name: Hotaru (ホタル) — SceneWeaver original SF-leaning android/SF girl
  (not a trademarked franchise clone; describe as original “Hotaru”)
- hair color / length / style: silver or pale blue; short-to-medium; clean cool cut
- eye color: luminous cyan / tech-glow impression
- signature accessories: subtle HUD / tech accents OK; clean SF silhouette
- overall impression: cool synthetic-beauty sci-fi

Default outfit
- sleek futuristic bodysuit or tech jacket + pants; minimal logos; soft neon trim

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20110

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### C11 実写系の成人女性コスプレイヤー（オリジナル） — seed `20111`

**重要:** 実在の特定コスプレイヤー・写真家・配信者を模倣しない。**成人と明示したオリジナル人物。** Try-On / Gate 5 成人検証に安全に再利用できる fixture。

```text
Prompt identity
- character name: (fictional) original adult Japanese woman cosplayer — mid-20s adult
- hair color / length / style: dark brown; shoulder-length; natural soft waves
- eye color: dark brown
- signature accessories: none trademarked; soft studio beauty look; no real-person likeness
- overall impression: approachable adult cosplayer between shoots;
  photoreal / live-action photography (not anime cel)

Default outfit
- simple modern casual: white blouse + dark skirt or jeans;
  convention-badge-free; no real-brand logos

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20111; content_rating=general（行為描写なし）

Human evaluation
- same 8-point scorecard as C01
  （style: photoreal vs anime の差も Notes に記録）
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
       / accidental celebrity likeness (must be 0)
```

**Style note:** photoreal for Try-On and later adult pipeline reuse. **No explicit sexual content in Gate 2.5.**

---

### S01 倉持めると — seed `20201` （Secondary）

```text
Prompt identity
- character name: Kuramochi Meruto (倉持めると)
- hair color / length / style: soft pink / light pink; long; twin-tails or high side-tied cute style
- eye color: pink / light magenta
- signature accessories: bunny / cute animal-ear motif optional if public design uses it;
  playful hair ornaments
- overall impression: energetic cute playful VTuber

Default outfit
- cute layered casual / signature pastel stage-casual look:
  frilly top, shorts or short skirt, soft stockings; record exact fragment in manifest

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20201

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

### S02 フレン・E・ルスタリオ — seed `20202` （Secondary）

```text
Prompt identity
- character name: Furen E Lustario (フレン・E・ルスタリオ)
- hair color / length / style: blonde / golden; long; voluminous stylish waves
- eye color: sharp green or teal (consistent cool knightly gaze)
- signature accessories: knightly headpiece / ear accents per public design; confident posture
- overall impression: gallant stylish knightly VTuber; confident

Default outfit
- stylized knight / stage costume (armor accents + elegant coat or tunic);
  record exact fragment in manifest `outfit_tags`

Pose / Camera / Background / Expression / Fixed
- same as §2; seed 20202

Human evaluation
- same 8-point scorecard as C01
Notes: identity drift / outfit leakage / unexpected attributes / prompt adherence
```

---

## 6. 成果物レイアウト

```text
docs/validation/moss-sft-gate2_5/
  README.md                 # 実行手順・PASS定義へのリンク
  contact_sheet.png         # Primary 11 枚グリッド（必須）
  SUMMARY.md                # 合否・所見・混同チェック
  human_scores.csv          # fixture_id, scores..., notes
  C01_lize.png
  C01_lize.manifest.json
  ...
  C11_liveaction_adult.png
  C11_liveaction_adult.manifest.json
  (optional) S01_*.png / S02_*.png
```

### Manifest 最低フィールド

```json
{
  "gate": "moss-sft-gate2_5",
  "fixture_id": "C01",
  "fixture_name": "リゼ・ヘルエスタ",
  "status": "generated",
  "capability": "LayoutGuidedRender",
  "model_id": "moss_image_sft",
  "workflow_template_id": "moss_sft_v1",
  "workflow_hash": "...",
  "seed": 20101,
  "prompt_hash": "...",
  "width": 1024,
  "height": 1024,
  "mime": "image/png",
  "sha256": "...",
  "external_job_ref": "...",
  "comfy_version": "...",
  "image_file": "C01_lize.png",
  "identity_summary": "...",
  "outfit_tags": "...",
  "human_score_total": null
}
```

---

## 7. 実行順との関係

```text
Gate 1                    ✅ PASS
Gate 1 e2e required       ✅ PASS
↓
Gate 2
UI → MOSS → Review → Adopt
  API vertical            ✅ PASS（pnpm test:moss:gate2:api）
  live required           ✅ PASS（pnpm test:moss:gate2:e2e:live:required）
↓
Gate 2.5
11 Primary fixtures × 1 image
+ manifest + contact_sheet + SUMMARY
                          ✅ PASS（pnpm test:moss:gate2_5）
↓
Gate 2.6 — Anima Prompt Refine
  tag列 Base → 編集 → 再生成 → 採用保存
  設計: anima-gate2_6_prompt_refine.md / anima-tag-compiler.md
↓
Gate 3 — Outfit Isolation A→B→C→A
  設計: moss-sft-gate3_outfit_isolation.md
  Primary: C01 / C06 / C07 / C10（same seed） ✅ PASS
↓
Gate 4
multi-character × outfit
↓
Gate 5
adult fixture only（adult rating profile）
↓
Character LoRA / Pose ecosystem
```

## 8. 意図的にやらないこと

- Gate 2.5 で Character LoRA を必須にしない
- Gate 2.5 automatic PASS に likeness ≥ N を入れない
- C11 で実在人物の再現を求めない
- R-18 行為描写を本ゲートに混ぜない
- 夜見れなを Secondary に落とさない（Primary C03 固定）
