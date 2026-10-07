"""Daily "AI会議" report - a real-data-only Japanese summary of the
previous day's batch run, click trend, and error/warning counts, emailed
to the site owner every morning via the existing Resend integration (see
app/email.py). Composed with the same rule-based, non-LLM logic as
frontend/components/AiTeamDashboard.tsx's buildPlanningSession() - no
Claude API call, no invented numbers. Every line either quotes a real
value directly or applies a simple, stated threshold to one.

"収益" itself is never reported as a yen figure: no API integration with
Rakuten/Amazon/Yahoo affiliate networks exists to know actual commission
earned, so click counts (this site's own first-party AffiliateClick
table) are reported honestly as a leading indicator, not a revenue
estimate."""

import collections
import datetime
import html as html_lib
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import crud, email, models, self_heal, x_post
from app.analytics_ga4 import GA4NotConfigured, get_top_pages
from app.config import get_settings

SHOP_LABELS = {"amazon": "Amazon", "rakuten": "楽天", "yahoo": "Yahoo!", "official": "公式サイト"}

OPTIMIZATION_ACTION_LABELS = {
    "rewrite_product": "商品説明のリライト",
    "new_guide": "新規ガイド作成",
    "reorder_homepage": "トップページ注目商品の入れ替え",
}


class DailyReportNotConfigured(Exception):
    pass


def _click_counts_between(
    db: Session, start: datetime.datetime, end: datetime.datetime
) -> dict[str, int]:
    rows = db.execute(
        select(models.AffiliateClick.shop, func.count())
        .where(models.AffiliateClick.created_at >= start, models.AffiliateClick.created_at < end)
        .group_by(models.AffiliateClick.shop)
    ).all()
    return {shop: count for shop, count in rows}


# STEP-report-v2 (2026-10-08): the three "改善施策" lines used to fire every
# single day - errors were counted over the last 100 log rows (not the last
# 24h) with no hint of what they were, price_fetch warnings likewise, and a
# shop with 0 clicks in a 24h window was flagged as a link-visibility
# problem even when the whole site only gets ~2 clicks a day. Each line now
# names its actual cause: the top error/warning patterns of the last 24h
# by source, and a 7-day click view that separates "too little traffic"
# from "this one shop's button isn't being clicked".
_URL_PATTERN = re.compile(r"https?://\S+")
_PAREN_PATTERN = re.compile(r"[（(][^（）()]*[）)]")
_NUMBER_PATTERN = re.compile(r"[¥￥]?\d[\d,]*")


def _log_pattern(log: models.ErrorLog, product_names: dict[int, str]) -> str:
    """The message with what varies per product removed - product name,
    URLs, parenthesised details (keyword, matched listing), numbers - so
    the same cause hitting 200 products counts as one pattern."""
    message = log.message
    name = product_names.get(log.product_id) if log.product_id is not None else None
    if name:
        message = message.replace(name, "〈商品〉")
    message = _URL_PATTERN.sub("", message)
    message = _PAREN_PATTERN.sub("", message)
    message = _NUMBER_PATTERN.sub("N", message)
    message = re.sub(r"\s+", " ", message).strip()
    return message[:80] + ("…" if len(message) > 80 else "")


class LogSummary:
    def __init__(self, total: int, by_source: list[tuple[str, int, list[tuple[str, int]]]]):
        self.total = total
        # [(source label, count, [(pattern, count), ... top 2])], most frequent first
        self.by_source = by_source

    def top_line(self) -> str:
        if not self.by_source:
            return ""
        label, count, patterns = self.by_source[0]
        pattern, pattern_count = patterns[0]
        return f"{label}の「{pattern}」（{pattern_count}件）"

    def html_details(self) -> str:
        parts = []
        for label, count, patterns in self.by_source[:4]:
            pats = " / ".join(f"「{html_lib.escape(p)}」{c}件" for p, c in patterns)
            parts.append(f"{html_lib.escape(label)} {count}件：{pats}")
        return "<br>".join(parts)


