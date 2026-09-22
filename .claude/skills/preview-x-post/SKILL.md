---
name: preview-x-post
description: PAR.（ゴルフ用品価格比較サイト）が毎日X(Twitter)に自動投稿する「本日のお買い得」文面（backend/app/x_post.py）を、実際には投稿せず・API費用も発生させずにローカルでプレビュー生成するスキル。「X投稿の文面を見たい」「今日は何が投稿される予定か確認したい」「手動でXに貼り付けたい文面が欲しい」ときに使う。実際にXへ投稿する・Claude APIで本番と同じ文面を生成する場合は必ず事前にユーザーへ確認する。
---

# preview-x-post

PAR.の日次X自動投稿（STEP11、`backend/app/x_post.py`）の文面を、**実際に投稿せず・原則コストをかけずに**
プレビューするスキル。このスキル自体は `post_tweet()` / `post_daily_deals()` を絶対に呼ばない。

## 絶対に守ること

- **実際にXへ投稿しない。** `post_tweet` / `post_daily_deals` を呼び出すのはこのスキルの範囲外。
- **デフォルトではClaude APIを呼ばない（費用を発生させない、絶対ルール1）。** 本番の`ANTHROPIC_API_KEY`が
  設定されていても、プレビュー用途では意図的に空にして、`_generate_tweet_body_rule_based`（無料のルールベース文面）
  の結果を見せる。Claudeが実際に生成する本番相当の文面まで見たい場合は、**必ずユーザーに「Claude APIを使うと
  ごく少額の費用が発生しますが実行してよいですか」と確認してから**、本物の`ANTHROPIC_API_KEY`で実行する。
- 使うDBはローカルの開発用SQLite（`backend/golf_deals.db` 等）を前提とする。本番DBへの接続や書き込みは行わない
  （このスキルは読み取り専用のプレビューであり、そもそも書き込み処理は無い）。

## 手順（無料のルールベース文面プレビュー・デフォルト）

```bash
cd backend && python3 -c "
import os
os.environ['ANTHROPIC_API_KEY'] = ''  # 費用が発生するAI生成を確実にスキップ
from app.config import get_settings
get_settings.cache_clear()

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
        print(f'X重み付き文字数: {x_post._x_weighted_length(text)} / 280')
finally:
    db.close()
"
```

- `products`が空の場合は「対象商品なし」と正直に報告する（無理に何かでっち上げない）。
- 出力された `text` をそのまま「コピペ用の文面」としてユーザーに提示する。

## Claude生成の本番相当文面まで見たい場合（要ユーザー許可・費用が発生する）

ユーザーから明示的な許可を得てから、上のスクリプトで `os.environ['ANTHROPIC_API_KEY'] = ''` の行を削除し
（＝ `.env` に設定された本番の `ANTHROPIC_API_KEY` をそのまま使う）、同じスクリプトを再実行する。
許可なくこちらを実行してはいけない。

## 文字数・URL周りの注意点（結果を説明するときに使う）

- X側の実際の文字数上限は280（`x_post.X_MAX_WEIGHTED_LENGTH`）。日本語等は1文字を2としてカウントする近似計算
  （`_x_weighted_length`）。
- 投稿URLはX側で常に23文字分（`X_URL_WEIGHTED_LENGTH`）としてカウントされる固定長のため、本文の実際の残り
  文字数はこれを差し引いて考える（`_truncate_for_x`が自動でこれを考慮して切り詰めている）。
- 複数商品が選ばれた場合はカテゴリページへのリンク、1商品のみの場合はその商品ページへのリンクになる
  （`_build_tweet_text`のロジック）。

## やってはいけないこと

- `post_tweet` / `post_daily_deals` を呼んで実際に投稿すること。
- ユーザーの許可なく本番の `ANTHROPIC_API_KEY` でAI生成を実行すること。
- 「本日投稿対象なし」の状況で、それらしい文面をでっち上げて見せること。
