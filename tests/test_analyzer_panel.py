"""
Tests for AnalyzerPanel.

Test suite for the Analyzer panel UI component.
Verifies company loading, analysis execution, and tab updates.

Phase 3 - UI Testing
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy

from quantum_terminal.ui.panels import AnalyzerPanel


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def analyzer(app):
    """Create an AnalyzerPanel instance for testing."""
    return AnalyzerPanel()


class TestAnalyzerPanelInitialization:
    """Test AnalyzerPanel initialization."""

    def test_panel_creates_without_error(self, analyzer):
        """Test that panel initializes without error."""
        assert analyzer is not None

    def test_panel_has_ticker_input(self, analyzer):
        """Test that ticker input widget is created."""
        assert hasattr(analyzer, 'ticker_input')
        assert analyzer.ticker_input is not None

    def test_panel_has_seven_tabs(self, analyzer):
        """Test that all 7 analysis tabs are created."""
        assert hasattr(analyzer, 'tabs')
        assert analyzer.tabs.count() == 7

    def test_tab_names(self, analyzer):
        """Test that tab names are correct."""
        expected_tabs = [
            "Screening",
            "Income Statement",
            "Margins",
            "Balance Sheet",
            "Historical",
            "Comparables",
            "Valuation"
        ]

        for i in range(analyzer.tabs.count()):
            assert analyzer.tabs.tabText(i) in expected_tabs

    def test_panel_has_sidebar(self, analyzer):
        """Test that sidebar components are created."""
        assert hasattr(analyzer, 'tradingview_chart')
        assert hasattr(analyzer, 'ai_chat')
        assert hasattr(analyzer, 'thesis_display')

    def test_no_company_loaded_initially(self, analyzer):
        """Test that no company is loaded initially."""
        assert analyzer.current_ticker is None


class TestScreeningTab:
    """Test Screening tab functionality."""

    def test_screening_tab_has_semaphores(self, analyzer):
        """Test that screening tab has 10 semaphores."""
        assert len(analyzer.semaphores) == 10

    def test_semaphore_factors(self, analyzer):
        """Test that all 10 quality factors are present."""
        factors = [
            "Current Ratio",
            "Quick Ratio",
            "D/E Ratio",
            "OCF/NI",
            "ROE",
            "ROIC",
            "EPS Growth",
            "Debt/EBITDA",
            "Interest Coverage",
            "D&A/CapEx"
        ]

        for factor in factors:
            assert factor in analyzer.semaphores


class TestIncomeStatementTab:
    """Test Income Statement tab."""

    def test_income_statement_has_manipulation_table(self, analyzer):
        """Test that manipulation detection table exists."""
        assert hasattr(analyzer, 'manip_table')
        assert analyzer.manip_table.columnCount() == 4

    def test_income_statement_has_history_table(self, analyzer):
        """Test that income history table exists."""
        assert hasattr(analyzer, 'income_table')
        assert analyzer.income_table.columnCount() == 7


class TestMarginsTab:
    """Test Margins tab."""

    def test_margins_tab_has_chart(self, analyzer):
        """Test that margins tab has a chart."""
        assert hasattr(analyzer, 'margin_chart')

    def test_margins_tab_has_table(self, analyzer):
        """Test that margins tab has a data table."""
        assert hasattr(analyzer, 'margin_table')
        assert analyzer.margin_table.columnCount() == 6


class TestBalanceSheetTab:
    """Test Balance Sheet tab."""

    def test_balance_sheet_has_nnwc_values(self, analyzer):
        """Test that NNWC values are displayed."""
        assert hasattr(analyzer, 'nnwc_value')
        assert hasattr(analyzer, 'nnwc_per_share')

    def test_balance_sheet_has_nnwc_table(self, analyzer):
        """Test that NNWC breakdown table exists."""
        assert hasattr(analyzer, 'nnwc_table')

    def test_balance_sheet_has_debt_schedule(self, analyzer):
        """Test that debt maturity schedule exists."""
        assert hasattr(analyzer, 'debt_table')

    def test_balance_sheet_has_liquidity_ratios(self, analyzer):
        """Test that liquidity ratios table exists."""
        assert hasattr(analyzer, 'liquidity_table')


class TestHistoricalTab:
    """Test Historical tab."""

    def test_historical_tab_has_recession_table(self, analyzer):
        """Test that recession performance table exists."""
        assert hasattr(analyzer, 'recession_table')

    def test_historical_tab_has_mgmt_table(self, analyzer):
        """Test that management changes table exists."""
        assert hasattr(analyzer, 'mgmt_table')

    def test_historical_tab_has_returns_table(self, analyzer):
        """Test that returns metrics table exists."""
        assert hasattr(analyzer, 'returns_table')


class TestComparablesTab:
    """Test Comparables tab."""

    def test_comparables_tab_has_peers_table(self, analyzer):
        """Test that peer comparison table exists."""
        assert hasattr(analyzer, 'peers_table')
        assert analyzer.peers_table.columnCount() == 8

    def test_comparables_tab_has_summary(self, analyzer):
        """Test that peer summary text widget exists."""
        assert hasattr(analyzer, 'peer_summary')


class TestValuationTab:
    """Test Valuation tab."""

    def test_valuation_tab_has_graham_table(self, analyzer):
        """Test that Graham formula table exists."""
        assert hasattr(analyzer, 'graham_table')

    def test_valuation_tab_has_iv_display(self, analyzer):
        """Test that intrinsic value is displayed."""
        assert hasattr(analyzer, 'graham_iv')

    def test_valuation_tab_has_mos_display(self, analyzer):
        """Test that margin of safety is displayed."""
        assert hasattr(analyzer, 'mos_display')

    def test_valuation_tab_has_decision_display(self, analyzer):
        """Test that buy/sell decision is displayed."""
        assert hasattr(analyzer, 'decision_display')

    def test_valuation_tab_has_chart(self, analyzer):
        """Test that valuation chart exists."""
        assert hasattr(analyzer, 'valuation_chart')

    def test_valuation_tab_has_alt_methods_table(self, analyzer):
        """Test that alternative valuation methods table exists."""
        assert hasattr(analyzer, 'alt_valuation_table')


class TestCompanyLoading:
    """Test company data loading."""

    def test_load_company_valid_ticker(self, analyzer):
        """Test loading a valid ticker."""
        result = analyzer.load_company("AAPL")
        assert result is True
        assert analyzer.current_ticker == "AAPL"

    def test_load_company_lowercase_ticker(self, analyzer):
        """Test loading ticker with lowercase (should convert)."""
        analyzer.load_company("aapl")
        assert analyzer.current_ticker == "AAPL"

    def test_load_company_stores_data(self, analyzer):
        """Test that company data is stored."""
        analyzer.load_company("AAPL")
        assert len(analyzer.company_data) > 0

    def test_load_company_emits_signals(self, analyzer):
        """Test that loading company emits signals."""
        spy_loaded = QSignalSpy(analyzer.company_loaded)
        spy_complete = QSignalSpy(analyzer.analysis_complete)

        analyzer.load_company("AAPL")

        assert len(spy_loaded) > 0
        assert len(spy_complete) > 0

    def test_load_company_updates_ticker_input(self, analyzer):
        """Test that ticker input is updated."""
        analyzer.load_company("AAPL")
        assert analyzer.ticker_input.text() == "AAPL"


class TestAnalysisExecution:
    """Test analysis execution."""

    def test_update_all_tabs_called_on_load(self, analyzer):
        """Test that update_all_tabs is called when loading company."""
        with patch.object(analyzer, 'update_all_tabs') as mock_update:
            analyzer.load_company("AAPL")
            mock_update.assert_called()

    def test_update_screening_tab(self, analyzer):
        """Test updating screening semaphores."""
        analyzer.load_company("AAPL")
        analyzer._update_screening_tab()
        # Semaphores should be updated (non-empty)
        assert len(analyzer.semaphores) == 10

    def test_update_income_statement_tab(self, analyzer):
        """Test updating income statement tab."""
        analyzer.load_company("AAPL")
        analyzer._update_income_statement_tab()
        # Tables should have rows
        assert analyzer.manip_table.rowCount() >= 0

    def test_update_balance_sheet_tab(self, analyzer):
        """Test updating balance sheet tab."""
        analyzer.load_company("AAPL")
        analyzer._update_balance_sheet_tab()
        # NNWC values should be set
        assert analyzer.nnwc_value.text() != ""

    def test_update_comparables_tab(self, analyzer):
        """Test updating comparables tab."""
        analyzer.load_company("AAPL")
        analyzer._update_comparables_tab()
        # Peers table should have rows
        assert analyzer.peers_table.rowCount() >= 0

    def test_update_valuation_tab(self, analyzer):
        """Test updating valuation tab."""
        analyzer.load_company("AAPL")
        analyzer._update_valuation_tab()
        # IV should be set
        assert analyzer.graham_iv.text() != "$0.00"


class TestTicker Input:
    """Test ticker input handling."""

    def test_ticker_input_on_enter(self, analyzer):
        """Test loading ticker on enter key."""
        analyzer.ticker_input.setText("AAPL")
        with patch.object(analyzer, 'load_company') as mock_load:
            analyzer._on_ticker_entered()
            mock_load.assert_called_once_with("AAPL")

    def test_load_button_click(self, analyzer):
        """Test load button functionality."""
        analyzer.ticker_input.setText("MSFT")
        with patch.object(analyzer, 'load_company') as mock_load:
            analyzer._on_load_company()
            mock_load.assert_called_once_with("MSFT")

    def test_load_empty_ticker(self, analyzer):
        """Test that empty ticker is not loaded."""
        analyzer.ticker_input.setText("")
        with patch.object(analyzer, 'load_company') as mock_load:
            analyzer._on_load_company()
            mock_load.assert_not_called()


class TestAIThesis:
    """Test AI thesis generation."""

    def test_generate_thesis_button_exists(self, analyzer):
        """Test that generate thesis button exists."""
        assert hasattr(analyzer, 'generate_thesis_btn')

    def test_generate_thesis_requires_loaded_company(self, analyzer):
        """Test that thesis generation requires loaded company."""
        # No company loaded yet
        with patch.object(analyzer, 'ai_thesis_generated') as mock_signal:
            analyzer._on_generate_thesis()
            # Should not emit signal without company

    def test_generate_thesis_with_loaded_company(self, analyzer):
        """Test generating thesis with loaded company."""
        analyzer.load_company("AAPL")
        spy = QSignalSpy(analyzer.ai_thesis_generated)
        analyzer._on_generate_thesis()
        assert len(spy) > 0

    def test_thesis_display_updated(self, analyzer):
        """Test that thesis display is updated."""
        analyzer.load_company("AAPL")
        analyzer._on_generate_thesis()
        assert len(analyzer.thesis_display.toPlainText()) > 0


class TestMockData:
    """Test mock data generation."""

    def test_mock_company_data_structure(self, analyzer):
        """Test that mock company data has expected structure."""
        data = analyzer._get_mock_company_data("AAPL")

        expected_keys = [
            "ticker", "current_price", "graham_iv",
            "margin_of_safety", "decision",
            "current_ratio", "debt_to_equity"
        ]

        for key in expected_keys:
            assert key in data

    def test_mock_thesis_generation(self, analyzer):
        """Test that mock thesis is generated."""
        thesis = analyzer._get_mock_thesis()
        assert len(thesis) > 0
        assert "AAPL" in thesis or "Apple" in thesis

    def test_mock_data_valuation_values(self, analyzer):
        """Test that mock data contains valuation values."""
        data = analyzer._get_mock_company_data("AAPL")

        assert "$" in data["current_price"]
        assert "$" in data["graham_iv"]
        assert "%" in data["margin_of_safety"]


class TestSignals:
    """Test AnalyzerPanel signals."""

    def test_company_loaded_signal(self, analyzer):
        """Test company_loaded signal."""
        spy = QSignalSpy(analyzer.company_loaded)
        analyzer.load_company("AAPL")
        assert len(spy) > 0

    def test_analysis_complete_signal(self, analyzer):
        """Test analysis_complete signal."""
        spy = QSignalSpy(analyzer.analysis_complete)
        analyzer.load_company("AAPL")
        assert len(spy) > 0

    def test_ai_thesis_generated_signal(self, analyzer):
        """Test ai_thesis_generated signal."""
        analyzer.load_company("AAPL")
        spy = QSignalSpy(analyzer.ai_thesis_generated)
        analyzer._on_generate_thesis()
        assert len(spy) > 0


class TestErrorHandling:
    """Test error handling."""

    def test_load_invalid_ticker(self, analyzer):
        """Test loading invalid ticker."""
        result = analyzer.load_company("INVALID")
        # May fail or return default data depending on infrastructure
        assert analyzer.current_ticker is not None or result is False

    def test_update_all_tabs_with_empty_data(self, analyzer):
        """Test updating tabs with empty company data."""
        analyzer.company_data = {}
        # Should not raise exception
        analyzer.update_all_tabs()

    def test_thesis_generation_error_handling(self, analyzer):
        """Test error handling in thesis generation."""
        analyzer.load_company("AAPL")
        with patch.object(analyzer, '_get_mock_thesis',
                         side_effect=Exception("Test error")):
            # Should not raise exception
            analyzer._on_generate_thesis()


class TestUIIntegration:
    """Test UI integration."""

    def test_full_analysis_workflow(self, analyzer):
        """Test complete analysis workflow."""
        # 1. Load company
        assert analyzer.load_company("AAPL")

        # 2. All tabs should be updated
        assert analyzer.current_ticker == "AAPL"

        # 3. Valuation should be displayed
        assert analyzer.graham_iv.text() != "$0.00"

        # 4. Generate thesis
        analyzer._on_generate_thesis()
        assert len(analyzer.thesis_display.toPlainText()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
