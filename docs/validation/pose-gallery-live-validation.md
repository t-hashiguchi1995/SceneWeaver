# Pose Gallery — live validation（実生成ゲート）

**段階:** A3（[`quality-validation-roadmap.md`](./quality-validation-roadmap.md)）  
**ステータス:** 実装済み / Auto 実行可（`pnpm test:pose-gallery:live`）— Human GT は別途  
**UI 方針:** [`../ux/pose-gallery-first.md`](../ux/pose-gallery-first.md)  
**前提:** A1 Gate 2.6 ✅ → A2 Gate 2.7 PASS → 本ゲート

---

## 分離原則（維持）

```text
Gallery の見本人物 ≠ 生成対象
Pose だけ抽出 → 現在の Character / Outfit に適用
```

---

## 内部ルーティング

```text
PoseDefinition
     │
     ├── prompt only
     │      ├─ Anima → tag compiler（例: standing, one hand on hip, contrapposto）
     │      └─ MOSS  → NL compiler（例: standing with one hand resting on her hip, …）
     │
     └── reference image
            └─ PoseControlledRender → LLLite
```

UI 上は Prompt-only / reference を同列。`asset://` はユーザーに見せない。

---

## Live ケース（P01–P05）

基準フロー:

```text
Gallery → Apply → Shot保存 → 実Comfy → Review → provenance → Character/Outfit非混線
```

| ケース | 入力 | 期待する生成経路 |
|--------|------|------------------|
| **P01** Prompt Pose | `pose_prompt` のみ | Anima Base / MOSS + Prompt |
| **P02** Reference Pose | reference PNG + strength | Anima Pose / LLLite |
| **P03** Flip | P02 + 左右反転 | Reference を反転して生成 |
| **P04** Character isolation | 同じ Pose × 別 Character | Pose だけ共有、人物は混ざらない |
| **P05** Outfit isolation | 同じ Pose × Outfit A/B | Pose 固定、衣装だけ切替 |

**P04 が最重要。** サムネ人物特徴が漏れたら Gallery-first 失敗。

推奨キャラ: **リゼ / 伊吹翼 / Firefly(ホタル)**（静的・動的・SF で差が見やすい）。  
Character Prompt は ANIMADEX GT 整合済みのものを使う。

---

## Provenance（方式統一）

Reference:

```json
{
  "pose_id": "hand_on_hip_01",
  "pose_method": "reference_image",
  "pose_prompt": "standing with one hand on hip",
  "pose_asset_id": "...",
  "control_strength": 1.0,
  "flipped": false
}
```

Prompt-only:

```json
{
  "pose_id": "arms_crossed_01",
  "pose_method": "prompt",
  "pose_prompt": "standing with arms crossed",
  "pose_asset_id": null,
  "control_strength": null,
  "flipped": false
}
```

---

## PASS 条件（案）

```text
✅ P01–P05 各ケースで画像生成成功
✅ provenance に pose_id / pose_method / flipped（+ strength/asset when reference）
✅ P04: サムネ人物の identity 漏れなし（GT チェックリスト）
✅ P05: Pose 固定のまま outfit のみ変化
✅ UI に asset:// を露出しない
```

---

## 実行

```bash
pnpm test:pose-gallery:live
```

成果物: [`pose-gallery-live/`](./pose-gallery-live/)（`SUMMARY.md` · `contact_sheet.png` · P01–P05）

`pose_method=prompt` で Shisei に line があっても Prompt Pose（BaseRender）を強制できる。

---

## Gate 順序

```text
Gate 1 / 2 / 2.5              ✅
Anima Gate 2.6 (+ ANIMADEX GT) ✅
Gate 2.7 Full Character        ✅ Auto + Human
Pose Gallery Live P01–P05      ▶ 本ゲート
Gate 3  A→B→C→A
Pose ecosystem（Prompt / LLLite / OpenPose / Pose LoRA）
```
