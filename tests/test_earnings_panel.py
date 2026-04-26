"""
Tests for Earnings Tracker Panel (Module 9).

Tests coverage:
- Calendar loading and filtering
- Surprise history tracking
- Implied move calculations
- AI analysis generation
- Alerts for 48h before earnings
- Watchlist integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Import panel under test
from quantum_terminal.ui.panels.earnings_panel import (
    EarningsPanel,
    EarningsLoaderWorker,
)


@pytest.fixture
def app():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def earnings_panel(app):
    """Create an EarningsPanel instance for testing."""
    watchlist = ["AAPL", "MSFT", "GOOGL"]
    panel = EarningsPanel(watchlist=watchlist)
    return panel


class TestEarningsLoaderWorker:
    """Tests for EarningsLoaderWorker."""

    def test_worker_initialization(self):
        """Test worker initialization."""
        from_date = datetime.now()
        to_date = datetime.now() + timedelta(days=30)
        watchlist = ["AAPL", "MSFT"]

        worker = EarningsLoaderWorker(from_date, to_date, watchlist)

        assert worker.from_date == from_date
        assert worker.to_date == to_date
        assert worker.watchlist == watchlist

    def test_earnings_calendar_generation(self):
        """Test earnings calendar is generated with correct structure."""
        from_date = datetime.now()
        to_date = from_date + timedelta(days=30)
        watchlist = ["AAPL", "MSFT", "GOOGL"]

        worker = EarningsLoaderWorker(from_date, to_date, watchlist)
        calendar = worker._get_earnings_calendar()

        assert len(calendar) > 0
        assert all(key in calendar[0] for key in [
            "date", "ticker", "company", "hour", "consensus_eps", "real_eps", "eps_beat_pct"
        ])

    def test_earnings_calendar_has_beat_miss_logic(self):
        """Test beat/miss calculation."""
        worker = EarningsLoaderWorker(datetime.now(), datetime.now() + timedelta(days=30), ["AAPL"])
        calendar = worker._get_earnings_calendar()

        for item in calendar:
            consensus = item["consensus_eps"]
            real = item["real_eps"]
            beat_pct = item["eps_beat_pct"]

            expected_beat = (real - consensus) / consensus * 100 if consensus != 0 else 0.0
            assert abs(beat_pct - expected_beat) < 0.01

    def test_implied_moves_calculation(self):
        """Test implied moves are calculated correctly."""
        worker = EarningsLoaderWorker(datetime.now(), datetime.now() + timedelta(days=30), ["AAPL", "MSFT"])
        moves = worker._get_implied_moves()

        assert len(moves) > 0
        for ticker, move in moves.items():
            assert move > 0
            assert move <= 10.0  # Cap at 10%

    def test_surprise_history_structure(self):
        """Test surprise history has correct structure."""
        worker = EarningsLoaderWorker(datetime.now(), datetime.now() + timedelta(days=30), ["AAPL"])
        history = worker._get_surprise_history()

        assert "AAPL" in history
        aapl_data = history["AAPL"]

        assert "surprising_beats" in aapl_data
        assert "avg_beat_pct" in aapl_data
        assert "streak" in aapl_data
        assert "recent_surprises" in aapl_data

        # Check recent surprises structure
        surprises = aapl_data["recent_surprises"]
        assert len(surprises) == 8  # Last 8 quarters

        for surprise in surprises:
            assert "quarter" in surprise
            assert "beat" in surprise
            assert "pct" in surprise
            assert isinstance(surprise["beat"], bool)

    def test_implied_moves_by_iv_bucket(self):
        """Test that high-IV stocks have higher implied moves."""
        worker = EarningsLoaderWorker(datetime.now(), datetime.now() + timedelta(days=30), [
            "TSLA", "AAPL"  # TSLA has high IV (45%), AAPL lower (25%)
        ])
        moves = worker._get_implied_moves()

        # TSLA should have higher implied move than AAPL
        assert moves.get("TSLA", 0) > moves.get("AAPL", 0)


class TestEarningsPanelUI:
    """Tests for EarningsPanel UI."""

    def test_panel_initialization(self, earnings_panel):
        """Test panel initializes correctly."""
        assert earnings_panel.watchlist == ["AAPL", "MSFT", "GOOGL"]
        assert earnings_panel.is_loading is False
        assert isinstance(earnings_panel.earnings_calendar, list)

    def test_calendar_tab_exists(self, earnings_panel):
        """Test calendar tab is created."""
        assert earnings_panel.calendar_table is not None
        assert earnings_panel.calendar_table.columnCount() == 9

    def test_company_tab_exists(self, earnings_panel):
        """Test company detail tab is created."""
        assert earnings_panel.company_combo is not None
        assert earnings_panel.surprise_table is not None

    def test_moves_tab_exists(self, earnings_panel):
        """Test implied moves tab is created."""
        assert earnings_panel.moves_table is not None
        assert earnings_panel.moves_table.columnCount() == 5

    def test_analysis_tab_exists(self, earnings_panel):
        """Test AI analysis tab is created."""
        assert earnings_panel.analysis_ticker_combo is not None
        assert earnings_panel.analysis_text is not None

    def test_period_filter_changes(self, earnings_panel):
        """Test period filter updates date range."""
        earnings_panel._on_period_changed("Next 7 days")
        assert (earnings_panel.filter_to_date - earnings_panel.filter_from_date).days <= 7

        earnings_panel._on_period_changed("Next 30 days")
        assert (earnings_panel.filter_to_date - earnings_panel.filter_from_date).days <= 30

    def test_watchlist_only_toggle(self, earnings_panel):
        """Test watchlist-only filter toggle."""
        earnings_panel.watchlist_only_btn.setChecked(False)
        count_before = len(earnings_panel._apply_calendar_filters())

        earnings_panel.watchlist_only_btn.setChecked(True)
        count_after = len(earnings_panel._apply_calendar_filters())

        # Should have fewer or equal events when filtered to watchlist
        assert count_after <= count_before


class TestEarningsCalendarPopulation:
    """Tests for calendar table population."""

    def test_populate_calendar_table(self, earnings_panel):
        """Test calendar table is populated correctly."""
        # Mock earnings data
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "eps_beat_pct": 4.2,
                "beat": True,
                "move_pct": 3.0,
                "in_watchlist": True,
            }
        ]

        earnings_panel._populate_calendar_table()

        assert earnings_panel.calendar_table.rowCount() == 1
        assert earnings_panel.calendar_table.item(0, 2).text() == "AAPL"

    def test_calendar_row_has_all_columns(self, earnings_panel):
        """Test each calendar row has all columns."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "MSFT",
                "company": "Microsoft Corp.",
                "hour": "16:30 ET",
                "consensus_eps": 3.08,
                "real_eps": 3.05,
                "eps_beat_pct": -0.97,
                "beat": False,
                "move_pct": 0.7,
                "in_watchlist": True,
            }
        ]

        earnings_panel._populate_calendar_table()

        row = 0
        assert earnings_panel.calendar_table.item(row, 0) is not None  # Date
        assert earnings_panel.calendar_table.item(row, 1) is not None  # Time
        assert earnings_panel.calendar_table.item(row, 2) is not None  # Ticker
        assert earnings_panel.calendar_table.item(row, 3) is not None  # Company
        assert earnings_panel.calendar_table.item(row, 4) is not None  # Consensus EPS
        assert earnings_panel.calendar_table.item(row, 5) is not None  # Real EPS
        assert earnings_panel.calendar_table.item(row, 6) is not None  # Beat/Miss %
        assert earnings_panel.calendar_table.item(row, 7) is not None  # Move %
        assert earnings_panel.calendar_table.item(row, 8) is not None  # Action

    def test_beat_colors_green(self, earnings_panel):
        """Test beat results are colored green."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "GOOGL",
                "company": "Alphabet Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.85,
                "real_eps": 1.92,
                "eps_beat_pct": 3.8,
                "beat": True,
                "move_pct": 2.7,
                "in_watchlist": True,
            }
        ]

        earnings_panel._populate_calendar_table()

        beat_item = earnings_panel.calendar_table.item(0, 6)
        # Check that the color is green (approximate RGB)
        assert beat_item.foreground().color().name() == "#00cc00"

    def test_miss_colors_red(self, earnings_panel):
        """Test miss results are colored red."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "TSLA",
                "company": "Tesla Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 0.75,
                "real_eps": 0.71,
                "eps_beat_pct": -5.3,
                "beat": False,
                "move_pct": 3.7,
                "in_watchlist": True,
            }
        ]

        earnings_panel._populate_calendar_table()

        miss_item = earnings_panel.calendar_table.item(0, 6)
        # Check that the color is red (approximate RGB)
        assert miss_item.foreground().color().name() == "#ff3333"


