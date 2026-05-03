import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from src.mteb_v1.visualization import Visualizer


def make_price_data():
    index = pd.date_range("2023-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "Close": [100, 102, 101, 105],
        },
        index=index,
    )


def make_signals(index):
    return pd.DataFrame(
        {
            "entry": [0, 1, 0, 1],
            "box_high": [103, 103, 104, 104],
        },
        index=index,
    )


def test_plot_signals_draws_close_entries_and_box_high(monkeypatch):
    df = make_price_data()
    signals = make_signals(df.index)
    shown = {"called": False}

    def fake_show():
        shown["called"] = True

    monkeypatch.setattr("src.mteb_v1.visualization.plt.show", fake_show)
    plt.close("all")

    Visualizer.plot_signals(df, signals)

    fig = plt.gcf()
    ax = fig.axes[0]
    lines = ax.get_lines()

    assert shown["called"] is True
    assert ax.get_title() == "MTEB-V1 Signals"
    assert lines[0].get_label() == "Close"
    assert lines[0].get_ydata().tolist() == [100, 102, 101, 105]
    assert lines[1].get_label() == "Box High"
    assert lines[1].get_ydata().tolist() == [103, 103, 104, 104]
    assert ax.collections[0].get_label() == "Entry"
    assert ax.collections[0].get_offsets().shape[0] == 2

    plt.close(fig)


def test_plot_interactive_adds_close_and_entry_traces(monkeypatch):
    df = make_price_data()
    signals = make_signals(df.index)
    shown = {"figure": None}

    def fake_show(self):
        shown["figure"] = self

    monkeypatch.setattr("src.mteb_v1.visualization.go.Figure.show", fake_show)

    Visualizer.plot_interactive(df, signals)

    fig = shown["figure"]
    assert fig is not None
    assert fig.layout.title.text == "MTEB-V1 Interactive Chart"
    assert fig.layout.xaxis.title.text == "Date"
    assert fig.layout.yaxis.title.text == "Price"
    assert len(fig.data) == 2
    assert fig.data[0].name == "Close"
    assert fig.data[0].mode == "lines"
    assert list(fig.data[0].y) == [100, 102, 101, 105]
    assert fig.data[1].name == "Entry"
    assert fig.data[1].mode == "markers"
    assert fig.data[1].marker.symbol == "triangle-up"
    assert list(fig.data[1].y) == [102, 105]
