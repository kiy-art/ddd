# 2026-10-15 一覧系ページのcanonical追加（差分案）

- 部署：04_SE（部内検討）／事業：001_Par.Golf
- 種別：技術SEO改善1件（スキル1章2「登録されるか」）。実装は監査後に全体統括。決裁レベルA相当（費用なし・元に戻せる・本番データに触れない・日次ジョブ6:00と無関係）。

## 1. 事実
- 巡回メモ：一覧系6ページ（/・deals・ranking・brands・guides・faq）で canonical が0件（全て200）。10/11の部内検討でもトップに無いことを確認済み。
- コード：`frontend/app/layout.tsx` は `metadataBase` のみで canonical なし（継承の心配なし）。`privacy`・`popular` は `alternates: { canonical: "/…" }` の書き方で既に実装済み＝既存の書き方に合わせた。
- クエリ違いの重複が起きるページ：`/?buy_score=…`（5タブ、app/page.tsx）、`/ranking?category=…`（app/ranking/page.tsx）。popular は10/〜 X投稿のutm対策で同じ方針（STEP74）。

## 2. 差分（`2026-10-15_一覧系canonical追加.patch`、6ファイル +28/-4）
| ファイル | 変更 |
|---|---|
| `app/page.tsx` | `export const metadata = { alternates: { canonical: "/" } }` を追加（title等はlayoutから継承。タブ違い `?buy_score=` も / に集約） |
| `app/deals/page.tsx` `brands` `guides` `faq` | metadata に `alternates.canonical` を1行追加 |
| `app/ranking/page.tsx` | 静的metadataを `generateMetadata` に変更。有効かつ既定以外のカテゴリは `/ranking?category=<値>`、既定（CATEGORIES[0]）・不正値は `/ranking`。カテゴリごとに別内容なので全部を /ranking に集約はしない |

## 3. 検証（今夜）
- `git apply --check`：作業ツリーに対して OK（コードは変更していない）。
- tsc / lint / build：**未実施**。`frontend/node_modules` が無く、部内検討中は npm 実行禁止のため。レビュー観点：`isCategory` は関数宣言で巻き上げされ generateMetadata から使える／Next.js 16 の `searchParams` は Promise（既存ページと同じ）。実装時に `npx tsc --noEmit` と `npm run lint` を必須にする。
- 本番確認（実装後）：`curl -s https://par-gear.com/{,deals,ranking,ranking?category=<2番目>,brands,guides,faq} | grep -o '<link rel="canonical"[^>]*>'` が各1件で、`?buy_score=strong_buy` でも `/` になること。

## 4. 効果・工数・戻し方
- 効果：6ページ（＋タブ5・カテゴリ違いのクエリURL）の重複URLの統合先を明示。流入への効果は未測定（推測で小）。測り方：Search Consoleの「重複: ユーザーにより選択されたcanonicalがないページ」の件数を実装前後で比較。
- 工数：調べる0.3h（済）／作る0.3h（済）／テスト0.4h／本番確認0.2h＝約1.2h（±40%）。
- 戻し方：`git revert`または `patch -R`。

## 5. エラー件数の内訳の出し方（目標「エラー 週1,000件以下」）
- 事実（依頼文より、今夜の管理API取得）：直近7日 error 7 / warning 248 / info 795（計1,050）。コード上 `ErrorLog` は level（error/warning/info）・source・product_id・message・created_at を持つ（`backend/app/models.py` 248行）。
- 定義の提案：**「エラー」＝level=error のみ**（目標名どおり、7件）。warning・info は「通知」として別管理。計1,050は info（795）の商品別「not found」「price mismatch」ノイズが75%（`routers/admin.py` auto_fix_logs の説明：info/warning は通常のノイズ）。
- 内訳の手順（読むだけ）：`GET /api/admin/logs?limit=50&offset=N` を N=0,50,… で空まで読み、created_at が今週月曜(10/12 0:00 JST、DBはUTCの推測=要確認)以降を、level×source で集計し、message の先頭30字（商品名を除いた型）で上位5を出す。値や認証は記録しない。
- 注意：info/warning は「古いログを整理」と日次ジョブの保持期間で消えるため、7日窓の数は削除の影響を受ける（件数が下がっても改善とは限らない）。毎日同時刻に level別件数を台帳に残すのが確実（`crud.count_error_logs_by_level` を日次記録する案、別件）。
- 今夜は内訳の集計そのものは未実施（管理APIの接続先を本セッションで確認できず）。

## 6. 週エラー数の現在値の推奨
- **採用：level=error の7件**（10/8〜15の7日窓の数字。今週=月曜10/12〜の窓では、これ以下）。理由：目標名が「エラー」、warning/infoは正常系のノイズを含み、混ぜると目標1,000を毎週超えて指標として意味を失う。
- 併記：「通知（warning+info）1,043件」を参考値として別欄に。窓の違い（直近7日 vs 今週）は注記する。

## 7. 過去の試行・市場
- `docs/knowledge/experiments.csv` にcanonical・エラー件数の過去施策はこの検討では未確認（推測せず「未確認」）。市場：プライム感謝祭（10/16〜19）前に重複URLを整理する意味がある（推測）。

## 結果
（実装・本番確認後に追記）

使ったスキル：pro-se（.claude/skills/pro-se/SKILL.md）、rampstack-seo:seo-technical は スキル未取得