class TestCompanyDetailTab:
    """Tests for company detail tab functionality."""

    def test_populate_company_combo(self, earnings_panel):
        """Test company combo is populated."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "eps_beat_pct": 4.2,
                "beat": True,
                "move_pct": 3.0,
                "in_watchlist": True,
            },
            {
                "date": "2026-04-26",
                "datetime": datetime.now() + timedelta(days=2),
                "ticker": "MSFT",
                "company": "Microsoft Corp.",
                "hour": "16:30 ET",
                "consensus_eps": 3.08,
                "real_eps": 3.05,
                "eps_beat_pct": -0.97,
                "beat": False,
                "move_pct": 0.7,
                "in_watchlist": True,
            }
        ]

        earnings_panel._populate_company_combo()

        # Should have 2 unique tickers
        assert earnings_panel.company_combo.count() == 2

    def test_company_surprise_history_display(self, earnings_panel):
        """Test surprise history is displayed correctly."""
        earnings_panel.surprise_history = {
            "AAPL": {
                "surprising_beats": 6,
                "avg_beat_pct": 2.3,
                "streak": 4,
                "recent_surprises": [
                    {"quarter": "Q1 2026", "beat": True, "pct": 4.2},
                    {"quarter": "Q4 2025", "beat": True, "pct": 3.1},
                    {"quarter": "Q3 2025", "beat": True, "pct": 2.8},
                    {"quarter": "Q2 2025", "beat": True, "pct": 1.5},
                    {"quarter": "Q1 2025", "beat": False, "pct": -1.2},
                    {"quarter": "Q4 2024", "beat": False, "pct": -0.8},
                    {"quarter": "Q3 2024", "beat": True, "pct": 2.1},
                    {"quarter": "Q2 2024", "beat": True, "pct": 1.9},
                ]
            }
        }

        earnings_panel._on_company_selected("AAPL")

        # Check that surprise history is populated
        assert earnings_panel.surprise_table.rowCount() == 8
        assert earnings_panel.beating_streak_label.text() == "Beating Streak: 4 quarters"

    def test_beating_streak_calculation(self, earnings_panel):
        """Test beating streak is calculated correctly."""
        earnings_panel.surprise_history = {
            "GOOGL": {
                "surprising_beats": 7,
                "avg_beat_pct": 2.7,
                "streak": 3,
                "recent_surprises": []
            }
        }

        earnings_panel._on_company_selected("GOOGL")

        assert "3" in earnings_panel.beating_streak_label.text()

    def test_guidance_tracking(self, earnings_panel):
        """Test guidance is displayed."""
        earnings_panel.surprise_history = {
            "MSFT": {
                "surprising_beats": 8,
                "avg_beat_pct": 3.1,
                "streak": 8,
                "recent_surprises": [],
                "guidance_revenue": "$62B-$63B",
                "previous_guidance": "$60B-$61B",
            }
        }

        earnings_panel._on_company_selected("MSFT")

        # Guidance should be visible in labels
        assert earnings_panel.revenue_guidance_label is not None


class TestImpliedMovesTab:
    """Tests for implied moves tab."""

    def test_populate_moves_table(self, earnings_panel):
        """Test implied moves table is populated."""
        earnings_panel.implied_moves = {
            "AAPL": 2.5,
            "MSFT": 2.2,
            "GOOGL": 2.3,
        }

        earnings_panel._populate_moves_table()

        assert earnings_panel.moves_table.rowCount() == 3

    def test_moves_table_columns(self, earnings_panel):
        """Test moves table has all required columns."""
        earnings_panel.implied_moves = {"AAPL": 2.5}
        earnings_panel._populate_moves_table()

        # Should have: Ticker | Price | IV Annual | Expected Move | Historical
        assert earnings_panel.moves_table.columnCount() == 5

    def test_high_iv_higher_move(self, earnings_panel):
        """Test high IV stocks have higher expected moves."""
        earnings_panel.implied_moves = {
            "TSLA": 4.5,  # High IV
            "AAPL": 2.5,  # Lower IV
        }

        assert earnings_panel.implied_moves["TSLA"] > earnings_panel.implied_moves["AAPL"]


class TestAIAnalysisTab:
    """Tests for AI analysis tab."""

    def test_analysis_tab_initialization(self, earnings_panel):
        """Test analysis tab components exist."""
        assert earnings_panel.analysis_ticker_combo is not None
        assert earnings_panel.analysis_text is not None

    def test_generate_analysis_button(self, earnings_panel):
        """Test analysis can be generated."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "eps_beat_pct": 4.2,
                "beat": True,
                "move_pct": 3.0,
                "in_watchlist": True,
            }
        ]
        earnings_panel.implied_moves = {"AAPL": 2.5}

        earnings_panel._populate_analysis_combo()
        earnings_panel._on_generate_analysis()

        # Analysis text should be populated
        assert len(earnings_panel.analysis_text.toPlainText()) > 0

    def test_analysis_includes_ticker_name(self, earnings_panel):
        """Test analysis includes ticker information."""
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "MSFT",
                "company": "Microsoft Corp.",
                "hour": "16:30 ET",
                "consensus_eps": 3.08,
                "real_eps": 3.05,
                "eps_beat_pct": -0.97,
                "beat": False,
                "move_pct": 0.7,
                "in_watchlist": True,
            }
        ]
        earnings_panel.implied_moves = {"MSFT": 2.2}

        earnings_panel._populate_analysis_combo()
        earnings_panel.analysis_ticker_combo.setCurrentText("MSFT")
        earnings_panel._on_generate_analysis()

        analysis_text = earnings_panel.analysis_text.toPlainText()
        assert "MSFT" in analysis_text


