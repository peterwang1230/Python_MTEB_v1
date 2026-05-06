import pandas as pd
from .config import Config
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
        mode = getattr(Config, "STRATEGY_MODE", "wave3")

        self._initialize_signal_columns(signals)
        if mode == "legacy_box":
            entry_candidates, setup = self._legacy_box_setup(htf_trend, mtf_trend)
        else:
            entry_candidates, setup = self._wave3_setup(htf_trend, mtf_trend)

        self._apply_trade_cycles(signals, entry_candidates, setup)

        self.locked = bool(signals["entry"].sum() > signals["exit"].sum())

        return signals

    @staticmethod
    def _initialize_signal_columns(signals: pd.DataFrame) -> None:
        signals['entry'] = 0
        signals['box_high'] = pd.NA
        for column in [
            "wave1_low",
            "wave1_high",
            "wave2_low",
            "entry_price",
            "stop_loss",
            "take_profit",
            "expected_gain_pct",
            "risk_reward",
        ]:
            signals[column] = pd.NA

        signals['exit'] = False
        signals['exit_reason'] = pd.NA

    def _wave3_setup(self, htf_trend: pd.Series, mtf_trend: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
        wave3 = self.detector.detect_wave3_setup_ltf()
        wave3["box_high"] = wave3["wave1_high"]
        volume_ok = self.detector.volume_condition_ltf()

        entry_candidates = (
            htf_trend &
            mtf_trend &
            wave3["wave3_setup"].fillna(False) &
            volume_ok
        )
        return entry_candidates, wave3

    def _legacy_box_setup(self, htf_trend: pd.Series, mtf_trend: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
        higher_low = self.detector.detect_hl_mtf().reindex(self.detector.ltf.index, method='ffill')
        breakout, box_high = self.detector.detect_box_breakout_ltf()
        above_ema = self.detector.is_above_ema_ltf()
        volume_ok = self.detector.volume_condition_ltf()

        entry_candidates = (
            htf_trend &
            mtf_trend &
            higher_low &
            breakout &
            above_ema &
            volume_ok
        )
        setup = pd.DataFrame(index=self.detector.ltf.index)
        setup["box_high"] = box_high
        setup["entry_price"] = self.detector.ltf["Close"]
        setup["stop_loss"] = setup["entry_price"] * (1 - Config.STOP_LOSS_PCT)
        risk = setup["entry_price"] - setup["stop_loss"]
        setup["take_profit"] = setup["entry_price"] + (risk * Config.LEGACY_BOX_TARGET_R_MULTIPLE)
        reward = setup["take_profit"] - setup["entry_price"]
        setup["expected_gain_pct"] = (reward / setup["entry_price"]) * 100
        setup["risk_reward"] = Config.LEGACY_BOX_TARGET_R_MULTIPLE
        for column in ["wave1_low", "wave1_high", "wave2_low"]:
            setup[column] = pd.NA
        return entry_candidates, setup

    def _apply_trade_cycles(
        self,
        signals: pd.DataFrame,
        entry_candidates: pd.Series,
        setup: pd.DataFrame,
    ) -> None:
        in_position = False
        stop_loss = 0.0
        take_profit = 0.0
        signal_columns = [
            "wave1_low",
            "wave1_high",
            "wave2_low",
            "entry_price",
            "stop_loss",
            "take_profit",
            "expected_gain_pct",
            "risk_reward",
        ]

        for index, row in self.detector.ltf.iterrows():
            if in_position:
                if float(row["Low"]) <= stop_loss:
                    signals.loc[index, "exit"] = True
                    signals.loc[index, "exit_reason"] = "SL"
                    in_position = False
                    continue
                if float(row["High"]) >= take_profit:
                    signals.loc[index, "exit"] = True
                    signals.loc[index, "exit_reason"] = "TP"
                    in_position = False
                    continue
                continue

            if not bool(entry_candidates.loc[index]):
                continue

            candidate_stop = setup.loc[index, "stop_loss"]
            candidate_target = setup.loc[index, "take_profit"]
            if pd.isna(candidate_stop) or pd.isna(candidate_target):
                continue

            signals.loc[index, "entry"] = 1
            signals.loc[index, "box_high"] = setup.loc[index, "box_high"]
            for column in signal_columns:
                signals.loc[index, column] = setup.loc[index, column]

            stop_loss = float(candidate_stop)
            take_profit = float(candidate_target)
            in_position = True

    @staticmethod
    def summarize_performance(signals: pd.DataFrame) -> dict[str, object]:
        """Summarize completed TP/SL outcomes from generated signals."""
        if signals.empty or "entry" not in signals or "exit" not in signals:
            return {
                "entries": 0,
                "completed_trades": 0,
                "wins": 0,
                "losses": 0,
                "open_trades": 0,
                "win_rate": None,
            }

        entries = int((signals["entry"] == 1).sum())
        exits = signals[signals["exit"] == True]
        completed_trades = len(exits)
        wins = int((exits["exit_reason"] == "TP").sum()) if "exit_reason" in exits else 0
        losses = int((exits["exit_reason"] == "SL").sum()) if "exit_reason" in exits else 0
        win_rate = wins / completed_trades if completed_trades > 0 else None

        return {
            "entries": entries,
            "completed_trades": completed_trades,
            "wins": wins,
            "losses": losses,
            "open_trades": max(entries - completed_trades, 0),
            "win_rate": win_rate,
        }