def _summarize_logs(db: Session, since: datetime.datetime, level: str, source: str | None = None) -> LogSummary:
    query = select(models.ErrorLog).where(models.ErrorLog.created_at >= since, models.ErrorLog.level == level)
    if source is not None:
        query = query.where(models.ErrorLog.source == source)
    logs = list(db.execute(query).scalars().all())
    product_ids = {log.product_id for log in logs if log.product_id is not None}
    product_names: dict[int, str] = {}
    if product_ids:
        rows = db.execute(
            select(models.Product.id, models.Product.name).where(models.Product.id.in_(product_ids))
        ).all()
        product_names = {pid: name for pid, name in rows}

    grouped: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for log in logs:
        grouped[self_heal._label(self_heal._logical_source(log))][_log_pattern(log, product_names)] += 1
    by_source = sorted(
        ((label, sum(c.values()), c.most_common(2)) for label, c in grouped.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    return LogSummary(len(logs), by_source)


def _format_change(today: int, yesterday: int) -> str:
    if yesterday == 0:
        return "比較対象となる前日データがありません" if today == 0 else f"前日は0件でした（{today}件に増加）"
    diff = today - yesterday
    pct = round(diff / yesterday * 100)
    sign = "+" if diff > 0 else ""
    return f"前日比 {sign}{diff}件（{sign}{pct}%）"


def build_daily_report(db: Session) -> tuple[str, str]:
    """Returns (subject, html_body). Pure computation - never sends
    anything itself, so it's trivially testable/previewable without
    Resend configured."""
    now = datetime.datetime.utcnow()
    today_jst_label = (now + datetime.timedelta(hours=9)).strftime("%Y年%m月%d日")

    day_start = now - datetime.timedelta(days=1)
    prev_day_start = now - datetime.timedelta(days=2)
    today_by_shop = _click_counts_between(db, day_start, now)
    prev_by_shop = _click_counts_between(db, prev_day_start, day_start)
    today_total = sum(today_by_shop.values())
    prev_total = sum(prev_by_shop.values())

    logs = crud.list_error_logs(db, limit=100)
    daily_job_log = next((log for log in logs if log.source == "daily_job"), None)
    self_heal_log = next((log for log in logs if log.source == "self_heal"), None)
    errors = _summarize_logs(db, day_start, "error")
    price_warnings = _summarize_logs(db, day_start, "warning", source="price_fetch")
    error_count = errors.total
    price_warning_count = price_warnings.total

    week_start = now - datetime.timedelta(days=7)
    week_by_shop = _click_counts_between(db, week_start, now)
    week_total = sum(week_by_shop.get(s, 0) for s in ("amazon", "rakuten", "yahoo"))
    published = db.execute(
        select(func.count()).select_from(models.Product).where(models.Product.pending_review.is_(False))
    ).scalar_one()
    with_yahoo_price = db.execute(
        select(func.count())
        .select_from(models.Product)
        .where(models.Product.pending_review.is_(False), models.Product.yahoo_price.is_not(None))
    ).scalar_one()
    yahoo_quota_hit = (
        db.execute(
            select(func.count())
            .select_from(models.ErrorLog)
            .where(models.ErrorLog.created_at >= day_start, models.ErrorLog.message.like("Yahoo: quota exhausted%"))
        ).scalar_one()
        > 0
    )
    settings = get_settings()
    yahoo_affiliate_ready = bool(settings.yahoo_affiliate_id.strip() and settings.yahoo_affiliate_pid.strip())

    try:
        top_pages = get_top_pages(days=1, limit=3)
        ga4_configured = True
    except GA4NotConfigured:
        top_pages = []
        ga4_configured = False

    lines: list[str] = []

    # CSO: yesterday's batch run
    lines.append(
        f"【新商品・価格取得】{daily_job_log.message}"
        if daily_job_log
        else "【新商品・価格取得】直近24時間の日次バッチ実行記録が見つかりませんでした。GitHub Actionsの実行状況をご確認ください。"
    )

    # CRO: click trend
    shop_breakdown = (
        " / ".join(f"{SHOP_LABELS.get(shop, shop)} {count}件" for shop, count in today_by_shop.items())
        if today_by_shop
        else "記録なし"
    )
    lines.append(f"【アフィリエイトクリック】直近24時間で{today_total}件（{shop_breakdown}）。{_format_change(today_total, prev_total)}。")

    # CPO: pipeline health
    lines.append(
        f"【システム状況】直近24時間のエラーは{error_count}件です。内訳：<br>{errors.html_details()}"
        if error_count > 0
        else "【システム状況】直近24時間のエラーは0件です。パイプラインは安定稼働中です。"
    )

    # STEP54: what the self-heal pass retried / couldn't fix (app/self_heal.py)
    if self_heal_log:
        lines.append(f"【自動修復】{self_heal_log.message.removeprefix('自動修復: ')}")

    # Compliance: price display accuracy
    if price_warning_count > 0:
        lines.append(
            f"【価格表示】直近24時間の価格取得の警告は{price_warning_count}件です（誤った価格を出さないために反映を止めたもので、該当商品は前回の価格のままです）。"
            f"内訳：<br>{price_warnings.html_details()}"
        )

    # CMO: search traffic
    if ga4_configured and top_pages:
        top = top_pages[0]
        lines.append(f"【検索流入】直近24時間で最もPVが多いページは「{top.path}」（{top.pageviews}PV）でした。")
    elif ga4_configured:
        lines.append("【検索流入】GA4は設定済みですが、直近24時間のページビューはまだ記録されていません。")
    else:
        lines.append("【検索流入】GA4のサーバー側連携（GA4_PROPERTY_ID/GA4_SERVICE_ACCOUNT_JSON）が未設定のため、詳細なページ別データは取得できません。")

    # CEO: rule-based next actions
    actions: list[str] = []
    # Clicks: judged on 7 days, not 24h - at a few clicks a day, any one
    # shop has 0 on most days without anything being wrong with its link.
    missing_week = [s for s in ("amazon", "rakuten", "yahoo") if week_by_shop.get(s, 0) == 0]
    if week_total == 0:
        actions.append(
            "直近7日間、どのショップへのクリックもありません。リンクの位置より先に、サイトへの訪問自体の少なさが原因です（検索流入・SNSでの集客を優先）。"
        )
    elif missing_week:
        actions.append(
            f"{'・'.join(SHOP_LABELS[s] for s in missing_week)}は直近7日間のクリックが0件です"
            f"（3ショップ合計は{week_total}件）。そのショップのボタンが出ている商品数と位置を確認しましょう。"
        )
    if published and with_yahoo_price / published < 0.3:
        actions.append(
            f"Yahoo!の価格が出ている商品は公開{published}件中{with_yahoo_price}件だけです。"
            "表示されないボタンはクリックされないため、Yahoo!のクリックが少ない主因はここです"
            + ("（日次の取得がYahoo!の利用上限で途中停止しています）。" if yahoo_quota_hit else "。")
        )
    if not yahoo_affiliate_ready:
        actions.append(
            "Yahoo!のリンクはアフィリエイト未設定（バリューコマースのsid・pid）のため、クリックされても報酬になりません。"
        )
    if error_count > 0:
        actions.append(f"エラーの最多原因：{errors.top_line()}。ここから対処しましょう。")
    if price_warning_count > 0:
        actions.append(
            f"価格取得の警告の最多原因：{price_warnings.top_line()}。反映を止めた商品は前回の価格のままなので、同じ商品が毎日続く場合は商品名の整形か非公開化で解消しましょう。"
        )
    if not ga4_configured:
        actions.append("GA4のサーバー側連携を設定すると、検索流入の詳細分析も日報に含められるようになります。")
    if not actions:
        actions.append("現状、緊急の課題は見当たりません。引き続きデータを蓄積し、明日また評価します。")

    # X (旧Twitter) の無料APIプランでは投稿自体ができなくなった (402) ため、
    # コピペ投稿できるテキストを毎朝この報告に含める - 自動投稿の代替導線。
    # STEP61: 朝・昼・夜の3本 (x_post.build_daily_manual_posts - 朝の分は
    # build_manual_post_text と同じ商品選定・文面)。
    manual_drafts = [d for d in x_post.build_daily_manual_posts(db) if d.text]

    # STEP42: app/content_optimizer.py's autonomous decisions from the last
    # 24h - what it changed and why (always shown), plus any effect
    # measurements that just came in for older changes (only when there
    # are any) - "何を・なぜ変更したか" と "うまくいったか" を毎朝報告する
    # という社長の要望に応える。
    optimization_actions = crud.list_optimization_actions(db, limit=100)
    recent_actions = [a for a in optimization_actions if a.created_at >= day_start]
    recently_evaluated = [
        a for a in optimization_actions if a.effect_evaluated_at is not None and a.effect_evaluated_at >= day_start
    ]

    subject = f"【PAR.】本日のAI会議レポート（{today_jst_label}）"
    body_items = "".join(f'<li style="margin-bottom: 10px; line-height: 1.6;">{line}</li>' for line in lines)
    action_items = "".join(f'<li style="margin-bottom: 6px; line-height: 1.6;">{a}</li>' for a in actions)
    manual_post_block = (
        "".join(
            f'<p style="font-size: 13px; font-weight: 600; margin: 0 0 6px;">{d.label}｜{d.theme}</p>'
            f'<pre style="white-space: pre-wrap; font-family: inherit; font-size: 13px; '
            f'background: #f5f4f0; border-radius: 8px; padding: 12px; margin: 0 0 16px;">{html_lib.escape(d.text)}</pre>'
            for d in manual_drafts
        )
        if manual_drafts
        else '<p style="font-size: 13px; color: #6b6a63; margin: 0 0 24px;">本日は投稿対象となる商品がありません。</p>'
    )

    if recent_actions:
        optimization_items = "".join(
            f'<li style="margin-bottom: 8px; line-height: 1.6;">'
            f"[{OPTIMIZATION_ACTION_LABELS.get(a.action_type, a.action_type)}] {a.target_path}<br>"
            f'<span style="color: #6b6a63; font-size: 13px;">判断根拠: {a.decision_basis}</span></li>'
            for a in recent_actions
        )
        optimization_block = f'<ul style="padding-left: 18px; font-size: 14px; margin: 0 0 12px;">{optimization_items}</ul>'
    else:
        optimization_block = '<p style="font-size: 13px; color: #6b6a63; margin: 0 0 12px;">本日は自動改善の対象がありませんでした。</p>'

    if recently_evaluated:
        worse = [a for a in recently_evaluated if a.effect_verdict == "worse"]
        effect_items = "".join(
            f'<li style="margin-bottom: 6px; line-height: 1.6;">{a.target_path}: {a.effect_summary}</li>'
            for a in recently_evaluated
        )
        optimization_block += (
            f'<p style="font-size: 13px; font-weight: 600; color: #6b6a63; margin: 12px 0 6px;">過去の変更の効果測定</p>'
            f'<ul style="padding-left: 18px; font-size: 14px; margin: 0;">{effect_items}</ul>'
        )
        # STEP44: a "worse" rewrite on a sufficient sample is undone
        # automatically - report it as done, and only ask the president to
        # judge the ones that weren't (thin sample, or a non-rewrite action).
        auto_reverted = [a for a in worse if a.revert_reason == "auto_worse"]
        needs_review = [a for a in worse if a.revert_reason != "auto_worse"]
        if auto_reverted:
            optimization_block += (
                f'<p style="font-size: 13px; color: #b3261e; margin: 8px 0 0;">'
                f"↩ {len(auto_reverted)}件は悪化と判定したため自動で元に戻し、最新の価格データで通常の文面に再生成しました。"
                f"この判定結果は効果測定の記録として蓄積されています。</p>"
            )
        if needs_review:
            optimization_block += (
                f'<p style="font-size: 13px; color: #b3261e; margin: 8px 0 0;">'
                f"⚠ {len(needs_review)}件は悪化と判定されましたが、サンプル数が少ないなどの理由で自動では戻していません。"
                f"管理画面の「AI自動改善ループ」から内容を確認し、必要であれば元に戻してください。</p>"
            )

    html = f"""
    <div style="font-family: sans-serif; max-width: 560px; margin: 0 auto; color: #14130f;">
      <p style="font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; color: #a5670e;">PAR. AI Executive War Room</p>
      <h1 style="font-size: 20px; margin: 8px 0 20px;">本日のAI会議レポート（{today_jst_label}）</h1>

      <ul style="padding-left: 18px; font-size: 14px; margin: 0 0 24px;">{body_items}</ul>

      <p style="font-size: 13px; font-weight: 600; color: #6b6a63; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">改善施策</p>
      <ul style="padding-left: 18px; font-size: 14px; margin: 0 0 24px;">{action_items}</ul>

      <p style="font-size: 13px; font-weight: 600; color: #6b6a63; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">本日のAI自動改善</p>
      <div style="margin: 0 0 24px;">{optimization_block}</div>

      <p style="font-size: 13px; font-weight: 600; color: #6b6a63; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">X投稿用テキスト（朝・昼・夜のコピペ用）</p>
      {manual_post_block}

      <p style="font-size: 12px; color: #6b6a63; line-height: 1.6;">
        ※このレポートに含まれる数値はすべて実データ（自社DBの記録）に基づいており、AIによる推測・作文は含まれていません。
        「クリック数」は実際の売上・収益とは異なり、あくまで先行指標としてご覧ください（実際の報酬額は各ASPの管理画面でご確認ください）。
      </p>
    </div>
    """
    return subject, html


def send_daily_report(db: Session) -> None:
    """No-ops (raises DailyReportNotConfigured, caught by the caller) when
    DAILY_REPORT_EMAIL isn't set - same "optional integration" treatment
    as resend_api_key/yahoo_client_id elsewhere in this codebase."""
    settings = get_settings()
    if not settings.daily_report_email:
        raise DailyReportNotConfigured("DAILY_REPORT_EMAIL is not configured")
    subject, html = build_daily_report(db)
    email.send_email(to=settings.daily_report_email, subject=subject, html=html)
