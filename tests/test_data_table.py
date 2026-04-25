"""
Tests for DataTable widget.
"""

import pytest
from PyQt6.QtWidgets import QApplication
import pandas as pd
from quantum_terminal.ui.widgets import DataTable


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def data_table(qapp):
    """Create DataTable instance."""
    columns = ["Ticker", "Price", "Change %", "Volume"]
    table = DataTable(columns=columns)
    return table


def test_data_table_creation(data_table):
    """Test DataTable creation."""
    assert data_table is not None
    assert data_table.columns == ["Ticker", "Price", "Change %", "Volume"]
    assert len(data_table.data) == 0


def test_set_data(data_table):
    """Test loading data into table."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
    ]

    data_table.set_data(data)

    assert len(data_table.data) == 2
    assert data_table.data[0]["Ticker"] == "AAPL"
    assert data_table.data[1]["Change %"] == -1.2


def test_set_dataframe(data_table):
    """Test loading DataFrame into table."""
    df = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "GOOGL"],
        "Price": [150.5, 320.25, 140.0],
        "Change %": [2.5, -1.2, 0.8],
        "Volume": [1000000, 500000, 750000],
    })

    data_table.set_dataframe(df)

    assert len(data_table.data) == 3
    assert data_table.data[2]["Ticker"] == "GOOGL"


def test_add_row(data_table):
    """Test adding single row."""
    data_table.set_data([])

    row = {"Ticker": "TSLA", "Price": 250.0, "Change %": 5.0, "Volume": 2000000}
    data_table.add_row(row)

    assert len(data_table.data) == 1
    assert data_table.data[0]["Ticker"] == "TSLA"


def test_add_rows(data_table):
    """Test adding multiple rows."""
    data_table.set_data([])

    rows = [
        {"Ticker": "TSLA", "Price": 250.0, "Change %": 5.0, "Volume": 2000000},
        {"Ticker": "META", "Price": 300.0, "Change %": 3.5, "Volume": 1500000},
    ]
    data_table.add_rows(rows)

    assert len(data_table.data) == 2


def test_remove_row(data_table):
    """Test removing row."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
    ]
    data_table.set_data(data)

    data_table.remove_row(0)

    assert len(data_table.data) == 1
    assert data_table.data[0]["Ticker"] == "MSFT"


def test_clear(data_table):
    """Test clearing table."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
    ]
    data_table.set_data(data)

    data_table.clear()

    assert len(data_table.data) == 0
    assert data_table.table.rowCount() == 0


def test_sort_by_column_numeric(data_table):
    """Test sorting by numeric column."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
        {"Ticker": "GOOGL", "Price": 140.0, "Change %": 0.8, "Volume": 750000},
    ]
    data_table.set_data(data)

    # Sort by Price descending
    data_table.sort_by_column(1, ascending=False)

    assert data_table.data[0]["Ticker"] == "MSFT"  # 320.25
    assert data_table.data[1]["Ticker"] == "AAPL"  # 150.50
    assert data_table.data[2]["Ticker"] == "GOOGL"  # 140.0


def test_sort_by_column_string(data_table):
    """Test sorting by string column."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
        {"Ticker": "GOOGL", "Price": 140.0, "Change %": 0.8, "Volume": 750000},
    ]
    data_table.set_data(data)

    # Sort by Ticker ascending
    data_table.sort_by_column(0, ascending=True)

    assert data_table.data[0]["Ticker"] == "AAPL"
    assert data_table.data[1]["Ticker"] == "GOOGL"
    assert data_table.data[2]["Ticker"] == "MSFT"


def test_get_selected_row(data_table):
    """Test getting selected row."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
    ]
    data_table.set_data(data)

    # Simulate selection
    data_table.table.selectRow(0)
    selected = data_table.get_selected_row()

    assert selected is not None
    assert selected["Ticker"] == "AAPL"


def test_get_all_data(data_table):
    """Test getting all data."""
    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
        {"Ticker": "MSFT", "Price": 320.25, "Change %": -1.2, "Volume": 500000},
    ]
    data_table.set_data(data)

    all_data = data_table.get_all_data()

    assert len(all_data) == 2
    assert all_data[0]["Ticker"] == "AAPL"


def test_row_selected_signal(data_table):
    """Test row_selected signal."""
    signal_emitted = False
    received_row = None

    def on_signal(row):
        nonlocal signal_emitted, received_row
        signal_emitted = True
        received_row = row

    data = [
        {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5, "Volume": 1000000},
    ]
    data_table.set_data(data)

    data_table.row_selected.connect(on_signal)
    data_table.table.selectRow(0)

    assert signal_emitted
    assert received_row == 0
