# 2026-11-26 BFガイドのAmazon確認日更新とX投稿案(マーケティング部 部内検討)

- その回の日付:2026-11-26(木)。代表者会議なし。決裁レベル:A(費用0円・patchを逆適用すれば戻せる)。
- 成果物:`2026-11-26_BFガイドAmazon確認日更新.patch`(frontend/lib/guides.ts のみ。BFガイド `prime-appreciation-sale-2026-golf` のAmazon箇所)。
- 位置づけ:11/25会議で決まった今夜のガイド変更枠(1日1件)。

## 1. 目標との関係(窓・出典・式)
| 数字 | 値 | 窓 | 出典 | 式 |
|---|---|---|---|---|
| 直近30日ショップクリック | 11 | 11/27 00:03 JST の30日前〜同時刻 | kpi/2026-11-27.json `shop_clicks.last_30d`、kpi_ledger.csv 11/27行 | backend/app/kpi.py `d30 = now - 30日` |
| 今月(11月)のショップクリック | 10 | 11/1行→11/27行 | kpi_ledger.csv | 42 − 32 = 10 |
| 11/30=30までの必要数 | あと20件 | 11/27〜11/30の4日 | 同上 | 11/30夜(12/1 0時台実行と仮定)の30日窓はほぼ11月分だけ → 30 − 10 = 20。20 ÷ 4日 = 5件/日 |
| 直近7日 | 2件 | 11/20〜11/26(11/27行) | kpi_ledger.csv 11/27行 | 2 ÷ 7 = 約0.29件/日 → 必要ペースは約17倍(5 ÷ 0.29) |
| BFガイドの検索表示 | 14日169回(前14日13回)、検索クリック8 | 受信箱の記載の窓(14日) | 事実.md 受信箱2(PDCA-2026-11-26) | — |
| ガイド経由ショップクリック | 累計0 | 累計 | 事実.md(guide_card・guide_end 押下0) | — |

- 結論:11/30=30は届かない見込み(上の算術による。「推測」ではなく、直近ペースが続く前提の計算)。今夜のpatchはクリック増を見込まない(見込み+0件。表記の正確さが目的。EXP-031と同じ扱い)。

## 2. 原文の確認(今夜やったこと)
| 対象 | 方法 | 結果(2026-11-26 15時台UTC=11/27 0時台JST) |
|---|---|---|
| https://www.aboutamazon.jp/news/retail/amazon-black-friday-2026 | WebFetch | 名前解決エラー(ENOTFOUND)。開けず |
| 同上 | curl | CONNECT 403(プロキシで拒否)。開けず |
| https://press.aboutamazon.com/jp/2026/11/black-friday-2026 | curl | CONNECT 403。開けず |
| https://www.phileweb.com/news/hobby/202611/19/8720.html(報道) | WebFetch | 名前解決エラー。開けず(ここでほかのサイトを試すのはやめた) |
| WebSearch「Amazon ブラックフライデー 2026 先行セール 11月27日 本セール 12月7日 aboutamazon.jp」 | 検索結果 | 先行 11/27 0:00〜11/29 23:59、本セール 11/30 0:00〜12/7 23:59(8日間、先行込み11日間)。見出し:phileweb「Amazon、恒例『ブラックフライデーセール』11/30より開催。11/27から先行セール」(URLの日付 2026/11/19)、Impress Watch「Amazonブラックフライデー、27日から先行セール開始 400万点が特価の11日間」。aboutamazon.jp の公式ページは、今夜の検索結果には出なかった |

- 判断:原文の本文を開けなかったので、**「原文ページは開いていません」の注記は残し、確認日だけ 11/24 → 11/26 に更新**した(依頼の条件どおり)。Yahoo!・楽天の注記は変えていない。
- ポイント(要エントリー・合計1万円以上・上限1万pt)は、巡回メモと検索要約だけが根拠で本文未確認のため、ガイドに入れていない。
- 作業環境の注記:原文の確認には、セッションのネットワーク設定で www.aboutamazon.jp(または press.aboutamazon.com)を許可する必要がある。

