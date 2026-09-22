import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CATEGORIES = ["driver", "iron", "wedge", "putter", "ball"]

BUY_SCORES = ["strong_buy", "buy", "neutral", "not_buy", "insufficient_data"]


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

    current_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lowest_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_signal_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    history_span_days: Mapped[int] = mapped_column(Integer, default=0)

    buy_score: Mapped[str] = mapped_column(String(30), default="insufficient_data")
    buy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    alerts). No email is actually sent yet - no email provider is configured
    - so this only records the request and lets an admin see which alerts
    have already crossed their target, ready to wire up real delivery
    (email/LINE/push) later without changing this schema."""

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
