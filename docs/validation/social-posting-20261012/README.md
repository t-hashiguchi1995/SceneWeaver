# X・pixiv・Patreon 実投稿テスト

2026-10-12、ユーザーがログインしたWindowsの専用ChromeにCDPで接続し、各サービスの投稿画面から実際に公開した。3サービスとも同じカフェ4コマ完成画像1枚を添付した。

- X: https://x.com/otk_LeiazelHets/status/2109323919966789666 — 本文「テスト」。投稿API応答の投稿IDを確認し、投稿URLを開いて本文を確認。
- pixiv: https://www.pixiv.net/artworks/150746419 — タイトル「リゼ・ヘルエスタ」、全体公開、全年齢、性的表現なし、AI生成あり。ユーザーのリンク付き説明文をもとに、テストであることと同じ画像のPatreon投稿を明記。公開URLで本文・画像ロード・AI生成表示を確認。
- Patreon: https://www.patreon.com/GenerativeAI410/posts/rizeheruesuta-172069779 — タイトル「リゼ・ヘルエスタ」、無料の全員公開。本文は「テスト」「今回は4コマ完成画像1枚の投稿テストです。」「pixivにもサンプル投稿しております。」。ログイン情報のない新規一時contextでも本文と画像を表示できることを確認。

## 範囲と記録

これは専用Chromeから外部サービスへの実投稿の検証。SceneWeaverアプリ内の公開ボタンから実投稿する連携は未実装のまま。今回その機能を実装した結果ではない。

パスワード入力はユーザーが行った。スクリプトはパスワードやCookieを読み出さず、storageState・認証データ・ネットワークtraceを保存しない。保存したJSONは投稿URL・本文等の結果と画像のローカルパスのみ。専用Chromeのログインセッションはブラウザ側に残るため、終了時はユーザーが専用Chromeのシークレットウィンドウをすべて閉じる。

投稿の二重送信を防ぐため、公開ボタンを押す前に各サービスのsubmission_started記録を作成し、記録がある場合は再送を停止する。Patreonとpixivは公開ページで確認後にpublishedへ更新した。

証拠: [X結果](x.json)、[pixiv結果](pixiv.json)、[Patreon結果](patreon.json)、[pixiv画面](pixiv.png)、[Patreon未ログイン画面](patreon.png)。
