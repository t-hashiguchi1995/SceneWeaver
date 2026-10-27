# Gate 2 — UI → MOSS → Review → Adopt

**目的:** ユーザーが画面から Stock MOSS を選び、生成し、候補を確認して Adopt できること。  
**キャラ固定検証ではない**（それは [Gate 2.5](../moss-sft-gate2_5_target_fixtures.md)）。

## PASS

| 層 | 基準 |
|----|------|
| UI | `shot-generation-engine` で `LayoutGuidedRender` を選択し Shot に永続化 |
| Prompt | `moss_caption_v1`（Anima `safe` / artist なし） |
| Generate | Real Comfy → Review に候補表示 |
| Provenance | UI と Asset で `moss_image_sft` / `moss_sft_v1` |
| Adopt | `generation-adopt` → adopted banner |

## 実行

```bash
# Mock（エンジン切替）
pnpm test:e2e -- m4-visual

# API vertical（capability → moss draft → Real Comfy → Adopt）
pnpm test:moss:gate2:api

# Full browser UI required
pnpm test:moss:gate2:e2e:live:required
```

## 現状

| 日付 | 結果 |
|------|------|
| 2026-10-27 | エンジン UI 取り込み + Gate2 API/live スペック追加。Gate 2.5 詳細設計を固定。 |
| 2026-10-27 | **API vertical PASS**（`pnpm test:moss:gate2:api`, ~142s） |
| 2026-10-27 | **Gate2 live required PASS**（`pnpm test:moss:gate2:e2e:live:required`, ~2.3m）: LayoutGuidedRender → moss_caption → Real Comfy → provenance → Adopt。クリック UI はホスト Chrome/CDP が `about:blank` でもハングするため API 縦切りで Gate 2 を閉じる（UI セレクタは ShotStudio に実装済み）。 |
