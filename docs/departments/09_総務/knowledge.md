# 09_総務のナレッジ

1行1件。`- YYYY-MM-DD [事業番号] 内容(根拠: 出典)`。推測は「推測」と書く。古くなった行は消さずに打ち消し線を引く。

## 部署の学び
- 2026-10-11 [001] 本番のYahoo!リンクはバリューコマース経由のアフィリエイトだが、免責ページ・FAQは「Yahoo!は紹介料の対象外」のまま。リンクの仕組みを変えたら法務ページも同時に直す(根拠: curl par-gear.com/products/ping-g430-max・/disclaimer・/faq、2026-10-12 0時台)
- 2026-10-11 [001] Amazonセールの記事・投稿に楽天・Yahoo!の値下がり商品を出すときは、見出しで「Amazonの価格ではない」と明示する。PAR.はAmazon価格を取得していない(根拠: frontend/app/disclaimer/page.tsx 57行、09_総務/01_部内検討/2026-10-11_表示規約チェック.md)
- 2026-10-11 [001] PR表記の部品(PrNotice・購入ボックス)は12pxで、ガイド本文14pxより小さい。社内基準「本文同等以上」に未達(根拠: frontend/components/PrNotice.tsx、app/guides/[slug]/page.tsx 153行)
- 2026-10-11 [001] Amazonアソシエイト運営規約5条：定型文を「サイト上で目立つように」表示、Amazonの支援・後援の暗示は禁止。価格表示・商標の細則はプログラム・ポリシーと商標ガイドライン側(根拠: https://affiliate.amazon.co.jp/help/operating/agreement 確認日2026-10-12)
- 2026-10-11 [001] 消費者庁ステマ規制ページは施行日・対象のみ。明瞭／不明瞭な表示の具体例は運用基準PDF側にある(根拠: https://www.caa.go.jp/policies/policy/representation/fair_labeling/stealth_marketing/ 確認日2026-10-12)
- 2026-10-17 [001] 10/11の🔴「Yahoo!は紹介料の対象外」は本番で修正済み（免責・FAQ・プライバシーがVC込みの3社表記）。ただし contracts.csv は「VC提携待ち・承認状態未確認」のまま、リンクだけ先に出ている(根拠: curl par-gear.com/disclaimer・/faq・/privacy 2026-10-17、docs/knowledge/contracts.csv)
- 2026-10-17 [001] Amazon定型文は免責ページだけにあり、トップ・商品ページ・フッターには無い。PR表記と運営者情報ページ(/about)も無い(404)(根拠: curl par-gear.com 2026-10-17)
- 2026-10-17 [001] 「表記審査9件」の原本はリポジトリに無く、件別の修正状況は判定不能。目標の測り方を決める必要あり(根拠: find/grep、2026-10-17)
- 2026-10-17 [001] 「AI」表記は、実態が「ルールベースの採点＋AI説明文」なので一文の注釈を添える。型落ちタグは手調査の is_current_generation のみ(根拠: frontend/lib/badges.ts 98行、免責・FAQ)
- 2026-10-17 [001] 二重価格は「最近相当期間価格」が基本。caa.go.jpは今夜接続不可で原文未開封(根拠: 検索結果の要約、https://www.caa.go.jp/policies/policy/representation/fair_labeling/representation_regulation/double_price)

## 代表者会議から持ち帰ったこと

## スキル改善メモ
（専門スキル `.claude/skills/pro-general-affairs/SKILL.md` で足りなかった点。月1回、人事部が改訂案にまとめる）
- 2026-10-11 [001] 一次情報にバリューコマース(Yahoo!)が無く、二重価格(将来価格・通常価格)の基準も無い → 一次情報に「バリューコマース規約」「消費者庁 不当な価格表示についての景品表示法上の考え方」を足し、法務ページ点検表に「参加ASPの一覧が実際のリンクと一致するか」を足す(根拠: 09_総務/01_部内検討/2026-10-11_表示規約チェック.md の2-6)
