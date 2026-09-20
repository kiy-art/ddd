import datetime

from pydantic import BaseModel, ConfigDict, Field

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
    buy_reason: str | None
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


class CsvImportResult(BaseModel):
    created_products: int
    updated_products: int
    prices_recorded: int
    errors: list[str]


class BuyScoreLiteral(BaseModel):
    value: str = Field(pattern="^(" + "|".join(BUY_SCORES) + ")$")
