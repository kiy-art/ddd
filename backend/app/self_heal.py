"""Log-driven self-healing for the daily job (STEP54).

Reads the error-level ErrorLog rows a run produced and, for the few
failure types that have a known, safe fix, applies that fix right away
instead of leaving it for the next day's run:

- a product's Rakuten / Yahoo! price lookup that raised (network blip,
  a 5xx the shared retry in http_retry.py gave up on) -> look up just
  those products again;
- the popularity-ranking sync or the consumables-corner price refresh
  failing (whole step or some categories/items) -> run that step again
  (5 and 7 API calls - cheap).

Everything else is only classified, never "fixed":

- a setup problem (401/403, missing or rejected key) - retrying can't
  help, so it's reported with what to check;
- a used-up quota / rate limit - it resets by itself, reported as such;
- anything without a known safe fix (an analysis bug, an X post that
  failed - retrying a public post risks a double post) - reported for a
  person to look at.

Deliberately NOT retried here, and why:
- product analysis: a retry may call Claude again (cost - absolute rule
  1); the daily job's own analysis stage runs right after this and
  already re-analyses every product, including the ones fixed here;
- price-alert emails: an alert is only marked sent after its email goes
  out, so a failed one is already retried on the next run;
- whole-stage Rakuten/Yahoo price fetches and discovery: minutes long,
  and the daily job's single request has a 900s budget
  (.github/workflows) - per-product retries are capped instead.

Rule-based only: no Claude call, only the same free Rakuten/Yahoo search
APIs the daily job already uses. Also flags products whose Rakuten
lookup keeps failing or finding nothing day after day - those need their
name/keyword looked at, which no retry can fix.

Each run writes one summary row (source="self_heal") that the daily
report and the admin log page show.
"""

import dataclasses
import datetime
import re
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import consumables_merchandiser, crud, models, pipeline, popularity
from app.config import get_settings

SOURCE = "self_heal"
SUMMARY_PREFIX = "自動修復"

# Keeps the daily job well inside its 900s request budget: at most this
# many products are looked up again per source, and no new remedy starts
# once this much time has gone by.
MAX_PRODUCT_RETRIES = 25
TIME_BUDGET_SECONDS = 120

# "Keeps failing" = a failed or empty Rakuten lookup on this many
# different days within the window.
REPEAT_WINDOW_DAYS = 7
REPEAT_MIN_DAYS = 3
MAX_LISTED_NAMES = 5

_CONFIG_PATTERN = re.compile(
    r"\b40[13]\b|unauthori[sz]ed|forbidden|not configured|wrong_parameter|invalid[_ ]?(?:api[_ ]?)?key"
    r"|accesskey|applicationid|api key",
    re.IGNORECASE,
)
# STEP74: Rakuten answers a keyword it won't accept with HTTP 400 and
# "error":"wrong_parameter" - the same error name a bad applicationId gets -
# so the description is checked first, or every such row reads as a setup
# problem ("check RAKUTEN_APP_ID") when the product name is what needs work.
_KEYWORD_PATTERN = re.compile(r"keyword is not valid|keyword must be under", re.IGNORECASE)
_QUOTA_PATTERN = re.compile(r"quota|\b429\b|too many requests|rate limit", re.IGNORECASE)

# What to check for a setup problem, by log source.
_CONFIG_HINTS = {
    "price_fetch": "楽天のRAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（楽天アプリ設定の許可サイトを含む）",
    "yahoo": "YahooのYAHOO_CLIENT_ID",
    "popularity": "楽天のRAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（楽天アプリ設定の許可サイトを含む）",
    "consumables": "楽天のRAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（楽天アプリ設定の許可サイトを含む）",
    "discovery": "楽天のRAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（楽天アプリ設定の許可サイトを含む）",
    "x_post": "XのAPIキー（X_API_KEY等4つ）",
    "price_alert_email": "RESEND_API_KEYと送信元ドメインの設定",
    "daily_report": "RESEND_API_KEYとDAILY_REPORT_EMAIL",
    "ai_generation": "ANTHROPIC_API_KEY（有効性・残高）",
    "content_optimizer": "ANTHROPIC_API_KEY（有効性・残高）とGA4/Search Consoleの設定",
}

# Rows that only restate errors already logged individually - and whose
# advice text names the API keys, which would make every such failure look
# like a setup problem. The per-item rows before them are what's judged.
_RESTATEMENT_PREFIXES = ("楽天の人気ランキングを1カテゴリも取得できませんでした",)

_SOURCE_LABELS = {
    "price_fetch": "価格取得（楽天）",
    "rakuten_keyword": "楽天の検索条件に合わない商品名（商品名の整形が必要）",
    "yahoo": "価格取得（Yahoo!）",
    "popularity": "人気ランキング",
    "consumables": "消耗品コーナー",
    "discovery": "新商品の自動発見",
    "analysis": "商品分析",
    "ai_generation": "AI説明文",
    "price_alert_email": "値下がり通知メール",
    "x_post": "X投稿",
    "daily_report": "日次レポート",
    "content_optimizer": "AIコンテンツ最適化",
    "image_backfill": "商品画像",
    "title_cleanup": "商品名の整形",
    "csv_import": "CSV取り込み",
}


