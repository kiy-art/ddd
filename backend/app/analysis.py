"""Rule-based price analysis and buy-time scoring.

AI is deliberately kept out of this module: every number used for the
buy_score decision (and the PAR. BUY SIGNAL score) is computed here from
real PriceHistory rows, using fixed arithmetic rules. Only the resulting
facts are ever handed to the AI layer for wording. Given the same price
history, this always produces the same score - nothing here is sampled,
guessed, or AI-generated.
"""

import dataclasses
import datetime

STRONG_BUY_RATIO = 0.85
BUY_RATIO = 0.90
NEAR_HIGH_RATIO = 0.97
NEAR_LOW_RATIO = 1.05
MIN_HISTORY_POINTS = 2
LOOKBACK_DAYS = 30
MOMENTUM_DAYS = 7

# STEP21: MSRP-based fallback/blend thresholds, used only when real price
# history is too thin to trust on its own (see _msrp_discount_tier and its
# two call sites in analyze_prices below). Deliberately its own, slightly
# wider set of ratios than STRONG_BUY_RATIO/BUY_RATIO above - those compare
# against a real 30-day average, a much more stable reference point than a
# single static MSRP figure, so a shallower discount is enough to trust.
MSRP_STRONG_BUY_RATIO = 0.80
MSRP_BUY_RATIO = 0.90
# With 2-3 real points, the 30-day average is itself barely more than the
# current price, so it rarely swings far enough to earn strong_buy/buy even
# for a genuinely well-discounted product - above this many points there's
# enough real trend data to trust it alone, so the MSRP blend stops
# applying (never overrides an already-informed real-trend verdict).
THIN_HISTORY_MSRP_BLEND_MAX_POINTS = 3
_BUY_SCORE_RANK = {"not_buy": 0, "neutral": 1, "buy": 2, "strong_buy": 3}

# PAR. BUY SIGNAL component weights (must sum to 1.0)
WEIGHT_VS_AVERAGE = 0.35
WEIGHT_VS_LOW = 0.25
WEIGHT_RANK = 0.25
WEIGHT_MOMENTUM = 0.15


@dataclasses.dataclass
class AnalysisResult:
    current_price: int
    average_price: int | None
    lowest_price: int | None
    highest_price_30d: int | None
    price_change_percent: float | None
    buy_score: str
    history_points_30d: int
    history_span_days: int
    buy_signal_score: int | None
    # STEP21: "price_history" (default - buy_score came from real trend
    # data, exactly as before this STEP) or "msrp_estimate" (buy_score was
    # set or upgraded from a static MSRP-vs-current-price comparison
    # because real history was too thin to trust alone). Callers use this
    # to word the explanation honestly (see rule_based_reason) and to skip
    # spending on a live AI call for a verdict that isn't backed by real
    # trend data (see app/ai.py).
    data_basis: str = "price_history"
    # % below/above MSRP, set only when data_basis == "msrp_estimate".
    # Deliberately a separate field from price_change_percent (which always
    # means "vs the real 30-day average") rather than overloading it, so a
    # caller can never confuse the two different bases for a percentage.
    msrp_discount_percent: float | None = None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# STEP49: the 0-99 score shown next to the verdict must never contradict it
# ("82 / 様子見" read as nonsense to a shopper). The verdict (buy_score)
# stays the single rule that decides the label - it also drives filters,
# badges and X-post selection - and the score is placed inside that
# verdict's band, ordered within it by the four real signals below. So
# 80+ always means "今が買い時", 65-79 "買い時", 40-64 "様子見",
# 39 or below "待つのが無難", on every page that shows the number.
SCORE_BANDS = {
    "strong_buy": (80, 99),
    "buy": (65, 79),
    "neutral": (40, 64),
    "not_buy": (1, 39),
}


def _score_in_band(composite: int, buy_score: str) -> int:
    """Linearly maps a raw 1-99 composite into the verdict's band
    (order-preserving: a stronger composite is still a higher score
    within the same verdict)."""
    lo, hi = SCORE_BANDS[buy_score]
    return int(round(lo + (composite - 1) / 98 * (hi - lo)))


