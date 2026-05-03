import os
from typing import Dict, Any

class Config:
    """Configuration for MTEB-V1 Strategy"""

    # Timeframes
    HTF = '1D'  # Daily
    MTF = '1h'  # Hourly
    LTF = '15m'  # 15 minutes

    # Indicators
    PIVOT_WINDOW = 5  # For pivot detection
    EMA_PERIOD = 20
    BOX_PERIOD = 20  # For box detection

    # Volume thresholds
    VOLUME_MULTIPLIER = 1.5  # Breakout volume > avg * this

    # Risk management
    STOP_LOSS_PCT = 0.05  # 5%
    TRAIL_PCT = 0.02  # 2% trail

    # Data
    DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data')

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {k: v for k, v in cls.__dict__.items() if not k.startswith('_')}
