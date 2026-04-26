"""
Trading Journal Panel - Complete Trade Logging and Analysis.

Features:
- Add new trades via dialog
- Live table of open trades with current prices
- Trading statistics (Win Rate, Profit Factor, Expectancy, etc.)
- Plan adherence tracking
- Equity curve visualization
- Weekly postmortem analysis

Phase 3+ - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, Dict, List, Any
from decimal import Decimal
from datetime import datetime, timedelta
import asyncio
import logging
import traceback

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
    QSpacerItem, QSizePolicy, QHeaderView, QAbstractItemView, QMenu,
    QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QBrush
import pyqtgraph as pg

from quantum_terminal.ui.dialogs.add_trade_dialog import AddTradeDialog, TradeData
from quantum_terminal.ui.widgets import MetricCard, AlertBanner
from quantum_terminal.utils.logger import get_logger

# Import configuration
try:
    from quantum_terminal.config import settings
except ImportError:
    settings = None

# Import infrastructure
try:
    from quantum_terminal.infrastructure.market_data.data_provider import (
        DataProvider,
    )
except ImportError:
    DataProvider = None

try:
    from quantum_terminal.infrastructure.ai.ai_gateway import AIGateway
except ImportError:
    AIGateway = None

# Import use cases
try:
    from quantum_terminal.application.trading import (
        LogTradeUseCase,
        CloseTradeUseCase,
        TradeStatisticsUseCase,
        PlanAdherenceUseCase,
        PostmortemUseCase,
    )
except ImportError:
    LogTradeUseCase = None

logger = get_logger(__name__)


class DataLoaderThread(QThread):
    """Background thread for async data loading."""

    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, data_fetcher):
        super().__init__()
        self.data_fetcher = data_fetcher
        self.daemon = True

    def run(self):
        try:
            data = asyncio.run(self.data_fetcher())
            self.data_loaded.emit(data)
        except Exception as e:
            logger.error(f"Data loader thread error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class TradingJournalPanel(QWidget):
    """
    Complete Trading Journal Panel with live trade tracking and analysis.

    Integrates with:
    - Domain layer: Risk metrics, trading formulas
    - Infrastructure: DataProvider (live quotes), AIGateway (postmortem analysis)
    - Application layer: Use cases for trade operations

    Signals:
        trade_added: Emitted when a new trade is added
        trade_closed: Emitted when a trade is closed
    """

    trade_added = pyqtSignal(dict)  # trade data
    trade_closed = pyqtSignal(str)  # trade_id

    def __init__(self, parent=None):
        """Initialize the Trading Journal Panel."""
        super().__init__(parent)
        self.trades: Dict[str, Dict] = {}  # trade_id -> trade data
        self.data_provider = DataProvider() if DataProvider else None
        self.ai_gateway = AIGateway() if AIGateway else None

        # Initialize use cases
        self.stats_usecase = TradeStatisticsUseCase(None)
        self.adherence_usecase = PlanAdherenceUseCase()
        self.postmortem_usecase = (
            PostmortemUseCase(self.ai_gateway) if self.ai_gateway else None
        )

        # UI timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_open_trades)
        self.update_timer.start(5000)  # Update every 5 seconds

        self.initUI()

    def initUI(self) -> None:
        """Initialize UI components."""
        main_layout = QVBoxLayout()

        # Header: Title + Add Trade Button
        header_layout = QHBoxLayout()
        title = QLabel("Trading Journal")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        add_btn = QPushButton("+ Add Trade")
        add_btn.setProperty("accent", True)
        add_btn.clicked.connect(self.open_add_trade_dialog)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # Scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ===== OPEN TRADES TABLE =====
        scroll_layout.addWidget(QLabel("Open Trades"))
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(11)
        self.trades_table.setHorizontalHeaderLabels(
            [
                "Ticker",
                "Dir",
                "Size",
                "Entry",
                "Current",
                "Exit",
                "Stop",
                "P&L $",
                "P&L %",
                "R Risk",
                "Status",
            ]
        )
        self.trades_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.trades_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.trades_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trades_table.customContextMenuRequested.connect(
            self.show_trade_context_menu
        )
        self.trades_table.setMaximumHeight(250)
        scroll_layout.addWidget(self.trades_table)

        # ===== STATISTICS =====
        scroll_layout.addWidget(QLabel("Trading Statistics"))
        stats_layout = QGridLayout()

        self.stat_cards = {
            "win_rate": MetricCard("Win Rate", "0%"),
            "profit_factor": MetricCard("Profit Factor", "0.0"),
            "expectancy": MetricCard("Expectancy", "$0"),
            "avg_r": MetricCard("Avg R", "0.0"),
            "avg_duration": MetricCard("Avg Duration", "0 days"),
            "adherence": MetricCard("Adherence", "0%"),
        }

        col = 0
        for card in self.stat_cards.values():
            stats_layout.addWidget(card, 0, col % 3)
            col += 1

        scroll_layout.addLayout(stats_layout)

        # ===== EQUITY CURVE =====
        scroll_layout.addWidget(QLabel("Equity Curve"))
        self.equity_curve_widget = pg.PlotWidget(
            title="Portfolio Equity Curve"
        )
        self.equity_curve_widget.setLabel("left", "Equity", units="$")
        self.equity_curve_widget.setLabel("bottom", "Date")
        self.equity_curve_widget.showGrid(True, True)
        self.equity_curve_widget.setMinimumHeight(300)
        self.equity_curve_line = self.equity_curve_widget.plot(
            pen=pg.mkPen(color=(52, 152, 219), width=2)
        )
        scroll_layout.addWidget(self.equity_curve_widget)

        # ===== ADHERENCE & POSTMORTEM =====
        adherence_layout = QHBoxLayout()

        self.adherence_card = MetricCard("Plan Adherence", "0%")
        adherence_layout.addWidget(self.adherence_card)

        postmortem_btn = QPushButton("Weekly Postmortem")
        postmortem_btn.setProperty("accent", True)
        postmortem_btn.clicked.connect(self.generate_postmortem)
        adherence_layout.addWidget(postmortem_btn)

        adherence_layout.addStretch()
        scroll_layout.addLayout(adherence_layout)

        # ===== POSTMORTEM ANALYSIS TEXT =====
        scroll_layout.addWidget(QLabel("Analysis"))
        self.analysis_text = QLabel("Ready for analysis...")
        self.analysis_text.setWordWrap(True)
        self.analysis_text.setStyleSheet(
            "background-color: #2c3e50; padding: 10px; border-radius: 4px;"
        )
        scroll_layout.addWidget(self.analysis_text)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)
        self.load_trades()

    def open_add_trade_dialog(self) -> None:
        """Open dialog to add a new trade."""
        dialog = AddTradeDialog(self)
        dialog.trade_saved.connect(self.on_trade_saved)
        dialog.exec()

    @pyqtSlot(TradeData)
    def on_trade_saved(self, trade_data: TradeData) -> None:
        """Handle new trade from dialog."""
        try:
            # Create trade dict
            trade = {
                "trade_id": self._generate_trade_id(),
                "ticker": trade_data.ticker,
                "direction": trade_data.direction,
                "size": trade_data.size,
                "entry_price": trade_data.entry_price,
                "exit_price": trade_data.exit_price,
                "stop_loss": trade_data.stop_loss,
                "take_profit": trade_data.take_profit,
                "reason": trade_data.reason,
                "plan_adherence": trade_data.plan_adherence,
                "entry_date": trade_data.entry_date,
                "status": "open",
                "current_price": trade_data.entry_price,
            }

            # Store in memory
            self.trades[trade["trade_id"]] = trade

            # Add to table
            self.add_trade_to_table(trade)

            # Emit signal
            self.trade_added.emit(trade)

            # Recalculate stats
            self.update_statistics()

            QMessageBox.information(
                self, "Success", f"Trade {trade_data.ticker} added successfully"
            )

        except Exception as e:
            logger.error(f"Error saving trade: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error", f"Failed to save trade: {str(e)}"
            )

    def add_trade_to_table(self, trade: Dict) -> None:
        """Add a trade row to the trades table."""
        row = self.trades_table.rowCount()
        self.trades_table.insertRow(row)

        # Create items
        items = [
            trade["ticker"],
            trade["direction"],
            f"{trade['size']:.2f}",
            f"${trade['entry_price']:.2f}",
            f"${trade.get('current_price', trade['entry_price']):.2f}",
            f"${trade.get('exit_price', 0):.2f}" if trade.get("exit_price") else "-",
            f"${trade.get('stop_loss', 0):.2f}" if trade.get("stop_loss") else "-",
            "$0.00",  # P&L $
            "0.00%",  # P&L %
            "0.0",  # R Risk
            trade["status"],
        ]

        for col, item_text in enumerate(items):
            item = QTableWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, trade["trade_id"])
            self.trades_table.setItem(row, col, item)

    def update_open_trades(self) -> None:
        """Update prices and P&L for open trades."""
        if not self.data_provider:
            return

        try:
            # Get unique tickers
            tickers = list(set(t["ticker"] for t in self.trades.values()))

            # Fetch quotes (non-blocking)
            asyncio.create_task(self._fetch_and_update_quotes(tickers))

        except Exception as e:
            logger.error(f"Error updating trades: {e}", exc_info=True)

    async def _fetch_and_update_quotes(self, tickers: List[str]) -> None:
        """Fetch quotes and update table."""
        try:
            for ticker in tickers:
                quote = await self.data_provider.get_quote(ticker)
                if quote and "price" in quote:
                    self._update_trade_price(ticker, quote["price"])
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}", exc_info=True)

    def _update_trade_price(self, ticker: str, price: float) -> None:
        """Update a trade's current price and P&L."""
        # Find and update all trades for this ticker
        for row in range(self.trades_table.rowCount()):
            ticker_item = self.trades_table.item(row, 0)
            if ticker_item and ticker_item.text() == ticker:
                # Update current price
                current_item = self.trades_table.item(row, 4)
                if current_item:
                    current_item.setText(f"${price:.2f}")

                # Get trade data
                trade_id = ticker_item.data(Qt.ItemDataRole.UserRole)
                if trade_id in self.trades:
                    trade = self.trades[trade_id]
                    trade["current_price"] = price

                    # Calculate P&L
                    entry = trade["entry_price"]
                    size = trade["size"]
                    direction = trade["direction"].lower()

                    if direction == "long" or direction == "buy":
                        pnl_dollars = (price - entry) * size
                    else:
                        pnl_dollars = (entry - price) * size

                    pnl_percent = (
                        ((price - entry) / entry * 100)
                        if direction == "long"
                        else ((entry - price) / entry * 100)
                    )

                    # Update table
                    pnl_dollar_item = self.trades_table.item(row, 7)
                    if pnl_dollar_item:
                        pnl_dollar_item.setText(f"${pnl_dollars:.2f}")
                        color = QColor(76, 175, 80) if pnl_dollars >= 0 else QColor(
                            244, 67, 54
                        )
                        pnl_dollar_item.setForeground(QBrush(color))

                    pnl_percent_item = self.trades_table.item(row, 8)
                    if pnl_percent_item:
                        pnl_percent_item.setText(f"{pnl_percent:.2f}%")
                        color = QColor(76, 175, 80) if pnl_percent >= 0 else QColor(
                            244, 67, 54
                        )
                        pnl_percent_item.setForeground(QBrush(color))

    def show_trade_context_menu(self, pos) -> None:
        """Show context menu for trade row."""
        item = self.trades_table.itemAt(pos)
        if not item:
            return

        row = item.row()
        trade_id = self.trades_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        close_action = menu.addAction("Close Trade")
        edit_action = menu.addAction("Edit Trade")
        delete_action = menu.addAction("Delete Trade")

        action = menu.exec(self.trades_table.mapToGlobal(pos))

        if action == close_action:
            self.close_trade_dialog(trade_id)
        elif action == edit_action:
            self.edit_trade(trade_id)
        elif action == delete_action:
            self.delete_trade(trade_id)

    def close_trade_dialog(self, trade_id: str) -> None:
        """Open dialog to close a trade."""
        if trade_id not in self.trades:
            return

        trade = self.trades[trade_id]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Close Trade - {trade['ticker']}")
        dialog.setGeometry(200, 200, 400, 150)

        layout = QFormLayout()

        exit_price_input = QDoubleSpinBox()
        exit_price_input.setRange(0.01, 1000000)
        exit_price_input.setValue(trade.get("current_price", trade["entry_price"]))
        exit_price_input.setSingleStep(0.01)
        layout.addRow("Exit Price:", exit_price_input)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Close Trade")
        save_btn.setProperty("accent", True)
        cancel_btn = QPushButton("Cancel")

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.setLayout(layout)

        save_btn.clicked.connect(
            lambda: self.confirm_close_trade(
                trade_id, exit_price_input.value(), dialog
            )
        )
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def confirm_close_trade(
        self, trade_id: str, exit_price: float, dialog: QDialog
    ) -> None:
        """Confirm and close a trade."""
        try:
            if trade_id not in self.trades:
                return

            trade = self.trades[trade_id]
            trade["exit_price"] = exit_price
            trade["exit_date"] = datetime.now().isoformat()
            trade["status"] = "closed"

            # Update table
            for row in range(self.trades_table.rowCount()):
                item = self.trades_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == trade_id:
                    self.trades_table.item(row, 5).setText(f"${exit_price:.2f}")
                    self.trades_table.item(row, 10).setText("closed")
                    break

            self.trade_closed.emit(trade_id)
            self.update_statistics()

            dialog.accept()
            QMessageBox.information(self, "Success", "Trade closed successfully")

        except Exception as e:
            logger.error(f"Error closing trade: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to close trade: {str(e)}")

    def edit_trade(self, trade_id: str) -> None:
        """Edit an existing trade."""
        QMessageBox.information(self, "Info", "Edit trade feature coming soon")

    def delete_trade(self, trade_id: str) -> None:
        """Delete a trade."""
        try:
            if trade_id not in self.trades:
                return

            # Remove from memory
            del self.trades[trade_id]

            # Remove from table
            for row in range(self.trades_table.rowCount()):
                item = self.trades_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == trade_id:
                    self.trades_table.removeRow(row)
                    break

            self.update_statistics()
            QMessageBox.information(self, "Success", "Trade deleted")

        except Exception as e:
            logger.error(f"Error deleting trade: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to delete trade: {str(e)}")

    async def update_statistics(self) -> None:
        """Update trading statistics."""
        try:
            trades_list = list(self.trades.values())

            # Get stats
            stats = await self.stats_usecase.execute(trades_list)

            if "error" not in stats:
                self.stat_cards["win_rate"].setValue(f"{stats.get('win_rate', 0):.1f}%")
                self.stat_cards["profit_factor"].setValue(
                    f"{stats.get('profit_factor', 0):.2f}"
                )
                self.stat_cards["expectancy"].setValue(
                    f"${stats.get('expectancy', 0):.2f}"
                )
                self.stat_cards["avg_r"].setValue(
                    f"{stats.get('avg_r_multiple', 0):.2f}"
                )
                self.stat_cards["avg_duration"].setValue(
                    f"{stats.get('avg_duration_days', 0):.0f} days"
                )

            # Get adherence
            adherence = await self.adherence_usecase.execute(trades_list)
            if "error" not in adherence:
                self.stat_cards["adherence"].setValue(
                    f"{adherence.get('adherence_score', 0):.1f}%"
                )

            # Update equity curve
            self.update_equity_curve(trades_list)

        except Exception as e:
            logger.error(f"Error updating statistics: {e}", exc_info=True)

    def update_equity_curve(self, trades: List[Dict]) -> None:
        """Update equity curve chart."""
        try:
            # Calculate cumulative equity
            dates = []
            equities = []
            cumulative = 0

            # Sort trades by entry date
            sorted_trades = sorted(trades, key=lambda t: t.get("entry_date", ""))

            for trade in sorted_trades:
                if trade.get("exit_price") and trade.get("exit_date"):
                    entry = Decimal(str(trade.get("entry_price", 0)))
                    exit_price = Decimal(str(trade.get("exit_price", 0)))
                    size = Decimal(str(trade.get("size", 0)))
                    direction = trade.get("direction", "Long").lower()

                    if direction == "long" or direction == "buy":
                        pnl = (exit_price - entry) * size
                    else:
                        pnl = (entry - exit_price) * size

                    cumulative += float(pnl)

                    try:
                        date = datetime.fromisoformat(trade.get("exit_date"))
                        dates.append(date.timestamp())
                        equities.append(cumulative)
                    except Exception:
                        pass

            if dates and equities:
                self.equity_curve_line.setData(dates, equities)

        except Exception as e:
            logger.error(f"Error updating equity curve: {e}", exc_info=True)

    async def generate_postmortem(self) -> None:
        """Generate weekly postmortem analysis."""
        try:
            if not self.postmortem_usecase:
                QMessageBox.warning(
                    self, "Error", "AI Gateway not initialized"
                )
                return

            # Get trades from last 7 days
            trades_list = list(self.trades.values())
            recent_trades = [
                t for t in trades_list
                if self._is_recent(t.get("exit_date") or t.get("entry_date"))
            ]

            if not recent_trades:
                QMessageBox.information(
                    self, "Info", "No trades in the past 7 days"
                )
                return

            # Generate postmortem
            result = await self.postmortem_usecase.execute(
                recent_trades, period="weekly"
            )

            if result.get("success"):
                self.analysis_text.setText(result.get("analysis", ""))
                QMessageBox.information(
                    self, "Analysis Complete", "Postmortem generated"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to generate analysis: {result.get('error')}",
                )

        except Exception as e:
            logger.error(f"Error generating postmortem: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error", f"Failed to generate postmortem: {str(e)}"
            )

    def _is_recent(self, date_str: str, days: int = 7) -> bool:
        """Check if date is within last N days."""
        try:
            trade_date = datetime.fromisoformat(date_str)
            return datetime.now() - trade_date <= timedelta(days=days)
        except Exception:
            return False

    def load_trades(self) -> None:
        """Load trades from memory/database."""
        # TODO: Load from database when infrastructure is ready
        pass

    def _generate_trade_id(self) -> str:
        """Generate unique trade ID."""
        return f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def closeEvent(self, event) -> None:
        """Clean up timers on close."""
        self.update_timer.stop()
        super().closeEvent(event)
