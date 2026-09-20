# ゴルフ買い時判定サービス (MVP)

ゴルフ用品の価格を継続的に記録し、過去価格との比較から「今買う価値があるか」を
ルールベースで判定し、AIが判定理由の説明文を生成して公開するサービスです。

MVPの目的は **売上ではなく「商品→価格→価格履歴→価格分析→買い時判定→AI説明→Web公開」
という一連の流れを完全自動で回せること** です。

## 1. 全体アーキテクチャ

```
                     ┌────────────────────┐
                     │  GitHub Actions     │  毎日1回 cron 起動
                     │ (update-prices.yml) │
                     └──────────┬───────────┘
                                │ 実行
                                ▼
┌──────────────────────────────────────────────────────────┐
│ backend/ (Python / FastAPI)                                │
│                                                              │
│  scripts/update_prices.py  … 日次バッチ                     │
│    1. 商品一覧取得                                           │
│    2. 価格取得 (CSVインポート / 将来はAPI・許可された取得方法) │
│    3. PriceHistory へ保存                                    │
│    4. 価格統計 (平均・最安値・変化率) を更新                   │
│    5. 買い時判定 (ルールベース, app/analysis.py)              │
│    6. AI説明文生成 (Claude API, app/ai.py) ※変化時のみ        │
│    7. エラーはスキップしてログ記録 (ErrorLog)                 │
│                                                              │
│  app/main.py … FastAPI アプリ (公開API + 管理API)             │
│  app/models.py, schemas.py, crud.py, database.py             │
└───────────────────────────┬──────────────────────────────┘
                             │ REST API (JSON)
                             ▼
┌──────────────────────────────────────────────────────────┐
│ frontend/ (Next.js / App Router)                            │
│   /                … 今日の買い時ゴルフ用品 一覧              │
│   /products/[slug]  … 商品詳細 (SEOページ)                    │
│   /category/[cat]   … カテゴリページ                          │
│   /admin/*          … 管理画面 (商品CRUD, 価格履歴, ログ)      │
└──────────────────────────────────────────────────────────┘
                             │
                             ▼
                     PostgreSQL (Product / PriceHistory / ErrorLog)
```

### 技術選定について

指示書の基本構成 (Python / Next.js / PostgreSQL / Claude API / cron or GitHub Actions /
低コストホスティング) をそのまま採用しています。変更点は以下の通りです。

- **Backend framework: FastAPI** — 型付きスキーマ (Pydantic) とAPI自動ドキュメント
  (`/docs`) が管理画面・バッチ処理両方の開発速度を上げるため採用。
- **ORM: SQLAlchemy 2.0** — PostgreSQLとテスト用SQLiteの両方で同じモデルを使い回せるため。
- **マイグレーション: 素朴な `create_all` スクリプト** — MVPの間はAlembicを導入せず
  `scripts/init_db.py` でテーブル作成する運用とし、スキーマが安定してから
  Alembicを導入する想定 (将来課題としてREADMEに明記)。
- **スケジューラ: GitHub Actions** — 追加インフラ不要でコストゼロのため cron より優先。
- **ホスティング候補**: Frontend = Vercel、Backend = Railway / Render / Fly.io など
  PostgreSQL込みで無料枠のあるPaaS、DB = 同PaaSのマネージドPostgres。

## 2. ディレクトリ構造

