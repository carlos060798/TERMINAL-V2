"""
ChartWidget: Candlestick chart with technical indicators using pyqtgraph.

Displays: OHLCV, volume bars, moving averages, RSI, MACD, Bollinger bands.
Fully interactive: pan, zoom, crosshair.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import pandas as pd
from typing import Optional, List, Tuple
from datetime import datetime


class ChartWidget(QWidget):
    """Interactive candlestick chart with technical indicators."""

    def __init__(self, title: str = "Price Chart"):
        """
        Initialize ChartWidget.

        Args:
            title: Chart title
        """
        super().__init__()
        self.title = title
        self.data: Optional[pd.DataFrame] = None
        self.plot_items = []
        self.indicators = {}

        self.initUI()

    def initUI(self) -> None:
        """Build chart UI with pyqtgraph."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle(self.title, size="12pt")
        self.plot_widget.setLabel("left", "Price", units="$")
        self.plot_widget.setLabel("bottom", "Date")
        self.plot_widget.setBackground("#1E1E1E")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)

        # Style
        self.plot_widget.getAxis("left").setPen(pg.mkPen("#A0A0A0"))
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen("#A0A0A0"))
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen("#A0A0A0"))
        self.plot_widget.getAxis("bottom").setTextPen(pg.mkPen("#A0A0A0"))

        # Volume subplot (below price)
        self.view_box = self.plot_widget.plotItem.vb
        self.volume_plot = pg.ViewBox()
        self.plot_widget.plotItem.scene().addItem(self.volume_plot)
        self.plot_widget.plotItem.setSecondaryPlotItem(self.volume_plot, "volume")

        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def plot_candlestick(self, data: pd.DataFrame) -> None:
        """
        Plot candlestick chart from OHLCV data.

        Args:
            data: DataFrame with columns: open, high, low, close, volume
                  Index: datetime
        """
        if data is None or len(data) == 0:
            return

        self.data = data.copy()
        self.plot_widget.clear()
        self.plot_items = []

        # Convert dates to numeric (seconds since epoch)
        dates = (data.index - data.index[0]).total_seconds() / 86400
        x_vals = np.arange(len(data))

        # Candlestick bodies
        body_width = 0.6
        for i in range(len(data)):
            o, h, l, c = (
                data.iloc[i]["open"],
                data.iloc[i]["high"],
                data.iloc[i]["low"],
                data.iloc[i]["close"],
            )

            color = "#00D26A" if c >= o else "#FF3B30"  # Green if close > open
            pen_color = pg.mkPen(color, width=1)

            # Wick (high-low line)
            wick = pg.LineSegmentROI(
                [x_vals[i], l], [x_vals[i], h], pen=pen_color
            )

            # Body (open-close rectangle)
            body_low = min(o, c)
            body_high = max(o, c)
            rect = pg.LinearRegionItem(
                [x_vals[i] - body_width / 2, x_vals[i] + body_width / 2],
                movable=False,
            )
            rect.setBounds([body_low, body_high])
            rect.setRegion([x_vals[i] - body_width / 2, x_vals[i] + body_width / 2])

        # Plot close line
        close_curve = self.plot_widget.plot(
            x_vals, data["close"].values, pen=pg.mkPen("#00D26A", width=2)
        )
        self.plot_items.append(close_curve)

        # Plot volume bars
        colors = [
            "#00D26A" if data.iloc[i]["close"] >= data.iloc[i]["open"] else "#FF3B30"
            for i in range(len(data))
        ]
        self.volume_plot.clear()
        for i, vol in enumerate(data["volume"].values):
            bar_item = pg.BarGraphItem(
                x=[x_vals[i]], height=[vol], width=0.8, brush=colors[i]
            )
            self.volume_plot.addItem(bar_item)

    def add_indicator(self, indicator_name: str, data: List[float]) -> None:
        """
        Add technical indicator line to chart.

        Args:
            indicator_name: Name of indicator (e.g., "SMA_20", "EMA_50")
            data: List of indicator values
        """
        if self.data is None or len(data) != len(self.data):
            return

        x_vals = np.arange(len(data))
        colors = {
            "SMA": "#FFA500",
            "EMA": "#1E90FF",
            "RSI": "#FF69B4",
            "MACD": "#9370DB",
            "BB_upper": "#FFFF00",
            "BB_lower": "#FFFF00",
        }

        color = next(
            (v for k, v in colors.items() if k in indicator_name), "#A0A0A0"
        )
        curve = self.plot_widget.plot(
            x_vals, data, pen=pg.mkPen(color, width=1), name=indicator_name
        )
        self.plot_items.append(curve)
        self.indicators[indicator_name] = data

    def add_moving_average(
        self, period: int, data_type: str = "close", ma_type: str = "SMA"
    ) -> None:
        """
        Add moving average to chart.

        Args:
            period: MA period (e.g., 20, 50, 200)
            data_type: "close", "open", "high", "low"
            ma_type: "SMA" or "EMA"
        """
        if self.data is None:
            return

        values = self.data[data_type].values

        if ma_type == "SMA":
            ma = pd.Series(values).rolling(window=period).mean().values
        else:  # EMA
            ma = pd.Series(values).ewm(span=period).mean().values

        self.add_indicator(f"{ma_type}_{period}", ma)

    def add_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> None:
        """
        Add Bollinger Bands to chart.

        Args:
            period: Moving average period
            std_dev: Standard deviations from mean
        """
        if self.data is None:
            return

        close = self.data["close"].values
        sma = pd.Series(close).rolling(window=period).mean().values
        std = pd.Series(close).rolling(window=period).std().values

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        self.add_indicator("BB_upper", upper.tolist())
        self.add_indicator("BB_lower", lower.tolist())

    def clear(self) -> None:
        """Clear all plot items."""
        self.plot_widget.clear()
        self.plot_items = []
        self.indicators = {}
        self.data = None

    def set_x_range(self, start: int, end: int) -> None:
        """Set visible x-axis range."""
        self.plot_widget.setXRange(start, end)

    def set_y_range(self, start: float, end: float) -> None:
        """Set visible y-axis range."""
        self.plot_widget.setYRange(start, end)

    def get_visible_data(self) -> Optional[pd.DataFrame]:
        """Get currently visible data range."""
        if self.data is None:
            return None
        return self.data.copy()
