# Trading Journal Panel - Main Window Integration Guide

## Quick Integration (Copy & Paste Ready)

Para agregar el Trading Journal Panel a la ventana principal, sigue estos pasos:

### Step 1: Import en main_window.py

```python
from quantum_terminal.ui.panels import (
    DashboardPanel,
    WatchlistPanel, 
    AnalyzerPanel,
    TradingJournalPanel,  # ADD THIS LINE
)
```

### Step 2: Crear instancia en __init__

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ... existing code ...
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Create panels
        self.dashboard = DashboardPanel()
        self.watchlist = WatchlistPanel()
        self.analyzer = AnalyzerPanel()
        self.journal = TradingJournalPanel()  # ADD THIS LINE
        
        # Add to tabs
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.watchlist, "Watchlist")
        self.tabs.addTab(self.analyzer, "Analyzer")
        self.tabs.addTab(self.journal, "Trading Journal")  # ADD THIS LINE
        
        self.setCentralWidget(self.tabs)
        
        # Connect signals
        self._connect_signals()
```

### Step 3: Conectar Signals

```python
def _connect_signals(self):
    """Connect inter-panel signals."""
    
    # ... existing connections ...
    
    # Trading Journal signals
    self.journal.trade_added.connect(self.on_trade_added)
    self.journal.trade_closed.connect(self.on_trade_closed)

@pyqtSlot(dict)
def on_trade_added(self, trade_data):
    """Handle trade added from journal panel."""
    logger.info(f"Trade added: {trade_data['ticker']} {trade_data['direction']}")
    
    # Optional: Sync with other panels
    if trade_data['ticker'] in self.watchlist.get_tickers():
        self.watchlist.highlight_trade(trade_data['ticker'])

@pyqtSlot(str)
def on_trade_closed(self, trade_id):
    """Handle trade closed from journal panel."""
    logger.info(f"Trade closed: {trade_id}")
    
    # Optional: Update dashboard with new stats
    self.update_dashboard_stats()
```

## Complete Example

```python
# quantum_terminal/ui/main_window.py

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QToolBar, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSlot

