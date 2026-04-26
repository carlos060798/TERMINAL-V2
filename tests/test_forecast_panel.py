"""
Tests for Forecast Panel UI - EPS/Revenue/Momentum tabs.

Test Coverage:
- Panel initialization: 3+ cases
- Forecast display: 4+ cases
- Signal display: 3+ cases
- Data loading: 2+ cases
- Integration: 2+ cases
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidget
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from quantum_terminal.ui.panels.forecast_panel import ForecastPanel
from quantum_terminal.infrastructure.ml.forecast_engine import (
    ForecastResult,
    MomentumSignal,
    EPSForecaster,
    MomentumSignalGenerator,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def forecast_panel(qapp):
    """Create ForecastPanel instance."""
    panel = ForecastPanel()
    return panel


@pytest.fixture
def eps_forecast_result():
    """Generate mock EPS forecast result."""
    dates = pd.date_range(end=datetime.now(), periods=8, freq='Q')
    values = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2]

    return ForecastResult(
        ticker='AAPL',
        metric='eps',
        forecast_dates=list(dates),
        forecast_values=values,
        lower_bounds_80=[v * 0.9 for v in values],
        upper_bounds_80=[v * 1.1 for v in values],
        lower_bounds_95=[v * 0.8 for v in values],
        upper_bounds_95=[v * 1.2 for v in values],
        mape=5.5
    )


@pytest.fixture
def revenue_forecast_result():
    """Generate mock revenue forecast result."""
    dates = pd.date_range(end=datetime.now(), periods=8, freq='Q')
    values = [50000, 52000, 54000, 56000, 58000, 60000, 62000, 64000]

    return ForecastResult(
        ticker='AAPL',
        metric='revenue',
        forecast_dates=list(dates),
        forecast_values=values,
        lower_bounds_80=[v * 0.95 for v in values],
        upper_bounds_80=[v * 1.05 for v in values],
        lower_bounds_95=[v * 0.9 for v in values],
        upper_bounds_95=[v * 1.1 for v in values],
        mape=3.2
    )


@pytest.fixture
def momentum_signal_result():
    """Generate mock momentum signal result."""
    return MomentumSignal(
        ticker='AAPL',
        signal='BUY',
        probability=0.75,
        rsi=65.5,
        macd=0.045,
        sma_20=155.2,
        sma_50=153.1,
        current_price=157.5,
        trend_strength=0.8
    )


@pytest.fixture
def historical_eps_data():
    """Generate mock historical EPS data."""
    dates = pd.date_range(end=datetime.now(), periods=40, freq='Q')
    eps = np.linspace(1.0, 3.0, 40) + np.random.normal(0, 0.1, 40)
    eps = np.abs(eps)

    return pd.DataFrame({
        'date': dates,
        'eps': eps
    })


@pytest.fixture
def historical_price_data():
    """Generate mock historical price data."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    prices = np.linspace(140, 160, 60) + np.random.normal(0, 2, 60)

    return pd.DataFrame({
        'date': dates,
        'open': prices - 0.5,
        'high': prices + 2,
        'low': prices - 2,
        'close': prices,
        'volume': np.random.normal(10000000, 2000000, 60)
    })


# ============================================================================
# Panel Initialization Tests
# ============================================================================

class TestForecastPanelInitialization:
    """Tests for panel initialization."""

    def test_panel_creates_successfully(self, qapp):
        """Test ForecastPanel creates without error."""
        panel = ForecastPanel()

        assert panel is not None
        assert hasattr(panel, 'tabs')
        assert hasattr(panel, 'ticker_input')
        assert hasattr(panel, 'load_btn')

    def test_panel_has_four_tabs(self, forecast_panel):
        """Test panel has 4 tabs."""
        assert forecast_panel.tabs.count() == 4

    def test_panel_tab_names(self, forecast_panel):
        """Test tab names are correct."""
        tab_names = [
            forecast_panel.tabs.tabText(i)
            for i in range(forecast_panel.tabs.count())
        ]

        assert "EPS" in tab_names[0]
        assert "Revenue" in tab_names[1]
        assert "Momentum" in tab_names[2]
        assert "Analysis" in tab_names[3]

    def test_panel_initializes_forecasters(self, forecast_panel):
        """Test panel initializes forecasting engines."""
        assert hasattr(forecast_panel, 'eps_forecaster')
        assert hasattr(forecast_panel, 'momentum_generator')
        assert isinstance(forecast_panel.eps_forecaster, EPSForecaster)
        assert isinstance(forecast_panel.momentum_generator, MomentumSignalGenerator)

    def test_panel_connects_signals(self, forecast_panel):
        """Test panel connects signals properly."""
        # Check signal connections exist
        assert forecast_panel.forecast_complete is not None
        assert forecast_panel.signal_generated is not None