@dataclasses.dataclass
class Remedy:
    label: str
    attempted: int
    succeeded: int


@dataclasses.dataclass
class HealResult:
    errors_seen: int = 0
    remedies: list[Remedy] = dataclasses.field(default_factory=list)
    needs_setup: list[str] = dataclasses.field(default_factory=list)  # "<label>: <what to check>"
    quota_limited: list[str] = dataclasses.field(default_factory=list)  # labels
    unresolved: list[str] = dataclasses.field(default_factory=list)  # "<label> N件"
    repeat_failures: list[str] = dataclasses.field(default_factory=list)  # product names
    repeat_failures_total: int = 0
    skipped_for_time: bool = False
    summary: str = ""
    # Products whose Rakuten price was looked up again (their analysis is
    # stale until re-run - the daily job's analysis stage does that).
    refetched_product_ids: list[int] = dataclasses.field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        return bool(
            self.needs_setup
            or self.unresolved
            or self.repeat_failures
            or any(r.succeeded < r.attempted for r in self.remedies)
        )


def _logical_source(log: models.ErrorLog) -> str:
    # Yahoo lookups share source="price_fetch" with Rakuten; tell them apart
    # by the "Yahoo" prefix every Yahoo message starts with.
    if log.source == "price_fetch" and log.message.startswith("Yahoo"):
        return "yahoo"
    return log.source


def _label(source: str) -> str:
    return _SOURCE_LABELS.get(source, source)


def classify(log: models.ErrorLog) -> str:
    """'keyword' | 'setup' | 'quota' | 'transient' for one error-level row."""
    if _KEYWORD_PATTERN.search(log.message):
        return "keyword"
    if _CONFIG_PATTERN.search(log.message):
        return "setup"
    if _QUOTA_PATTERN.search(log.message):
        return "quota"
    return "transient"


def latest_watermark(db: Session) -> int:
    """The newest ErrorLog id right now - pass it to heal() as since_id to
    look only at rows written after this point (the daily job takes one
    at its start). Ids, not timestamps: created_at is set by the database
    clock, which needn't match this process's."""
    newest = db.execute(select(models.ErrorLog.id).order_by(models.ErrorLog.id.desc()).limit(1)).scalar()
    return newest or 0


def default_since_id(db: Session) -> int:
    """For a manual run: everything after the last self-heal summary, or -
    if there has never been one - the last 24 hours of rows."""
    last_summary = db.execute(
        select(models.ErrorLog.id)
        .where(models.ErrorLog.source == SOURCE)
        .order_by(models.ErrorLog.id.desc())
        .limit(1)
    ).scalar()
    if last_summary:
        return last_summary
    newest = db.execute(select(models.ErrorLog).order_by(models.ErrorLog.id.desc()).limit(1)).scalar()
    if newest is None or newest.created_at is None:
        return 0
    cutoff = newest.created_at - datetime.timedelta(hours=24)
    oldest_in_window = db.execute(
        select(models.ErrorLog.id)
        .where(models.ErrorLog.created_at >= cutoff)
        .order_by(models.ErrorLog.id.asc())
        .limit(1)
    ).scalar()
    return (oldest_in_window or 1) - 1


def _repeat_failures(db: Session) -> tuple[list[str], int]:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=REPEAT_WINDOW_DAYS)
    rows = db.execute(
        select(models.ErrorLog.product_id, models.ErrorLog.created_at, models.ErrorLog.level, models.ErrorLog.message)
        .where(
            models.ErrorLog.source == "price_fetch",
            models.ErrorLog.product_id.is_not(None),
            models.ErrorLog.created_at >= cutoff,
        )
    ).all()
    days: dict[int, set[datetime.date]] = {}
    for product_id, created_at, level, message in rows:
        if message.startswith("Yahoo") or created_at is None:
            continue
        if level == "error" or "見つかりませんでした" in message:
            days.setdefault(product_id, set()).add(created_at.date())
    flagged_ids = sorted(pid for pid, d in days.items() if len(d) >= REPEAT_MIN_DAYS)
    if not flagged_ids:
        return [], 0
    products = db.execute(select(models.Product).where(models.Product.id.in_(flagged_ids))).scalars().all()
    names = sorted(p.name for p in products)  # a deleted product drops out here
    return names[:MAX_LISTED_NAMES], len(names)


def _summarize(result: HealResult) -> str:
    parts = [f"{SUMMARY_PREFIX}: 確認したエラー{result.errors_seen}件"]
    if result.remedies:
        parts.append(
            "再実行 " + " / ".join(f"{r.label} {r.succeeded}/{r.attempted}件成功" for r in result.remedies)
        )
    elif result.errors_seen:
        parts.append("自動で再実行できるエラーはありませんでした")
    if result.quota_limited:
        parts.append("利用上限のため明日自動で再開: " + "・".join(result.quota_limited))
    if result.needs_setup:
        parts.append("要設定確認: " + " / ".join(result.needs_setup))
    if result.unresolved:
        parts.append("自動では直せないエラー（ログを確認してください）: " + "・".join(result.unresolved))
    if result.repeat_failures:
        more = result.repeat_failures_total - len(result.repeat_failures)
        names = "、".join(result.repeat_failures) + (f" ほか{more}件" if more > 0 else "")
        parts.append(
            f"直近{REPEAT_WINDOW_DAYS}日で{REPEAT_MIN_DAYS}日以上、楽天で価格を取得できていない商品"
            f"（商品名の見直しが必要）: {names}"
        )
    if result.skipped_for_time:
        parts.append("時間の上限に達したため、一部の再実行は明日に持ち越し")
    return "。".join(parts) + "。"


