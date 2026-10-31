# SceneWeaver 品質確認ロードマップ

**方針:** Gate 通過だけでは「できた」扱いにしない。  
**実画像 + Ground Truth + UI操作** が揃って初めて合格。

評価 GT: [`animadex-character-evaluation.md`](./animadex-character-evaluation.md)（ANIMADEX → 公式 → Danbooru）

---

## 段階一覧

| 段階 | 目的 | 状態 |
|------|------|------|
| **P12** | Phase 1–2 Quick Studio vertical slice | 🟡 CONDITIONAL → close後 ✅ |
| **A1** | Anima Prompt 品質（Gate 2.6・5キャラ） | ✅ |
| **A2** | Anima 全標準キャラ確認（**Gate 2.7**・C01–C11） | 🔴 |
| **A3** | Pose Gallery 実生成（P01–P05） | 🔴 |
| **A4** | 衣装 A→B→C→A（Gate 3・4キャラ） | 🔴 |
| **M1** | MOSS キャラ品質（同一 Semantic GT） | 🔴 |
| **M2** | MOSS Prompt refinement（Base→edit→same seed） | 🔴 |
| **Fair** | Anima vs MOSS Production Fair | 🔴 |
| **UX1** | 主要ユースケース UIUX（5本） | 🔴 |
| **INT** | 統合 E2E / 複数キャラ×衣装 | 最後 |
| Adult / Character LoRA / Pose ecosystem | 後段 | 🔴 |

```text
0. Phase 1–2 Quick Studio vertical slice
   (Pose API → /studio → Anima PNG → provenance → Review → Adopt=copy)
1. A2 Gate 2.7 Full Character Coverage
2. A3 Pose Gallery Live P01–P05
3. A4 Gate 3 Outfit isolation
4. M1 / M2 MOSS quality + refine
5. Anima vs MOSS Fair
6. UX1 vertical review
7. 複数キャラ×衣装
8. Adult / LoRA / Pose ecosystem
```

キャラ・ポーズ・衣装・MOSS・UIUX は **別々に確認してから** 統合する。

---

## A2 — Gate 2.7 Anima Full Character Coverage

詳細: [`anima-gate2_7_full_coverage.md`](./anima-gate2_7_full_coverage.md)

11 Primary を ANIMADEX+公式 GT で contact sheet 化し、  
「Anima は標準キャラ群について概ねいける」と言えるかを見る。

---

## A3 — Pose Gallery Live

詳細: [`pose-gallery-live-validation.md`](./pose-gallery-live-validation.md)

| ケース | 見るもの |
|--------|----------|
| P01 | ポーズ指示が反映されるか |
| P02 | LLLite で姿勢が寄るか |
| P03 | 左右反転が効くか |
| P04 | Pose 参考人物が混ざらないか |
| P05 | Pose 固定で衣装だけ変えられるか |

`Gallery→選択→Shot→Generate→実画像→Review→provenance` まで必須。  
「操作できる」だけでは PASS にしない。

---

## A4 — Gate 3 Outfit

対象例: リゼ / 春日未来 / 伊吹翼 / Firefly  
主眼: **最後の A に B/C の服が残らない**（Prompt snapshot + OutfitProfile + 画像）。

---

## M1 / M2 — MOSS

同一 Semantic GT から Anima tag / MOSS NL へ分岐。  
「実 PNG が出た」「UI→Review→Adopt」だけでは品質合格にしない。  
5キャラ程度で Base caption → edit → same seed → adopt。

---

## UX1 — コア体験 5本

1. Image Generation（Character→Outfit→Prompt→Generate→Adopt）
2. Pose（Choose Pose→Gallery→Apply→Generate）※ URI 非露出
3. Outfit / Try-On
4. Character（登録→見た目→Prompt→生成→保存）
5. Review（比較→provenance→Adopt/Reject/Regen）

各フローで **入力→実行→出力→次の行動** が迷わず繋がるか。
