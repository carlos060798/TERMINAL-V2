"""
EquityCurveWidget: Equity curve and drawdown visualization using pyqtgraph.

Features: Animated equity curve, drawdown band, performance metrics overlay.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from datetime import datetime


class EquityCurveWidget(QWidget):
    """Interactive equity curve and drawdown visualization."""

    def __init__(self, title: str = "Equity Curve"):
        """
        Initialize EquityCurveWidget.

        Args:
            title: Widget title
        """
        super().__init__()
        self.title = title
        self.equity_data: Optional[np.ndarray] = None
        self.drawdown_data: Optional[np.ndarray] = None

        self.initUI()

    def initUI(self) -> None:
        """Build equity curve UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget with two y-axes
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle(self.title, size="12pt")
        self.plot_widget.setLabel("left", "Equity", units="$")
        self.plot_widget.setLabel("bottom", "Days")
        self.plot_widget.setBackground("#1E1E1E")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)

        # Style axes
        self.plot_widget.getAxis("left").setPen(pg.mkPen("#A0A0A0"))
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen("#A0A0A0"))

        # Secondary axis for drawdown
        self.right_axis = pg.AxisItem(orientation="right")
        self.right_axis.setPen(pg.mkPen("#FF3B30"))
        self.right_axis.setLabel("Max Drawdown", units="%")
        self.plot_widget.plotItem.scene().addItem(self.right_axis)

        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def plot_equity(self, equity: List[float], starting_capital: float = 100000) -> None:
        """
        Plot equity curve.

        Args:
            equity: List of equity values over time
            starting_capital: Initial investment (for reference line)
        """
        if not equity or len(equity) == 0:
            return

        self.equity_data = np.array(equity)
        x_vals = np.arange(len(equity))

        self.plot_widget.clear()

        # Reference line (starting capital)
        ref_line = self.plot_widget.plot(
            x_vals,
            [starting_capital] * len(equity),
            pen=pg.mkPen("#A0A0A0", width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            name="Starting Capital",
        )

        # Equity curve (main)
        equity_curve = self.plot_widget.plot(
            x_vals,
            self.equity_data,
            pen=pg.mkPen("#00D26A", width=2),
            name="Equity",
        )

        # Fill area under curve
        fill = pg.FillBetweenItem(
            x=x_vals,
            y1=self.equity_data,
            y2=[starting_capital] * len(equity),
            brush=pg.mkBrush("#00D26A", alpha=50),
        )
        self.plot_widget.addItem(fill)

    def plot_drawdown(self, equity: List[float]) -> None:
        """
        Plot drawdown band (secondary axis).

        Args:
            equity: Equity curve values
        """
        if not equity or len(equity) < 2:
            return

        # Calculate running maximum and drawdown
        equity_arr = np.array(equity)
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max * 100

        self.drawdown_data = drawdown
        x_vals = np.arange(len(drawdown))

        # Plot drawdown as area fill (in red)
        dd_curve = pg.PlotCurveItem(
            x_vals, drawdown, pen=pg.mkPen("#FF3B30", width=1)
        )

        # Create secondary viewbox for drawdown
        view_box2 = pg.ViewBox()
        self.plot_widget.plotItem.scene().addItem(view_box2)
        self.right_axis.linkToView(view_box2)
        view_box2.setXLink(self.plot_widget.plotItem)

        view_box2.addItem(dd_curve)
        view_box2.setYRange(min(drawdown), 0)

    def plot_both(self, equity: List[float], starting_capital: float = 100000) -> None:
        """
        Plot equity curve and drawdown together.

        Args:
            equity: Equity values over time
            starting_capital: Initial capital for reference
        """
        self.plot_equity(equity, starting_capital)
        self.plot_drawdown(equity)

    def add_annotation(self, x: int, y: float, text: str, color: str = "#FFFFFF") -> None:
        """
        Add text annotation to chart.

        Args:
            x: X position
            y: Y position (equity value)
            text: Annotation text
            color: Text color
        """
        text_item = pg.TextItem(text, anchor=(0, 1))
        text_item.setPos(x, y)
        text_item.setColor(color)
        self.plot_widget.addItem(text_item)

    def add_performance_metrics(self, metrics: dict) -> None:
        """
        Add performance metrics as text overlay.

        Args:
            metrics: Dict with keys: total_return, sharpe_ratio, max_drawdown, win_rate
        """
        metric_text = f"""
        Return: {metrics.get('total_return', 0):+.2f}%
        Sharpe: {metrics.get('sharpe_ratio', 0):.2f}
        Max DD: {metrics.get('max_drawdown', 0):.2f}%
        Win Rate: {metrics.get('win_rate', 0):.1f}%
        """

        text_item = pg.TextItem(metric_text)
        text_item.setPos(0, max(self.equity_data) if self.equity_data is not None else 0)
        text_item.setColor("#00D26A")
        text_item.setFont(pg.mkFont("JetBrains Mono", 10))
        self.plot_widget.addItem(text_item)

    def set_x_range(self, start: int, end: int) -> None:
        """Set visible x-axis range."""
        self.plot_widget.setXRange(start, end)

    def set_y_range(self, start: float, end: float) -> None:
        """Set visible y-axis range."""
        self.plot_widget.setYRange(start, end)

    def clear(self) -> None:
        """Clear all plot items."""
        self.plot_widget.clear()
        self.equity_data = None
        self.drawdown_data = None

    def get_statistics(self, equity: List[float]) -> dict:
        """
        Calculate portfolio statistics.

        Args:
            equity: Equity curve

        Returns:
            Dict with statistics
        """
        equity_arr = np.array(equity)
        returns = np.diff(equity_arr) / equity_arr[:-1]

        total_return = (equity_arr[-1] - equity_arr[0]) / equity_arr[0] * 100
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max
        max_drawdown = np.min(drawdown) * 100

        win_rate = (np.sum(returns > 0) / len(returns) * 100) if len(returns) > 0 else 0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "avg_return": np.mean(returns) * 100,
            "volatility": np.std(returns) * np.sqrt(252) * 100,
        }
