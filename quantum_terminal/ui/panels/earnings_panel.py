"""
Earnings Tracker Panel - Earnings calendar, surprises, and implied moves.

Features:
- Earnings Calendar: Date | Hour | Ticker | Company | Consensus EPS | Real EPS | Beat/Miss | Move %
- Filters: by week/month, watchlist integration
- Alerts: 48h before for open positions
- Company View: 8-quarter surprise history, beating streak, guidance
- Implied Move: Expected move from IV (±%)
- Management Guidance: Revenue & EPS guidance tracking
- AI Analysis: "What to expect from {ticker} earnings"
- Color coding: Green=beat, Red=miss

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Module 9: Earnings Tracker
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
from threading import Thread
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QHeaderView, QMenu,
    QMessageBox, QPushButton, QSpacerItem, QSizePolicy, QProgressBar,
    QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QCalendarWidget,
    QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent, QThread, pyqtSlot, QDate
from PyQt6.QtGui import QFont, QColor, QIcon, QBrush
from PyQt6.QtCore import QSize

from quantum_terminal.ui.widgets import TickerSearch, DataTable
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.config import settings

logger = get_logger(__name__)


class EarningsLoaderWorker(QThread):
    """Worker thread for loading earnings data without blocking UI."""

    progress = pyqtSignal(int)  # Loading progress
    finished = pyqtSignal(dict)  # Dict with earnings calendar and implied moves
    error = pyqtSignal(str)  # Error message

    def __init__(self, from_date: datetime, to_date: datetime, watchlist: List[str]):
        super().__init__()
        self.from_date = from_date
        self.to_date = to_date
        self.watchlist = watchlist

    def run(self):
        """Run earnings data loading in worker thread."""
        try:
            result_data = {
                "calendar": self._get_earnings_calendar(),
                "implied_moves": self._get_implied_moves(),
                "surprise_history": self._get_surprise_history(),
            }
            self.finished.emit(result_data)

        except Exception as e:
            logger.error(f"Earnings loader error: {e}", exc_info=True)
            self.error.emit(f"Failed to load earnings data: {str(e)}")

    def _get_earnings_calendar(self) -> List[Dict]:
        """Fetch earnings calendar (mock for MVP, real: finnhub_adapter.get_earnings_calendar)."""
        # Mock earnings calendar - in production use:
        # from quantum_terminal.infrastructure.market_data import finnhub_adapter
        # earnings = await finnhub_adapter.get_earnings_calendar(from_date, to_date)

        today = datetime.now()
        calendar = []

        tickers_to_fetch = self.watchlist if self.watchlist else ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

        mock_data = {
            "AAPL": {
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "guidance_revenue": "$95B-$97B",
                "previous_guidance": "$93B-$95B",
            },
            "MSFT": {
                "company": "Microsoft Corp.",
                "hour": "16:30 ET",
                "consensus_eps": 3.08,
                "real_eps": 3.05,
                "guidance_revenue": "$62B-$63B",
                "previous_guidance": "$60B-$61B",
            },
            "GOOGL": {
                "company": "Alphabet Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.85,
                "real_eps": 1.92,
                "guidance_revenue": "$88B-$90B",
                "previous_guidance": "$85B-$87B",
            },
            "TSLA": {
                "company": "Tesla Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 0.75,
                "real_eps": 0.71,
                "guidance_revenue": "$28B-$29B",
                "previous_guidance": "$27B-$28B",
            },
            "AMZN": {
                "company": "Amazon.com Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 0.95,
                "real_eps": 1.02,
                "guidance_revenue": "$147B-$150B",
                "previous_guidance": "$144B-$147B",
            },
        }

        for ticker in tickers_to_fetch:
            base_data = mock_data.get(ticker.upper(), {})
            if not base_data:
                continue

            # Generate dates for next 30 days
            days_offset = np.random.randint(1, 30)
            earnings_date = today + timedelta(days=days_offset)

            consensus = base_data.get("consensus_eps", 1.0)
            real = base_data.get("real_eps", 1.0)
            beat = (real - consensus) / consensus * 100 if consensus != 0 else 0.0

            calendar.append({
                "date": earnings_date.strftime("%Y-%m-%d"),
                "datetime": earnings_date,
                "ticker": ticker.upper(),
                "company": base_data.get("company", ticker),
                "hour": base_data.get("hour", "After Market"),
                "consensus_eps": consensus,
                "real_eps": real,
                "eps_beat_pct": beat,
                "beat": beat > 0.5,  # Beat if > 0.5%
                "move_pct": abs(beat) * 0.7,  # Approximate move from beat magnitude
                "guidance_revenue": base_data.get("guidance_revenue", "N/A"),
                "previous_guidance": base_data.get("previous_guidance", "N/A"),
                "in_watchlist": ticker.upper() in self.watchlist,
                "days_until": days_offset,
            })

        # Sort by date
        calendar.sort(key=lambda x: x["datetime"])
        return calendar

    def _get_implied_moves(self) -> Dict[str, float]:
        """Calculate implied moves from IV (mock for MVP)."""
        # In production: use yfinance options data to calculate IV
        # from quantum_terminal.infrastructure.market_data import yfinance
        # options = await yfinance.Ticker(ticker).option_chain()
        # iv = calculate_historical_volatility(options)
        # implied_move = iv * stock_price

        mock_iv = {
            "AAPL": 25.5,  # 25.5% annualized, ~1.5% for one earnings
            "MSFT": 22.3,
            "GOOGL": 23.8,
            "TSLA": 45.2,  # High IV
            "AMZN": 26.1,
        }

        implied_moves = {}
        for ticker, iv_pct in mock_IV.items():
            # Convert annual IV to one-event move estimate: IV/sqrt(252) ≈ daily vol, then * sqrt(1 day from earnings)
            implied_move = (iv_pct / np.sqrt(252)) * np.sqrt(1) * np.sqrt(2)  # ~2x normal vol for event
            implied_moves[ticker] = min(implied_move, 10.0)  # Cap at 10%

        return implied_moves

    def _get_surprise_history(self) -> Dict[str, Dict]:
        """Get historical surprise data for each ticker (last 8 quarters)."""
        mock_history = {
            "AAPL": {
                "surprising_beats": 6,  # Out of last 8
                "avg_beat_pct": 2.3,
                "streak": 4,  # 4 quarters in a row beating
                "recent_surprises": [
                    {"quarter": "Q1 2026", "beat": True, "pct": 4.2},
                    {"quarter": "Q4 2025", "beat": True, "pct": 3.1},
                    {"quarter": "Q3 2025", "beat": True, "pct": 2.8},
                    {"quarter": "Q2 2025", "beat": True, "pct": 1.5},
                    {"quarter": "Q1 2025", "beat": False, "pct": -1.2},
                    {"quarter": "Q4 2024", "beat": False, "pct": -0.8},
                    {"quarter": "Q3 2024", "beat": True, "pct": 2.1},
                    {"quarter": "Q2 2024", "beat": True, "pct": 1.9},
                ],
            },
            "MSFT": {
                "surprising_beats": 8,
                "avg_beat_pct": 3.1,
                "streak": 8,
                "recent_surprises": [
                    {"quarter": f"Q{q}", "beat": True, "pct": np.random.uniform(1, 4)} for q in range(1, 9)
                ],
            },
            "GOOGL": {
                "surprising_beats": 7,
                "avg_beat_pct": 2.7,
                "streak": 3,
                "recent_surprises": [
                    {"quarter": f"Q{q}", "beat": np.random.random() > 0.3, "pct": np.random.uniform(-2, 4)} for q in range(1, 9)
                ],
            },
            "TSLA": {
                "surprising_beats": 5,
                "avg_beat_pct": 1.8,
                "streak": 2,
                "recent_surprises": [
                    {"quarter": f"Q{q}", "beat": np.random.random() > 0.4, "pct": np.random.uniform(-3, 5)} for q in range(1, 9)
                ],
            },
            "AMZN": {
                "surprising_beats": 6,
                "avg_beat_pct": 2.5,
                "streak": 3,
                "recent_surprises": [
                    {"quarter": f"Q{q}", "beat": np.random.random() > 0.35, "pct": np.random.uniform(-1, 4)} for q in range(1, 9)
                ],
            },
        }

        return mock_history


class EarningsPanel(QWidget):
    """
    Earnings Tracker panel showing calendar, surprises, and implied moves.

    Signals:
        - ticker_selected: Emitted when user selects a ticker for detailed analysis
        - alert_requested: Emitted when user requests 48h pre-earnings alert
    """

    ticker_selected = pyqtSignal(str)  # ticker
    alert_requested = pyqtSignal(str)  # ticker

    def __init__(self, parent=None, watchlist: Optional[List[str]] = None):
        """Initialize the earnings tracker panel."""
        super().__init__(parent)
        self.watchlist = watchlist or []
        self.earnings_calendar: List[Dict] = []
        self.implied_moves: Dict[str, float] = {}
        self.surprise_history: Dict[str, Dict] = {}
        self.loader_worker: Optional[EarningsLoaderWorker] = None
        self.is_loading = False

        # Date filter
        self.filter_from_date = datetime.now()
        self.filter_to_date = datetime.now() + timedelta(days=30)

        self.initUI()
        self.setup_connections()
        self._load_earnings_data()

    def initUI(self):
        """Build the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title bar
        title_layout = self._build_title_bar()
        main_layout.addLayout(title_layout)

        # Filter section
        filter_layout = self._build_filter_section()
        main_layout.addLayout(filter_layout)

        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 1: Earnings Calendar
        self.calendar_tab = self._build_calendar_tab()
        self.tabs.addTab(self.calendar_tab, "Earnings Calendar")

        # Tab 2: By Company (Detailed)
        self.company_tab = self._build_company_tab()
        self.tabs.addTab(self.company_tab, "By Company")

        # Tab 3: Implied Moves
        self.moves_tab = self._build_moves_tab()
        self.tabs.addTab(self.moves_tab, "Implied Moves")

        # Tab 4: AI Analysis
        self.analysis_tab = self._build_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "AI Analysis")

        main_layout.addWidget(self.tabs)

        # Status bar
        status_layout = self._build_status_bar()
        main_layout.addLayout(status_layout)

        self.setLayout(main_layout)

    def _build_title_bar(self) -> QHBoxLayout:
        """Build title bar."""
        layout = QHBoxLayout()

        title = QLabel("Earnings Tracker")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addSpacing(10)

        # Status indicator
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: #00cc00; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Event count
        self.count_label = QLabel("0 events")
        layout.addWidget(self.count_label)

        return layout

    def _build_filter_section(self) -> QHBoxLayout:
        """Build filter section with date range and watchlist toggle."""
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Filter by:"))

        # Period selector
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Next 7 days", "Next 2 weeks", "Next 30 days", "All"])
        self.period_combo.currentTextChanged.connect(self._on_period_changed)
        layout.addWidget(self.period_combo)

        layout.addSpacing(20)

        # Watchlist only toggle
        self.watchlist_only_btn = QPushButton("📍 Watchlist Only")
        self.watchlist_only_btn.setMaximumWidth(130)
        self.watchlist_only_btn.setCheckable(True)
        self.watchlist_only_btn.setChecked(False)
        self.watchlist_only_btn.clicked.connect(self._on_watchlist_toggle)
        layout.addWidget(self.watchlist_only_btn)

        layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self._load_earnings_data)
        layout.addWidget(refresh_btn)

        return layout

    def _build_calendar_tab(self) -> QWidget:
        """Build earnings calendar tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)

        # Calendar table: Date | Hour | Ticker | Company | Consensus EPS | Real EPS | Beat/Miss | Move %
        self.calendar_table = QTableWidget()
        self.calendar_table.setColumnCount(9)
        self.calendar_table.setHorizontalHeaderLabels([
            "Date", "Time", "Ticker", "Company", "Consensus EPS", "Real EPS", "Beat/Miss %", "Move %", "Action"
        ])

        header = self.calendar_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        self.calendar_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #444;
                gridline-color: #333;
                background-color: #1a1a1a;
                alternate-background-color: #252525;
            }
            QTableWidget::item {
                padding: 6px;
                border-right: 1px solid #333;
                height: 28px;
            }
            QTableWidget::item:selected {
                background-color: #1e90ff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #fff;
                padding: 6px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)

        self.calendar_table.setAlternatingRowColors(True)
        self.calendar_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.calendar_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.calendar_table.customContextMenuRequested.connect(self._on_calendar_context_menu)
        self.calendar_table.doubleClicked.connect(self._on_calendar_double_clicked)

        layout.addWidget(self.calendar_table)
        return container

    def _build_company_tab(self) -> QWidget:
        """Build company detail tab with surprise history."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # Company selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Company:"))
        self.company_combo = QComboBox()
        self.company_combo.currentTextChanged.connect(self._on_company_selected)
        selector_layout.addWidget(self.company_combo)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Surprise statistics
        stats_layout = QHBoxLayout()

        self.beating_streak_label = QLabel("Beating Streak: --")
        self.beating_streak_label.setFont(QFont("JetBrains Mono", 11))
        stats_layout.addWidget(self.beating_streak_label)

        stats_layout.addSpacing(20)

        self.avg_beat_label = QLabel("Avg Beat: --")
        self.avg_beat_label.setFont(QFont("JetBrains Mono", 11))
        stats_layout.addWidget(self.avg_beat_label)

        stats_layout.addSpacing(20)

        self.beats_count_label = QLabel("Beats (8Q): --")
        self.beats_count_label.setFont(QFont("JetBrains Mono", 11))
        stats_layout.addWidget(self.beats_count_label)

        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Surprise history table
        self.surprise_table = QTableWidget()
        self.surprise_table.setColumnCount(4)
        self.surprise_table.setHorizontalHeaderLabels(["Quarter", "Result", "Beat/Miss %", "EPS vs Consensus"])

        header = self.surprise_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.surprise_table)

        # Guidance section
        guidance_label = QLabel("Management Guidance")
        guidance_label.setFont(QFont("JetBrains Mono", 11, weight=QFont.Weight.Bold))
        layout.addWidget(guidance_label)

        guidance_layout = QHBoxLayout()

        self.revenue_guidance_label = QLabel("Revenue Guidance: --")
        guidance_layout.addWidget(self.revenue_guidance_label)

        guidance_layout.addSpacing(30)

        self.prev_guidance_label = QLabel("Previous: --")
        guidance_layout.addWidget(self.prev_guidance_label)

        guidance_layout.addStretch()

        layout.addLayout(guidance_layout)

        return container

    def _build_moves_tab(self) -> QWidget:
        """Build implied moves tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        title = QLabel("Expected Stock Movement")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel("Based on option implied volatility (IV), market expects these moves after earnings")
        desc.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(desc)

        # Moves table: Ticker | Current Price | IV Annual | Expected Move | Historical vs Implied
        self.moves_table = QTableWidget()
        self.moves_table.setColumnCount(5)
        self.moves_table.setHorizontalHeaderLabels([
            "Ticker", "Current Price", "IV (Annual %)", "Expected Move (±%)", "Historical Avg"
        ])

        header = self.moves_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.moves_table)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend: IV = Implied Volatility from option chain"))
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        return container

    def _build_analysis_tab(self) -> QWidget:
        """Build AI analysis tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # Ticker selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Analyze:"))
        self.analysis_ticker_combo = QComboBox()
        self.analysis_ticker_combo.currentTextChanged.connect(self._on_analysis_ticker_changed)
        selector_layout.addWidget(self.analysis_ticker_combo)

        analyze_btn = QPushButton("🤖 Generate Analysis")
        analyze_btn.setMaximumWidth(150)
        analyze_btn.clicked.connect(self._on_generate_analysis)
        selector_layout.addWidget(analyze_btn)

        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Analysis text area
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #444;
                font-family: 'JetBrains Mono';
                font-size: 10px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.analysis_text)

        # Loading indicator
        self.analysis_progress = QProgressBar()
        self.analysis_progress.setVisible(False)
        self.analysis_progress.setMaximumHeight(20)
        layout.addWidget(self.analysis_progress)

        return container

    def _build_status_bar(self) -> QHBoxLayout:
        """Build status bar."""
        layout = QHBoxLayout()

        self.last_update_label = QLabel("Last update: --")
        layout.addWidget(self.last_update_label)

        layout.addStretch()

        return layout

    def _load_earnings_data(self) -> None:
        """Load earnings calendar and implied moves."""
        if self.is_loading:
            logger.warning("Already loading earnings data")
            return

        self.is_loading = True
        self.status_label.setText("● Loading...")
        self.status_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        self.progress_bar.setVisible(True)

        self.loader_worker = EarningsLoaderWorker(
            self.filter_from_date,
            self.filter_to_date,
            self.watchlist
        )
        self.loader_worker.finished.connect(self._on_loader_finished)
        self.loader_worker.error.connect(self._on_loader_error)
        self.loader_worker.start()

    @pyqtSlot(dict)
    def _on_loader_finished(self, data: Dict) -> None:
        """Handle loader finished signal."""
        try:
            self.earnings_calendar = data.get("calendar", [])
            self.implied_moves = data.get("implied_moves", {})
            self.surprise_history = data.get("surprise_history", {})

            self._populate_calendar_table()
            self._populate_company_combo()
            self._populate_moves_table()
            self._populate_analysis_combo()

            self._update_count()
            self._update_last_update_time()

            self.status_label.setText("● Ready")
            self.status_label.setStyleSheet("color: #00cc00; font-weight: bold;")

            logger.info(f"Loaded {len(self.earnings_calendar)} earnings events")

        except Exception as e:
            logger.error(f"Error processing earnings data: {e}", exc_info=True)
        finally:
            self.is_loading = False
            self.progress_bar.setVisible(False)

    @pyqtSlot(str)
    def _on_loader_error(self, error_msg: str) -> None:
        """Handle loader error signal."""
        logger.error(f"Earnings loader error: {error_msg}")
        QMessageBox.warning(self, "Load Error", f"Failed to load earnings data:\n{error_msg}")
        self.is_loading = False
        self.progress_bar.setVisible(False)
        self.status_label.setText("● Error")
        self.status_label.setStyleSheet("color: #ff3333; font-weight: bold;")

    def _populate_calendar_table(self) -> None:
        """Populate the earnings calendar table."""
        self.calendar_table.setRowCount(0)

        # Apply filters
        filtered_calendar = self._apply_calendar_filters()

        for item in filtered_calendar:
            row = self.calendar_table.rowCount()
            self.calendar_table.insertRow(row)

            date_str = item["date"]
            ticker = item["ticker"]
            company = item["company"]
            hour = item["hour"]
            consensus_eps = item["consensus_eps"]
            real_eps = item["real_eps"]
            beat_pct = item["eps_beat_pct"]
            move_pct = item["move_pct"]

            # Date
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 0, date_item)

            # Time
            time_item = QTableWidgetItem(hour)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 1, time_item)

            # Ticker
            ticker_item = QTableWidgetItem(ticker)
            ticker_item.setFlags(ticker_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 2, ticker_item)

            # Company
            company_item = QTableWidgetItem(company)
            company_item.setFlags(company_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 3, company_item)

            # Consensus EPS
            consensus_item = QTableWidgetItem(f"${consensus_eps:.2f}")
            consensus_item.setFlags(consensus_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 4, consensus_item)

            # Real EPS
            real_item = QTableWidgetItem(f"${real_eps:.2f}")
            real_item.setFlags(real_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 5, real_item)

            # Beat/Miss %
            beat_item = QTableWidgetItem(f"{beat_pct:+.1f}%")
            beat_item.setFlags(beat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            if beat_pct > 0:
                beat_item.setForeground(QBrush(QColor("#00cc00")))  # Green for beat
            elif beat_pct < 0:
                beat_item.setForeground(QBrush(QColor("#ff3333")))  # Red for miss
            else:
                beat_item.setForeground(QBrush(QColor("#ffffff")))  # White for match

            self.calendar_table.setItem(row, 6, beat_item)

            # Move %
            move_item = QTableWidgetItem(f"±{move_pct:.1f}%")
            move_item.setFlags(move_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.calendar_table.setItem(row, 7, move_item)

            # Action button
            action_item = QTableWidgetItem("→ Analyze")
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            action_item.setForeground(QBrush(QColor("#1e90ff")))
            self.calendar_table.setItem(row, 8, action_item)

    def _populate_company_combo(self) -> None:
        """Populate company selector with unique tickers."""
        tickers = list(set([item["ticker"] for item in self.earnings_calendar]))
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.company_combo.addItems(sorted(tickers))
        self.company_combo.blockSignals(False)

        if tickers:
            self._on_company_selected(tickers[0])

    def _populate_moves_table(self) -> None:
        """Populate implied moves table."""
        self.moves_table.setRowCount(0)

        for ticker, implied_move in self.implied_moves.items():
            row = self.moves_table.rowCount()
            self.moves_table.insertRow(row)

            # Mock current price for demo
            mock_prices = {"AAPL": 182.50, "MSFT": 420.25, "GOOGL": 165.40, "TSLA": 245.30, "AMZN": 198.75}
            price = mock_prices.get(ticker, 150.0)

            # Mock IV annual
            mock_ivs = {"AAPL": 25.5, "MSFT": 22.3, "GOOGL": 23.8, "TSLA": 45.2, "AMZN": 26.1}
            iv_annual = mock_ivs.get(ticker, 25.0)

            ticker_item = QTableWidgetItem(ticker)
            ticker_item.setFlags(ticker_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.moves_table.setItem(row, 0, ticker_item)

            price_item = QTableWidgetItem(f"${price:.2f}")
            price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.moves_table.setItem(row, 1, price_item)

            iv_item = QTableWidgetItem(f"{iv_annual:.1f}%")
            iv_item.setFlags(iv_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.moves_table.setItem(row, 2, iv_item)

            move_item = QTableWidgetItem(f"±{implied_move:.1f}%")
            move_item.setFlags(move_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.moves_table.setItem(row, 3, move_item)

            # Historical average move (mock)
            hist_move = implied_move * 0.8  # Usually slightly less than implied
            hist_item = QTableWidgetItem(f"±{hist_move:.1f}%")
            hist_item.setFlags(hist_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.moves_table.setItem(row, 4, hist_item)

    def _populate_analysis_combo(self) -> None:
        """Populate analysis ticker selector."""
        tickers = list(set([item["ticker"] for item in self.earnings_calendar]))
        self.analysis_ticker_combo.blockSignals(True)
        self.analysis_ticker_combo.clear()
        self.analysis_ticker_combo.addItems(sorted(tickers))
        self.analysis_ticker_combo.blockSignals(False)

    def _apply_calendar_filters(self) -> List[Dict]:
        """Apply active filters to calendar."""
        filtered = self.earnings_calendar

        # Filter by watchlist
        if self.watchlist_only_btn.isChecked():
            filtered = [item for item in filtered if item["in_watchlist"]]

        return filtered

    def _update_count(self) -> None:
        """Update event count label."""
        count = len(self._apply_calendar_filters())
        self.count_label.setText(f"{count} events")

    def _update_last_update_time(self) -> None:
        """Update last update timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_update_label.setText(f"Last update: {timestamp}")

    @pyqtSlot(str)
    def _on_period_changed(self, period: str) -> None:
        """Handle period filter change."""
        today = datetime.now()

        if "7 days" in period:
            self.filter_to_date = today + timedelta(days=7)
        elif "2 weeks" in period:
            self.filter_to_date = today + timedelta(days=14)
        elif "30 days" in period:
            self.filter_to_date = today + timedelta(days=30)
        else:  # All
            self.filter_to_date = today + timedelta(days=365)

        self._populate_calendar_table()
        self._update_count()

    @pyqtSlot(bool)
    def _on_watchlist_toggle(self, checked: bool) -> None:
        """Handle watchlist-only toggle."""
        self._populate_calendar_table()
        self._update_count()

    @pyqtSlot(str)
    def _on_company_selected(self, ticker: str) -> None:
        """Handle company selection."""
        if not ticker:
            return

        history = self.surprise_history.get(ticker.upper(), {})
        self.surprise_table.setRowCount(0)

        # Update statistics
        beating_streak = history.get("streak", 0)
        avg_beat = history.get("avg_beat_pct", 0)
        beats_count = history.get("surprising_beats", 0)

        self.beating_streak_label.setText(f"Beating Streak: {beating_streak} quarters")
        self.avg_beat_label.setText(f"Avg Beat: {avg_beat:+.1f}%")
        self.beats_count_label.setText(f"Beats (8Q): {beats_count}/8")

        # Populate surprise history
        surprises = history.get("recent_surprises", [])
        for i, surprise in enumerate(surprises):
            row = self.surprise_table.rowCount()
            self.surprise_table.insertRow(row)

            quarter = surprise.get("quarter", f"Q{i+1}")
            beat = surprise.get("beat", False)
            pct = surprise.get("pct", 0)

            quarter_item = QTableWidgetItem(quarter)
            quarter_item.setFlags(quarter_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.surprise_table.setItem(row, 0, quarter_item)

            result_item = QTableWidgetItem("✓ Beat" if beat else "✗ Miss")
            result_item.setFlags(result_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            result_item.setForeground(QBrush(QColor("#00cc00") if beat else QColor("#ff3333")))
            self.surprise_table.setItem(row, 1, result_item)

            pct_item = QTableWidgetItem(f"{pct:+.1f}%")
            pct_item.setFlags(pct_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            pct_item.setForeground(QBrush(QColor("#00cc00") if pct > 0 else QColor("#ff3333")))
            self.surprise_table.setItem(row, 2, pct_item)

            eps_item = QTableWidgetItem("Above consensus" if pct > 0 else "Below consensus")
            eps_item.setFlags(eps_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.surprise_table.setItem(row, 3, eps_item)

        # Update guidance
        guidance_revenue = history.get("guidance_revenue", "N/A") if "guidance_revenue" not in history else "N/A"
        prev_guidance = history.get("previous_guidance", "N/A") if "previous_guidance" not in history else "N/A"

        self.revenue_guidance_label.setText(f"Revenue Guidance: {guidance_revenue}")
        self.prev_guidance_label.setText(f"Previous: {prev_guidance}")

    @pyqtSlot(str)
    def _on_analysis_ticker_changed(self, ticker: str) -> None:
        """Handle analysis ticker change."""
        self.analysis_text.clear()

    def _on_generate_analysis(self) -> None:
        """Generate AI analysis for selected ticker."""
        ticker = self.analysis_ticker_combo.currentText()
        if not ticker:
            return

        self.analysis_text.clear()
        self.analysis_progress.setVisible(True)
        self.analysis_text.setText("Generating analysis with AI...\n\n")

        # In production, call: await ai_gateway.generate(prompt, tipo="fast")
        # For now, mock response

        mock_analysis = f"""
Earnings Analysis: {ticker}

Historical Performance:
{ticker} has a strong track record of beating EPS expectations, with a recent 4-quarter beating streak.
The company's average beat magnitude over the last 8 quarters is +2.3%, suggesting management provides
conservative guidance to ensure consistent beats.

Recent Trends:
- Revenue growth accelerating year-over-year
- Operating margins expanding due to scale benefits
- Capital allocation focused on shareholder returns and R&D

Expected Outcomes:
Based on analyst consensus and recent trends, we expect {ticker} to:
1. Beat on EPS by approximately 2-3%
2. Meet or slightly exceed revenue guidance
3. Maintain or improve operating margins

Market Expectations:
Option markets are pricing in a ±{self.implied_moves.get(ticker, 2.5):.1f}% move after earnings,
which is in line with historical volatility. This implies investors expect a relatively muted reaction
unless guidance surprises significantly.

Key Watch Points:
- Management commentary on macro headwinds
- Guidance changes for next quarter/year
- Free cash flow generation and capital allocation plans

Recommendation:
Monitor for guidance changes which typically drive larger post-earnings moves. Keep position sizing
appropriate for expected volatility.
        """

        self.analysis_text.setText(mock_analysis)
        self.analysis_progress.setVisible(False)

    def _on_calendar_context_menu(self, position) -> None:
        """Handle right-click context menu."""
        item = self.calendar_table.itemAt(position)
        if not item:
            return

        row = item.row()
        ticker = self.calendar_table.item(row, 2).text()

        menu = QMenu()
        analyze_action = menu.addAction("📊 Analyze")
        alert_action = menu.addAction("🔔 Set Alert (48h before)")

        action = menu.exec(self.calendar_table.mapToGlobal(position))

        if action == analyze_action:
            self.ticker_selected.emit(ticker)
        elif action == alert_action:
            self.alert_requested.emit(ticker)

    def _on_calendar_double_clicked(self, index) -> None:
        """Handle double-click on calendar row."""
        row = index.row()
        ticker = self.calendar_table.item(row, 2).text()
        self.ticker_selected.emit(ticker)

    def setup_connections(self) -> None:
        """Set up signal/slot connections."""
        pass


# Module-level exports
__all__ = ["EarningsPanel", "EarningsLoaderWorker"]
