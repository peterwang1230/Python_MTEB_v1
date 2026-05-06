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
                "volume": float(row["Volume"]),
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
        entry_price = entries.loc[index].get("entry_price")
        if pd.isna(entry_price):
            entry_price = df.loc[index, "Close"]
        markers.append(
            {
                "time": _chart_time(index),
                "position": "belowBar",
                "color": COLOR_BULL,
                "shape": "arrowUp",
                "text": f"Buy3 ({float(entry_price):.2f})",
            }
        )
    return markers


def trade_history(signals: pd.DataFrame) -> pd.DataFrame:
    """Pair entries and exits into a compact trade ledger."""
    columns = [
        "Entry Time",
        "Entry Price",
        "Stop",
        "Target",
        "Expected Gain",
        "R/R",
        "Exit Time",
        "Exit Price",
        "Result",
    ]
    if signals.empty or "entry" not in signals:
        return pd.DataFrame(columns=columns)

    trades = []
    active_trade = None
    for index, row in signals.iterrows():
        if int(row.get("entry", 0)) == 1:
            active_trade = {
                "Entry Time": index,
                "Entry Price": row.get("entry_price"),
                "Stop": row.get("stop_loss"),
                "Target": row.get("take_profit"),
                "Expected Gain": row.get("expected_gain_pct"),
                "R/R": row.get("risk_reward"),
                "Exit Time": pd.NA,
                "Exit Price": pd.NA,
                "Result": "OPEN",
            }
            continue

        if active_trade is None or not bool(row.get("exit", False)):
            continue

        result = str(row.get("exit_reason"))
        active_trade["Exit Time"] = index
        active_trade["Result"] = result
        if result == "TP":
            active_trade["Exit Price"] = active_trade["Target"]
        elif result == "SL":
            active_trade["Exit Price"] = active_trade["Stop"]
        trades.append(active_trade)
        active_trade = None

    if active_trade is not None:
        trades.append(active_trade)

    return pd.DataFrame(trades, columns=columns)


def exit_signals_to_markers(df: pd.DataFrame, signals: pd.DataFrame) -> List[Dict[str, str | int]]:
    """Build TP/SL markers from paired trade exits."""
    markers = []
    trades = trade_history(signals)
    if trades.empty:
        return markers

    for _, trade in trades.iterrows():
        exit_time = trade["Exit Time"]
        result = trade["Result"]
        if pd.isna(exit_time) or result not in {"TP", "SL"} or exit_time not in df.index:
            continue

        is_win = result == "TP"
        exit_price = trade["Exit Price"]
        price_text = f" ({float(exit_price):.2f})" if pd.notna(exit_price) else ""
        markers.append(
            {
                "time": _chart_time(exit_time),
                "position": "aboveBar",
                "color": COLOR_BULL if is_win else COLOR_BEAR,
                "shape": "arrowDown",
                "text": f"{result}{price_text}",
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


def signal_level_to_line(signals: pd.DataFrame, column: str) -> List[Dict[str, float]]:
    """Extend the latest entry level through the latest chart bar."""
    if signals.empty or "entry" not in signals or column not in signals:
        return []

    entries = signals[(signals["entry"] == 1) & signals[column].notna()]
    if entries.empty:
        return []

    entry_index = entries.index[-1]
    last_index = signals.index[-1]
    value = float(entries.iloc[-1][column])
    points = [{"time": _chart_time(entry_index), "value": value}]
    if entry_index != last_index:
        points.append({"time": _chart_time(last_index), "value": value})
    return points


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


def chart_markers(df: pd.DataFrame, signals: pd.DataFrame, wave_points: List[Dict[str, float | str]]) -> List[Dict[str, str | int]]:
    """Build all chart markers in chronological order for stable rendering."""
    markers = (
        signals_to_markers(df, signals) +
        exit_signals_to_markers(df, signals) +
        pivot_wave_to_markers(wave_points)
    )
    return sorted(markers, key=lambda marker: int(marker["time"]))


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
        "markers": chart_markers(df, signals, wave_points),
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
        "stopLoss": signal_level_to_line(signals, "stop_loss"),
        "takeProfit": signal_level_to_line(signals, "take_profit"),
        "wave": pivot_wave_to_line(wave_points),
        "markers": chart_markers(df, signals, wave_points),
        "hoverRows": ohlcv_to_hover_rows(df),
    }


def latest_strategy_state(signals: pd.DataFrame) -> Dict[str, str]:
    """Summarize the latest strategy state for the Streamlit status strip."""
    if signals.empty:
        return {
            "entry": "NO DATA",
            "box_high": "-",
            "last_signal_time": "-",
            "entry_price": "-",
            "stop_loss": "-",
            "take_profit": "-",
            "expected_gain_pct": "-",
            "risk_reward": "-",
            "exit_reason": "-",
        }

    latest = signals.iloc[-1]
    entries = signals[signals["entry"] == 1] if "entry" in signals else pd.DataFrame()
    trades = trade_history(signals)
    latest_trade = trades.iloc[-1] if not trades.empty else pd.Series(dtype=object)
    exit_reason = latest_trade.get("Result", "-") if not trades.empty else "-"
    if exit_reason == "OPEN":
        exit_reason = "-"
    return {
        "entry": "Buy3" if int(latest.get("entry", 0)) == 1 else "WAIT",
        "box_high": f"{float(latest.get('box_high')):.2f}"
        if pd.notna(latest.get("box_high"))
        else "-",
        "last_signal_time": str(entries.index[-1]) if not entries.empty else "-",
        "entry_price": f"{float(latest_trade.get('Entry Price')):.2f}"
        if pd.notna(latest_trade.get("Entry Price"))
        else "-",
        "stop_loss": f"{float(latest_trade.get('Stop')):.2f}"
        if pd.notna(latest_trade.get("Stop"))
        else "-",
        "take_profit": f"{float(latest_trade.get('Target')):.2f}"
        if pd.notna(latest_trade.get("Target"))
        else "-",
        "expected_gain_pct": f"{float(latest_trade.get('Expected Gain')):.2f}%"
        if pd.notna(latest_trade.get("Expected Gain"))
        else "-",
        "risk_reward": f"{float(latest_trade.get('R/R')):.2f}"
        if pd.notna(latest_trade.get("R/R"))
        else "-",
        "exit_reason": str(exit_reason),
    }
