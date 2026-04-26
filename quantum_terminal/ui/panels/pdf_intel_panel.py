"""
PDF Intel Panel - Smart financial document processing.

Handles drag-and-drop PDF processing (10-K, 10-Q, Earnings Releases).
Extracts financial metrics, compares with SEC XBRL data, and calculates
Graham-Dodd valuation metrics.

Module 8 - Phase 3 UI Implementation
Reference: PLAN_MAESTRO.md - PDF Intel Module
"""

from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
import json
import asyncio

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QScrollArea, QFrame, QGridLayout, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import QMimeData

from quantum_terminal.ui.widgets import (
    MetricCard, AlertBanner
)
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.config import settings

# Import infrastructure
try:
    from quantum_terminal.infrastructure.pdf.pdf_extractor import (
        PDFExtractor, FinancialData, get_pdf_extractor
    )
except ImportError:
    PDFExtractor = None
    FinancialData = None

try:
    from quantum_terminal.infrastructure.pdf.pdf_validator import PDFValidator
except ImportError:
    PDFValidator = None

try:
    from quantum_terminal.infrastructure.macro.sec_adapter import SECAdapter
except ImportError:
    SECAdapter = None

# Import domain layer
try:
    from quantum_terminal.domain.valuation import graham_formula
except ImportError:
    graham_formula = None

logger = get_logger(__name__)


class PDFProcessorThread(QThread):
    """Background thread for PDF processing."""

    progress_updated = pyqtSignal(int, str)  # progress %, message
    processing_complete = pyqtSignal(dict)  # results
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, pdf_files: List[str], ticker: str):
        """Initialize processor thread.

        Args:
            pdf_files: List of PDF file paths
            ticker: Stock ticker symbol
        """
        super().__init__()
        self.pdf_files = pdf_files
        self.ticker = ticker
        self.results = {}

    def run(self):
        """Run PDF processing in background."""
        try:
            if not PDFExtractor:
                self.error_occurred.emit("PDFExtractor not available")
                return

            extractor = get_pdf_extractor()
            total_files = len(self.pdf_files)

            for idx, pdf_path in enumerate(self.pdf_files):
                try:
                    progress = int((idx / total_files) * 100)
                    self.progress_updated.emit(progress, f"Processing {Path(pdf_path).name}...")

                    # Run async extraction
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    data = loop.run_until_complete(
                        extractor.extract_from_pdf(pdf_path, self.ticker)
                    )
                    loop.close()

                    if data:
                        key = f"{data.document_type}_{idx}"
                        self.results[key] = data

                except Exception as e:
                    logger.error(f"Error processing {pdf_path}: {e}")
                    self.error_occurred.emit(f"Error processing {Path(pdf_path).name}: {str(e)}")

            self.progress_updated.emit(100, "Complete")
            self.processing_complete.emit(self.results)

        except Exception as e:
            logger.error(f"Processor thread error: {e}", exc_info=True)
            self.error_occurred.emit(f"Processing error: {str(e)}")


