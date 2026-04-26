"""
Watchlist Panel - Live ticker data with real-time updates.

Features:
- Table with Ticker, Price, Daily %, Score, MoS, P/E, Graham IV
- Batch updates every 60 seconds
- Finnhub WebSocket for live price updates
- Right-click context menu: Analyze, Add Alert, Remove
- Search bar with autocomplete
- Sub-tabs: Technical, Dividends, Fundamentals

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, List, Dict
from decimal import Decimal
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QHeaderView, QMenu,
    QMessageBox, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor, QIcon, QBrush
from PyQt6.QtCore import QSize

from quantum_terminal.ui.widgets import TickerSearch, DataTable
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class WatchlistPanel(QWidget):
    """
    Watchlist panel showing live stock data with real-time updates.

    Signals:
        - ticker_double_clicked: Emitted when user double-clicks a ticker
        - ticker_added: Emitted when a ticker is added
        - ticker_removed: Emitted when a ticker is removed
        - alert_requested: Emitted when user requests to add an alert
    """

    ticker_double_clicked = pyqtSignal(str)  # ticker
    ticker_added = pyqtSignal(str)  # ticker
    ticker_removed = pyqtSignal(str)  # ticker
    alert_requested = pyqtSignal(str)  # ticker

    def __init__(self, parent=None):
        """Initialize the watchlist panel."""
        super().__init__(parent)
        self.watchlist = []
        self.batch_update_timer = QTimer()
        self.batch_update_timer.timeout.connect(self._on_batch_update)
        self.initUI()
        self.setup_connections()

    def initUI(self):
        """Build the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title bar
        title_layout = self._build_title_bar()
        main_layout.addLayout(title_layout)

        # Search/Add section
        search_layout = self._build_search_section()
        main_layout.addLayout(search_layout)

        # Main content: Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 1: Watchlist table
        self.watchlist_table = self._build_watchlist_table()
        self.tabs.addTab(self.watchlist_table, "Watchlist")

        # Tab 2: Technical indicators
        self.technical_tab = self._build_technical_tab()
        self.tabs.addTab(self.technical_tab, "Technical")

        # Tab 3: Dividends
        self.dividends_tab = self._build_dividends_tab()
        self.tabs.addTab(self.dividends_tab, "Dividends")

        # Tab 4: Fundamentals
        self.fundamentals_tab = self._build_fundamentals_tab()
        self.tabs.addTab(self.fundamentals_tab, "Fundamentals")

        main_layout.addWidget(self.tabs)

        # Status bar
        status_layout = self._build_status_bar()
        main_layout.addLayout(status_layout)

        self.setLayout(main_layout)

    def _build_title_bar(self) -> QHBoxLayout:
        """Build title bar."""
        layout = QHBoxLayout()

        title = QLabel("Watchlist")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addSpacing(10)

        # Status indicator
        self.status_label = QLabel("● Live")
        self.status_label.setStyleSheet("color: #00cc00; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Watchlist count
        self.count_label = QLabel("0 tickers")
        layout.addWidget(self.count_label)

        return layout

    def _build_search_section(self) -> QHBoxLayout:
        """Build search and add section."""
        layout = QHBoxLayout()

        # Ticker search with autocomplete
        self.ticker_search = TickerSearch()
        self.ticker_search.search_requested.connect(self._on_search_requested)
        layout.addWidget(QLabel("Search ticker:"))
        layout.addWidget(self.ticker_search)

        # Quick add button
        add_btn = QPushButton("+ Add")
        add_btn.setMaximumWidth(80)
        add_btn.clicked.connect(self._on_add_ticker_clicked)
        layout.addWidget(add_btn)

        layout.addStretch()

        # Filter buttons
        filter_label = QLabel("Filter:")
        layout.addWidget(filter_label)

        for sector in ["All", "Tech", "Finance", "Healthcare"]:
            btn = QPushButton(sector)
            btn.setMaximumWidth(70)
            btn.setCheckable(True)
            if sector == "All":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=sector: self._on_sector_filter(s))
            layout.addWidget(btn)

        return layout

    def _build_watchlist_table(self) -> QWidget:
        """Build main watchlist table."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Table: Ticker | Price | Δ% | Quality Score | MoS % | P/E | Graham IV
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Ticker", "Price", "Δ Today %", "Quality", "MoS %",
            "P/E", "Graham IV", "Action"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #444;
                gridline-color: #333;
                background-color: #1a1a1a;
            }
            QTableWidget::item {
                padding: 4px;
                border-right: 1px solid #333;
            }
            QTableWidget::item:selected {
                background-color: #1e90ff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #fff;
                padding: 4px;
                border: 1px solid #444;
            }
        """)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        self.table.doubleClicked.connect(self._on_table_double_clicked)

        layout.addWidget(self.table)
        return container

    def _build_technical_tab(self) -> QWidget:
        """Build technical indicators tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Technical Indicators (RSI, MACD, Bollinger Bands)"))
        # TODO: Add technical indicator charts
        layout.addStretch()
        return container

    def _build_dividends_tab(self) -> QWidget:
        """Build dividends tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Dividend History and Yield"))
        # TODO: Add dividend yield chart and history table
        layout.addStretch()
        return container

    def _build_fundamentals_tab(self) -> QWidget:
        """Build fundamentals tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Fundamental Metrics"))
        # TODO: Add fundamental metrics comparison
        layout.addStretch()
        return container

    def _build_status_bar(self) -> QHBoxLayout:
        """Build status bar with update info."""
        layout = QHBoxLayout()

        self.last_update_label = QLabel("Last update: --")
        layout.addWidget(self.last_update_label)

        layout.addSpacing(20)

        # Auto-update toggle
        self.auto_update_btn = QPushButton("Auto-update: ON")
        self.auto_update_btn.setMaximumWidth(120)
        self.auto_update_btn.setCheckable(True)
        self.auto_update_btn.setChecked(True)
        self.auto_update_btn.clicked.connect(self._on_auto_update_toggled)
        layout.addWidget(self.auto_update_btn)

        layout.addStretch()

        # Refresh now button
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_btn)

        return layout

    def add_ticker(self, ticker: str) -> bool:
        """
        Add a ticker to the watchlist.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if added, False if already exists
        """
        ticker = ticker.upper()
        if ticker in self.watchlist:
            logger.warning(f"Ticker {ticker} already in watchlist")
            return False

        try:
            self.watchlist.append(ticker)
            self._add_table_row(ticker)
            self._update_count()
            self.ticker_added.emit(ticker)
            logger.info(f"Ticker {ticker} added to watchlist")
            return True
        except Exception as e:
            logger.error(f"Failed to add ticker {ticker}: {e}", exc_info=True)
            return False

    def remove_ticker(self, ticker: str) -> bool:
        """
        Remove a ticker from the watchlist.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if removed, False if not found
        """
        ticker = ticker.upper()
        if ticker not in self.watchlist:
            logger.warning(f"Ticker {ticker} not in watchlist")
            return False

        try:
            self.watchlist.remove(ticker)
            self._remove_table_row(ticker)
            self._update_count()
            self.ticker_removed.emit(ticker)
            logger.info(f"Ticker {ticker} removed from watchlist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove ticker {ticker}: {e}", exc_info=True)
            return False

    def batch_update(self) -> None:
        """
        Batch update all tickers (called every 60 seconds).

        Note:
            In Phase 3, this calls async infrastructure methods.
            For MVP, uses mock data.
        """
        try:
            if not self.watchlist:
                return

            logger.info(f"Batch updating {len(self.watchlist)} tickers")

            # TODO: Replace with actual async infrastructure call
            # quotes = await get_quotes_batch(self.watchlist)
            quotes = self._get_mock_quotes(self.watchlist)

            for ticker, data in quotes.items():
                self._update_table_row(ticker, data)

            self._update_last_update_time()

        except Exception as e:
            logger.error(f"Batch update failed: {e}", exc_info=True)

    def _on_batch_update(self):
        """Timer callback for batch updates."""
        self.batch_update()

    def _on_auto_update_toggled(self, checked: bool):
        """Handle auto-update toggle."""
        if checked:
            self.start_batch_updates()
            self.auto_update_btn.setText("Auto-update: ON")
        else:
            self.stop_batch_updates()
            self.auto_update_btn.setText("Auto-update: OFF")

    def _on_refresh_clicked(self):
        """Handle manual refresh button."""
        self.batch_update()

    def _on_search_requested(self, ticker: str):
        """Handle search request."""
        if ticker:
            self.add_ticker(ticker)

    def _on_add_ticker_clicked(self):
        """Handle add button click."""
        ticker = self.ticker_search.get_current_ticker()
        if ticker:
            self.add_ticker(ticker)

    def _on_sector_filter(self, sector: str):
        """Handle sector filter button."""
        logger.info(f"Sector filter: {sector}")
        # TODO: Filter table by sector

    def _on_table_context_menu(self, position):
        """Handle right-click context menu."""
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        ticker = self.table.item(row, 0).text()

        menu = QMenu()
        analyze_action = menu.addAction("Analyze")
        add_alert_action = menu.addAction("Add Price Alert")
        menu.addSeparator()
        remove_action = menu.addAction("Remove")

        action = menu.exec(self.table.mapToGlobal(position))

        if action == analyze_action:
            self.ticker_double_clicked.emit(ticker)
        elif action == add_alert_action:
            self.alert_requested.emit(ticker)
        elif action == remove_action:
            self.remove_ticker(ticker)

    def _on_table_double_clicked(self, index):
        """Handle double-click on table row."""
        row = index.row()
        ticker = self.table.item(row, 0).text()
        self.ticker_double_clicked.emit(ticker)

    def _add_table_row(self, ticker: str) -> None:
        """Add a new row to the table."""
        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)

        # Populate with mock data
        data = self._get_mock_quote_data(ticker)

        items = [
            ticker,
            data["price"],
            data["change_pct"],
            data["quality_score"],
            data["mos_pct"],
            data["pe_ratio"],
            data["graham_iv"],
            "→"
        ]

        for col, value in enumerate(items):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Color code change_pct
            if col == 2:
                try:
                    pct = float(value.rstrip("%"))
                    if pct > 0:
                        item.setForeground(QBrush(QColor("#00cc00")))
                    elif pct < 0:
                        item.setForeground(QBrush(QColor("#ff3333")))
                except:
                    pass

            self.table.setItem(row_pos, col, item)

    def _remove_table_row(self, ticker: str) -> None:
        """Remove a row from the table."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == ticker:
                self.table.removeRow(row)
                break

    def _update_table_row(self, ticker: str, data: Dict) -> None:
        """Update an existing table row."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == ticker:
                # Update price and changes
                self.table.item(row, 1).setText(data.get("price", "N/A"))
                change_pct = data.get("change_pct", "0.00%")
                self.table.item(row, 2).setText(change_pct)

                # Color code
                try:
                    pct = float(change_pct.rstrip("%"))
                    color = QColor("#00cc00") if pct > 0 else QColor("#ff3333")
                    self.table.item(row, 2).setForeground(QBrush(color))
                except:
                    pass

                break

    def _update_count(self):
        """Update ticker count label."""
        count = len(self.watchlist)
        self.count_label.setText(f"{count} ticker{'s' if count != 1 else ''}")

    def _update_last_update_time(self):
        """Update last update timestamp."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_update_label.setText(f"Last update: {timestamp}")

    def start_batch_updates(self, interval_seconds: int = 60) -> None:
        """
        Start batch update timer.

        Args:
            interval_seconds: Update interval in seconds
        """
        self.batch_update_timer.setInterval(interval_seconds * 1000)
        self.batch_update_timer.start()
        logger.info(f"Batch updates started (interval: {interval_seconds}s)")

    def stop_batch_updates(self) -> None:
        """Stop batch update timer."""
        self.batch_update_timer.stop()
        logger.info("Batch updates stopped")

    def setup_connections(self):
        """Set up signal/slot connections."""
        pass

    @staticmethod
    def _get_mock_quotes(tickers: List[str]) -> Dict:
        """
        Return mock quote data for MVP.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with quote data
        """
        quotes = {}
        for ticker in tickers:
            quotes[ticker] = WatchlistPanel._get_mock_quote_data(ticker)
        return quotes

    @staticmethod
    def _get_mock_quote_data(ticker: str) -> Dict:
        """Get mock quote data for a single ticker."""
        mock_data = {
            "AAPL": {
                "price": "$195.42",
                "change_pct": "+2.34%",
                "quality_score": "85",
                "mos_pct": "18%",
                "pe_ratio": "28.5",
                "graham_iv": "$220.50",
            },
            "MSFT": {
                "price": "$417.89",
                "change_pct": "+1.12%",
                "quality_score": "82",
                "mos_pct": "12%",
                "pe_ratio": "32.1",
                "graham_iv": "$480.25",
            },
            "GOOGL": {
                "price": "$156.23",
                "change_pct": "-0.89%",
                "quality_score": "78",
                "mos_pct": "8%",
                "pe_ratio": "24.5",
                "graham_iv": "$180.50",
            },
            "AMZN": {
                "price": "$184.15",
                "change_pct": "+3.21%",
                "quality_score": "76",
                "mos_pct": "15%",
                "pe_ratio": "52.3",
                "graham_iv": "$210.75",
            },
            "TSLA": {
                "price": "$242.84",
                "change_pct": "+5.67%",
                "quality_score": "62",
                "mos_pct": "25%",
                "pe_ratio": "68.9",
                "graham_iv": "$190.25",
            },
        }
        return mock_data.get(ticker.upper(), {
            "price": "$0.00",
            "change_pct": "0.00%",
            "quality_score": "0",
            "mos_pct": "0%",
            "pe_ratio": "0.0",
            "graham_iv": "$0.00",
        })


# Module-level exports
__all__ = ["WatchlistPanel"]
