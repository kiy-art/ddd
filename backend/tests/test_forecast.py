import datetime

from app import forecast


def _days_ago(n):
    return datetime.datetime.utcnow() - datetime.timedelta(days=n)


def test_no_forecast_with_no_history():
    assert forecast.forecast_price([], 10000) is None


def test_no_forecast_below_minimum_points():
    history = [(10000, _days_ago(20)), (9500, _days_ago(5))]
    assert forecast.forecast_price(history, 9500) is None


def test_no_forecast_below_minimum_span():
    # Enough points, but all within a few days - too short a span to trust a trend.
    history = [(10000, _days_ago(3)), (9900, _days_ago(2)), (9800, _days_ago(1)), (9700, _days_ago(0))]
    assert forecast.forecast_price(history, 9700) is None


def test_low_confidence_downward_trend():
    history = [
        (10000, _days_ago(20)),
        (9500, _days_ago(14)),
        (9200, _days_ago(7)),
        (9000, _days_ago(0)),
    ]
    result = forecast.forecast_price(history, 9000)
    assert result is not None
    assert result.confidence == "low"
    assert result.trend == "down"
    assert result.low_price <= result.center_price <= result.high_price
    assert result.target_date > _days_ago(0)
    assert any("価格データを基に算出" in r for r in result.reasons)


def test_medium_confidence_needs_more_data():
    history = [(10000 - i * 50, _days_ago(35 - i)) for i in range(9)]
    result = forecast.forecast_price(history, history[-1][0])
    assert result is not None
    assert result.confidence == "medium"


def test_high_confidence_needs_long_span_and_many_points():
    history = [(10000 - i * 30, _days_ago(95 - i * 6)) for i in range(16)]
    result = forecast.forecast_price(history, history[-1][0])
    assert result is not None
    assert result.confidence == "high"


def test_flat_trend_stays_flat():
    history = [
        (10000, _days_ago(20)),
        (10050, _days_ago(14)),
        (9950, _days_ago(7)),
        (10000, _days_ago(0)),
    ]
    result = forecast.forecast_price(history, 10000)
    assert result is not None
    assert result.trend == "flat"


def test_center_never_extrapolates_beyond_clamp():
    # A very steep short trend shouldn't be allowed to project an absurd price.
    history = [
        (10000, _days_ago(20)),
        (5000, _days_ago(14)),
        (2000, _days_ago(7)),
        (1000, _days_ago(0)),
    ]
    result = forecast.forecast_price(history, 1000)
    assert result is not None
    assert result.center_price >= round(1000 * forecast.FORECAST_CLAMP_MIN_RATIO)


def test_range_never_collapses_to_a_point():
    history = [(10000, _days_ago(20 - i)) for i in range(21)]  # perfectly flat, no residual
    result = forecast.forecast_price(history, 10000)
    assert result is not None
    assert result.high_price > result.low_price
