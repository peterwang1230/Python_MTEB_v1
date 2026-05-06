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
    STRATEGY_MODE = "wave3"  # "legacy_box", "wave3", or "quality_wave3"
    LEGACY_BOX_TARGET_R_MULTIPLE = 2.0  # Legacy breakout take-profit in R
    WAVE3_REBOUND_LOOKBACK = 3  # Bars used to confirm price turning up after wave 2
    WAVE3_TARGET_EXTENSION = 1.618  # Estimated wave 3 target from wave 1 length
    WAVE3_STOP_BUFFER_PCT = 0.005  # Stop slightly below the wave 2 low
    WAVE3_USE_QUALITY_FILTERS = False  # Keep original Wave3 behavior by default
    WAVE3_BREAKOUT_TOLERANCE_PCT = 0.005  # Allow entries within 0.5% below H1
    WAVE3_MIN_RISK_REWARD = 1.5  # Reject low-quality entries with poor reward/risk
    WAVE3_MIN_EXPECTED_GAIN_PCT = 2.0  # Reject setups with too little upside

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
