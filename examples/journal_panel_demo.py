"""
Demonstration of Trading Journal Panel usage.

This example shows how to:
1. Create and integrate the panel
2. Add trades manually
3. Monitor statistics
4. Generate postmortem analysis
"""

import sys
import asyncio
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import pyqtSlot

# Import the panel
from quantum_terminal.ui.panels.journal_panel import TradingJournalPanel


class DemoWindow(QMainWindow):
    """Demo window with Trading Journal Panel."""

    def __init__(self):
        """Initialize demo window."""
        super().__init__()
        self.setWindowTitle("Trading Journal Panel Demo")
        self.setGeometry(100, 100, 1400, 900)

        # Create main widget
        main_widget = QWidget()
        layout = QVBoxLayout()

        # Create journal panel
        self.journal_panel = TradingJournalPanel()

        # Connect signals
        self.journal_panel.trade_added.connect(self.on_trade_added)
        self.journal_panel.trade_closed.connect(self.on_trade_closed)

        layout.addWidget(self.journal_panel)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    @pyqtSlot(dict)
    def on_trade_added(self, trade_data):
        """Handle trade added signal."""
        print(f"[EVENT] Trade added: {trade_data.get('ticker')} {trade_data.get('direction')}")

    @pyqtSlot(str)
    def on_trade_closed(self, trade_id):
        """Handle trade closed signal."""
        print(f"[EVENT] Trade closed: {trade_id}")

    def add_sample_trades(self):
        """Add sample trades for demonstration."""
        now = datetime.now()

        sample_trades = [
            {
                "trade_id": "DEMO_001",
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 150.0,
                "exit_price": 155.0,
                "stop_loss": 145.0,
                "take_profit": 160.0,
                "reason": "Bullish breakout on 1h chart, above 50MA",
                "plan_adherence": True,
                "entry_date": (now - timedelta(days=5)).isoformat(),
                "exit_date": (now - timedelta(days=4)).isoformat(),
                "status": "closed",
            },
            {
                "trade_id": "DEMO_002",
                "ticker": "MSFT",
                "direction": "Long",
                "size": 50.0,
                "entry_price": 300.0,
                "exit_price": 295.0,
                "stop_loss": 295.0,
                "take_profit": 310.0,
                "reason": "Support at 200MA, RR 1:2",
                "plan_adherence": True,
                "entry_date": (now - timedelta(days=3)).isoformat(),
                "exit_date": (now - timedelta(days=2)).isoformat(),
                "status": "closed",
            },
            {
                "trade_id": "DEMO_003",
                "ticker": "GOOG",
                "direction": "Long",
                "size": 75.0,
                "entry_price": 2800.0,
                "exit_price": 2850.0,
                "stop_loss": 2750.0,
                "take_profit": 2900.0,
                "reason": "Channel breakout, volume spike",
                "plan_adherence": True,
                "entry_date": (now - timedelta(days=2)).isoformat(),
                "exit_date": (now - timedelta(days=1)).isoformat(),
                "status": "closed",
            },
            {
                "trade_id": "DEMO_004",
                "ticker": "TSLA",
                "direction": "Short",
                "size": 50.0,
                "entry_price": 250.0,
                "exit_price": 245.0,
                "stop_loss": 260.0,
                "take_profit": 230.0,
                "reason": "Overbought on 4h, resistance at 250",
                "plan_adherence": True,
                "entry_date": (now - timedelta(days=1)).isoformat(),
                "exit_date": now.isoformat(),
                "status": "closed",
            },
            {
                "trade_id": "DEMO_005",
                "ticker": "SPY",
                "direction": "Long",
                "size": 200.0,
                "entry_price": 420.0,
                "exit_price": None,
                "stop_loss": 415.0,
                "take_profit": 430.0,
                "reason": "Index oversold, retesting support",
                "plan_adherence": True,
                "entry_date": now.isoformat(),
                "status": "open",
                "current_price": 421.5,
            },
        ]

        for trade in sample_trades:
            self.journal_panel.trades[trade["trade_id"]] = trade
            self.journal_panel.add_trade_to_table(trade)

        print(f"[DEMO] Added {len(sample_trades)} sample trades")

        # Update statistics
        asyncio.create_task(self.journal_panel.update_statistics())


def main():
    """Run demo application."""
    app = QApplication(sys.argv)

    # Create and show window
    window = DemoWindow()
    window.show()

    # Add sample trades
    window.add_sample_trades()

    print("\n" + "=" * 60)
    print("Trading Journal Panel Demo")
    print("=" * 60)
    print("\nPanel features:")
    print("1. Add Trade: Click '+ Add Trade' to open dialog")
    print("2. Open Trades Table: Shows all active positions")
    print("3. Statistics: Win Rate, Profit Factor, Expectancy, etc.")
    print("4. Equity Curve: Cumulative P&L chart")
    print("5. Plan Adherence: % of trades following plan")
    print("6. Postmortem: AI analysis of weekly trades")
    print("\nSample trades have been added for demonstration.")
    print("=" * 60 + "\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
