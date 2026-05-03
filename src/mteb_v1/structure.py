import pandas as pd
from typing import Dict, Tuple
from .config import Config
from .indicators import Indicators

class StructureDetector:
    """Detect market structures across timeframes"""

    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.data = data
        self.htf = data['HTF']
        self.mtf = data['MTF']
        self.ltf = data['LTF']

    def detect_trend_htf(self) -> pd.Series:
        """Detect trend in HTF (simple: EMA slope)"""
        ema = Indicators.ema(self.htf['Close'], Config.EMA_PERIOD)
        return ema.diff() > 0  # Bullish if EMA rising

    def detect_trend_mtf(self) -> pd.Series:
        """Detect trend in MTF"""
        ema = Indicators.ema(self.mtf['Close'], Config.EMA_PERIOD)
        return ema.diff() > 0

    def detect_hl_mtf(self) -> pd.Series:
        """Detect Higher Low in MTF"""
        pivot_high, pivot_low = Indicators.pivot_points(self.mtf, Config.PIVOT_WINDOW)
        return Indicators.detect_higher_low(pivot_low)

    def detect_box_breakout_ltf(self) -> Tuple[pd.Series, pd.Series]:
        """Detect box and breakout in LTF"""
        box_high, box_low = Indicators.detect_box(self.ltf, Config.BOX_PERIOD)
        breakout = self.ltf['Close'] > box_high
        return breakout, pd.Series([box_high] * len(self.ltf), index=self.ltf.index)

    def is_above_ema_ltf(self) -> pd.Series:
        """Check if price is above EMA in LTF"""
        ema = Indicators.ema(self.ltf['Close'], Config.EMA_PERIOD)
        return self.ltf['Close'] > ema

    def volume_condition_ltf(self) -> pd.Series:
        """Check volume condition for breakout"""
        return Indicators.volume_breakout(self.ltf, Config.BOX_PERIOD, Config.VOLUME_MULTIPLIER)