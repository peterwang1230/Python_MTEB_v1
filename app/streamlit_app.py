from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from mteb_v1.data_loader import DataLoader
from mteb_v1 import config, streamlit_charts, strategy, structure

config = importlib.reload(config)
streamlit_charts = importlib.reload(streamlit_charts)
structure = importlib.reload(structure)
strategy = importlib.reload(strategy)
Config = config.Config
StructureDetector = structure.StructureDetector
StrategyEngine = strategy.StrategyEngine


st.set_page_config(
    page_title="MTEB-V1 Trading Desk",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #090d13;
            color: #d8dde8;
        }
        [data-testid="stSidebar"] {
            background: #0c1119;
            border-right: 1px solid rgba(216, 221, 232, 0.08);
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: #d8dde8;
        }
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 1.5rem;
            max-width: 1600px;
        }
        .desk-title {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid rgba(216, 221, 232, 0.08);
            padding-bottom: 0.85rem;
            margin-bottom: 0.85rem;
        }
        .desk-title h1 {
            font-family: Avenir Next, Helvetica Neue, sans-serif;
            font-size: 1.55rem;
            font-weight: 650;
            letter-spacing: 0;
            margin: 0;
            color: #f2f5f9;
        }
        .desk-title span {
            color: #8d99ad;
            font-size: 0.88rem;
        }
        .status-strip {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 1px;
            background: rgba(216, 221, 232, 0.08);
            border: 1px solid rgba(216, 221, 232, 0.08);
            margin-bottom: 0.9rem;
        }
        .status-cell {
            background: #0f141d;
            min-height: 72px;
            padding: 0.75rem 0.8rem;
        }
        .status-cell small {
            display: block;
            color: #8d99ad;
            font-size: 0.72rem;
            text-transform: uppercase;
            margin-bottom: 0.32rem;
        }
        .status-cell strong {
            color: #f2f5f9;
            font-size: 1rem;
            font-weight: 650;
        }
        .status-cell .ok { color: #26a69a; }
        .status-cell .wait { color: #d7b56d; }
        .status-cell .bad { color: #ef5350; }
        .data-note {
            color: #8d99ad;
            font-size: 0.85rem;
            margin-top: 0.35rem;
        }
        @media (max-width: 900px) {
            .status-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .desk-title {
                display: block;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(symbol: str, period: str, prepost: bool) -> tuple[str, dict[str, pd.DataFrame]]:
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    for candidate in yahoo_symbol_candidates(symbol):
        base_df = load_yahoo_history(candidate, period, yahoo_interval(Config.LTF), prepost)
        if not base_df.empty:
            return candidate, {
                "HTF": resample_to_timeframe(base_df, Config.HTF),
                "MTF": resample_to_timeframe(base_df, Config.MTF),
                "LTF": resample_to_timeframe(base_df, Config.LTF),
            }

    candidates = yahoo_symbol_candidates(symbol)
    return candidates[0] if candidates else symbol, {
        "HTF": empty.copy(),
        "MTF": empty.copy(),
        "LTF": empty.copy(),
    }


def yahoo_symbol_candidates(symbol: str) -> list[str]:
    normalized = symbol.strip().upper()
    if not normalized:
        return []
    if "." in normalized or not normalized.isdigit():
        return [normalized]
    return [f"{normalized}.TW", f"{normalized}.TWO", normalized]


def load_yahoo_history(
    symbol: str,
    period: str,
    interval: str,
    prepost: bool,
) -> pd.DataFrame:
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


def yahoo_interval(timeframe: str) -> str:
    return timeframe.strip().replace("min", "m")


def pandas_frequency(timeframe: str) -> str:
    normalized = timeframe.strip()
    if normalized.endswith("m") and normalized[:-1].isdigit():
        return f"{normalized[:-1]}min"
    return normalized.replace("H", "h")


def resample_to_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    timeframe = pandas_frequency(timeframe)
    ohlcv_dict = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    return df.resample(timeframe).agg(ohlcv_dict).dropna()


def last_flag(series: pd.Series) -> str:
    if series.empty or pd.isna(series.iloc[-1]):
        return "WAIT"
    return "ON" if bool(series.iloc[-1]) else "WAIT"


def condition_snapshot(detector: StructureDetector) -> dict[str, str]:
    wave3 = detector.detect_wave3_setup_ltf()
    return {
        "HTF": last_flag(detector.detect_trend_htf()),
        "MTF": last_flag(detector.detect_trend_mtf()),
        "HL": last_flag(detector.detect_hl_mtf()),
        "Wave3": last_flag(wave3["wave3_setup"]),
        "Volume": last_flag(detector.volume_condition_ltf()),
    }


def status_class(value: str) -> str:
    if value in {"ON", "Buy3"}:
        return "ok"
    if value in {"WAIT", "NO DATA"}:
        return "wait"
    return "bad"


def render_status(symbol: str, snapshot: dict[str, str], state: dict[str, str]) -> None:
    cells = [
        ("Symbol", symbol.upper()),
        ("HTF trend", snapshot.get("HTF", "WAIT")),
        ("MTF trend", snapshot.get("MTF", "WAIT")),
        ("Higher low", snapshot.get("HL", "WAIT")),
        ("Wave3 setup", snapshot.get("Wave3", "WAIT")),
        ("Signal", state["entry"]),
    ]
    html = ['<div class="status-strip">']
    for label, value in cells:
        html.append(
            f'<div class="status-cell"><small>{label}</small>'
            f'<strong class="{status_class(value)}">{value}</strong></div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_interactive_chart(df: pd.DataFrame, signals: pd.DataFrame, key: str) -> None:
    payload = streamlit_charts.build_interactive_chart_payload(df, signals)
    payload_json = json.dumps(payload)
    components.html(
        f"""
        <div id="chart-root-{key}" class="chart-root">
            <div class="hover-card">
                <div class="hover-symbol">Cursor</div>
                <div id="hover-date-{key}" class="hover-date">-</div>
                <div class="hover-grid">
                    <span>Open</span><strong id="hover-open-{key}">-</strong>
                    <span>Close</span><strong id="hover-close-{key}">-</strong>
                    <span>Volume</span><strong id="hover-volume-{key}">-</strong>
                    <span>Upper wick</span><strong id="hover-upper-{key}">-</strong>
                    <span>Lower wick</span><strong id="hover-lower-{key}">-</strong>
                </div>
            </div>
            <div id="chart-{key}" class="chart"></div>
        </div>
        <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        const payload = {payload_json};
        const root = document.getElementById("chart-root-{key}");
        const container = document.getElementById("chart-{key}");
        const hoverRows = new Map(payload.hoverRows.map(row => [row.time, row]));
        const fmt = value => Number(value).toFixed(2);
        const fmtVolume = value => new Intl.NumberFormat("en-US", {{
            maximumFractionDigits: 0,
        }}).format(Number(value));

        const chart = LightweightCharts.createChart(container, {{
            height: 640,
            layout: {{
                background: {{ type: "solid", color: "#0f141d" }},
                textColor: "#d8dde8",
                fontFamily: "Avenir Next, Helvetica Neue, sans-serif",
            }},
            grid: {{
                vertLines: {{ color: "rgba(82, 91, 111, 0.18)" }},
                horzLines: {{ color: "rgba(82, 91, 111, 0.18)" }},
            }},
            rightPriceScale: {{
                borderVisible: false,
                scaleMargins: {{ top: 0.08, bottom: 0.26 }},
            }},
            timeScale: {{
                borderVisible: false,
                timeVisible: true,
                secondsVisible: false,
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {{ color: "rgba(216, 221, 232, 0.28)" }},
                horzLine: {{ color: "rgba(216, 221, 232, 0.28)" }},
            }},
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: "rgba(38, 166, 154, 0.95)",
            downColor: "rgba(239, 83, 80, 0.95)",
            borderVisible: false,
            wickUpColor: "rgba(38, 166, 154, 0.95)",
            wickDownColor: "rgba(239, 83, 80, 0.95)",
        }});
        candleSeries.setData(payload.candles);
        candleSeries.setMarkers(payload.markers);

        const boxSeries = chart.addLineSeries({{
            color: "#d7b56d",
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            priceLineVisible: false,
            lastValueVisible: true,
        }});
        boxSeries.setData(payload.boxHigh);

        const stopSeries = chart.addLineSeries({{
            color: "#ef5350",
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            priceLineVisible: true,
            priceLineColor: "#ef5350",
            priceLineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
        }});
        stopSeries.setData(payload.stopLoss);

        const targetSeries = chart.addLineSeries({{
            color: "#26a69a",
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            priceLineVisible: true,
            priceLineColor: "#26a69a",
            priceLineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
        }});
        targetSeries.setData(payload.takeProfit);

        const waveSeries = chart.addLineSeries({{
            color: "#b9c5d8",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
        }});
        waveSeries.setData(payload.wave);

        const volumeSeries = chart.addHistogramSeries({{
            priceFormat: {{ type: "volume" }},
            priceScaleId: "volume",
        }});
        volumeSeries.priceScale().applyOptions({{
            scaleMargins: {{ top: 0.78, bottom: 0 }},
        }});
        volumeSeries.setData(payload.volume);

        function updateHover(row) {{
            document.getElementById("hover-date-{key}").textContent = row.label;
            document.getElementById("hover-open-{key}").textContent = fmt(row.open);
            document.getElementById("hover-close-{key}").textContent = fmt(row.close);
            document.getElementById("hover-volume-{key}").textContent = fmtVolume(row.volume);
            document.getElementById("hover-upper-{key}").textContent =
                fmt(row.high) + " / " + fmt(row.upperWick);
            document.getElementById("hover-lower-{key}").textContent =
                fmt(row.low) + " / " + fmt(row.lowerWick);
        }}

        if (payload.hoverRows.length > 0) {{
            updateHover(payload.hoverRows[payload.hoverRows.length - 1]);
        }}

        chart.subscribeCrosshairMove(param => {{
            if (!param || param.time === undefined) {{
                return;
            }}
            const row = hoverRows.get(param.time);
            if (row) {{
                updateHover(row);
            }}
        }});

        chart.timeScale().fitContent();
        new ResizeObserver(() => {{
            chart.applyOptions({{ width: root.clientWidth }});
            chart.timeScale().fitContent();
        }}).observe(root);
        </script>
        <style>
        .chart-root {{
            position: relative;
            width: 100%;
            height: 640px;
            background: #0f141d;
            border: 1px solid rgba(216, 221, 232, 0.12);
            overflow: hidden;
        }}
        .chart {{
            position: absolute;
            inset: 0;
        }}
        .hover-card {{
            position: absolute;
            z-index: 5;
            top: 12px;
            left: 12px;
            pointer-events: none;
            min-width: 300px;
            padding: 0.7rem 0.78rem;
            background: rgba(9, 13, 19, 0.84);
            border: 1px solid rgba(216, 221, 232, 0.12);
            backdrop-filter: blur(8px);
            font-family: Avenir Next, Helvetica Neue, sans-serif;
            color: #d8dde8;
        }}
        .hover-symbol {{
            color: #8d99ad;
            font-size: 0.72rem;
            text-transform: uppercase;
        }}
        .hover-date {{
            color: #f2f5f9;
            font-weight: 650;
            margin: 0.2rem 0 0.55rem;
        }}
        .hover-grid {{
            display: grid;
            grid-template-columns: repeat(4, auto);
            gap: 0.28rem 0.72rem;
            align-items: baseline;
            font-size: 0.78rem;
        }}
        .hover-grid span {{
            color: #8d99ad;
        }}
        .hover-grid strong {{
            color: #f2f5f9;
            font-weight: 650;
        }}
        @media (max-width: 720px) {{
            .hover-card {{
                left: 8px;
                right: 8px;
                min-width: 0;
            }}
            .hover-grid {{
                grid-template-columns: repeat(2, auto);
            }}
        }}
        </style>
        """,
        height=646,
    )


def query_param_value(name: str, default: str) -> str:
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value)


def main() -> None:
    apply_style()

    default_symbol = query_param_value("symbol", "AAPL").strip().upper() or "AAPL"
    if "symbol_input" not in st.session_state:
        st.session_state.symbol_input = default_symbol

    with st.sidebar:
        st.title("MTEB-V1")
        symbol = st.text_input("Symbol", key="symbol_input").strip().upper()
        if symbol and query_param_value("symbol", "") != symbol:
            st.query_params["symbol"] = symbol
        period = st.selectbox("History", ["5d", "1mo"], index=1)
        prepost = st.toggle("Pre/Post market", value=False)
        st.caption("Yahoo 15m intraday data is limited; use 1mo or shorter for reliable loading.")

        st.divider()
        st.subheader("Strategy")
        strategy_mode = st.selectbox(
            "Mode",
            ["Legacy Box Breakout", "Original Wave3", "Quality Filtered"],
            index=0,
        )
        if strategy_mode == "Legacy Box Breakout":
            Config.STRATEGY_MODE = "legacy_box"
            Config.WAVE3_USE_QUALITY_FILTERS = False
        elif strategy_mode == "Quality Filtered":
            Config.STRATEGY_MODE = "quality_wave3"
            Config.WAVE3_USE_QUALITY_FILTERS = True
        else:
            Config.STRATEGY_MODE = "wave3"
            Config.WAVE3_USE_QUALITY_FILTERS = False
        st.write(f"HTF: `{Config.HTF}`")
        st.write(f"MTF: `{Config.MTF}`")
        st.write(f"LTF: `{Config.LTF}`")
        st.write(f"EMA: `{Config.EMA_PERIOD}`")
        st.write(f"Box: `{Config.BOX_PERIOD}`")
        st.write(f"Volume x: `{Config.VOLUME_MULTIPLIER}`")
        if Config.STRATEGY_MODE == "legacy_box":
            st.write(f"Target R: `{Config.LEGACY_BOX_TARGET_R_MULTIPLE}`")
            st.write(f"Stop: `{Config.STOP_LOSS_PCT:.1%}`")
        elif Config.WAVE3_USE_QUALITY_FILTERS:
            st.write(f"Near H1: `{Config.WAVE3_BREAKOUT_TOLERANCE_PCT:.1%}`")
            st.write(f"Min R/R: `{Config.WAVE3_MIN_RISK_REWARD}`")
            st.write(f"Min Gain: `{Config.WAVE3_MIN_EXPECTED_GAIN_PCT:.1f}%`")

    st.markdown(
        f"""
        <div class="desk-title">
            <h1>{symbol or "AAPL"} Trading Desk</h1>
            <span>15m execution chart · 1H structure · 1D direction</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not symbol:
        st.warning("Enter a symbol to load market data.")
        return

    try:
        with st.spinner(f"Loading {symbol} from Yahoo Finance..."):
            resolved_symbol, data = load_market_data(symbol, period, prepost)
    except Exception as exc:
        st.error(f"Unable to load market data: {exc}")
        return

    if data["LTF"].empty:
        candidates = ", ".join(yahoo_symbol_candidates(symbol))
        st.warning(f"No market data returned. Tried: {candidates}. Try another symbol or shorter history.")
        return

    try:
        detector = StructureDetector(data)
        engine = StrategyEngine(detector)
        signals = engine.generate_signals()
        performance = engine.summarize_performance(signals)
        snapshot = condition_snapshot(detector)
    except Exception as exc:
        st.error(f"Unable to evaluate strategy: {exc}")
        return

    state = streamlit_charts.latest_strategy_state(signals)
    trades = streamlit_charts.trade_history(signals)
    render_status(resolved_symbol, snapshot, state)

    chart_key = f"{resolved_symbol}-{period}-{prepost}".replace(".", "-").replace("_", "-")
    render_interactive_chart(data["LTF"], signals, chart_key)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Latest")
        win_rate = performance["win_rate"]
        metric_cols = st.columns(6)
        metric_cols[0].metric("Entries", performance["entries"])
        metric_cols[1].metric("Closed", performance["completed_trades"])
        metric_cols[2].metric("Open", performance["open_trades"])
        metric_cols[3].metric("Wins", performance["wins"])
        metric_cols[4].metric("Losses", performance["losses"])
        metric_cols[5].metric("Win Rate", f"{win_rate:.1%}" if win_rate is not None else "-")
        latest_bar = data["LTF"].iloc[-1]
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Close": round(float(latest_bar["Close"]), 2),
                        "Volume": int(latest_bar["Volume"]),
                        "Entry": state["entry_price"],
                        "Stop": state["stop_loss"],
                        "Target": state["take_profit"],
                        "Expected Gain": state["expected_gain_pct"],
                        "R/R": state["risk_reward"],
                        "Exit": state["exit_reason"],
                        "Last Buy3": state["last_signal_time"],
                        "Open Trades": performance["open_trades"],
                    }
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    with right:
        st.subheader("Trade History")
        if trades.empty:
            st.info("No trades generated for the loaded history.")
        else:
            display_trades = trades.copy().sort_values("Entry Time", ascending=False)
            for column in ["Entry Time", "Exit Time"]:
                display_trades[column] = display_trades[column].apply(
                    lambda value: "-" if pd.isna(value) else str(value)
                )
            for column in ["Entry Price", "Stop", "Target", "Exit Price", "R/R"]:
                display_trades[column] = display_trades[column].apply(
                    lambda value: "-" if pd.isna(value) else f"{float(value):.2f}"
                )
            display_trades["Expected Gain"] = display_trades["Expected Gain"].apply(
                lambda value: "-" if pd.isna(value) else f"{float(value):.2f}%"
            )
            st.dataframe(
                display_trades,
                hide_index=True,
                use_container_width=True,
            )

        st.subheader("Signals")
        st.dataframe(
            signals.tail(25).sort_index(ascending=False),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
