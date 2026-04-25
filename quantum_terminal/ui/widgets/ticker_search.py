"""
TickerSearch: Autocomplete ticker search widget with fuzzy matching.

Features: Real-time suggestions, fuzzy matching, keyboard navigation.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QCompleter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon
from typing import List, Optional, Callable
from difflib import SequenceMatcher


class TickerSearch(QWidget):
    """Autocomplete ticker search with fuzzy matching and suggestions."""

    ticker_selected = pyqtSignal(str)  # Emitted when ticker is selected
    search_text_changed = pyqtSignal(str)  # Emitted when text changes

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        on_search: Optional[Callable[[str], List[str]]] = None,
    ):
        """
        Initialize TickerSearch.

        Args:
            tickers: Initial list of tickers for autocomplete
            on_search: Optional callback for dynamic ticker fetch
        """
        super().__init__()
        self.tickers = tickers or []
        self.on_search = on_search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        self.initUI()

    def initUI(self) -> None:
        """Build search UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker (e.g., AAPL, MSFT)...")
        self.search_input.setFont(QFont("Inter", 12))
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet(self._get_input_stylesheet())
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        layout.addWidget(self.search_input)

        # Autocomplete list
        self.suggestion_list = QListWidget()
        self.suggestion_list.setFont(QFont("JetBrains Mono", 11))
        self.suggestion_list.setStyleSheet(self._get_list_stylesheet())
        self.suggestion_list.itemClicked.connect(self._on_item_selected)
        self.suggestion_list.setMaximumHeight(200)
        self.suggestion_list.hide()
        layout.addWidget(self.suggestion_list)

        self.setLayout(layout)

        # Qt Completer for native autocomplete
        self.completer_model = QStringListModel(self.tickers)
        self.completer = QCompleter(self.completer_model)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_input.setCompleter(self.completer)

    def set_tickers(self, tickers: List[str]) -> None:
        """
        Update ticker list.

        Args:
            tickers: New list of tickers
        """
        self.tickers = tickers
        self.completer_model.setStringList(tickers)

    def add_ticker(self, ticker: str) -> None:
        """Add single ticker to list."""
        if ticker not in self.tickers:
            self.tickers.append(ticker)
            self.completer_model.setStringList(self.tickers)

    def search(self, query: str) -> List[str]:
        """
        Perform fuzzy search on tickers.

        Args:
            query: Search query (partial ticker or company name)

        Returns:
            List of matching tickers
        """
        if not query:
            return self.tickers[:10]  # Return first 10 if empty

        query_upper = query.upper()
        matches = []

        for ticker in self.tickers:
            # Exact prefix match (highest priority)
            if ticker.startswith(query_upper):
                matches.append((ticker, 1.0))
            # Fuzzy match (lower priority)
            else:
                ratio = SequenceMatcher(None, query_upper, ticker).ratio()
                if ratio > 0.6:
                    matches.append((ticker, ratio))

        # Sort by match score, then alphabetically
        matches.sort(key=lambda x: (-x[1], x[0]))
        return [m[0] for m in matches[:10]]

    def get_selected(self) -> str:
        """Get currently selected ticker."""
        return self.search_input.text().upper().strip()

    def clear(self) -> None:
        """Clear search input."""
        self.search_input.clear()
        self.suggestion_list.clear()
        self.suggestion_list.hide()

    def _on_text_changed(self, text: str) -> None:
        """Handle search input change."""
        self.search_text_changed.emit(text)

        # Debounce search
        self.search_timer.stop()
        self.search_timer.start(200)

    def _on_return_pressed(self) -> None:
        """Handle Return key press."""
        selected = self.get_selected()
        if selected:
            self.ticker_selected.emit(selected)
            self.suggestion_list.hide()

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle suggestion list item click."""
        ticker = item.text()
        self.search_input.setText(ticker)
        self.ticker_selected.emit(ticker)
        self.suggestion_list.hide()

    def _perform_search(self) -> None:
        """Perform search and update suggestions."""
        query = self.search_input.text().strip()

        if not query:
            self.suggestion_list.hide()
            return

        # Get suggestions (dynamic or static)
        if self.on_search:
            suggestions = self.on_search(query)
        else:
            suggestions = self.search(query)

        # Update suggestion list
        self.suggestion_list.clear()
        for ticker in suggestions[:10]:
            item = QListWidgetItem(ticker)
            item.setFont(QFont("JetBrains Mono", 11))
            self.suggestion_list.addItem(item)

        if suggestions:
            self.suggestion_list.show()
        else:
            self.suggestion_list.hide()

    @staticmethod
    def _get_input_stylesheet() -> str:
        """Get stylesheet for search input."""
        return """
            QLineEdit {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 2px solid #3A3A3A;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #00D26A;
            }
            QLineEdit::placeholder {
                color: #606060;
            }
        """

    @staticmethod
    def _get_list_stylesheet() -> str:
        """Get stylesheet for suggestion list."""
        return """
            QListWidget {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 0px;
            }
            QListWidget::item {
                padding: 6px 8px;
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #3A3A3A;
            }
            QListWidget::item:selected {
                background-color: #00D26A;
                color: #000000;
                font-weight: bold;
            }
        """
