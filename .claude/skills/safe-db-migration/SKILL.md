---
name: safe-db-migration
description: PAR.（ゴルフ用品価格比較サイト）のDB移行・大掃除・一括データ修正を安全に実行、または新規作成するスキル。「dry-run」「本番データへの適用」「大掃除」「一括修正」「マイグレーション」といった作業のとき、または既存の商品データを一括で書き換える新機能を作るときに使う。Renderの無料プランにはWeb Shellが無いため、管理画面のAPIエンドポイント経由でしか本番DBに実行できないという制約（STEP16）を前提とする。
---

# safe-db-migration

PAR.でのDBへの一括変更（STEP15の商品名クレンジング統合、STEP16の管理API化で確立したパターン）を
安全に実行・拡張するためのスキル。対象は「複数行・複数商品にまたがる一括書き換え」であり、
1商品の手動修正（管理画面の通常編集フォーム）はこのスキルの対象外。

## 絶対に守ること（docs/ai_company_guidelines.md 由来）

1. **本番への実際の適用（apply=True / dry_run=false）は、ユーザーの明示的な許可なしに実行しない。**
   dry-run（プレビューのみ、書き込みなし）は許可なく実行してよいが、結果を見せて確認を取ってから本適用に進む。
2. Renderの無料プランには **Web Shell（SSH/コンソール）が無い**。ローカルのサンドボックスやCLIスクリプトから本番Postgresへ直接繋いで実行する手段は無い（そのような接続を試みないこと）。本番DBへ実際に反映する唯一の$0の手段は、Bearerトークン認証で保護された管理画面のAPIエンドポイントを、社長自身が管理画面のボタンから実行することである。
3. 大規模な一括変更ロジックを新規実装する前には、必ず提案とユーザーの確認を行う（絶対ルール3）。

## 既存の実装パターン（新規マイグレーションはこの型に合わせる）

STEP15/16で確立した「ロジック共有」パターン（`app/title_migration.py` が実例）：

```
backend/app/<name>_migration.py       # 本体ロジック（CLIとAPIの両方から呼ばれる、唯一の実装）
backend/scripts/<name>_migration.py   # 薄いCLIラッパー（argparse、--apply省略時はdry-run）
backend/app/routers/admin.py          # POST /admin/run-<name>-migration（require_admin保護、dry_run:bool=False）
```

- 本体関数のシグネチャ：`run_<name>_migration(db: Session, apply: bool, on_progress: Callable | None = None) -> <Name>MigrationResult`
- `<Name>MigrationResult` は dataclass で、`applied: bool` と件数（例: `renamed`, `merge_groups`）に加えて、
  **人間が読める `plan_lines: list[str]`**（何をした/するつもりかを1行ずつ）を必ず持つ。CLIの標準出力にも、
  管理画面のAPIレスポンスにも、`ErrorLog`（`crud.create_error_log`、`source="<name>_migration"`等）にも
  この`plan_lines`をそのまま使い回せるようにする。
- **デフォルトは常にdry-run**。CLIは`--apply`フラグが無ければ何も書き込まない。管理APIは`dry_run: bool = False`
  というクエリパラメータを取るが（つまりボタンを押すと実行される設計）、管理画面のUIボタン側に
  `window.confirm()`による実行前確認ダイアログを必ず付ける（STEP16の設計）。
- 処理に時間がかかりうる場合は `app/progress.py` のSSEライブダッシュボードに新しいステージとして統合する（STEP13/16参照。フロントエンドの`LiveJobDashboard`は汎用設計のため変更不要なことが多い）。
- 冪等性：同じマイグレーションを`--apply`で2回実行しても、2回目は何もすることがない（既に処理済みのものは対象から除外される）ように作る。

## 既存マイグレーションを実行する手順

1. **必ずdry-runを先に実行する**：
   ```bash
   cd backend && python3 scripts/<name>_migration.py         # --apply無し = dry-run
   ```
   または管理画面から `?dry_run=true` で叩く。出力される `plan_lines`（変更予定の一覧）を確認する。
2. dry-runの結果をユーザーに提示し、**本適用してよいか明示的な確認を取る**。
3. 確認が取れたら本適用：
   ```bash
   cd backend && python3 scripts/<name>_migration.py --apply
   ```
   本番へは、社長が管理画面の該当ボタン（確認ダイアログあり）を押す形で実行してもらう。このスキルの実行者（Claude）自身が本番DBに直接書き込むことはできない・しない。
4. 適用後、返ってきた件数（`plan_lines`や dataclass のカウント）をそのまま報告する。「成功しました」とだけ言わず、実際に何件リネーム/統合/修正されたかを数字で示す。

## 新しいマイグレーションを作るとき

1. 上記の「既存の実装パターン」に厳密に従う。dry-runをサポートしないマイグレーションは絶対に作らない。
2. `tests/test_<name>_migration.py` を `tests/test_title_migration.py` と同じ形で作成する：
   - dry-runでは何も変更されないことのテスト。
   - applyで期待通りの変更がされることのテスト。
   - 再実行しても安全（冪等）なことのテスト。
   - 管理APIエンドポイントの認証必須テスト（未認証だと401/403になること）。
3. 実装・テスト後は必ず：
   ```bash
   cd backend
   ruff check app/<name>_migration.py scripts/<name>_migration.py app/routers/admin.py
   python3 -m pytest tests/test_<name>_migration.py -q
   python3 -m pytest -q
   ```
4. 新規マイグレーションのロジックや管理画面ボタンをユーザーに説明する際は、「dry-runがデフォルトであること」「本番適用は社長自身がボタンを押すまで実行されないこと」を明確に伝える。

## やってはいけないこと

- `--apply` や `dry_run=false` を、ユーザーに確認せず実行すること。
- 本番Postgresに直接接続しようとすること（そもそも手段が無い設計であり、試みるべきでもない）。
- `plan_lines`や件数を確認せずに「マイグレーション完了しました」と報告すること。
- 冪等性を持たない（再実行すると壊れる/重複する）マイグレーションを作ること。
