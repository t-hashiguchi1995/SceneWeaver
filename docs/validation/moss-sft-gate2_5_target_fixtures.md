# Gate 2.5 — Target fixture smoke（計画）

**前提:** Gate 1（neutral smoke）PASS。Gate 2（UI → Review → Adopt）は generic 可。  
**本ゲート:** 合意済みキャラで「指定対象の生成検証」を開始する。実装/実行は Gate 2 の後。

Gate 1 の `gate1_seed_12345.png` は **中立人物スモーク**であり、リゼ等の検証完了を意味しない。

## キャラマトリクス（各1枚・衣装固定・背景簡素）

### Primary

| ID | キャラ | 目的 |
|----|--------|------|
| C01 | リゼ・ヘルエスタ | 長髪・青系・王族モチーフ |
| C02 | 栞葉るり | 落ち着いた見た目 |
| C03 | 星川サラ | 明るい色味・ポップ寄り |
| C04 | イレイナ | 帽子・髪・衣装特徴 |
| C05 | 春日未来 | アイドル系 |
| C06 | 伊吹翼 | 元気系・ポーズ向き |
| C07 | 暁美ほむら | ダークトーン |
| C08 | 鹿目まどか | ほむらとの対比 |
| C09 | ホタル | SF寄り |
| C10 | 実写系女性 | 実写・Try-On・成人向け分離用 |

### Secondary

| ID | キャラ |
|----|--------|
| S01 | 夜見れな |
| S02 | 倉持めると |
| S03 | フレン・E・ルスタリオ |

## 固定条件（最初）

- capability: `LayoutGuidedRender` / model: `moss_image_sft`
- 解像度 1024²、OpenMOSS sampling preset
- 背景: 簡素スタジオ or 単色
- 衣装: キャラ default 1 種のみ（複数衣装は Gate 3+）
- content_rating: general（R-18 は T11 / Gate 5 に分離）

## 評価観点（人手）

- 黒画像・ノイズではない
- identity の大崩れがない（髪色・目・印象がキャラとして追える）
- プロンプト/仕様の主要特徴が大まかに出ている
- （厳密な一致性・LoRA 品質は後続レーン）

## 成果物

```text
docs/validation/moss-sft-gate2_5/
  C01_rize.png + .manifest.json
  ...
  SUMMARY.md
```

## この後

```text
Gate 2.5 PASS
  → A→B→C→A / multi-char×outfit
  → モデル比較
  → Character LoRA lane / Pose ecosystem lane
```