def _buy_signal_score(
    current_price: int,
    average_price: int,
    lowest_price: int,
    recent_prices: list[int],
    momentum_percent: float | None,
) -> int:
    """0-99 score combining four independent, real signals:
    - deviation from the 30-day average (bigger discount = higher score)
    - distance from the all-time low (closer to the low = higher score)
    - percentile rank within the 30-day window (cheaper than more of the
      recent history = higher score)
    - 7-day momentum (falling price = higher score; neutral if unknown)
    """
    avg_deviation_pct = ((current_price - average_price) / average_price) * 100
    vs_average = _clamp(-avg_deviation_pct / 25, -1, 1)

    low_gap_pct = ((current_price - lowest_price) / lowest_price) * 100 if lowest_price else 0
    vs_low = _clamp(1 - (low_gap_pct / 15), -1, 1)

    rank = sum(1 for p in recent_prices if p >= current_price) / len(recent_prices)
    rank_component = rank * 2 - 1

    momentum = _clamp(-momentum_percent / 15, -1, 1) if momentum_percent is not None else 0.0

    combined = (
        vs_average * WEIGHT_VS_AVERAGE
        + vs_low * WEIGHT_VS_LOW
        + rank_component * WEIGHT_RANK
        + momentum * WEIGHT_MOMENTUM
    )
    return int(_clamp(round(50 + combined * 49), 1, 99))


def _recent_momentum_percent(
    current_price: int, recent: list[tuple[int, datetime.datetime]], now: datetime.datetime
) -> float | None:
    """% change vs the price closest to exactly 7 days ago. None if no
    price point is at least 7 days old yet."""
    cutoff = now - datetime.timedelta(days=MOMENTUM_DAYS)
    candidates = [(p, t) for p, t in recent if t <= cutoff]
    if not candidates:
        return None
    price_7d_ago, _ = min(candidates, key=lambda pt: abs((now - pt[1]).days - MOMENTUM_DAYS))
    if not price_7d_ago:
        return None
    return round(((current_price - price_7d_ago) / price_7d_ago) * 100, 1)


def _msrp_discount_tier(current_price: int, msrp: int) -> tuple[str, float]:
    """Classifies current_price purely against MSRP - real information
    (MSRP is a manually-curated fact, never fabricated - see
    docs/ai_company_guidelines.md), but a much weaker signal than a real
    30-day trend: it says nothing about whether this is unusually cheap
    FOR THIS PRODUCT, only that it's cheap relative to list price."""
    discount_percent = round(((current_price - msrp) / msrp) * 100, 1)
    if current_price < msrp * MSRP_STRONG_BUY_RATIO:
        tier = "strong_buy"
    elif current_price < msrp * MSRP_BUY_RATIO:
        tier = "buy"
    elif current_price >= msrp:
        tier = "not_buy"
    else:
        tier = "neutral"
    return tier, discount_percent


