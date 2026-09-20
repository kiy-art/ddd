"""Rule-based price analysis and buy-time scoring.

AI is deliberately kept out of this module: every number used for the
buy_score decision is computed here from real PriceHistory rows, and only
the resulting facts are ever handed to the AI layer for wording.
"""

import dataclasses
import datetime

STRONG_BUY_RATIO = 0.85
BUY_RATIO = 0.90
NEAR_HIGH_RATIO = 0.97
MIN_HISTORY_POINTS = 2
LOOKBACK_DAYS = 30


@dataclasses.dataclass
class AnalysisResult:
    current_price: int
    average_price: int | None
    lowest_price: int | None
    highest_price_30d: int | None
    price_change_percent: float | None
    buy_score: str
    history_points_30d: int


def analyze_prices(
    current_price: int,
    history_prices: list[tuple[int, datetime.datetime]],
    now: datetime.datetime | None = None,
) -> AnalysisResult:
    """history_prices: list of (price, recorded_at), any order, may include current."""
    now = now or datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(days=LOOKBACK_DAYS)

    recent = [p for p, t in history_prices if t >= cutoff]
    all_prices = [p for p, _ in history_prices]

    lowest_price = min(all_prices + [current_price]) if all_prices else current_price

    if len(recent) < MIN_HISTORY_POINTS:
        return AnalysisResult(
            current_price=current_price,
            average_price=None,
            lowest_price=lowest_price,
            highest_price_30d=None,
            price_change_percent=None,
            buy_score="insufficient_data",
            history_points_30d=len(recent),
        )

    average_price = round(sum(recent) / len(recent))
    highest_30d = max(recent)
    price_change_percent = round(((current_price - average_price) / average_price) * 100, 1)

    if current_price < average_price * STRONG_BUY_RATIO:
        buy_score = "strong_buy"
    elif current_price < average_price * BUY_RATIO:
        buy_score = "buy"
    elif current_price >= highest_30d * NEAR_HIGH_RATIO:
        buy_score = "not_buy"
    else:
        buy_score = "neutral"

    return AnalysisResult(
        current_price=current_price,
        average_price=average_price,
        lowest_price=lowest_price,
        highest_price_30d=highest_30d,
        price_change_percent=price_change_percent,
        buy_score=buy_score,
        history_points_30d=len(recent),
    )


def rule_based_reason(result: AnalysisResult) -> str:
    """Deterministic Japanese explanation, used as a fallback when AI is unavailable
    and as the factual basis handed to the AI for wording."""
    if result.buy_score == "insufficient_data":
        return "価格データが不足しているため判定できません。"

    pct = result.price_change_percent
    if result.buy_score == "strong_buy":
        return f"現在価格は過去{LOOKBACK_DAYS}日平均より{abs(pct)}%安く、強い買い時候補です。"
    if result.buy_score == "buy":
        return f"現在価格は過去{LOOKBACK_DAYS}日平均より{abs(pct)}%安く、買い時候補です。"
    if result.buy_score == "not_buy":
        return f"現在価格は過去{LOOKBACK_DAYS}日の最高値付近のため、買い時ではありません。"
    return f"現在価格は過去{LOOKBACK_DAYS}日平均から{pct}%の変化で、様子見が妥当です。"
