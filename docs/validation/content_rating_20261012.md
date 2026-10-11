# 品質確認と成人向け区分の機能検証（2026-10-12）

## 品質確認の現状

既存の画像検証では、実ComfyUIの出力についてPNG形式・寸法・候補数、送信Promptの文字列一致、stepsやseedなどの生成条件、履歴を確認する。同じseedで簡易タグ／元Prompt／steps変更を比較するgalleryも保存している。

これは生成処理の正常性と比較条件の確認であり、作品品質の自動合格判定ではない。画像ごとの人物再現・手指・衣装・構図などを採点した評価表は未整備。既存の目視所見は [リゼ検証報告](rize_validation_20261011.md) を参照。

ストーリー検証のLLMはstubで、場面に応じたセリフの変化が不適合。実LLMの作品品質は未検証。固定応答のCriticスコアは品質の根拠として扱えない。

## 成人向け区分の検証範囲

性的内容を含まないダミー文字列で機能を検証する。露骨な性的画像の生成・目視評価は実施していない。

- 一般向けprofileではadult素材をpositive／negativeの両方から除外し、素材のLoRAも取り込まない。
- assembly関数へ明示的にadult profileを渡すとgeneral／adultのダミー素材を採用し、不明な区分を除外する。
- 実際のPromptRendererは一般向けprofile固定。render_specにadultを指定してもadult素材は除外され、警告が履歴用metadataに残る。
- プロジェクトのadult区分はDBに保存して読み出せる。
- 既存インポートはR-18素材をadult-taggedとして分類し、取り込み対象から除外する。

したがって、区分の保存と除外処理は存在するが、成人向け素材の取り込みから生成までの対応は未完了。画像品質やR-18生成成功を示す結果ではない。

追加テスト: [test_content_rating.py](../../tests/unit/test_content_rating.py)。

実行結果: 新規5ケースを含む28件すべて通過（203.10秒）。Starlette TestClientの依存に関する非推奨警告が1件。

実行コマンド:

```sh
uv run pytest tests/unit/test_content_rating.py tests/unit/test_legacy_prompt_import.py tests/unit/test_ui_architecture.py tests/unit/test_generation_review.py tests/unit/test_prompt_draft.py tests/unit/test_dialogue_pipeline.py tests/unit/test_workflow_compiler.py tests/integration/test_prompt_library.py
```
