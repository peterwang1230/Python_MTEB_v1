import pandas as pd
import numpy as np
from typing import Tuple
from .config import Config

class RiskManager:
    """Risk management for positions"""

    @staticmethod
    def calculate_stop_loss(entry_price: float) -> float:
        """Calculate stop loss price"""
        return entry_price * (1 - Config.STOP_LOSS_PCT)

    @staticmethod
    def calculate_trailing_stop(high_water_mark: float, current_price: float) -> float:
        """Calculate trailing stop"""
        trail_amount = high_water_mark * Config.TRAIL_PCT
        return max(high_water_mark - trail_amount, current_price * (1 - Config.STOP_LOSS_PCT))

    @staticmethod
    def check_exit_conditions(current_price: float, stop_loss: float, trailing_stop: float,
                           htf_trend: bool, mtf_trend: bool, hl_broken: bool) -> str:
        """Check various exit conditions"""
        if current_price <= stop_loss:
            return 'SL'
        if current_price <= trailing_stop:
            return 'TRAIL'
        if not htf_trend or not mtf_trend:
            return 'TREND'
        if hl_broken:
            return 'STRUCT'
        return None