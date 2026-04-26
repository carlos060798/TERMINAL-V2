"""
Tests for DashboardPanel.

Test suite for the Dashboard panel UI component.
Verifies KPI display, data loading, and chart updates.

Phase 3 - UI Testing
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy

from quantum_terminal.ui.panels import DashboardPanel


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def dashboard(app):
    """Create a DashboardPanel instance for testing."""
    return DashboardPanel()


class TestDashboardPanelInitialization:
    """Test DashboardPanel initialization."""

    def test_panel_creates_without_error(self, dashboard):
        """Test that panel initializes without error."""
        assert dashboard is not None

    def test_panel_has_metric_cards(self, dashboard):
        """Test that all KPI cards are created."""
        assert hasattr(dashboard, 'card_total_value')
        assert hasattr(dashboard, 'card_pnl_usd')
        assert hasattr(dashboard, 'card_pnl_pct')
        assert hasattr(dashboard, 'card_sharpe')
        assert hasattr(dashboard, 'card_sortino')
        assert hasattr(dashboard, 'card_var')

    def test_panel_has_charts(self, dashboard):
        """Test that charts are created."""
        assert hasattr(dashboard, 'heatmap')
        assert hasattr(dashboard, 'equity_chart')

    def test_panel_has_refresh_timer(self, dashboard):
        """Test that refresh timer is initialized."""
        assert hasattr(dashboard, 'refresh_timer')
        assert dashboard.refresh_timer is not None


class TestPortfolioDataLoading:
    """Test portfolio data loading."""

    def test_load_portfolio_data_calls_update_metrics(self, dashboard):
        """Test that loading data triggers metrics update."""
        with patch.object(dashboard, 'update_metrics') as mock_update:
            dashboard.load_portfolio_data()
            mock_update.assert_called_once()

    def test_load_portfolio_data_with_period(self, dashboard):
        """Test loading data with different time periods."""
        periods = ["1D", "1W", "1M", "3M", "YTD", "1Y"]
        for period in periods:
            dashboard.load_portfolio_data(period=period)
            assert dashboard.portfolio_data is not None

    def test_load_portfolio_data_stores_data(self, dashboard):
        """Test that loaded data is stored."""
        dashboard.load_portfolio_data()
        assert len(dashboard.portfolio_data) > 0


class TestMetricsUpdate:
    """Test metrics update functionality."""

    def test_update_metrics_with_valid_data(self, dashboard):
        """Test updating metrics with valid data."""
        dashboard.portfolio_data = {
            "total_value": "$100,000.00",
            "total_value_change_pct": "+1.5%",
            "pnl_usd": "$1,500.00",
            "pnl_pct": "+1.5%",
            "pnl_trend": "+0.5%",
            "sharpe_ratio": "1.25",
            "sortino_ratio": "1.85",
            "var_95": "$5,000.00",
            "max_drawdown": "-5.0%",
            "beta": "1.0",
            "avg_quality_score": "75.0/100",
            "correlation_spy": "0.85",
        }

        # Should not raise exception
        dashboard.update_metrics()

    def test_update_metrics_with_empty_data(self, dashboard):
        """Test updating metrics with empty data."""
        dashboard.portfolio_data = {}
        # Should not raise exception
        dashboard.update_metrics()

    def test_update_metrics_with_invalid_data(self, dashboard):
        """Test updating metrics with invalid data types."""
        dashboard.portfolio_data = {
            "total_value": None,
            "pnl_usd": "invalid",
        }
        # Should not raise exception
        dashboard.update_metrics()


class TestEquityCurveUpdate:
    """Test equity curve updates."""

    def test_refresh_equity_curve_with_valid_data(self, dashboard):
        """Test refreshing equity curve with valid data."""
        dates = ["2024-01-01", "2024-02-01", "2024-03-01"]
        values = [100000, 105000, 110000]

        # Should not raise exception
        dashboard.refresh_equity_curve(dates, values)

    def test_refresh_equity_curve_with_empty_data(self, dashboard):
        """Test refreshing equity curve with empty data."""
        dashboard.refresh_equity_curve([], [])

    def test_refresh_equity_curve_with_mismatched_lengths(self, dashboard):
        """Test refreshing equity curve with mismatched data lengths."""
        dates = ["2024-01-01", "2024-02-01"]
        values = [100000, 105000, 110000]  # Extra value

        # Should handle gracefully
        dashboard.refresh_equity_curve(dates, values)


class TestAutoRefresh:
    """Test auto-refresh functionality."""

    def test_start_auto_refresh(self, dashboard):
        """Test starting auto-refresh."""
        dashboard.start_auto_refresh(interval_seconds=30)
        assert dashboard.refresh_timer.isActive()

    def test_stop_auto_refresh(self, dashboard):
        """Test stopping auto-refresh."""
        dashboard.start_auto_refresh()
        dashboard.stop_auto_refresh()
        assert not dashboard.refresh_timer.isActive()

    def test_auto_refresh_interval(self, dashboard):
        """Test auto-refresh interval is set correctly."""
        interval = 45
        dashboard.start_auto_refresh(interval_seconds=interval)
        assert dashboard.refresh_timer.interval() == interval * 1000


class TestSignals:
    """Test DashboardPanel signals."""

    def test_sector_clicked_signal(self, dashboard):
        """Test sector_clicked signal is emitted."""
        spy = QSignalSpy(dashboard.sector_clicked)
        dashboard._on_sector_clicked("Technology")
        assert len(spy) == 1

    def test_refresh_requested_signal(self, dashboard):
        """Test refresh_requested signal is emitted."""
        spy = QSignalSpy(dashboard.refresh_requested)
        dashboard._on_refresh_clicked()
        assert len(spy) == 1


class TestMockData:
    """Test mock data generation."""

    def test_mock_data_structure(self, dashboard):
        """Test that mock data has expected structure."""
        data = dashboard._get_mock_portfolio_data()

        expected_keys = [
            "total_value", "pnl_usd", "sharpe_ratio",
            "sortino_ratio", "var_95", "max_drawdown",
            "beta", "avg_quality_score", "correlation_spy",
            "sector_allocation", "equity_curve"
        ]

        for key in expected_keys:
            assert key in data

    def test_mock_sector_allocation(self, dashboard):
        """Test mock sector allocation data."""
        data = dashboard._get_mock_portfolio_data()
        sectors = data["sector_allocation"]

        assert "Technology" in sectors
        assert "Financials" in sectors
        assert len(sectors) > 0

    def test_mock_equity_curve(self, dashboard):
        """Test mock equity curve data."""
        data = dashboard._get_mock_portfolio_data()
        curve = data["equity_curve"]

        assert len(curve["dates"]) == len(curve["values"])
        assert len(curve["dates"]) == len(curve["drawdown"])


class TestPeriodSelection:
    """Test time period selection."""

    def test_period_changed_signal(self, dashboard):
        """Test period change handling."""
        with patch.object(dashboard, 'load_portfolio_data') as mock_load:
            dashboard._on_period_changed("1W")
            mock_load.assert_called_once_with(period="1W")

    def test_all_periods_supported(self, dashboard):
        """Test that all UI periods are supported."""
        periods = ["1D", "1W", "1M", "3M", "YTD", "1Y", "All"]
        for period in periods:
            # Should not raise exception
            dashboard._on_period_changed(period)


class TestErrorHandling:
    """Test error handling."""

    def test_load_portfolio_data_error_logging(self, dashboard):
        """Test that errors are logged properly."""
        with patch.object(dashboard, '_get_mock_portfolio_data',
                         side_effect=Exception("Test error")):
            # Should not raise, but log error
            dashboard.load_portfolio_data()

    def test_update_metrics_error_logging(self, dashboard):
        """Test metrics update error handling."""
        dashboard.portfolio_data = {"invalid": "structure"}
        # Should not raise exception
        dashboard.update_metrics()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
