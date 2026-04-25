"""
Main window for Quantum Investment Terminal.

Implements Bloomberg-style 3-column layout:
- Left: Navigation panel (12 modules)
- Center: Module panels (QTabWidget)
- Right: AI Chat sidebar
- Top: Market ticker bar (real-time)
- Bottom: Status bar with metrics
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QStatusBar,
    QMenuBar,
    QMenu,
    QToolBar,
    QFrame,
)

from quantum_terminal.ui.styles import load_stylesheet, Colors
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class MarketBarWidget(QFrame):
    """Real-time market ticker bar at the top of the window."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize market bar with key indices."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND_PANEL};")
        self.setMaximumHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(20)

        # Market indices to display
        self.indices = {
            "S&P 500": {"value": "4,567.89", "change": "+0.45%", "positive": True},
            "NASDAQ": {"value": "14,234.56", "change": "-0.12%", "positive": False},
            "BTC": {"value": "$67,890", "change": "+2.34%", "positive": True},
            "WTI": {"value": "$78.45", "change": "+1.23%", "positive": True},
            "10Y": {"value": "4.23%", "change": "+0.05%", "positive": False},
            "VIX": {"value": "15.67", "change": "-0.34%", "positive": True},
            "DXY": {"value": "105.23", "change": "+0.12%", "positive": True},
        }

        # Create labels for each index
        self.index_labels = {}
        for symbol, data in self.indices.items():
            # Symbol label
            symbol_label = QLabel(symbol)
            symbol_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;"
            )
            layout.addWidget(symbol_label)

            # Value and change label
            color = Colors.POSITIVE if data["positive"] else Colors.NEGATIVE
            value_text = f"{data['value']} {data['change']}"
            value_label = QLabel(value_text)
            value_label.setStyleSheet(f"color: {color}; font-family: monospace;")
            layout.addWidget(value_label)
            self.index_labels[symbol] = value_label

            # Separator
            if symbol != "DXY":
                separator = QLabel("|")
                separator.setStyleSheet(f"color: {Colors.BORDER};")
                layout.addWidget(separator)

        layout.addStretch()

        # Last update time
        self.update_label = QLabel("Updated: 14:23:45 UTC")
        self.update_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 9px;")
        layout.addWidget(self.update_label)

    def update_indices(self, updates: dict) -> None:
        """Update market indices."""
        for symbol, data in updates.items():
            if symbol in self.index_labels:
                color = Colors.POSITIVE if data.get("positive", False) else Colors.NEGATIVE
                value_text = f"{data['value']} {data['change']}"
                self.index_labels[symbol].setText(value_text)
                self.index_labels[symbol].setStyleSheet(
                    f"color: {color}; font-family: monospace;"
                )


