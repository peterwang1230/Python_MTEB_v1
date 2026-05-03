import pandas as pd
import numpy as np
from typing import Tuple
from .config import Config

class Indicators:
    """Technical indicators for the strategy"""

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period).mean()

    @staticmethod
    def pivot_points(df: pd.DataFrame, window: int = 5) -> Tuple[pd.Series, pd.Series]:
        """Detect pivot high and low points"""
        highs = df['High']
        lows = df['Low']

        # Pivot High: higher than previous and next window points
        pivot_high = pd.Series(False, index=df.index, dtype=bool)
        for i in range(window, len(df) - window):
            if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
                pivot_high.iloc[i] = True

        # Pivot Low: lower than previous and next window points
        pivot_low = pd.Series(False, index=df.index, dtype=bool)
        for i in range(window, len(df) - window):
            if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
                pivot_low.iloc[i] = True

        return pivot_high, pivot_low

    @staticmethod
    def detect_higher_low(pivot_low: pd.Series) -> pd.Series:
        """Detect Higher Low pattern"""
        hl = pd.Series(index=pivot_low.index, dtype=bool)
        low_indices = pivot_low[pivot_low].index

        for i in range(1, len(low_indices)):
            if pivot_low.index.get_loc(low_indices[i-1]) < pivot_low.index.get_loc(low_indices[i]):
                prev_low = pivot_low.loc[low_indices[i-1]]
                curr_low = pivot_low.loc[low_indices[i]]
                if curr_low > prev_low:
                    hl.loc[low_indices[i]] = True

        return hl

    @staticmethod
    def detect_box(df: pd.DataFrame, period: int) -> Tuple[float, float]:
        """Detect consolidation box"""
        recent_high = df['High'].tail(period).max()
        recent_low = df['Low'].tail(period).min()
        return recent_high, recent_low

    @staticmethod
    def volume_breakout(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
        """Detect volume breakout"""
        avg_volume = df['Volume'].rolling(period).mean()
        return df['Volume'] > avg_volume * multiplier
