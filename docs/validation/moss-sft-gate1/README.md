# MOSS-SFT Gate 1 — Real Comfy 1枚

#B 必須ゲート。配線テストではなく、**本物の PNG が1枚出ること**を証明する。

## 合格条件

| 項目 | 基準 |
|------|------|
| 経路 | SceneWeaver UseCase → Comfy → Asset |
| capability | `LayoutGuidedRender` |
| model_id | `moss_image_sft` |
| workflow | `moss_sft_v1` + `workflow_hash` + seed |
| prompt | `moss_caption_v1`（`safe` / `@fuzichoco` / `@rella` なし） |
| 画像 | PNG decode 可能、width/height ≥ 512、近黒でない |
| artifact | このディレクトリに `gate1_seed_*.png` + `.manifest.json` |
| replay | 同一 seed で capability / workflow スナップショット復元 |

## Manifest（成功時）

```json
{
  "gate": "moss-sft-gate1",
  "status": "passed",
  "capability": "LayoutGuidedRender",
  "model_id": "moss_image_sft",
  "workflow_template_id": "moss_sft_v1",
  "workflow_hash": "...",
  "seed": 12345,
  "prompt_hash": "...",
  "width": 1024,
  "height": 1024,
  "mime": "image/png",
  "sha256": "...",
  "external_job_ref": "...",
  "comfy_version": "0.42.1",
  "image_file": "gate1_seed_12345.png"
}
```

`comfy_version` は必須。native MOSS 境界の再現に使う。

## FAIL の分類

| パターン | クラス | 扱い |
|----------|--------|------|
| Comfy unreachable | **ENV** | ホスト起動 |
| LayoutGuidedRender configured だが `moss_image` CLIP なし | **ENV** | Comfy → **≥ 0.42.1**（最低 e087d8f+） |
| weights 欠落 | **ENV** | Comfy-Org/MOSS-Image 配置 |
| node/weights あり → submit 成功 → 画像0枚 / 黒画像 | **SW** | SceneWeaver / workflow 調査 |

期待する現状 FAIL（良い FAIL）:

```text
Comfy reachable → LayoutGuidedRender configured
  → native moss_image CLIP type がない → ENV FAIL
```

## 実行（入口はこれだけ使う）

`pnpm test:e2e:live:required -- moss-sft` は使わない。root script が複合シェルのため、pnpm の余分引数が Playwright に届かないことがある。

```bash
# pytest — artifact を docs/validation/moss-sft-gate1/ に書き出す
pnpm test:moss:live

# Playwright — MOSS だけ / unreachable=FAIL（専用 script）
pnpm test:moss:e2e:live:required
```

開発用の全 live suite（skip 可）は従来どおり `pnpm test:e2e:live`。

## ホスト前提

| | 条件 |
|--|------|
| 最低 | ComfyUI **e087d8f+**（`CLIPLoader type=moss_image`） |
| **推奨（Gate 1）** | ComfyUI **≥ 0.42.1**（0.42.0 MOSS support + 0.42.1 template crash fix） |
| Weights | `moss_image_sft_int8_convrot.safetensors` / `qwen3.5_9b_w4a8_gptq.safetensors` / `flux2-vae_small.safetensors`（Comfy-Org/MOSS-Image） |
| VAE | **FP32**（`--bf16-vae` なし — Flux2 BF16 黒画像回避） |

## 現状ステータス

| 日付 | 結果 | メモ |
|------|------|------|
| 2026-10-25 | **ENV BLOCKED** | Comfy `0.31.1` — `moss_image` 未搭載。重み未配置。Gate1 PNG 未生成。 |
| 2026-10-26 | **ENV BLOCKED（継続）** | head `2dc367d`+。テスト入口は揃ったが **実 PNG は 0枚**（このディレクトリは README のみ）。Character LoRA / Pose ecosystem は [計画のみ](../character_lora_pose_ecosystem_plan.md) — **実装しない**。 |
| 2026-10-26 | **pytest PASS — 目視待ち** | Comfy `0.42.5` + 3 weights。`pnpm test:moss:live` → `gate1_seed_12345.png` (1024²)。**e2e:required は未実行**（先に PNG 目視）。 |
| 2026-10-26 | **Gate 1 e2e PASS** | `pnpm test:moss:e2e:live:required` PASS。**neutral smoke のみ** — 対象キャラ検証は [Gate 2.5](../moss-sft-gate2_5_target_fixtures.md)。 |

### いまやること（コード変更ではない）

```text
Comfy 0.31.1 → >= 0.42.1 → MOSS 3 weights → pnpm test:moss:live
  → gate1_seed_*.png 目視 → pnpm test:moss:e2e:live:required → Gate 1 PASS
```