```
.
├── README.md
├── .env.example                  … ルートの環境変数一覧 (参照用)
├── .github/workflows/update-prices.yml
├── data/sample_products.csv      … CSVインポートのサンプル
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py               … FastAPIアプリ本体
│   │   ├── config.py             … 環境変数読み込み
│   │   ├── database.py           … SQLAlchemy engine/session
│   │   ├── models.py             … Product / PriceHistory / ErrorLog
│   │   ├── schemas.py            … Pydanticスキーマ
│   │   ├── crud.py               … DB操作
│   │   ├── analysis.py           … 価格統計・買い時判定ロジック (ルールベース)
│   │   ├── ai.py                 … Claude APIによる説明文生成
│   │   ├── csv_import.py         … CSVインポート処理
│   │   ├── logging_utils.py      … ErrorLog記録ヘルパー
│   │   ├── auth.py               … 管理APIの認証
│   │   └── routers/
│   │       ├── products.py       … 公開API
│   │       └── admin.py          … 管理API
│   ├── scripts/
│   │   ├── init_db.py            … テーブル作成
│   │   └── update_prices.py      … 日次バッチ本体
│   └── tests/
│       ├── conftest.py
│       ├── test_analysis.py
│       ├── test_csv_import.py
│       └── test_api.py
└── frontend/
    ├── package.json
    ├── .env.example
    ├── app/
    │   ├── page.tsx               … トップページ
    │   ├── products/[slug]/page.tsx
    │   ├── category/[category]/page.tsx
    │   └── admin/
    │       ├── page.tsx           … 管理ダッシュボード
    │       ├── products/page.tsx  … 商品CRUD
    │       ├── logs/page.tsx      … エラーログ
    │       └── login.tsx
    ├── components/
    │   ├── ProductCard.tsx
    │   └── BuyStatusBadge.tsx
    └── lib/api.ts
```

## 3. DB設計

### Product

| column               | type          | 備考                                         |
|----------------------|---------------|----------------------------------------------|
| id                    | serial PK     |                                               |
| slug                  | string unique | URL用 (`/products/{slug}`)                    |
| name                  | string        |                                               |
| brand                 | string        |                                               |
| category              | string        | driver / iron / wedge / putter / ball        |
| model_number          | string null   |                                               |
| image_url             | string null   |                                               |
| product_url           | string null   | 販売元ページ                                  |
| affiliate_url         | string null   | アフィリエイトリンク                          |
| current_price         | int null      |                                               |
| previous_price        | int null      | 直前の価格取得時点の価格                      |
| lowest_price          | int null      | 過去最安値                                    |
| average_price         | int null      | 過去30日平均                                  |
| price_change_percent  | float null    | 平均比の変化率(%) 負=値下がり                 |
| buy_score             | string        | strong_buy / buy / neutral / not_buy / insufficient_data |
| buy_reason            | text null     | ルールに基づく判定根拠 (AI生成)               |
| ai_title              | string null   | AI生成タイトル                                |
| ai_summary            | text null     | AI生成要約                                    |
| ai_caution            | text null     | 注意書き                                      |
| ai_generated_at       | datetime null | 最後にAI生成した日時 (コスト制御に利用)       |
| ai_content_hash       | string null   | 生成元データのハッシュ (差分検知)             |
| created_at            | datetime      |                                               |
| updated_at            | datetime      |                                               |

### PriceHistory

| column       | type      | 備考             |
|--------------|-----------|------------------|
| id           | serial PK |                  |
| product_id   | FK        | Product.id       |
| price        | int       |                  |
| recorded_at  | datetime  |                  |

### ErrorLog

| column       | type      | 備考                                              |
|--------------|-----------|---------------------------------------------------|
| id           | serial PK |                                                    |
| level        | string    | info / error                                       |
| source       | string    | price_fetch / ai_generation / db / api / csv_import |
| product_id   | FK null   |                                                    |
| message      | text      |                                                     |
| created_at   | datetime  |                                                     |

## 4. 買い時判定ロジック (ルールベース、`app/analysis.py`)

1. 過去30日の価格データが2件未満 → `insufficient_data` (判定不能)
2. `current_price < average_price(30日) * 0.85` → `strong_buy` (強い買い時候補)
3. `current_price < average_price(30日) * 0.90` → `buy` (買い時候補)
4. `current_price >= max_price(30日) * 0.97` (過去30日最高値付近) → `not_buy`
5. 上記いずれにも該当しない → `neutral` (様子見)

AIは上記ルールの結果と実際の価格数値のみを入力として受け取り、**存在しない価格やデータを
作らない**よう、システムプロンプトで数値の創作を禁止しています (`app/ai.py`)。

