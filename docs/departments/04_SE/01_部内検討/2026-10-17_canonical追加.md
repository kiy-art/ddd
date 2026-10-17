# 2026-10-17 一覧系ページにcanonicalを追加(レベルA・パッチのみ、未適用)

使ったスキル:pro-se(1章2「登録されるか」)。rampstack-seo:seo-technical はスキル未取得。

## 何を
`frontend/app/` の次のページのmetadataに `alternates: { canonical: "<自分のパス>" }` を追加(10ファイル、+15行)。
`/`(page.tsx。metadata新設)、`/deals`、`/ranking`、`/brands`、`/guides`、`/faq`、`/compare`、`/contact`、`/disclaimer`、`/brand/[brand]`(generateMetadata内、`encodeURIComponent`で商品ページ・サイトマップと同じ形)。
現コードで確認した結果:商品・カテゴリ・ガイド詳細・比較ペア・/popular・/privacyには既にあり、上記は未設定だった(「追加済み」は一部ページのみ)。layout.tsxには置かない(置くと個別指定の無いページが「/」を指してしまうため)。

## なぜ
`/?utm_*`、`/?tab=`、`/ranking?category=`、`/compare?slugs=` など、同じページが複数URLで届く。canonicalが無いと重複として別扱いされ、評価が分散する(スキル1章2、Google「canonical」。一次情報の再確認は今夜未実施)。X投稿のutm付きリンクも「/」に統合される。
見込み効果:URLが何件統合されるかは未取得(Search Consoleの数値なし)。流入への直接効果は小さいが工数は小さい(推測)。
注意:`/ranking?category=` の各カテゴリ表示も `/ranking` に統合される。カテゴリ別をそれぞれ検索に出したいなら別案(カテゴリごとにcanonical)にすべき。要判断。

## 検証
- `npm ci` 成功。`npx tsc --noEmit`:変更起因のエラーなし。残る1件は `app/layout.tsx` の `LayoutProps` 未解決(`next typegen`未実行による既存の事象。変更とは無関係)。
- `npx eslint`(変更ファイルのみ):エラーなし。
- 未検証:`next build`、本番HTMLでの `<link rel="canonical">` 出力、Search Consoleでの反映。適用後に `curl -s https://par-gear.com/deals | grep canonical` で確認する。バックエンドは未変更。

## 適用方法
全体統括が監査後に `git apply docs/departments/04_SE/01_部内検討/2026-10-17_canonical追加.patch`。日次ジョブ(6:00)とは無関係、元に戻せる(revertのみ)。工数:適用と確認で約30分。

## 提案のみ(レベルB・今夜は未着手)
比較ページがサイトマップの629/1,143件を占め、URLにセール文言が混入している件は、薄い/重複のおそれ。サイトマップから除外するかnoindexにする判断は、構造変更を伴うため別議題にする。
