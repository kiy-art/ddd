"""STEP75 (approval #003, option 1A): deletes personal data that has
passed the retention period stated on /privacy.

- Price alerts: 90 days after the notification was sent, or 1 year after
  registration when it was never sent.
- Contact messages: 1 year after they were read (there is no "handled"
  column, so read_at stands in for it). Unread ones are kept.

Deletion cannot be undone, so the admin endpoint defaults to a dry run
that only counts (POST /admin/run-retention-purge, routers/admin.py), and
the plan lines carry row ids and dates - never an email address, since
they are written to the error log.
"""

import dataclasses
import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import models

ALERT_AFTER_SENT_DAYS = 90
ALERT_UNSENT_DAYS = 365
CONTACT_AFTER_READ_DAYS = 365


@dataclasses.dataclass
class RetentionPurgeResult:
    applied: bool
    price_alerts: int
    contact_messages: int
    plan_lines: list[str]


def run_retention_purge(
    db: Session, apply: bool, now: datetime.datetime | None = None
) -> RetentionPurgeResult:
    now = now or datetime.datetime.utcnow()
    sent_cutoff = now - datetime.timedelta(days=ALERT_AFTER_SENT_DAYS)
    unsent_cutoff = now - datetime.timedelta(days=ALERT_UNSENT_DAYS)
    read_cutoff = now - datetime.timedelta(days=CONTACT_AFTER_READ_DAYS)

    alerts = list(
        db.execute(
            select(models.PriceAlert).where(
                or_(
                    and_(models.PriceAlert.notified_at.is_not(None), models.PriceAlert.notified_at < sent_cutoff),
                    and_(models.PriceAlert.notified_at.is_(None), models.PriceAlert.created_at < unsent_cutoff),
                )
            )
        )
        .scalars()
        .all()
    )
    messages = list(
        db.execute(
            select(models.ContactMessage).where(
                models.ContactMessage.read_at.is_not(None), models.ContactMessage.read_at < read_cutoff
            )
        )
        .scalars()
        .all()
    )

    lines = [
        f"値下がり通知 #{a.id}: "
        + (f"送信 {a.notified_at:%Y-%m-%d}（{ALERT_AFTER_SENT_DAYS}日経過）" if a.notified_at else f"登録 {a.created_at:%Y-%m-%d}（未送信・1年経過）")
        for a in alerts
    ] + [f"お問い合わせ #{m.id}: 既読 {m.read_at:%Y-%m-%d}（1年経過）" for m in messages]

    if apply:
        for row in [*alerts, *messages]:
            db.delete(row)
        db.commit()
    return RetentionPurgeResult(
        applied=apply, price_alerts=len(alerts), contact_messages=len(messages), plan_lines=lines
    )