def analyze_prices(
    current_price: int,
    history_prices: list[tuple[int, datetime.datetime]],
    now: datetime.datetime | None = None,
    msrp: int | None = None,
) -> AnalysisResult:
    """history_prices: list of (price, recorded_at), any order, may include current.

    msrp: optional, real manually-curated fact (Product.msrp) - when given
    and real price history is too thin to trust on its own, used as a
    fallback/blend signal (see the MSRP_* constants and data_basis on
    AnalysisResult above). Omitting it (the default) reproduces the exact
    pre-STEP21 behavior."""
    now = now or datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(days=LOOKBACK_DAYS)

    recent = [(p, t) for p, t in history_prices if t >= cutoff]
    recent_prices = [p for p, _ in recent]
    all_prices = [p for p, _ in history_prices]

    lowest_price = min(all_prices + [current_price]) if all_prices else current_price
    span_days = (now - min(t for _, t in recent)).days if recent else 0

    if len(recent) < MIN_HISTORY_POINTS:
        # STEP21: real trend data doesn't exist yet (0 or 1 points), but
        # MSRP - a real, already-known fact - lets a genuinely well-priced
        # new listing show a tentative positive signal instead of sitting
        # in insufficient_data until tomorrow's second price snapshot.
        # Deliberately one-directional: only ever produces "buy"/
        # "strong_buy", never "not_buy"/"neutral" - with no trend evidence
        # at all, asserting a NEGATIVE judgment this confidently would be
        # presuming more than the single data point actually supports;
        # staying at insufficient_data is the honest call there.
        if msrp and msrp > 0:
            tier, discount_percent = _msrp_discount_tier(current_price, msrp)
            if tier in ("buy", "strong_buy"):
                return AnalysisResult(
                    current_price=current_price,
                    average_price=None,
                    lowest_price=lowest_price,
                    highest_price_30d=None,
                    price_change_percent=None,
                    buy_score=tier,
                    history_points_30d=len(recent),
                    history_span_days=span_days,
                    buy_signal_score=None,
                    data_basis="msrp_estimate",
                    msrp_discount_percent=discount_percent,
                )
        return AnalysisResult(
            current_price=current_price,
            average_price=None,
            lowest_price=lowest_price,
            highest_price_30d=None,
            price_change_percent=None,
            buy_score="insufficient_data",
            history_points_30d=len(recent),
            history_span_days=span_days,
            buy_signal_score=None,
        )

    average_price = round(sum(recent_prices) / len(recent_prices))
    highest_30d = max(recent_prices)
    price_change_percent = round(((current_price - average_price) / average_price) * 100, 1)

    if current_price < average_price * STRONG_BUY_RATIO:
        buy_score = "strong_buy"
    elif current_price < average_price * BUY_RATIO:
        buy_score = "buy"
    elif current_price >= highest_30d * NEAR_HIGH_RATIO:
        buy_score = "not_buy"
    else:
        buy_score = "neutral"

    # STEP21: with only 2-3 real points, the 30-day average above is
    # barely more than the current price itself, so it rarely swings far
    # enough to earn strong_buy/buy even for a product genuinely priced
    # well below MSRP - let a clearly positive MSRP signal (buy/strong_buy
    # only - never merely upgrade into "neutral", which isn't a buy signal
    # and would leave rule_based_reason's msrp_estimate wording, below,
    # with nothing to say) upgrade a neutral/not_buy verdict in that thin
    # regime. Never downgrades an already-positive real-trend verdict (the
    # more-informed signal always wins), and never applies once there's
    # enough real history to trust the trend alone (see
    # THIN_HISTORY_MSRP_BLEND_MAX_POINTS).
    data_basis = "price_history"
    msrp_discount_percent = None
    if msrp and msrp > 0 and len(recent) <= THIN_HISTORY_MSRP_BLEND_MAX_POINTS:
        msrp_tier, msrp_discount_percent = _msrp_discount_tier(current_price, msrp)
        if msrp_tier in ("buy", "strong_buy") and _BUY_SCORE_RANK[msrp_tier] > _BUY_SCORE_RANK[buy_score]:
            buy_score = msrp_tier
            data_basis = "msrp_estimate"
        else:
            msrp_discount_percent = None

    momentum_percent = _recent_momentum_percent(current_price, recent, now)
    buy_signal_score = _score_in_band(
        _buy_signal_score(current_price, average_price, lowest_price, recent_prices, momentum_percent),
        buy_score,
    )

    return AnalysisResult(
        current_price=current_price,
        average_price=average_price,
        lowest_price=lowest_price,
        highest_price_30d=highest_30d,
        price_change_percent=price_change_percent,
        buy_score=buy_score,
        history_points_30d=len(recent),
        history_span_days=span_days,
        buy_signal_score=buy_signal_score,
        data_basis=data_basis,
        msrp_discount_percent=msrp_discount_percent,
    )


def rule_based_reason(result: AnalysisResult) -> str:
    """Deterministic Japanese explanation, used as a fallback when AI is unavailable
    and as the factual basis handed to the AI for wording."""
    if result.buy_score == "insufficient_data":
        if result.history_span_days > 0:
            return f"価格データを蓄積中です（現在{result.history_span_days}日分）。判定にはもう少しデータが必要です。"
        return "価格データが不足しているため判定できません。"

    # STEP21: this verdict came from a static MSRP comparison, not a real
    # price trend (see AnalysisResult.data_basis) - say so plainly rather
    # than reusing the "過去30日平均より安く" wording below, which would
    # claim a real trend comparison that doesn't actually exist yet.
    if result.data_basis == "msrp_estimate":
        pct = abs(result.msrp_discount_percent)
        if result.buy_score == "strong_buy":
            text = f"価格推移データがまだ少ないための暫定判定ですが、定価より{pct}%安く、強い買い時候補です。"
        else:
            text = f"価格推移データがまだ少ないための暫定判定ですが、定価より{pct}%安く、買い時候補です。"
        near_low = result.lowest_price is not None and result.current_price <= result.lowest_price * NEAR_LOW_RATIO
        if near_low:
            text += "過去30日間でも最安値水準です。"
        return text

    pct = result.price_change_percent
    if result.buy_score == "strong_buy":
        text = f"現在価格は過去{LOOKBACK_DAYS}日平均より{abs(pct)}%安く、強い買い時候補です。"
    elif result.buy_score == "buy":
        text = f"現在価格は過去{LOOKBACK_DAYS}日平均より{abs(pct)}%安く、買い時候補です。"
    elif result.buy_score == "not_buy":
        text = f"現在価格は過去{LOOKBACK_DAYS}日の最高値付近のため、買い時ではありません。"
    else:
        text = f"現在価格は過去{LOOKBACK_DAYS}日平均から{pct}%の変化で、様子見が妥当です。"

    near_low = result.lowest_price is not None and result.current_price <= result.lowest_price * NEAR_LOW_RATIO
    if near_low and result.buy_score in ("strong_buy", "buy"):
        text += "過去30日間でも最安値水準です。"
    return text
