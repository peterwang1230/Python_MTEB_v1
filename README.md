# MTEB-V1 Strategy

Multi-Timeframe Trend Expansion Breakout Strategy

## Installation

```bash
pip install -e .
```

## Usage

See scripts/ for examples.

## Streamlit Trading Desk

Run the TradingView-style research interface:

```bash
pip install -e .
streamlit run app/streamlit_app.py
```

The first version loads recent Yahoo Finance data through `yfinance`, derives the
configured HTF/MTF/LTF frames, and renders candlesticks, volume, box-high levels,
and BUY-3 markers with Lightweight Charts.

Because the app uses Yahoo 15m intraday bars, keep the history selection at
`1mo` or shorter. Longer intraday ranges may return no data from Yahoo Finance.