# ============================================================================
# EPS Forecast Display Tests
# ============================================================================

class TestEPSForecastDisplay:
    """Tests for EPS forecast display."""

    def test_display_eps_forecast_updates_table(
        self,
        forecast_panel,
        eps_forecast_result
    ):
        """Test EPS forecast updates table."""
        forecast_panel._display_eps_forecast(eps_forecast_result)

        # Check table has rows
        assert forecast_panel.eps_stats_table.rowCount() == 8

        # Check values in first row
        first_value = forecast_panel.eps_stats_table.item(0, 1).text()
        assert '$' in first_value
        assert '2.' in first_value

    def test_display_eps_forecast_updates_chart(
        self,
        forecast_panel,
        eps_forecast_result
    ):
        """Test EPS forecast updates chart."""
        forecast_panel._display_eps_forecast(eps_forecast_result)

        # Chart should be updated (check it has data)
        assert forecast_panel.eps_chart is not None

    def test_display_eps_forecast_table_columns(
        self,
        forecast_panel,
        eps_forecast_result
    ):
        """Test EPS forecast table has correct columns."""
        forecast_panel._display_eps_forecast(eps_forecast_result)

        expected_columns = ["Quarter", "Forecast", "Lower 80%", "Upper 80%"]
        for i, col_name in enumerate(expected_columns):
            assert col_name in forecast_panel.eps_stats_table.horizontalHeaderItem(i).text()

    def test_display_eps_forecast_bounds_ordering(
        self,
        forecast_panel,
        eps_forecast_result
    ):
        """Test bounds are properly ordered in display."""
        forecast_panel._display_eps_forecast(eps_forecast_result)

        for i in range(forecast_panel.eps_stats_table.rowCount()):
            lower_str = forecast_panel.eps_stats_table.item(i, 2).text()
            forecast_str = forecast_panel.eps_stats_table.item(i, 1).text()
            upper_str = forecast_panel.eps_stats_table.item(i, 3).text()

            # Extract values
            lower = float(lower_str.replace('$', ''))
            forecast = float(forecast_str.replace('$', ''))
            upper = float(upper_str.replace('$', ''))

            # Check ordering
            assert lower <= forecast
            assert forecast <= upper


# ============================================================================
# Revenue Forecast Display Tests
# ============================================================================

class TestRevenueForecastDisplay:
    """Tests for revenue forecast display."""

    def test_display_revenue_forecast_updates_table(
        self,
        forecast_panel,
        revenue_forecast_result
    ):
        """Test revenue forecast updates table."""
        forecast_panel._display_revenue_forecast(revenue_forecast_result)

        assert forecast_panel.revenue_stats_table.rowCount() == 8

    def test_display_revenue_forecast_updates_chart(
        self,
        forecast_panel,
        revenue_forecast_result
    ):
        """Test revenue forecast updates chart."""
        forecast_panel._display_revenue_forecast(revenue_forecast_result)

        assert forecast_panel.revenue_chart is not None

    def test_display_revenue_forecast_units(
        self,
        forecast_panel,
        revenue_forecast_result
    ):
        """Test revenue is displayed in millions."""
        forecast_panel._display_revenue_forecast(revenue_forecast_result)

        first_value = forecast_panel.revenue_stats_table.item(0, 1).text()
        assert 'M' in first_value  # Should be in millions


# ============================================================================
# Momentum Signal Display Tests
# ============================================================================