class NavigationWidget(QListWidget):
    """Left sidebar: Navigation between 12 modules."""

    module_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize navigation with all 12 modules."""
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

        # All modules in Quantum Terminal
        modules = [
            ("Dashboard", "📊"),
            ("Watchlist", "👁️"),
            ("Analyzer", "🔍"),
            ("Screener", "🔎"),
            ("Macro", "🌍"),
            ("Journal", "📓"),
            ("Thesis", "💡"),
            ("PDF Intel", "📄"),
            ("Earnings", "📈"),
            ("Monitor", "⚠️"),
            ("Backtest", "🧪"),
            ("Risk", "⚔️"),
        ]

        for module_name, icon in modules:
            item = QListWidgetItem(f"{icon}  {module_name}")
            item.setData(256, module_name)  # Store actual name in user role
            item.setFont(QFont("Segoe UI", 10))
            self.addItem(item)

        # Select first item by default
        self.setCurrentRow(0)
        self.itemClicked.connect(self._on_item_selected)

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        """Emit signal when module is selected."""
        module_name = item.data(256)
        self.module_selected.emit(module_name)


class ChatWidget(QFrame):
    """Right sidebar: AI Chat assistant."""

    send_message = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize AI chat sidebar."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMinimumWidth(240)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("AI Assistant")
        header.setStyleSheet(
            f"color: {Colors.ACCENT}; font-weight: bold; font-size: 12px;"
        )
        layout.addWidget(header)

        # Chat history display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(200)
        self.chat_display.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {Colors.BACKGROUND_MAIN};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 3px;
                padding: 6px;
            }}
        """
        )
        layout.addWidget(self.chat_display)

        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Ask me anything...")
        self.message_input.setMinimumHeight(32)
        self.message_input.returnPressed.connect(self._send_message)
        layout.addWidget(self.message_input)

        # Send button
        send_btn = QPushButton("Send")
        send_btn.setMinimumHeight(32)
        send_btn.setObjectName("primaryBtn")
        send_btn.clicked.connect(self._send_message)
        layout.addWidget(send_btn)

        # Suggestions
        suggestions_label = QLabel("Quick Actions:")
        suggestions_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 9px; margin-top: 8px;"
        )
        layout.addWidget(suggestions_label)

        suggestions = [
            "Score this ticker",
            "Find similar theses",
            "Analyze fundamentals",
            "Check thesis quality",
        ]

        for suggestion in suggestions:
            btn = QPushButton(suggestion)
            btn.setMaximumHeight(24)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.ACCENT};
                    border: 1px solid {Colors.ACCENT};
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 9px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.ACCENT_TRANSPARENT};
                }}
            """
            )
            btn.clicked.connect(lambda checked, s=suggestion: self._suggest_action(s))
            layout.addWidget(btn)

        layout.addStretch()

    def _send_message(self) -> None:
        """Send message from input field."""
        message = self.message_input.text().strip()
        if message:
            self.send_message.emit(message)
            self.message_input.clear()

    def _suggest_action(self, action: str) -> None:
        """Handle quick action suggestions."""
        self.message_input.setText(action)
        self._send_message()

    def add_message(self, sender: str, message: str, is_error: bool = False) -> None:
        """Add message to chat display."""
        color = Colors.ERROR if is_error else Colors.TEXT_PRIMARY
        sender_color = Colors.ACCENT if sender == "Assistant" else Colors.TEXT_SECONDARY

        html = f"""
        <p>
            <span style="color: {sender_color}; font-weight: bold;">{sender}:</span>
            <span style="color: {color};">{message}</span>
        </p>
        """
        self.chat_display.append(html)


class ModulePanelWidget(QTabWidget):
    """Center panel: QTabWidget with tabs for each module."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize module tabs."""
        super().__init__(parent)
        self.setDocumentMode(True)

        # Module tabs - will be populated by main window
        self.module_panels = {}

    def add_module_tab(self, name: str, widget: QWidget) -> None:
        """Add a new module tab."""
        self.addTab(widget, name)
        self.module_panels[name] = widget

    def select_module(self, name: str) -> None:
        """Select a module by name."""
        if name in self.module_panels:
            index = self.indexOf(self.module_panels[name])
            self.setCurrentIndex(index)


