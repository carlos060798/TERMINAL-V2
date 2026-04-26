"""
Analyzer Panel - Comprehensive Graham-Dodd Analysis (7 Tabs).

Tabs:
1. Screening: 10 quality semaphores (Current Ratio, OCF/NI, D/E, etc.)
2. Income Statement: EPS, OCF/NI, D&A/CapEx, manipulation detection
3. Margins: Gross, Operating, Net margins vs sector
4. Balance Sheet: NNWC, Liquidation Value, Debt ladder
5. Historical: Recession performance, management changes, ROE/ROA/ROIC
6. Comparables: 5 peers with ratio comparison
7. Valuation: Graham Formula, MoS, P/E adjusted, EPV

Sidebar:
- TradingView chart embed
- AI Thesis panel (Groq/DeepSeek analysis)
- Chat with AI about company

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, Dict, List, Tuple
from decimal import Decimal
import logging
import asyncio

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QLabel, QHeaderView, QScrollArea, QSplitter,
    QPushButton, QTextEdit, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPixmap, QBrush
from PyQt6.QtWebEngineWidgets import QWebEngineView

from quantum_terminal.ui.widgets import ChartWidget, AIChatWidget
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.domain.valuation import (
    graham_formula, nnwc, liquidation_value, adjusted_pe_ratio
)
from quantum_terminal.domain.risk import quality_score, detect_manipulation

logger = get_logger(__name__)


class AnalyzerPanel(QWidget):
    """
    Comprehensive analyzer panel with 7 Graham-Dodd analysis tabs.

    Signals:
        - company_loaded: Emitted when a new company is loaded
        - analysis_complete: Emitted when analysis is complete
        - ai_thesis_generated: Emitted when AI generates thesis
    """

    company_loaded = pyqtSignal(str)  # ticker
    analysis_complete = pyqtSignal(str)  # ticker
    ai_thesis_generated = pyqtSignal(str, str)  # ticker, thesis_text

    def __init__(self, parent=None):
        """Initialize the analyzer panel."""
        super().__init__(parent)
        self.current_ticker = None
        self.company_data = {}
        self.analysis_results = {}
        self.initUI()
        self.setup_connections()

    def initUI(self):
        """Build the UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left side: Tabs
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # Title and ticker selector
        title_layout = self._build_title_section()
        title_widget = QWidget()
        title_widget.setLayout(title_layout)
        left_splitter.addWidget(title_widget)

        # Main tabs
        self.tabs = self._build_analysis_tabs()
        left_splitter.addWidget(self.tabs)

        left_splitter.setSizes([80, 920])
        main_layout.addWidget(left_splitter, 70)

        # Right side: Sidebar
        self.sidebar = self._build_sidebar()
        main_layout.addWidget(self.sidebar, 30)

        self.setLayout(main_layout)

    def _build_title_section(self) -> QVBoxLayout:
        """Build title and ticker selector section."""
        layout = QVBoxLayout()

        title = QLabel("Company Analyzer")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Ticker search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Ticker:"))
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Enter ticker (e.g., AAPL)")
        self.ticker_input.setMaximumWidth(150)
        self.ticker_input.returnPressed.connect(self._on_ticker_entered)
        search_layout.addWidget(self.ticker_input)

        load_btn = QPushButton("Load")
        load_btn.setMaximumWidth(70)
        load_btn.clicked.connect(self._on_load_company)
        search_layout.addWidget(load_btn)

        layout.addLayout(search_layout)

        return layout

    def _build_analysis_tabs(self) -> QTabWidget:
        """Build the 7 analysis tabs."""
        tabs = QTabWidget()

        # Tab 1: Screening (10 quality semaphores)
        self.screening_tab = self._build_screening_tab()
        tabs.addTab(self.screening_tab, "Screening")

        # Tab 2: Income Statement
        self.income_tab = self._build_income_statement_tab()
        tabs.addTab(self.income_tab, "Income Statement")

        # Tab 3: Margins
        self.margins_tab = self._build_margins_tab()
        tabs.addTab(self.margins_tab, "Margins")

        # Tab 4: Balance Sheet
        self.balance_tab = self._build_balance_sheet_tab()
        tabs.addTab(self.balance_tab, "Balance Sheet")

        # Tab 5: Historical
        self.historical_tab = self._build_historical_tab()
        tabs.addTab(self.historical_tab, "Historical")

        # Tab 6: Comparables
        self.comparables_tab = self._build_comparables_tab()
        tabs.addTab(self.comparables_tab, "Comparables")

        # Tab 7: Valuation
        self.valuation_tab = self._build_valuation_tab()
        tabs.addTab(self.valuation_tab, "Valuation")

        return tabs

    def _build_screening_tab(self) -> QWidget:
        """Build Screening tab with 10 quality semaphores."""
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("Quality Screening - 10 Key Factors")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Grid of 10 semaphores
        grid = QHBoxLayout()

        self.semaphores = {}
        factors = [
            ("Current Ratio", "> 1.5"),
            ("Quick Ratio", "> 1.0"),
            ("D/E Ratio", "< 0.5"),
            ("OCF/NI", "> 0.8"),
            ("ROE", "> 15%"),
            ("ROIC", "> WACC"),
            ("EPS Growth", "+ 5-15% CAGR"),
            ("Debt/EBITDA", "< 2.5x"),
            ("Interest Coverage", "> 3.0x"),
            ("D&A/CapEx", "< 0.8"),
        ]

        for i, (factor, threshold) in enumerate(factors):
            sem_widget = self._create_semaphore(factor, threshold)
            self.semaphores[factor] = sem_widget
            grid.addWidget(sem_widget)

            if (i + 1) % 5 == 0:
                layout.addLayout(grid)
                grid = QHBoxLayout()

        if grid.count() > 0:
            layout.addLayout(grid)

        layout.addStretch()
        return container

    def _create_semaphore(self, factor: str, threshold: str) -> QWidget:
        """Create a single semaphore indicator."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Colored indicator (initially gray)
        indicator = QLabel("●")
        indicator.setStyleSheet("color: #666; font-size: 24px;")
        indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(indicator)

        # Factor name
        name = QLabel(factor)
        name.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        # Threshold
        thresh = QLabel(threshold)
        thresh.setFont(QFont("Arial", 8))
        thresh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thresh.setStyleSheet("color: #aaa;")
        layout.addWidget(thresh)

        widget.setStyleSheet("""
            QWidget {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
        """)

        # Store reference for updates
        widget._indicator = indicator

        return widget

    def _build_income_statement_tab(self) -> QWidget:
        """Build Income Statement tab."""
        container = QWidget()
        layout = QVBoxLayout(container)

        # Manipulation detection section
        manip_label = QLabel("Manipulation Detection (5 schemes)")
        manip_font = QFont()
        manip_font.setBold(True)
        manip_label.setFont(manip_font)
        layout.addWidget(manip_label)

        self.manip_table = QTableWidget()
        self.manip_table.setColumnCount(4)
        self.manip_table.setHorizontalHeaderLabels([
            "Scheme", "Status", "Signal", "Severity"
        ])
        self.manip_table.setMaximumHeight(150)
        layout.addWidget(self.manip_table)

        # Key metrics
        metrics_label = QLabel("Key Metrics (10 Years)")
        metrics_font = QFont()
        metrics_font.setBold(True)
        metrics_label.setFont(metrics_font)
        layout.addWidget(metrics_label)

        self.income_table = QTableWidget()
        self.income_table.setColumnCount(7)
        self.income_table.setHorizontalHeaderLabels([
            "Year", "Revenue", "EBITDA", "EPS", "OCF", "OCF/NI", "D&A/CapEx"
        ])
        layout.addWidget(self.income_table)

        return container

    def _build_margins_tab(self) -> QWidget:
        """Build Margins tab."""
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("Margin Analysis - 10 Year Trend")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Margin chart
        self.margin_chart = ChartWidget()
        layout.addWidget(self.margin_chart)

        # Margin table
        self.margin_table = QTableWidget()
        self.margin_table.setColumnCount(6)
        self.margin_table.setHorizontalHeaderLabels([
            "Year", "Gross %", "Operating %", "Net %",
            "Vs Sector", "Change"
        ])
        self.margin_table.setMaximumHeight(200)
        layout.addWidget(self.margin_table)

        return container

    def _build_balance_sheet_tab(self) -> QWidget:
        """Build Balance Sheet tab."""
        container = QWidget()
        layout = QVBoxLayout(container)

        # NNWC and Liquidation Value section
        valuation_label = QLabel("Net-Net & Liquidation Analysis")
        valuation_font = QFont()
        valuation_font.setBold(True)
        valuation_label.setFont(valuation_font)
        layout.addWidget(valuation_label)

        # NNWC calculation
        nnwc_layout = QHBoxLayout()
        nnwc_layout.addWidget(QLabel("NNWC Value:"))
        self.nnwc_value = QLabel("$0.00")
        self.nnwc_value.setStyleSheet("font-weight: bold; color: #1e90ff;")
        nnwc_layout.addWidget(self.nnwc_value)

        nnwc_layout.addSpacing(20)
        nnwc_layout.addWidget(QLabel("NNWC/Share:"))
        self.nnwc_per_share = QLabel("$0.00")
        self.nnwc_per_share.setStyleSheet("font-weight: bold; color: #1e90ff;")
        nnwc_layout.addWidget(self.nnwc_per_share)

        nnwc_layout.addStretch()
        layout.addLayout(nnwc_layout)

        # NNWC breakdown table
        self.nnwc_table = QTableWidget()
        self.nnwc_table.setColumnCount(3)
        self.nnwc_table.setHorizontalHeaderLabels(["Item", "Value", "Notes"])
        self.nnwc_table.setMaximumHeight(150)
        layout.addWidget(self.nnwc_table)

        # Debt schedule
        layout.addWidget(QLabel("Debt Maturity Schedule"))
        self.debt_table = QTableWidget()
        self.debt_table.setColumnCount(4)
        self.debt_table.setHorizontalHeaderLabels([
            "Year", "Amount", "Interest Rate", "Status"
        ])
        self.debt_table.setMaximumHeight(150)
        layout.addWidget(self.debt_table)

        # Liquidity ratios
        layout.addWidget(QLabel("Liquidity Ratios"))
        self.liquidity_table = QTableWidget()
        self.liquidity_table.setColumnCount(5)
        self.liquidity_table.setHorizontalHeaderLabels([
            "Metric", "Current", "Industry Avg", "Benchmark", "Status"
        ])
        self.liquidity_table.setMaximumHeight(100)
        layout.addWidget(self.liquidity_table)

        layout.addStretch()
        return container

    def _build_historical_tab(self) -> QWidget:
        """Build Historical tab."""
        container = QWidget()
        layout = QVBoxLayout(container)

        # Recession performance
        layout.addWidget(QLabel("Recession Performance (Last 3 downturns)"))
        self.recession_table = QTableWidget()
        self.recession_table.setColumnCount(5)
        self.recession_table.setHorizontalHeaderLabels([
            "Period", "Start %", "Trough %", "Recovery", "Outperform?"
        ])
        self.recession_table.setMaximumHeight(120)
        layout.addWidget(self.recession_table)

        # Management changes
        layout.addWidget(QLabel("Management Changes (8-K Events)"))
        self.mgmt_table = QTableWidget()
        self.mgmt_table.setColumnCount(4)
        self.mgmt_table.setHorizontalHeaderLabels([
            "Date", "Event", "Position", "Notes"
        ])
        self.mgmt_table.setMaximumHeight(150)
        layout.addWidget(self.mgmt_table)

        # Return metrics
        layout.addWidget(QLabel("Return Metrics (10 Years)"))
        self.returns_table = QTableWidget()
        self.returns_table.setColumnCount(6)
        self.returns_table.setHorizontalHeaderLabels([
            "Year", "ROE %", "ROA %", "ROIC %", "WACC %", "Spread"
        ])
        self.returns_table.setMaximumHeight(200)
        layout.addWidget(self.returns_table)

        layout.addStretch()
        return container

    def _build_comparables_tab(self) -> QWidget:
        """Build Comparables tab."""
        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(QLabel("Peer Comparison (5 Similar Companies)"))

        self.peers_table = QTableWidget()
        self.peers_table.setColumnCount(8)
        self.peers_table.setHorizontalHeaderLabels([
            "Company", "P/E", "P/B", "ROE %", "D/E", "Dividend %",
            "EPS Growth", "Rating"
        ])
        layout.addWidget(self.peers_table)

        # Outlier highlight and valuation vs peers
        summary_label = QLabel("Valuation vs Peers")
        summary_font = QFont()
        summary_font.setBold(True)
        summary_label.setFont(summary_font)
        layout.addWidget(summary_label)

        self.peer_summary = QTextEdit()
        self.peer_summary.setReadOnly(True)
        self.peer_summary.setMaximumHeight(100)
        layout.addWidget(self.peer_summary)

        layout.addStretch()
        return container

    def _build_valuation_tab(self) -> QWidget:
        """Build Valuation tab (Graham Formula, MoS, EPV)."""
        container = QWidget()
        layout = QVBoxLayout(container)

        # Graham Formula section
        graham_title = QLabel("Graham Formula Valuation")
        graham_font = QFont()
        graham_font.setBold(True)
        graham_font.setPointSize(11)
        graham_title.setFont(graham_font)
        layout.addWidget(graham_title)

        self.graham_table = QTableWidget()
        self.graham_table.setColumnCount(3)
        self.graham_table.setHorizontalHeaderLabels([
            "Metric", "Value", "Formula Component"
        ])
        self.graham_table.setMaximumHeight(180)
        layout.addWidget(self.graham_table)

        # Summary valuation metrics
        summary_layout = QHBoxLayout()

        # Intrinsic Value
        summary_layout.addWidget(QLabel("Intrinsic Value:"))
        self.graham_iv = QLabel("$0.00")
        self.graham_iv.setStyleSheet("font-weight: bold; font-size: 14px; color: #00cc00;")
        summary_layout.addWidget(self.graham_iv)

        summary_layout.addSpacing(20)

        # Current Price
        summary_layout.addWidget(QLabel("Current Price:"))
        self.current_price_disp = QLabel("$0.00")
        self.current_price_disp.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self.current_price_disp)

        summary_layout.addSpacing(20)

        # Margin of Safety
        summary_layout.addWidget(QLabel("Margin of Safety:"))
        self.mos_display = QLabel("0.00%")
        self.mos_display.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffaa00;")
        summary_layout.addWidget(self.mos_display)

        summary_layout.addSpacing(20)

        # Decision
        summary_layout.addWidget(QLabel("Decision:"))
        self.decision_display = QLabel("BUY")
        self.decision_display.setStyleSheet("font-weight: bold; font-size: 14px; color: #00cc00;")
        summary_layout.addWidget(self.decision_display)

        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        # Price vs Graham IV chart
        self.valuation_chart = ChartWidget()
        layout.addWidget(self.valuation_chart)

        # Alternative valuation methods
        alt_label = QLabel("Alternative Valuation Methods")
        alt_font = QFont()
        alt_font.setBold(True)
        alt_label.setFont(alt_font)
        layout.addWidget(alt_label)

        self.alt_valuation_table = QTableWidget()
        self.alt_valuation_table.setColumnCount(4)
        self.alt_valuation_table.setHorizontalHeaderLabels([
            "Method", "IV", "MoS %", "Notes"
        ])
        self.alt_valuation_table.setMaximumHeight(120)
        layout.addWidget(self.alt_valuation_table)

        layout.addStretch()
        return container

    def _build_sidebar(self) -> QWidget:
        """Build right sidebar with TradingView chart and AI thesis."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # TradingView chart section
        chart_title = QLabel("Price Chart")
        chart_font = QFont()
        chart_font.setBold(True)
        chart_title.setFont(chart_font)
        layout.addWidget(chart_title)

        # TradingView embed (QWebEngineView)
        self.tradingview_chart = QWebEngineView()
        self.tradingview_chart.setMinimumHeight(200)
        layout.addWidget(self.tradingview_chart)

        # AI Thesis section
        thesis_title = QLabel("AI Thesis Analysis")
        thesis_font = QFont()
        thesis_font.setBold(True)
        thesis_title.setFont(thesis_font)
        layout.addWidget(thesis_title)

        # Generate thesis button
        self.generate_thesis_btn = QPushButton("Generate Thesis")
        self.generate_thesis_btn.clicked.connect(self._on_generate_thesis)
        layout.addWidget(self.generate_thesis_btn)

        # Thesis display
        self.thesis_display = QTextEdit()
        self.thesis_display.setReadOnly(True)
        self.thesis_display.setMaximumHeight(200)
        layout.addWidget(self.thesis_display)

        # AI Chat section
        chat_title = QLabel("AI Chat")
        chat_font = QFont()
        chat_font.setBold(True)
        chat_title.setFont(chat_font)
        layout.addWidget(chat_title)

        self.ai_chat = AIChatWidget()
        layout.addWidget(self.ai_chat)

        return container

    def load_company(self, ticker: str) -> bool:
        """
        Load company data and run all analyses.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if loaded successfully
        """
        ticker = ticker.upper()
        try:
            logger.info(f"Loading company data for {ticker}")

            # TODO: Replace with actual infrastructure call
            # company_data = await get_company_fundamentals(ticker)
            self.company_data = self._get_mock_company_data(ticker)
            self.current_ticker = ticker

            # Update ticker display
            self.ticker_input.setText(ticker)

            # Run all analyses
            self.update_all_tabs()
            self.company_loaded.emit(ticker)
            self.analysis_complete.emit(ticker)

            logger.info(f"Company {ticker} loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load company {ticker}: {e}", exc_info=True)
            return False

    def update_all_tabs(self) -> None:
        """Update all analysis tabs with current company data."""
        try:
            if not self.company_data:
                return

            self._update_screening_tab()
            self._update_income_statement_tab()
            self._update_margins_tab()
            self._update_balance_sheet_tab()
            self._update_historical_tab()
            self._update_comparables_tab()
            self._update_valuation_tab()

        except Exception as e:
            logger.error(f"Failed to update tabs: {e}", exc_info=True)

    def _update_screening_tab(self):
        """Update screening semaphores."""
        data = self.company_data
        checks = {
            "Current Ratio": data.get("current_ratio", 0) > 1.5,
            "Quick Ratio": data.get("quick_ratio", 0) > 1.0,
            "D/E Ratio": data.get("debt_to_equity", 1) < 0.5,
            "OCF/NI": data.get("ocf_ni", 0) > 0.8,
            "ROE": data.get("roe", 0) > 15,
            "ROIC": data.get("roic", 0) > data.get("wacc", 0),
            "EPS Growth": 5 <= data.get("eps_growth", 0) <= 15,
            "Debt/EBITDA": data.get("debt_ebitda", 10) < 2.5,
            "Interest Coverage": data.get("interest_coverage", 0) > 3.0,
            "D&A/CapEx": data.get("da_capex", 1) < 0.8,
        }

        for factor, passed in checks.items():
            if factor in self.semaphores:
                color = "#00cc00" if passed else "#ff3333"
                self.semaphores[factor]._indicator.setStyleSheet(f"color: {color}; font-size: 24px;")

    def _update_income_statement_tab(self):
        """Update income statement data."""
        data = self.company_data

        # Manipulation detection
        manipulations = data.get("manipulation_schemes", {})
        self.manip_table.setRowCount(len(manipulations))
        for row, (scheme, status) in enumerate(manipulations.items()):
            self.manip_table.setItem(row, 0, QTableWidgetItem(scheme))
            self.manip_table.setItem(row, 1, QTableWidgetItem(status.get("status", "OK")))
            self.manip_table.setItem(row, 2, QTableWidgetItem(status.get("signal", "None")))
            self.manip_table.setItem(row, 3, QTableWidgetItem(status.get("severity", "Low")))

        # Historical income statement
        history = data.get("income_history", [])
        self.income_table.setRowCount(len(history))
        for row, year_data in enumerate(history):
            self.income_table.setItem(row, 0, QTableWidgetItem(str(year_data.get("year", ""))))
            self.income_table.setItem(row, 1, QTableWidgetItem(str(year_data.get("revenue", ""))))
            self.income_table.setItem(row, 2, QTableWidgetItem(str(year_data.get("ebitda", ""))))
            self.income_table.setItem(row, 3, QTableWidgetItem(str(year_data.get("eps", ""))))
            self.income_table.setItem(row, 4, QTableWidgetItem(str(year_data.get("ocf", ""))))
            self.income_table.setItem(row, 5, QTableWidgetItem(str(year_data.get("ocf_ni", ""))))
            self.income_table.setItem(row, 6, QTableWidgetItem(str(year_data.get("da_capex", ""))))

    def _update_margins_tab(self):
        """Update margins analysis."""
        data = self.company_data
        margins_history = data.get("margins_history", [])

        self.margin_table.setRowCount(len(margins_history))
        for row, year_data in enumerate(margins_history):
            self.margin_table.setItem(row, 0, QTableWidgetItem(str(year_data.get("year", ""))))
            self.margin_table.setItem(row, 1, QTableWidgetItem(f"{year_data.get('gross_margin', 0):.1f}%"))
            self.margin_table.setItem(row, 2, QTableWidgetItem(f"{year_data.get('operating_margin', 0):.1f}%"))
            self.margin_table.setItem(row, 3, QTableWidgetItem(f"{year_data.get('net_margin', 0):.1f}%"))

            vs_sector = year_data.get("vs_sector", 0)
            vs_color = "#00cc00" if vs_sector > 0 else "#ff3333" if vs_sector < 0 else "#999999"
            vs_item = QTableWidgetItem(f"{vs_sector:+.1f}%")
            vs_item.setForeground(QBrush(QColor(vs_color)))
            self.margin_table.setItem(row, 4, vs_item)

            change = year_data.get("change", 0)
            arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
            self.margin_table.setItem(row, 5, QTableWidgetItem(f"{arrow} {abs(change):.1f}%"))

    def _update_balance_sheet_tab(self):
        """Update balance sheet analysis."""
        data = self.company_data

        # NNWC values
        self.nnwc_value.setText(data.get("nnwc_value", "$0.00"))
        self.nnwc_per_share.setText(data.get("nnwc_per_share", "$0.00"))

        # NNWC breakdown
        nnwc_items = data.get("nnwc_breakdown", [])
        self.nnwc_table.setRowCount(len(nnwc_items))
        for row, item in enumerate(nnwc_items):
            self.nnwc_table.setItem(row, 0, QTableWidgetItem(item.get("item", "")))
            self.nnwc_table.setItem(row, 1, QTableWidgetItem(item.get("value", "")))
            self.nnwc_table.setItem(row, 2, QTableWidgetItem(item.get("notes", "")))

        # Debt schedule
        debt_schedule = data.get("debt_schedule", [])
        self.debt_table.setRowCount(len(debt_schedule))
        for row, debt_item in enumerate(debt_schedule):
            self.debt_table.setItem(row, 0, QTableWidgetItem(str(debt_item.get("year", ""))))
            self.debt_table.setItem(row, 1, QTableWidgetItem(str(debt_item.get("amount", ""))))
            self.debt_table.setItem(row, 2, QTableWidgetItem(str(debt_item.get("rate", ""))))
            self.debt_table.setItem(row, 3, QTableWidgetItem(str(debt_item.get("status", ""))))

        # Liquidity ratios
        liquidity_metrics = data.get("liquidity_metrics", [])
        self.liquidity_table.setRowCount(len(liquidity_metrics))
        for row, metric in enumerate(liquidity_metrics):
            self.liquidity_table.setItem(row, 0, QTableWidgetItem(metric.get("metric", "")))
            self.liquidity_table.setItem(row, 1, QTableWidgetItem(str(metric.get("current", ""))))
            self.liquidity_table.setItem(row, 2, QTableWidgetItem(str(metric.get("industry_avg", ""))))
            self.liquidity_table.setItem(row, 3, QTableWidgetItem(str(metric.get("benchmark", ""))))

            status = metric.get("status", "NEUTRAL")
            status_color = "#00cc00" if status == "PASS" else "#ff3333" if status == "FAIL" else "#ffaa00"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(QColor(status_color)))
            self.liquidity_table.setItem(row, 4, status_item)

    def _update_historical_tab(self):
        """Update historical analysis."""
        data = self.company_data

        # Recession performance
        recessions = data.get("recession_performance", [])
        self.recession_table.setRowCount(len(recessions))
        for row, rec in enumerate(recessions):
            self.recession_table.setItem(row, 0, QTableWidgetItem(rec.get("period", "")))
            self.recession_table.setItem(row, 1, QTableWidgetItem(rec.get("start", "")))
            self.recession_table.setItem(row, 2, QTableWidgetItem(rec.get("trough", "")))
            self.recession_table.setItem(row, 3, QTableWidgetItem(rec.get("recovery", "")))

            outperform = rec.get("outperform", False)
            outperform_color = "#00cc00" if outperform else "#ff3333"
            outperform_item = QTableWidgetItem("YES" if outperform else "NO")
            outperform_item.setForeground(QBrush(QColor(outperform_color)))
            self.recession_table.setItem(row, 4, outperform_item)

        # Management changes
        mgmt_events = data.get("management_events", [])
        self.mgmt_table.setRowCount(len(mgmt_events))
        for row, event in enumerate(mgmt_events):
            self.mgmt_table.setItem(row, 0, QTableWidgetItem(event.get("date", "")))
            self.mgmt_table.setItem(row, 1, QTableWidgetItem(event.get("event", "")))
            self.mgmt_table.setItem(row, 2, QTableWidgetItem(event.get("position", "")))
            self.mgmt_table.setItem(row, 3, QTableWidgetItem(event.get("notes", "")))

        # Return metrics
        returns = data.get("return_metrics", [])
        self.returns_table.setRowCount(len(returns))
        for row, ret in enumerate(returns):
            self.returns_table.setItem(row, 0, QTableWidgetItem(str(ret.get("year", ""))))
            self.returns_table.setItem(row, 1, QTableWidgetItem(f"{ret.get('roe', 0):.1f}%"))
            self.returns_table.setItem(row, 2, QTableWidgetItem(f"{ret.get('roa', 0):.1f}%"))
            self.returns_table.setItem(row, 3, QTableWidgetItem(f"{ret.get('roic', 0):.1f}%"))
            self.returns_table.setItem(row, 4, QTableWidgetItem(f"{ret.get('wacc', 0):.1f}%"))

            spread = ret.get("roic", 0) - ret.get("wacc", 0)
            spread_color = "#00cc00" if spread > 0 else "#ff3333"
            spread_item = QTableWidgetItem(f"{spread:+.1f}%")
            spread_item.setForeground(QBrush(QColor(spread_color)))
            self.returns_table.setItem(row, 5, spread_item)

    def _update_comparables_tab(self):
        """Update peer comparison."""
        peers = self.company_data.get("peers", [])
        self.peers_table.setRowCount(len(peers))

        # Calculate peer averages for comparison
        if peers:
            pe_values = [float(p.get("pe", "0")) for p in peers]
            pe_avg = sum(pe_values) / len(pe_values) if pe_values else 0

        for row, peer in enumerate(peers):
            ticker_item = QTableWidgetItem(peer.get("name", ""))
            self.peers_table.setItem(row, 0, ticker_item)

            # P/E with color coding
            pe = float(peer.get("pe", "0"))
            pe_item = QTableWidgetItem(str(peer.get("pe", "")))
            pe_color = "#00cc00" if pe < pe_avg else "#ff3333" if pe > pe_avg else "#ffaa00"
            pe_item.setForeground(QBrush(QColor(pe_color)))
            self.peers_table.setItem(row, 1, pe_item)

            self.peers_table.setItem(row, 2, QTableWidgetItem(str(peer.get("pb", ""))))

            # ROE with color
            roe = str(peer.get("roe", "")).rstrip("%")
            roe_item = QTableWidgetItem(peer.get("roe", ""))
            roe_color = "#00cc00" if float(roe) > 15 else "#ffaa00" if float(roe) > 10 else "#ff3333"
            roe_item.setForeground(QBrush(QColor(roe_color)))
            self.peers_table.setItem(row, 3, roe_item)

            self.peers_table.setItem(row, 4, QTableWidgetItem(str(peer.get("de", ""))))
            self.peers_table.setItem(row, 5, QTableWidgetItem(str(peer.get("div_yield", ""))))
            self.peers_table.setItem(row, 6, QTableWidgetItem(str(peer.get("eps_growth", ""))))

            rating = peer.get("rating", "")
            rating_item = QTableWidgetItem(rating)
            rating_color = "#00cc00" if rating == "BUY" else "#ffaa00" if rating == "HOLD" else "#ff3333"
            rating_item.setForeground(QBrush(QColor(rating_color)))
            self.peers_table.setItem(row, 7, rating_item)

        # Update summary text
        if peers:
            summary_text = self._generate_peer_summary(peers)
            self.peer_summary.setText(summary_text)

    def _generate_peer_summary(self, peers: List[Dict]) -> str:
        """Generate summary commentary comparing company to peers."""
        if not peers:
            return "No peer data available."

        pe_values = [float(p.get("pe", "0")) for p in peers]
        avg_pe = sum(pe_values) / len(pe_values)
        company_pe = pe_values[0] if pe_values else 0

        summary = f"Peer Analysis:\n"
        summary += f"Avg P/E: {avg_pe:.1f}x\n"

        if company_pe < avg_pe * 0.9:
            summary += f"✓ CHEAPER than peers (by {((avg_pe - company_pe) / avg_pe * 100):.1f}%)\n"
            summary += "Potential value opportunity."
        elif company_pe > avg_pe * 1.1:
            summary += f"✗ PRICIER than peers (by {((company_pe - avg_pe) / avg_pe * 100):.1f}%)\n"
            summary += "May be overvalued relative to peers."
        else:
            summary += "≈ FAIRLY PRICED vs peers"

        # Count BUY ratings
        buy_count = sum(1 for p in peers if p.get("rating") == "BUY")
        summary += f"\n\nBUY Ratings: {buy_count}/{len(peers)} peers"

        return summary

    def _update_valuation_tab(self):
        """Update valuation analysis."""
        data = self.company_data

        # Graham formula metrics
        self.graham_iv.setText(data.get("graham_iv", "$0.00"))
        self.current_price_disp.setText(data.get("current_price", "$0.00"))
        self.mos_display.setText(data.get("margin_of_safety", "0.00%"))

        # Decision color coding
        decision = data.get("decision", "HOLD")
        decision_color = "#00cc00" if decision == "BUY" else "#ffaa00" if decision == "HOLD" else "#ff3333"
        self.decision_display.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {decision_color};")
        self.decision_display.setText(decision)

        # Graham table
        graham_components = data.get("graham_components", {})
        self.graham_table.setRowCount(len(graham_components))
        for row, (metric, value) in enumerate(graham_components.items()):
            self.graham_table.setItem(row, 0, QTableWidgetItem(metric))
            self.graham_table.setItem(row, 1, QTableWidgetItem(str(value)))

        # Alternative valuation methods
        alt_methods = data.get("alternative_valuations", [])
        self.alt_valuation_table.setRowCount(len(alt_methods))
        for row, method in enumerate(alt_methods):
            self.alt_valuation_table.setItem(row, 0, QTableWidgetItem(method.get("method", "")))
            self.alt_valuation_table.setItem(row, 1, QTableWidgetItem(method.get("iv", "")))

            mos = float(method.get("mos", "0").rstrip("%")) if method.get("mos") else 0
            mos_color = "#00cc00" if mos > 0 else "#ff3333"
            mos_item = QTableWidgetItem(method.get("mos", "0%"))
            mos_item.setForeground(QBrush(QColor(mos_color)))
            self.alt_valuation_table.setItem(row, 2, mos_item)

            self.alt_valuation_table.setItem(row, 3, QTableWidgetItem(method.get("notes", "")))

    def _calculate_graham_valuation(self, fundamentals: Dict) -> Dict:
        """
        Calculate Graham-Dodd intrinsic value with quality adjustment.

        Args:
            fundamentals: Dict with eps, growth_rate, risk_free_rate, etc.

        Returns:
            Dict with IV, margin of safety, decision
        """
        try:
            eps = fundamentals.get("eps", 0)
            growth = fundamentals.get("growth_rate", 8.0)
            rf_rate = fundamentals.get("risk_free_rate", 4.5)

            # Calculate quality score (0-100)
            q_score = quality_score(
                current_ratio=fundamentals.get("current_ratio", 1.5),
                ocf_to_ni=fundamentals.get("ocf_ni", 1.0),
                debt_to_equity=fundamentals.get("debt_to_equity", 0.5),
                dividend_coverage=fundamentals.get("dividend_coverage", 2.0),
                earnings_growth=growth / 100.0,
                margin_stability=fundamentals.get("margin_stability", 0.08),
                roe=fundamentals.get("roe", 0.15) / 100.0,
                tax_burden=fundamentals.get("tax_rate", 0.25),
                asset_turnover=fundamentals.get("asset_turnover", 1.0),
                valuation_gap=fundamentals.get("valuation_gap", -0.1),
            )

            # Calculate Graham IV
            iv = graham_formula(eps=eps, growth_rate=growth, risk_free_rate=rf_rate, quality_score=q_score)

            # Calculate alternative valuations
            current_assets = fundamentals.get("current_assets", 0)
            total_liabilities = fundamentals.get("total_liabilities", 0)
            inventory = fundamentals.get("inventory", 0)
            fixed_assets = fundamentals.get("fixed_assets", 0)
            shares_outstanding = fundamentals.get("shares_outstanding", 1)

            nnwc_value = nnwc(current_assets, total_liabilities)
            nnwc_per_share = nnwc_value / shares_outstanding if shares_outstanding > 0 else 0

            liq_value = liquidation_value(
                current_assets=current_assets,
                inventory=inventory,
                fixed_assets=fixed_assets,
                total_liabilities=total_liabilities,
            )
            liq_per_share = liq_value / shares_outstanding if shares_outstanding > 0 else 0

            current_price = fundamentals.get("current_price", iv * 0.9)
            mos = ((iv - current_price) / iv * 100) if iv > 0 else 0

            # Decision logic
            if current_price < iv * 0.70:
                decision = "BUY"
            elif current_price < iv:
                decision = "HOLD"
            else:
                decision = "AVOID"

            return {
                "graham_iv": iv,
                "nnwc_per_share": nnwc_per_share,
                "liquidation_per_share": liq_per_share,
                "current_price": current_price,
                "margin_of_safety": mos,
                "quality_score": q_score,
                "decision": decision,
            }

        except Exception as e:
            logger.error(f"Graham valuation calculation failed: {e}", exc_info=True)
            return {}

    def _detect_manipulation_flags(self, financials: Dict) -> List[Tuple[str, bool]]:
        """
        Detect Graham-Dodd red flags from financial statements.

        Args:
            financials: Financial metrics dict

        Returns:
            List of (flag_name, is_flagged) tuples
        """
        try:
            flags = detect_manipulation(
                ocf=financials.get("ocf", 0),
                net_income=financials.get("net_income", 0),
                depreciation=financials.get("depreciation", 0),
                capex=financials.get("capex", 0),
                equity_delta=financials.get("equity_delta", 0),
                ni_less_dividends=financials.get("ni_less_dividends", 0),
            )
            return [(k, v) for k, v in flags.items()]
        except Exception as e:
            logger.error(f"Manipulation detection failed: {e}", exc_info=True)
            return []

    def _on_ticker_entered(self):
        """Handle ticker input enter key."""
        self._on_load_company()

    def _on_load_company(self):
        """Handle load company button click."""
        ticker = self.ticker_input.text().strip()
        if ticker:
            self.load_company(ticker)

    def _on_generate_thesis(self):
        """Handle generate thesis button click."""
        if not self.current_ticker:
            logger.warning("No company loaded")
            return

        try:
            # TODO: Call AI gateway asynchronously
            # thesis = await ai_gateway.generate_thesis(self.current_ticker, company_data)
            thesis = self._get_mock_thesis()
            self.thesis_display.setText(thesis)
            self.ai_thesis_generated.emit(self.current_ticker, thesis)
            logger.info(f"Thesis generated for {self.current_ticker}")
        except Exception as e:
            logger.error(f"Failed to generate thesis: {e}", exc_info=True)

    def setup_connections(self):
        """Set up signal/slot connections."""
        pass

    @staticmethod
    def _get_mock_company_data(ticker: str) -> Dict:
        """Return mock company data for MVP."""
        return {
            "ticker": ticker,
            "current_price": "$195.42",
            "graham_iv": "$220.50",
            "margin_of_safety": "12.8%",
            "decision": "BUY",
            "current_ratio": 2.1,
            "quick_ratio": 1.8,
            "debt_to_equity": 0.35,
            "ocf_ni": 1.05,
            "roe": 22.5,
            "roic": 18.3,
            "wacc": 6.2,
            "eps_growth": 10.2,
            "debt_ebitda": 1.8,
            "interest_coverage": 8.5,
            "da_capex": 0.65,
            "nnwc_value": "$450M",
            "nnwc_per_share": "$28.50",
            "manipulation_schemes": {
                "OCF/NI Divergence": {"status": "OK", "signal": "None", "severity": "Low"},
                "D&A/CapEx Ratio": {"status": "OK", "signal": "None", "severity": "Low"},
                "Hidden Liabilities": {"status": "OK", "signal": "None", "severity": "Low"},
                "Revenue Recognition": {"status": "OK", "signal": "None", "severity": "Low"},
                "Working Capital": {"status": "OK", "signal": "None", "severity": "Low"},
            },
            "income_history": [
                {"year": 2023, "revenue": "383.3B", "ebitda": "122.2B", "eps": "6.05", "ocf": "121.1B", "ocf_ni": 1.02, "da_capex": 0.65},
                {"year": 2022, "revenue": "394.3B", "ebitda": "123.5B", "eps": "5.61", "ocf": "122.2B", "ocf_ni": 1.03, "da_capex": 0.64},
                {"year": 2021, "revenue": "365.8B", "ebitda": "119.4B", "eps": "5.29", "ocf": "110.5B", "ocf_ni": 1.04, "da_capex": 0.63},
            ],
            "margins_history": [
                {"year": 2023, "gross_margin": 46.2, "operating_margin": 32.0, "net_margin": 25.3, "vs_sector": 3.5, "change": 0.8},
                {"year": 2022, "gross_margin": 45.8, "operating_margin": 31.2, "net_margin": 24.7, "vs_sector": 2.8, "change": -0.3},
                {"year": 2021, "gross_margin": 46.0, "operating_margin": 31.5, "net_margin": 25.0, "vs_sector": 3.2, "change": 0.5},
            ],
            "debt_schedule": [
                {"year": 2024, "amount": "$25B", "rate": "3.2%", "status": "Active"},
                {"year": 2025, "amount": "$35B", "rate": "3.5%", "status": "Active"},
                {"year": 2027, "amount": "$15B", "rate": "2.8%", "status": "Active"},
            ],
            "nnwc_breakdown": [
                {"item": "Current Assets", "value": "$62.2B", "notes": "Cash, AR, Inventory"},
                {"item": "Current Liabilities", "value": "$28.4B", "notes": "Accounts payable, short-term debt"},
                {"item": "NNWC Value", "value": "$33.8B", "notes": "Conservative liquidation estimate"},
            ],
            "liquidity_metrics": [
                {"metric": "Current Ratio", "current": "2.19", "industry_avg": "1.65", "benchmark": "1.50", "status": "PASS"},
                {"metric": "Quick Ratio", "current": "1.82", "industry_avg": "1.25", "benchmark": "1.00", "status": "PASS"},
                {"metric": "Cash Ratio", "current": "0.95", "industry_avg": "0.55", "benchmark": "0.30", "status": "PASS"},
            ],
            "recession_performance": [
                {"period": "2008-2009 GFC", "start": "-28.5%", "trough": "-61.2%", "recovery": "18 months", "outperform": True},
                {"period": "2020 COVID", "start": "-12.3%", "trough": "-25.8%", "recovery": "4 months", "outperform": True},
                {"period": "2022 Tech Selloff", "start": "-18.2%", "trough": "-32.5%", "recovery": "8 months", "outperform": True},
            ],
            "management_events": [
                {"date": "2023-01-15", "event": "CEO Succession", "position": "Chief Executive Officer", "notes": "Smooth transition, internal candidate"},
                {"date": "2022-06-30", "event": "CFO Change", "position": "Chief Financial Officer", "notes": "Promoted from VP Finance"},
            ],
            "return_metrics": [
                {"year": 2023, "roe": 22.5, "roa": 16.2, "roic": 18.3, "wacc": 6.2},
                {"year": 2022, "roe": 21.8, "roa": 15.9, "roic": 17.8, "wacc": 5.8},
                {"year": 2021, "roe": 21.2, "roa": 15.5, "roic": 17.2, "wacc": 5.2},
            ],
            "peers": [
                {"name": "Microsoft", "pe": "32.1", "pb": "11.2", "roe": "45.2%", "de": "0.42", "div_yield": "0.8%", "eps_growth": "11.2%", "rating": "BUY"},
                {"name": "Google", "pe": "24.5", "pb": "6.8", "roe": "19.8%", "de": "0.08", "div_yield": "0.0%", "eps_growth": "8.5%", "rating": "BUY"},
                {"name": "Amazon", "pe": "40.2", "pb": "3.2", "roe": "8.5%", "de": "0.95", "div_yield": "0.0%", "eps_growth": "15.3%", "rating": "HOLD"},
                {"name": "Meta", "pe": "28.5", "pb": "8.9", "roe": "12.4%", "de": "0.15", "div_yield": "0.0%", "eps_growth": "12.8%", "rating": "BUY"},
                {"name": "Nvidia", "pe": "48.3", "pb": "15.2", "roe": "62.1%", "de": "0.22", "div_yield": "0.1%", "eps_growth": "89.5%", "rating": "BUY"},
            ],
            "graham_components": {
                "EPS (normalized)": "$6.05",
                "Growth Rate": "10.2%",
                "Risk-Free Rate": "4.5%",
                "Quality Score": "82/100",
                "IV Formula": "$220.50",
            },
            "alternative_valuations": [
                {"method": "Graham Number", "iv": "$185.32", "mos": "-5.2%", "notes": "Conservative floor valuation"},
                {"method": "NNWC Value", "iv": "$28.50", "mos": "-85.4%", "notes": "Per share, deep value metric"},
                {"method": "Liquidation Value", "iv": "$42.18", "mos": "-78.4%", "notes": "Most conservative estimate"},
                {"method": "P/E Adjusted", "iv": "$212.50", "mos": "+8.8%", "notes": "Sector-adjusted multiple"},
            ],
        }

    @staticmethod
    def _get_mock_thesis() -> str:
        """Return mock AI thesis for MVP."""
        return """Apple Inc. (AAPL) - Investment Thesis

STRENGTHS:
• Exceptional brand moat with premium pricing power
• Strong FCF generation ($121B OCF in 2023)
• Solid balance sheet (CR 2.1, D/E 0.35)
• Consistent earnings growth (CAGR ~10%)

CONCERNS:
• Valuation near upper range (P/E 32.1)
• iPhone revenue concentration (~52%)
• Regulatory risks in App Store monetization
• Mature market growth limits

VALUATION:
Graham IV: $220.50 | Current: $195.42 | MoS: 12.8%
The margin of safety is reasonable for a quality company.

RATING: BUY (accumulate on weakness)
Target: $240-260 (12-18 month horizon)
"""


# Module-level exports
__all__ = ["AnalyzerPanel"]
