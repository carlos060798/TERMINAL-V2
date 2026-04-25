"""
Tests for TickerSearch widget.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from quantum_terminal.ui.widgets import TickerSearch


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_tickers():
    """Sample ticker list."""
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "META", "NVDA", "NFLX", "JPM", "BAC"
    ]


@pytest.fixture
def ticker_search(qapp, sample_tickers):
    """Create TickerSearch instance."""
    return TickerSearch(tickers=sample_tickers)


def test_ticker_search_creation(ticker_search, sample_tickers):
    """Test TickerSearch creation."""
    assert ticker_search is not None
    assert ticker_search.tickers == sample_tickers


def test_set_tickers(ticker_search):
    """Test setting new ticker list."""
    new_tickers = ["AAPL", "MSFT", "GOOGL"]
    ticker_search.set_tickers(new_tickers)

    assert ticker_search.tickers == new_tickers


def test_add_ticker(ticker_search):
    """Test adding single ticker."""
    initial_count = len(ticker_search.tickers)

    ticker_search.add_ticker("NEW")

    assert len(ticker_search.tickers) == initial_count + 1
    assert "NEW" in ticker_search.tickers


def test_add_duplicate_ticker(ticker_search):
    """Test adding duplicate ticker."""
    initial_count = len(ticker_search.tickers)

    ticker_search.add_ticker("AAPL")  # Already exists

    assert len(ticker_search.tickers) == initial_count  # No duplicates


def test_search_exact_prefix(ticker_search):
    """Test exact prefix matching."""
    results = ticker_search.search("AA")

    assert "AAPL" in results
    assert results[0] == "AAPL"  # Exact match first


def test_search_fuzzy_match(ticker_search):
    """Test fuzzy matching."""
    results = ticker_search.search("AP")

    assert "AAPL" in results


def test_search_case_insensitive(ticker_search):
    """Test case-insensitive search."""
    results_upper = ticker_search.search("MS")
    results_lower = ticker_search.search("ms")

    assert results_upper == results_lower
    assert "MSFT" in results_upper


def test_search_empty_query(ticker_search):
    """Test search with empty query."""
    results = ticker_search.search("")

    assert len(results) == 10  # Returns first 10 by default
    assert "AAPL" in results


def test_search_no_matches(ticker_search):
    """Test search with no matches."""
    results = ticker_search.search("XYZ")

    assert len(results) == 0


def test_get_selected(ticker_search):
    """Test getting selected ticker."""
    ticker_search.search_input.setText("AAPL")

    selected = ticker_search.get_selected()

    assert selected == "AAPL"


def test_get_selected_whitespace(ticker_search):
    """Test getting selected with whitespace."""
    ticker_search.search_input.setText("  MSFT  ")

    selected = ticker_search.get_selected()

    assert selected == "MSFT"


def test_clear(ticker_search):
    """Test clearing search."""
    ticker_search.search_input.setText("AAPL")

    ticker_search.clear()

    assert ticker_search.search_input.text() == ""
    assert ticker_search.suggestion_list.count() == 0


def test_ticker_selected_signal(ticker_search):
    """Test ticker_selected signal."""
    signal_emitted = False
    received_ticker = None

    def on_signal(ticker):
        nonlocal signal_emitted, received_ticker
        signal_emitted = True
        received_ticker = ticker

    ticker_search.ticker_selected.connect(on_signal)
    ticker_search.search_input.setText("AAPL")
    ticker_search._on_return_pressed()

    assert signal_emitted
    assert received_ticker == "AAPL"


def test_search_text_changed_signal(ticker_search):
    """Test search_text_changed signal."""
    signal_emitted = False
    received_text = None

    def on_signal(text):
        nonlocal signal_emitted, received_text
        signal_emitted = True
        received_text = text

    ticker_search.search_text_changed.connect(on_signal)
    ticker_search.search_input.setText("AA")

    assert signal_emitted
    assert received_text == "AA"
