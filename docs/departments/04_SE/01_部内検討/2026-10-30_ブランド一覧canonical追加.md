# 2026-10-30 /brand/[brand] にcanonicalを追加(技術SEO)
## 事実(確認日 2026-10-30)
- 全page.tsxを照合した結果、canonical未設定でindex対象なのは `frontend/app/brand/[brand]/page.tsx` のみ。他の未設定ページは /admin配下(robots.tsでdisallow)、/alerts/unsubscribe、/search・/finder・/favorites(noindex)。(根拠: grep、frontend/app/robots.ts)
- sitemap.ts は `/brand/<ブランド名>` を載せている(sitemap.ts 142行目)。カテゴリ・商品・/brands・/dealsは設定済み。
- 直近7日 error 7件(目標20件以下は達成中)。(根拠: 2026-10-30_事実.md)
## 変更
- `generateMetadata` に `alternates: { canonical: "/brand/" + encodeURIComponent(name) }` を1行追加。
## 確認
- `npx next typegen` 後 `npx tsc --noEmit`: エラー0件(今回は既知のLayoutProps1件も出なかった)。
## 効果(推測)
- 並べ替え等のクエリ付きURLが評価分散するのを防ぐ。件数・順位への効果は未測定。測り方: Search Consoleの「重複」系の登録状況を2週間後に確認。
## デメリット・リスク
- 低。ブランド名の表記ゆれ(大文字小文字)は統合されない。本番反映は自動取り込み後。元に戻すのは1行削除。
## 未解決候補(今回は未着手)
- トップHTML約570KB、/deals割引率表記の不一致(deals.tsのdropLabel要確認)、「読み込み中…」残存(管理画面中心)、/admin認証有無は未確認。
使ったスキル:pro-se(テクニカルSEOの考え方:rampstack-seo:seo-technical は未取得)
