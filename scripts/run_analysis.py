#!/usr/bin/env python3
"""
Analysis script
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mteb_v1.data_loader import DataLoader
from mteb_v1.indicators import Indicators
import pandas as pd

def main():
    # Load sample data
    symbol = 'AAPL'
    start = '2023-01-01'
    end = '2024-01-01'

    df = DataLoader.load_yahoo(symbol, start, end)

    # Calculate indicators
    ema = Indicators.ema(df['Close'], 20)
    pivot_high, pivot_low = Indicators.pivot_points(df, 5)

    print(f"Data loaded: {len(df)} rows")
    print(f"EMA calculated: {ema.iloc[-1]:.2f}")
    print(f"Pivot highs: {pivot_high.sum()}")
    print(f"Pivot lows: {pivot_low.sum()}")

if __name__ == '__main__':
    main()