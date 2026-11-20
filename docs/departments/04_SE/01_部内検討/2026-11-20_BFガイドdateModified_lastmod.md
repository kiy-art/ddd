# 2026-11-20 BFセールガイドの技術SEO点検(P-010の技術面)と dateModified / lastmod の修正patch

対象:/guides/prime-appreciation-sale-2026-golf(slug据え置き)。タイトル・説明文の文言はマーケ担当のため触らない。

## 結論
- 見つかった問題は1つ:**本文を更新しても dateModified と sitemap の lastmod が公開日(2026-11-08)のまま**。patchで直す。他の点検項目(title・description・canonical・OGP・Article/BreadcrumbList)は、コード上は問題なし。
- 効果の見込み:Googleに「11/18・11/19に日程を更新した」と伝わり、再クロールの目安になる。ただし lastmod・dateModified は再クロールの**ヒント**で、順位や表示回数が増える保証は無い(推測)。計測:Search Consoleのサイトマップ画面とURL検査で最終クロール日を、patch適用後の数日で見る(未取得)。

## 根拠(コードの行)
- frontend/lib/guides.ts 61行:publishedAt: "2026-11-08"。Guide型(18〜33行)に更新日の項目が無い。
- 同ファイル 50〜55行のコメントで、本文は11/18(EXP-026 楽天公式日程)・11/19(EXP-028 Amazon公式日程)に書き換え済みと分かる。git log:1bc15a6(11/19)・ffe70d5(11/18)が lib/guides.ts を変更。
- frontend/app/guides/[slug]/page.tsx 86〜87行:datePublished も dateModified も guide.publishedAt。
- frontend/app/sitemap.ts 101行:lastModified: toLastModified(guide.publishedAt)。
- 11/10記録では本番sitemapのBFガイド lastmod は 2026-11-08(2026-11-10_BFガイドsitemap確認_と_P003原因切り分け.md)。

## 点検結果(コード読み取りのみ。今夜はcurlで本番HTMLを再取得していない=未確認)
| 項目 | 結果 |
|---|---|
| title / description | generateMetadata(page.tsx 54〜69行)で guide.title / description を使用。問題なし |
| canonical | alternates.canonical に自身のURL(SITE_URL+slug)。問題なし |
| OGP | type=article・url・title・description。**og:imageはページ側で指定なし**。同フォルダの opengraph-image.tsx が自動で付く(ファイルは存在、出力は今夜未確認) |
| Twitter | summary_large_image。問題なし |
| 構造化データ | Article(author/publisher=Organization)・BreadcrumbList。Articleに image が無い(任意項目だがリッチリザルトの推奨。今回は変更せず、候補) |
| dateModified | **要修正(下記)** |
| sitemap lastmod | **要修正(下記)** |

## 変更内容(patch:2026-11-20_BFガイドdateModified_lastmod.patch、3ファイル・各1〜数行)
1. frontend/lib/guides.ts:Guide型に任意項目 updatedAt を追加。BFガイドに updatedAt: "2026-11-19"。
2. frontend/app/guides/[slug]/page.tsx:dateModified を guide.updatedAt ?? guide.publishedAt に。
3. frontend/app/sitemap.ts:lastModified を toLastModified(guide.updatedAt ?? guide.publishedAt) に。
- updatedAt が無い他のガイドは従来どおり(挙動不変)。AIガイド(DB)は項目なしで従来どおり。
- 画面の表示(公開日の表示)・文言は変えない。`git apply --check` は成功済み(適用はしていない)。テスト:フロントにテスト基盤が無く、patchにテストは含めない。確認は tsc と build。

## デメリット・リスク
- updatedAt は**手で更新する**項目。本文を変えるたびに日付を上げ忘れると今回と同じ状態に戻る(運用の穴は残る)。ガイド更新の依頼文に「updatedAtも更新」と書くのが必要。
- 内容の実質的な変更が無いのに日付だけ上げると、Googleに無視される恐れがある。上げるのは本文を実際に変えた時だけ。
- 今回の 2026-11-19 は「EXP-026・028の本文変更日」で、コードコメント・git logに基づく。公開ページ上の「公開日」表示は11/8のままなので、読者には更新日が見えない(見せるかはマーケ・Webデザインと相談。今回はやらない)。
- 12/1以降に改題する時(方針:同じURLで改題)は、その都度 updatedAt を上げる必要がある。
- できなくなること:無し(元に戻せる。1つのpatchを逆適用するだけ。費用0円、本番データに触れない、日次ジョブと無関係。レベルA)。

## 工数(推測)
調べる0.5h・作る0.2h・テスト(tsc・build)0.3h・本番確認(sitemap.xml の lastmod と、ページの JSON-LD の dateModified)0.2h。合計約1.2h(±30%)。

## 確認方法(全体統括が適用後)
1. cd frontend && npx next typegen && npx tsc --noEmit(既知1件以外が増えないこと)、npm run build。
2. 本番で `curl -s https://par-gear.com/sitemap.xml` のBFガイド行の lastmod が 2026-11-19 になっていること(sitemapは1時間ごとに再生成、revalidate=3600)。
3. `curl -s https://par-gear.com/guides/prime-appreciation-sale-2026-golf` の JSON-LD に "dateModified":"2026-11-19" があること。
4. 判定:11/27(P-010の判定日)にSearch Consoleでこのページの表示・クリックを見る(ただし本patchだけの効果は切り分けられない)。

## 自部署の目標(error 週20件以下)との関係
今週4件(Yahoo 429のみ。2026-11-20_事実.md)。今夜はerror件数を動かす変更なし(増分0)。429を想定内扱いにする案は次回に回す。理由:目標には余裕があり、今夜は集客(技術SEO)を優先した。ただし429は毎日1件のerrorで、ログの意味が薄れる点は残る。

## 会議に出したい件(11/21)
- ガイドを書き換える依頼には「updatedAtを更新する」を必ず入れる運用にしてよいか(上げ忘れ防止)。
- 公開ページに「最終更新日」を表示するか(読者向けの信頼性。Webデザイン・マーケ判断)。

## 知識への追記案
- ガイドの更新日は手動項目。更新時は updatedAt を上げる(knowledge.md に追記済み)。

使ったスキル:pro-se、rampstack-seo:seo-technical(Skillツール無し。~/.claude/plugins の SKILL.md をファイルで参照。6層のうち 1・2・5・6 をコードで点検、レポート様式はpro-seの形式に簡略化)
