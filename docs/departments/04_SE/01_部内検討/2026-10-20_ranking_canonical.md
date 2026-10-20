# 2026-10-20 /ranking の canonical(カテゴリ別・自己参照)

## 事実(curl 2026-10-21 0:1x JST、読み取りのみ)
- 主要9URLすべて200。TTFB 0.3〜0.8秒(スリープ明けではない状態)。/ 566KB、/ranking 548KB、/deals 69KB、他は45〜78KB。比較ページは83〜98KB。
- canonical: /(あり、JSON-LD 2)、/deals /compare /brands /guides /faq あり。**/ranking のみ無し**(10/17の監査条件で外した)。
- sitemap.xml 1,155URL(compare 633、products 431、category 43、brand 27、guides 14)。robots.txt は /compare? のみ Disallow で、sitemapの比較ペアは対象外=整合。
- 比較ページ12件抽出: 全て200・canonical自己参照・noindexなし・JSON-LD 1〜2。
- 商品名の日時混入(例「10/4 20:00 10/09 01:59」)が比較URLのslugにまで出ている(titleist…-10-4-20-00-10-09-01-59-professional-tech-tg53-2、titleist-10-9-23-pro-v1…)。未修正。10/11の学びと同件。

## 提案(diff: 2026-10-20_ranking_canonical.patch)
- 対象: frontend/app/ranking/page.tsx の `metadata` を `generateMetadata` に置換。カテゴリ別は自己参照、先頭カテゴリ/不正値は /ranking。10/17の「カテゴリ別が統合されてしまう」懸念を解消。
- 工数: 調べる済・作る済、テスト0.25h、本番確認0.25h。±20%。元に戻せる(1ファイル)、本番データに触れない、日次ジョブと無関係。
- 効果: /ranking?category=X の重複判定を防ぐ。見込み流入は推測不能(未取得)。小さい。測り方: 反映後に curl で canonical 出力を確認、Search Consoleの重複エラー件数。
- 注意: tscの前に `next typegen`。generateMetadata は searchParams が Promise(page.tsxと同形)。

## 次の候補(優先順)
1. 商品名の日時混入の取り込み時整形(比較633ページのURL/タイトルの質、backend側の名前整形)。
2. / と /ranking の約550KB軽量化(商品リストの件数・画像props。RSCペイロード原因は未特定)。
3. 報酬なしリンク373件の形式別集計。

使ったスキル:pro-se(rampstack-seo:seo-technical は未取得につきpro-seの点検順で代替)