class QuantumTerminal(QMainWindow):
    """Main window for Quantum Investment Terminal."""

    def __init__(self):
        """Initialize main window with 3-column Bloomberg layout."""
        super().__init__()
        self.setWindowTitle("Quantum Investment Terminal")
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(QSize(1200, 700))

        logger.info("Initializing Quantum Terminal")

        # Apply stylesheet
        stylesheet = load_stylesheet()
        if stylesheet:
            self.setStyleSheet(stylesheet)
        else:
            logger.warning("Failed to load stylesheet")

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Market bar (top)
        self.market_bar = MarketBarWidget()
        main_layout.addWidget(self.market_bar)

        # 3-column splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"background-color: {Colors.BACKGROUND_MAIN};")

        # Left: Navigation
        self.nav = NavigationWidget()
        splitter.addWidget(self.nav)

        # Center: Module tabs
        self.tabs = ModulePanelWidget()
        splitter.addWidget(self.tabs)

        # Right: AI Chat
        self.chat = ChatWidget()
        splitter.addWidget(self.chat)

        # Set column proportions: NAV 15%, CENTER 70%, CHAT 15%
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar_widget = self.create_status_bar()
        self.setStatusBar(self.status_bar_widget)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Connect signals
        self.nav.module_selected.connect(self._on_module_selected)
        self.chat.send_message.connect(self._on_chat_message)

        # Timer for updating market data
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self._update_market_bar)
        self.market_timer.start(5000)  # Update every 5 seconds

        # Initialize placeholder module
        self._init_placeholder_modules()

        logger.info("Quantum Terminal initialized successfully")

    def create_status_bar(self) -> QStatusBar:
        """Create status bar with metrics."""
        status_bar = QStatusBar()
        status_bar.setMaximumHeight(24)

        # Status indicators
        db_status = QLabel("✓ Database")
        db_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 9px;")
        status_bar.addWidget(db_status)

        api_status = QLabel("APIs: 5/6 ✓")
        api_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 9px;")
        status_bar.addPermanentWidget(api_status)

        cache_status = QLabel("Cache: 847 items")
        cache_status.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9px;")
        status_bar.addPermanentWidget(cache_status)

        memory_status = QLabel("RAM: 342 MB")
        memory_status.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9px;")
        status_bar.addPermanentWidget(memory_status)

        return status_bar

    def create_menu_bar(self) -> None:
        """Create menu bar with File, Edit, View, Data, Help."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&New Thesis").triggered.connect(
            lambda: logger.info("New thesis")
        )
        file_menu.addAction("&Open").triggered.connect(lambda: logger.info("Open file"))
        file_menu.addSeparator()
        file_menu.addAction("&Import Data").triggered.connect(
            lambda: logger.info("Import data")
        )
        file_menu.addAction("&Export").triggered.connect(
            lambda: logger.info("Export data")
        )
        file_menu.addSeparator()
        file_menu.addAction("&Settings").triggered.connect(
            lambda: logger.info("Settings")
        )
        file_menu.addAction("E&xit").triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("&Undo").triggered.connect(lambda: logger.info("Undo"))
        edit_menu.addAction("&Redo").triggered.connect(lambda: logger.info("Redo"))
        edit_menu.addSeparator()
        edit_menu.addAction("&Copy").triggered.connect(lambda: logger.info("Copy"))
        edit_menu.addAction("&Paste").triggered.connect(lambda: logger.info("Paste"))

        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("&Refresh").triggered.connect(self._update_market_bar)
        view_menu.addSeparator()
        view_menu.addAction("&Fullscreen").triggered.connect(self._toggle_fullscreen)
        view_menu.addAction("&Reset Layout").triggered.connect(self._reset_layout)

        # Data menu
        data_menu = menubar.addMenu("&Data")
        data_menu.addAction("&Fetch Quotes").triggered.connect(
            lambda: logger.info("Fetch quotes")
        )
        data_menu.addAction("&Run Screener").triggered.connect(
            lambda: logger.info("Run screener")
        )
        data_menu.addAction("&Sync Database").triggered.connect(
            lambda: logger.info("Sync database")
        )

        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&Documentation").triggered.connect(
            lambda: logger.info("Show documentation")
        )
        help_menu.addAction("&About").triggered.connect(lambda: logger.info("About"))

    def create_toolbar(self) -> None:
        """Create toolbar with common actions."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMaximumHeight(32)
        toolbar.setIconSize(QSize(16, 16))

        toolbar.addAction("🔄 Refresh").triggered.connect(self._update_market_bar)
        toolbar.addSeparator()
        toolbar.addAction("🔍 Search").triggered.connect(lambda: logger.info("Search"))
        toolbar.addAction("⚙️ Settings").triggered.connect(lambda: logger.info("Settings"))

    def _init_placeholder_modules(self) -> None:
        """Initialize placeholder widgets for each module."""
        modules = [
            "Dashboard",
            "Watchlist",
            "Analyzer",
            "Screener",
            "Macro",
            "Journal",
            "Thesis",
            "PDF Intel",
            "Earnings",
            "Monitor",
            "Backtest",
            "Risk",
        ]

        for module_name in modules:
            # Create placeholder widget
            placeholder = QFrame()
            placeholder.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {Colors.BACKGROUND_PANEL};
                    border: 1px solid {Colors.BORDER};
                }}
            """
            )
            layout = QVBoxLayout(placeholder)
            label = QLabel(f"Module: {module_name}")
            label.setStyleSheet(
                f"""
                color: {Colors.ACCENT};
                font-size: 14px;
                font-weight: bold;
            """
            )
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

            # Add placeholder text
            info = QLabel(
                f"[Placeholder for {module_name} module]\n"
                f"Ready to implement with application layer"
            )
            info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(info)
            layout.addStretch()

            self.tabs.add_module_tab(module_name, placeholder)

    def _on_module_selected(self, module_name: str) -> None:
        """Handle module selection from navigation."""
        logger.info(f"Selected module: {module_name}")
        self.tabs.select_module(module_name)

    def _on_chat_message(self, message: str) -> None:
        """Handle chat message from user."""
        logger.info(f"Chat message: {message}")
        self.chat.add_message("User", message)

        # Simulate AI response (placeholder)
        self.chat.add_message("Assistant", "Processing your request...")

    def _update_market_bar(self) -> None:
        """Update market bar data (simulated)."""
        logger.debug("Updating market bar")
        # In production, this would fetch real data
        # For now, just log the action

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _reset_layout(self) -> None:
        """Reset the splitter layout to default proportions."""
        logger.info("Resetting layout to default")
        # Reset would be implemented in production

    def closeEvent(self, event) -> None:
        """Clean up on window close."""
        self.market_timer.stop()
        logger.info("Closing Quantum Terminal")
        event.accept()