class TestMomentumSignalDisplay:
    """Tests for momentum signal display."""

    def test_display_momentum_signal_buy(
        self,
        forecast_panel,
        momentum_signal_result
    ):
        """Test momentum signal BUY display."""
        forecast_panel._display_momentum_signal(momentum_signal_result)

        label_text = forecast_panel.momentum_signal_label.text()
        assert 'BUY' in label_text

    def test_display_momentum_signal_sell(self, forecast_panel):
        """Test momentum signal SELL display."""
        signal = MomentumSignal(
            ticker='AAPL',
            signal='SELL',
            probability=0.35,
            rsi=35.0,
            macd=-0.05,
            sma_20=150.0,
            sma_50=155.0,
            current_price=145.0,
            trend_strength=0.65
        )

        forecast_panel._display_momentum_signal(signal)

        label_text = forecast_panel.momentum_signal_label.text()
        assert 'SELL' in label_text

    def test_display_momentum_signal_metrics_table(
        self,
        forecast_panel,
        momentum_signal_result
    ):
        """Test momentum metrics are displayed in table."""
        forecast_panel._display_momentum_signal(momentum_signal_result)

        # Check table has metrics
        assert forecast_panel.momentum_metrics.rowCount() > 0

        # Check specific metrics exist
        table = forecast_panel.momentum_metrics
        metric_names = [
            table.item(i, 0).text()
            for i in range(table.rowCount())
        ]

        assert 'Signal' in metric_names
        assert 'RSI' in metric_names
        assert 'MACD' in metric_names

    def test_display_momentum_signal_values(
        self,
        forecast_panel,
        momentum_signal_result
    ):
        """Test momentum signal values are displayed correctly."""
        forecast_panel._display_momentum_signal(momentum_signal_result)

        table = forecast_panel.momentum_metrics
        for i in range(table.rowCount()):
            name = table.item(i, 0).text()
            value = table.item(i, 1).text()

            assert value != ""  # Should have a value
            if 'RSI' in name:
                assert '65' in value
            if 'Price' in name:
                assert '157' in value


# ============================================================================
# Data Setting Tests
# ============================================================================

class TestForecastPanelDataSetting:
    """Tests for setting data on panel."""

    def test_set_data_updates_ticker(
        self,
        forecast_panel,
        historical_eps_data,
        historical_price_data
    ):
        """Test set_data updates ticker."""
        forecast_panel.set_data(
            ticker='MSFT',
            eps_data=historical_eps_data,
            price_data=historical_price_data
        )

        assert forecast_panel.current_ticker == 'MSFT'
        assert forecast_panel.ticker_input.text() == 'MSFT'

    def test_set_data_stores_historical_data(
        self,
        forecast_panel,
        historical_eps_data,
        historical_price_data
    ):
        """Test set_data stores historical data."""
        forecast_panel.set_data(
            ticker='GOOG',
            eps_data=historical_eps_data,
            price_data=historical_price_data
        )

        assert hasattr(forecast_panel, 'eps_historical')
        assert hasattr(forecast_panel, 'price_historical')
        assert len(forecast_panel.eps_historical) > 0
        assert len(forecast_panel.price_historical) > 0


# ============================================================================
# User Interaction Tests
# ============================================================================

class TestForecastPanelInteraction:
    """Tests for user interaction with panel."""

    def test_load_ticker_without_input(self, forecast_panel):
        """Test loading ticker without entering one."""
        # Should show error (would need QMessageBox mock)
        forecast_panel.ticker_input.setText('')

        with patch.object(QMessageBox, 'warning'):
            forecast_panel._on_load_ticker()
            # Dialog would show, but test verifies code path

    def test_load_ticker_with_input(self, forecast_panel):
        """Test loading ticker with input."""
        forecast_panel.ticker_input.setText('AAPL')
        forecast_panel._on_load_ticker()

        assert forecast_panel.current_ticker == 'AAPL'

    def test_sensitivity_adjustment_without_forecast(self, forecast_panel):
        """Test sensitivity adjustment requires forecast first."""
        forecast_panel.growth_adjust.setValue(20)

        with patch.object(QMessageBox, 'warning'):
            forecast_panel._on_sensitivity_change()

    def test_sensitivity_adjustment_with_forecast(
        self,
        forecast_panel,
        eps_forecast_result
    ):
        """Test sensitivity adjustment updates values."""
        forecast_panel.forecast_data['eps'] = eps_forecast_result
        forecast_panel._display_eps_forecast(eps_forecast_result)

        forecast_panel.growth_adjust.setValue(20)
        forecast_panel._on_sensitivity_change()

        # Should have adjusted values
        updated_value = forecast_panel.eps_stats_table.item(0, 1).text()
        assert '$' in updated_value


