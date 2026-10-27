# Character LoRA / Pose Ecosystem — 検証計画（実装前）

**UI 方針:** Pose のユーザー入口は **Gallery-first**（[`../ux/pose-gallery-first.md`](../ux/pose-gallery-first.md)）。  
URI 手入力は廃止。Prompt Pose / Reference Image / OpenPose / Pose LoRA は同じ Gallery に統合する。

**実装着手禁止条件:** [`moss-sft-gate1`](moss-sft-gate1/README.md) が PASS し、実 PNG を目視確認するまで  
`LoraLoader` / LoRA registry / strength UI には着手しない。

現状（`feat/moss-sft-stock` @ 文書作成時点）:

| レーン | 状態 |
|--------|------|
| Anima Base / Pose / Qwen Try-On | 過去 real 実績あり |
| MOSS Stock Gate 1 | **ENV BLOCKED** — 実 PNG **0枚** |
| Anima + Character LoRA | ❌ 未実装（本計画のみ） |
| Pony/Illustrious/NoobAI Pose LoRA | ❌ 別エコシステム比較研究（本計画のみ） |

---

## 1. 二種類に分ける

| 対象 | 位置づけ | SceneWeaver での扱い |
|------|----------|----------------------|
| リゼ / 星川 / 栞葉 / 倉持 / フレンの Anima（Community DiT）LoRA | **Character LoRA** | Anima キャラ再現性評価 |
| Pony / Illustrious / NoobAI の pose LoRA 一覧 | **Pose ecosystem** | Anima とは**別モデル系**。そのまま Anima に載せない |

Anima は Community DiT。Civitai の Pony/Illustrious/NoobAI フィルタで出る pose LoRA は SDXL 系エコシステムであり、現行 Anima + LLLite（画像参照）とは方式が異なる。

---

## 2. Character LoRA 検証レーン（Gate 1 後・#B に混ぜない）

### Fixtures

| 優先 | キャラ | 備考 |
|------|--------|------|
| Primary | リゼ・ヘルエスタ / 星川サラ / 栞葉るり | 既存標準 fixture |
| Secondary | 倉持めると / フレン・E・ルスタリオ | 追加 fixture |

星川サラは PixAI ミラー上 Community DiT ユーザー LoRA・trigger（`nijisara` 等）を確認済み。他4件は **ページタイトルだけで trigger/hash/license を推測しない**。registry 投入前に各モデルで下記を実ページから記録する。

### Registry 必須フィールド

```text
model_id
model_version_id
base_model
architecture          # 例: community_dit / anima
filename
sha256
trigger_words
recommended_strength
license
allow_download
allow_redistribution
source_url
```

### 実験マトリクス（固定 vs 可変）

固定: Prompt / Seed / Resolution / sampler / camera / pose  

可変: LoRA OFF / 0.6 / 0.8 / 1.0

衣装過学習チェック（必須）:

```text
Character LoRA + Default Outfit
Character LoRA + Outfit A
Character LoRA + Outfit B
Character LoRA + Outfit C
```

評価軸: キャラ同一性、髪型・髪色・目・アクセ、通常衣装、別衣装での過学習、表情/ポーズ/背景耐性、LoRA 無し Anima との差。

### コンテンツ分離

- Character LoRA lane = **一般 / SFW** の同一性テスト
- R-18 Stock baseline = 既存 **T11 adult fixture** に分離（本レーンに混ぜない）

---

## 3. Pose ecosystem 比較研究（Character LoRA 実験の後）

現行 SceneWeaver:

```text
Anima + LLLite Pose Control + pose reference image
```

Civitai Pose LoRA（典型）:

```text
Base checkpoint + Pose LoRA + trigger prompt
```

将来比較表:

| 方法 | 指定 | 見たい点 |
|------|------|----------|
| Anima LLLite | Pose 画像 | 任意姿勢への追従 |
| Pose LoRA（別系） | LoRA + trigger | 特定 pose の品質 |
| Prompt のみ | text | 最簡易 baseline |
| 将来 OpenPose | Skeleton | 厳密な身体配置 |

→ 「ポーズ指定機能をどう作るか」の設計材料。Anima 実装に Pony 系 LoRA を直結しない。

---

## 4. 実行順序（固定）

```text
Gate 1  MOSS Stock 実画像 1枚 + 目視
   ↓
Gate 2  UI → MOSS → Review → Adopt
   ↓
Character LoRA Experiment   (Anima + Primary/Secondary)
   ↓
Pose ecosystem Experiment   (LLLite vs 他系 Pose LoRA)
```

Multi-Entity / A→B→C→A / R-18 Stock は #B の Gate 順に従い、**Character LoRA 実装より前に Gate 1 を終わらせる**。
