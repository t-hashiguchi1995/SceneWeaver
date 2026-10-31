# Gate 2.7 — Anima Full Character Coverage

**段階:** A2  
**ステータス:** Automatic PASS / Human PENDING  


**前提:** Gate 2.6 human PASS（ANIMADEX GT）  
**目的:** 5キャラだけでなく **全 Primary** で「Anima は標準キャラ群について概ねいける」と言えるか確認する。

評価は雰囲気禁止。[`animadex-character-evaluation.md`](./animadex-character-evaluation.md) の GT チェックリスト。

---

## Roster（最低 11）

| ID | Character | 備考 |
|----|-----------|------|
| C01 | リゼ・ヘルエスタ | Gate 2.6 adopted あり |
| C02 | 栞葉るり | |
| C03 | 夜見れな | |
| C04 | 星川サラ | Gate 2.6 adopted あり |
| C05 | イレイナ | Gate 2.6 adopted あり |
| C06 | 春日未来 | |
| C07 | 伊吹翼 | Pose Live 推奨キャラ |
| C08 | 暁美ほむら | Gate 2.6 adopted あり |
| C09 | 鹿目まどか | |
| C10 | Firefly | Gate 2.6 adopted あり（HSR） |
| C11 | オリジナル成人実写系 | general 外見／行為描写は別 Gate |

---

## フロー（各キャラ）

```text
1. ANIMADEX + 公式 → Ground Truth 記入
2. Semantic Spec（Trigger / tags）
3. Anima compile（adopted があれば優先）
4. Fixed seed で BaseRender 生成
5. GT チェックリスト採点
6. 必要なら Prompt edit → same seed → adopt
7. contact sheet に載せる
```

Gate 2.6 済み5人は adopted Prompt を起点に再生成してよい（seed は Gate 2.7 表で固定）。

---

## GT チェック項目（必須）

```text
Trigger / Hair / Eyes / Hairstyle /
Signature accessory / Default outfit / Main colors / Silhouette
```

C11 は「実写寄りオリジナル」として別基準（anime bias 支配的でないこと）を SUMMARY に明記。

---

## 成果物

```text
docs/validation/anima-gate2_7/
  C01/ … C11/
    image.png
    manifest.json
    gt_checklist.md   # または CSV 行
  adopted_prompts/    # 未採用キャラはここで確定
  contact_sheet.png
  human_scores.csv
  SUMMARY.md
```

---

## PASS 条件

### Automatic

```text
✅ 11/11 PNG decode ≥512 + provenance（anima_base / anima_base_v1 / seed / prompt_hash）
✅ contact_sheet.png + SUMMARY.md + human_scores.csv
✅ Trigger が Prompt / provenance に残る（C11 は original 方針どおり）
```

### Human（GT）

```text
✅ catastrophic failure なし
✅ 11中 ≥9 が GT 主要項目を概ね満たす（識別可能）
✅ contact sheet 上で別人取り違えが支配的でない
✅ C11 が極端な anime 化で破綻しない
```

「生成できた」だけでは PASS にしない。

---

## 実行

```bash
pnpm test:anima:gate2_7
```

Human FAIL 後の固定 seed rematch（C02 / C04 / C06 / C11）:

```bash
pnpm test:anima:gate2_7:remediation
```

---

## Next

Gate 2.7 Human PASS → **A3 Pose Gallery Live P01–P05**  
→ A4 Gate 3（リゼ / 未来 / 翼 / Firefly）

UI/UX（Phase 2.1 Quick Studio 3-pane 等）は画像品質 Gate とは分離して進める。
