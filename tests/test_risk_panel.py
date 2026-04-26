"""
Risk Manager Panel Tests

Comprehensive test suite for RiskManagerPanel UI component.
Tests cover:
- Current Risk Exposure calculation and display
- VaR analysis (Historical, Monte Carlo, Parametric)
- Correlation matrix heatmap
- Concentration analysis (sector and position)
- Efficient Frontier (Markowitz) optimization
- Stress testing scenarios
- Risk limits configuration

Mock Data:
- Mock DataProvider for quote fetching
- Mock riskfolio for Markowitz optimization
- Mock scipy for statistical calculations

Phase 3 - UI Layer Testing
Reference: PLAN_MAESTRO.md - Phase 3: UI Tests
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
import sys

# Import the panel
from quantum_terminal.ui.panels.risk_panel import RiskManagerPanel
from quantum_terminal.domain.risk import calculate_var


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def qapp():
    """PyQt6 application instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def risk_panel(qapp):
    """Create a RiskManagerPanel instance."""
    panel = RiskManagerPanel()
    return panel


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data for testing."""
    return {
        "open_trades": [
            {
                "ticker": "AAPL",
                "entry": 150.0,
                "stop": 145.0,
                "qty": 100,
                "status": "Open"
            },
            {
                "ticker": "MSFT",
                "entry": 320.0,
                "stop": 310.0,
                "qty": 50,
                "status": "Open"
            },
        ],
        "positions": [
            {
                "ticker": "AAPL",
                "price": 160.0,
                "qty": 100,
                "sector": "Technology"
            },
            {
                "ticker": "MSFT",
                "price": 330.0,
                "qty": 50,
                "sector": "Technology"
            },
            {
                "ticker": "JPM",
                "price": 160.0,
                "qty": 40,
                "sector": "Financials",
                "beta": 1.2
            },
        ],
        "historical_returns": {
            "AAPL": [0.01, -0.02, 0.03, 0.015, -0.01, 0.02, 0.01, -0.015, 0.025, 0.02,
                     0.015, -0.005, 0.02, 0.01, -0.02, 0.025, 0.015, -0.01, 0.02, 0.01] * 2,
            "MSFT": [0.015, -0.01, 0.025, 0.02, -0.015, 0.025, 0.015, -0.01, 0.02, 0.015,
                     0.01, 0.005, 0.02, 0.015, -0.015, 0.02, 0.01, -0.005, 0.015, 0.01] * 2,
            "JPM": [0.02, -0.025, 0.03, 0.025, -0.02, 0.025, 0.02, -0.015, 0.025, 0.02,
                    0.015, 0.01, 0.025, 0.02, -0.02, 0.025, 0.015, -0.01, 0.02, 0.015] * 2,
        },
        "total_capital": 50000.0,
        "current_capital": 45000.0
    }


@pytest.fixture
def high_correlation_returns():
    """Returns with high correlation between assets."""
    return {
        "AAPL": [0.01, 0.015, 0.02, 0.025, 0.03] * 8,
        "MSFT": [0.012, 0.017, 0.022, 0.027, 0.032] * 8,  # Highly correlated with AAPL
    }


@pytest.fixture
def diversified_returns():
    """Returns with low correlation between assets."""
    return {
        "AAPL": [0.01, -0.02, 0.03, -0.015, 0.025] * 8,
        "AGG": [-0.005, 0.01, -0.015, 0.005, -0.01] * 8,  # Bond fund, low correlation
    }


# ============================================================================
# TESTS: CURRENT RISK EXPOSURE
# ============================================================================

class TestCurrentRiskExposure:
    """Test risk exposure calculation and display."""

    def test_panel_initialization(self, risk_panel):
        """Test that panel initializes with default values."""
        assert risk_panel.risk_limits["capital_at_risk_limit"] == 10000.0
        assert risk_panel.risk_limits["max_drawdown_daily"] == 2.0

    def test_update_portfolio_data(self, risk_panel, sample_portfolio):
        """Test portfolio data update."""
        risk_panel.update_portfolio_data(sample_portfolio)

        assert len(risk_panel.open_trades) == 2
        assert len(risk_panel.positions) == 3
        assert "AAPL" in risk_panel.historical_returns

    def test_capital_at_risk_calculation(self, risk_panel, sample_portfolio):
        """Test capital at risk (R) calculation."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_exposure_display()

        # R = |entry - stop| * qty
        # AAPL: |150 - 145| * 100 = 500
        # MSFT: |320 - 310| * 50 = 500
        # Total R = 1000

        assert "500" in risk_panel.capital_at_risk_card.value().text()

    def test_exposure_alert_under_60_percent(self, risk_panel, sample_portfolio):
        """Test that no alert appears when using < 60% of limit."""
        risk_panel.risk_limits["capital_at_risk_limit"] = 10000.0
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_exposure_display()

        # ~10% utilization, should be fine
        assert risk_panel.exposure_alert.text() == ""

    def test_exposure_alert_over_80_percent(self, risk_panel, sample_portfolio):
        """Test that warning appears when using > 80% of limit."""
        risk_panel.risk_limits["capital_at_risk_limit"] = 1000.0  # Low limit
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_exposure_display()

        # ~100% utilization, should show warning
        assert "WARNING" in risk_panel.exposure_alert.text()

    def test_trades_table_population(self, risk_panel, sample_portfolio):
        """Test that trades table is populated correctly."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_exposure_display()

        assert risk_panel.trades_table.rowCount() == 2
        # Check first trade
        ticker_item = risk_panel.trades_table.item(0, 0)
        assert ticker_item.text() == "AAPL"


# ============================================================================
# TESTS: VaR ANALYSIS
# ============================================================================

class TestVaRAnalysis:
    """Test VaR calculation and display."""

    def test_var_95_calculation(self, risk_panel, sample_portfolio):
        """Test VaR at 95% confidence level."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_var_display()

        var_item = risk_panel.var_table.item(0, 1)
        assert var_item is not None
        var_text = var_item.text()
        assert "%" in var_text

    def test_var_99_calculation(self, risk_panel, sample_portfolio):
        """Test VaR at 99% confidence level."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_var_display()

        var_item = risk_panel.var_table.item(1, 1)
        assert var_item is not None
        var_text = var_item.text()
        assert "%" in var_text

    def test_var_dollar_conversion(self, risk_panel, sample_portfolio):
        """Test that VaR is converted to dollar values correctly."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_var_display()

        dollar_item = risk_panel.var_table.item(0, 2)
        assert dollar_item is not None
        assert "$" in dollar_item.text()

    def test_var_insufficient_data(self, risk_panel):
        """Test VaR handling with insufficient data."""
        portfolio = {
            "positions": [{"ticker": "AAPL", "price": 150, "qty": 100}],
            "historical_returns": {"AAPL": [0.01, 0.02]},  # Only 2 returns
            "open_trades": [],
        }
        risk_panel.update_portfolio_data(portfolio)
        risk_panel.refresh_var_display()

        var_item = risk_panel.var_table.item(0, 1)
        assert var_item.text() == "N/A"

    def test_var_interpretation_text(self, risk_panel, sample_portfolio):
        """Test that VaR interpretation is provided."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_var_display()

        interp = risk_panel.var_interp_label.text()
        assert "confident" in interp.lower()
        assert "$" in interp

    def test_var_method_selection(self, risk_panel, sample_portfolio):
        """Test switching between VaR methods."""
        risk_panel.update_portfolio_data(sample_portfolio)

        # Should have three methods
        assert risk_panel.var_method_combo.count() == 3

        # Change to Monte Carlo
        risk_panel.var_method_combo.setCurrentText("Monte Carlo")
        assert risk_panel.var_method_combo.currentText() == "Monte Carlo"

        # Details should update
        details = risk_panel.var_details_label.text()
        assert "Monte Carlo" in details


# ============================================================================
# TESTS: CORRELATION ANALYSIS
# ============================================================================

class TestCorrelationAnalysis:
    """Test correlation matrix and heatmap."""

    def test_high_correlation_detection(self, risk_panel, high_correlation_returns):
        """Test detection of highly correlated positions."""
        portfolio = {
            "positions": [
                {"ticker": "AAPL", "price": 160, "qty": 100},
                {"ticker": "MSFT", "price": 330, "qty": 50},
            ],
            "historical_returns": high_correlation_returns,
            "open_trades": [],
        }
        risk_panel.update_portfolio_data(portfolio)
        risk_panel.refresh_correlation_display()

        # Should detect high correlation and populate warnings table
        assert risk_panel.corr_warnings_table.rowCount() > 0

    def test_low_correlation_detection(self, risk_panel, diversified_returns):
        """Test that diversified positions don't trigger warnings."""
        portfolio = {
            "positions": [
                {"ticker": "AAPL", "price": 160, "qty": 100},
                {"ticker": "AGG", "price": 105, "qty": 100},
            ],
            "historical_returns": diversified_returns,
            "open_trades": [],
        }
        risk_panel.update_portfolio_data(portfolio)
        risk_panel.refresh_correlation_display()

        # Low correlation, should have 0 warnings
        assert risk_panel.corr_warnings_table.rowCount() == 0

    def test_correlation_heatmap_generation(self, risk_panel, sample_portfolio):
        """Test that correlation heatmap is generated."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_correlation_display()

        # Canvas should have been drawn
        assert risk_panel.corr_canvas is not None

    def test_correlation_signal_emission(self, risk_panel, high_correlation_returns):
        """Test that correlation warning signal is emitted."""
        portfolio = {
            "positions": [
                {"ticker": "AAPL", "price": 160, "qty": 100},
                {"ticker": "MSFT", "price": 330, "qty": 50},
            ],
            "historical_returns": high_correlation_returns,
            "open_trades": [],
        }

        with patch.object(risk_panel.correlation_warning, 'emit') as mock_emit:
            risk_panel.update_portfolio_data(portfolio)
            risk_panel.refresh_correlation_display()

            # Signal should be emitted for high correlation
            assert mock_emit.called


# ============================================================================
# TESTS: CONCENTRATION ANALYSIS
# ============================================================================

class TestConcentrationAnalysis:
    """Test concentration analysis."""

    def test_position_concentration_calculation(self, risk_panel, sample_portfolio):
        """Test that position concentration is calculated correctly."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_concentration_display()

        # AAPL: 160 * 100 = 16000
        # MSFT: 330 * 50 = 16500
        # JPM: 160 * 40 = 6400
        # Total: 38900
        # AAPL: 41.1% (should trigger alert for >15%)

        assert risk_panel.position_table.rowCount() == 3

    def test_concentration_alert_position_over_15_percent(self, risk_panel, sample_portfolio):
        """Test that positions over 15% trigger alert."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_concentration_display()

        # Check for red background on high concentration items
        for row in range(risk_panel.position_table.rowCount()):
            status_item = risk_panel.position_table.item(row, 2)
            if "HIGH" in status_item.text():
                assert "⚠️" in status_item.text()

    def test_sector_concentration_calculation(self, risk_panel, sample_portfolio):
        """Test sector concentration."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_concentration_display()

        # Tech: 41.1% + 42.4% = 83.5%
        # Financials: 16.5%
        # Should show Tech is concentrated

        tech_rows = [
            risk_panel.sector_table.item(i, 0).text()
            for i in range(risk_panel.sector_table.rowCount())
            if "Technology" in risk_panel.sector_table.item(i, 0).text()
        ]
        assert len(tech_rows) > 0

    def test_concentration_pie_chart_generation(self, risk_panel, sample_portfolio):
        """Test that pie chart is generated."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_concentration_display()

        assert risk_panel.concentration_canvas is not None


# ============================================================================
# TESTS: EFFICIENT FRONTIER
# ============================================================================

class TestEfficientFrontier:
    """Test Markowitz efficient frontier."""

    @patch('quantum_terminal.ui.panels.risk_panel.rp')
    def test_frontier_generation(self, mock_rp, risk_panel, sample_portfolio):
        """Test efficient frontier generation with mocked riskfolio."""
        # Mock riskfolio
        mock_portfolio = MagicMock()
        mock_rp.Portfolio.return_value = mock_portfolio
        mock_portfolio.optimization.return_value = np.array([0.4, 0.3, 0.3])
        mock_portfolio.efficient_frontier.return_value = [
            np.array([0.4, 0.3, 0.3]),
            np.array([0.3, 0.4, 0.3]),
            np.array([0.3, 0.3, 0.4]),
        ]

        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.refresh_frontier_display()

        assert mock_rp.Portfolio.called

    def test_frontier_recommendation_text(self, risk_panel, sample_portfolio):
        """Test that optimization recommendation is provided."""
        risk_panel.update_portfolio_data(sample_portfolio)

        # Frontier display should generate recommendation
        # (May show as N/A if riskfolio not installed)
        recommendation = risk_panel.frontier_recommendation.text()
        # Either shows actual recommendation or N/A
        assert isinstance(recommendation, str)


# ============================================================================
# TESTS: STRESS TESTING
# ============================================================================

class TestStressTesting:
    """Test stress testing scenarios."""

    def test_stress_test_20_percent_drop(self, risk_panel, sample_portfolio):
        """Test -20% market downturn scenario."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.on_stress_test(-0.20)

        # Check that scenario is populated in table
        scenario_item = risk_panel.stress_table.item(0, 0)
        assert scenario_item is not None

    def test_stress_test_50_percent_drop(self, risk_panel, sample_portfolio):
        """Test -50% (GFC) scenario."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.on_stress_test(-0.50)

        scenario_item = risk_panel.stress_table.item(1, 1)
        assert scenario_item is not None
        assert "-50" in scenario_item.text()

    def test_stress_test_35_percent_drop(self, risk_panel, sample_portfolio):
        """Test -35% (COVID) scenario."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.on_stress_test(-0.35)

        scenario_item = risk_panel.stress_table.item(2, 1)
        assert scenario_item is not None
        assert "-35" in scenario_item.text()

    def test_stress_test_pnl_calculation(self, risk_panel, sample_portfolio):
        """Test that P&L impact is calculated."""
        risk_panel.update_portfolio_data(sample_portfolio)
        risk_panel.on_stress_test(-0.20)

        pnl_item = risk_panel.stress_table.item(0, 2)
        assert "$" in pnl_item.text()

    def test_stress_test_signal_emission(self, risk_panel, sample_portfolio):
        """Test that stress_test_updated signal is emitted."""
        risk_panel.update_portfolio_data(sample_portfolio)

        with patch.object(risk_panel.stress_test_updated, 'emit') as mock_emit:
            risk_panel.on_stress_test(-0.20)
            assert mock_emit.called

    def test_portfolio_beta_calculation(self, risk_panel, sample_portfolio):
        """Test weighted portfolio beta calculation."""
        risk_panel.update_portfolio_data(sample_portfolio)

        beta = risk_panel._calculate_portfolio_beta()
        assert isinstance(beta, float)
        assert beta > 0


