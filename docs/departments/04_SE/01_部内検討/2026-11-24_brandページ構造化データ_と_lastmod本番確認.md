# 2026-11-24 /brand/[brand] の構造化データ追加patch と lastmod 本番確認

決裁A(元に戻せる・費用0円・DB変更なし)。patch:`04_SE/2026-11-24_brand_jsonld.patch`(`git apply --check` 通過。テスト・ビルドは未実行)。

## 1. 前夜適用のlastmod(EXP-034)の本番確認(2026-11-24夜、curl)
- sitemap.xml:200、TTFB 0.55秒、95KB、588URL(商品496・カテゴリ45・ブランド24・ガイド15・トップ系8)。robots.txt 200。
- 商品lastmod:付き261件・無し235件(価格が一度も変わっていない商品)。11/22時点の「494件中489件が当日」から、当日(11/24)28件・11/23 11件・11/22 7件…と50日に分散。直った。
- /api/sitemap/products:200、0.22〜0.52秒(3回)。api側の分布もsitemapと一致(None 235)。
- ガイドは5日に分布(9/22が9件・9/25が3件はpublishedAtのまま。書き直しは反映されない既知の点)。
- 事実:Search Consoleでの検出URL数・再クロールは未取得(次回以降、社長共有の範囲)。

## 2. 点検で見つけた穴:/brand/[brand] にJSON-LDが無い
- 標本(curl 11/24):category・category/x/brand・guides・productsにはBreadcrumbList/ItemList/Article/Productがあるが、/brand/TaylorMade・Srixon・Wilson は構造化データ0件(canonicalは正常)。sitemapに24URL。
- 直し:frontend/app/brand/[brand]/page.tsx に、category/[category]/[brand]/page.tsx と同じ形のBreadcrumbList+ItemListを追加(+約25行・-0行、1ファイル。SITE_URL import追加)。
- 効果の見込み(推測):パンくず表示とリスト理解の補助。流入への直接効果は小さい(24ページ)。ショップクリックへの寄与は未取得・測れない。

## デメリット・リスク
- HTMLが商品数分(ブランドあたり最大数十件)増える。軽微。
- JSON-LDは価格を含めないので景表法上のリスクなし。Productは出さない(一覧に価格を置くと表示中の価格との不一致リスク)。
- レンダリングを変えるのでtsc・buildで要確認。戻し方:git revert(DB変更なし)。

## 全体統括の確認コマンド
1. `cd frontend && npx next typegen && npx tsc --noEmit && npm run build`
2. 適用後 `curl -s https://par-gear.com/brand/Srixon | grep -o '"@type":"[A-Za-z]*"' | sort | uniq -c`(BreadcrumbList・ItemList・ListItemが出る)。
3. 不存在ブランド /brand/zzz が404/noindexのままか(11/11の対応が壊れていないこと)。

## 今週のerror
2件(11/23・11/24のYahoo 429、事実ファイル)/目標20。今夜の増分0。429は上限到達で、warningへ書き換えて隠す変更はしない(11/2記録のとおりself_healがerrorを読む)。
「par-gear.comが検索に出ない」は11/20に確定済みのため、今夜は扱わない。

## 知識への追記案
- sitemap lastmod分布は、適用1日後に当日集中(489/494)→50日分散・235件は無し、応答は0.2〜0.55秒で問題なし。

使ったスキル:pro-se(ファイルで読了)、rampstack-seo:seo-technical(Skillツールが使えず ~/.claude/plugins/ 配下のSKILL.mdをファイルで参照。有料ツール前提部分は未使用)
