"""
Investment Thesis Panel - Create, Track, and Analyze Investment Theses.

Comprehensive thesis management system with:
- New thesis creation with embeddings storage
- Automatic thesis scoring (0-100)
- Real-time tracking of active theses
- Semantic search across historical theses (RAG)
- Historical performance analysis
- AI-powered thesis analysis and improvement

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: Investment Thesis Module
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QMessageBox, QProgressBar, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QBrush, QIcon

from quantum_terminal.ui.widgets import DataTable, AlertBanner, MetricCard
from quantum_terminal.ui.dialogs.new_thesis_dialog import NewThesisDialog, ThesisData
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.cache import cache

logger = get_logger(__name__)


# ============================================================================
# Thread for async operations (embeddings, RAG, AI analysis)
# ============================================================================

class ThesisWorkerThread(QThread):
    """Background thread for thesis operations (embeddings, RAG, AI)."""

    operation_complete = pyqtSignal(dict)  # {"operation": str, "result": Any}
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, operation: str, **kwargs):
        """
        Initialize worker thread.

        Args:
            operation: Operation type (embed, rag_search, ai_analyze, score)
            **kwargs: Operation-specific parameters
        """
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs

    def run(self):
        """Execute the background operation."""
        try:
            if self.operation == "embed":
                result = self._embed_thesis()
            elif self.operation == "rag_search":
                result = self._rag_search()
            elif self.operation == "ai_analyze":
                result = self._ai_analyze()
            elif self.operation == "score":
                result = self._score_thesis()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")

            self.operation_complete.emit({
                "operation": self.operation,
                "result": result
            })
        except Exception as e:
            logger.error(f"Worker error ({self.operation}): {e}", exc_info=True)
            self.error_occurred.emit(str(e))

    def _embed_thesis(self) -> Dict:
        """Generate embedding for thesis text."""
        try:
            # Mock implementation - in production, use sentence-transformers
            thesis_text = self.kwargs.get("text", "")
            # TODO: Replace with actual embedding using sentence-transformers
            embedding = [0.1 * (i % 10) for i in range(384)]  # 384-dim mock vector

            return {
                "embedding": embedding,
                "ticker": self.kwargs.get("ticker"),
                "text_len": len(thesis_text)
            }
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def _rag_search(self) -> List[Dict]:
        """Search for similar theses using RAG."""
        try:
            # Mock implementation - in production, use ChromaDB
            query = self.kwargs.get("query", "")
            top_k = self.kwargs.get("top_k", 5)

            # TODO: Replace with actual ChromaDB search
            similar = [
                {
                    "ticker": "MOCK",
                    "similarity": 0.85 - (i * 0.1),
                    "thesis": f"Mock thesis {i+1}",
                    "date": datetime.now().isoformat()
                }
                for i in range(min(top_k, 3))
            ]

            return similar
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            raise

    def _ai_analyze(self) -> Dict:
        """Analyze thesis using AI gateway."""
        try:
            # Mock implementation - in production, use ai_gateway.generate()
            thesis_text = self.kwargs.get("text", "")

            # TODO: Replace with actual ai_gateway.generate()
            analysis = {
                "strengths": ["Strong fundamental case", "Clear catalysts"],
                "weaknesses": ["High valuation", "Competitive pressure"],
                "suggested_price_target": 125.50,
                "confidence": 0.75
            }

            return analysis
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            raise

    def _score_thesis(self) -> Dict:
        """Calculate thesis score using domain scorer."""
        try:
            # Mock implementation - in production, use domain.thesis_scorer
            ticker = self.kwargs.get("ticker")
            eps = self.kwargs.get("eps", 5.0)
            growth = self.kwargs.get("growth", 15.0)

            # TODO: Replace with actual thesis_scorer logic
            score = min(100, max(0, 50 + (growth / 2) - (eps * 2)))

            strength = "STRONG" if score > 75 else "MODERATE" if score > 50 else "WEAK"

            return {
                "score": round(score, 2),
                "strength": strength,
                "factors": {
                    "valuation": 65,
                    "catalysts": 70,
                    "risks": 55,
                    "margin_of_safety": 60
                }
            }
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            raise


# ============================================================================
# Main Thesis Panel
# ============================================================================

class ThesisPanel(QWidget):
    """
    Complete investment thesis management panel.

    Features:
    - Create new theses with embeddings
    - Automatic scoring (0-100)
    - Real-time tracking of active theses
    - RAG semantic search
    - Historical performance analysis
    - AI-powered analysis

    Signals:
        thesis_created: Emitted when new thesis is created
        thesis_updated: Emitted when thesis is updated
    """

    thesis_created = pyqtSignal(str)  # thesis_id
    thesis_updated = pyqtSignal(str)  # thesis_id

    def __init__(self, parent=None):
        """Initialize Thesis Panel."""
        super().__init__(parent)
        self.setWindowTitle("Investment Thesis Manager")

        # State
        self.current_theses: Dict[str, Dict] = {}  # {thesis_id: thesis_data}
        self.historical_theses: List[Dict] = []
        self.worker_thread: Optional[ThesisWorkerThread] = None

        # Initialize UI
        self.initUI()
        self.setup_connections()

    def initUI(self) -> None:
        """Initialize UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title bar
        title_layout = QHBoxLayout()
        title_label = QLabel("Investment Thesis Manager")
        title_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))

        new_thesis_btn = QPushButton("+ New Thesis")
        new_thesis_btn.setProperty("accent", True)
        new_thesis_btn.setFixedSize(120, 36)
        new_thesis_btn.clicked.connect(self.show_new_thesis_dialog)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(new_thesis_btn)
        main_layout.addLayout(title_layout)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Inter", 10))

        # Tab 1: Active Theses
        self.tab_active = self.create_active_theses_tab()
        self.tabs.addTab(self.tab_active, "Active Theses")

        # Tab 2: Semantic Search (RAG)
        self.tab_rag = self.create_rag_search_tab()
        self.tabs.addTab(self.tab_rag, "Search Theses")

        # Tab 3: Historical Performance
        self.tab_history = self.create_historical_tab()
        self.tabs.addTab(self.tab_history, "Historical Performance")

        # Tab 4: AI Analysis
        self.tab_ai = self.create_ai_analysis_tab()
        self.tabs.addTab(self.tab_ai, "AI Analysis")

        main_layout.addWidget(self.tabs)

        self.setLayout(main_layout)

    def create_active_theses_tab(self) -> QWidget:
        """Create 'Active Theses' tab with real-time tracking."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Metrics row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.metric_count = MetricCard("Total Theses", "0")
        self.metric_active = MetricCard("Active", "0")
        self.metric_avg_score = MetricCard("Avg Score", "0")
        self.metric_hit_rate = MetricCard("Hit Rate", "0%")

        metrics_layout.addWidget(self.metric_count)
        metrics_layout.addWidget(self.metric_active)
        metrics_layout.addWidget(self.metric_avg_score)
        metrics_layout.addWidget(self.metric_hit_rate)
        metrics_layout.addStretch()

        layout.addLayout(metrics_layout)

        # Table of active theses
        columns = [
            "Ticker", "Thesis (Summary)", "Entry Price", "Current Price",
            "% to Target", "Status", "Score", "Days Left", "Actions"
        ]
        self.table_active = DataTable(columns, enable_filter=True)
        self.table_active.row_selected.connect(self.on_thesis_selected)
        layout.addWidget(self.table_active)

        # Detail panel (collapsed by default)
        self.detail_panel = self.create_thesis_detail_panel()
        layout.addWidget(self.detail_panel)

        return widget

    def create_thesis_detail_panel(self) -> QGroupBox:
        """Create collapsible detail panel for selected thesis."""
        group = QGroupBox("Thesis Details")
        group.setCheckable(True)
        group.setChecked(False)
        layout = QVBoxLayout()

        # Form with thesis details
        form = QFormLayout()

        self.detail_ticker = QLineEdit()
        self.detail_ticker.setReadOnly(True)
        form.addRow("Ticker:", self.detail_ticker)

        self.detail_thesis = QTextEdit()
        self.detail_thesis.setReadOnly(True)
        self.detail_thesis.setMaximumHeight(80)
        form.addRow("Thesis:", self.detail_thesis)

        self.detail_catalysts = QTextEdit()
        self.detail_catalysts.setReadOnly(True)
        self.detail_catalysts.setMaximumHeight(60)
        form.addRow("Catalysts:", self.detail_catalysts)

        self.detail_risks = QTextEdit()
        self.detail_risks.setReadOnly(True)
        self.detail_risks.setMaximumHeight(60)
        form.addRow("Risks:", self.detail_risks)

        # Score breakdown
        score_layout = QHBoxLayout()
        self.detail_score = MetricCard("Overall Score", "0")
        self.detail_strength = MetricCard("Strength", "N/A")
        score_layout.addWidget(self.detail_score)
        score_layout.addWidget(self.detail_strength)
        score_layout.addStretch()
        form.addRow("Scoring:", score_layout)

        # Buttons
        button_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_selected_thesis)
        close_btn = QPushButton("Close Thesis")
        close_btn.clicked.connect(self.close_selected_thesis)
        ai_btn = QPushButton("AI Analysis")
        ai_btn.clicked.connect(self.analyze_selected_thesis)

        button_layout.addWidget(edit_btn)
        button_layout.addWidget(close_btn)
        button_layout.addWidget(ai_btn)
        button_layout.addStretch()

        layout.addLayout(form)
        layout.addLayout(button_layout)
        group.setLayout(layout)

        return group

    def create_rag_search_tab(self) -> QWidget:
        """Create semantic search tab using RAG."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Search input
        search_layout = QHBoxLayout()

        search_label = QLabel("Find Similar Theses:")
        search_label.setFont(QFont("Inter", 10))

        self.rag_query = QLineEdit()
        self.rag_query.setPlaceholderText(
            'e.g., "Value theses with M&A catalysts" or "Turnaround situations"'
        )
        self.rag_query.setMinimumHeight(36)

        search_btn = QPushButton("Search")
        search_btn.setFixedSize(100, 36)
        search_btn.setProperty("accent", True)
        search_btn.clicked.connect(self.rag_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.rag_query)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Progress bar
        self.rag_progress = QProgressBar()
        self.rag_progress.setVisible(False)
        layout.addWidget(self.rag_progress)

        # Results table
        columns = ["Ticker", "Similarity", "Thesis Summary", "Date Created", "Status"]
        self.table_rag_results = DataTable(columns, enable_filter=False)
        self.table_rag_results.row_selected.connect(self.on_rag_result_selected)
        layout.addWidget(self.table_rag_results)

        # Result detail
        self.rag_detail_text = QTextEdit()
        self.rag_detail_text.setReadOnly(True)
        self.rag_detail_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Selected Result:"))
        layout.addWidget(self.rag_detail_text)

        return widget

    def create_historical_tab(self) -> QWidget:
        """Create historical performance analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Summary stats
        stats_layout = QHBoxLayout()
        self.stat_total = MetricCard("Total Closed", "0")
        self.stat_winners = MetricCard("Winners", "0")
        self.stat_losers = MetricCard("Losers", "0")
        self.stat_win_rate = MetricCard("Win Rate", "0%")
        self.stat_avg_return = MetricCard("Avg Return", "0%")

        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_winners)
        stats_layout.addWidget(self.stat_losers)
        stats_layout.addWidget(self.stat_win_rate)
        stats_layout.addWidget(self.stat_avg_return)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Type breakdown
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Performance by Type:"))
        for thesis_type in ["Value", "Growth", "Income", "Turnaround", "Special"]:
            metric = MetricCard(thesis_type, "0%")
            type_layout.addWidget(metric)
        type_layout.addStretch()

        layout.addLayout(type_layout)

        # Historical table
        columns = [
            "Ticker", "Type", "Entry Date", "Exit Date", "Entry Price",
            "Exit Price", "Return %", "Thesis Summary", "Outcome"
        ]
        self.table_history = DataTable(columns, enable_filter=True)
        self.table_history.row_selected.connect(self.on_history_selected)
        layout.addWidget(self.table_history)

        # Lessons learned
        self.history_lessons = QTextEdit()
        self.history_lessons.setReadOnly(True)
        self.history_lessons.setMaximumHeight(120)
        layout.addWidget(QLabel("Lessons Learned:"))
        layout.addWidget(self.history_lessons)

        return widget

    def create_ai_analysis_tab(self) -> QWidget:
        """Create AI thesis analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Instructions
        instructions = QLabel(
            "Select a thesis above and analyze it using AI. "
            "AI will evaluate strengths, risks, and suggest improvements."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Input form
        form = QFormLayout()

        self.ai_ticker = QLineEdit()
        self.ai_ticker.setPlaceholderText("AAPL")
        form.addRow("Ticker:", self.ai_ticker)

        self.ai_thesis = QTextEdit()
        self.ai_thesis.setPlaceholderText("Paste your investment thesis here...")
        self.ai_thesis.setMinimumHeight(100)
        form.addRow("Thesis:", self.ai_thesis)

        # AI analysis type
        ai_type_layout = QHBoxLayout()
        self.ai_type = QComboBox()
        self.ai_type.addItems([
            "Auto (Fast analysis)",
            "Deep reasoning",
            "Valuation focus",
            "Risk assessment"
        ])
        ai_type_layout.addWidget(QLabel("Analysis Type:"))
        ai_type_layout.addWidget(self.ai_type)
        ai_type_layout.addStretch()
        form.addRow("", ai_type_layout)

        layout.addLayout(form)

        # Analyze button
        analyze_btn = QPushButton("Analyze with AI")
        analyze_btn.setProperty("accent", True)
        analyze_btn.setFixedHeight(40)
        analyze_btn.clicked.connect(self.analyze_thesis_ai)
        layout.addWidget(analyze_btn)

        # Progress
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        layout.addWidget(self.ai_progress)

        # Results
        self.ai_results = QTextEdit()
        self.ai_results.setReadOnly(True)
        layout.addWidget(QLabel("Analysis Results:"))
        layout.addWidget(self.ai_results)

        # Export button
        export_btn = QPushButton("Export Analysis")
        export_btn.clicked.connect(self.export_ai_analysis)
        layout.addWidget(export_btn)

        layout.addStretch()

        return widget

    def setup_connections(self) -> None:
        """Setup signal-slot connections."""
        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_active_theses)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def show_new_thesis_dialog(self) -> None:
        """Show dialog to create new thesis."""
        dialog = NewThesisDialog(self)
        if dialog.exec() == dialog.Accepted:
            thesis_data = dialog.get_thesis_data()
            if thesis_data:
                self.create_thesis_from_data(thesis_data)

    def create_thesis_from_data(self, thesis_data: ThesisData) -> None:
        """
        Create thesis from dialog data.

        Args:
            thesis_data: ThesisData object from dialog
        """
        try:
            # Combine thesis text
            thesis_text = f"{thesis_data.thesis_text}\n\nCatalysts: {thesis_data.catalysts_short_term}\n\nRisks: {thesis_data.risks}"

            # Generate embedding (async)
            thesis_id = f"{thesis_data.ticker}_{datetime.now().timestamp()}"

            self.worker_thread = ThesisWorkerThread(
                "embed",
                ticker=thesis_data.ticker,
                text=thesis_text
            )
            self.worker_thread.operation_complete.connect(
                lambda result: self._on_embedding_complete(thesis_id, thesis_data, result)
            )
            self.worker_thread.error_occurred.connect(self._on_embedding_error)
            self.worker_thread.start()

            # Show progress
            QMessageBox.information(
                self,
                "Thesis Created",
                f"Thesis for {thesis_data.ticker} is being processed...\n"
                "Embeddings are being generated for semantic search."
            )

        except Exception as e:
            logger.error(f"Failed to create thesis: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create thesis: {str(e)}")

    @pyqtSlot(dict)
    def _on_embedding_complete(self, thesis_id: str, thesis_data: ThesisData, result: Dict) -> None:
        """Handle embedding completion."""
        try:
            # Score the thesis
            score_thread = ThesisWorkerThread(
                "score",
                ticker=thesis_data.ticker,
                eps=5.0,  # TODO: Get from market data
                growth=15.0  # TODO: Get from fundamentals
            )
            score_thread.operation_complete.connect(
                lambda r: self._on_scoring_complete(thesis_id, thesis_data, result, r)
            )
            score_thread.error_occurred.connect(self._on_scoring_error)
            score_thread.start()

        except Exception as e:
            logger.error(f"Embedding handling error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Processing error: {str(e)}")

    @pyqtSlot(dict)
    def _on_scoring_complete(
        self,
        thesis_id: str,
        thesis_data: ThesisData,
        embedding_result: Dict,
        score_result: Dict
    ) -> None:
        """Handle scoring completion and save thesis."""
        try:
            # Store thesis
            thesis = {
                "thesis_id": thesis_id,
                "ticker": thesis_data.ticker,
                "company_name": thesis_data.company_name,
                "text": thesis_data.thesis_text,
                "catalysts": {
                    "short": thesis_data.catalysts_short_term,
                    "medium": thesis_data.catalysts_medium_term,
                    "long": thesis_data.catalysts_long_term
                },
                "risks": thesis_data.risks,
                "price_target": thesis_data.price_target,
                "horizon_months": thesis_data.horizon_months,
                "margin_of_safety": thesis_data.margin_of_safety,
                "moat_type": thesis_data.moat_type,
                "score": score_result.get("result", {}).get("score", 0),
                "strength": score_result.get("result", {}).get("strength", "UNKNOWN"),
                "embedding": embedding_result.get("result", {}).get("embedding", []),
                "created_at": datetime.now(),
                "status": "ACTIVE"
            }

            self.current_theses[thesis_id] = thesis

            # TODO: Save to database with embeddings
            # TODO: Store in ChromaDB for semantic search

            # Refresh UI
            self.refresh_active_theses()
            self.thesis_created.emit(thesis_id)

            QMessageBox.information(
                self,
                "Success",
                f"Thesis for {thesis_data.ticker} created successfully!\n"
                f"Score: {thesis['score']:.1f}/100 ({thesis['strength']})"
            )

        except Exception as e:
            logger.error(f"Failed to save thesis: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save thesis: {str(e)}")

    @pyqtSlot(str)
    def _on_embedding_error(self, error: str) -> None:
        """Handle embedding error."""
        logger.error(f"Embedding error: {error}")
        QMessageBox.critical(self, "Embedding Error", f"Failed to generate embeddings: {error}")

    @pyqtSlot(str)
    def _on_scoring_error(self, error: str) -> None:
        """Handle scoring error."""
        logger.error(f"Scoring error: {error}")
        QMessageBox.critical(self, "Scoring Error", f"Failed to score thesis: {error}")

    def refresh_active_theses(self) -> None:
        """Refresh active theses table and metrics."""
        try:
            # Clear table
            self.table_active.table.setRowCount(0)

            if not self.current_theses:
                return

            # Add rows
            for thesis_id, thesis in self.current_theses.items():
                if thesis.get("status") != "ACTIVE":
                    continue

                row = self.table_active.table.rowCount()
                self.table_active.table.insertRow(row)

                # TODO: Fetch current price
                current_price = 120.0  # Mock
                entry_price = 100.0    # Mock
                price_change_pct = ((current_price - entry_price) / entry_price) * 100

                price_target = thesis.get("price_target", 150.0)
                pct_to_target = ((price_target - current_price) / current_price) * 100

                horizon = thesis.get("horizon_months", 12)
                days_left = max(0, (30 * horizon) - 10)  # Mock

                items = [
                    QTableWidgetItem(thesis.get("ticker", "")),
                    QTableWidgetItem(thesis.get("text", "")[:50] + "..."),
                    QTableWidgetItem(f"${entry_price:.2f}"),
                    QTableWidgetItem(f"${current_price:.2f}"),
                    QTableWidgetItem(f"{pct_to_target:+.1f}%"),
                    QTableWidgetItem(thesis.get("status", "ACTIVE")),
                    QTableWidgetItem(f"{thesis.get('score', 0):.1f}"),
                    QTableWidgetItem(f"{days_left}d"),
                    QTableWidgetItem("View")
                ]

                for col, item in enumerate(items):
                    item.setFont(QFont("JetBrains Mono", 9))
                    # Color code score
                    if col == 6:  # Score column
                        score = thesis.get("score", 0)
                        if score > 75:
                            item.setForeground(QBrush(QColor("#00D26A")))
                        elif score > 50:
                            item.setForeground(QBrush(QColor("#FDB022")))
                        else:
                            item.setForeground(QBrush(QColor("#FF6B6B")))

                    self.table_active.table.setItem(row, col, item)

            # Update metrics
            active_count = len([t for t in self.current_theses.values() if t.get("status") == "ACTIVE"])
            avg_score = sum(t.get("score", 0) for t in self.current_theses.values()) / len(self.current_theses) if self.current_theses else 0

            self.metric_count.set_value(str(len(self.current_theses)))
            self.metric_active.set_value(str(active_count))
            self.metric_avg_score.set_value(f"{avg_score:.1f}")
            # TODO: Calculate hit rate from historical data
            self.metric_hit_rate.set_value("0%")

        except Exception as e:
            logger.error(f"Failed to refresh active theses: {e}", exc_info=True)

    @pyqtSlot(int)
    def on_thesis_selected(self, row: int) -> None:
        """Handle thesis row selection."""
        try:
            # Find thesis from table
            ticker_item = self.table_active.table.item(row, 0)
            if not ticker_item:
                return

            ticker = ticker_item.text()
            thesis = next(
                (t for t in self.current_theses.values() if t.get("ticker") == ticker),
                None
            )

            if thesis:
                # Update detail panel
                self.detail_ticker.setText(thesis.get("ticker", ""))
                self.detail_thesis.setText(thesis.get("text", ""))
                catalysts = thesis.get("catalysts", {})
                self.detail_catalysts.setText(
                    f"Short: {catalysts.get('short', '')}\n"
                    f"Medium: {catalysts.get('medium', '')}\n"
                    f"Long: {catalysts.get('long', '')}"
                )
                self.detail_risks.setText(thesis.get("risks", ""))

                self.detail_score.set_value(f"{thesis.get('score', 0):.1f}")
                self.detail_strength.set_value(thesis.get("strength", "UNKNOWN"))

                # Show detail panel
                self.detail_panel.setChecked(True)

        except Exception as e:
            logger.error(f"Failed to select thesis: {e}", exc_info=True)

    def rag_search(self) -> None:
        """Perform semantic search on theses."""
        query = self.rag_query.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search query")
            return

        self.rag_progress.setVisible(True)
        self.rag_progress.setValue(0)

        # Start RAG search in background
        self.worker_thread = ThesisWorkerThread(
            "rag_search",
            query=query,
            top_k=5
        )
        self.worker_thread.operation_complete.connect(self._on_rag_search_complete)
        self.worker_thread.error_occurred.connect(self._on_rag_search_error)
        self.worker_thread.start()

    @pyqtSlot(dict)
    def _on_rag_search_complete(self, result: Dict) -> None:
        """Handle RAG search completion."""
        try:
            similar = result.get("result", [])

            # Populate results table
            self.table_rag_results.table.setRowCount(0)

            for similar_thesis in similar:
                row = self.table_rag_results.table.rowCount()
                self.table_rag_results.table.insertRow(row)

                items = [
                    QTableWidgetItem(similar_thesis.get("ticker", "")),
                    QTableWidgetItem(f"{similar_thesis.get('similarity', 0):.2%}"),
                    QTableWidgetItem(similar_thesis.get("thesis", "")[:50] + "..."),
                    QTableWidgetItem(similar_thesis.get("date", "")),
                    QTableWidgetItem("CLOSED")  # Mock
                ]

                for col, item in enumerate(items):
                    item.setFont(QFont("JetBrains Mono", 9))
                    self.table_rag_results.table.setItem(row, col, item)

            self.rag_progress.setVisible(False)
            QMessageBox.information(
                self,
                "Search Complete",
                f"Found {len(similar)} similar theses"
            )

        except Exception as e:
            logger.error(f"RAG search error: {e}", exc_info=True)

    @pyqtSlot(str)
    def _on_rag_search_error(self, error: str) -> None:
        """Handle RAG search error."""
        self.rag_progress.setVisible(False)
        QMessageBox.critical(self, "Search Error", f"RAG search failed: {error}")

    @pyqtSlot(int)
    def on_rag_result_selected(self, row: int) -> None:
        """Handle RAG result selection."""
        thesis_item = self.table_rag_results.table.item(row, 2)
        if thesis_item:
            self.rag_detail_text.setText(thesis_item.text())

    @pyqtSlot(int)
    def on_history_selected(self, row: int) -> None:
        """Handle historical thesis selection."""
        # TODO: Populate lessons learned
        pass

    def analyze_thesis_ai(self) -> None:
        """Analyze thesis using AI gateway."""
        ticker = self.ai_ticker.text().strip()
        thesis = self.ai_thesis.toPlainText().strip()

        if not ticker or not thesis:
            QMessageBox.warning(self, "Input Error", "Please fill in ticker and thesis")
            return

        self.ai_progress.setVisible(True)
        self.ai_progress.setValue(0)

        self.worker_thread = ThesisWorkerThread(
            "ai_analyze",
            ticker=ticker,
            text=thesis
        )
        self.worker_thread.operation_complete.connect(self._on_ai_analysis_complete)
        self.worker_thread.error_occurred.connect(self._on_ai_analysis_error)
        self.worker_thread.start()

    @pyqtSlot(dict)
    def _on_ai_analysis_complete(self, result: Dict) -> None:
        """Handle AI analysis completion."""
        try:
            analysis = result.get("result", {})

            output = "=== AI Thesis Analysis ===\n\n"

            output += "STRENGTHS:\n"
            for strength in analysis.get("strengths", []):
                output += f"  • {strength}\n"

            output += "\nWEAKNESSES:\n"
            for weakness in analysis.get("weaknesses", []):
                output += f"  • {weakness}\n"

            output += f"\nSUGGESTED PRICE TARGET: ${analysis.get('suggested_price_target', 'N/A')}\n"
            output += f"CONFIDENCE: {analysis.get('confidence', 0):.0%}\n"

            self.ai_results.setText(output)
            self.ai_progress.setVisible(False)

        except Exception as e:
            logger.error(f"AI analysis error: {e}", exc_info=True)

    @pyqtSlot(str)
    def _on_ai_analysis_error(self, error: str) -> None:
        """Handle AI analysis error."""
        self.ai_progress.setVisible(False)
        QMessageBox.critical(self, "Analysis Error", f"AI analysis failed: {error}")

    def analyze_selected_thesis(self) -> None:
        """Analyze currently selected thesis using AI."""
        ticker = self.detail_ticker.text().strip()
        thesis = self.detail_thesis.toPlainText().strip()

        if not ticker or not thesis:
            QMessageBox.warning(self, "No Selection", "Please select a thesis first")
            return

        self.ai_ticker.setText(ticker)
        self.ai_thesis.setPlainText(thesis)
        self.tabs.setCurrentWidget(self.tab_ai)
        self.analyze_thesis_ai()

    def edit_selected_thesis(self) -> None:
        """Edit currently selected thesis."""
        ticker = self.detail_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, "No Selection", "Please select a thesis first")
            return

        QMessageBox.information(
            self,
            "Edit Thesis",
            f"Edit functionality for {ticker} coming soon"
        )

    def close_selected_thesis(self) -> None:
        """Close currently selected thesis."""
        ticker = self.detail_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, "No Selection", "Please select a thesis first")
            return

        # Find and close thesis
        for thesis in self.current_theses.values():
            if thesis.get("ticker") == ticker and thesis.get("status") == "ACTIVE":
                thesis["status"] = "CLOSED"
                thesis["closed_at"] = datetime.now()
                # TODO: Move to historical
                break

        self.refresh_active_theses()
        QMessageBox.information(
            self,
            "Thesis Closed",
            f"Thesis for {ticker} has been closed"
        )

    def export_ai_analysis(self) -> None:
        """Export AI analysis to file."""
        ticker = self.ai_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, "No Analysis", "Please analyze a thesis first")
            return

        # TODO: Export to PDF or text file
        QMessageBox.information(
            self,
            "Export",
            f"Analysis for {ticker} export functionality coming soon"
        )
