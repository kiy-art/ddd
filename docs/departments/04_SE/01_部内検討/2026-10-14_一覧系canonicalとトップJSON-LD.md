# 2026-10-14 一覧系canonicalとトップJSON-LD(技術SEO)

## 成果物
`docs/departments/04_SE/2026-10-14_一覧系canonicalとトップJSON-LD.patch`(unified diff、7ファイル・追加25行、削除0行)

## 内容
- canonicalを追加: `/deals` `/ranking` `/brands` `/guides` `/faq` `/disclaimer`(各 page.tsx の metadata に `alternates: { canonical: "/xxx" }`)。トップ `app/page.tsx` には metadata を新設し canonical `/`。layout.tsx の `metadataBase` があるので絶対URL(https://par-gear.com/...)になる(根拠: next/dist/docs generate-metadata.md 402行、sitemap.ts・layout.tsx)。
- トップに JSON-LD(WebSite+Organization、@graph)。name・urlのみ。ロゴ・sameAs・SearchActionは実体が確認できないため入れない(/searchはnoindex)。新しい外部通信・秘密情報なし。
- 依頼の「8ページ」のうち **`/about` はこのリポジトリに存在しない**(app/about 無し)。実質7ページ。aboutを作るなら別件(内容は事業側の判断)。
- 効果: トップの `/?buy_score=…` 4種を `/` に統合、`/ranking?category=…` 等の絞り込みURLを基準URLに寄せる。重複URLの統合が目的で、流入増の保証はない(推測。Googleは自動でcanonicalを選ぶため、効果は小〜中)。
- 注意: `/ranking?category=x` は絞り込み表示が別内容のため、canonicalを `/ranking` に寄せるとカテゴリ別ビューは単独で登録されにくくなる(カテゴリは `/category/x` が受け皿)。気になるなら ranking だけ外してもよい。

## 検証(リポジトリ外の一時コピー。本体は未変更)
- `git archive HEAD` の一時コピーで `git apply --check` OK。
- `npm ci` → `npx next typegen` → `npx tsc --noEmit` エラー0(typegen前は layout.tsx の `LayoutProps` 未定義の既存エラー=型未生成のため。今回の変更とは無関係)。
- `npx eslint`(変更7ファイル)警告・エラー0。
- 未実施: `next build`、本番表示確認(適用後に curl で `<link rel="canonical">` と `application/ld+json` を確認する)。
- 戻せるか: はい(7ファイルのgit revert)。本番データに触れない。日次ジョブ(6:00)と無関係。工数: 適用・push・本番確認で約30分(±30%)。
- 注意: 本番は10/12・10/13分が未反映(このリポジトリは10/11の状態)。適用は議長がpush可能になってから。

## 比較ページ629件(noindex/sitemap除外の評価だけ。削除・リダイレクトはしない)
現状: `app/sitemap.ts` の pairEntries が、全商品×近い価格帯の2商品(nearestRivals)の組を全部サイトマップに入れる。件数629は2026-10-14のSE確認(common.md)。URLは商品slugの連結なので、slugに型番・セール文言が混ざると長く不安定なURLになる。
- 案A(サイトマップから外すだけ): sitemap.ts の pairEntries を空にする(または上位N件に絞る)。1か所・数行・約1時間。ページ自体は残り、内部リンクから発見・登録はされうる。効果は「Search Consoleの検出・未登録の増加を止める」程度。戻せる。
- 案B(noindex): compare/[pair]/page.tsx の generateMetadata で条件付き `robots: { index:false, follow:true }`(brand×categoryページと同じ書き方。category/[category]/[brand]/page.tsx 75行)。条件は「両商品が公開・価格あり・slugに日付/セール語が無い」など。約2〜3時間(±40%)。登録済みのものがあれば検索から消える=戻しにくい場面あり。
- 判断材料が不足: Search Consoleの「クロール済み・未登録」「検出・未登録」の件数、比較ページ経由の表示・クリックは未取得。先にそれを取る(1回/GSC画面)。
- SE部の推奨(推測): まず案A(サイトマップを、商品ページが上位に来たものの組に絞る)を採用し、GSCの数字を見てから案Bを判断。理由=クリック25のうち比較経由の記録が無く(場所別に「店比較5」はあるが比較ページ経由の流入は未取得)、noindexで失うものが現時点で不明なため。
- 根本対策の候補: 商品名の整形(10/11に確認した日時混入。knowledge.md参照)をslug生成の前で直す。

## 日次ジョブ・エラー件数(目標「エラー週1,000件以下」の定義案)
- 数える対象を **ログレベル error の週(月曜始まり)合計** と定義することを提案。直近7日は error 7(common.md、2026-10-14 15:01 UTC)で目標1,000の0.7%。warning 253 は別枠で監視(日次ジョブのスキップ=楽天151・Yahoo!627 が主因か。推測、内訳は未取得)。
- 「週1,000件以下」は現状の約140倍の余裕があり、目標として緩すぎる。会議で「error 週20件以下」等への引き下げを提案したい。

## 会議に出したい件
1. 比較ページ629件の扱い: まずサイトマップを絞る(案A)でよいか。社長承認は不要(費用なし)だが、noindex(案B)は戻しにくいので決裁レベルを議長に相談。
2. SE目標「エラー週1,000件以下」の定義(error のみ・月曜始まり)と、水準の引き下げ。
3. `/about` ページが存在しない。作るなら内容・運営者表記(特商法・運営者情報)は他部署と法務確認が必要。
4. 本番反映の遅れ(10/12・10/13分がpush不可)。canonical/JSON-LDの効果は反映後でないと測れない。

測り方: 適用後、GSCの「ページのインデックス登録」で「重複しています。ユーザーにより、正規ページとして選択されていません」「代替ページ(適切な canonical タグあり)」の件数を適用の前後1〜2週で比べる。

使ったスキル:pro-se(プラグインスキル rampstack-seo:seo-technical は未取得)
