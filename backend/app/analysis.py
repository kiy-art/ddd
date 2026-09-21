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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


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


def analyze_prices(
    current_price: int,
    history_prices: list[tuple[int, datetime.datetime]],
    now: datetime.datetime | None = None,
) -> AnalysisResult:
    """history_prices: list of (price, recorded_at), any order, may include current."""
    now = now or datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(days=LOOKBACK_DAYS)

    recent = [(p, t) for p, t in history_prices if t >= cutoff]
    recent_prices = [p for p, _ in recent]
    all_prices = [p for p, _ in history_prices]

    lowest_price = min(all_prices + [current_price]) if all_prices else current_price
    span_days = (now - min(t for _, t in recent)).days if recent else 0

    if len(recent) < MIN_HISTORY_POINTS:
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

    momentum_percent = _recent_momentum_percent(current_price, recent, now)
    buy_signal_score = _buy_signal_score(
        current_price, average_price, lowest_price, recent_prices, momentum_percent
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
    )


def rule_based_reason(result: AnalysisResult) -> str:
    """Deterministic Japanese explanation, used as a fallback when AI is unavailable
    and as the factual basis handed to the AI for wording."""
    if result.buy_score == "insufficient_data":
        if result.history_span_days > 0:
            return f"価格データを蓄積中です（現在{result.history_span_days}日分）。判定にはもう少しデータが必要です。"
        return "価格データが不足しているため判定できません。"

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
