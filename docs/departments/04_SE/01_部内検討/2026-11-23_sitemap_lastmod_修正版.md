# 2026-11-23 sitemap lastmod patch の修正版(再提出)

決裁A(元に戻せる・費用0円・DB変更なし)。patch:`04_SE/2026-11-23_sitemap_lastmod_価格変更日_修正版.patch`(`git apply --check` 通過。テスト・ビルドは未実行)。

## 差し戻し理由について
自部署の記録(11/22記録・knowledge.md)に、監査の差し戻し理由の記載は無い(未取得)。そのため、旧patchを自分で読み直して見つけた弱点を直した。理由が別にあれば、全体統括から教えてほしい。

## 旧patch(11/22)の弱点と直し
1. **日付が1日ずれる**:旧版は「現在価格と違う最後の履歴行」の日時=変更の**前**の記録日を出していた。修正版は「その後で最初に記録された行」=変更を観測した日にした(crud.py list_published_slugs、集計2回)。A→B→A と戻った場合も、戻った日が出る。
2. **テストが不安定**:旧テストは初期行の時刻(実行時の now)と先頭19文字を比べ、同一秒の記録に依存した。修正版は recorded_at を固定日付で与え、「変更あり」「同額の追記では動かない」「変更なし→None」「価格が元に戻る」の4場面を決め打ちで確認する(test_site_stats.py、新規2テスト)。
3. 変えていない所:schemas.SitemapProduct の任意項目 price_changed_at、frontend/lib/api.ts の任意項目、frontend/app/sitemap.ts の `toLastModified(product.price_changed_at)`(旧と同じ)。

## 効果の見込み(推測)
- 事実:11/22時点で商品494件中489件のlastmodが当日(旧記録 curl sitemap 11/22)。直す=lastmodが実際の価格変更日だけになる。Googleはlastmodが実態を反映していないと無視すると説明されている(スキルの要点。公式原文は今夜開いていない)。
- 登録数・表示への効果は未取得。集客への直接の寄与は小さい見込み(推測)。週error目標への影響は0。

## デメリット・リスク
- 価格が一度も変わらない商品はlastmod無しになる(失うのは更新日の申告のみ)。価格以外の更新(説明・画像・AI再生成)は出ない。
- クエリは旧版の1回から2回に増える(price_history全件の集計×2)。Render無料のスリープ明けで、sitemap.tsの8秒タイムアウトに収まるかは本番未計測。1時間ISRなので失敗しても前回のsitemapが残る設計。
- 履歴に古い誤記録(別店の価格など)があると、その日付が出る。
- 日次ジョブ(6:00)とは独立(読み取りのみ)。

## 全体統括の確認コマンド
1. `cd backend && pytest tests/test_site_stats.py tests/test_pipeline.py -q`(add_priceに過去のrecorded_atを渡すテストあり。analyze_pricesが過去日付でも通るかは未実行のため要確認)
2. `cd frontend && npx next typegen && npx tsc --noEmit && npm run build`
3. 適用後 `curl -s https://par-gear.com/sitemap.xml | grep -c lastmod` と日付の分布(489件が当日でなくなること)、`/api/sitemap/products` の応答時間。
4. 1週間後、Search Consoleのsitemap「検出されたURL数」を前後比較(社長共有の範囲)。
戻し方:`git revert`(DB・スキーマ変更なし)。

## 巡回メモの扱い(site:検索)
「site:」の検索は今夜で閉じる。11/20社長共有のSearch Consoleで「検索減は季節需要」と確定済み。今夜はコード(sitemap.ts・crud.py)の確認に切り替えた。

## 今週のerror
11/23のYahoo 429の1件(事実ファイル、管理API logs)/目標20。今夜の増分0。

## 知識への追記案
- lastmodの日付は「変更の前の記録」でなく「変更を観測した記録」にする。時刻依存のテストは日時を固定して書く。

使ったスキル:pro-se(ファイルで読了)、rampstack-seo:seo-technical(Skillツールが使えず ~/.claude/plugins/ 配下のSKILL.mdをファイルで参照。有料ツール前提部分は未使用)
