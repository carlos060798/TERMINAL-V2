"""
Demonstration of Backtesting Panel functionality.

This example shows how to use the BacktestPanel for running various
investment strategies with historical data using vectorbt.

Run:
    python examples/backtest_panel_demo.py
"""

import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QSize

from quantum_terminal.ui.panels.backtest_panel import (
    BacktestPanel, BacktestConfig, StrategyType, BacktestResults
)


class BacktestDemoWindow(QMainWindow):
    """Demo window for backtesting panel."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Investment Terminal - Backtest Panel Demo")
        self.setGeometry(100, 100, 1600, 900)

        # Create the backtest panel
        self.backtest_panel = BacktestPanel()

        # Connect signals
        self.backtest_panel.backtest_completed.connect(self.on_backtest_complete)
        self.backtest_panel.backtest_error.connect(self.on_backtest_error)

        # Set as central widget
        self.setCentralWidget(self.backtest_panel)

    def on_backtest_complete(self, results: BacktestResults):
        """Handle backtest completion."""
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS - {results.strategy.value}")
        print(f"{'='*60}")
        print(f"Duration:        {results.duration_days} days")
        print(f"Number of Trades: {results.num_trades}")
        print(f"\nRETURNS")
        print(f"Total Return:    {results.total_return:>10.2%}")
        print(f"CAGR:            {results.cagr:>10.2%}")
        print(f"\nRISK")
        print(f"Sharpe Ratio:    {results.sharpe_ratio:>10.2f}")
        print(f"Sortino Ratio:   {results.sortino_ratio:>10.2f}")
        print(f"Max Drawdown:    {results.max_drawdown:>10.2%}")
        print(f"\nTRADE STATS")
        print(f"Win Rate:        {results.win_rate:>10.2%}")
        print(f"Profit Factor:   {results.profit_factor:>10.2f}")
        print(f"{'='*60}\n")

    def on_backtest_error(self, error_msg: str):
        """Handle backtest error."""
        print(f"\nBACKTEST ERROR: {error_msg}\n")


def demo_config():
    """Print example configurations for different strategies."""
    print("\n" + "="*60)
    print("BACKTEST STRATEGIES AVAILABLE")
    print("="*60)

    strategies = [
        ("SMA Crossover", "Buy when SMA(20) > SMA(50), sell when crosses below"),
        ("RSI Mean Reversion", "Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)"),
        ("MACD Momentum", "Buy when MACD > Signal line, sell when crosses below"),
        ("Graham Net-Net", "Buy when price < NNWC (0.7x 200-day MA), sell at fair value"),
        ("Multi-factor", "Combines SMA (bullish trend) + RSI (not weak) + MACD (momentum)")
    ]

    for i, (name, desc) in enumerate(strategies, 1):
        print(f"\n{i}. {name}")
        print(f"   {desc}")

    print("\n" + "="*60)
    print("CONFIGURATION PARAMETERS")
    print("="*60)

    params = {
        "Tickers": "AAPL,MSFT,GOOGL (comma-separated)",
        "Date Range": "Configurable start/end dates (default: 2 years)",
        "Initial Capital": "Dollar amount (default: $100,000)",
        "Position Size": "% of capital per position (default: 10%)",
        "Slippage": "% cost per trade (default: 0.01%)",
        "Commission": "$ per trade (default: $5.00)",
        "SMA Fast": "Short-term MA period (default: 20)",
        "SMA Slow": "Long-term MA period (default: 50)",
        "RSI Period": "RSI lookback period (default: 14)",
        "RSI Oversold": "Oversold threshold (default: 30)",
        "RSI Overbought": "Overbought threshold (default: 70)",
        "MACD Fast": "MACD fast EMA (default: 12)",
        "MACD Slow": "MACD slow EMA (default: 26)",
        "MACD Signal": "MACD signal line EMA (default: 9)"
    }

    for key, value in params.items():
        print(f"  {key:20s} : {value}")

    print("\n" + "="*60)
    print("VISUALIZATION TABS")
    print("="*60)

    tabs = [
        ("Equity Curve", "Portfolio value over time vs S&P 500 benchmark"),
        ("Metrics", "Comprehensive performance statistics"),
        ("Trades", "Trade-by-trade breakdown with P&L"),
        ("Monte Carlo", "1000 random walk simulations of equity curve"),
        ("Returns Distribution", "Histogram of daily returns with normal curve")
    ]

    for tab, desc in tabs:
        print(f"  * {tab:20s} - {desc}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Print configuration guide
    demo_config()

    # Create application
    app = QApplication(sys.argv)
    window = BacktestDemoWindow()
    window.show()

    # Usage instructions
    print("USAGE INSTRUCTIONS:")
    print("-" * 60)
    print("1. Select a strategy from the dropdown")
    print("2. Enter tickers (comma-separated, e.g., AAPL,MSFT)")
    print("3. Set date range (default: 2 years)")
    print("4. Configure capital and position sizing")
    print("5. Adjust slippage and commission")
    print("6. Tune strategy parameters as needed")
    print("7. Click 'Run Backtest' to execute")
    print("8. Review results in the tabs:")
    print("   - Equity Curve: Visual performance vs benchmark")
    print("   - Metrics: Key statistics (Sharpe, Sortino, Win Rate)")
    print("   - Trades: Individual trade analysis")
    print("   - Monte Carlo: Risk assessment via simulation")
    print("   - Returns Distribution: Return profile analysis")
    print("-" * 60 + "\n")

    sys.exit(app.exec())
