#!/usr/bin/env python3
"""
Run backtest script
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mteb_v1.backtest import BacktestEngine
from mteb_v1.data_loader import DataLoader
from mteb_v1.strategy import StrategyEngine
from mteb_v1.structure import StructureDetector
from mteb_v1.visualization import Visualizer

def main():
    # Parameters
    symbol = 'AAPL'
    start = '2023-01-01'
    end = '2024-01-01'

    # Load data
    print("Loading data...")
    data_dict = DataLoader.load_multi_timeframe(symbol, start, end)

    # Create components
    detector = StructureDetector(data_dict)
    engine = StrategyEngine(detector)

    # Generate signals
    print("Generating signals...")
    signals = engine.generate_signals()

    # Visualize
    print("Plotting results...")
    Visualizer.plot_signals(data_dict['LTF'], signals)

    print("Backtest completed!")

if __name__ == '__main__':
    main()