class PDFIntelPanel(QWidget):
    """Main PDF Intel Panel for financial document processing.

    Features:
    - Drag & drop PDF upload with type detection
    - Automatic extraction of financial metrics
    - Cross-validation with SEC XBRL data
    - Graham-Dodd valuation calculation
    - Batch processing for multiple documents
    - Document timeline and history
    """

    pdf_processed = pyqtSignal(dict)  # Emitted when PDF processing complete

    def __init__(self, parent=None):
        """Initialize PDF Intel Panel."""
        super().__init__(parent)

        self.pdf_extractor = get_pdf_extractor() if PDFExtractor else None
        self.pdf_validator = PDFValidator(SECAdapter()) if PDFValidator else None
        self.sec_adapter = SECAdapter() if SECAdapter else None

        self.current_ticker = "AAPL"
        self.extracted_data: Dict[str, FinancialData] = {}
        self.comparison_results: Dict[str, List] = {}
        self.processor_thread: Optional[PDFProcessorThread] = None

        # UI state
        self.setAcceptDrops(True)
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

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._build_upload_tab(), "Upload")
        tabs.addTab(self._build_extracted_data_tab(), "Extracted Data")
        tabs.addTab(self._build_ratios_tab(), "Graham Ratios")
        tabs.addTab(self._build_comparison_tab(), "SEC Validation")
        tabs.addTab(self._build_timeline_tab(), "Timeline")

        main_layout.addWidget(tabs)

        # Status bar
        status_layout = self._build_status_bar()
        main_layout.addLayout(status_layout)

    def _build_title_bar(self) -> QHBoxLayout:
        """Build title bar with ticker input."""
        layout = QHBoxLayout()

        title = QLabel("PDF Intel")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)

        ticker_label = QLabel("Ticker:")
        self.ticker_input = QComboBox()
        self.ticker_input.setEditable(True)
        self.ticker_input.addItems(["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"])
        self.ticker_input.currentTextChanged.connect(self._on_ticker_changed)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(ticker_label)
        layout.addWidget(self.ticker_input)

        return layout

    def _build_upload_tab(self) -> QWidget:
        """Build file upload tab with drag-and-drop."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Instructions
        instructions = QLabel(
            "Drag and drop PDF files here or click to browse.\n"
            "Supports: 10-K, 10-Q, Earnings Releases, Investor Days"
        )
        instructions.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(instructions)

        # Drop zone
        self.drop_zone = QFrame()
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed #666;
                border-radius: 8px;
                background-color: #222;
            }
            QFrame:hover {
                border: 2px dashed #0080ff;
                background-color: #262626;
            }
        """)
        self.drop_zone.setMinimumHeight(150)

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_label = QLabel("📄 Drop PDFs here\nOR")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_font = QFont()
        drop_font.setPointSize(12)
        drop_label.setFont(drop_font)

        browse_btn = QPushButton("Browse Files")
        browse_btn.setMaximumWidth(150)
        browse_btn.clicked.connect(self._on_browse_clicked)

        drop_layout.addStretch()
        drop_layout.addWidget(drop_label)
        drop_layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        drop_layout.addStretch()

        layout.addWidget(self.drop_zone)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # Status label
        self.upload_status_label = QLabel("Ready")
        self.upload_status_label.setStyleSheet("color: #0f0;")
        layout.addWidget(self.upload_status_label)

        # Batch controls
        batch_layout = QHBoxLayout()

        folder_btn = QPushButton("Process Folder")
        folder_btn.clicked.connect(self._on_process_folder_clicked)

        batch_size_label = QLabel("Batch size:")
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setValue(10)
        self.batch_size_spin.setMinimum(1)
        self.batch_size_spin.setMaximum(100)

        batch_layout.addWidget(folder_btn)
        batch_layout.addWidget(batch_size_label)
        batch_layout.addWidget(self.batch_size_spin)
        batch_layout.addStretch()

        layout.addLayout(batch_layout)
        layout.addStretch()

        return widget

    def _build_extracted_data_tab(self) -> QWidget:
        """Build extracted data tab with table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            "Document Type", "Revenue", "Net Income", "EPS", "Assets", "Liabilities", "Equity", "Debt"
        ])
        self.data_table.setRowCount(0)
        self.data_table.setColumnWidth(0, 100)
        for i in range(1, 8):
            self.data_table.setColumnWidth(i, 100)

        layout.addWidget(self.data_table)

        # Export button
        export_btn = QPushButton("Export to JSON")
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)

        return widget

    def _build_ratios_tab(self) -> QWidget:
        """Build Graham-Dodd ratios tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setSpacing(12)

        # Ratio cards
        self.ratio_cards = {}
        ratios = [
            ("Graham IV", "Intrinsic Value", "price_units"),
            ("P/E Ratio", "Price/Earnings", "ratio"),
            ("P/B Ratio", "Price/Book", "ratio"),
            ("PEG Ratio", "P/E to Growth", "ratio"),
            ("Dividend Yield", "Annual Yield", "percent"),
            ("Debt/Equity", "Leverage Ratio", "ratio"),
            ("FCF Yield", "Free Cash Flow Yield", "percent"),
        ]

        for idx, (name, description, unit) in enumerate(ratios):
            card = MetricCard(name, description, "—", unit)
            self.ratio_cards[name] = card
            row = idx // 2
            col = idx % 2
            scroll_layout.addWidget(card, row, col)

        scroll_layout.addItem(
            QSpacerItem(0, 0, expanding=(True, True)),
            len(ratios) // 2 + 1, 0, 1, 2
        )
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Calculate button
        calc_btn = QPushButton("Calculate Ratios")
        calc_btn.clicked.connect(self._on_calculate_ratios_clicked)
        layout.addWidget(calc_btn)

        return widget

    def _build_comparison_tab(self) -> QWidget:
        """Build SEC validation comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(5)
        self.comparison_table.setHorizontalHeaderLabels([
            "Metric", "PDF Value", "SEC Value", "Variance %", "Status"
        ])
        self.comparison_table.setRowCount(0)
        for i in range(5):
            self.comparison_table.setColumnWidth(i, 120)

        layout.addWidget(self.comparison_table)

        # Validate button
        validate_btn = QPushButton("Validate vs SEC")
        validate_btn.clicked.connect(self._on_validate_clicked)
        layout.addWidget(validate_btn)

        return widget

    def _build_timeline_tab(self) -> QWidget:
        """Build document timeline tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Timeline list
        self.timeline_text = QTextEdit()
        self.timeline_text.setReadOnly(True)
        self.timeline_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ddd;
                border: 1px solid #333;
                font-family: monospace;
                font-size: 10px;
            }
        """)

        layout.addWidget(self.timeline_text)

        # Clear history button
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self._on_clear_history_clicked)
        layout.addWidget(clear_btn)

        return widget

    def _build_status_bar(self) -> QHBoxLayout:
        """Build status bar at bottom."""
        layout = QHBoxLayout()

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.file_count_label = QLabel("Files: 0")
        layout.addWidget(self.file_count_label)

        return layout

    def setup_connections(self):
        """Setup signal-slot connections."""
        pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            files = [url.toLocalFile() for url in mime_data.urls()]
            pdf_files = [f for f in files if f.lower().endswith('.pdf')]

            if pdf_files:
                self._process_pdf_files(pdf_files)

    @pyqtSlot()
    def _on_browse_clicked(self):
        """Handle browse button click."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )

        if files:
            self._process_pdf_files(files)

    @pyqtSlot()
    def _on_process_folder_clicked(self):
        """Handle process folder button click."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with PDFs")

        if folder:
            pdf_files = list(Path(folder).glob("*.pdf"))
            pdf_files = [str(f) for f in pdf_files]

            if pdf_files:
                self._process_pdf_files(pdf_files)
            else:
                self.upload_status_label.setText("No PDF files found in folder")
                self.upload_status_label.setStyleSheet("color: #f00;")

    def _process_pdf_files(self, pdf_files: List[str]):
        """Process list of PDF files."""
        ticker = self.ticker_input.currentText()
        self.current_ticker = ticker

        # Start background thread
        self.processor_thread = PDFProcessorThread(pdf_files, ticker)
        self.processor_thread.progress_updated.connect(self._on_progress_updated)
        self.processor_thread.processing_complete.connect(self._on_processing_complete)
        self.processor_thread.error_occurred.connect(self._on_processing_error)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.processor_thread.start()

    @pyqtSlot(int, str)
    def _on_progress_updated(self, progress: int, message: str):
        """Update progress bar and status."""
        self.progress_bar.setValue(progress)
        self.upload_status_label.setText(message)
        self.upload_status_label.setStyleSheet("color: #0f0;")

    @pyqtSlot(dict)
    def _on_processing_complete(self, results: dict):
        """Handle processing complete."""
        self.extracted_data = results
        self.progress_bar.setVisible(False)

        self.upload_status_label.setText(f"Processed {len(results)} documents")
        self.upload_status_label.setStyleSheet("color: #0f0;")

        self.file_count_label.setText(f"Files: {len(results)}")

        # Update tables
        self._update_data_table()
        self._update_timeline()

        self.pdf_processed.emit(results)
        logger.info(f"Processed {len(results)} PDF files")

    @pyqtSlot(str)
    def _on_processing_error(self, error: str):
        """Handle processing error."""
        self.upload_status_label.setText(f"Error: {error}")
        self.upload_status_label.setStyleSheet("color: #f00;")
        self.progress_bar.setVisible(False)
        logger.error(f"PDF processing error: {error}")

    def _update_data_table(self):
        """Update extracted data table."""
        self.data_table.setRowCount(0)

        for idx, (key, data) in enumerate(self.extracted_data.items()):
            if not isinstance(data, FinancialData):
                continue

            self.data_table.insertRow(idx)

            # Document type
            self.data_table.setItem(idx, 0, QTableWidgetItem(data.document_type))

            # Revenue (most recent)
            revenue = data.revenue[-1] if data.revenue else None
            self.data_table.setItem(
                idx, 1, QTableWidgetItem(f"${revenue/1e9:.2f}B" if revenue else "—")
            )

            # Net Income
            net_income = data.net_income[-1] if data.net_income else None
            self.data_table.setItem(
                idx, 2, QTableWidgetItem(f"${net_income/1e9:.2f}B" if net_income else "—")
            )

            # EPS
            eps = data.eps[-1] if data.eps else None
            self.data_table.setItem(
                idx, 3, QTableWidgetItem(f"${eps:.2f}" if eps else "—")
            )

            # Assets
            self.data_table.setItem(
                idx, 4, QTableWidgetItem(
                    f"${data.total_assets/1e9:.2f}B" if data.total_assets else "—"
                )
            )

            # Liabilities
            self.data_table.setItem(
                idx, 5, QTableWidgetItem(
                    f"${data.total_liabilities/1e9:.2f}B" if data.total_liabilities else "—"
                )
            )

            # Equity
            self.data_table.setItem(
                idx, 6, QTableWidgetItem(
                    f"${data.shareholders_equity/1e9:.2f}B" if data.shareholders_equity else "—"
                )
            )

            # Debt
            self.data_table.setItem(
                idx, 7, QTableWidgetItem(
                    f"${data.total_debt/1e9:.2f}B" if data.total_debt else "—"
                )
            )

    def _update_timeline(self):
        """Update timeline view."""
        timeline_text = "Document Processing Timeline\n"
        timeline_text += "=" * 50 + "\n\n"

        for idx, (key, data) in enumerate(self.extracted_data.items(), 1):
            if not isinstance(data, FinancialData):
                continue

            timeline_text += f"{idx}. {data.document_type}\n"
            if data.filing_date:
                timeline_text += f"   Filed: {data.filing_date}\n"
            timeline_text += f"   Ticker: {data.ticker}\n"
            timeline_text += f"   Data points: Rev={len(data.revenue)}, "
            timeline_text += f"NI={len(data.net_income)}, EPS={len(data.eps)}\n\n"

        self.timeline_text.setPlainText(timeline_text)

    @pyqtSlot()
    def _on_calculate_ratios_clicked(self):
        """Calculate Graham-Dodd ratios."""
        if not self.extracted_data or not graham_formula:
            logger.warning("No data or graham_formula not available")
            return

        # Get first data
        data = next(iter(self.extracted_data.values()), None)
        if not isinstance(data, FinancialData) or not data.eps:
            return

        try:
            # Get recent market data (simplified - would need DataProvider)
            current_price = 150.0  # Placeholder
            eps = data.eps[-1]
            growth_rate = 8.0  # Placeholder
            risk_free_rate = 4.5  # Placeholder

            # Calculate Graham IV
            iv = graham_formula(eps, growth_rate, risk_free_rate, quality_score=100)

            # Update cards
            if "Graham IV" in self.ratio_cards:
                self.ratio_cards["Graham IV"].update_value(f"${iv:.2f}")

            if "P/E Ratio" in self.ratio_cards:
                pe = current_price / eps if eps else 0
                self.ratio_cards["P/E Ratio"].update_value(f"{pe:.2f}x")

            if "Debt/Equity" in self.ratio_cards:
                if data.shareholders_equity and data.total_debt:
                    de = data.total_debt / data.shareholders_equity
                    self.ratio_cards["Debt/Equity"].update_value(f"{de:.2f}x")

            logger.info("Ratios calculated successfully")

        except Exception as e:
            logger.error(f"Error calculating ratios: {e}", exc_info=True)

    @pyqtSlot()
    def _on_validate_clicked(self):
        """Validate PDF data against SEC."""
        if not self.extracted_data or not self.pdf_validator:
            logger.warning("No data or validator not available")
            return

        # Get first data
        data = next(iter(self.extracted_data.values()), None)
        if not isinstance(data, FinancialData):
            return

        # Run validation in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            results = loop.run_until_complete(
                self.pdf_validator.compare_with_sec(data, self.current_ticker)
            )

            # Update comparison table
            self.comparison_table.setRowCount(0)

            for idx, result in enumerate(results):
                self.comparison_table.insertRow(idx)

                self.comparison_table.setItem(idx, 0, QTableWidgetItem(result.metric_name))
                self.comparison_table.setItem(
                    idx, 1, QTableWidgetItem(f"{result.pdf_value:,.0f}" if result.pdf_value else "—")
                )
                self.comparison_table.setItem(
                    idx, 2, QTableWidgetItem(f"{result.sec_value:,.0f}" if result.sec_value else "—")
                )
                self.comparison_table.setItem(
                    idx, 3, QTableWidgetItem(
                        f"{result.variance_percent:.2f}%" if result.variance_percent else "—"
                    )
                )

                status_item = QTableWidgetItem(result.status)
                if result.status == "match":
                    status_item.setForeground(QColor("#0f0"))
                elif result.status == "acceptable":
                    status_item.setForeground(QColor("#fc0"))
                elif result.status == "warning":
                    status_item.setForeground(QColor("#f80"))
                else:
                    status_item.setForeground(QColor("#f00"))

                self.comparison_table.setItem(idx, 4, status_item)

        finally:
            loop.close()

    @pyqtSlot(str)
    def _on_ticker_changed(self, ticker: str):
        """Handle ticker change."""
        self.current_ticker = ticker.upper()
        logger.debug(f"Ticker changed to {self.current_ticker}")

    @pyqtSlot()
    def _on_export_clicked(self):
        """Export extracted data to JSON."""
        if not self.extracted_data:
            self.status_label.setText("No data to export")
            return

        # Prepare data
        export_data = {}
        for key, data in self.extracted_data.items():
            if isinstance(data, FinancialData):
                export_data[key] = {
                    "ticker": data.ticker,
                    "document_type": data.document_type,
                    "filing_date": data.filing_date,
                    "revenue": data.revenue,
                    "net_income": data.net_income,
                    "eps": data.eps,
                    "total_assets": data.total_assets,
                    "total_debt": data.total_debt,
                }

        # Save to file
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Exported Data", "", "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.status_label.setText(f"Exported to {Path(file_path).name}")
            except Exception as e:
                self.status_label.setText(f"Export error: {str(e)}")
                logger.error(f"Export error: {e}", exc_info=True)

    @pyqtSlot()
    def _on_clear_history_clicked(self):
        """Clear document history."""
        self.extracted_data.clear()
        self.comparison_results.clear()
        self.data_table.setRowCount(0)
        self.comparison_table.setRowCount(0)
        self.timeline_text.clear()
        self.file_count_label.setText("Files: 0")
        self.status_label.setText("History cleared")
