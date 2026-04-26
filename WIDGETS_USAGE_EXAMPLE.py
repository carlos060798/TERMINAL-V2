"""
Example usage of Quantum Terminal UI widgets.

This file demonstrates how to use each widget in a real application.
"""

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import all widgets
from quantum_terminal.ui.widgets import (
    MetricCard,
    ChartWidget,
    DataTable,
    TickerSearch,
    AlertBanner,
    AIChatWidget,
    HeatmapWidget,
    EquityCurveWidget,
)


class WidgetDemoWindow(QMainWindow):
    """Demo window showing all widget usage."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Terminal - Widget Demo")
        self.setGeometry(100, 100, 1400, 900)

        self._init_widgets()
        self._setup_layout()

    def _init_widgets(self):
        """Initialize all widgets."""
        # 1. MetricCard example
        self.metric_card = MetricCard(title="Sharpe Ratio", unit="pts")
        self.metric_card.set_value(1.85, animate=False)
        self.metric_card.set_change(0.15, absolute=0.15)

        # 2. ChartWidget example
        self.chart = ChartWidget(title="AAPL Daily")
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        ohlcv_data = pd.DataFrame({
            "open": np.random.uniform(150, 160, 30),
            "high": np.random.uniform(160, 165, 30),
            "low": np.random.uniform(145, 155, 30),
            "close": np.random.uniform(150, 160, 30),
            "volume": np.random.randint(50000000, 100000000, 30),
        }, index=dates)
        self.chart.plot_candlestick(ohlcv_data)
        self.chart.add_moving_average(period=10, ma_type="SMA")

        # 3. DataTable example
        self.table = DataTable(columns=["Ticker", "Price", "Change %", "Volume"])
        table_data = [
            {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 85000000},
            {"Ticker": "MSFT", "Price": 420.25, "Change %": 1.2, "Volume": 25000000},
            {"Ticker": "GOOGL", "Price": 140.00, "Change %": -0.8, "Volume": 30000000},
            {"Ticker": "AMZN", "Price": 180.75, "Change %": 3.1, "Volume": 55000000},
        ]
        self.table.set_data(table_data)

        # 4. TickerSearch example
        tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "META", "NVDA", "NFLX", "JPM", "BAC",
        ]
        self.ticker_search = TickerSearch(tickers=tickers)
        self.ticker_search.ticker_selected.connect(self._on_ticker_selected)

        # 5. AlertBanner example
        self.alert = AlertBanner()

        # 6. AIChatWidget example
        self.chat = AIChatWidget()
        self.chat.add_message("assistant", "Hi! I'm your AI assistant. Ask me about portfolio analysis.")
        self.chat.add_message("user", "What's the Sharpe ratio of my portfolio?")
        self.chat.add_message("assistant", "Based on your holdings, your Sharpe ratio is 1.85, indicating good risk-adjusted returns.")

        # 7. HeatmapWidget example
        self.heatmap = HeatmapWidget(title="Sector Performance")
        sector_data = {
            "Technology": 5.2,
            "Healthcare": 1.8,
            "Financials": -0.5,
            "Energy": 3.1,
            "Utilities": -1.2,
        }
        self.heatmap.plot_sector_heatmap(sector_data)

        # 8. EquityCurveWidget example
        self.equity_curve = EquityCurveWidget(title="Portfolio Equity")
        equity = [100000 + i * np.sin(i/10) * 5000 for i in range(100)]
        self.equity_curve.plot_both(equity, starting_capital=100000)

    def _setup_layout(self):
        """Setup main layout with all widgets."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Top: Alert banner
        main_layout.addWidget(self.alert)

        # First row: Metric cards + Chart
        top_row = QHBoxLayout()
        top_row.addWidget(self.metric_card)
        top_row.addWidget(self.chart, 3)
        main_layout.addLayout(top_row)

        # Second row: Table
        main_layout.addWidget(self.table)

        # Third row: Search + Heatmap + Equity
        bottom_row = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(self.ticker_search)
        left_col.addWidget(self.chat, 2)
        bottom_row.addLayout(left_col)
        bottom_row.addWidget(self.heatmap, 2)
        bottom_row.addWidget(self.equity_curve, 2)
        main_layout.addLayout(bottom_row)

        central_widget.setLayout(main_layout)

    def _on_ticker_selected(self, ticker: str):
        """Handle ticker selection."""
        self.alert.show_alert(
            f"Selected: {ticker}",
            level="success",
            duration_ms=3000
        )
        # Update chart, table, etc. here


def main():
    """Run demo."""
    app = QApplication([])

    # Create and show window
    window = WidgetDemoWindow()
    window.show()

    # Show welcome alert
    window.alert.show_alert(
        "Welcome to Quantum Terminal Widget Demo!",
        level="info",
        duration_ms=5000
    )

    app.exec()


if __name__ == "__main__":
    main()
