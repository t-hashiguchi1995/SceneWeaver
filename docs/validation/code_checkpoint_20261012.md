# コード固定とpush前の検証（2026-10-12）

Validated code commit: `ea83b366e12e25dc0ad3d64a7917326902a07363`

このコミットで、ローカルの制作UI・Prompt Assembly・状態引継ぎ・画像表示・履歴・CSP出力・検証用スクリプト・R2設計書・既存検証記録を固定した。認証情報、runtime DB、ブラウザプロファイルは含めない。追加・変更236ファイルの秘密情報パターン検査で検出なし。最大ファイル約5.9MB。

## 今回再実行した検証

- `uv run pytest`: 全52件通過、skipなし、302.91秒。Starlette TestClientの非推奨警告1件。
- `pnpm --dir apps/web build`: TypeScriptチェックとVite production build通過。
- `git diff --check` と staged diffの空白チェック: 通過。
- コミット後の `git status --short`: 出力なし。テスト開始時のtrackedコードとこのコミットのコードは同一。実行中にコード編集は行っていない。

環境: Linux Python 3.12.10、pytest 9.1.1、Vite 8.3.4。Backend試験は一時runtimeとfake画像バックエンドを使用。

## 既存結果として含めた記録

- [mock browser 10件](release-20261012/README.md): 実API・Worker・Web、LLM=stub、Image=fake。
- [real Comfy 4件](comfy_prompt_library_20261011.md): RTX 3090、実Comfy、LLM=stub。
- [実投稿3サービス](social-posting-20261012/README.md): 専用Chrome経由、各1件・同一画像1枚・全員公開。
- [R2 HTML表示・操作](r2-design-20261012/README.md): ローカルリンク・操作・1440px／390px確認。

これらの既存記録はコミット前に取得した結果で、当時の検証コードSHAは未固定。今回のpush準備でブラウザE2E・実Comfy・外部投稿を再実行したものではない。実LLM品質、アプリ内Publish統合、CSP round-trip、LoRA適用は未完了。

本ファイルとREADMEの検証件数更新は後続の文書コミットに保存する。検証コードSHAは上記コミットのまま。rcタグの作成やProduction releaseは今回のpushに含めない。
