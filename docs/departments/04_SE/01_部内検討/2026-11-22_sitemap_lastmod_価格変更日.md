# 2026-11-22 sitemapの商品lastmodを「実際に価格が変わった日」にする(patch案)

決裁A(元に戻せる・費用0円・本番データは読むだけ)。patch:`04_SE/2026-11-22_sitemap_lastmod_価格変更日.patch`(`git apply --check` 確認済み。テスト・ビルドは未実行)。

## 何を・なぜ
- 事実(curl https://par-gear.com/sitemap.xml、2026-11-22 15:07 UTC取得):586URL。商品494URLのlastmodのうち **489件が2026-11-22、5件が11/21**。つまり全商品が「今日更新」と申告している。
- 原因(推測を含む):`Product.updated_at` は `onupdate=func.now()`(backend/app/models.py 163行)。日次ジョブがyahoo_checked_atなどを書くたびに動く(pipeline.py 407-408行)。価格もカテゴリ・ブランド・固定ページはlastmod無し(45+24+9件)。
- Googleの説明(スキルの要点、公式は未開封):lastmodは「実際の変更を一貫して反映」していないと無視される。全件が毎日同じ日付だと信頼されず、変わったページの再巡回の手がかりにならない(推測)。登録数を増やす=集客の入口に近いが、効果の大きさは未取得。
- 変更:商品のlastmodを「履歴の価格が現在価格と違う最後の記録日時」(=価格が変わった日の前日以内)にする。変わっていない商品はlastmod無し。
  - backend/app/crud.py `list_published_slugs`:グループ化1クエリで price_changed_at を算出(戻りは SitemapProduct)。
  - backend/app/schemas.py `SitemapProduct`:`price_changed_at` 追加(任意)。
  - frontend/lib/api.ts `SitemapProduct` に任意項目、frontend/app/sitemap.ts は `toLastModified(product.price_changed_at)`。
  - backend/tests/test_site_stats.py:2テスト(変更なし→None、価格変更→最後に違った行の日時、同額の追記では動かない)。
- 触らないもの:guides.ts、/popular、ガイドのlastmod(既存の dateModified 対応のまま)。

## デメリット・リスク
- lastmodが付く商品が減る(値下がり・値上がりが一度もない商品は無し)。lastmodが無くてもsitemap・巡回は有効で、失うのは「更新日の申告」だけ(Googleは信頼しない値を無視するので実害は小さい、推測)。
- 価格以外の変更(説明文・画像・AI再生成)はlastmodに出ない。商品ページの本文変化を伝えられない。
- 価格履歴の価格が現在価格と違う行を探す前提。履歴に古い誤記録があると、その日付が出る。
- 1クエリ追加(price_history全件のGROUP BY)。バックエンド(Render無料・スリープ明け)でsitemapは1時間ISRなので負荷は小さい見込みだが、実測は未取得。8秒タイムアウト(sitemap.ts)に収まるか要確認。
- 効果(登録数・表示)が出るのは早くて数日後で、3日の表示44件では判定できない。集客への寄与は推測。

## 確認手順(全体統括)
1. `cd backend && pytest tests/test_site_stats.py tests/test_pipeline.py -q`(テストの前提:create_productが初期価格行を作る。未実行のため要確認)
2. `cd frontend && npx next typegen && npx tsc --noEmit && npm run build`
3. 適用後に `curl -s https://par-gear.com/sitemap.xml | grep -c lastmod` と、日付の分布(今日が489件でなくなること)を確認。`/api/sitemap/products` の応答時間も測る。
4. 1週間後、Search Consoleのsitemap「検出されたURL数」と表示のあるURL数を比べる。

## 元に戻す方法
`git revert` で戻る(DB変更なし・スキーマ変更なし)。

## 週次エラー目標との関係
今夜のerrorは0(前週5)/目標20。Yahoo 429は11/2の記録どおり日1件で余裕あり、変更せず。今夜の増分は0。

## 知識への追記案
- sitemapのlastmodは、全商品が毎日「今日」になっていた(489/494)。updated_atは日次ジョブで動くため。

使ったスキル:pro-se(ファイルで読了)、rampstack-seo:seo-technical(Skillツールが使えず ~/.claude/plugins/.../seo-technical/SKILL.md をファイルで参照。有料ツール前提部分は未使用)
