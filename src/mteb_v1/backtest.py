import pandas as pd
import backtrader as bt
from typing import Dict, List
from .config import Config
from .data_loader import DataLoader
from .strategy import StrategyEngine
from .structure import StructureDetector
from .risk import RiskManager

class MTEBStrategy(bt.Strategy):
    """Backtrader strategy implementation"""

    params = (
        ('engine', None),
    )

    def __init__(self):
        self.engine = self.p.engine
        self.position_size = 1
        self.entry_price = None
        self.stop_loss = None
        self.trailing_stop = None
        self.high_water_mark = None

    def next(self):
        if self.engine is None:
            return

        signals = self.engine.generate_signals()
        current_signal = signals.iloc[-1] if not signals.empty else None

        if current_signal is None:
            return

        # Entry
        if current_signal['entry'] and not self.position:
            self.buy(size=self.position_size)
            self.entry_price = self.data.close[0]
            self.stop_loss = RiskManager.calculate_stop_loss(self.entry_price)
            self.high_water_mark = self.entry_price
            self.trailing_stop = self.stop_loss

        # Exit management
        elif self.position:
            self.high_water_mark = max(self.high_water_mark, self.data.high[0])
            self.trailing_stop = RiskManager.calculate_trailing_stop(self.high_water_mark, self.data.close[0])

            # Check exit conditions
            exit_reason = RiskManager.check_exit_conditions(
                self.data.close[0], self.stop_loss, self.trailing_stop,
                True, True, False  # Simplified
            )

            if exit_reason:
                self.sell(size=self.position.size)

class BacktestEngine:
    """Backtest engine using Backtrader"""

    @staticmethod
    def run_backtest(symbol: str, start: str, end: str) -> bt.Analyzer:
        """Run backtest and return results"""
        # Load data
        data_dict = DataLoader.load_multi_timeframe(symbol, start, end)

        # Create detector and engine
        detector = StructureDetector(data_dict)
        engine = StrategyEngine(detector)

        # Setup backtrader
        cerebro = bt.Cerebro()
        cerebro.addstrategy(MTEBStrategy, engine=engine)

        # Add data (using LTF for now)
        data = bt.feeds.PandasData(dataname=data_dict['LTF'])
        cerebro.adddata(data)

        # Run backtest
        cerebro.run()

        return cerebro.analyzers