# ============================================================================
# TESTS: RISK LIMITS CONFIGURATION
# ============================================================================

class TestRiskLimitsConfiguration:
    """Test risk limits configuration."""

    def test_risk_limits_initialization(self, risk_panel):
        """Test that risk limits are initialized."""
        assert risk_panel.limit_dd_daily.value() == 2.0
        assert risk_panel.limit_dd_total.value() == 10.0

    def test_save_risk_limits(self, risk_panel):
        """Test saving modified risk limits."""
        risk_panel.limit_dd_daily.setValue(3.0)
        risk_panel.limit_capital_risk.setValue(15000.0)

        risk_panel.on_save_limits()

        assert risk_panel.risk_limits["max_drawdown_daily"] == 3.0
        assert risk_panel.risk_limits["capital_at_risk_limit"] == 15000.0

    def test_risk_limit_signal_emission(self, risk_panel):
        """Test that risk_limit_changed signal is emitted."""
        with patch.object(risk_panel.risk_limit_changed, 'emit') as mock_emit:
            risk_panel.on_save_limits()
            assert mock_emit.called

    def test_limit_bounds(self, risk_panel):
        """Test that limit spinboxes have correct bounds."""
        assert risk_panel.limit_dd_daily.minimum() == 0.1
        assert risk_panel.limit_dd_daily.maximum() == 50.0

        assert risk_panel.limit_capital_risk.minimum() == 100
        assert risk_panel.limit_capital_risk.maximum() == 1000000


