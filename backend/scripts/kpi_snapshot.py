"""STEP71: record this week's KPIs into the company knowledge base.

Fetches GET /api/admin/kpi-summary from production and
  - saves the full response to docs/knowledge/kpi/YYYY-MM-DD.json
  - appends one row of headline numbers to docs/knowledge/kpi_ledger.csv

Run by the weekly management meeting (.claude/skills/ai-company-meeting).
Auth comes from the cloud environment's API credential for
golf-deals-backend.onrender.com (injected by the proxy, never visible
here); PAR_ADMIN_API_TOKEN is a fallback. API base: PAR_API_BASE.

    python scripts/kpi_snapshot.py            # fetch and record
    python scripts/kpi_snapshot.py --dry-run  # fetch and print the row only
"""

import argparse
import csv
import datetime
import json
import os
import pathlib
import sys

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "docs" / "knowledge"
LEDGER = KNOWLEDGE / "kpi_ledger.csv"

COLUMNS = [
    "date",
    "published_products",
    "products_with_image",
    "pending_review",
    "shop_clicks_total",
    "shop_clicks_7d",
    "shop_clicks_prev_7d",
    "search_snapshot_date",
    "search_impressions_3d",
    "search_clicks_3d",
    "search_ctr",
    "search_avg_position",
    "ga4_snapshot_date",
    "ga4_pageviews_1d",
    "price_alerts_total",
    "errors_7d",
    "revenue_jpy_month_to_date",  # filled by hand from ASP reports (経理)
    "note",
]


def ledger_row(summary: dict, today: datetime.date) -> dict:
    sc = summary.get("search_console") or {}
    ga = summary.get("ga4") or {}
    cat = summary.get("catalog") or {}
    clicks = summary.get("shop_clicks") or {}
    return {
        "date": today.isoformat(),
        "published_products": cat.get("published_products"),
        "products_with_image": cat.get("with_image"),
        "pending_review": cat.get("pending_review"),
        "shop_clicks_total": clicks.get("total"),
        "shop_clicks_7d": clicks.get("last_7d"),
        "shop_clicks_prev_7d": clicks.get("prev_7d"),
        "search_snapshot_date": sc.get("snapshot_date", ""),
        "search_impressions_3d": sc.get("impressions", ""),
        "search_clicks_3d": sc.get("clicks", ""),
        "search_ctr": sc.get("ctr", ""),
        "search_avg_position": sc.get("avg_position", ""),
        "ga4_snapshot_date": ga.get("snapshot_date", ""),
        "ga4_pageviews_1d": ga.get("pageviews", ""),
        "price_alerts_total": (summary.get("price_alerts") or {}).get("total"),
        "errors_7d": sum((summary.get("errors_last_7d") or {}).values()),
        "revenue_jpy_month_to_date": "",
        "note": "",
    }


def record(summary: dict, today: datetime.date, knowledge: pathlib.Path = KNOWLEDGE) -> dict:
    (knowledge / "kpi").mkdir(parents=True, exist_ok=True)
    (knowledge / "kpi" / f"{today.isoformat()}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ledger = knowledge / "kpi_ledger.csv"
    row = ledger_row(summary, today)
    rows = []
    if ledger.exists():
        with ledger.open(encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("date") != row["date"]]  # one row per day
    rows.append(row)
    with ledger.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    # The token normally isn't visible here at all: the cloud environment's
    # "API認証情報" injects the Authorization header on the way out for
    # golf-deals-backend.onrender.com. PAR_ADMIN_API_TOKEN is only a fallback.
    token = os.environ.get("PAR_ADMIN_API_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    base = os.environ.get("PAR_API_BASE", "https://golf-deals-backend.onrender.com").rstrip("/")
    try:
        response = httpx.get(f"{base}/api/admin/kpi-summary", headers=headers, timeout=120)
        if response.status_code in (401, 403):
            print("Not authorized - set the API credential for the admin API (未取得).", file=sys.stderr)
            return 2
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Could not fetch KPIs: {type(exc).__name__}", file=sys.stderr)
        return 1
    summary = response.json()
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date()  # JST
    if args.dry_run:
        print(json.dumps(ledger_row(summary, today), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(record(summary, today), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