## 3. patchの中身(差分3か所)
1. 日程の節のAmazon段落:「(11月24日時点の確認。…原文ページは開いていません。…)」→「(11月26日時点の確認。…原文ページは開いていません。…)」。ほかの文は同じ。
2. よくある質問のAmazonの答え:「(検索結果で確認。…)」→「(11月26日時点、検索結果で確認。…)」。
3. 先頭コメントに 2026-11-26 の行を追加(原文が開けなかったこと、注記を残したこと、updatedAt を動かさないこと)。
- updatedAt は 2026-11-25 のまま。確認日だけの変更で本文の内容は変わらないため、更新日(JSON-LD dateModified・sitemap lastmod、EXP-030)を新しくしない(推測:中身の変わらない日付更新は再巡回の手がかりとして弱く、誤解のもとになる)。
- 確認:`git apply --check` 成功(作業ツリーの現状に対して)。11/28予定の `2026-11-25_冬ボールガイドv3.patch` を先に当てた後でも `--check` 成功(別ガイドの箇所なので順番に依存しない)。
- 「最安」「強い買い時」・取り消し線は使っていない。
- seo-onpageの8項目で見たこと:1 title・2 description・3 見出し・7 URLは変えない(P-013で変えたばかりで、EXP-036の測定中)。4 本文は確認日だけ。5 内部リンク・6 画像は対象外。8 構造化データ:FAQPageを出しているのは frontend/app/faq/page.tsx だけで、ガイドのFAQ文は構造化データに入っていない(grep「FAQPage」で確認)。dateModifiedは updatedAt を動かさないので変わらない。
- 適用時刻の条件:なし(いつ当てても文は正しい)。ただし12/8の改題(TODO)より前に当てること。

## 4. デメリット・リスク(メリットと同じ重さで)
- メリット:Amazon先行セールが始まる時点の確認日が本文に出る。読者が「いつ確かめた日程か」を見られる。費用0円。
- デメリット1:クリック増は見込めない(見込み+0件)。今夜のガイド変更枠を、クリックに効く変更(例:最初の画面に値下がり商品へのボタン)に使えない。
- デメリット2:原文を開けていないので、日程が公式と違っていた場合の誤りは残る(検索結果と報道2件は一致)。
- デメリット3:適用は11/27以降になる見込みで、そのとき先行セールは始まっているが、本文は「予定です」のまま。誤りではないが古く見える。「開催中」に変えるには開始の事実を確認する必要があり、今夜はしていない。
- 重なり:EXP-036(P-013、測定11/25〜12/1、判定12/1)とP-011(guide_card・guide_endの押下、判定11/28)の測定期間に入る。ボタン・見出し・title・descriptionは変えないので影響は小さい(推測)が、適用した日を「(適用日) BFガイドAmazon確認日更新」として実験ログに書き、混ざりを残す。
- 戻し方:`git apply -R 2026-11-26_BFガイドAmazon確認日更新.patch`。

## 5. 過去の試行・市場・時期
- 過去の試行(experiments.csv):EXP-028(11/20、Amazon日程を出典付きで追加、見込み+0〜1、未測定)、EXP-036(11/25、Amazon中心へ改題、見込み+0〜2、判定12/1、未測定)、EXP-031(11/22、表記の正確さ目的でクリック増を見込まない)。日程表記の変更でクリックが増えたという実測はまだ無い(hit列は全件空欄=11/25議事録 振り返り)。
- 市場・時期:Amazon先行セールは11/27 0:00開始(上の検索結果)。market_ledger.csv 11/27行ではボールの直近7日で下がった商品が15/95件、グローブ10/55件、中央値はすべて0.0%。BFガイドの検索表示は直近14日169回(前14日13回、受信箱)で、セール期間中に読まれる時期。

## 6. 公開APIで確かめた数字(X投稿案の根拠)
- 取得:`https://golf-deals-backend.onrender.com/api/products?category=ball` と `category=glove`(2026-11-26 15:09 UTC 取得、価格の更新は 11/26 03:53 UTC=11/26 12:53 JST の日次ジョブ)。ボール124件・グローブ60件。
- ダンロップ SRIXON Z-STAR XV (12個入り)(slug `srixon-srixon-z-star-xv-12`):current_price 4,950円・average_price 6,638円・price_change_percent −25.4・history_span_days 29・pending_review false。buy_reasonは「過去30日平均より25.4%安く…」。
  - 注意:knowledge 11/23行の「Z-STAR XV は11/24に neutral(−3.0%)」と同じ出品かは未確認(slug を記録していなかった)。
