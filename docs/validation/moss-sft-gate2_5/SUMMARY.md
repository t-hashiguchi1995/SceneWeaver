# MOSS-SFT Gate 2.5 — SUMMARY

## Run metadata

- date: `2026-10-27T11:15:00Z`（JST 20:15 完了）
- commit: `a9928dd`（作業ツリーに Gate2/2.5 未コミット変更あり）
- model_id: `moss_image_sft`
- workflow_template_id: `moss_sft_v1`
- capability: `LayoutGuidedRender`
- comfy_version: `0.42.5`
- resolution: `1024x1024`
- seed policy: fixed per fixture_id（C01=20101 … C11=20111）
- sampling: OpenMOSS 50 / CFG 3 / euler / sgm_uniform / shift 5 / SLG 22
- runtime: ~27m43s（`pnpm test:moss:gate2_5`）

## Automatic gate

- fixtures generated: **11 / 11**
- manifests: **11 / 11**
- contact_sheet.png: **present**
- SUMMARY.md / human_scores.csv: **present**
- provenance: LayoutGuidedRender / moss_image_sft / moss_sft_v1 / seed / workflow_hash / external_job_ref

**automatic: PASS**

## Human gate

### Contact sheet 所見（本番）

#### A. 顔の均一化
- 共有の moe 顔立ちはあるが、**全員同顔ではない**
- C01 / C04 / C05 / C08 / C09 は髪・目・表情で十分区別できる
- C08（抑えた目）と C04/C09（明るい目）の差が特に明確

#### B. 色の潰れ
- 髪色帯は概ね保持（水色 / ラベンダー / 黒髪 / 金 / 灰金 / ピンク / 銀）
- C01 のみ **目色が clear blue → 紫寄り**にドリフト（主な減点）
- 衣装の基調色差は contact sheet 上で追える

#### C. シルエット差
- C05 イレイナ: 魔女帽子 + 外套がはっきり
- C08 ↔ C09: ほむら（黒紫・直線）とまどか（ピンク・フリル）の対比が強い
- C10 ホタル: テックスーツ + シアン発光で SF 寄り
- C11: 唯一の実写枠として一目で分離

#### D. Style drift
- **C11 はアニメ顔に寄っていない**（photoreal 維持）→ anime bias なし
- アニメ側が過剰写実に崩れる兆候もなし

### Per fixture

| ID | Name | Seed | Auto | Score | Human | Notes |
|----|------|------|------|-------|-------|-------|
| C01 | リゼ・ヘルエスタ | 20101 | passed | 7/8 | pass | 髪・王冠・衣装OK / 目色ドリフト |
| C02 | 栞葉るり | 20102 | passed | 8/8 | pass | ラベンダー+パステル清楚 |
| C03 | 夜見れな | 20103 | passed | 8/8 | pass | 黒髪赤目+黒赤ゴシック |
| C04 | 星川サラ | 20104 | passed | 8/8 | pass | 金髪+明るいアイドル衣装 |
| C05 | イレイナ | 20105 | passed | 8/8 | pass | 帽子シルエット強い |
| C06 | 春日未来 | 20106 | passed | 8/8 | pass | ピンクツイン+ステージ衣装 |
| C07 | 伊吹翼 | 20107 | passed | 8/8 | pass | 短髪金髪+スポーティ |
| C08 | 暁美ほむら | 20108 | passed | 8/8 | pass | 黒髪紫目+暗MG |
| C09 | 鹿目まどか | 20109 | passed | 8/8 | pass | ピンクMG / C08と明確対比 |
| C10 | ホタル | 20110 | passed | 8/8 | pass | 銀髪シアン目+SFスーツ |
| C11 | 実写系成人コスプレイヤー（オリジナル） | 20111 | passed | 8/8 | pass | 実写維持 / 特定人物模倣なし |

## Aggregate

- total fixtures: **11**
- auto passed: **11**
- auto failed: **0**
- human passed: **11 / 11**（参考ライン 9/11 を上回る）
- average score: **7.91 / 8**（参考ライン 5/8 を上回る）
- C11 extreme fail: **なし**

## Common failure patterns

- [x] face homogenization — **軽微**（moe共有はあるが支配的でない）
- [x] eye color drift — **C01 で確認**
- [ ] outfit simplification — 目立たず
- [ ] accessory omission — 王冠・帽子・リボンは概ね出ている
- [ ] background over-generation — なし（plain studio）
- [ ] anime bias on C11 — **なし**
- [x] pose stiffness — **軽微**（正面立ちが多いが仕様どおり）

## Status

- automatic: **PASS**
- human: **PASS**（暫定ラインクリア。厳密 likeness は Character LoRA lane）

## Next

- Gate 3: 1キャラ複数衣装 A→B→C→A（混線検証）
- Gate 4: multi-character × outfit
- Gate 5: adult baseline（C11 系）
