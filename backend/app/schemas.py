import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

from app.models import AFFILIATE_SHOPS, BUY_SCORES, CATEGORIES, PERFORMANCE_TYPES, SKILL_LEVELS


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
    msrp: int | None = None
    release_date: datetime.date | None = None
    skill_level: str | None = Field(default=None, pattern="^(" + "|".join(SKILL_LEVELS) + ")$")
    performance_type: str | None = Field(default=None, pattern="^(" + "|".join(PERFORMANCE_TYPES) + ")$")
    is_current_generation: bool | None = None


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
    msrp: int | None = None
    release_date: datetime.date | None = None
    skill_level: str | None = Field(default=None, pattern="^(" + "|".join(SKILL_LEVELS) + ")$")
    performance_type: str | None = Field(default=None, pattern="^(" + "|".join(PERFORMANCE_TYPES) + ")$")
    is_current_generation: bool | None = None


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
    popularity_rank: int | None
    popularity_updated_at: datetime.datetime | None
    yahoo_price: int | None
    yahoo_url: str | None
    yahoo_updated_at: datetime.datetime | None
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


class AutoFixLogsResult(BaseModel):
    deleted: dict[str, int]
    total_deleted: int
    remaining_by_level: dict[str, int]


class BrandSummary(BaseModel):
    brand: str
    product_count: int


class BrandPriceMover(BaseModel):
    product_slug: str
    product_name: str
    change_percent: float


class BrandPriceStats(BaseModel):
    """Real, aggregate price-movement stats for one brand, computed from its
    products' own recorded PriceHistory (see crud.get_brand_price_stats) -
    never a per-brand editorial claim. None fields mean "not enough data",
    not zero."""

    brand: str
    tracked_count: int
    reliable_count: int
    declining_count: int
    rising_count: int
    flat_count: int
    average_change_percent: float | None
    average_msrp_discount_percent: float | None
    biggest_decline: BrandPriceMover | None


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


class AffiliateClickCreate(BaseModel):
    product_id: int | None = None
    category: str | None = Field(default=None, pattern="^(" + "|".join(CATEGORIES) + ")$")
    shop: str = Field(pattern="^(" + "|".join(AFFILIATE_SHOPS) + ")$")
    placement: str = Field(min_length=1, max_length=30)


class AffiliateClickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    category: str | None
    shop: str
    placement: str
    created_at: datetime.datetime


class AffiliateClickRecentOut(AffiliateClickOut):
    product_name: str | None
    product_slug: str | None


class ShopClickCount(BaseModel):
    shop: str
    count: int


class ProductClickCount(BaseModel):
    product_id: int
    product_name: str
    product_slug: str
    clicks: int


class AffiliateClickSummary(BaseModel):
    total: int
    by_shop: list[ShopClickCount]
    top_products: list[ProductClickCount]
    recent: list[AffiliateClickRecentOut]


class PageStatOut(BaseModel):
    path: str
    pageviews: int
    active_users: int
    bounce_rate: float
    avg_engagement_seconds: float


class AiOptimizationActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_type: str
    target_path: str
    product_id: int | None
    guide_slug: str | None
    decision_basis: str
    content_before: str | None
    content_after: str | None
    status: str
    created_at: datetime.datetime
    effect_evaluated_at: datetime.datetime | None
    effect_summary: str | None
    effect_verdict: str | None
    reverted_at: datetime.datetime | None


class ContentOptimizationRunResult(BaseModel):
    snapshot_captured: bool
    actions_evaluated: int
    actions_applied: int
    actions: list[AiOptimizationActionOut]


class GuideSectionSchema(BaseModel):
    heading: str
    paragraphs: list[str]


class GuideArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    description: str
    published_at: datetime.date
    related_categories: list[str]
    featured_kind: str | None
    featured_category: str | None
    featured_heading: str | None
    featured_limit: int | None
    sections: list[GuideSectionSchema]
    source: str


class TrendingProductsOut(BaseModel):
    decision_basis: str | None
    products: list[ProductOut]


class ImprovementOpportunityOut(BaseModel):
    product_id: int
    product_name: str
    target_path: str
    goal: str
    decision_basis: str
    est_extra_shop_clicks: float
    priority_score: float
    shop_click_rate_known: bool
