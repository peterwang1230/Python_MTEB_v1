from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .config import Config
from .indicators import Indicators


COLOR_BULL = "rgba(38, 166, 154, 0.95)"
COLOR_BEAR = "rgba(239, 83, 80, 0.95)"
COLOR_GRID = "rgba(82, 91, 111, 0.18)"
COLOR_TEXT = "#d8dde8"
COLOR_PANEL = "#0f141d"
COLOR_BOX = "#d7b56d"
COLOR_WAVE_HIGH = "#77a7ff"
COLOR_WAVE_LOW = "#f0c86b"
COLOR_WAVE = "#b9c5d8"


def _chart_time(value: pd.Timestamp) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return int(timestamp.timestamp())


def ohlcv_to_candles(df: pd.DataFrame) -> List[Dict[str, float]]:
    """Convert an OHLCV DataFrame to Lightweight Charts candlestick data."""
    records = []
    for index, row in df.iterrows():
        records.append(
            {
                "time": _chart_time(index),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            }
        )
    return records


def ohlcv_to_hover_rows(df: pd.DataFrame) -> List[Dict[str, float | int | str]]:
    """Convert OHLC rows with wick metrics for browser-side cursor readout."""
    records = []
    for index, row in df.iterrows():
        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        body_high = max(open_price, close)
        body_low = min(open_price, close)
        records.append(
            {
                "time": _chart_time(index),
                "label": pd.Timestamp(index).strftime("%Y-%m-%d %H:%M"),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "upperWick": high - body_high,
                "lowerWick": body_low - low,
            }
        )
    return records


def ohlcv_to_volume(df: pd.DataFrame) -> List[Dict[str, float | str]]:
    """Convert volume data to a color-coded Lightweight Charts histogram."""
    records = []
    for index, row in df.iterrows():
        color = COLOR_BULL if row["Close"] >= row["Open"] else COLOR_BEAR
        records.append(
            {
                "time": _chart_time(index),
                "value": float(row["Volume"]),
                "color": color,
            }
        )
    return records


def signals_to_markers(df: pd.DataFrame, signals: pd.DataFrame) -> List[Dict[str, str | int]]:
    """Build BUY markers aligned to strategy entry signals."""
    if signals.empty or "entry" not in signals:
        return []

    entries = signals[signals["entry"] == 1]
    markers = []
    for index in entries.index:
        if index not in df.index:
            continue
        markers.append(
            {
                "time": _chart_time(index),
                "position": "belowBar",
                "color": COLOR_BULL,
                "shape": "arrowUp",
                "text": "BUY-3",
            }
        )
    return markers


def box_high_to_line(signals: pd.DataFrame) -> List[Dict[str, float]]:
    """Convert box high levels to a line series."""
    if signals.empty or "box_high" not in signals:
        return []

    series = signals["box_high"].dropna()
    return [
        {
            "time": _chart_time(index),
            "value": float(value),
        }
        for index, value in series.items()
    ]


def pivot_wave_points(df: pd.DataFrame, window: int = Config.PIVOT_WINDOW) -> List[Dict[str, float | str]]:
    """Build alternating pivot high/low points for a wave line overlay."""
    pivot_high, pivot_low = Indicators.pivot_points(df, window)
    points = []

    for index in df.index:
        if bool(pivot_high.get(index, False)):
            points.append(
                {
                    "time": _chart_time(index),
                    "value": float(df.loc[index, "High"]),
                    "kind": "H",
                }
            )
        if bool(pivot_low.get(index, False)):
            points.append(
                {
                    "time": _chart_time(index),
                    "value": float(df.loc[index, "Low"]),
                    "kind": "L",
                }
            )

    return _dedupe_adjacent_wave_points(points)


def _dedupe_adjacent_wave_points(points: List[Dict[str, float | str]]) -> List[Dict[str, float | str]]:
    wave = []
    for point in points:
        if not wave:
            wave.append(point)
            continue

        previous = wave[-1]
        if point["kind"] != previous["kind"]:
            wave.append(point)
            continue

        if point["kind"] == "H" and point["value"] > previous["value"]:
            wave[-1] = point
        elif point["kind"] == "L" and point["value"] < previous["value"]:
            wave[-1] = point

    return wave


def pivot_wave_to_line(wave_points: List[Dict[str, float | str]]) -> List[Dict[str, float]]:
    return [
        {
            "time": int(point["time"]),
            "value": float(point["value"]),
        }
        for point in wave_points
    ]


