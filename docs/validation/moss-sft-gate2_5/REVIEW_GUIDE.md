# Gate 2.5 — Contact sheet / SUMMARY レビュー観点テンプレート

実行後にこの順で見る。評価の揺れを抑えるのが目的。

---

## 1. Individual PNG（1枚ずつ）

各 `C##_*.png` について最低限:

| 観点 | 見るもの |
|------|----------|
| decode | 開ける / ≥512 |
| 人物成立 | 黒・ノイズ・人体崩壊でない |
| 髪 | 色・長さ・大まかなスタイルが仕様どおりか |
| 衣装 | 標準衣装の大枠（色帯・シルエット） |
| 背景 | plain studio を逸脱していないか |
| ポーズ/枠 | standing + medium〜full + eye level が崩れていないか |

採点は `human_scores.csv` の 8点欄に記入。

---

## 2. Contact sheet（本番）

`contact_sheet.png` を一画面で比較する。

### A. 顔の均一化

- 全員が同じ顔に見えないか
- 特に **C01 / C04 / C05 / C08 / C09** の差が出ているか

### B. 色の潰れ

- 髪色差（水色 / ラベンダー / 黒髪 / 金 / 灰金 / ピンク / 銀 など）
- 目色差
- 衣装の基調色差

### C. シルエット差

- C05 イレイナの帽子
- C08 ほむら ↔ C09 まどかの印象差
- C10 ホタルの SF 寄り感
- C11 の実写感

### D. Style drift

- C11 がアニメ顔になりすぎていないか
- 逆にアニメ側が不自然に写実寄りになっていないか

---

## 3. SUMMARY.md に書く内容

```text
Run metadata
- date / commit / model_id / workflow_template_id / comfy_version / resolution / seed policy

Per fixture
- fixture id / pass-fail / score (0-8) / short notes

Aggregate
- total / passed / failed / average score / common failure patterns
```

### Common failure pattern チェック

- [ ] face homogenization
- [ ] eye color drift
- [ ] outfit simplification
- [ ] accessory omission
- [ ] background over-generation
- [ ] anime bias on C11
- [ ] pose stiffness

---

## 4. Human PASS 判定（参考ライン）

- catastrophic なし
- 各 fixture 最低限識別可能 + 主要特徴が概ね追える
- 全員同顔が支配的でない
- **11中 9以上 human pass / 平均 5/8 以上 / C11 極端崩れなし**

Automatic PASS（成果物揃い）とは独立。likeness hard は Character LoRA lane。
