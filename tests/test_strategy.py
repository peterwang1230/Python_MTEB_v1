import pandas as pd

from src.mteb_v1.strategy import StrategyEngine


class FakeDetector:
    def __init__(
        self,
        htf_trend=True,
        mtf_trend=True,
        higher_low=True,
        breakout=True,
        above_ema=True,
        volume_ok=True,
    ):
        self.ltf = pd.DataFrame(
            {"Close": [100, 101, 102]},
            index=pd.date_range("2023-01-01", periods=3, freq="15min"),
        )
        self.htf_trend = htf_trend
        self.mtf_trend = mtf_trend
        self.higher_low = higher_low
        self.breakout = breakout
        self.above_ema = above_ema
        self.volume_ok = volume_ok

    def _series(self, value):
        return pd.Series([value] * len(self.ltf), index=self.ltf.index)

    def detect_trend_htf(self):
        return self._series(self.htf_trend)

    def detect_trend_mtf(self):
        return self._series(self.mtf_trend)

    def detect_hl_mtf(self):
        return self._series(self.higher_low)

    def detect_box_breakout_ltf(self):
        return self._series(self.breakout), self._series(110)

    def is_above_ema_ltf(self):
        return self._series(self.above_ema)

    def volume_condition_ltf(self):
        return self._series(self.volume_ok)


def test_generate_signals_enters_when_all_conditions_are_true():
    engine = StrategyEngine(FakeDetector())

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [1, 1, 1]
    assert signals["box_high"].tolist() == [110, 110, 110]
    assert signals["exit"].tolist() == [False, False, False]
    assert engine.locked is True


def test_generate_signals_does_not_enter_when_one_condition_is_false():
    engine = StrategyEngine(FakeDetector(volume_ok=False))

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [0, 0, 0]
    assert engine.locked is False


def test_generate_signals_lock_prevents_repeated_entries():
    engine = StrategyEngine(FakeDetector())

    first_signals = engine.generate_signals()
    second_signals = engine.generate_signals()

    assert first_signals["entry"].tolist() == [1, 1, 1]
    assert second_signals["entry"].tolist() == [0, 0, 0]
    assert engine.locked is True


def test_generate_signals_returns_dataframe_aligned_to_ltf_index():
    detector = FakeDetector()
    engine = StrategyEngine(detector)

    signals = engine.generate_signals()

    assert isinstance(signals, pd.DataFrame)
    assert signals.index.equals(detector.ltf.index)
    assert list(signals.columns) == ["entry", "box_high", "exit"]
