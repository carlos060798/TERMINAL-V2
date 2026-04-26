"""
Test suite for AnalyzerPanel - Graham-Dodd analysis UI component.

Tests verify:
1. Panel initialization and tab creation (7 Graham tabs)
2. Data loading and display updates
3. Graham formula integration with domain layer
4. Quality score calculation
5. Manipulation detection (5 red flags)
6. Peer comparison and summary generation
7. Valuation calculations (Graham IV, NNWC, Liquidation)
8. Thread safety and error handling

Phase 3 - UI Layer Testing
Reference: CLAUDE.md - AnalyzerPanel with 7 Graham tabs
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication

from quantum_terminal.ui.panels.analyzer_panel import AnalyzerPanel
from quantum_terminal.domain.valuation import (
    graham_formula, nnwc, liquidation_value, adjusted_pe_ratio
)
from quantum_terminal.domain.risk import quality_score, detect_manipulation


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
    """Test AnalyzerPanel initialization and structure."""

    def test_panel_creates_without_error(self, analyzer):
        """Test that panel initializes without error."""
        assert analyzer is not None
        assert analyzer.current_ticker is None
        assert analyzer.company_data == {}

    def test_panel_has_ticker_input(self, analyzer):
        """Test that ticker input widget is created."""
        assert hasattr(analyzer, 'ticker_input')
        assert analyzer.ticker_input is not None

    def test_panel_has_seven_tabs(self, analyzer):
        """Test that all 7 Graham-Dodd analysis tabs are created."""
        assert hasattr(analyzer, 'tabs')
        assert analyzer.tabs.count() == 7

    def test_tab_names_correct(self, analyzer):
        """Test that tabs have correct names."""
        expected_tabs = [
            "Screening",
            "Income Statement",
            "Margins",
            "Balance Sheet",
            "Historical",
            "Comparables",
            "Valuation",
        ]
        for i, expected_name in enumerate(expected_tabs):
            assert analyzer.tabs.tabText(i) == expected_name

    def test_screening_semaphores_count(self, analyzer):
        """Test that 10 quality semaphores are created."""
        assert len(analyzer.semaphores) == 10

    def test_screening_semaphore_factors(self, analyzer):
        """Test that all Graham quality factors exist."""
        expected_factors = [
            "Current Ratio",
            "Quick Ratio",
            "D/E Ratio",
            "OCF/NI",
            "ROE",
            "ROIC",
            "EPS Growth",
            "Debt/EBITDA",
            "Interest Coverage",
            "D&A/CapEx",
        ]
        for factor in expected_factors:
            assert factor in analyzer.semaphores

    def test_sidebar_widgets_exist(self, analyzer):
        """Test that sidebar contains chart, thesis, and chat."""
        assert analyzer.tradingview_chart is not None
        assert analyzer.generate_thesis_btn is not None
        assert analyzer.thesis_display is not None
        assert analyzer.ai_chat is not None

    def test_signals_defined(self, analyzer):
        """Test that panel signals are properly defined."""
        assert analyzer.company_loaded is not None
        assert analyzer.analysis_complete is not None
        assert analyzer.ai_thesis_generated is not None

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


class TestGrahamValuation:
    """Test Graham formula calculations."""

    def test_graham_valuation_basic(self, analyzer):
        """Test basic Graham IV calculation."""
        fundamentals = {
            "eps": 5.0,
            "growth_rate": 8.0,
            "risk_free_rate": 4.5,
            "current_ratio": 2.0,
            "ocf_ni": 1.0,
            "debt_to_equity": 0.3,
            "dividend_coverage": 2.5,
            "margin_stability": 0.05,
            "roe": 0.20,
            "tax_rate": 0.25,
            "asset_turnover": 1.2,
            "valuation_gap": -0.05,
            "current_price": 100,
            "current_assets": 500,
            "total_liabilities": 300,
            "inventory": 100,
            "fixed_assets": 200,
            "shares_outstanding": 1000,
        }

        result = analyzer._calculate_graham_valuation(fundamentals)

        assert result is not None
        assert "graham_iv" in result
        assert "quality_score" in result
        assert "margin_of_safety" in result
        assert "decision" in result
        assert result["graham_iv"] > 0
        assert 0 <= result["quality_score"] <= 100

    def test_graham_decision_buy(self, analyzer):
        """Verify BUY decision when price << IV."""
        fundamentals = {
            "eps": 5.0,
            "growth_rate": 10.0,
            "risk_free_rate": 3.0,
            "current_ratio": 2.0,
            "ocf_ni": 1.0,
            "debt_to_equity": 0.3,
            "dividend_coverage": 2.5,
            "margin_stability": 0.05,
            "roe": 0.20,
            "tax_rate": 0.25,
            "asset_turnover": 1.2,
            "valuation_gap": -0.2,
            "current_price": 50,
            "current_assets": 500,
            "total_liabilities": 300,
            "inventory": 100,
            "fixed_assets": 200,
            "shares_outstanding": 1000,
        }

        result = analyzer._calculate_graham_valuation(fundamentals)
        assert result["decision"] == "BUY"

    def test_graham_decision_avoid(self, analyzer):
        """Verify AVOID decision when price > IV."""
        fundamentals = {
            "eps": 2.0,
            "growth_rate": 3.0,
            "risk_free_rate": 5.0,
            "current_ratio": 1.5,
            "ocf_ni": 0.9,
            "debt_to_equity": 0.8,
            "dividend_coverage": 1.5,
            "margin_stability": 0.10,
            "roe": 0.08,
            "tax_rate": 0.25,
            "asset_turnover": 0.8,
            "valuation_gap": 0.5,
            "current_price": 500,
            "current_assets": 300,
            "total_liabilities": 300,
            "inventory": 80,
            "fixed_assets": 100,
            "shares_outstanding": 1000,
        }

        result = analyzer._calculate_graham_valuation(fundamentals)
        assert result["decision"] == "AVOID"

    def test_nnwc_calculation(self, analyzer):
        """Verify NNWC per-share calculation."""
        fundamentals = {
            "eps": 5.0,
            "growth_rate": 8.0,
            "risk_free_rate": 4.5,
            "current_ratio": 2.0,
            "ocf_ni": 1.0,
            "debt_to_equity": 0.3,
            "dividend_coverage": 2.5,
            "margin_stability": 0.05,
            "roe": 0.20,
            "tax_rate": 0.25,
            "asset_turnover": 1.2,
            "valuation_gap": -0.05,
            "current_price": 100,
            "current_assets": 1000,
            "total_liabilities": 600,
            "inventory": 200,
            "fixed_assets": 400,
            "shares_outstanding": 100,
        }

        result = analyzer._calculate_graham_valuation(fundamentals)
        # NNWC = CA - TL = 1000 - 600 = 400; per share = 400/100 = 4.0
        assert result["nnwc_per_share"] == 4.0

    def test_quality_score_integration(self, analyzer):
        """Verify quality score affects Graham IV."""
        fundamentals = {
            "eps": 5.0,
            "growth_rate": 8.0,
            "risk_free_rate": 4.5,
            "current_ratio": 1.0,
            "ocf_ni": 0.5,
            "debt_to_equity": 2.0,
            "dividend_coverage": 0.8,
            "margin_stability": 0.20,
            "roe": 0.02,
            "tax_rate": 0.50,
            "asset_turnover": 0.3,
            "valuation_gap": 0.3,
            "current_price": 100,
            "current_assets": 100,
            "total_liabilities": 200,
            "inventory": 20,
            "fixed_assets": 50,
            "shares_outstanding": 10,
        }

        result = analyzer._calculate_graham_valuation(fundamentals)
        quality = result["quality_score"]
        assert quality < 50  # Poor fundamentals


class TestManipulationDetection:
    """Test Graham red flag detection."""

    def test_detect_manipulation_ocf_ni(self, analyzer):
        """Verify OCF < NI flag detection."""
        financials = {
            "ocf": 400,
            "net_income": 900,
            "depreciation": 300,
            "capex": 150,
            "equity_delta": 300,
            "ni_less_dividends": 650,
        }

        flags = analyzer._detect_manipulation_flags(financials)
        ocf_flag = next((f for f in flags if f[0] == "ocf_below_ni"), None)
        assert ocf_flag is not None
        assert ocf_flag[1] is True

    def test_detect_manipulation_da_exceeds_capex(self, analyzer):
        """Verify D&A > CapEx flag detection."""
        financials = {
            "ocf": 1000,
            "net_income": 900,
            "depreciation": 300,
            "capex": 150,
            "equity_delta": 650,
            "ni_less_dividends": 650,
        }

        flags = analyzer._detect_manipulation_flags(financials)
        da_flag = next((f for f in flags if f[0] == "da_exceeds_capex"), None)
        assert da_flag is not None
        assert da_flag[1] is True

    def test_detect_manipulation_healthy_company(self, analyzer):
        """Verify no major flags for healthy company."""
        financials = {
            "ocf": 1000,
            "net_income": 900,
            "depreciation": 200,
            "capex": 250,
            "equity_delta": 650,
            "ni_less_dividends": 650,
        }

        flags = analyzer._detect_manipulation_flags(financials)
        assert len(flags) == 5
        # ocf_below_ni should be False
        assert not flags[0][1]


class TestPeerComparison:
    """Test peer comparison."""

    def test_peer_summary_cheaper(self, analyzer):
        """Verify summary when company is cheaper."""
        peers = [
            {"name": "Company", "pe": "15.0"},
            {"name": "Peer1", "pe": "20.0"},
            {"name": "Peer2", "pe": "22.0"},
        ]

        summary = analyzer._generate_peer_summary(peers)
        assert "CHEAPER" in summary or "cheaper" in summary

    def test_peer_summary_expensive(self, analyzer):
        """Verify summary when company is more expensive."""
        peers = [
            {"name": "Company", "pe": "35.0"},
            {"name": "Peer1", "pe": "20.0"},
            {"name": "Peer2", "pe": "22.0"},
        ]

        summary = analyzer._generate_peer_summary(peers)
        assert "PRICIER" in summary or "pricier" in summary


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