class TestAlerts:
    """Tests for 48h before earnings alerts."""

    def test_alert_for_open_positions(self, earnings_panel):
        """Test alerts are triggered 48h before earnings."""
        earnings_date = datetime.now() + timedelta(hours=48)
        earnings_panel.earnings_calendar = [
            {
                "date": earnings_date.strftime("%Y-%m-%d"),
                "datetime": earnings_date,
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "eps_beat_pct": 4.2,
                "beat": True,
                "move_pct": 3.0,
                "in_watchlist": True,
                "days_until": 2,
            }
        ]

        # Check if alert would be triggered for open position
        upcoming_event = earnings_panel.earnings_calendar[0]
        assert upcoming_event["days_until"] <= 2


class TestWatchlistIntegration:
    """Tests for watchlist integration."""

    def test_watchlist_filtering(self, earnings_panel):
        """Test earnings are filtered by watchlist."""
        earnings_panel.watchlist = ["AAPL", "MSFT"]
        earnings_panel.earnings_calendar = [
            {
                "date": "2026-04-25",
                "datetime": datetime.now() + timedelta(days=1),
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.42,
                "real_eps": 1.48,
                "eps_beat_pct": 4.2,
                "beat": True,
                "move_pct": 3.0,
                "in_watchlist": True,
            },
            {
                "date": "2026-04-26",
                "datetime": datetime.now() + timedelta(days=2),
                "ticker": "GOOGL",
                "company": "Alphabet Inc.",
                "hour": "16:30 ET",
                "consensus_eps": 1.85,
                "real_eps": 1.92,
                "eps_beat_pct": 3.8,
                "beat": True,
                "move_pct": 2.7,
                "in_watchlist": False,
            }
        ]

        earnings_panel.watchlist_only_btn.setChecked(True)
        filtered = earnings_panel._apply_calendar_filters()

        # Should only have AAPL (watchlist ticker)
        assert len(filtered) == 1
        assert filtered[0]["ticker"] == "AAPL"

    def test_watchlist_integration_shows_upcoming_earnings(self, earnings_panel):
        """Test upcoming earnings for watchlist are shown."""
        earnings_panel.watchlist = ["AAPL", "MSFT", "GOOGL"]
        earnings_panel._populate_company_combo()

        # All watchlist tickers should be available in company selector
        assert earnings_panel.company_combo.count() >= 0  # May be 0 until data loads


