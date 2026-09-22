import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

from app.models import BUY_SCORES, CATEGORIES


class PriceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: int
    recorded_at: datetime.datetime


class ProductBase(BaseModel):
    name: str
    brand: str
    category: str = Field(pattern="^(" + "|".join(CATEGORIES) + ")$")
    model_number: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    affiliate_url: str | None = None


class ProductCreate(ProductBase):
    slug: str | None = None
    initial_price: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    category: str | None = Field(default=None, pattern="^(" + "|".join(CATEGORIES) + ")$")
    model_number: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    affiliate_url: str | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    current_price: int | None
    previous_price: int | None
    lowest_price: int | None
    average_price: int | None
    price_change_percent: float | None
    buy_score: str
    buy_signal_score: int | None
    history_span_days: int
    buy_reason: str | None
    pending_review: bool
    forecast_confidence: str | None
    forecast_center_price: int | None
    forecast_low_price: int | None
    forecast_high_price: int | None
    forecast_target_date: datetime.datetime | None
    forecast_trend: str | None
    forecast_reason: str | None
    ai_title: str | None
    ai_summary: str | None
    ai_caution: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ProductDetailOut(ProductOut):
    price_history: list[PriceHistoryOut] = []


class PriceCreate(BaseModel):
    price: int
    recorded_at: datetime.datetime | None = None


class ErrorLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    source: str
    product_id: int | None
    message: str
    created_at: datetime.datetime


class BrandSummary(BaseModel):
    brand: str
    product_count: int


class PriceAnomalyOut(BaseModel):
    price_history_id: int
    product_id: int
    product_name: str
    product_slug: str
    price: int
    recorded_at: datetime.datetime
    reference_price: int
    ratio: float


class CsvImportResult(BaseModel):
    created_products: int
    updated_products: int
    prices_recorded: int
    errors: list[str]


class BuyScoreLiteral(BaseModel):
    value: str = Field(pattern="^(" + "|".join(BUY_SCORES) + ")$")


class PriceAlertCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    target_price: int = Field(gt=0)


class PriceAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    email: str
    target_price: int
    created_at: datetime.datetime
    notified_at: datetime.datetime | None


class PriceAlertAdminOut(PriceAlertOut):
    product_name: str
    product_slug: str
    current_price: int | None
    triggered: bool


class ContactMessageCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    message: str = Field(min_length=1, max_length=5000)


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    email: str
    message: str
    created_at: datetime.datetime
    read_at: datetime.datetime | None


class PageStatOut(BaseModel):
    path: str
    pageviews: int
    active_users: int
    bounce_rate: float
    avg_engagement_seconds: float
