import datetime

from app import analysis


def _days_ago(n):
    return datetime.datetime.utcnow() - datetime.timedelta(days=n)


def test_insufficient_data_with_no_history():
    result = analysis.analyze_prices(10000, [])
    assert result.buy_score == "insufficient_data"
    assert result.average_price is None


def test_insufficient_data_with_one_point():
    history = [(10000, _days_ago(5))]
    result = analysis.analyze_prices(9500, history)
    assert result.buy_score == "insufficient_data"


def test_strong_buy_below_85_percent_of_average():
    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    result = analysis.analyze_prices(8000, history)  # 80% of 10000 avg
    assert result.buy_score == "strong_buy"
    assert result.average_price == 10000
    assert result.price_change_percent == -20.0


def test_buy_below_90_percent_but_not_85():
    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    result = analysis.analyze_prices(8800, history)  # 88% of avg
    assert result.buy_score == "buy"


def test_not_buy_near_30d_high():
    history = [(8000, _days_ago(25)), (10000, _days_ago(5))]
    result = analysis.analyze_prices(9900, history)  # near the 10000 high
    assert result.buy_score == "not_buy"


def test_neutral_when_no_rule_matches():
    history = [(9000, _days_ago(20)), (11000, _days_ago(5))]
    result = analysis.analyze_prices(9800, history)
    assert result.buy_score == "neutral"


def test_old_history_outside_30_days_is_excluded():
    history = [(5000, _days_ago(45)), (5000, _days_ago(40))]
    result = analysis.analyze_prices(4800, history)
    assert result.buy_score == "insufficient_data"


def test_lowest_price_considers_all_history_not_just_30d():
    history = [(3000, _days_ago(90)), (9000, _days_ago(10)), (9000, _days_ago(5))]
    result = analysis.analyze_prices(8800, history)
    assert result.lowest_price == 3000


def test_rule_based_reason_is_deterministic_text():
    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    result = analysis.analyze_prices(8000, history)
    reason = analysis.rule_based_reason(result)
    assert "20.0%" in reason
    assert "強い買い時" in reason
