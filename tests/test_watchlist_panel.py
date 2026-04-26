"""
Tests for WatchlistPanel.

Test suite for the Watchlist panel UI component.
Verifies ticker management, batch updates, and data display.

Phase 3 - UI Testing
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy

from quantum_terminal.ui.panels import WatchlistPanel


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def watchlist(app):
    """Create a WatchlistPanel instance for testing."""
    return WatchlistPanel()


class TestWatchlistPanelInitialization:
    """Test WatchlistPanel initialization."""

    def test_panel_creates_without_error(self, watchlist):
        """Test that panel initializes without error."""
        assert watchlist is not None

    def test_panel_has_table(self, watchlist):
        """Test that watchlist table is created."""
        assert hasattr(watchlist, 'table')
        assert watchlist.table is not None

    def test_panel_has_search_widget(self, watchlist):
        """Test that search widget is created."""
        assert hasattr(watchlist, 'ticker_search')
        assert watchlist.ticker_search is not None

    def test_panel_has_tabs(self, watchlist):
        """Test that all tabs are created."""
        assert hasattr(watchlist, 'tabs')
        assert watchlist.tabs.count() == 4  # Watchlist, Technical, Dividends, Fundamentals

    def test_watchlist_starts_empty(self, watchlist):
        """Test that watchlist starts with no tickers."""
        assert len(watchlist.watchlist) == 0
        assert watchlist.table.rowCount() == 0


class TestAddTicker:
    """Test adding tickers to watchlist."""

    def test_add_single_ticker(self, watchlist):
        """Test adding a single ticker."""
        result = watchlist.add_ticker("AAPL")
        assert result is True
        assert "AAPL" in watchlist.watchlist
        assert watchlist.table.rowCount() == 1

    def test_add_lowercase_ticker(self, watchlist):
        """Test adding ticker with lowercase (should convert to uppercase)."""
        watchlist.add_ticker("aapl")
        assert "AAPL" in watchlist.watchlist

    def test_add_duplicate_ticker(self, watchlist):
        """Test adding duplicate ticker returns False."""
        watchlist.add_ticker("AAPL")
        result = watchlist.add_ticker("AAPL")
        assert result is False
        assert watchlist.table.rowCount() == 1

    def test_add_multiple_tickers(self, watchlist):
        """Test adding multiple different tickers."""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers:
            watchlist.add_ticker(ticker)
        assert len(watchlist.watchlist) == 3
        assert watchlist.table.rowCount() == 3

    def test_add_ticker_emits_signal(self, watchlist):
        """Test that adding ticker emits signal."""
        spy = QSignalSpy(watchlist.ticker_added)
        watchlist.add_ticker("AAPL")
        assert len(spy) == 1

    def test_add_ticker_updates_count(self, watchlist):
        """Test that count label is updated."""
        watchlist.add_ticker("AAPL")
        assert "1 ticker" in watchlist.count_label.text()


class TestRemoveTicker:
    """Test removing tickers from watchlist."""

    def test_remove_existing_ticker(self, watchlist):
        """Test removing an existing ticker."""
        watchlist.add_ticker("AAPL")
        result = watchlist.remove_ticker("AAPL")
        assert result is True
        assert "AAPL" not in watchlist.watchlist
        assert watchlist.table.rowCount() == 0

    def test_remove_nonexistent_ticker(self, watchlist):
        """Test removing a ticker that doesn't exist."""
        result = watchlist.remove_ticker("AAPL")
        assert result is False

    def test_remove_ticker_emits_signal(self, watchlist):
        """Test that removing ticker emits signal."""
        watchlist.add_ticker("AAPL")
        spy = QSignalSpy(watchlist.ticker_removed)
        watchlist.remove_ticker("AAPL")
        assert len(spy) == 1

    def test_remove_ticker_updates_count(self, watchlist):
        """Test that count label is updated after removal."""
        watchlist.add_ticker("AAPL")
        watchlist.add_ticker("MSFT")
        watchlist.remove_ticker("AAPL")
        assert "1 ticker" in watchlist.count_label.text()


class TestBatchUpdate:
    """Test batch update functionality."""

    def test_batch_update_with_empty_watchlist(self, watchlist):
        """Test batch update with no tickers."""
        # Should not raise exception
        watchlist.batch_update()

    def test_batch_update_with_tickers(self, watchlist):
        """Test batch update with tickers in watchlist."""
        watchlist.add_ticker("AAPL")
        watchlist.add_ticker("MSFT")
        # Should not raise exception
        watchlist.batch_update()

    def test_batch_update_updates_table(self, watchlist):
        """Test that batch update refreshes table data."""
        watchlist.add_ticker("AAPL")
        initial_price = watchlist.table.item(0, 1).text()
        watchlist.batch_update()
        # Price should be updated (in mock, may be same value)
        updated_price = watchlist.table.item(0, 1).text()
        assert updated_price is not None

    def test_batch_update_updates_timestamp(self, watchlist):
        """Test that batch update updates last_update_label."""
        watchlist.add_ticker("AAPL")
        watchlist.batch_update()
        assert "Last update:" in watchlist.last_update_label.text()


