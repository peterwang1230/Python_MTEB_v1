import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from .config import Config

class DataLoader:
    """Load and resample data for multi-timeframe analysis"""

    @staticmethod
    def normalize_timeframe(timeframe: str) -> str:
        """Normalize timeframe aliases for current pandas frequency parsing."""
        normalized = timeframe.strip()
        if normalized.endswith("m") and normalized[:-1].isdigit():
            return f"{normalized[:-1]}min"
        return normalized.replace("H", "h")

    @staticmethod
    def yahoo_symbol_candidates(symbol: str) -> List[str]:
        """Return likely Yahoo Finance symbols for a user-entered ticker."""
        normalized = symbol.strip().upper()
        if not normalized:
            return []
        if "." in normalized or not normalized.isdigit():
            return [normalized]
        return [f"{normalized}.TW", f"{normalized}.TWO", normalized]

    @staticmethod
    def load_yahoo(symbol: str, start: str, end: str) -> pd.DataFrame:
        """Load data from Yahoo Finance"""
        df = yf.download(symbol, start=start, end=end)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.index = pd.to_datetime(df.index)
        return df

    @staticmethod
    def load_yahoo_history(
        symbol: str,
        period: str = "2mo",
        interval: str = "15m",
        prepost: bool = False,
    ) -> pd.DataFrame:
        """Load recent Yahoo Finance history for charting and intraday analysis."""
        df = yf.Ticker(symbol).history(
            period=period,
            interval=interval,
            prepost=prepost,
            auto_adjust=False,
        )
        if df.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        return df

    @classmethod
    def load_first_available_history(
        cls,
        symbol: str,
        period: str = "2mo",
        interval: str = "15m",
        prepost: bool = False,
    ) -> Tuple[str, pd.DataFrame]:
        """Load the first non-empty Yahoo history across likely symbol variants."""
        candidates = cls.yahoo_symbol_candidates(symbol)
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        for candidate in candidates:
            df = cls.load_yahoo_history(candidate, period, interval, prepost)
            if not df.empty:
                return candidate, df

        return candidates[0] if candidates else symbol, empty

    @staticmethod
    def resample_to_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample data to specified timeframe"""
        timeframe = DataLoader.normalize_timeframe(timeframe)
        ohlcv_dict = {
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }
        return df.resample(timeframe).agg(ohlcv_dict).dropna()

    @classmethod
    def load_multi_timeframe(cls, symbol: str, start: str, end: str) -> Dict[str, pd.DataFrame]:
        """Load data for all timeframes"""
        base_df = cls.load_yahoo(symbol, start, end)

        timeframes = {
            'HTF': Config.HTF,
            'MTF': Config.MTF,
            'LTF': Config.LTF
        }

        data = {}
        for name, tf in timeframes.items():
            data[name] = cls.resample_to_timeframe(base_df, tf)

        return data

    @classmethod
    def load_multi_timeframe_history(
        cls,
        symbol: str,
        period: str = "2mo",
        interval: str = "15m",
        prepost: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """Load recent market data and derive the configured strategy timeframes."""
        _, base_df = cls.load_first_available_history(symbol, period, interval, prepost)
        if base_df.empty:
            return {"HTF": base_df.copy(), "MTF": base_df.copy(), "LTF": base_df.copy()}

        return {
            "HTF": cls.resample_to_timeframe(base_df, Config.HTF),
            "MTF": cls.resample_to_timeframe(base_df, Config.MTF),
            "LTF": cls.resample_to_timeframe(base_df, Config.LTF),
        }

    @classmethod
    def load_resolved_multi_timeframe_history(
        cls,
        symbol: str,
        period: str = "2mo",
        interval: str = "15m",
        prepost: bool = False,
    ) -> Tuple[str, Dict[str, pd.DataFrame]]:
        """Load recent market data and return the Yahoo symbol that worked."""
        resolved_symbol, base_df = cls.load_first_available_history(
            symbol,
            period,
            interval,
            prepost,
        )
        if base_df.empty:
            empty_data = {"HTF": base_df.copy(), "MTF": base_df.copy(), "LTF": base_df.copy()}
            return resolved_symbol, empty_data

        return resolved_symbol, {
            "HTF": cls.resample_to_timeframe(base_df, Config.HTF),
            "MTF": cls.resample_to_timeframe(base_df, Config.MTF),
            "LTF": cls.resample_to_timeframe(base_df, Config.LTF),
        }
