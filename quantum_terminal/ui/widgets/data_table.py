"""
DataTable: Enhanced QTableWidget with sorting, filtering, and resizable columns.

Features: Click-to-sort, filter-as-you-type, column resizing, row selection.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush
from typing import List, Dict, Any, Optional
import pandas as pd


class DataTable(QWidget):
    """Enhanced table widget with sorting and filtering capabilities."""

    row_selected = pyqtSignal(int)  # Emitted when row is selected
    cell_double_clicked = pyqtSignal(int, int)  # Row, column

    def __init__(self, columns: List[str], enable_filter: bool = True):
        """
        Initialize DataTable.

        Args:
            columns: Column names
            enable_filter: Show filter row
        """
        super().__init__()
        self.columns = columns
        self.enable_filter = enable_filter
        self.data: List[Dict[str, Any]] = []
        self.sorted_indices: List[int] = list(range(len(columns)))
        self.filter_active = False
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._apply_filter)

        self.initUI()

    def initUI(self) -> None:
        """Build table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filter row
        if self.enable_filter:
            filter_layout = QHBoxLayout()
            filter_layout.setContentsMargins(8, 4, 8, 4)

            self.filter_inputs: Dict[str, QLineEdit] = {}
            for col in self.columns:
                filter_input = QLineEdit()
                filter_input.setPlaceholderText(f"Filter {col}...")
                filter_input.setFont(QFont("Inter", 10))
                filter_input.setStyleSheet(
                    """
                    QLineEdit {
                        background-color: #2A2A2A;
                        color: #FFFFFF;
                        border: 1px solid #3A3A3A;
                        border-radius: 3px;
                        padding: 4px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #00D26A;
                    }
                """
                )
                filter_input.textChanged.connect(self._on_filter_changed)
                filter_layout.addWidget(filter_input)
                self.filter_inputs[col] = filter_input

            layout.addLayout(filter_layout)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setStyleSheet(self._get_stylesheet())
        self.table.setFont(QFont("JetBrains Mono", 10))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)

        # Header
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.sectionClicked.connect(self._on_header_clicked)

        # Signals
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.itemDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Load table data from list of dicts.

        Args:
            data: List of dicts with keys matching column names
        """
        self.data = data
        self.sorted_indices = list(range(len(data)))
        self._refresh_table()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """
        Load table data from DataFrame.

        Args:
            df: DataFrame to display
        """
        data = df.to_dict(orient="records")
        self.set_data(data)

    def add_row(self, row_data: Dict[str, Any]) -> None:
        """
        Add single row to table.

        Args:
            row_data: Dict with values for each column
        """
        self.data.append(row_data)
        self.sorted_indices = list(range(len(self.data)))
        self._refresh_table()

    def add_rows(self, rows: List[Dict[str, Any]]) -> None:
        """
        Add multiple rows to table.

        Args:
            rows: List of dicts
        """
        self.data.extend(rows)
        self.sorted_indices = list(range(len(self.data)))
        self._refresh_table()

    def remove_row(self, index: int) -> None:
        """Remove row by index."""
        if 0 <= index < len(self.data):
            self.data.pop(index)
            self.sorted_indices = list(range(len(self.data)))
            self._refresh_table()

    def clear(self) -> None:
        """Clear all rows."""
        self.data = []
        self.sorted_indices = []
        self.table.setRowCount(0)

    def sort_by_column(self, col_index: int, ascending: bool = True) -> None:
        """
        Sort table by column.

        Args:
            col_index: Column index
            ascending: Sort direction
        """
        if not self.data or col_index >= len(self.columns):
            return

        col_name = self.columns[col_index]
        try:
            self.data.sort(key=lambda x: float(x.get(col_name, 0)), reverse=not ascending)
        except (ValueError, TypeError):
            # Fallback to string sort if not numeric
            self.data.sort(key=lambda x: str(x.get(col_name, "")), reverse=not ascending)

        self.sorted_indices = list(range(len(self.data)))
        self._refresh_table()

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Get currently selected row data."""
        selected = self.table.selectedIndexes()
        if not selected:
            return None
        row_idx = selected[0].row()
        if 0 <= row_idx < len(self.data):
            return self.data[row_idx]
        return None

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get all table data."""
        return self.data.copy()

    def _refresh_table(self) -> None:
        """Rebuild table from data."""
        self.table.setRowCount(len(self.data))

        for row_idx, row_data in enumerate(self.data):
            for col_idx, col_name in enumerate(self.columns):
                value = row_data.get(col_name, "")
                item = QTableWidgetItem(str(value))
                item.setFont(QFont("JetBrains Mono", 10))

                # Color-code numeric values
                if isinstance(value, (int, float)):
                    if value < 0:
                        item.setForeground(QBrush(QColor("#FF3B30")))
                    elif value > 0:
                        item.setForeground(QBrush(QColor("#00D26A")))

                self.table.setItem(row_idx, col_idx, item)

    def _on_header_clicked(self, col_idx: int) -> None:
        """Handle column header click for sorting."""
        self.sort_by_column(col_idx)

    def _on_row_selected(self) -> None:
        """Handle row selection."""
        selected = self.table.selectedIndexes()
        if selected:
            self.row_selected.emit(selected[0].row())

    def _on_cell_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle cell double-click."""
        row = self.table.row(item)
        col = self.table.column(item)
        self.cell_double_clicked.emit(row, col)

    def _on_filter_changed(self) -> None:
        """Handle filter input change (debounced)."""
        self.filter_timer.stop()
        self.filter_timer.start(300)  # Wait 300ms before filtering

    def _apply_filter(self) -> None:
        """Apply filter based on filter inputs."""
        if not self.enable_filter:
            return

        # Build filter dict from inputs
        filters = {col: self.filter_inputs[col].text() for col in self.columns}

        # Filter data
        filtered_data = []
        for item in self.data:
            match = True
            for col, filter_text in filters.items():
                if filter_text and filter_text.lower() not in str(item.get(col, "")).lower():
                    match = False
                    break
            if match:
                filtered_data.append(item)

        # Update display
        self.table.setRowCount(len(filtered_data))
        for row_idx, row_data in enumerate(filtered_data):
            for col_idx, col_name in enumerate(self.columns):
                value = row_data.get(col_name, "")
                item = QTableWidgetItem(str(value))
                item.setFont(QFont("JetBrains Mono", 10))
                self.table.setItem(row_idx, col_idx, item)

    @staticmethod
    def _get_stylesheet() -> str:
        """Get stylesheet for table."""
        return """
            QTableWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #2A2A2A;
                gridline-color: #2A2A2A;
                font-family: 'JetBrains Mono';
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #2A2A2A;
            }
            QTableWidget::item:selected {
                background-color: #00D26A;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #A0A0A0;
                padding: 4px;
                border: none;
                border-right: 1px solid #2A2A2A;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #2A2A2A;
            }
        """
