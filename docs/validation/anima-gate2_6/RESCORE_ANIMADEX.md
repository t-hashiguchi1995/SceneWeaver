# Gate 2.6 — ANIMADEX Ground Truth 再採点

**対象画像:** 初回 run（`a9928dd` 近傍の local artifacts）  
**方法:** [`ground_truth.md`](./ground_truth.md) のチェックリスト照合（「雰囲気」禁止）

---

## 初回 human スコア（雰囲気採点） vs GT 再採点

| ID | 旧 Base→Edited (Δ) | GT Base→Edited (Δ) | 判定 |
|----|-------------------|---------------------|------|
| C01 | 14→19 (+5) | **15→18 (+3)** | 改善は維持。ただし旧 prompt の `blue eyes` は GT 不一致 |
| C04 | 11→19 (+8) | **11→16 (+5)** | 改善は維持。Edited の twin tails は GT side ponytail とずれ |
| C05 | 19→20 (+1) | **19→20 (+1)** | 妥当（高 Base） |
| C08 | 19→16 (−3) | **19→13 (−6)** | **明確な悪化**（MG 白ジャケット/リボン/Soul Gem が弱化） |
| C10 | 12→18 (+6) | **2→3 (+1)** | **偽改善**。定義自体が Firefly ではなく original android |

### GT チェック要約

**C01** — purple eyes / two-tone white-blue / blunt bangs / crown: Base・Edited とも概ね一致。Edited の方が royal blue シルエットが明確 → Δ+。

**C04** — hetero red/yellow / X ornament: Edited で大幅改善。side ponytail 未達だが別人ではない。

**C05** — witch hat / black robe / ash hair: 両方高一致。

**C08** — magical girl: Base 高一致。Edited は dark dress 寄りで GT outfit/accessory 低下 → 悪化。

**C10** — Firefly: grey **long** hair / purple eyes / black hairband / white shirt / black jacket。  
Base（短髪・cyan・白テックスーツ）も Edited（暗色メカスーツ・neon cyan）も **GT 項目ほぼ全滅**。旧 18/20 は「自作 android 定義への適合」であり Firefly 評価としては無効。

---

## 改訂後の Human PASS

初回宣言の human PASS は **撤回**する。

```text
旧: 4/5 Δ>0 / 明確悪化なし → PASS
新: 真の GT 改善は C01/C04/C05 の 3/5
    C08 明確悪化
    C10 ターゲット誤り（採点不能に近い）
 → human: FAIL（条件付き）
```

automatic（生成成功・成果物）は引き続き PASS。

---

## 是正アクション → 実施済み

1. ✅ Semantic / Edited を ANIMADEX Trigger+Tags に修正（C10→Firefly、目色、MG 衣装）
2. ✅ Gate 2.6 再実行
3. ✅ GT 再採点 → **5/5 Δ>0 / human PASS**（`SUMMARY.md` / `human_scores.csv`）

### 再 run GT スコア

| ID | Base | Edited | Δ |
|----|------|--------|---|
| C01 | 15 | 20 | +5 |
| C04 | 11 | 20 | +9 |
| C05 | 19 | 20 | +1 |
| C08 | 16 | 20 | +4 |
| C10 | 15 | 19 | +4 |

初回の「雰囲気 PASS」は無効。正式 human PASS は本再 run を採用する。