from quantum_terminal.ui.panels import (
    DashboardPanel,
    WatchlistPanel,
    AnalyzerPanel,
    TradingJournalPanel,
)
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window with all panels."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Investment Terminal")
        self.setGeometry(0, 0, 1600, 1000)

        # Create tab widget
        self.tabs = QTabWidget()

        # Create panels
        self.dashboard = DashboardPanel()
        self.watchlist = WatchlistPanel()
        self.analyzer = AnalyzerPanel()
        self.journal = TradingJournalPanel()  # Trading Journal

        # Add tabs
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.watchlist, "Watchlist")
        self.tabs.addTab(self.analyzer, "Analyzer")
        self.tabs.addTab(self.journal, "Trading Journal")

        # Set central widget
        self.setCentralWidget(self.tabs)

        # Create menu bar
        self._create_menu_bar()

        # Create toolbar
        self._create_toolbar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Connect signals
        self._connect_signals()

    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Export Journal...", self.export_journal)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Settings...", self.open_settings)
        tools_menu.addAction("Backtest...", self.open_backtest)

        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Documentation", self.open_docs)
        help_menu.addAction("About", self.open_about)

    def _create_toolbar(self):
        """Create toolbar with quick actions."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Add buttons
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_all)
        toolbar.addWidget(refresh_btn)

        toolbar.addSeparator()

        add_trade_btn = QPushButton("+ Add Trade")
        add_trade_btn.clicked.connect(self.journal.open_add_trade_dialog)
        toolbar.addWidget(add_trade_btn)

        toolbar.addStretch()

        # Status indicator
        status_label = QPushButton("Online")
        status_label.setStyleSheet("background-color: green; color: white;")
        toolbar.addWidget(status_label)

    def _connect_signals(self):
        """Connect inter-panel signals."""
        # Trading Journal signals
        self.journal.trade_added.connect(self.on_trade_added)
        self.journal.trade_closed.connect(self.on_trade_closed)

        # Dashboard signals
        self.dashboard.sector_clicked.connect(self.on_sector_clicked)

        # Watchlist signals
        self.watchlist.stock_selected.connect(self.on_stock_selected)

    @pyqtSlot(dict)
    def on_trade_added(self, trade_data):
        """Handle trade added from journal."""
        logger.info(f"Trade added: {trade_data['ticker']} {trade_data['direction']}")
        
        # Update status bar
        self.status_bar.showMessage(
            f"Trade added: {trade_data['ticker']} @ ${trade_data['entry_price']}"
        )
        
        # Sync with watchlist if exists
        if hasattr(self.watchlist, 'add_to_watchlist'):
            self.watchlist.add_to_watchlist(trade_data['ticker'])

    @pyqtSlot(str)
    def on_trade_closed(self, trade_id):
        """Handle trade closed from journal."""
        logger.info(f"Trade closed: {trade_id}")
        self.status_bar.showMessage("Trade closed")

    @pyqtSlot(str)
    def on_sector_clicked(self, sector):
        """Handle sector click from dashboard."""
        self.tabs.setCurrentWidget(self.watchlist)
        self.watchlist.filter_by_sector(sector)

    @pyqtSlot(str)
    def on_stock_selected(self, ticker):
        """Handle stock selection from watchlist."""
        self.tabs.setCurrentWidget(self.analyzer)
        self.analyzer.analyze_stock(ticker)

    def refresh_all(self):
        """Refresh all panels."""
        self.dashboard.refresh()
        self.watchlist.refresh()
        self.analyzer.refresh()

    def export_journal(self):
        """Export trading journal to CSV."""
        # TODO: Implement export functionality
        pass

    def open_settings(self):
        """Open settings dialog."""
        # TODO: Implement settings
        pass

    def open_backtest(self):
        """Open backtest tool."""
        # TODO: Implement backtest
        pass

    def open_docs(self):
        """Open documentation."""
        # TODO: Open docs
        pass

    def open_about(self):
        """Show about dialog."""
        # TODO: Show about dialog
        pass


def main():
    """Run the application."""
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## Panel Communication Flow

```
MainWindow
├── Dashboard Panel
│   └── sector_clicked → MainWindow → Watchlist.filter_by_sector()
│
├── Watchlist Panel  
│   └── stock_selected → MainWindow → Analyzer.analyze_stock()
│
├── Analyzer Panel
│   └── (analysis results)
│
└── Trading Journal Panel ✓ NEW
    ├── trade_added → MainWindow → Watchlist.highlight()
    └── trade_closed → MainWindow → refresh_stats()
```

## API Reference

### TradingJournalPanel Public Methods

```python
# Dialog Management
panel.open_add_trade_dialog() -> None
"""Open dialog to add new trade."""

# Data Management
panel.add_trade_to_table(trade: Dict) -> None
"""Add trade row to table."""

panel.delete_trade(trade_id: str) -> None
"""Delete a trade."""

# Updates
panel.update_open_trades() -> None
"""Update prices for open trades (called every 5 sec)."""

panel.update_statistics() -> None
"""Recalculate all statistics (async)."""

panel.update_equity_curve(trades: List[Dict]) -> None
"""Update equity curve chart."""

# Analysis
panel.generate_postmortem() -> None
"""Generate weekly AI analysis (async)."""

# Utilities
panel.load_trades() -> None
"""Load trades from database."""

# Events
panel.show_trade_context_menu(pos) -> None
"""Show context menu for trade row."""
```

### Signals

```python
# Connect to these signals:
panel.trade_added.connect(callback)
"""Emitted when trade added. Payload: Dict with trade data."""

panel.trade_closed.connect(callback)
"""Emitted when trade closed. Payload: str (trade_id)."""
```

## Configuration

### Settings in config.py

```python
# Add to quantum_terminal/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Trading Journal settings
    JOURNAL_UPDATE_INTERVAL_SEC: int = 5  # Update prices every 5 sec
    JOURNAL_EQUITY_HISTORY_DAYS: int = 365  # Show 1 year history
    JOURNAL_POSTMORTEM_ENABLED: bool = True  # Enable AI analysis
    JOURNAL_AUTO_BACKUP: bool = True  # Auto backup trades
    
    class Config:
        env_file = ".env"
```

## Error Handling

El panel maneja automáticamente:
- API failures (fallback chains)
- Invalid prices (validation)
- Database errors (logging)
- AI unavailability (graceful degradation)

```python
# Example error handling
try:
    panel.update_open_trades()
except Exception as e:
    logger.error(f"Failed to update trades: {e}")
    panel.status_bar.showMessage("Update failed - check logs")
```

## Performance Tips

1. **Limit trade history**: Only show last N trades
2. **Defer calculations**: Use threading for stats
3. **Cache equity curve**: Recalculate on close only
4. **Batch API calls**: Fetch quotes for multiple tickers at once

```python
# Example: Limit table to last 50 trades
self.trades_table.setMaximumHeight(250)  # Fixed height with scroll
self.trades = {k: v for k, v in list(self.trades.items())[-50:]}
```

## Next Steps

After integration:

1. **Test in MainWindow**
   ```bash
   python main.py
   # Navigate to Trading Journal tab
   # Add sample trades
   # Verify statistics update
   ```

2. **Connect Database**
   - Implement trades_repo for persistence
   - Use SQLAlchemy ORM
   - Run migrations

3. **Add Export Feature**
   - Export to CSV/Excel
   - Generate PDF reports
   - Email summaries

4. **Extend with Real Data**
   - Connect to real broker API
   - Sync orders with trades
   - Real-time P&L updates

## Troubleshooting

### Panel doesn't update prices
- Check DataProvider is initialized
- Verify API keys in .env
- Check console logs for errors

### Statistics are zero
- Verify trades have exit_price
- Check TradeStatisticsUseCase is imported
- Ensure trades list is not empty

### Postmortem not working
- Check GROQ_API_KEY is set
- Verify AIGateway is initialized
- Check network connectivity

### UI freezes
- Ensure async operations use threads
- Check DataLoaderThread is running
- Verify no blocking calls in main thread

## Support

For issues or questions:
1. Check JOURNAL_PANEL_INTEGRATION.md for detailed docs
2. Review test cases for examples
3. Check debug logs: `logging.getLogger('quantum_terminal').setLevel(logging.DEBUG)`
4. Run demo: `python examples/journal_panel_demo.py`
