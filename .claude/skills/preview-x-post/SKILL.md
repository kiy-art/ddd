---
name: preview-x-post
description: PAR.（ゴルフ用品価格比較サイト）が毎日生成するX(Twitter)投稿文面（backend/app/x_post.py）を、実際には投稿せずにローカルでプレビュー生成するスキル。「X投稿の文面を見たい」「今日は何が投稿される予定か確認したい」「手動でXに貼り付けたい文面が欲しい」ときに使う。実際にXへ投稿する場合は必ず事前にユーザーへ確認する。
---

# preview-x-post

PAR.の日次X投稿（STEP11、STEP41で手動投稿運用、STEP45でCTR重視の文面に刷新、`backend/app/x_post.py`）の文面を、
**実際に投稿せずに**プレビューするスキル。このスキル自体は `post_tweet()` / `post_daily_deals()` を絶対に呼ばない。
STEP45以降、文面は事実データのみから組み立てる決定的なテンプレート（フック→商品→価格→スコア→CTA→URL→ハッシュタグ）で
生成されClaude APIは呼ばないため、プレビューに費用は発生しない。

## 絶対に守ること

- **実際にXへ投稿しない。** `post_tweet` / `post_daily_deals` を呼び出すのはこのスキルの範囲外。
- 使うDBはローカルの開発用SQLite（`backend/golf_deals.db` 等）を前提とする。本番DBへの接続や書き込みは行わない
  （このスキルは読み取り専用のプレビューであり、そもそも書き込み処理は無い）。

## 手順

```bash
cd backend && python3 -c "
from app.database import SessionLocal
from app import x_post

db = SessionLocal()
try:
    products = x_post.select_deals_of_the_day(db, count=2)
    if not products:
        print('本日投稿対象となる商品はありません（強い買い時シグナルの信頼できる商品も、MSRP割引の商品も無し）。')
    else:
        text = x_post._build_tweet_text(db, products)
        print('--- 投稿予定の商品 ---')
        for p in products:
            print(f'{p.brand} {p.name}（現在価格: {p.current_price}円, buy_score: {p.buy_score}）')
        print()
        print('--- プレビュー本文（このままコピペ可能） ---')
        print(text)
        print()
        url = next(l for l in text.split(chr(10)) if l.startswith('http'))
        print(f'X重み付き文字数: {x_post._post_weighted_length(text.replace(url, str()))} / 280')
finally:
    db.close()
"
```

- `products`が空の場合は「対象商品なし」と正直に報告する（無理に何かでっち上げない）。
- 出力された `text` をそのまま「コピペ用の文面」としてユーザーに提示する。

## 文字数・URL周りの注意点（結果を説明するときに使う）

- X側の実際の文字数上限は280（`x_post.X_MAX_WEIGHTED_LENGTH`）。日本語等は1文字を2としてカウントする近似計算
  （`_x_weighted_length`）。
- 投稿URLはX側で常に23文字分（`X_URL_WEIGHTED_LENGTH`）としてカウントされる固定長。上限を超えそうな場合は
  `_generate_post_text`が「長い商品名の短縮→2本目の紹介行→スコア行」の順に要素を削って収める
  （フック・価格・CTAは削らない）。
- リンクは常に1本目の商品ページ（商品写真・価格・フックが入ったOGP画像が表示される）。2本目は本文で紹介するのみ。
- フック（1行目）は事実で裏付けられる場合のみ出る：「過去N日間の最安値」は価格履歴7日以上、「半額以下」「ほぼ半額」は
  四捨五入前の正確な割引率、「楽天ランキングN位」は3日以内に取得した順位に限る。

## やってはいけないこと

- `post_tweet` / `post_daily_deals` を呼んで実際に投稿すること。
- 「本日投稿対象なし」の状況で、それらしい文面をでっち上げて見せること。
