# 2026-11-06 ブランドページのcanonical追加案 と「検索に出ない」技術調査

## 成果物
`2026-11-06_brand_canonical.patch`(frontend/app/brand/[brand]/page.tsx の generateMetadata に alternates.canonical を1行追加)。
一時worktreeに当て、`npx next typegen` → `npx tsc --noEmit` はエラー0。worktreeは削除済み(作業ツリーは未変更)。pytestは変更がbackend外のため未実行。

## 調査結果(事実。curl 2026-11-06 15:04Z)
- robots.txt: 200。`Allow: /`、Disallow は /admin /alerts /search /finder /compare? と sort/tab付きURLのみ。Sitemap行あり。トップを塞ぐ記述なし。
- sitemap.xml: 200、521URL(商品433・brand24・category42・guides15・固定ページ)。商品433は公開商品数と一致。
- トップ: 200、`<link rel="canonical" href="https://par-gear.com">`、robots meta無し、X-Robots-Tagヘッダ無し、JSON-LD(WebSite・Organization)あり。
- 標本9URL(商品3・カテゴリ2・deals・ranking・guides)すべて 200・canonical有・noindex無し。TTFB 0.26〜0.48秒。商品はProduct/AggregateOffer/BreadcrumbList、カテゴリはItemList/BreadcrumbList。
- http→https は 301。www.par-gear.com はこの環境のプロキシが403を返し判定不能(未確認)。
- 結論:noindex・canonical誤り・sitemap欠落・robots遮断のいずれも見当たらない。「site:で出ない」は技術要因より、ドメインが新しく評価待ち(推測)の可能性が高い。Search Consoleで表示13・平均順位5.5(事実資料)は、インデックス自体はされていることを示す。site:検索の未表示だけでは不具合と判断しない。

## 見つかった不具合
- /brand/[brand] だけ canonical が無い(curl /brand/Titleist、全page.tsx照合でも当該ファイルのみ。admin・search・finder等はnoindex想定で対象外)。sitemapに24URL載っている。
- 効果:重複統合の保険。流入増の見込みは小さい(推測)。測り方:デプロイ後 curl で canonical有を確認、Search Consoleの「重複」系の件数を2週後に比較。
- 工数:作る0.1h+テスト0.2h+本番確認0.1h=約0.4h(±30%)。元に戻せる・本番データ非接触・日次ジョブ6:00と無関係。決裁レベルA相当(費用0円)。
- 注意:日本語ブランド名は encodeURIComponent でエンコードして出る(sitemapの形式と一致)。

## デメリット/確認したこと
- brand別の効果は小さく、集客の主因ではない。優先度は低め。
- 確認:sitemapのbrand URLは英字表記で、エンコード差による不一致は標本で無し。日本語名ブランドは未確認。

## 目標の進み
エラー(level=error)週: 事実資料では7件(目標20以下)。kpi欠測日の原因は11/5記録済(11/4分)。他日は未確認のまま。

## 会議に出したい件
「site:par-gear.com」未表示は技術要因が見当たらない。SC基準で判断し、site:検索の巡回を指標から外す提案。

使ったスキル:pro-se(担当スキル rampstack-seo:seo-technical は未取得、pro-seの点検順で代替)
