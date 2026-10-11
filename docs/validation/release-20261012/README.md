# X・pixiv・Patreon向け公開フローの実アプリ検証

2026-10-12、`pnpm test:e2e` を実行。API（8010）、Worker、Web（5174）を起動し、Playwrightから実Chromeを操作した。10テストすべて通過（ブラウザ実行55.8秒）。テスト終了時にスタックを停止した。

テスト専用DBを使用。画像バックエンドはfake、LLMはstub。追加の公開プレビューテストではAPI応答をmockせず、実アプリの入力欄とボタンから操作した。外部サイトへのログイン・アップロード・公開は実施していない。

## 確認できた動作

- 画像採用 → CSP出力 → X／pixiv／Patreonの版プレビュー表示。
- プロジェクトURLから公開準備画面を開き、日本語・絵文字・複数行の説明を入力して版を作成。
- Xの本文・hashtags・alt_text、pixivのtitle・description・tags・AI開示フラグ、Patreonのtitle・body_markdownがAPI応答に反映。
- APIデータの改行保持、3サービスすべての画面への本文反映。
- 入力を変更して再作成すると、3サービスすべての本文が更新される。
- 幅390pxで横にはみ出さない。公開画面でJavaScript例外なし。

証拠: [desktop](desktop.png)、[mobile](mobile.png)、[API応答](preview.json)。

## 未対応・目視で見つかった課題

- 現在の公開機能は `/api/v1/releases/preview` のみ。3サービスの認証・投稿送信・公開結果確認は未実装。プレビュー成功は実投稿成功を意味しない。
- プレビューAPIはtitle／summary／hashtagsのみを受け取り、採用画像やCSP出力を受け取らない。Patreonのattachment_orderは空。画像投稿の検証はできない。
- データ中の改行は保持されるが、画面の通常のp要素では改行が空白へ潰れる。
- PatreonのMarkdownはレンダリングされず、`##` を含む生の文字列として表示される。
- 入力欄は標準ブラウザの外見で、特にモバイルではラベルと欄の並びが読みにくい。
- 外部サービス側の文字数・画像条件・投稿制限への適合性、投稿の保存・予約・再送・二重投稿防止は今回未検証。

追加テスト: [release-preview.spec.ts](../../../tests/e2e/specs/release-preview.spec.ts)。