def pivot_wave_to_markers(wave_points: List[Dict[str, float | str]]) -> List[Dict[str, str | int]]:
    markers = []
    for point in wave_points:
        is_high = point["kind"] == "H"
        markers.append(
            {
                "time": int(point["time"]),
                "position": "aboveBar" if is_high else "belowBar",
                "color": COLOR_WAVE_HIGH if is_high else COLOR_WAVE_LOW,
                "shape": "circle",
                "text": point["kind"],
            }
        )
    return markers


def build_price_volume_chart(df: pd.DataFrame, signals: pd.DataFrame) -> List[Dict]:
    """Build the chart payload consumed by streamlit-lightweight-charts."""
    wave_points = pivot_wave_points(df)
    candle_series = {
        "type": "Candlestick",
        "data": ohlcv_to_candles(df),
        "options": {
            "upColor": COLOR_BULL,
            "downColor": COLOR_BEAR,
            "borderVisible": False,
            "wickUpColor": COLOR_BULL,
            "wickDownColor": COLOR_BEAR,
        },
        "markers": signals_to_markers(df, signals) + pivot_wave_to_markers(wave_points),
    }

    box_high_series = {
        "type": "Line",
        "data": box_high_to_line(signals),
        "options": {
            "color": COLOR_BOX,
            "lineWidth": 2,
            "lineStyle": 2,
            "priceLineVisible": False,
            "lastValueVisible": True,
        },
    }

    volume_series = {
        "type": "Histogram",
        "data": ohlcv_to_volume(df),
        "options": {
            "priceFormat": {"type": "volume"},
            "priceScaleId": "volume",
        },
        "priceScale": {
            "scaleMargins": {
                "top": 0.78,
                "bottom": 0,
            },
        },
    }

    wave_series = {
        "type": "Line",
        "data": pivot_wave_to_line(wave_points),
        "options": {
            "color": COLOR_WAVE,
            "lineWidth": 2,
            "priceLineVisible": False,
            "lastValueVisible": False,
            "crosshairMarkerVisible": True,
        },
    }

    chart_options = {
        "height": 640,
        "layout": {
            "background": {"type": "solid", "color": COLOR_PANEL},
            "textColor": COLOR_TEXT,
            "fontFamily": "Avenir Next, Helvetica Neue, sans-serif",
        },
        "grid": {
            "vertLines": {"color": COLOR_GRID},
            "horzLines": {"color": COLOR_GRID},
        },
        "rightPriceScale": {
            "borderVisible": False,
            "scaleMargins": {"top": 0.08, "bottom": 0.26},
        },
        "timeScale": {
            "borderVisible": False,
            "timeVisible": True,
            "secondsVisible": False,
        },
        "crosshair": {
            "mode": 1,
            "vertLine": {"color": "rgba(216, 221, 232, 0.22)"},
            "horzLine": {"color": "rgba(216, 221, 232, 0.22)"},
        },
    }

    return [
        {
            "chart": chart_options,
            "series": [candle_series, box_high_series, wave_series, volume_series],
        }
    ]


def build_interactive_chart_payload(df: pd.DataFrame, signals: pd.DataFrame) -> Dict[str, List[Dict]]:
    """Build payload for the custom browser-side Lightweight Charts component."""
    wave_points = pivot_wave_points(df)
    return {
        "candles": ohlcv_to_candles(df),
        "volume": ohlcv_to_volume(df),
        "boxHigh": box_high_to_line(signals),
        "wave": pivot_wave_to_line(wave_points),
        "markers": signals_to_markers(df, signals) + pivot_wave_to_markers(wave_points),
        "hoverRows": ohlcv_to_hover_rows(df),
    }


def latest_strategy_state(signals: pd.DataFrame) -> Dict[str, str]:
    """Summarize the latest strategy state for the Streamlit status strip."""
    if signals.empty:
        return {
            "entry": "NO DATA",
            "box_high": "-",
            "last_signal_time": "-",
        }

    latest = signals.iloc[-1]
    entries = signals[signals["entry"] == 1] if "entry" in signals else pd.DataFrame()
    return {
        "entry": "BUY-3" if int(latest.get("entry", 0)) == 1 else "WAIT",
        "box_high": f"{float(latest.get('box_high')):.2f}"
        if pd.notna(latest.get("box_high"))
        else "-",
        "last_signal_time": str(entries.index[-1]) if not entries.empty else "-",
    }
