# 2026-11-08 BFガイドのsitemap掲載 / P-003 検索表示減の切り分け

## (1) sitemapにguideのslugは自動で入るか(事実: frontend/app/sitemap.ts、curl 2026-11-08)
- 静的ガイド(frontend/lib/guides.ts の GUIDES 配列に追加)は **自動で入る**(sitemap.ts の GUIDES.map)。手動追加は不要。本番sitemapはguides 14件(+一覧)で、GUIDES 14件と一致。ISRは1時間(revalidate=3600)なので、デプロイ後最大1時間で反映。
- **穴**: DB保存のAIガイド(/api/guides、content_optimizerのnew_guide)は /guides 一覧には出るが、sitemap.ts は GUIDES しか見ない=**sitemapに入らない**。現在はDBのAIガイド0件(一覧の14件=sitemapの14件、curl)なので実害は未発生。マーケがBFガイドをGUIDESに書けば不要、DB経由なら要patch。
- lastmod: guideは publishedAt のみ。prime-appreciation-sale-2026-golf は11/1に書き直したが lastmod は 2026-10-12 のまま(本番sitemap)。更新日を持つ項目は無い(別案、未patch)。
- canonical: /guides/[slug] は generateMetadata で絶対URL指定済み。prime guideの本番HTMLに canonical あり・robots meta無し(curl)。

## 成果物
`2026-11-08_sitemap_AIガイド含める.patch`(sitemap.ts のみ、`git apply --check` OK)。listAllGuides()(静的+DBを結合、例外を投げない)を使い、8秒タイムアウト、失敗時は従来のGUIDESのみに戻す。
- 効果: BF向けガイドをDB経由で公開しても、最大1時間でsitemapに入る。今のsitemapURLは変わらない(0件追加)。直接の流入増は見込まない。
- デメリット: 今は効果ゼロ(AIガイド0件)。/api/guides を毎時1回余分に呼ぶ(Render無料のスリープ起こしの可能性、ISRなので1時間1回)。AIガイドは公開前審査を経ずsitemapに載る(一覧には既に出ている)。テスト・ビルド未実施。元に戻せる、費用0、決裁A相当。工数0.3h。

## (2) P-003 検索表示減(1日43→12)の切り分け
| 要因 | 確認 | 結果 |
|---|---|---|
| robots.txt | curl 200 | 遮断なし(/admin等のみ。Crawl-delay 5はGoogle無視) |
| sitemap | curl 200・520URL | 正常。ガイド14件を含む |
| canonical | guide本番HTML | あり・正しい |
| noindex | guide本番HTML | なし |
| 季節要因 | 事実記録(感謝祭ガイド307→3回) | 約6割を占める。ガイドが終了済みの内容に書き直された(11/1)ことも重なる(推測) |
| インデックス | SC未登録の件数 | **未確認**(SEは取得不可。管理者の共有待ち) |
- 技術面で表示を減らす不具合は見つからない。減少は主に季節要因+検索クエリ側の需要消失とみるのが妥当(推測)。残り4割の内訳(ページ別・クエリ別)はSC画面が必要で**未確認**。
- 測り方: SCのページ別表示を10/12〜25と10/27〜11/8で比べる(管理者に依頼)。

## (3) 日次kpi欠測
11/5以降は毎日json+台帳が揃っている(kpi/2026-11-09.jsonまで)。残件は10/30〜11/4の原因(実行履歴なし、未確認)。新たな材料なし。

## エラー
今週(11/9月曜〜)はまだ0件。先週7件(事実記録)。

使ったスキル:pro-se(rampstack-seo:seo-technical はSkillツールが無く、スキル未取得。pro-seの点検順で代替)
