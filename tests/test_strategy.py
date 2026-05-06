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
        wave3_setup=True,
    ):
        self.ltf = pd.DataFrame(
            {
                "High": [102, 103, 131],
                "Low": [99, 100, 101],
                "Close": [100, 101, 102],
            },
            index=pd.date_range("2023-01-01", periods=3, freq="15min"),
        )
        self.htf_trend = htf_trend
        self.mtf_trend = mtf_trend
        self.higher_low = higher_low
        self.breakout = breakout
        self.above_ema = above_ema
        self.volume_ok = volume_ok
        self.wave3_setup = wave3_setup

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

    def detect_wave3_setup_ltf(self):
        return pd.DataFrame(
            {
                "wave3_setup": self._series(self.wave3_setup),
                "wave1_low": self._series(90),
                "wave1_high": self._series(110),
                "wave2_low": self._series(98),
                "entry_price": self._series(101),
                "stop_loss": self._series(97),
                "take_profit": self._series(130),
                "expected_gain_pct": self._series(28.7),
                "risk_reward": self._series(7.25),
            },
            index=self.ltf.index,
        )

    def is_above_ema_ltf(self):
        return self._series(self.above_ema)

    def volume_condition_ltf(self):
        return self._series(self.volume_ok)


def test_generate_signals_enters_when_all_conditions_are_true():
    engine = StrategyEngine(FakeDetector())

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [1, 0, 0]
    assert signals["box_high"].iloc[0] == 110
    assert signals["wave2_low"].iloc[0] == 98
    assert signals["stop_loss"].iloc[0] == 97
    assert signals["take_profit"].iloc[0] == 130
    assert signals["box_high"].iloc[1:].isna().all()
    assert signals["wave2_low"].iloc[1:].isna().all()
    assert signals["stop_loss"].iloc[1:].isna().all()
    assert signals["take_profit"].iloc[1:].isna().all()
    assert signals["exit"].tolist() == [False, False, True]
    assert signals["exit_reason"].tolist() == [pd.NA, pd.NA, "TP"]
    assert engine.locked is False


def test_generate_signals_does_not_enter_without_wave3_setup():
    engine = StrategyEngine(FakeDetector(wave3_setup=False))

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [0, 0, 0]
    assert engine.locked is False


def test_generate_signals_does_not_keep_closed_trade_locked_between_runs():
    engine = StrategyEngine(FakeDetector())

    first_signals = engine.generate_signals()
    second_signals = engine.generate_signals()

    assert first_signals["entry"].tolist() == [1, 0, 0]
    assert second_signals["entry"].tolist() == [1, 0, 0]
    assert engine.locked is False


def test_generate_signals_allows_new_entry_after_exit():
    detector = FakeDetector()
    detector.ltf = pd.DataFrame(
        {
            "High": [100, 100, 131, 100, 100, 100],
            "Low": [99, 99, 99, 99, 90, 99],
            "Close": [100, 101, 102, 103, 104, 105],
        },
        index=pd.date_range("2023-01-01", periods=6, freq="15min"),
    )
    engine = StrategyEngine(detector)

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [1, 0, 0, 1, 0, 1]
    assert signals["exit"].tolist() == [False, False, True, False, True, False]
    assert signals["exit_reason"].tolist() == [pd.NA, pd.NA, "TP", pd.NA, "SL", pd.NA]

    summary = engine.summarize_performance(signals)

    assert summary["entries"] == 3
    assert summary["completed_trades"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["open_trades"] == 1
    assert summary["win_rate"] == 0.5


def test_legacy_box_breakout_generates_continuous_trades(monkeypatch):
    from src.mteb_v1.config import Config

    monkeypatch.setattr(Config, "STRATEGY_MODE", "legacy_box")
    monkeypatch.setattr(Config, "STOP_LOSS_PCT", 0.05)
    monkeypatch.setattr(Config, "LEGACY_BOX_TARGET_R_MULTIPLE", 2.0)
    detector = FakeDetector()
    detector.ltf = pd.DataFrame(
        {
            "High": [101, 101, 111, 101, 101, 101],
            "Low": [99, 99, 99, 99, 94, 99],
            "Close": [100, 101, 102, 100, 99, 100],
        },
        index=pd.date_range("2023-01-01", periods=6, freq="15min"),
    )
    engine = StrategyEngine(detector)

    signals = engine.generate_signals()

    assert signals["entry"].tolist() == [1, 0, 0, 1, 0, 1]
    assert signals["exit"].tolist() == [False, False, True, False, True, False]
    assert signals["exit_reason"].tolist() == [pd.NA, pd.NA, "TP", pd.NA, "SL", pd.NA]
    assert signals.loc[signals.index[0], "entry_price"] == 100
    assert signals.loc[signals.index[0], "stop_loss"] == 95
    assert signals.loc[signals.index[0], "take_profit"] == 110
    assert signals.loc[signals.index[0], "risk_reward"] == 2.0

    summary = engine.summarize_performance(signals)

    assert summary["entries"] == 3
    assert summary["completed_trades"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["open_trades"] == 1
    assert summary["win_rate"] == 0.5


def test_generate_signals_returns_dataframe_aligned_to_ltf_index():
    detector = FakeDetector()
    engine = StrategyEngine(detector)

    signals = engine.generate_signals()

    assert isinstance(signals, pd.DataFrame)
    assert signals.index.equals(detector.ltf.index)
    assert list(signals.columns) == [
        "entry",
        "box_high",
        "wave1_low",
        "wave1_high",
        "wave2_low",
        "entry_price",
        "stop_loss",
        "take_profit",
        "expected_gain_pct",
        "risk_reward",
        "exit",
        "exit_reason",
    ]


def test_summarize_performance_counts_tp_sl_win_rate():
    signals = pd.DataFrame(
        {
            "entry": [1, 0, 1, 0, 1],
            "exit": [False, True, False, True, False],
            "exit_reason": [pd.NA, "TP", pd.NA, "SL", pd.NA],
        }
    )

    summary = StrategyEngine.summarize_performance(signals)

    assert summary == {
        "entries": 3,
        "completed_trades": 2,
        "wins": 1,
        "losses": 1,
        "open_trades": 1,
        "win_rate": 0.5,
    }


def test_summarize_performance_returns_none_win_rate_without_completed_trades():
    signals = pd.DataFrame(
        {
            "entry": [1, 0],
            "exit": [False, False],
            "exit_reason": [pd.NA, pd.NA],
        }
    )

    summary = StrategyEngine.summarize_performance(signals)

    assert summary["completed_trades"] == 0
    assert summary["open_trades"] == 1
    assert summary["win_rate"] is None
