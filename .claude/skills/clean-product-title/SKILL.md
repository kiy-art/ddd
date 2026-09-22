---
name: clean-product-title
description: PAR.（ゴルフ用品価格比較サイト）の商品タイトルクレンジングロジック（backend/app/title_cleaner.py・backend/app/brands.py）を検証・強化するスキル。「送料無料」「9/23まで」「千葉県柏市」「パールサテン」等のノイズを含む商品タイトルを「ブランド名＋型番」に整形するルールをテスト・追加するとき、新しい実例タイトルの清掃結果を確認したいとき、またはtests/test_title_cleaner.pyのテストを実行・追加するときに使う。DBへの実際の書き込みはこのスキルの範囲外（safe-db-migrationスキール参照）。
---

# clean-product-title

PAR.の商品名クレンジング（STEP15/16/18/19で確立）を扱うスキル。対象は常に
`backend/app/title_cleaner.py` と `backend/app/brands.py` の**ロジックそのもの**であり、
DBの実データを書き換える作業ではない（実データへの反映は `safe-db-migration` スキルが担当する）。

## 前提として理解しておくこと

- 2層構成：
  1. `strip_promotional_noise()` — 決定的な正規表現パス。無料・即時・常に動く安全網。
  2. `clean_product_title()` — `ANTHROPIC_API_KEY` 設定時のみ、Claude APIで仕上げる（正規表現後のテキストとブランド/カテゴリという「既に確定した事実」だけを渡し、出力は「非空・入力より大幅に長くない・既知のブランド表記を含む」の3点でサニティチェック。不合格なら正規表現の結果にフォールバック）。
- ブランド表記は `backend/app/brands.py` に集約されている：
  - `BRAND_KEYWORDS` — 商品発見時のブランド一致判定用（サブブランド／商品ラインの統合マッピングも含む。例: `Vokey`→`Titleist`）。
  - `BRAND_NAME_SYNONYMS` — タイトル内の「同一ブランド名の異表記重複」除去専用（真の同一名ペアのみ。例: `Titleist`⇔`タイトリスト`、`Fourteen`⇔`フォーティーン`⇔`フォーティン`）。**この2つを混同しないこと** — `BRAND_KEYWORDS`のサブブランド情報をここに入れると、型番の区別情報が誤って消える。
- 既知の制約（正規表現層だけでは解決できない）：型番自体の異表記重複（「OPUS SP」⇔「オーパス エスピー」、「FR-3」⇔「FR3」、「PRO V1」⇔「プロV1」等）は、辞書化されていない任意の型番の綴り違いを正規表現では認識できない。これはClaude連携層に委ねる設計であり、無理に正規表現で全解決しようとしないこと。

## 実例タイトルを清掃してみたいとき（DBは触らない）

1. 正規表現層のみの結果を確認（コストゼロ、常に安全）：
   ```bash
   cd backend && python3 -c "
   from app.title_cleaner import strip_promotional_noise
   print(strip_promotional_noise('<清掃したい生タイトル>', brand='<ブランド名>'))
   "
   ```
2. Claude連携込みの最終結果まで見たい場合、**本番のANTHROPIC_API_KEYを使うと実際にAPI費用が発生する**（絶対ルール1）。ユーザーから明示的な許可がない限り、本番キーでの `clean_product_title()` 呼び出しは行わないこと。許可があれば：
   ```bash
   cd backend && python3 -c "
   from app.title_cleaner import clean_product_title
   print(clean_product_title('<生タイトル>', '<ブランド>', '<カテゴリ>'))
   "
   ```
   許可がない場合は、正規表現層の結果と「Claudeが設定されていれば型番の異表記重複もここまで整形されるはず」という説明にとどめる。

## 新しいノイズパターンを追加するとき

1. 既存のパターン群のどこに追加すべきか判断する：
   - 単純な固定フレーズ（「クーポン発行中」「ギフト」等）→ `_PROMO_PHRASES` リストに追記。
   - 数値や可変部分を含む複雑なパターン（年式、シャフト型番、セット数等）→ 専用の `re.compile(...)` 定数を新設し、なぜそのパターンが必要か・何を誤除去しないための工夫か（例: クラブ自身の型番を巻き込まないようシャフトブランド接頭辞に限定）をコメントで明記。
   - ブランド名の表記揺れ → `app/brands.py` の `BRAND_NAME_SYNONYMS` に追加（`BRAND_KEYWORDS` には入れない）。
2. `strip_promotional_noise()` 内の適用順序に新しいパターンを組み込む（ブラケット除去→日付/年式→数量→定型フレーズ→仕上げ/シャフト→自治体名→装飾記号→ブランド重複除去→空カッコ除去→空白正規化、の既存順序を尊重する）。
3. `tests/test_title_cleaner.py` に以下2種類のテストを追加する：
   - 正規表現層のみの結果を検証するテスト（実際にトレースして得られた文字列で `assert` すること。期待値を推測で書かない）。
   - 必要なら、Claude APIをモック化した `clean_product_title()` の最終結果テスト。モックは同ファイル内の `_FakeTextBlock`/`_FakeMessage`/`_FakeMessages`/`_FakeClient` パターン（`anthropic.Anthropic` を `monkeypatch.setattr` で差し替える）を再利用し、**本物のAPIを呼ばない**。

## 検証手順（変更後は必ず実行）

```bash
cd backend
ruff check app/title_cleaner.py app/brands.py
python3 -m pytest tests/test_title_cleaner.py -q
python3 -m pytest -q   # 全体テスト。GA4サンドボックス起因の2件以外は全てパスすること
```

## 最後に

- 既存の安全フィルター（`_looks_like_accessory`・`_looks_like_non_retail_listing`・`AUTO_PUBLISH_NG_KEYWORDS`、いずれも`app/discovery.py`/`app/pipeline.py`）はこのスキルの対象外。これらは**生タイトル**に対して判定される設計を壊さないこと。
- 変更内容とテスト結果をユーザーに簡潔に報告する。`docs/ai_company_guidelines.md` への記録（STEPn番号を振っての追記）は、ユーザーが望む場合のみ行う。
