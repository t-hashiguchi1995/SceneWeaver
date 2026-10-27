# Pose UI — Gallery-first（正式デザイン方針）

**ステータス:** 採用  
**参照体験:** [ai-pose-gallery.pages.dev](https://ai-pose-gallery.pages.dev/) 同系統（サムネ一覧・タグ・お気に入り・探索中心）  
**分離原則:** Pose は Character / Outfit から独立。Gallery の見本人物は **生成対象ではない**。

```text
Character → Outfit → Pose Gallery（ポーズだけ適用）→ Model → Generate
```

---

## 廃止する UI

Shot Studio の最終形では次を出さない:

```text
Use Pose
Pose Reference   asset://...
Control Strength （単独のURI入力行）
```

代わりに:

```text
Pose
[ Choose Pose ]

選択中:
┌─────────────┐
│ thumbnail   │
│ One hand hip│
│ strength 1.0│
│ [Change]    │
└─────────────┘
```

`[Change]` / `[Choose Pose]` → Pose Gallery。

---

## Gallery レイアウト

```text
Pose Gallery · Search · ♡ Favorites
[All] [Standing] [Sitting] [Action] [Hands] [Cute] [Dynamic]
カードグリッド（大きなサムネ + ラベル + ♡ + Apply）
Load more / Random
```

カードクリック → 右 Drawer:

- 大プレビュー
- タイトル / タグ
- Pose Prompt（表示・コピー）
- Strength スライダー
- ♡ Favorite
- Apply to current Shot
- （将来）左右反転

---

## カードが持つデータ（人物固有情報なし）

| フィールド | 意味 |
|------------|------|
| id | 安定 ID |
| title | 表示名 |
| categories / tags | Standing / Sitting / … |
| thumbUrl | Gallery 用サムネ |
| posePrompt | テキスト指示（Prompt Pose） |
| referenceUri | 画像参照（LLLite / OpenPose 用）。任意 |
| backendKinds | `prompt` / `reference_image` / `openpose` / `pose_lora`（将来） |
| defaultStrength | 既定 strength |

見本画像に写っている人物の identity / franchise は **カードに持たせない**。

---

## 将来の統合（同じ Gallery）

```text
Gallery
  ├─ Prompt Pose
  ├─ Reference Image Pose
  ├─ OpenPose Skeleton
  └─ Pose LoRA
```

ユーザーからは全部「Pose」。内部方式だけ違う。Anima LLLite / OpenPose / Pose LoRA を別画面にしない。

---

## Shot への適用結果

Apply 時に Shot / `render_spec.pose` へ:

| フィールド | 意味 |
|------------|------|
| `pose_id` | Gallery カード ID |
| `pose_prompt` | Prompt-only / 併用テキスト |
| `pose_asset_uri` / `pose_asset_id` | reference がある場合のみ |
| `control_strength` | LLLite 等の strength |
| `pose_flip` | 左右反転（将来） |

内部ルーティング:

```text
Pose Gallery → PoseDefinition → Shot.render_spec.pose
   ├─ referenceあり → PoseControlledRender / LLLite
   └─ referenceなし → BaseRender / LayoutGuidedRender + pose_prompt コンパイル
```

UI 上は Prompt-only と reference-image を同列に見せる。方式はユーザーに意識させない。

Character / Outfit は変更しない。**Pose Gallery の見本人物 ≠ 生成対象**。

---

## Provenance（生成後に残す）

```json
{
  "pose_id": "standing_hand_on_hip_01",
  "pose_method": "reference_image",
  "pose_prompt": "standing with one hand on hip",
  "pose_asset_id": "...",
  "control_strength": 1.0,
  "flipped": false
}
```

`pose_method`: `prompt` | `reference_image` | `openpose` | `pose_lora`（将来）。

---

## Real validation（Gate 順序）

実装レビュー基準は UI 表示ではなく:

```text
Gallery → Apply → Shot保存 → 実Comfy → Review → provenance → Character/Outfit非混線
```

ケース **P01–P05**（Prompt / Reference / Flip / Character isolation / Outfit isolation）は
[`../validation/pose-gallery-live-validation.md`](../validation/pose-gallery-live-validation.md)。

前提: Gate 2.6 が ANIMADEX Ground Truth 再採点で human PASS していること。  
リモートが `a9928dd` の間は設計承認のみ（実装差分未確認）。

---

## 実装マップ

| 部品 | 場所 |
|------|------|
| 方針 | 本ドキュメント |
| カタログ | `apps/web/src/pose/catalog.ts` |
| Gallery UI | `apps/web/src/components/PoseGallery.tsx` |
| Shot 選択表示 | `apps/web/src/components/PosePicker.tsx` |
| 配線 | `ShotStudioPage.tsx` |

Pose ecosystem 検証計画（LoRA 等）は [`../validation/character_lora_pose_ecosystem_plan.md`](../validation/character_lora_pose_ecosystem_plan.md) を継続。UI 入口はこの Gallery に揃える。
