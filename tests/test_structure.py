import pandas as pd

from src.mteb_v1.structure import StructureDetector


def make_ohlcv(periods=30, freq="h", close_start=100, volume=100):
    index = pd.date_range("2023-01-01", periods=periods, freq=freq)
    closes = [close_start + i for i in range(periods)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 1 for value in closes],
            "Low": [value - 1 for value in closes],
            "Close": closes,
            "Volume": [volume for _ in range(periods)],
        },
        index=index,
    )


def make_detector():
    return StructureDetector(
        {
            "HTF": make_ohlcv(periods=30, freq="D"),
            "MTF": make_ohlcv(periods=30, freq="h"),
            "LTF": make_ohlcv(periods=30, freq="15min"),
        }
    )


def test_detect_trend_htf_returns_bullish_trend_for_rising_prices():
    detector = make_detector()

    trend = detector.detect_trend_htf()

    assert isinstance(trend, pd.Series)
    assert trend.index.equals(detector.htf.index)
    assert trend.iloc[1:].all()


def test_detect_trend_mtf_returns_bullish_trend_for_rising_prices():
    detector = make_detector()

    trend = detector.detect_trend_mtf()

    assert isinstance(trend, pd.Series)
    assert trend.index.equals(detector.mtf.index)
    assert trend.iloc[1:].all()


def test_detect_hl_mtf_returns_series_aligned_to_mtf_index():
    detector = make_detector()

    higher_low = detector.detect_hl_mtf()

    assert isinstance(higher_low, pd.Series)
    assert higher_low.index.equals(detector.mtf.index)


def test_detect_box_breakout_ltf_returns_breakout_and_box_high_series():
    detector = make_detector()
    detector.ltf.loc[detector.ltf.index[-20:], "High"] = 105
    detector.ltf.loc[detector.ltf.index[-1], "Close"] = 106

    breakout, box_high = detector.detect_box_breakout_ltf()

    assert isinstance(breakout, pd.Series)
    assert isinstance(box_high, pd.Series)
    assert breakout.index.equals(detector.ltf.index)
    assert box_high.index.equals(detector.ltf.index)
    assert box_high.iloc[-1] == 105
    assert breakout.iloc[-1]


def test_is_above_ema_ltf_identifies_latest_price_above_ema():
    detector = make_detector()

    above_ema = detector.is_above_ema_ltf()

    assert isinstance(above_ema, pd.Series)
    assert above_ema.index.equals(detector.ltf.index)
    assert above_ema.iloc[-1]


def test_volume_condition_ltf_detects_latest_volume_breakout():
    detector = make_detector()
    detector.ltf["Volume"] = 100
    detector.ltf.loc[detector.ltf.index[-1], "Volume"] = 5000

    volume_ok = detector.volume_condition_ltf()

    assert isinstance(volume_ok, pd.Series)
    assert volume_ok.index.equals(detector.ltf.index)
    assert volume_ok.iloc[-1]
