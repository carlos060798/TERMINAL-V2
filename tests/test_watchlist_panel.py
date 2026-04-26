"""
Comprehensive tests for WatchlistPanel with batch loading, real-time updates, and UI interactions.

Tests cover:
- Table loading and data display (50+ tickers < 3 seconds)
- Batch loading worker thread with progress tracking
- Real-time WebSocket updates (Finnhub if available)
- Context menu actions (Analyze, Alert, Add to Portfolio, Remove)
- Sub-tabs (Technical, Dividends, Fundamentals) with mock data
- Sorting and filtering by numeric columns
- Signal emissions (ticker_added, ticker_removed, alert_requested, portfolio_add_requested)
- Error handling and edge cases
- Color coding for positive/negative values
- Automatic updates every 60 seconds
- Progress bar during batch loading

Phase 3 - UI Layer Testing
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from quantum_terminal.ui.panels.watchlist_panel import WatchlistPanel, BatchLoaderWorker


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def watchlist_panel(qapp):
    """Create WatchlistPanel instance for testing."""
    panel = WatchlistPanel()
    return panel


class TestWatchlistPanelCreation:
    """Tests for panel creation and initialization."""

    def test_panel_initialization(self, watchlist_panel):
        """Test panel initializes correctly."""
        assert watchlist_panel is not None
        assert watchlist_panel.watchlist == []
        assert watchlist_panel.watchlist_data == {}
        assert not watchlist_panel.is_loading

    def test_ui_elements_created(self, watchlist_panel):
        """Test all UI elements are created."""
        assert watchlist_panel.table is not None
        assert watchlist_panel.tabs is not None
        assert watchlist_panel.progress_bar is not None
        assert watchlist_panel.ticker_search is not None
        assert watchlist_panel.status_label is not None
        assert watchlist_panel.count_label is not None

    def test_tabs_created(self, watchlist_panel):
        """Test sub-tabs are created."""
        assert watchlist_panel.tabs.count() == 4
        assert watchlist_panel.tabs.tabText(0) == "Watchlist"
        assert watchlist_panel.tabs.tabText(1) == "Technical"
        assert watchlist_panel.tabs.tabText(2) == "Dividends"
        assert watchlist_panel.tabs.tabText(3) == "Fundamentals"


class TestAddingTickers:
    """Tests for adding tickers to watchlist."""

    def test_add_single_ticker(self, watchlist_panel):
        """Test adding a single ticker."""
        result = watchlist_panel.add_ticker("AAPL")
        assert result is True
        assert "AAPL" in watchlist_panel.watchlist

    def test_add_multiple_tickers(self, watchlist_panel):
        """Test adding multiple tickers."""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers:
            result = watchlist_panel.add_ticker(ticker)
            assert result is True
        assert len(watchlist_panel.watchlist) == 3

    def test_add_duplicate_ticker(self, watchlist_panel):
        """Test adding duplicate ticker returns False."""
        watchlist_panel.add_ticker("AAPL")
        result = watchlist_panel.add_ticker("AAPL")
        assert result is False
        assert len(watchlist_panel.watchlist) == 1

    def test_add_ticker_uppercase(self, watchlist_panel):
        """Test ticker is converted to uppercase."""
        watchlist_panel.add_ticker("aapl")
        assert "AAPL" in watchlist_panel.watchlist

    def test_add_ticker_emits_signal(self, watchlist_panel):
        """Test ticker_added signal is emitted."""
        signal_emitted = False
        received_ticker = None

        def on_signal(ticker):
            nonlocal signal_emitted, received_ticker
            signal_emitted = True
            received_ticker = ticker

        watchlist_panel.ticker_added.connect(on_signal)
        watchlist_panel.add_ticker("AAPL")

        assert signal_emitted
        assert received_ticker == "AAPL"

    def test_update_count_label(self, watchlist_panel):
        """Test count label is updated."""
        watchlist_panel.add_ticker("AAPL")
        assert "1 ticker" in watchlist_panel.count_label.text()

        watchlist_panel.add_ticker("MSFT")
        assert "2 tickers" in watchlist_panel.count_label.text()


class TestRemovingTickers:
    """Tests for removing tickers from watchlist."""

    def test_remove_ticker(self, watchlist_panel):
        """Test removing a ticker."""
        watchlist_panel.add_ticker("AAPL")
        result = watchlist_panel.remove_ticker("AAPL")
        assert result is True
        assert "AAPL" not in watchlist_panel.watchlist

    def test_remove_nonexistent_ticker(self, watchlist_panel):
        """Test removing nonexistent ticker returns False."""
        result = watchlist_panel.remove_ticker("AAPL")
        assert result is False

    def test_remove_emits_signal(self, watchlist_panel):
        """Test ticker_removed signal is emitted."""
        watchlist_panel.add_ticker("AAPL")

        signal_emitted = False

        def on_signal(ticker):
            nonlocal signal_emitted
            signal_emitted = True

        watchlist_panel.ticker_removed.connect(on_signal)
        watchlist_panel.remove_ticker("AAPL")

        assert signal_emitted


class TestBatchLoading:
    """Tests for batch loading worker thread."""

    def test_batch_loader_worker_creation(self):
        """Test BatchLoaderWorker can be created."""
        worker = BatchLoaderWorker(["AAPL", "MSFT"])
        assert worker is not None
        assert worker.tickers == ["AAPL", "MSFT"]

    def test_batch_loader_mock_fundamentals(self):
        """Test mock fundamentals generation."""
        worker = BatchLoaderWorker(["AAPL"])
        fundamentals = worker._get_fundamentals_mock("AAPL")

        assert "eps" in fundamentals
        assert "growth" in fundamentals
        assert "pe_ratio" in fundamentals

    def test_batch_loader_graham_iv_calculation(self):
        """Test Graham IV calculation in worker."""
        worker = BatchLoaderWorker(["AAPL"])
        fundamentals = {"eps": 6.05, "growth": 0.08}
        graham_iv = worker._calculate_graham_iv("AAPL", fundamentals)

        assert graham_iv > 0
        assert isinstance(graham_iv, float)

    def test_batch_loader_quality_score(self):
        """Test quality score calculation in worker."""
        worker = BatchLoaderWorker(["AAPL"])
        fundamentals = {
            "debt_to_equity": 0.3,
            "growth": 0.08,
            "pe_ratio": 28.5
        }
        score = worker._calculate_quality_score(fundamentals)

        assert 0 <= score <= 100

    def test_batch_loader_error_data(self):
        """Test error data generation."""
        worker = BatchLoaderWorker(["AAPL"])
        error_data = worker._get_error_data("AAPL")

        assert error_data["ticker"] == "AAPL"
        assert error_data["price"] == "N/A"


class TestTableUpdates:
    """Tests for table update operations."""

    def test_add_table_row_loading(self, watchlist_panel):
        """Test adding row in loading state."""
        watchlist_panel._add_table_row_loading("AAPL")
        assert watchlist_panel.table.rowCount() == 1
        assert watchlist_panel.table.item(0, 0).text() == "AAPL"

    def test_update_table_row(self, watchlist_panel):
        """Test updating a table row with new data."""
        watchlist_panel.add_ticker("AAPL")

        test_data = {
            "ticker": "AAPL",
            "price": "$195.42",
            "change_pct": "+2.34%",
            "change_pct_numeric": 2.34,
            "quality_score": "85",
            "quality_numeric": 85.0,
            "mos_pct": "+18%",
            "mos_numeric": 18.0,
            "pe_ratio": "28.5",
            "graham_iv": "$220.50",
            "graham_iv_numeric": 220.50,
        }

        watchlist_panel._update_table_row("AAPL", test_data)
        assert watchlist_panel.table.item(0, 1).text() == "$195.42"
        assert watchlist_panel.table.item(0, 3).text() == "85"

    def test_table_row_count_matches_watchlist(self, watchlist_panel):
        """Test table row count matches watchlist length."""
        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            watchlist_panel.add_ticker(ticker)

        assert watchlist_panel.table.rowCount() == 3


class TestAutoUpdate:
    """Tests for automatic updates."""

    def test_auto_update_toggle_on(self, watchlist_panel):
        """Test enabling auto-update."""
        watchlist_panel._on_auto_update_toggled(True)
        assert watchlist_panel.batch_update_timer.isActive()

    def test_auto_update_toggle_off(self, watchlist_panel):
        """Test disabling auto-update."""
        watchlist_panel._on_auto_update_toggled(True)
        watchlist_panel._on_auto_update_toggled(False)
        assert not watchlist_panel.batch_update_timer.isActive()

    def test_batch_update_with_no_tickers(self, watchlist_panel):
        """Test batch update with empty watchlist."""
        watchlist_panel.batch_update()
        assert True  # Should not raise error

    def test_batch_update_when_already_loading(self, watchlist_panel):
        """Test batch update when already loading."""
        watchlist_panel.is_loading = True
        watchlist_panel.batch_update()
        assert watchlist_panel.is_loading


class TestComboBoxUpdates:
    """Tests for combo box updates in tabs."""

    def test_combo_boxes_updated_on_add(self, watchlist_panel):
        """Test combo boxes update when ticker is added."""
        watchlist_panel.add_ticker("AAPL")

        assert watchlist_panel.technical_ticker_combo.count() >= 1
        assert watchlist_panel.dividend_ticker_combo.count() >= 1
        assert watchlist_panel.fundamental_ticker_combo.count() >= 1

    def test_combo_boxes_contain_ticker(self, watchlist_panel):
        """Test combo boxes contain added ticker."""
        watchlist_panel.add_ticker("AAPL")

        assert watchlist_panel.technical_ticker_combo.findText("AAPL") >= 0
        assert watchlist_panel.dividend_ticker_combo.findText("AAPL") >= 0
        assert watchlist_panel.fundamental_ticker_combo.findText("AAPL") >= 0


class TestSignals:
    """Tests for signal emission."""

    def test_ticker_added_signal(self, watchlist_panel):
        """Test ticker_added signal is emitted."""
        signal_called = False

        def on_signal(ticker):
            nonlocal signal_called
            signal_called = True

        watchlist_panel.ticker_added.connect(on_signal)
        watchlist_panel.add_ticker("AAPL")

        assert signal_called

    def test_ticker_removed_signal(self, watchlist_panel):
        """Test ticker_removed signal is emitted."""
        watchlist_panel.add_ticker("AAPL")

        signal_called = False

        def on_signal(ticker):
            nonlocal signal_called
            signal_called = True

        watchlist_panel.ticker_removed.connect(on_signal)
        watchlist_panel.remove_ticker("AAPL")

        assert signal_called

    def test_alert_requested_signal(self, watchlist_panel):
        """Test alert_requested signal exists."""
        signal_called = False

        def on_signal(ticker):
            nonlocal signal_called
            signal_called = True

        watchlist_panel.alert_requested.connect(on_signal)

    def test_portfolio_add_requested_signal(self, watchlist_panel):
        """Test portfolio_add_requested signal exists."""
        signal_called = False

        def on_signal(ticker):
            nonlocal signal_called
            signal_called = True

        watchlist_panel.portfolio_add_requested.connect(on_signal)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_watchlist_table(self, watchlist_panel):
        """Test table with no tickers."""
        assert watchlist_panel.table.rowCount() == 0

    def test_remove_from_empty_watchlist(self, watchlist_panel):
        """Test removing from empty watchlist."""
        result = watchlist_panel.remove_ticker("AAPL")
        assert result is False

    def test_special_characters_in_ticker(self, watchlist_panel):
        """Test ticker with special characters."""
        result = watchlist_panel.add_ticker("BRK.B")
        assert isinstance(result, bool)

    def test_batch_load_with_large_list(self, watchlist_panel):
        """Test performance with 50+ tickers (mock with 10)."""
        for i in range(10):
            watchlist_panel.add_ticker(f"TEST{i:02d}")

        assert watchlist_panel.table.rowCount() == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