def heal(db: Session, since_id: int, clock: Callable[[], float] = time.monotonic) -> HealResult:
    """Looks at error-level rows with id > since_id, applies the known
    fixes, and writes one summary row. Never raises - a remedy that blows
    up is logged and counted as not fixed."""
    started = clock()
    result = HealResult()
    settings = get_settings()

    errors = list(
        db.execute(
            select(models.ErrorLog)
            .where(models.ErrorLog.id > since_id, models.ErrorLog.level == "error", models.ErrorLog.source != SOURCE)
            .order_by(models.ErrorLog.id.asc())
        ).scalars().all()
    )
    errors = [log for log in errors if not log.message.startswith(_RESTATEMENT_PREFIXES)]
    result.errors_seen = len(errors)

    retry_rakuten: set[int] = set()
    retry_yahoo: set[int] = set()
    retry_popularity = False
    retry_consumables = False
    unresolved_counts: dict[str, int] = {}
    setup_seen: set[str] = set()
    quota_seen: set[str] = set()

    for log in errors:
        source = _logical_source(log)
        kind = classify(log)
        if kind == "keyword":
            # Retrying sends the same keyword again; the product name needs work.
            unresolved_counts["rakuten_keyword"] = unresolved_counts.get("rakuten_keyword", 0) + 1
            continue
        if kind == "setup":
            if source not in setup_seen:
                setup_seen.add(source)
                hint = _CONFIG_HINTS.get(source, "該当する環境変数")
                result.needs_setup.append(f"{_label(source)}（{hint}を確認）")
            continue
        if kind == "quota":
            if source not in quota_seen:
                quota_seen.add(source)
                result.quota_limited.append(_label(source))
            continue
        if source == "price_fetch" and log.product_id is not None:
            retry_rakuten.add(log.product_id)
        elif source == "yahoo" and log.product_id is not None and settings.yahoo_client_id:
            retry_yahoo.add(log.product_id)
        elif source == "popularity":
            retry_popularity = True
        elif source == "consumables":
            retry_consumables = True
        else:
            unresolved_counts[source] = unresolved_counts.get(source, 0) + 1

    def _time_left() -> bool:
        if clock() - started < TIME_BUDGET_SECONDS:
            return True
        result.skipped_for_time = True
        return False

    def _run(label: str, attempted: int, fn: Callable[[], int]) -> None:
        if attempted == 0 or not _time_left():
            return
        try:
            succeeded = fn()
        except Exception as exc:  # noqa: BLE001 - a failed remedy is reported, never fatal
            db.rollback()
            crud.create_error_log(db, source=SOURCE, level="warning", message=f"{label}の再実行に失敗しました: {exc}")
            succeeded = 0
        result.remedies.append(Remedy(label=label, attempted=attempted, succeeded=min(succeeded, attempted)))

    rakuten_ids = sorted(retry_rakuten)[:MAX_PRODUCT_RETRIES]
    result.refetched_product_ids = rakuten_ids
    _run(
        "楽天の価格再取得",
        len(rakuten_ids),
        lambda: pipeline.fetch_rakuten_prices(db, only_product_ids=rakuten_ids)[0],
    )
    yahoo_ids = sorted(retry_yahoo)[:MAX_PRODUCT_RETRIES]
    _run(
        "Yahoo!の価格再取得",
        len(yahoo_ids),
        lambda: pipeline.fetch_yahoo_prices(db, only_product_ids=yahoo_ids)[0],
    )
    if retry_popularity:
        total = len(popularity.CATEGORY_GENRE_IDS)
        _run("人気ランキングのカテゴリ再取得", total, lambda: popularity.sync_popularity_rankings(db)[1])
    if retry_consumables:
        # Success = the refresh ran through again (its own per-item skips
        # are routine "no matching listing" cases, logged as info).
        _run("消耗品の価格再取得", 1, lambda: (consumables_merchandiser.refresh_consumable_prices(db), 1)[1])
    if len(retry_rakuten) > len(rakuten_ids) or len(retry_yahoo) > len(yahoo_ids):
        result.skipped_for_time = True

    result.unresolved = [f"{_label(src)} {n}件" for src, n in unresolved_counts.items()]
    try:
        result.repeat_failures, result.repeat_failures_total = _repeat_failures(db)
    except Exception:  # noqa: BLE001 - the flag list is a bonus, never fatal
        db.rollback()

    result.summary = _summarize(result)
    crud.create_error_log(
        db, source=SOURCE, level="warning" if result.needs_attention else "info", message=result.summary
    )
    return result
