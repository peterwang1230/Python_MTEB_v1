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
        box_high = self.ltf['High'].rolling(Config.BOX_PERIOD).max().shift(1)
        breakout = self.ltf['Close'] > box_high
        return breakout.fillna(False), box_high

    def detect_wave3_setup_ltf(self) -> pd.DataFrame:
        """Find wave-3 launch setups from an L1-H1-L2 pivot sequence."""
        result = pd.DataFrame(index=self.ltf.index)
        for column in [
            "wave3_setup",
            "wave1_low",
            "wave1_high",
            "wave2_low",
            "entry_price",
            "stop_loss",
            "take_profit",
            "expected_gain_pct",
            "risk_reward",
        ]:
            result[column] = pd.NA
        result["wave3_setup"] = False

        if len(self.ltf) < (Config.PIVOT_WINDOW * 2) + Config.WAVE3_REBOUND_LOOKBACK + 3:
            return result

        pivot_high, pivot_low = Indicators.pivot_points(self.ltf, Config.PIVOT_WINDOW)
        rebound_line = (
            self.ltf["High"]
            .rolling(Config.WAVE3_REBOUND_LOOKBACK)
            .max()
            .shift(1)
        )
        above_rebound = self.ltf["Close"] > rebound_line
        above_ema = self.is_above_ema_ltf()

        pivots: list[tuple[int, pd.Timestamp, str, float]] = []
        triggered_wave2_positions: set[int] = set()
        for position, index in enumerate(self.ltf.index):
            confirmed_through = position - Config.PIVOT_WINDOW
            if confirmed_through < 0:
                continue

            confirmed_index = self.ltf.index[confirmed_through]
            if bool(pivot_low.loc[confirmed_index]):
                pivots.append((confirmed_through, confirmed_index, "L", float(self.ltf.loc[confirmed_index, "Low"])))
            if bool(pivot_high.loc[confirmed_index]):
                pivots.append((confirmed_through, confirmed_index, "H", float(self.ltf.loc[confirmed_index, "High"])))
            pivots = self._dedupe_pivots(pivots)

            wave = self._latest_wave1_wave2(pivots)
            if wave is None:
                continue

            l1_pos, _, l1_price, h1_pos, _, h1_price, l2_pos, _, l2_price = wave
            if position <= l2_pos:
                continue
            if l2_pos in triggered_wave2_positions:
                continue

            if not bool(above_rebound.iloc[position]) or not bool(above_ema.iloc[position]):
                continue

            entry_price = float(self.ltf["Close"].iloc[position])

            wave1_length = h1_price - l1_price
            stop_loss = l2_price * (1 - Config.WAVE3_STOP_BUFFER_PCT)
            take_profit = l2_price + (wave1_length * Config.WAVE3_TARGET_EXTENSION)
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
            if wave1_length <= 0 or risk <= 0 or reward <= 0:
                continue

            expected_gain_pct = (reward / entry_price) * 100
            risk_reward = reward / risk
            if Config.WAVE3_USE_QUALITY_FILTERS:
                launch_level = h1_price * (1 - Config.WAVE3_BREAKOUT_TOLERANCE_PCT)
                if entry_price < launch_level:
                    continue
                if risk_reward < Config.WAVE3_MIN_RISK_REWARD:
                    continue
                if expected_gain_pct < Config.WAVE3_MIN_EXPECTED_GAIN_PCT:
                    continue

            result.loc[index, "wave3_setup"] = True
            result.loc[index, "wave1_low"] = l1_price
            result.loc[index, "wave1_high"] = h1_price
            result.loc[index, "wave2_low"] = l2_price
            result.loc[index, "entry_price"] = entry_price
            result.loc[index, "stop_loss"] = stop_loss
            result.loc[index, "take_profit"] = take_profit
            result.loc[index, "expected_gain_pct"] = expected_gain_pct
            result.loc[index, "risk_reward"] = risk_reward
            triggered_wave2_positions.add(l2_pos)

        return result

    @staticmethod
    def _dedupe_pivots(pivots: list[tuple[int, pd.Timestamp, str, float]]) -> list[tuple[int, pd.Timestamp, str, float]]:
        deduped: list[tuple[int, pd.Timestamp, str, float]] = []
        for pivot in pivots:
            if not deduped or pivot[2] != deduped[-1][2]:
                deduped.append(pivot)
                continue
            previous = deduped[-1]
            if pivot[2] == "H" and pivot[3] > previous[3]:
                deduped[-1] = pivot
            elif pivot[2] == "L" and pivot[3] < previous[3]:
                deduped[-1] = pivot
        return deduped

    @staticmethod
    def _latest_wave1_wave2(
        pivots: list[tuple[int, pd.Timestamp, str, float]]
    ) -> tuple[int, pd.Timestamp, float, int, pd.Timestamp, float, int, pd.Timestamp, float] | None:
        for first, second, third in zip(pivots[-3::-1], pivots[-2::-1], pivots[-1::-1]):
            if first[2] == "L" and second[2] == "H" and third[2] == "L":
                l1_pos, l1_index, _, l1_price = first
                h1_pos, h1_index, _, h1_price = second
                l2_pos, l2_index, _, l2_price = third
                if l1_price < l2_price < h1_price:
                    return l1_pos, l1_index, l1_price, h1_pos, h1_index, h1_price, l2_pos, l2_index, l2_price
        return None

    def is_above_ema_ltf(self) -> pd.Series:
        """Check if price is above EMA in LTF"""
        ema = Indicators.ema(self.ltf['Close'], Config.EMA_PERIOD)
        return self.ltf['Close'] > ema

    def volume_condition_ltf(self) -> pd.Series:
        """Check volume condition for breakout"""
        return Indicators.volume_breakout(self.ltf, Config.BOX_PERIOD, Config.VOLUME_MULTIPLIER)
