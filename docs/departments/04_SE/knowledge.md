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

## 代表者会議から持ち帰ったこと

## スキル改善メモ
（専門スキル `.claude/skills/pro-se/SKILL.md` で足りなかった点。月1回、人事部が改訂案にまとめる）
- 2026-10-11 [001] 1章3「正しく読めるか」に、数値の演出（カウントアップ等）の初期値がHTMLに出る落とし穴が無い → 「curlで取ったHTMLで数値・スコアが0や空でないか」を点検項目に足す(根拠: 01_部内検討/2026-10-11_トップ数値の初期表示修正.md)
- 2026-10-17 [001] 点検項目に「canonical未設定ページの一覧(grepで全page.tsxを照合)」と「tsc前のnext typegen」が無い → 1章2に足す(根拠: 2026-10-17_canonical追加.md)

- 2026-10-18 [001] 管理系ページがnoindexか・公開ナビに管理リンクが無いかの点検が無い → 1章1に「robots disallowだけでなくnoindexと公開リンクの有無」を足す(根拠: 2026-10-18_管理画面リンク除去.md)

使ったスキル:pro-se
