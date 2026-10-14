# 04_SEのナレッジ

1行1件。`- YYYY-MM-DD [事業番号] 内容(根拠: 出典)`。推測は「推測」と書く。古くなった行は消さずに打ち消し線を引く。

## 部署の学び
- 2026-10-11 [001] "use client"の部品もサーバーで先にHTMLになるため、useStateの初期値（例：CountUpの0）がそのままHTMLに出る。数値は初期値を実数にし、演出は後から動かす(根拠: curl https://par-gear.com/ で掲載商品0・スコア0が64か所、next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md 109行)
- 2026-10-11 [001] 商品名に「10/4 20:00 10/09 01:59」の日時混入を確認（タイトリスト PROFESSIONAL TG73 グローブ、name・ai_title・alt）。取り込み時の名前整形が次の不具合候補(根拠: curl https://par-gear.com/ 2026-10-12 00:17 JST)
- 2026-10-11 [001] トップに canonical と JSON-LD が無い（商品ページにはある）(根拠: curl https://par-gear.com/ のHTML)

- 2026-10-14 [001] リポジトリに /about ページが無い(依頼は一覧系8ページだが実在は7)。canonical/JSON-LD は metadata の alternates と page内scriptで足せる(根拠: frontend/app 一覧、2026-10-14 パッチ検証)
- 2026-10-14 [001] 型チェックは `npx next typegen` を先に実行しないと layout.tsx の LayoutProps が未定義エラーになる(根拠: 一時コピーでの tsc 結果)
- 2026-10-14 [001] 直近7日ログ error 7 / warning 253。目標「エラー週1,000件以下」は余裕が約140倍で緩い(根拠: 管理API 2026-10-14 15:01 UTC)

## 代表者会議から持ち帰ったこと

## スキル改善メモ
（専門スキル `.claude/skills/pro-se/SKILL.md` で足りなかった点。月1回、人事部が改訂案にまとめる）
- 2026-10-11 [001] 1章3「正しく読めるか」に、数値の演出（カウントアップ等）の初期値がHTMLに出る落とし穴が無い → 「curlで取ったHTMLで数値・スコアが0や空でないか」を点検項目に足す(根拠: 01_部内検討/2026-10-11_トップ数値の初期表示修正.md)