## 5. API設計

Base URL: `${API_URL}/api`

### 公開エンドポイント

| method | path                              | 説明                               |
|--------|-----------------------------------|------------------------------------|
| GET    | /health                           | ヘルスチェック                      |
| GET    | /products                         | 商品一覧 (category, buy_score, limit, offset で絞込) |
| GET    | /products/{slug}                  | 商品詳細 + 価格履歴                 |
| GET    | /categories/{category}            | カテゴリ別商品一覧                  |

### 管理API (`Authorization: Bearer {ADMIN_API_TOKEN}` 必須)

| method | path                                  | 説明                     |
|--------|---------------------------------------|--------------------------|
| GET    | /admin/products                       | 全商品一覧 (非公開含む)   |
| POST   | /admin/products                       | 商品追加                 |
| PUT    | /admin/products/{id}                  | 商品編集                 |
| DELETE | /admin/products/{id}                  | 商品削除                 |
| GET    | /admin/products/{id}/prices           | 価格履歴確認             |
| POST   | /admin/products/{id}/prices           | 価格を手動追加           |
| POST   | /admin/import/csv                     | CSVインポート            |
| GET    | /admin/logs                           | エラーログ確認           |
| POST   | /admin/run-update                     | 分析+AI生成パイプライン手動実行 |

## 6. 環境変数

### backend/.env

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/golf_deals
ANTHROPIC_API_KEY=sk-ant-xxxx
CLAUDE_MODEL=claude-sonnet-5
ADMIN_API_TOKEN=change-me-to-a-random-secret
CORS_ORIGINS=http://localhost:3000
```

### frontend/.env

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 7. CSVインポート形式

```
product_name,brand,category,model_number,price,product_url,image_url
PING G440,PING,driver,G440,68000,https://example.com/g440,https://example.com/g440.jpg
```

- `category` は driver / iron / wedge / putter / ball のいずれか
- 既存商品 (name+brand+model_numberが一致) は価格のみ追加、新規はProductも作成
- 取り込みは `POST /api/admin/import/csv` または `python scripts/update_prices.py --csv path.csv`

## 8. 開発手順

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL, ANTHROPIC_API_KEY, ADMIN_API_TOKEN を設定
python scripts/init_db.py         # テーブル作成
uvicorn app.main:app --reload     # http://localhost:8000 , docs: /docs
pytest                            # テスト実行

# 価格更新バッチ (CSVインポート → 分析 → AI生成)
python scripts/update_prices.py --csv ../data/sample_products.csv

# Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev                        # http://localhost:3000
```

## 9. Phase進行状況

- [x] Phase 1: プロジェクト作成
- [x] Phase 2: DB設計
- [x] Phase 3: 商品CRUD
- [x] Phase 4: 価格履歴機能
- [x] Phase 5: 価格分析ロジック
- [x] Phase 6: AI買い時コメント生成
- [x] Phase 7: Web画面
- [x] Phase 8: 管理画面
- [x] Phase 9: 自動更新 (GitHub Actions)
- [x] Phase 10: テスト (pytest)
- [ ] Phase 11: デプロイ (Vercel / Railway等へのデプロイはユーザー側のアカウント設定が必要なため未実施。手順は本READMEの通り)

## 10. セキュリティ / コスト制御メモ

- APIキー・管理者トークンはすべて環境変数管理 (`.env`, `.env.example`を参照)。`.env`は`.gitignore`済み。
- 管理APIはBearerトークンで保護。フロントの管理画面はログイン画面でトークンを入力し、
  ブラウザの`localStorage`に保持して以降のリクエストに付与する簡易実装。
- AI生成は「新商品」「価格変動」「判定変化」の場合のみ実行し、それ以外は`ai_content_hash`を
  比較して再生成をスキップすることでAPI呼び出しコストを抑制する。
- エラーはスキップして`ErrorLog`に記録し、バッチ全体を止めない。
