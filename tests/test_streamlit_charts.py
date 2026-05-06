import pandas as pd

from src.mteb_v1.streamlit_charts import (
    build_interactive_chart_payload,
    build_price_volume_chart,
    box_high_to_line,
    chart_markers,
    exit_signals_to_markers,
    latest_strategy_state,
    ohlcv_to_candles,
    ohlcv_to_hover_rows,
    ohlcv_to_volume,
    pivot_wave_points,
    pivot_wave_to_line,
    signal_level_to_line,
    signals_to_markers,
    trade_history,
)


def make_ohlcv():
    index = pd.date_range("2023-01-01 09:30", periods=3, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100, 102, 101],
            "High": [103, 104, 105],
            "Low": [99, 101, 100],
            "Close": [102, 101, 104],
            "Volume": [1000, 1500, 2000],
        },
        index=index,
    )


def make_signals(index):
    return pd.DataFrame(
        {
            "entry": [0, 1, 0],
            "box_high": [103, 103, 104],
            "entry_price": [None, 101, None],
            "stop_loss": [None, 99, None],
            "take_profit": [None, 112, None],
            "exit": [False, False, True],
            "exit_reason": [None, None, "TP"],
        },
        index=index,
    )


def test_ohlcv_to_candles_converts_rows_to_lightweight_chart_shape():
    candles = ohlcv_to_candles(make_ohlcv())

    assert len(candles) == 3
    assert candles[0]["time"] == 1672565400
    assert candles[0]["open"] == 100
    assert candles[0]["high"] == 103
    assert candles[0]["low"] == 99
    assert candles[0]["close"] == 102


def test_ohlcv_to_volume_colors_up_and_down_bars():
    volume = ohlcv_to_volume(make_ohlcv())

    assert volume[0]["value"] == 1000
    assert "38, 166, 154" in volume[0]["color"]
    assert "239, 83, 80" in volume[1]["color"]


def test_ohlcv_to_hover_rows_includes_wick_metrics():
    hover_rows = ohlcv_to_hover_rows(make_ohlcv())

    assert hover_rows[0]["open"] == 100
    assert hover_rows[0]["close"] == 102
    assert hover_rows[0]["volume"] == 1000
    assert hover_rows[0]["upperWick"] == 1
    assert hover_rows[0]["lowerWick"] == 1


def test_signals_to_markers_creates_buy_3_marker_for_entries():
    df = make_ohlcv()
    signals = make_signals(df.index)

    markers = signals_to_markers(df, signals)

    assert markers == [
        {
            "time": 1672566300,
            "position": "belowBar",
            "color": "rgba(38, 166, 154, 0.95)",
            "shape": "arrowUp",
            "text": "Buy3 (101.00)",
        }
    ]


def test_exit_signals_to_markers_creates_tp_sl_markers():
    df = make_ohlcv()
    signals = make_signals(df.index)

    markers = exit_signals_to_markers(df, signals)

    assert markers == [
        {
            "time": 1672567200,
            "position": "aboveBar",
            "color": "rgba(38, 166, 154, 0.95)",
            "shape": "arrowDown",
            "text": "TP (112.00)",
        }
    ]


def test_trade_history_pairs_entry_with_exit():
    df = make_ohlcv()
    signals = make_signals(df.index)

    trades = trade_history(signals)

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["Entry Time"] == df.index[1]
    assert trade["Entry Price"] == 101
    assert trade["Exit Time"] == df.index[2]
    assert trade["Exit Price"] == 112
    assert trade["Result"] == "TP"


def test_chart_markers_are_sorted_for_stable_lightweight_chart_rendering():
    df = make_ohlcv()
    signals = make_signals(df.index)
    wave_points = [
        {"time": 1672565400, "value": 103.0, "kind": "H"},
        {"time": 1672567200, "value": 100.0, "kind": "L"},
    ]

    markers = chart_markers(df, signals, wave_points)

    assert [marker["time"] for marker in markers] == [1672565400, 1672566300, 1672567200, 1672567200]
    assert [marker["text"] for marker in markers] == ["H", "Buy3 (101.00)", "TP (112.00)", "L"]


def test_box_high_to_line_keeps_time_aligned_levels():
    df = make_ohlcv()
    signals = make_signals(df.index)

    line = box_high_to_line(signals)

    assert [point["value"] for point in line] == [103, 103, 104]
    assert [point["time"] for point in line] == [1672565400, 1672566300, 1672567200]


def test_signal_level_to_line_extends_latest_entry_to_last_bar():
    df = make_ohlcv()
    signals = make_signals(df.index)

    line = signal_level_to_line(signals, "take_profit")

    assert [point["time"] for point in line] == [1672566300, 1672567200]
    assert [point["value"] for point in line] == [112, 112]


def test_build_price_volume_chart_returns_chart_series_payload():
    df = make_ohlcv()
    signals = make_signals(df.index)

    charts = build_price_volume_chart(df, signals)

    assert len(charts) == 1
    assert charts[0]["chart"]["height"] == 640
    assert [series["type"] for series in charts[0]["series"]] == [
        "Candlestick",
        "Line",
        "Line",
        "Histogram",
    ]
    assert charts[0]["series"][0]["markers"][0]["text"] == "Buy3 (101.00)"


def test_pivot_wave_to_line_keeps_time_and_price_only():
    wave = pivot_wave_to_line(
        [
            {"time": 1672565400, "value": 103.0, "kind": "H"},
            {"time": 1672566300, "value": 101.0, "kind": "L"},
        ]
    )

    assert wave == [
        {"time": 1672565400, "value": 103.0},
        {"time": 1672566300, "value": 101.0},
    ]


def test_pivot_wave_points_only_uses_true_pivot_nodes():
    index = pd.date_range("2023-01-01", periods=7, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [1, 1, 4, 2, 1, 1, 2],
            "High": [1, 2, 5, 2, 1, 2, 3],
            "Low": [1, 0, 1, 2, 1, 0, 1],
            "Close": [1, 1, 4, 2, 1, 1, 2],
            "Volume": [100 for _ in range(7)],
        },
        index=index,
    )

    points = pivot_wave_points(df, window=1)

    assert [point["kind"] for point in points] == ["L", "H", "L"]
    assert [point["value"] for point in points] == [0, 5, 0]


def test_build_interactive_chart_payload_includes_hover_and_wave_layers():
    df = make_ohlcv()
    signals = make_signals(df.index)

    payload = build_interactive_chart_payload(df, signals)

    assert set(payload) == {
        "candles",
        "volume",
        "boxHigh",
        "stopLoss",
        "takeProfit",
        "wave",
        "markers",
        "hoverRows",
    }
    assert payload["hoverRows"][0]["upperWick"] == 1
    assert payload["markers"][0]["text"] == "Buy3 (101.00)"
    assert any(marker["text"] == "TP (112.00)" for marker in payload["markers"])
    assert payload["stopLoss"][0]["value"] == 99
    assert payload["takeProfit"][0]["value"] == 112


def test_latest_strategy_state_summarizes_waiting_state_and_last_entry():
    df = make_ohlcv()
    signals = make_signals(df.index)

    state = latest_strategy_state(signals)

    assert state["entry"] == "WAIT"
    assert state["box_high"] == "104.00"
    assert state["last_signal_time"] == "2023-01-01 09:45:00+00:00"
    assert state["exit_reason"] == "TP"