- フットジョイ 左手用グローブ 5枚セット ウェザーソフ FGWF23(slug `footjoy-5-fgwf23`):current_price 3,790円・average_price 5,799円・price_change_percent −34.6・history_span_days 29・pending_review false。Yahoo!の価格は 10/29 の取得で古いため使わない。
- 式:(現在価格 − 過去30日平均) ÷ 過去30日平均。Z-STAR XV (4,950 − 6,638) ÷ 6,638 = −25.4%、FGWF23 (3,790 − 5,799) ÷ 5,799 = −34.6%(API値と一致)。
- URLの応答:4つのURL(下の投稿先)は 11/26 15時台UTC に 200。

## 7. X投稿案3本(手動投稿用。文字数はURLを除く本文。公開前に価格を再確認すること)
utmは `backend/app/x_post.py` の手動枠(utm_source=x・utm_medium=social・utm_campaign=morning/noon/evening・utm_content=post)に合わせた。

### 案1(朝:セールガイド。126字)
```
【PR】Amazonブラックフライデーは先行セール11/27〜29、本セール11/30〜12/7の予定です（11/26時点、検索結果で確認）。
割引の表示だけで決めず、PAR.が1日1回記録している楽天市場の価格の推移と並べて比べる手順をまとめました。
https://par-gear.com/guides/prime-appreciation-sale-2026-golf?utm_source=x&utm_medium=social&utm_campaign=morning&utm_content=post
```

### 案2(昼:値下がり速報。131字)
```
【PR】スリクソン Z-STAR XV（12個入り）が楽天市場で4,950円。PAR.の記録では過去30日平均6,638円より25.4%安い価格です（11/26昼の取得）。
セール中は価格が変わりやすいので、購入前にショップで最新の価格・送料を確認してください。
https://par-gear.com/products/srixon-srixon-z-star-xv-12?utm_source=x&utm_medium=social&utm_campaign=noon&utm_content=post
```

### 案3(夜:ギフト×5,000円以内。129字)
```
【PR】5,000円以内のギフト候補に。フットジョイ ウェザーソフ FGWF23 左手用5枚セットが楽天市場で3,790円。PAR.の記録では過去30日平均5,799円より34.6%安い価格です（11/26昼の取得）。
サイズは商品ページで確認してください。
https://par-gear.com/products/footjoy-5-fgwf23?utm_source=x&utm_medium=social&utm_campaign=evening&utm_content=post
```

- 点検:【PR】は先頭/URLは par-gear.com 配下/「最安」「強い買い時」「必ず」なし/価格は楽天市場・PAR.の記録・取得日つき/1投稿1メッセージ/冒頭で「何がいくら」を言う(案2・3)。
- リスク:投稿時に価格が戻っていたら案2・3は出さない(公開APIで current_price を再確認する。違えば数字を直すか投稿しない)。案3の「ギフト 5000円」は検索数未取得で、狙いは推測(巡回メモ②)。案1の日程は原文未開封。
- 測り方:utm_source=x の訪問(GA4)と、その後のショップクリック。型(セール案内/値下がり速報/ギフト)ごとに記録する。

## 8. 知識への追記(knowledge.mdに書いた)
- 部署の学び2件、代表者会議から持ち帰ったこと1件(11/25会議)、スキル改善メモ1件。

## 出典
- 事実.md:`docs/departments/01_全体統括/01_部内検討/2026-11-26_事実.md`
- 議事録:`docs/departments/00_代表者会議/議事録/2026-11/2026-11-25.md`
- 台帳:`docs/knowledge/kpi_ledger.csv` 11/1行・11/27行、`docs/knowledge/kpi/2026-11-27.json`、`docs/knowledge/experiments.csv` EXP-028・031・036、`docs/knowledge/market_ledger.csv` 11/27行
- 検索結果(2026-11-26):https://www.phileweb.com/news/hobby/202611/19/8720.html 、https://www.watch.impress.co.jp/docs/news/2157749.html (いずれも見出し・要約のみ。本文未開封)
- 公開API:https://golf-deals-backend.onrender.com/api/products?category=ball 、同 category=glove

使ったスキル:pro-marketing(.claude/skills/pro-marketing/SKILL.md)、rampstack-seo:seo-onpage(ファイルで参照:~/.claude/plugins 配下のSKILL.md。Skillツールはこの環境に無い)、marketing:content-creation(ファイルで参照。同上)