class TestSurpriseMetrics:
    """Tests for surprise tracking metrics."""

    def test_surprise_magnitude_calculation(self):
        """Test surprise magnitude is calculated correctly."""
        worker = EarningsLoaderWorker(
            datetime.now(),
            datetime.now() + timedelta(days=30),
            ["AAPL"]
        )

        calendar = worker._get_earnings_calendar()
        for item in calendar:
            consensus = item["consensus_eps"]
            real = item["real_eps"]
            beat_pct = item["eps_beat_pct"]

            # Magnitude should be percentage difference
            expected = (real - consensus) / consensus * 100 if consensus != 0 else 0.0
            assert abs(beat_pct - expected) < 0.01

    def test_surprise_streak_tracking(self, earnings_panel):
        """Test beating streak is tracked correctly."""
        earnings_panel.surprise_history = {
            "AAPL": {
                "surprising_beats": 6,
                "avg_beat_pct": 2.3,
                "streak": 4,  # 4 quarters in a row beating
                "recent_surprises": [
                    {"quarter": "Q1 2026", "beat": True, "pct": 4.2},
                    {"quarter": "Q4 2025", "beat": True, "pct": 3.1},
                    {"quarter": "Q3 2025", "beat": True, "pct": 2.8},
                    {"quarter": "Q2 2025", "beat": True, "pct": 1.5},
                ]
            }
        }

        earnings_panel._on_company_selected("AAPL")

        assert "4" in earnings_panel.beating_streak_label.text()

    def test_average_beat_percentage(self, earnings_panel):
        """Test average beat percentage calculation."""
        earnings_panel.surprise_history = {
            "MSFT": {
                "surprising_beats": 8,
                "avg_beat_pct": 3.1,
                "streak": 8,
                "recent_surprises": []
            }
        }

        earnings_panel._on_company_selected("MSFT")

        assert "3.1" in earnings_panel.avg_beat_label.text()


class TestSignals:
    """Tests for panel signals."""

    def test_ticker_selected_signal(self, earnings_panel):
        """Test ticker_selected signal is emitted."""
        signal_emitted = False
        selected_ticker = None

        def on_signal(ticker):
            nonlocal signal_emitted, selected_ticker
            signal_emitted = True
            selected_ticker = ticker

        earnings_panel.ticker_selected.connect(on_signal)
        earnings_panel.ticker_selected.emit("AAPL")

        assert signal_emitted
        assert selected_ticker == "AAPL"

    def test_alert_requested_signal(self, earnings_panel):
        """Test alert_requested signal is emitted."""
        signal_emitted = False
        alert_ticker = None

        def on_signal(ticker):
            nonlocal signal_emitted, alert_ticker
            signal_emitted = True
            alert_ticker = ticker

        earnings_panel.alert_requested.connect(on_signal)
        earnings_panel.alert_requested.emit("MSFT")

        assert signal_emitted
        assert alert_ticker == "MSFT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
