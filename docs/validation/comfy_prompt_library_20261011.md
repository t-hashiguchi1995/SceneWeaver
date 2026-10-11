# 実ComfyUI・プロンプト集の検証（2026-10-11）

Windows上の実ComfyUI `http://127.0.0.1:8188`、ComfyUI 0.31.1、PyTorch 2.10.0+cu130、NVIDIA RTX 3090で検証しました。LLMは検証用stub、画像バックエンドは実ComfyUIです。

`pnpm test:e2e:live`: 4件通過、スキップ0件、約2.9分。

| 検証 | 結果 |
|---|---|
| Anima BaseRender | 4画像、Asset保存、seed・workflow hash・外部job参照を確認 |
| Anima PoseControlledRender | 4画像、pose画像参照・control model・strengthのprovenanceを確認 |
| Qwen OutfitTryOn | 4候補、実画像バイト・model・workflowのprovenanceを確認 |
| 指定ZIP → Default Prompt → Anima | カフェ衣装・背景と共通照明を合成し4画像生成。4枚ともブラウザで画像サイズを確認 |

[ZIP素材からの実生成画像](comfy-prompt-library.png)

通常生成の最初の実行では画像生成に成功しましたが、テストのPrompt版名の期待値が旧形式でした。現在の版名 `v1` に修正し、4候補の件数も明示的に検証して再実行を通過しました。

通常の画面E2Eは9件通過。フロントエンドのproduction buildも通過。ライブラリー取り込み・組み立てと既存APIのBackend回帰も通過しました。

## 取り込み

入力: `c:/Users/hassy/Downloads/playwright_project-master/prompts.zip`

SHA-256: `06ec63f4fa41597f4e78be08b3186bddc958725947aa59c08cb87bcbcb1c3761`

既存の `runtime/studio.db` に459件を追加しました。内訳はキャラクター15件、Prompt素材340件、カテゴリラベル106件です。R18タグ付き16レコードと非対応形式8レコードは既存インポート方針に従い取り込み対象外です。これはZIP内すべての内容を意味する件数ではなく、正規化されたレコード数です。

キャラクター内の衣装・ポーズ・表情カテゴリも素材として取り込みました。素材のIDと内容ハッシュをDefault Promptの構成要素に保存し、生成時に履歴へ固定します。

## 操作

1. APIを再起動して変更を反映します。
2. 新規ショットはライブラリーがある場合、Anima Story Panelを使用します。既存ショットはProfileで選択できます。
3. ショット画面の「プロンプト集から構築」で検索して素材を選択します。
4. 「条件を保存」後、Promptを再構築します。既存の手修正を置き換える場合は画面で確認します。
5. 生成して4候補を比較します。

再取り込みは次のコマンドで実行できます（WSLパス）。同一内容は重複作成せず、変更済み内容はconflictとして報告します。

```sh
uv run python scripts/import_legacy_prompts.py --source /mnt/c/Users/hassy/Downloads/playwright_project-master/prompts.zip --apply
```

`soft_indoor` はDefault Promptの共通照明に使用します。選択素材・ショット指定の優先順位を適用し、同一種類の衣装・ポーズ・照明は1件を使用します。旧式の `{blue | white}` などは先頭候補を確定させるため、同じ構成から同じPromptを作れます。

LoRAタグはモデル修飾として保持しますが、現在の承認済みWorkflowには適用スロットがなく、そのPromptの生成は明示的に停止します。ZIP内のLoRA、旧マクロ、投稿設定や全作品設定の互換性まで検証したものではありません。