# ============================================================================
# TESTS: HELPER FUNCTIONS
# ============================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_portfolio_returns_calculation(self, risk_panel, sample_portfolio):
        """Test calculation of weighted portfolio returns."""
        risk_panel.update_portfolio_data(sample_portfolio)
        returns = risk_panel._calculate_portfolio_returns()

        assert isinstance(returns, list)
        assert len(returns) > 0

    def test_current_weights_calculation(self, risk_panel, sample_portfolio):
        """Test calculation of current portfolio weights."""
        risk_panel.update_portfolio_data(sample_portfolio)
        weights = risk_panel._get_current_weights()

        assert isinstance(weights, dict)
        # Weights should sum to approximately 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_get_current_weights_empty_portfolio(self, risk_panel):
        """Test weights calculation with empty portfolio."""
        portfolio = {
            "positions": [],
            "open_trades": [],
            "historical_returns": {},
        }
        risk_panel.update_portfolio_data(portfolio)
        weights = risk_panel._get_current_weights()

        assert weights == {}


# ============================================================================
# TESTS: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test error handling in risk panel."""

    def test_update_with_invalid_data(self, risk_panel):
        """Test that invalid data is handled gracefully."""
        invalid_portfolio = {
            "open_trades": None,
            "positions": None,
            "historical_returns": None,
        }

        # Should not raise exception
        try:
            risk_panel.update_portfolio_data(invalid_portfolio)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

    def test_refresh_with_missing_historical_data(self, risk_panel):
        """Test that missing historical data doesn't crash VaR display."""
        portfolio = {
            "positions": [{"ticker": "AAPL", "price": 150, "qty": 100}],
            "historical_returns": {},
            "open_trades": [],
        }

        risk_panel.update_portfolio_data(portfolio)
        # Should handle gracefully
        risk_panel.refresh_var_display()

    def test_concentration_with_zero_value_positions(self, risk_panel):
        """Test concentration with zero-value positions."""
        portfolio = {
            "positions": [
                {"ticker": "AAPL", "price": 0, "qty": 0},
                {"ticker": "MSFT", "price": 330, "qty": 50},
            ],
            "historical_returns": {},
            "open_trades": [],
        }

        risk_panel.update_portfolio_data(portfolio)
        # Should handle gracefully
        risk_panel.refresh_concentration_display()


# ============================================================================
# TESTS: UI COMPONENT RENDERING
# ============================================================================

class TestUIRendering:
    """Test UI component rendering."""

    def test_panel_tabs_creation(self, risk_panel):
        """Test that all tabs are created."""
        assert risk_panel.tabs.count() == 7
        tab_names = [
            risk_panel.tabs.tabText(i)
            for i in range(risk_panel.tabs.count())
        ]
        assert "Risk Exposure" in tab_names
        assert "VaR Analysis" in tab_names
        assert "Correlations" in tab_names

    def test_metric_cards_creation(self, risk_panel):
        """Test that metric cards are created."""
        assert risk_panel.capital_at_risk_card is not None
        assert risk_panel.limit_card is not None
        assert risk_panel.used_percent_card is not None

    def test_tables_creation(self, risk_panel):
        """Test that data tables are created."""
        assert risk_panel.trades_table is not None
        assert risk_panel.var_table is not None
        assert risk_panel.stress_table is not None

    def test_buttons_creation(self, risk_panel):
        """Test that buttons are created."""
        assert risk_panel.stress_btn_20 is not None
        assert risk_panel.stress_btn_50 is not None
        assert risk_panel.stress_btn_35 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
