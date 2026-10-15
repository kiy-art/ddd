# 04_SEのナレッジ

1行1件。`- YYYY-MM-DD [事業番号] 内容(根拠: 出典)`。推測は「推測」と書く。古くなった行は消さずに打ち消し線を引く。

## 部署の学び
- 2026-10-11 [001] "use client"の部品もサーバーで先にHTMLになるため、useStateの初期値（例：CountUpの0）がそのままHTMLに出る。数値は初期値を実数にし、演出は後から動かす(根拠: curl https://par-gear.com/ で掲載商品0・スコア0が64か所、next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md 109行)
- 2026-10-11 [001] 商品名に「10/4 20:00 10/09 01:59」の日時混入を確認（タイトリスト PROFESSIONAL TG73 グローブ、name・ai_title・alt）。取り込み時の名前整形が次の不具合候補(根拠: curl https://par-gear.com/ 2026-10-12 00:17 JST)
- 2026-10-11 [001] トップに canonical と JSON-LD が無い（商品ページにはある）(根拠: curl https://par-gear.com/ のHTML)
- 2026-10-15 [001] 一覧系6ページのcanonical差分を作成。タブ・カテゴリ等のクエリ違いは集約先を内容で分ける（ranking?category=は別canonical、/?buy_score=は/に集約）。週エラー数は level=error のみを採用し、warning/infoは通知として別欄(根拠: 01_部内検討/2026-10-15_一覧系canonical追加.md、backend/app/models.py ErrorLog)

## 代表者会議から持ち帰ったこと

## スキル改善メモ
（専門スキル `.claude/skills/pro-se/SKILL.md` で足りなかった点。月1回、人事部が改訂案にまとめる）
- 2026-10-11 [001] 1章3「正しく読めるか」に、数値の演出（カウントアップ等）の初期値がHTMLに出る落とし穴が無い → 「curlで取ったHTMLで数値・スコアが0や空でないか」を点検項目に足す(根拠: 01_部内検討/2026-10-11_トップ数値の初期表示修正.md)