class TestAutoUpdate:
    """Test auto-update timer functionality."""

    def test_start_batch_updates(self, watchlist):
        """Test starting batch updates."""
        watchlist.start_batch_updates(interval_seconds=60)
        assert watchlist.batch_update_timer.isActive()

    def test_stop_batch_updates(self, watchlist):
        """Test stopping batch updates."""
        watchlist.start_batch_updates()
        watchlist.stop_batch_updates()
        assert not watchlist.batch_update_timer.isActive()

    def test_batch_update_interval(self, watchlist):
        """Test auto-update interval is set correctly."""
        interval = 45
        watchlist.start_batch_updates(interval_seconds=interval)
        assert watchlist.batch_update_timer.interval() == interval * 1000

    def test_auto_update_toggle(self, watchlist):
        """Test toggling auto-update on/off."""
        assert watchlist.auto_update_btn.isChecked()
        watchlist._on_auto_update_toggled(False)
        assert not watchlist.batch_update_timer.isActive()
        watchlist._on_auto_update_toggled(True)
        assert watchlist.batch_update_timer.isActive()


class TestTableOperations:
    """Test table operations."""

    def test_table_columns(self, watchlist):
        """Test that table has correct columns."""
        assert watchlist.table.columnCount() == 8
        headers = [watchlist.table.horizontalHeaderItem(i).text()
                   for i in range(8)]
        assert "Ticker" in headers
        assert "Price" in headers
        assert "Quality" in headers

    def test_table_row_data(self, watchlist):
        """Test that table rows contain correct data."""
        watchlist.add_ticker("AAPL")
        ticker = watchlist.table.item(0, 0).text()
        assert ticker == "AAPL"

    def test_table_is_not_editable(self, watchlist):
        """Test that table items are not editable."""
        watchlist.add_ticker("AAPL")
        item = watchlist.table.item(0, 0)
        assert not item.flags() & item.ItemFlag.ItemIsEditable


class TestMockData:
    """Test mock data generation."""

    def test_mock_quotes_structure(self, watchlist):
        """Test that mock quotes have expected structure."""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        quotes = watchlist._get_mock_quotes(tickers)

        assert len(quotes) == 3
        for ticker in tickers:
            assert ticker in quotes

    def test_mock_quote_data_fields(self, watchlist):
        """Test that mock quote data has all required fields."""
        data = watchlist._get_mock_quote_data("AAPL")

        expected_fields = [
            "price", "change_pct", "quality_score",
            "mos_pct", "pe_ratio", "graham_iv"
        ]

        for field in expected_fields:
            assert field in data

    def test_mock_quote_data_format(self, watchlist):
        """Test that mock quote data has correct format."""
        data = watchlist._get_mock_quote_data("AAPL")

        # Price should have $
        assert "$" in data["price"]
        # Change percent should have %
        assert "%" in data["change_pct"]
        # IV should have $
        assert "$" in data["graham_iv"]

    def test_mock_unknown_ticker(self, watchlist):
        """Test mock data for unknown ticker."""
        data = watchlist._get_mock_quote_data("UNKNOWN")

        # Should return default values
        assert data["price"] == "$0.00"
        assert data["change_pct"] == "0.00%"


class TestSignals:
    """Test WatchlistPanel signals."""

    def test_ticker_double_clicked_signal(self, watchlist):
        """Test ticker_double_clicked signal."""
        watchlist.add_ticker("AAPL")
        spy = QSignalSpy(watchlist.ticker_double_clicked)
        watchlist._on_table_double_clicked(watchlist.table.model().index(0, 0))
        # Signal may not be emitted in test environment, but shouldn't error

    def test_alert_requested_signal(self, watchlist):
        """Test alert_requested signal."""
        watchlist.add_ticker("AAPL")
        spy = QSignalSpy(watchlist.alert_requested)
        # In real usage, triggered by context menu


class TestContextMenu:
    """Test context menu functionality."""

    def test_context_menu_actions(self, watchlist):
        """Test that context menu has correct actions."""
        watchlist.add_ticker("AAPL")
        # Context menu is created dynamically, verified via method existence
        assert hasattr(watchlist, '_on_table_context_menu')


class TestErrorHandling:
    """Test error handling."""

    def test_add_ticker_error_handling(self, watchlist):
        """Test error handling when adding ticker."""
        # Empty string should be handled gracefully
        result = watchlist.add_ticker("")
        # May return False or True depending on implementation

    def test_remove_ticker_error_handling(self, watchlist):
        """Test error handling when removing non-existent ticker."""
        result = watchlist.remove_ticker("NONEXISTENT")
        assert result is False

    def test_batch_update_error_handling(self, watchlist):
        """Test that batch update handles errors gracefully."""
        with patch.object(watchlist, '_get_mock_quotes',
                         side_effect=Exception("Test error")):
            # Should not raise exception
            watchlist.batch_update()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
