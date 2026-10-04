# トレンド・市場状況

経営判断の前提にする外部・市場の情報。会議のたびに更新する。新しいものを上に足す。古くなった情報は消さずに打ち消し線を引く（判断の経緯が追えるように）。

## 2つの情報源
1. **自社データ（事実）**：`market_ledger.csv`（`kpi_snapshot.py`が会議ごとに自動で追記）。
   - 中身：カテゴリ別に、約30日前と比べて値下がり・値上がり・横ばいの商品数、変化率の中央値、直近30日の新商品数。
   - 元データ：毎日の価格取得（`price_history`）。比べられた商品数（`compared`）が少ないカテゴリは、傾向として扱わない。
2. **外部の情報**：マーケティング部・営業部がWeb検索で調べ、出典URLと確認日を付けて下に書く。
   - 例：新モデルの発売・発表、季節の需要（ゴルフシーズン・ボーナス・年末商戦・型落ちの値下げ時期）、ショップのセール（楽天スーパーSALE・お買い物マラソン・Yahoo!のPayPay施策・Amazonのセール）、ASPの報酬キャンペーン、競合サイトの動き、検索需要の変化。
   - 出典の無いもの、裏付けの取れないものは書かない。予想は「推測」と明記する。

## 判断への使い方
- 施策の優先順位：季節やセールの時期に合わせる。例：セールの前に該当カテゴリのページを整える。
- 実験の解釈：PDCAの測定期間に、セールや新モデルの発売が重なっていなかったかを確認し、`experiments.csv`の`learning`に書く。市場全体の動きと施策の効果を取り違えないため。
- 新しい収益の柱：市場の伸び・縮みを根拠にする（運営モデル1.1）。

## 記録

### 外部の情報

| 確認日 | 内容 | 出典 | 判断への影響 |
|---|---|---|---|
| 2026-10-05 | スリクソン ZXi RKTドライバー（4モデル）と新ZXiアイアンが2026-09-12発売。PAR.は未掲載 | https://sports.yahoo.co.jp/column/detail/2026080700008-spnavido 、https://zaikei.co.jp/releases/3556533/ （検索結果の要約） | 旧ZXiが型落ちへ。新旧比較（N4）の候補 |
| 2026-10-05 | 2026年モデル：Qi4D（1/29）、Callaway Quantum（2/6）、ミズノ JPX ONE（3/6）、Cobra OPTM。PAR.は未掲載 | https://kakaku.com/golf/driver/ranking_6110/ 、https://www.golfdigest-minna.jp/_ct/17818324 （要約） | カタログに追加する候補。Qi35・Elyte・G430は型落ち |
| 2026-10-05 | ブリヂストン B-Limited BX TOUR MAX（9/18）、BX★★TOUR（10/9）。PING i240・iDiは2025年の発売で新製品ではない | https://sports.yahoo.co.jp/column/detail/2026081400002-spnavido 、https://clubping.jp/news/2025/pingnews250903.pdf | 「新製品」と誤って書かない |
| 2026-10-05 | 2027年のPro V1・Pro V1xは試作品のテスト中（推測：2027年初めの発売） | https://www.titleist.com/teamtitleist/team-titleist/f/the-clubhouse/77196/2027-pro-v1-pro-v1x-golf-ball-prototype-reviews-official-discussion | Pro V1 2025が型落ちになる時期に備える |
| 2026-10-05 | テーラーメイドは2027年モデルのドライバー等を発売せず、2年周期にするとの報道（要確認） | https://shotnavi.jp/newslive/news_41717.htm （要約） | 型落ちの値下がりの時期が例年と変わる可能性（推測） |
| 2026-10-05 | 新モデルは、発表の数か月前にUSGAの適合リストに載ることが多い | https://www.golfmagic.com/equipment/news/taylormade-qi4d-usga-conforming-list | 毎月の会議で、2027年モデルの兆しとして確認する |
| 2026-10-05 | 楽天お買い物マラソン 10/4 20:00〜10/9 1:59（予想記事と商品名の文言から。公式は未確認）。9/4〜9/11に楽天スーパーSALEが開催された | https://8and.jp/2026/10/04/ 、https://tinpanblog.com/rakuten-super-sale-september2026-cross-shop-points-guide/ | EXP-001の測定期間と重なる（交絡） |
| 2026-10-05 | Amazonプライム感謝祭：先行10/13〜15、本番10/16〜19 | https://ecnomikata.com/ecnews/51773/ | Amazonの適格販売を稼ぐ機会。表記の修正は10/5に済ませた（D3） |
| 2026-10-05 | 12月の楽天スーパーSALEは**予想**で12/4〜12/11（公式は未発表）。ブラックフライデー・いい買物の日は未発表 | https://appllio.com/rakuten-super-sale-schedule | 12月はINV-001の撤退判断の月なので、セールの影響を考えに入れる |
| 2026-10-05 | ゴルフ場の需要期は春（4〜7月）と秋（9〜11月） | https://car-me.jp/golfee/articles/11515 | 10〜11月はX投稿の反応が取りやすい時期（推測） |
| 2026-10-05 | 型落ちクラブは年末年始に最大50%前後引き、後継の発売前に40〜60%引きの例も（一般論。個別の商品の見込みとしては書かない） | https://pricey.jp/web/articles/2715 | 型落ちの値下がりページは11月までに用意 |
| 2026-10-05 | 価格.comはドライバーの最安価格と下落率を表示。大手（GDO・楽天GORA）もAI機能を入れ始めた | https://kakaku.com/golf/driver/ 、https://corp.rakuten.co.jp/news/press/2026/0512_01.html （要約） | 最安表示では勝てない。PAR.の違いは「買い時の判定」と「新旧の価格差」に置く |
| 2026-10-05 | ASPの目安（すべて要再確認）：楽天2〜4%・1件上限1,000円、Amazonは上限なし（料率は未確認）、ゴルフ5・アルペン4.18%（VC）、ゴルフスクール1件5,000〜30,000円、買取1,300〜1,500円、GDOは提携の募集を終了 | https://www.a8.net/campus/campus-blog/946-golf.html 、https://media-analytics.jp/affisearch/promotions/sports-depot-golf5-alpen-no-koshiki-online-store 、https://www.golfdigest.co.jp/prepre/affiliate/default03.asp | #004の前提。数字は推測として扱う |
| 2026-10-05 | Amazon PA-API 5.0は廃止され、Creators APIへ移行したとの記事（要確認） | https://dev.to/th3nate/amazon-pa-api-v5-is-shutting-down-april-30-2026-here-is-what-changes-at-the-auth-layer-22ek | 将来Amazonの価格を取るなら、Creators APIを前提にする |
| 2026-10-05 | Xの外部リンク付き投稿が伸びにくいかは、根拠が分かれている | https://buffer.com/resources/links-on-x/ 、https://ppc.land/x-drops-year-old-link-penalty-musk-tells-zuckerberg-on-platform/ | utmで自社のデータを取る（EXP-007） |
