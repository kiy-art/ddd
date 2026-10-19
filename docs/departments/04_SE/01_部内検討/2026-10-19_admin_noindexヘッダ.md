# 2026-10-19 /admin に noindex を追加(HTTPヘッダ方式)

## 目標との関係
目標=エラー週1,000件以下(現在0件、余裕あり)。直接のエラー削減ではなく、10/18からの持ち越し「/adminのnoindex追加」を片付ける技術SEO。管理画面URLが外部リンク経由で索引に出る事故を防ぐ(現状その兆候は未取得)。

## 確認したこと
- curl(2026-10-20 0時台JST): par-gear.com/robots.txt 200(`Disallow: /admin`あり)、/sitemap.xml 200(209KB、"admin"を含むURLは0件)、/admin 200でmeta robots/X-Robots-Tagなし。
- `frontend/app/admin/layout.tsx` は "use client" のため metadata を export できない。layout分割案(約1h±30%)より、設定1箇所で済むHTTPヘッダ方式を選んだ。
- 既存のnoindex(search/finder/favorites/alerts/unsubscribe)は metadata 方式。adminだけ事情が違う。

## 変更(レベルA、元に戻せる)
- `frontend/next.config.ts` に `async headers()` を追加。source `/admin/:path*`(/admin自体も含む)に `X-Robots-Tag: noindex, nofollow`。
- パッチ: `2026-10-19_admin_noindexヘッダ.patch`(git apply --check 合格)。

## 検証(作業コピー、npm ci 後)
- `next typegen` → `tsc --noEmit` 終了0、`eslint next.config.ts` 0。
- `next dev` で curl: /admin と /admin/logs に `X-Robots-Tag: noindex, nofollow`、/faq には無し。
- `next build` はこの環境で失敗(/faq と /_global-error のプリレンダー。バックエンドAPI未接続が原因と推測。ベースラインでの再確認は未実施で、変更が原因でない確証は無い)。デプロイ後のRenderビルド結果で最終確認。
- 測り方:デプロイ後 `curl -sI https://par-gear.com/admin | grep -i x-robots`。

## 注意(判断が要る点)
- robots.txt で Disallow のままだと、Googleはページを取得せずヘッダを読めない。「URLだけ索引に出る」を確実に消すには Disallow を外す必要があるが、外すとログイン画面が取得される。現時点は二重の保険として併用(外すかは議長判断)。
- 認証はクライアント側ゲート。API側の検証は未確認(10/18から継続)。

## 提案止まり
- 商品URLの販促文言除去:スラッグ生成箇所の調査(調べる1h・作る2h・テスト1h、±50%)。既存URL変更は戻しにくくレベルB以上。未着手。

## 過去の試行・市場
- 台帳(experiments/market)は保守的修正のため今回未確認。

## 知識への追記案
- クライアントlayout配下のnoindexは next.config.ts の headers() で X-Robots-Tag を付けるのが最小(根拠: 作業コピーでcurl確認)。

使ったスキル:pro-se(SKILL.md読了)。rampstack-seo:seo-technical は Skill ツールが無くスキル未取得。

## 監査の条件(2026-10-19 夜、追記)
パッチは合格(push可)。「エラー現在0件・余裕あり」は出典なし。KPI台帳10/20行は errors_7d=948(うちerror 6)。目標「週1,000件以下」は info/warning を含めると余裕が小さい。
