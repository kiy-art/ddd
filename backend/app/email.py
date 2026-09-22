"""Client for sending transactional email via Resend (https://resend.com).

Resend's free plan (no credit card required) covers this: 3,000 emails/
month, 100/day, and sending works immediately with the shared
onboarding@resend.dev address - no domain verification needed to ship this
feature (see RESEND_FROM_EMAIL in config.py; a verified custom domain can
be swapped in later purely by changing that env var, no code change).

https://resend.com/docs/api-reference/emails/send-email
"""

import httpx

from app.config import get_settings

SEND_URL = "https://api.resend.com/emails"


class ResendNotConfigured(Exception):
    pass


class EmailSendError(Exception):
    pass


def send_email(to: str, subject: str, html: str, timeout: float = 10.0) -> None:
    """Raises ResendNotConfigured / EmailSendError on failure - callers
    decide how to handle that (see pipeline.send_price_alert_notifications,
    which logs and leaves the alert unsent so it's retried next run)."""
    settings = get_settings()
    if not settings.resend_api_key:
        raise ResendNotConfigured("RESEND_API_KEY is not configured")

    response = httpx.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.resend_from_email, "to": [to], "subject": subject, "html": html},
        timeout=timeout,
    )
    if response.is_error:
        raise EmailSendError(f"Resend API {response.status_code}: {response.text[:500]}")


def price_alert_email_html(product_name: str, product_url: str, current_price: int, target_price: int) -> str:
    """Plain, factual content only - the real current price and the
    subscriber's own target price, no urgency language or fabricated
    claims (matches the site's honesty stance elsewhere)."""
    return f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; color: #14130f;">
      <p style="font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; color: #a5670e;">PAR. 値下がり通知</p>
      <h1 style="font-size: 20px; margin: 8px 0 16px;">{product_name}</h1>
      <p style="font-size: 15px; line-height: 1.6;">
        設定していただいた目標価格 <strong>¥{target_price:,}</strong> 以下になりました。<br>
        現在価格：<strong style="font-size: 20px;">¥{current_price:,}</strong>
      </p>
      <p style="margin: 24px 0;">
        <a href="{product_url}" style="background: #d3852e; color: #fff; padding: 12px 24px; border-radius: 999px; text-decoration: none; font-weight: 600;">
          商品ページで詳細を見る
        </a>
      </p>
      <p style="font-size: 12px; color: #6b6a63; line-height: 1.6;">
        ※価格・在庫は変動するため、購入前に販売元サイトで最新価格をご確認ください。このメールは、以前このサイトで値下がり通知を設定された方にお送りしています。
      </p>
    </div>
    """
