# リゼ・ヘルエスタの複数パターン検証

実ComfyUI（RTX 3090、Anima）で実行した結果です。

- [既存タグ・ご提示Prompt・stepsの比較（12画像）](rize-quality/20261011T075202734857Z/index.html)
- [図書館・カフェ・握手会の3場面×3コマ（36画像）](rize/20261011T072531980675Z/index.html)
- [ブラウザでの48画像デコード・モバイル幅確認](rize-browser-check.json)

## 既存Promptの使用状況と修正

最初の36画像ではZIPの衣装・照明・表情・ポーズ素材を使用しました。一方、品質・画風はDefault Prompt Builderの簡易設定（`anime illustration, masterpiece, best quality, highres`）でした。既存Anima Compilerの `year 2025, newest, score_9, score_8, @fuzichoco, @rella` を引き継いでいなかったため、元Prompt全体を維持した検証ではありませんでした。

新規ショットでライブラリーがある場合は、既存Animaの品質・artistタグを含む `anima_legacy_v1` を設定するよう修正しました。既存の手修正や履歴は書き換えません。画面で品質プリセットを選択し、条件保存後にPromptを再構築できます。steps・CFGも条件として設定でき、生成スナップショットと再生成条件に保存します。

## 同一seedでの品質比較

| 条件 | Positive | Steps | CFG | 枚数 |
|---|---|---:|---:|---:|
| A | 同じ内容からyear/newest/score/artistタグを除き、簡易画風タグを使用 | 8 | 4 | 4 |
| B | ご提示のPromptそのまま | 8 | 4 | 4 |
| C | ご提示のPromptそのまま | 24 | 4 | 4 |

全条件のseedは20261011、768×1024、sampler=`er_sde`、scheduler=`simple`、negative固定です。B・Cは改行も含めたpositiveの文字列一致を生成履歴で検証しました。比較用の入力は [rize_user_prompt.txt](../../tests/fixtures/story/rize_user_prompt.txt) です。

代表候補ではAは平坦なアニメ塗り、B/Cは髪・目・衣服に色の重なりや細かな描き込みが増える画風になりました。画風の好み、衣装の解釈、指や構図は画像ごとに差があり、生成成功だけで品質が合格したとは扱いません。galleryで各4候補を比較できます。

## セリフとストーリー

検証は「図書館の謎が返却日のメモだと分かる」「巨大なコーヒーカップへのツッコミから休憩へ」「緊張するファンを迎えて見送る」の3パターンです。各パターンに導入・転換・結末を設けました。

現在LLMはstubです。全9ビートで同じセリフ候補と同じDirector目的を返したため、場面適合性とセリフの変化は不適合です。27候補は記録しましたが、実LLMの品質検証は未完了です。画像に対応する確定セリフは検証用の創作を手修正してロックしたものです。LLMがそのセリフや物語を自動生成した結果ではありません。

公式設定と外見は[にじさんじの公式プロフィール](https://www.nijisanji.jp/talents/l/lize-helesta)を参照しました。口調例と3つの物語は検証用の創作で、本人の実発言や公式作品ではありません。

見つかったアプリ側の欠落も修正しました。前のコマで確定したセリフ・状態変化・関係性を次のDirector/Writer/Criticに渡し、ショット計画には確定セリフと状態を渡します。Default Promptの背景・照明・衣装にもBeatの状態変化を反映します。セリフの状態引き継ぎとロック保持はBackendテストで確認しました。

LoRA付き固有衣装は現在の承認済みWorkflowで適用できず、黙って落とさず生成前に停止することも検証しました。これらのWorkflow互換性は画像品質とは別の未対応項目です。Workflow設定の変更により、以前の設定ハッシュで作られた履歴の再生成は差異検出で停止する場合があります。

## 再実行

```sh
# 未設定LLMをstubとして明記した画像・状態引き継ぎ検証
uv run python scripts/validate_rize_patterns.py --source /mnt/c/Users/hassy/Downloads/playwright_project-master/prompts.zip --allow-stub
# ご提示の元Promptとstepsの比較
uv run python scripts/validate_rize_quality.py
# LLM接続後のストーリー構成・セリフ自動生成も含む検証
uv run python scripts/validate_rize_patterns.py --source /mnt/c/Users/hassy/Downloads/playwright_project-master/prompts.zip --llm-base-url YOUR_URL --llm-model YOUR_MODEL --generate-story
```

APIキーはアプリSettingsまたは `SCENEWEAVER_LLM_API_KEY` で設定します。レポートにキーは保存しません。作業用DBは各検証run内に隔離しています。

既存画面のE2Eは9件通過、Frontend buildも通過。Backendは確定セリフ・状態引き継ぎ、Prompt原文保持、sampling値検証、再生成条件の保持を検証済みです。
