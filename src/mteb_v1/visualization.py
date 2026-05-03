import matplotlib.pyplot as plt
import plotly.graph_objects as go
from typing import Dict
import pandas as pd

class Visualizer:
    """Visualization for strategy results"""

    @staticmethod
    def plot_signals(df: pd.DataFrame, signals: pd.DataFrame):
        """Plot price with signals"""
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df.index, df['Close'], label='Close')

        # Plot entries
        entry_points = signals[signals['entry'] == 1]
        ax.scatter(entry_points.index, df.loc[entry_points.index, 'Close'],
                  marker='^', color='green', label='Entry')

        # Plot box high
        ax.plot(signals.index, signals['box_high'], color='orange', label='Box High')

        ax.legend()
        ax.set_title('MTEB-V1 Signals')
        plt.show()

    @staticmethod
    def plot_interactive(df: pd.DataFrame, signals: pd.DataFrame):
        """Interactive plot with Plotly"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close'))

        entry_points = signals[signals['entry'] == 1]
        fig.add_trace(go.Scatter(x=entry_points.index, y=df.loc[entry_points.index, 'Close'],
                                mode='markers', marker=dict(symbol='triangle-up', color='green'),
                                name='Entry'))

        fig.update_layout(title='MTEB-V1 Interactive Chart', xaxis_title='Date', yaxis_title='Price')
        fig.show()