"""
MTEB-V4 Backtest System - data_loader.py

Purpose
-------
Load OHLCV market data into a clean pandas DataFrame for downstream modules:
- indicators.py
- signal_engine.py
- position_sizer.py
- backtester.py
- report.py

Supported sources in this first version:
1. CSV file
2. Yahoo Finance via yfinance

Required output schema:
    DatetimeIndex
    columns = ['open', 'high', 'low', 'close', 'volume']

Optional adjusted close is kept as 'adj_close' when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

import pandas as pd


DataSource = Literal["csv", "yahoo"]
Timeframe = Literal["1d", "1wk", "1mo", "1h", "30m", "15m", "5m"]


@dataclass(frozen=True)
class DataConfig:
    """Configuration for loading price data."""

    source: DataSource
    symbol: str
    start: Optional[str] = None
    end: Optional[str] = None
    timeframe: Timeframe = "1d"
    csv_path: Optional[str | Path] = None
    timezone: Optional[str] = None
    auto_adjust: bool = False


class DataLoaderError(Exception):
    """Raised when data loading or validation fails."""


class DataLoader:
    """Load and normalize OHLCV data for the backtest engine."""

    REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]

    COLUMN_ALIASES = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Adj_Close": "adj_close",
        "AdjClose": "adj_close",
        "Volume": "volume",
        "Date": "date",
        "Datetime": "datetime",
        "Timestamp": "datetime",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "adj_close": "adj_close",
        "volume": "volume",
        "date": "date",
        "datetime": "datetime",
        "timestamp": "datetime",
    }

    def __init__(self, config: DataConfig):
        self.config = config

    def load(self) -> pd.DataFrame:
        """Load data from the configured source and return normalized OHLCV data."""
        if self.config.source == "csv":
            df = self._load_csv()
        elif self.config.source == "yahoo":
            df = self._load_yahoo()
        else:
            raise DataLoaderError(f"Unsupported data source: {self.config.source}")

        return self._normalize(df)

    def _load_csv(self) -> pd.DataFrame:
        if not self.config.csv_path:
            raise DataLoaderError("csv_path is required when source='csv'.")

        path = Path(self.config.csv_path)
        if not path.exists():
            raise DataLoaderError(f"CSV file not found: {path}")

        try:
            return pd.read_csv(path)
        except Exception as exc:
            raise DataLoaderError(f"Failed to read CSV file: {path}") from exc

    def _load_yahoo(self) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise DataLoaderError(
                "yfinance is not installed. Install it with: pip install yfinance"
            ) from exc

        try:
            df = yf.download(
                tickers=self.config.symbol,
                start=self.config.start,
                end=self.config.end,
                interval=self.config.timeframe,
                auto_adjust=self.config.auto_adjust,
                progress=False,
            )
        except Exception as exc:
            raise DataLoaderError(f"Yahoo download failed for {self.config.symbol}") from exc

        if df.empty:
            raise DataLoaderError(f"No data returned for symbol: {self.config.symbol}")

        return df.reset_index()

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names, parse datetime, validate OHLCV, and clean rows."""
        if df.empty:
            raise DataLoaderError("Input DataFrame is empty.")

        df = df.copy()

        # Flatten MultiIndex columns returned by yfinance in some cases.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        df = df.rename(columns={col: self.COLUMN_ALIASES.get(str(col), str(col)) for col in df.columns})

        date_col = self._find_datetime_column(df)
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df = df.set_index(date_col)
        df.index.name = "datetime"

        if self.config.timezone:
            df = self._apply_timezone(df, self.config.timezone)

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise DataLoaderError(f"Missing required columns: {missing}")

        keep_cols = self.REQUIRED_COLUMNS.copy()
        if "adj_close" in df.columns:
            keep_cols.append("adj_close")

        df = df[keep_cols]
        df = self._coerce_numeric(df)
        df = self._clean_ohlcv(df)
        df = self._filter_date_range(df)

        return df

    @staticmethod
    def _find_datetime_column(df: pd.DataFrame) -> str:
        for candidate in ["datetime", "date"]:
            if candidate in df.columns:
                return candidate
        raise DataLoaderError("No datetime/date column found in input data.")

    @staticmethod
    def _apply_timezone(df: pd.DataFrame, timezone: str) -> pd.DataFrame:
        if df.index.tz is None:
            df.index = df.index.tz_localize(timezone)
        else:
            df.index = df.index.tz_convert(timezone)
        return df

    @staticmethod
    def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        # Remove rows with missing core OHLC values.
        df = df.dropna(subset=["open", "high", "low", "close"])

        # Volume can be missing for some index/fund data; fill with 0 for engine compatibility.
        df["volume"] = df["volume"].fillna(0)

        # Basic market data sanity checks.
        valid = (
            (df["high"] >= df[["open", "close", "low"]].max(axis=1))
            & (df["low"] <= df[["open", "close", "high"]].min(axis=1))
            & (df["open"] > 0)
            & (df["high"] > 0)
            & (df["low"] > 0)
            & (df["close"] > 0)
            & (df["volume"] >= 0)
        )
        df = df.loc[valid]

        if df.empty:
            raise DataLoaderError("No valid OHLCV rows remain after cleaning.")

        return df

    def _filter_date_range(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.config.start:
            df = df.loc[df.index >= pd.Timestamp(self.config.start, tz=df.index.tz)]
        if self.config.end:
            df = df.loc[df.index < pd.Timestamp(self.config.end, tz=df.index.tz)]

        if df.empty:
            raise DataLoaderError("No data remains after applying start/end filters.")

        return df


if __name__ == "__main__":
    # Example 1: Yahoo Finance
    config = DataConfig(
        source="yahoo",
        symbol="AAPL",
        start="2020-01-01",
        end="2024-01-01",
        timeframe="1d",
        auto_adjust=False,
    )

    loader = DataLoader(config)
    data = loader.load()
    print(data.head())
    print(data.tail())
    print(data.info())

    # Example 2: CSV
    # config = DataConfig(
    #     source="csv",
    #     symbol="2330.TW",
    #     csv_path="data/2330_TW.csv",
    #     start="2020-01-01",
    #     end="2024-01-01",
    # )
    # data = DataLoader(config).load()
