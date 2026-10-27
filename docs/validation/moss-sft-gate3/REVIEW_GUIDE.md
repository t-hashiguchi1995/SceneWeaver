# Gate 3 — レビュー観点テンプレート

## 見る順

1. **Prompt / manifest**（自動でほぼ担保）— A2 に B/C marker が無いこと
2. **`sequence.png`**（本番）— 横一列で衣装残留を目視
3. 個別 PNG — Identity / Outfit / Leakage 採点

## sequence.png の見方

```text
[A1] → [B] → [C] → [A2]
```

| チェック | FAIL 例 |
|----------|---------|
| B に A が残る | A の青白ドレス要素がパーカーに混ざる |
| C に A/B が残る | 赤ドレスにフーディ/デニム痕跡 |
| **A2 に B/C が残る** | パーカー・デニム・赤ドレス・スーツ等が A 復帰に混入 → **即 FAIL** |
| A1≈A2 衣装仕様 | カテゴリ・色帯が A に戻っている |

## 採点（各 turn 0–6）

| 軸 | 0 | 1 | 2 |
|----|---|---|---|
| Identity | 大崩れ | 一部維持 | 良好 |
| Outfit | 指定不一致 | 部分一致 | 明確に一致 |
| Leakage | 強い混入 | 軽微 | なし |

1キャラ 24点。**A2 Leakage=2 が human PASS の必須条件。**

## Common failure patterns

- [ ] A attributes persist into B
- [ ] B/C attributes persist into A2（最悪）
- [ ] identity drift across turns
- [ ] outfit category collapse（全部似たドレスになる）
- [ ] wrong silhouette on SF (C10) after casual/formal
