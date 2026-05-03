import backtrader as bt
import pandas as pd

from src.mteb_v1 import backtest as backtest_module
from src.mteb_v1.backtest import BacktestEngine, MTEBStrategy


def make_ohlcv(periods=30):
    index = pd.date_range("2023-01-01", periods=periods, freq="15min")
    closes = [100 + i for i in range(periods)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 1 for value in closes],
            "Low": [value - 1 for value in closes],
            "Close": closes,
            "Volume": [1000 for _ in closes],
        },
        index=index,
    )


class FakeSignalEngine:
    def __init__(self, index):
        self.index = index

    def generate_signals(self):
        return pd.DataFrame(
            {
                "entry": [0] * len(self.index),
                "box_high": [110] * len(self.index),
                "exit": [False] * len(self.index),
            },
            index=self.index,
        )


def test_mteb_strategy_receives_engine_from_backtrader_params():
    data_frame = make_ohlcv()
    engine = FakeSignalEngine(data_frame.index)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MTEBStrategy, engine=engine)
    cerebro.adddata(bt.feeds.PandasData(dataname=data_frame))

    strategies = cerebro.run()

    assert strategies[0].engine is engine


def test_mteb_strategy_without_engine_leaves_broker_value_unchanged():
    data_frame = make_ohlcv()
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    cerebro.addstrategy(MTEBStrategy)
    cerebro.adddata(bt.feeds.PandasData(dataname=data_frame))

    cerebro.run()

    assert cerebro.broker.getvalue() == 10000


def test_run_backtest_uses_loaded_ltf_data_without_external_download(monkeypatch):
    data_frame = make_ohlcv()
    captured = {}

    def fake_load_multi_timeframe(symbol, start, end):
        captured["args"] = (symbol, start, end)
        return {
            "HTF": data_frame,
            "MTF": data_frame,
            "LTF": data_frame,
        }

    class FakeStructureDetector:
        def __init__(self, data):
            self.data = data
            self.ltf = data["LTF"]

    class FakeStrategyEngine:
        def __init__(self, detector):
            self.detector = detector

        def generate_signals(self):
            return pd.DataFrame(
                {
                    "entry": [0] * len(self.detector.ltf),
                    "box_high": [110] * len(self.detector.ltf),
                    "exit": [False] * len(self.detector.ltf),
                },
                index=self.detector.ltf.index,
            )

    monkeypatch.setattr(
        backtest_module.DataLoader,
        "load_multi_timeframe",
        staticmethod(fake_load_multi_timeframe),
    )
    monkeypatch.setattr(backtest_module, "StructureDetector", FakeStructureDetector)
    monkeypatch.setattr(backtest_module, "StrategyEngine", FakeStrategyEngine)

    analyzers = BacktestEngine.run_backtest("AAPL", "2023-01-01", "2023-02-01")

    assert captured["args"] == ("AAPL", "2023-01-01", "2023-02-01")
    assert analyzers is not None
