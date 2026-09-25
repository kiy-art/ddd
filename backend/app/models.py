import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CATEGORIES = ["driver", "iron", "wedge", "putter", "ball"]

# Which real outbound destination a click went to - "official" covers the
# manufacturer's own product page (no affiliate relationship, still worth
# counting separately from a marketplace link).
AFFILIATE_SHOPS = ["amazon", "rakuten", "yahoo", "official"]

BUY_SCORES = ["strong_buy", "buy", "neutral", "not_buy", "insufficient_data"]

# The manufacturer's own stated target skill level for this specific model
# (e.g. PING explicitly markets G440 MAX as its most forgiving/beginner-
# friendly driver in the line, and G440 LST as a lower-spin better-player
# model) - researched per product from official product pages/press
# releases, never inferred from price or guessed. "all_levels" is for a
# model a manufacturer explicitly positions as broadly suitable, not a
# default for "unresearched" (that's None).
SKILL_LEVELS = ["beginner", "all_levels", "advanced"]

# Likewise the manufacturer's own stated performance emphasis for this
# model within its lineup (a "MAX"/forgiveness variant vs an "LS"/low-spin
# distance variant vs a "Tour"/control-shaping variant, etc).
PERFORMANCE_TYPES = ["distance", "forgiveness", "control", "balanced"]


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50), index=True)
    model_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    product_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    affiliate_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Manually-curated facts, not touched by the daily price-fetch pipeline
    # (unlike current_price/average_price/etc below, which sync_product_analysis
    # recomputes from price history every run). msrp is the manufacturer's
    # suggested retail price at launch - a fixed reference point so "XX% off"
    # can mean something concrete, not just "below its own rolling average"
    # (which can itself already be a discounted price).
    msrp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    release_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    # Manufacturer-stated lineup positioning (see SKILL_LEVELS/PERFORMANCE_TYPES
    # above) and whether this is still the brand's current model in this
    # category as of when it was last checked - all three researched facts,
    # None meaning "not researched yet", never a guess from price/specs we
    # don't actually have.
    skill_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    performance_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_current_generation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Rakuten Ichiba's own real-time bestseller rank for this product's
    # category (see app/popularity.py) - refreshed on every sync, and
    # cleared (not left stale) the moment the product drops out of that
    # ranking, unlike msrp/release_date above.
    popularity_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity_updated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # A second, independent price source (Yahoo!ショッピング, see app/yahoo.py)
    # alongside the Rakuten-sourced current_price below - auto-synced the
    # same way, cleared (not left stale) when a fetch finds no match. Never
    # feeds into buy_score/price_change_percent/forecast_*, which stay
    # anchored to the single Rakuten-sourced price_history series so the
    # existing analysis isn't disturbed by a second, independently-noisy
    # source; it exists purely for the store comparison table.
    yahoo_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yahoo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    yahoo_updated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    current_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lowest_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_signal_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    history_span_days: Mapped[int] = mapped_column(Integer, default=0)

    buy_score: Mapped[str] = mapped_column(String(30), default="insufficient_data")
    buy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Short-term price forecast (see app/forecast.py). All nullable: a
    # product without enough price history simply has no forecast rather
    # than a fabricated one - never backfilled with a guess.
    forecast_confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    forecast_center_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forecast_low_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forecast_high_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forecast_target_date: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    forecast_trend: Mapped[str | None] = mapped_column(String(10), nullable=True)
    forecast_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # True for a product auto-discovered via the Rakuten catalog-search
    # pipeline (see app/discovery.py) that an admin hasn't reviewed yet.
    # Hidden from every public endpoint regardless of buy_score until an
    # admin approves it — auto-discovery has no human curation checking
    # brand/model/category are actually correct, unlike a manually-entered
    # or CSV-imported product.
    pending_review: Mapped[bool] = mapped_column(Boolean, default=False)

    ai_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_caution: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ai_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="PriceHistory.recorded_at"
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    price: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="price_history")


class PriceAlert(Base):
    """A "notify me when this drops below ¥X" subscription (spec: price-drop
    alerts). Delivery is email via Resend (see app/email.py,
    pipeline.send_price_alert_notifications) - a no-op until RESEND_API_KEY
    is configured, in which case this still only lets an admin see which
    alerts have already crossed their target (see routers/admin.py's
    list_price_alerts)."""

    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    target_price: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    notified_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    product: Mapped["Product"] = relationship()


class ContactMessage(Base):
    """A message submitted through the public /contact form. No email
    provider is configured (see PriceAlert above for the same constraint),
    so this only records the message for an admin to read in the admin
    panel - nothing is sent automatically."""

    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class AffiliateClick(Base):
    """A single outbound click on a shop/affiliate link (Amazon search,
    Rakuten, Yahoo!ショッピング, or a plain manufacturer link) from a product
    card, product detail page, or comparison view. GA4 already receives the
    same event client-side (see frontend/lib/analytics.ts's trackEvent), but
    that data is only reachable through the GA4 Data API (see
    analytics_ga4.py), which requires separate credentials that may not be
    configured. This table is the site's own first-party record, so the
    admin dashboard's click-count metrics never depend on GA4 being set up."""

    __tablename__ = "affiliate_clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shop: Mapped[str] = mapped_column(String(20), index=True)
    placement: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="error")
    source: Mapped[str] = mapped_column(String(50))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
