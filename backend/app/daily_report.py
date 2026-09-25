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

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import crud, email, models
from app.analytics_ga4 import GA4NotConfigured, get_top_pages
from app.config import get_settings

SHOP_LABELS = {"amazon": "Amazon", "rakuten": "楽天", "yahoo": "Yahoo!", "official": "公式サイト"}


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
    error_count = sum(1 for log in logs if log.level == "error")
    price_warning_count = sum(1 for log in logs if log.level == "warning" and log.source == "price_fetch")

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
        f"【システム状況】直近のログにエラーが{error_count}件あります。商品管理ページでの確認をおすすめします。"
        if error_count > 0
        else "【システム状況】直近のログにエラーは見当たりません。パイプラインは安定稼働中です。"
    )

    # Compliance: price display accuracy
    if price_warning_count > 0:
        lines.append(
            f"【価格表示】価格乖離・アクセサリ誤検出などの警告が{price_warning_count}件あります。表示価格の正確性を優先して確認しましょう。"
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
    seen_shops = set(today_by_shop.keys())
    missing_shops = [s for s in ("amazon", "rakuten", "yahoo") if s not in seen_shops]
    if missing_shops:
        actions.append(f"{'・'.join(SHOP_LABELS[s] for s in missing_shops)}へのクリックが未記録です。リンクの表示位置・視認性を確認しましょう。")
    if error_count > 0:
        actions.append("エラーログの内容を確認し、原因を特定しましょう。")
    if price_warning_count > 0:
        actions.append("価格表示の警告（price_fetch）の内容を確認し、表示価格の正確性を優先しましょう。")
    if not ga4_configured:
        actions.append("GA4のサーバー側連携を設定すると、検索流入の詳細分析も日報に含められるようになります。")
    if not actions:
        actions.append("現状、緊急の課題は見当たりません。引き続きデータを蓄積し、明日また評価します。")

    subject = f"【PAR.】本日のAI会議レポート（{today_jst_label}）"
    body_items = "".join(f'<li style="margin-bottom: 10px; line-height: 1.6;">{line}</li>' for line in lines)
    action_items = "".join(f'<li style="margin-bottom: 6px; line-height: 1.6;">{a}</li>' for a in actions)

    html = f"""
    <div style="font-family: sans-serif; max-width: 560px; margin: 0 auto; color: #14130f;">
      <p style="font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; color: #a5670e;">PAR. AI Executive War Room</p>
      <h1 style="font-size: 20px; margin: 8px 0 20px;">本日のAI会議レポート（{today_jst_label}）</h1>

      <ul style="padding-left: 18px; font-size: 14px; margin: 0 0 24px;">{body_items}</ul>

      <p style="font-size: 13px; font-weight: 600; color: #6b6a63; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">改善施策</p>
      <ul style="padding-left: 18px; font-size: 14px; margin: 0 0 24px;">{action_items}</ul>

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
