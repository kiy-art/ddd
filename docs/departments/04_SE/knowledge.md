# 04_SEのナレッジ

1行1件。`- YYYY-MM-DD [事業番号] 内容(根拠: 出典)`。推測は「推測」と書く。古くなった行は消さずに打ち消し線を引く。

## 部署の学び
- 2026-10-11 [001] "use client"の部品もサーバーで先にHTMLになるため、useStateの初期値（例：CountUpの0）がそのままHTMLに出る。数値は初期値を実数にし、演出は後から動かす(根拠: curl https://par-gear.com/ で掲載商品0・スコア0が64か所、next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md 109行)
- 2026-10-11 [001] 商品名に「10/4 20:00 10/09 01:59」の日時混入を確認（タイトリスト PROFESSIONAL TG73 グローブ、name・ai_title・alt）。取り込み時の名前整形が次の不具合候補(根拠: curl https://par-gear.com/ 2026-10-12 00:17 JST)
- 2026-10-11 [001] トップに canonical と JSON-LD が無い（商品ページにはある）(根拠: curl https://par-gear.com/ のHTML)
- 2026-10-15 [001] 一覧系6ページのcanonical差分を作成。タブ・カテゴリ等のクエリ違いは集約先を内容で分ける（ranking?category=は別canonical、/?buy_score=は/に集約）。週エラー数は level=error のみを採用し、warning/infoは通知として別欄(根拠: 01_部内検討/2026-10-15_一覧系canonical追加.md、backend/app/models.py ErrorLog)

- 2026-10-14 [001] リポジトリに /about ページが無い(依頼は一覧系8ページだが実在は7)。canonical/JSON-LD は metadata の alternates と page内scriptで足せる(根拠: frontend/app 一覧、2026-10-14 パッチ検証)
- 2026-10-14 [001] 型チェックは `npx next typegen` を先に実行しないと layout.tsx の LayoutProps が未定義エラーになる(根拠: 一時コピーでの tsc 結果)
- 2026-10-14 [001] 直近7日ログ error 7 / warning 253。目標「エラー週1,000件以下」は余裕が約140倍で緩い(根拠: 管理API 2026-10-14 15:01 UTC)
- 2026-10-16 [001] 一覧系8ページ(brands/compare/deals/faq/guides/ranking/contact/disclaimer)にcanonicalが無かったため追加。新規ページ作成時はmetadataにalternates.canonicalを入れる(根拠: frontend/app/各page.tsx、01_部内検討/2026-10-16_一覧系8ページcanonical追加.md)
- 2026-10-17 [001] 一覧系ページ(/, deals, ranking, brands, guides, faq, compare, contact, disclaimer, brand/[brand])はcanonical未設定だった。商品・カテゴリ・ガイド詳細・比較ペアなどは設定済み。layout.tsxに置くと未設定ページが「/」を指すため各ページに置く(根拠: frontend/app の grep、01_部内検討/2026-10-17_canonical追加.md)
- 2026-10-17 [001] `tsc --noEmit` は `next typegen` を先に実行しないと layout.tsx の LayoutProps で既存エラーが出る。検証時は区別する(根拠: 作業コピーで npm ci 後に実行)
- 2026-10-17 [001] /ranking?category= はカテゴリごとに内容が違う。canonicalを/rankingに固定するとカテゴリ別が統合されるため、要判断(根拠: frontend/app/ranking/page.tsx 139-143行)
- 2026-10-19 [001] クライアントlayout配下(/admin)のnoindexは next.config.ts の headers() で X-Robots-Tag を付けるのが最小。robots Disallow と併用するとGoogleがヘッダを読めない点に注意(根拠: 01_部内検討/2026-10-19_admin_noindexヘッダ.md、dev server curl)
- 2026-10-20 [001] /rankingのみcanonical無し(他の一覧系は反映済)。generateMetadataでカテゴリ別自己参照にするdiffを作成。比較ページのslugにも日時混入が残る(根拠: curl par-gear.com、01_部内検討/2026-10-20_ranking_canonical.md)
- 2026-10-21 [001] 直近7日error 6件は全て同一原因(Yahoo APIのAppID総回数上限429、日次ジョブで1日1件)。件数は目標(週20)内だが、Yahoo更新が1日14件前後で全商品に回るのに約48日(推測)(根拠: 管理API /api/admin/logs 2026-10-21、01_部内検討/2026-10-21_商品タイトル最安値表現.md)
- 2026-10-21 [001] 商品ページ429件のtitleに「買い時・最安値比較」、descriptionに「最安値と割引率」。比較は楽天・Yahoo!の2店のみで景表法上の懸念。差分を作成(根拠: curl par-gear.com/products/*、frontend/lib/productSeo.ts)
- 2026-10-21 [001] 公開商品429件のリンク内訳: 楽天アフィURLあり421/なし8、Yahoo!(VC)あり303/なし126、公式サイト等45(うち4件example.com)。営業の「373件」は再現できず定義の確認が必要(根拠: /api/products 2026-10-21)
- 2026-10-21 [001] curlはこの環境で使え、sitemap1,152URLの標本18件はすべて200・canonicalあり。compareのslug/titleに日時混入96件(根拠: curl par-gear.com/sitemap.xml)
- 2026-10-22 [001] EXP-008の「悪化」=施策前7日と後7日の商品群ショップクリック合計が-10%以下。上位クリックを選んで比べるため平均への回帰で悪化が出やすく、対照も無いので判定不能(推測)。停止はフラグ homepage_reorder_enabled(既定False)の差分で、一時コピーpytest全564件合格(根拠: content_optimizer.py 675-703行、01_部内検討/2026-10-22_EXP-008停止.md)
- 2026-10-22 [001] 本番の注目ギアは1商品のみで、product_urlがexample.comの表記(根拠: curl /api/homepage/trending 2026-10-23)
- 2026-10-23 [001] gitの履歴は10/18の1コミットにまとまり、それ以前のrobots/sitemap/canonicalの反映日はコードから確定できない。sitemapは1,154URL(比較639)で10/17会議の比較除外は未実施。商品ページは約39KB(gzip)、応答開始0.6秒(根拠: git log、curl par-gear.com 2026-10-23)

## 代表者会議から持ち帰ったこと
- 2026-10-21 [001] 10/17会議: canonical差分はbuild確認と/ranking?categoryの扱い決定が条件、営業の373件の内訳(クリック数順)をSEに依頼、比較ページのSCクリック取得(根拠: 議事録 2026-10/2026-10-17.md 43・90-92行)

## スキル改善メモ
（専門スキル `.claude/skills/pro-se/SKILL.md` で足りなかった点。月1回、人事部が改訂案にまとめる）
- 2026-10-11 [001] 1章3「正しく読めるか」に、数値の演出（カウントアップ等）の初期値がHTMLに出る落とし穴が無い → 「curlで取ったHTMLで数値・スコアが0や空でないか」を点検項目に足す(根拠: 01_部内検討/2026-10-11_トップ数値の初期表示修正.md)
- 2026-10-17 [001] 点検項目に「canonical未設定ページの一覧(grepで全page.tsxを照合)」と「tsc前のnext typegen」が無い → 1章2に足す(根拠: 2026-10-17_canonical追加.md)

- 2026-10-18 [001] 管理系ページがnoindexか・公開ナビに管理リンクが無いかの点検が無い → 1章1に「robots disallowだけでなくnoindexと公開リンクの有無」を足す(根拠: 2026-10-18_管理画面リンク除去.md)

- 2026-10-21 [001] title/descriptionの言い切り(最安値等)の点検、sitemap標本抽出の手順が無い → 1章に足す(根拠: 2026-10-21_商品タイトル最安値表現.md)

使ったスキル:pro-se
