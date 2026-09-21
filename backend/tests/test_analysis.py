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


def test_buy_signal_score_is_none_when_insufficient_data():
    result = analysis.analyze_prices(9500, [(10000, _days_ago(5))])
    assert result.buy_signal_score is None


def test_buy_signal_score_is_deterministic_for_same_input():
    history = [(10000, _days_ago(20)), (9500, _days_ago(10)), (9000, _days_ago(3))]
    a = analysis.analyze_prices(8000, history)
    b = analysis.analyze_prices(8000, history)
    assert a.buy_signal_score == b.buy_signal_score
    assert isinstance(a.buy_signal_score, int)
    assert 1 <= a.buy_signal_score <= 99


def test_buy_signal_score_higher_for_cheaper_price_same_history():
    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    cheaper = analysis.analyze_prices(7500, history)
    pricier = analysis.analyze_prices(9800, history)
    assert cheaper.buy_signal_score > pricier.buy_signal_score


def test_buy_signal_score_rewards_being_at_all_time_low():
    history = [(20000, _days_ago(90)), (10000, _days_ago(20)), (10000, _days_ago(10))]
    at_low = analysis.analyze_prices(10000, history)  # matches the recent price, but not the 20000 old high
    history_high_low = [(9000, _days_ago(90)), (10000, _days_ago(20)), (10000, _days_ago(10))]
    above_low = analysis.analyze_prices(10000, history_high_low)  # same avg/rank, but 9000 is the all-time low
    assert at_low.buy_signal_score > above_low.buy_signal_score


def test_buy_signal_score_rewards_recent_downward_momentum():
    # Both scenarios have identical average/low/rank inputs; only whether a
    # price point >=7 days old exists (giving a real momentum reading)
    # differs, isolating the momentum component's effect.
    history_with_week_old_point = [(10000, _days_ago(10)), (10000, _days_ago(8))]
    falling = analysis.analyze_prices(9000, history_with_week_old_point)

    history_all_recent = [(10000, _days_ago(3)), (10000, _days_ago(1))]
    no_momentum_ref = analysis.analyze_prices(9000, history_all_recent)

    assert falling.buy_signal_score > no_momentum_ref.buy_signal_score


def test_history_span_days_tracks_actual_data_age():
    history = [(10000, _days_ago(6)), (10000, _days_ago(0))]
    result = analysis.analyze_prices(9500, history)
    assert result.history_span_days == 6


def test_history_span_days_zero_when_all_same_day():
    history = [(10000, _days_ago(0)), (10000, _days_ago(0))]
    result = analysis.analyze_prices(9500, history)
    assert result.history_span_days == 0


def test_rule_based_reason_mentions_all_time_low_when_applicable():
    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    result = analysis.analyze_prices(7900, history)  # also the all-time low
    reason = analysis.rule_based_reason(result)
    assert "最安値水準" in reason


def test_rule_based_reason_for_thin_data_mentions_accumulation():
    history = [(10000, _days_ago(2))]
    result = analysis.analyze_prices(9800, history)
    assert result.buy_score == "insufficient_data"
    reason = analysis.rule_based_reason(result)
    assert "蓄積" in reason
