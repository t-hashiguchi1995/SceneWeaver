# R2設計書の表示・操作検証

対象: [SceneWeaver UI・統合設計書 R2](../../architecture/sceneweaver_ui_integration_design_r2.html)。

`node scripts/check_r2_design.cjs` を一時のheadless Chromeで実行。ログイン済みChromeへの接続、画像生成、外部投稿は行っていない。

確認結果:

- 10セクション、16項目の状態表、22リンク・アンカーの存在を確認。
- 状態フィルター、キーボードでのタブ移動、本文変更による確認チェック解除、改行表示、結果不明の復旧デモが動作。
- 幅1440pxと390pxで表示を確認。モバイルのページ全体に横はみ出しなし。JavaScript例外なし。
- デスクトップ先頭と公開画面のスクリーンショットを目視確認。

証拠: [チェック結果](checks.json)、[先頭画面](desktop-top.png)、[公開画面](release-wireframe.png)、[全体](desktop.png)、[モバイル](mobile.png)。

アプリの全回帰、実LLM品質、実Comfy、実投稿の追加検証を示す結果ではない。R2中のそれらの件数は既存検証記録から引用した。