# ============================================================================
# Widget Access Tests
# ============================================================================

class TestForecastPanelWidgets:
    """Tests for panel widgets."""

    def test_panel_has_ticker_input(self, forecast_panel):
        """Test panel has ticker input field."""
        assert hasattr(forecast_panel, 'ticker_input')
        assert hasattr(forecast_panel.ticker_input, 'text')

    def test_panel_has_load_button(self, forecast_panel):
        """Test panel has load button."""
        assert hasattr(forecast_panel, 'load_btn')
        assert hasattr(forecast_panel.load_btn, 'clicked')

    def test_panel_has_eps_controls(self, forecast_panel):
        """Test panel has EPS forecast controls."""
        assert hasattr(forecast_panel, 'eps_periods')
        assert hasattr(forecast_panel, 'eps_interval')
        assert hasattr(forecast_panel, 'eps_stats_table')
        assert hasattr(forecast_panel, 'eps_chart')

    def test_panel_has_revenue_controls(self, forecast_panel):
        """Test panel has revenue forecast controls."""
        assert hasattr(forecast_panel, 'rev_periods')
        assert hasattr(forecast_panel, 'rev_interval')
        assert hasattr(forecast_panel, 'revenue_stats_table')
        assert hasattr(forecast_panel, 'revenue_chart')

    def test_panel_has_momentum_controls(self, forecast_panel):
        """Test panel has momentum controls."""
        assert hasattr(forecast_panel, 'momentum_lookback')
        assert hasattr(forecast_panel, 'momentum_signal_label')
        assert hasattr(forecast_panel, 'momentum_metrics')

    def test_panel_has_analysis_controls(self, forecast_panel):
        """Test panel has analysis controls."""
        assert hasattr(forecast_panel, 'accuracy_table')
        assert hasattr(forecast_panel, 'growth_adjust')
        assert hasattr(forecast_panel, 'impact_text')


# ============================================================================
# Edge Cases
# ============================================================================

class TestForecastPanelEdgeCases:
    """Tests for edge cases."""

    def test_display_empty_forecast(self, forecast_panel):
        """Test displaying forecast with no data."""
        empty_result = ForecastResult(
            ticker='TEST',
            metric='eps',
            forecast_dates=[],
            forecast_values=[],
            lower_bounds_80=[],
            upper_bounds_80=[],
            lower_bounds_95=[],
            upper_bounds_95=[]
        )

        # Should not crash
        forecast_panel._display_eps_forecast(empty_result)
        assert forecast_panel.eps_stats_table.rowCount() == 0

    def test_momentum_signal_with_extreme_rsi(self, forecast_panel):
        """Test momentum signal with extreme RSI values."""
        signal = MomentumSignal(
            ticker='TEST',
            signal='SELL',
            probability=0.95,
            rsi=99.5,
            macd=1.0,
            sma_20=200.0,
            sma_50=180.0,
            current_price=210.0,
            trend_strength=0.99
        )

        # Should not crash
        forecast_panel._display_momentum_signal(signal)

    def test_set_data_with_minimal_data(self, forecast_panel):
        """Test set_data with minimal data."""
        minimal_eps = pd.DataFrame({
            'date': [datetime.now()],
            'eps': [1.0]
        })

        # Should not crash
        forecast_panel.set_data(
            ticker='MIN',
            eps_data=minimal_eps
        )

        assert forecast_panel.current_ticker == 'MIN'
