import pandas as pd
from typing import Optional
from .structure import StructureDetector

class StrategyEngine:
    """Main strategy engine for entry/exit signals"""

    def __init__(self, detector: StructureDetector):
        self.detector = detector
        self.locked = False  # Cycle lock

    def generate_signals(self) -> pd.DataFrame:
        """Generate buy/sell signals"""
        signals = pd.DataFrame(index=self.detector.ltf.index)

        # Trend conditions
        htf_trend = self.detector.detect_trend_htf().reindex(self.detector.ltf.index, method='ffill')
        mtf_trend = self.detector.detect_trend_mtf().reindex(self.detector.ltf.index, method='ffill')

        # Structure conditions
        hl = self.detector.detect_hl_mtf().reindex(self.detector.ltf.index, method='ffill')
        breakout, box_high = self.detector.detect_box_breakout_ltf()
        above_ema = self.detector.is_above_ema_ltf()
        volume_ok = self.detector.volume_condition_ltf()

        # Entry conditions (all must be true)
        entry_conditions = (
            htf_trend &
            mtf_trend &
            hl &
            breakout &
            above_ema &
            volume_ok &
            (not self.locked)
        )

        signals['entry'] = entry_conditions.astype(int)
        signals['box_high'] = box_high

        # Lock after entry
        if entry_conditions.any():
            self.locked = True

        # Exit conditions (simplified: stop loss or trend change)
        # For now, simple exit after some bars or trend change
        signals['exit'] = False  # Placeholder

        return signals
