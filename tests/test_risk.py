import pytest

from src.mteb_v1.risk import RiskManager


def test_calculate_stop_loss_uses_configured_percentage():
    stop_loss = RiskManager.calculate_stop_loss(100)

    assert stop_loss == pytest.approx(95)


def test_calculate_trailing_stop_uses_high_water_mark_when_higher():
    trailing_stop = RiskManager.calculate_trailing_stop(
        high_water_mark=120,
        current_price=100,
    )

    assert trailing_stop == pytest.approx(117.6)


def test_calculate_trailing_stop_uses_current_price_stop_when_higher():
    trailing_stop = RiskManager.calculate_trailing_stop(
        high_water_mark=100,
        current_price=120,
    )

    assert trailing_stop == pytest.approx(114)


def test_check_exit_conditions_returns_stop_loss_first():
    exit_reason = RiskManager.check_exit_conditions(
        current_price=94,
        stop_loss=95,
        trailing_stop=98,
        htf_trend=False,
        mtf_trend=False,
        hl_broken=True,
    )

    assert exit_reason == "SL"


def test_check_exit_conditions_returns_trailing_stop_before_trend():
    exit_reason = RiskManager.check_exit_conditions(
        current_price=97,
        stop_loss=95,
        trailing_stop=98,
        htf_trend=False,
        mtf_trend=True,
        hl_broken=True,
    )

    assert exit_reason == "TRAIL"


def test_check_exit_conditions_returns_trend_when_timeframe_trend_breaks():
    exit_reason = RiskManager.check_exit_conditions(
        current_price=100,
        stop_loss=95,
        trailing_stop=98,
        htf_trend=True,
        mtf_trend=False,
        hl_broken=True,
    )

    assert exit_reason == "TREND"


def test_check_exit_conditions_returns_structure_when_higher_low_breaks():
    exit_reason = RiskManager.check_exit_conditions(
        current_price=100,
        stop_loss=95,
        trailing_stop=98,
        htf_trend=True,
        mtf_trend=True,
        hl_broken=True,
    )

    assert exit_reason == "STRUCT"


def test_check_exit_conditions_returns_none_when_no_exit_condition_matches():
    exit_reason = RiskManager.check_exit_conditions(
        current_price=100,
        stop_loss=95,
        trailing_stop=98,
        htf_trend=True,
        mtf_trend=True,
        hl_broken=False,
    )

    assert exit_reason is None
