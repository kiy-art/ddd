"""Rule-based short-term price forecasting.

Deliberately limited to what real data in this system can actually
support today: a linear trend fit over a product's own recorded price
history (analysis.py's "Phase 1" from the redesign brief - moving
average/trend). The brief also describes forecasting from release-cycle
data, past-generation price curves and per-brand seasonal patterns
(Phases 2-5), but this system has no release_date/series/model-lineage
data for any product, and no product yet has multiple
generations of price history to learn a real cycle from - so those
factors are intentionally left out rather than faking them with
plausible-looking numbers. See SeasonalTrend.tsx for the same "not
enough data yet" stance applied to seasonal analysis.

Nothing here is AI-generated: same input always produces the same
output, same as analysis.py's buy_score.
"""

import dataclasses
import datetime

# Below this many data points or this few days of span, a linear trend is
# just noise - showing a confident-looking forecast would overstate what a
# handful of price points can actually tell you.
MIN_FORECAST_POINTS = 4
MIN_FORECAST_SPAN_DAYS = 14

# Confidence is about how much real data backs the forecast, not a
# probability the forecast will be correct (see spec: confidence reflects
# "the amount/quality of available historical data").
HIGH_CONFIDENCE_SPAN_DAYS = 90
HIGH_CONFIDENCE_POINTS = 15
MEDIUM_CONFIDENCE_SPAN_DAYS = 30
MEDIUM_CONFIDENCE_POINTS = 8

# How far ahead to project. Kept short deliberately: a simple linear fit
# over a few weeks of real data says very little about prices 6 months out.
FORECAST_HORIZON_DAYS = 45

# The forecast center is clamped to this range around the current price so
# a short noisy history can't extrapolate into an implausible number - the
# same kind of guardrail as pipeline.py's PRICE_SANITY_MIN/MAX_RATIO for
# fetched prices, just tighter since this is a 45-day-out projection, not a
# single fetched data point.
FORECAST_CLAMP_MIN_RATIO = 0.6
FORECAST_CLAMP_MAX_RATIO = 1.4

# Minimum half-width of the forecast range, as a fraction of the center
# price - even a very clean trend line doesn't justify presenting a single
# exact number, so the range never collapses to a point.
MIN_BAND_RATIO = 0.04


@dataclasses.dataclass
class ForecastResult:
    confidence: str  # "high" | "medium" | "low"
    center_price: int
    low_price: int
    high_price: int
    target_date: datetime.datetime
    trend: str  # "down" | "up" | "flat"
    trend_percent_total: float  # % change implied by the fitted trend over the observed span
    reasons: list[str]


def _confidence(points: int, span_days: int) -> str | None:
    if span_days >= HIGH_CONFIDENCE_SPAN_DAYS and points >= HIGH_CONFIDENCE_POINTS:
        return "high"
    if span_days >= MEDIUM_CONFIDENCE_SPAN_DAYS and points >= MEDIUM_CONFIDENCE_POINTS:
        return "medium"
    if span_days >= MIN_FORECAST_SPAN_DAYS and points >= MIN_FORECAST_POINTS:
        return "low"
    return None


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Ordinary least-squares slope/intercept for y = slope*x + intercept."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def forecast_price(
    history_prices: list[tuple[int, datetime.datetime]],
    current_price: int,
    now: datetime.datetime | None = None,
) -> ForecastResult | None:
    """history_prices: (price, recorded_at) pairs, any order, may include the
    current price. Returns None when there isn't enough real data to say
    anything - never a placeholder or guessed forecast."""
    now = now or datetime.datetime.utcnow()
    if not history_prices:
        return None

    points = sorted(history_prices, key=lambda pt: pt[1])
    span_days = (now - points[0][1]).days
    confidence = _confidence(len(points), span_days)
    if confidence is None:
        return None

    xs = [(t - points[0][1]).total_seconds() / 86400 for _, t in points]
    ys = [float(p) for p, _ in points]
    slope, intercept = _linear_fit(xs, ys)

    now_x = (now - points[0][1]).total_seconds() / 86400
    target_x = now_x + FORECAST_HORIZON_DAYS
    raw_center = intercept + slope * target_x

    clamp_low = current_price * FORECAST_CLAMP_MIN_RATIO
    clamp_high = current_price * FORECAST_CLAMP_MAX_RATIO
    center = round(min(max(raw_center, clamp_low), clamp_high))

    fitted = [intercept + slope * x for x in xs]
    residuals = [y - f for y, f in zip(ys, fitted)]
    if len(residuals) >= 2:
        mean_sq = sum(r * r for r in residuals) / len(residuals)
        residual_spread = mean_sq**0.5
    else:
        residual_spread = 0.0
    band = max(residual_spread, center * MIN_BAND_RATIO)

    low = round(max(0, center - band))
    high = round(center + band)

    trend_percent_total = round(((center - current_price) / current_price) * 100, 1) if current_price else 0.0
    if trend_percent_total <= -3:
        trend = "down"
    elif trend_percent_total >= 3:
        trend = "up"
    else:
        trend = "flat"

    daily_change_percent = round((slope / current_price) * 100, 2) if current_price else 0.0
    reasons = [
        f"過去{span_days}日間・{len(points)}件の価格データを基に算出しています。",
        f"この期間の傾向線では、1日あたり平均{'+' if daily_change_percent >= 0 else ''}{daily_change_percent}%の変化が見られます。",
    ]
    recent_cutoff = now - datetime.timedelta(days=7)
    recent_points = [p for p, t in points if t >= recent_cutoff]
    if len(recent_points) >= 2:
        recent_change = round(((recent_points[-1] - recent_points[0]) / recent_points[0]) * 100, 1)
        if (recent_change < 0) == (trend == "down") and abs(recent_change) >= 1:
            reasons.append(f"直近7日間の値動き（{recent_change:+.1f}%）も同じ方向で、傾向と整合しています。")
        elif abs(recent_change) >= 1:
            reasons.append(f"直近7日間の値動き（{recent_change:+.1f}%）は全体の傾向と逆方向で、不確実性が高い状態です。")

    target_date = points[0][1] + datetime.timedelta(days=target_x)

    return ForecastResult(
        confidence=confidence,
        center_price=center,
        low_price=low,
        high_price=high,
        target_date=target_date,
        trend=trend,
        trend_percent_total=trend_percent_total,
        reasons=reasons,
    )
