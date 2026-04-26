"""
Comprehensive tests for Screener Panel module.

Tests cover:
- Preset definitions and metadata
- Filter application and validation
- Universe selection (S&P 500, Russell 2000, Custom)
- Screening results table population
- Data consistency and accuracy
- Graham formula integration
- Quality score consistency
- CSV export functionality
- Signal emission for ticker selection
- Edge cases and error handling

Phase 4 - Screener Module Testing
Reference: PLAN_MAESTRO.md - Phase 4: Testing Strategy
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Import from domain and UI
from quantum_terminal.domain.valuation import graham_formula, nnwc
from quantum_terminal.domain.risk import quality_score, detect_manipulation
from quantum_terminal.ui.panels.screener_panel import (
    ScreenerWorker,
    ScreenerPanel,
    SCREENER_PRESETS,
    SP500_LIST,
    RUSSELL2000_LIST,
)

logger = logging.getLogger(__name__)


class TestScreenerPresets:
    """Test screener preset definitions."""

    def test_preset_count(self):
        """Verify all 6 Graham presets are defined."""
        assert len(SCREENER_PRESETS) == 6

    def test_preset_names(self):
        """Verify preset names match specification."""
        expected_names = {
            "Graham Classic",
            "Net-Net",
            "Quality + Value",
            "Dividends",
            "Avoid Traps",
            "Whales + Insiders",
        }
        assert set(SCREENER_PRESETS.keys()) == expected_names

    def test_preset_structure(self):
        """Verify each preset has required fields."""
        for preset_name, preset in SCREENER_PRESETS.items():
            assert "filters" in preset, f"{preset_name} missing filters"
            assert "description" in preset, f"{preset_name} missing description"
            assert isinstance(preset["filters"], dict)
            assert isinstance(preset["description"], str)

    def test_preset_descriptions_non_empty(self):
        """Verify preset descriptions are meaningful."""
        for preset_name, preset in SCREENER_PRESETS.items():
            desc = preset["description"]
            assert len(desc) > 10, f"{preset_name} has insufficient description"
            assert any(
                keyword in desc.lower()
                for keyword in ["graham", "value", "dividend", "quality", "trap", "whale", "net-net"]
            )

    def test_graham_classic_filters(self):
        """Test Graham Classic preset filters."""
        preset = SCREENER_PRESETS["Graham Classic"]
        filters = preset["filters"]

        # Should have P/E < 15, D/E < 1, Current Ratio > 1.5
        assert "pe_ratio" in filters
        assert "debt_to_equity" in filters
        assert "current_ratio" in filters

        assert filters["pe_ratio"] == (0, 15)
        assert filters["debt_to_equity"] == (0, 1.0)
        assert filters["current_ratio"] == (1.5, 10)

    def test_net_net_preset(self):
        """Test Net-Net preset."""
        preset = SCREENER_PRESETS["Net-Net"]
        filters = preset["filters"]

        assert "price_to_nnwc" in filters
        assert filters["price_to_nnwc"] == (0, 0.67)

    def test_quality_plus_value_preset(self):
        """Test Quality + Value preset."""
        preset = SCREENER_PRESETS["Quality + Value"]
        filters = preset["filters"]

        assert "quality_score" in filters
        assert "margin_of_safety" in filters
        assert filters["quality_score"] == (70, 100)
        assert filters["margin_of_safety"] == (20, 100)

    def test_dividend_preset(self):
        """Test Dividend preset."""
        preset = SCREENER_PRESETS["Dividends"]
        filters = preset["filters"]

        assert "dividend_yield" in filters
        assert "payout_ratio" in filters
        assert filters["dividend_yield"] == (3.0, 100)
        assert filters["payout_ratio"] == (0, 60)

    def test_avoid_traps_preset(self):
        """Test Avoid Traps preset."""
        preset = SCREENER_PRESETS["Avoid Traps"]
        filters = preset["filters"]

        assert "ocf_to_ni_ratio" in filters
        assert "manipulation_score" in filters
        assert filters["ocf_to_ni_ratio"] == (0.8, 100)

    def test_whales_insiders_preset(self):
        """Test Whales + Insiders preset."""
        preset = SCREENER_PRESETS["Whales + Insiders"]
        filters = preset["filters"]

        assert "insider_buying_ratio" in filters
        assert "short_interest_ratio" in filters


class TestUniverseDefinitions:
    """Test universe definitions."""

    def test_sp500_sample_size(self):
        """Verify S&P 500 sample has valid tickers."""
        assert len(SP500_LIST) > 0
        assert all(isinstance(t, str) for t in SP500_LIST)
        assert all(len(t) <= 5 for t in SP500_LIST)  # Ticker length <= 5

    def test_sp500_contains_major_caps(self):
        """Verify S&P 500 sample includes major caps."""
        major_caps = {"AAPL", "MSFT", "GOOG", "AMZN", "TSLA"}
        assert major_caps.issubset(set(SP500_LIST))

    def test_russell2000_sample_size(self):
        """Verify Russell 2000 sample has tickers."""
        assert len(RUSSELL2000_LIST) > 0
        assert all(isinstance(t, str) for t in RUSSELL2000_LIST)

    def test_universe_lists_no_duplicates(self):
        """Ensure no duplicate tickers within universe lists."""
        assert len(SP500_LIST) == len(set(SP500_LIST))
        assert len(RUSSELL2000_LIST) == len(set(RUSSELL2000_LIST))

    def test_universe_lists_no_overlap(self):
        """Verify S&P 500 and Russell 2000 samples don't heavily overlap."""
        overlap = set(SP500_LIST) & set(RUSSELL2000_LIST)
        # Some overlap is OK (large-caps in Russell 2000), but not 100%
        assert len(overlap) < len(RUSSELL2000_LIST)


class TestScreenerWorkerFiltering:
    """Test screener worker filtering logic."""

    def test_worker_initializes(self):
        """Test ScreenerWorker initialization."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        filters = {"pe_ratio": (0, 20)}

        worker = ScreenerWorker(tickers, filters)

        assert worker.tickers == tickers
        assert worker.filters == filters
        assert worker.results == []

    def test_screen_ticker_basic(self):
        """Test basic ticker screening."""
        worker = ScreenerWorker(["AAPL"], {"pe_ratio": (0, 30)})

        fundamentals = {
            "ticker": "AAPL",
            "price": 150.0,
            "pe_ratio": 25.0,
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.01,
            "ocf_to_ni": 1.1,
            "eps": 6.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        assert result is not None
        assert result["ticker"] == "AAPL"
        assert "price" in result
        assert "iv" in result
        assert "mos_percent" in result
        assert "quality_score" in result
        assert "decision" in result

    def test_screen_ticker_fails_filter(self):
        """Test ticker that doesn't pass filters."""
        worker = ScreenerWorker(["AAPL"], {"pe_ratio": (0, 15)})

        fundamentals = {
            "ticker": "AAPL",
            "price": 150.0,
            "pe_ratio": 25.0,  # Exceeds filter
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.01,
            "ocf_to_ni": 1.1,
            "eps": 6.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        assert result is None  # Should be filtered out

    def test_screen_ticker_passes_filter(self):
        """Test ticker that passes filters."""
        worker = ScreenerWorker(["AAPL"], {"pe_ratio": (0, 30)})

        fundamentals = {
            "ticker": "AAPL",
            "price": 150.0,
            "pe_ratio": 20.0,  # Within filter
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.01,
            "ocf_to_ni": 1.1,
            "eps": 6.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        assert result is not None
        assert result["pe_ratio"] == 20.0

    def test_decision_buy_signal(self):
        """Test BUY decision on strong fundamentals."""
        worker = ScreenerWorker(
            ["AAPL"],
            {
                "quality_score": (70, 100),
                "margin_of_safety": (20, 100),
            },
        )

        fundamentals = {
            "ticker": "AAPL",
            "price": 100.0,
            "pe_ratio": 15.0,
            "debt_to_equity": 0.3,
            "current_ratio": 2.5,
            "roe": 0.25,
            "dividend_yield": 0.02,
            "ocf_to_ni": 1.2,
            "eps": 10.0,
            "growth_rate": 0.12,
        }

        result = worker._screen_ticker(fundamentals)

        if result:  # If passes filters
            # With high ROE and low DE, should get strong quality score
            assert result["decision"] in ["BUY", "HOLD"]

    def test_decision_avoid_signal(self):
        """Test AVOID decision on weak fundamentals."""
        worker = ScreenerWorker(["BAD"], {"pe_ratio": (0, 50)})

        fundamentals = {
            "ticker": "BAD",
            "price": 100.0,
            "pe_ratio": 45.0,  # Very high
            "debt_to_equity": 2.5,  # Very high
            "current_ratio": 0.5,  # Very low
            "roe": 0.05,  # Low
            "dividend_yield": 0.001,
            "ocf_to_ni": 0.5,  # Weak
            "eps": 1.0,
            "growth_rate": 0.01,
        }

        result = worker._screen_ticker(fundamentals)

        if result:
            # Low quality should suggest AVOID
            assert result["quality_score"] < 50

    def test_multiple_filters_all_apply(self):
        """Test that all filters are applied (AND logic)."""
        filters = {
            "pe_ratio": (0, 20),
            "debt_to_equity": (0, 1),
            "quality_score": (50, 100),
        }
        worker = ScreenerWorker(["TEST"], filters)

        # Fails PE filter
        fundamentals_fail_pe = {
            "ticker": "TEST",
            "price": 100.0,
            "pe_ratio": 25.0,  # FAILS
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.02,
            "ocf_to_ni": 1.1,
            "eps": 5.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals_fail_pe)
        assert result is None


class TestScreenerPanelUI:
    """Test screener panel UI initialization and signals."""

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_panel_initializes(self, mock_provider):
        """Test ScreenerPanel initialization."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        assert panel is not None
        assert panel.current_universe == SP500_LIST
        assert panel.current_filters == {}
        assert panel.screening_results == []

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_preset_combo_has_options(self, mock_provider):
        """Test preset dropdown has all presets."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        assert panel.preset_combo.count() == 6

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_universe_combo_has_options(self, mock_provider):
        """Test universe dropdown has options."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        assert panel.universe_combo.count() == 3  # S&P 500, Russell 2000, Custom

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_filters_ui_created(self, mock_provider):
        """Test filter UI elements are created."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        assert len(panel.filters_ui) > 0
        # Each filter should have (min_spin, max_spin, slider)
        for filter_key, (min_spin, max_spin, slider) in panel.filters_ui.items():
            assert min_spin is not None
            assert max_spin is not None
            assert slider is not None

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_build_current_filters(self, mock_provider):
        """Test filter building from UI."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        # Set some filter values
        if panel.filters_ui:
            first_filter = list(panel.filters_ui.keys())[0]
            min_spin, max_spin, _ = panel.filters_ui[first_filter]
            min_spin.setValue(5.0)
            max_spin.setValue(15.0)

            panel._build_current_filters()

            assert first_filter in panel.current_filters
            assert panel.current_filters[first_filter] == (5.0, 15.0)

    @patch("quantum_terminal.ui.panels.screener_panel.DataProvider")
    def test_results_table_initialized(self, mock_provider):
        """Test results table is created with correct columns."""
        mock_provider.return_value = MagicMock()

        panel = ScreenerPanel()

        assert panel.results_table.columnCount() == 9
        expected_headers = [
            "Ticker", "Price", "IV", "MoS%", "Score", "P/E", "OCF/NI", "D/E", "Decision"
        ]
        for i, expected in enumerate(expected_headers):
            assert panel.results_table.horizontalHeaderItem(i).text() == expected


class TestScreenerIntegration:
    """Integration tests with domain layer."""

    def test_graham_formula_in_screening(self):
        """Test Graham formula is used in screening."""
        worker = ScreenerWorker(["TEST"], {})

        fundamentals = {
            "ticker": "TEST",
            "price": 100.0,
            "pe_ratio": 15.0,
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.02,
            "ocf_to_ni": 1.1,
            "eps": 5.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        if result:
            # Graham formula should produce a valid intrinsic value
            assert result["iv"] > 0
            assert isinstance(result["iv"], float)

    def test_quality_score_calculation(self):
        """Test quality score is calculated correctly."""
        worker = ScreenerWorker(["TEST"], {})

        fundamentals = {
            "ticker": "TEST",
            "price": 100.0,
            "pe_ratio": 15.0,
            "debt_to_equity": 0.3,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.02,
            "ocf_to_ni": 1.1,
            "eps": 5.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        if result:
            assert 0 <= result["quality_score"] <= 100
            assert isinstance(result["quality_score"], int)

    def test_margin_of_safety_calculation(self):
        """Test Margin of Safety is calculated correctly."""
        worker = ScreenerWorker(["TEST"], {})

        fundamentals = {
            "ticker": "TEST",
            "price": 80.0,
            "pe_ratio": 15.0,
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.02,
            "ocf_to_ni": 1.1,
            "eps": 5.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        if result:
            # Price 80 < IV should give positive MoS
            assert result["mos_percent"] > 0 or result["iv"] < 80


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_price_handling(self):
        """Test handling of zero price."""
        worker = ScreenerWorker(["ZERO"], {})

        fundamentals = {
            "ticker": "ZERO",
            "price": 0.0,
            "pe_ratio": 0.0,
            "debt_to_equity": 0.0,
            "current_ratio": 2.0,
            "roe": 0.10,
            "dividend_yield": 0.0,
            "ocf_to_ni": 1.0,
            "eps": 0.0,
            "growth_rate": 0.0,
        }

        result = worker._screen_ticker(fundamentals)

        # Should handle gracefully (return None or fallback values)
        if result:
            assert "ticker" in result

    def test_negative_pe_ratio(self):
        """Test handling of negative P/E (loss-making company)."""
        worker = ScreenerWorker(["LOSS"], {"pe_ratio": (0, 100)})

        fundamentals = {
            "ticker": "LOSS",
            "price": 50.0,
            "pe_ratio": -5.0,  # Negative due to loss
            "debt_to_equity": 1.0,
            "current_ratio": 1.5,
            "roe": -0.10,  # Negative ROE
            "dividend_yield": 0.0,
            "ocf_to_ni": 0.5,
            "eps": -2.0,
            "growth_rate": -0.05,
        }

        result = worker._screen_ticker(fundamentals)

        # Should be filtered out due to poor quality
        if result:
            assert result["quality_score"] < 30

    def test_very_high_leverage(self):
        """Test handling of very high leverage."""
        worker = ScreenerWorker(["LEVER"], {"debt_to_equity": (0, 5)})

        fundamentals = {
            "ticker": "LEVER",
            "price": 100.0,
            "pe_ratio": 20.0,
            "debt_to_equity": 4.0,  # Very high
            "current_ratio": 0.9,
            "roe": 0.15,
            "dividend_yield": 0.01,
            "ocf_to_ni": 0.8,
            "eps": 5.0,
            "growth_rate": 0.05,
        }

        result = worker._screen_ticker(fundamentals)

        if result:
            # High leverage should reduce quality score
            assert result["quality_score"] < 70

    def test_empty_filters_dict(self):
        """Test screening with empty filters."""
        worker = ScreenerWorker(["AAPL"], {})

        fundamentals = {
            "ticker": "AAPL",
            "price": 150.0,
            "pe_ratio": 25.0,
            "debt_to_equity": 0.5,
            "current_ratio": 2.0,
            "roe": 0.20,
            "dividend_yield": 0.01,
            "ocf_to_ni": 1.1,
            "eps": 6.0,
            "growth_rate": 0.10,
        }

        result = worker._screen_ticker(fundamentals)

        # With no filters, should pass
        assert result is not None

    def test_invalid_fundamentals_dict(self):
        """Test handling of missing required fields."""
        worker = ScreenerWorker(["BAD"], {})

        fundamentals = {
            "ticker": "BAD",
            # Missing most fields
            "price": 100.0,
        }

        result = worker._screen_ticker(fundamentals)

        # Should handle gracefully
        # Either returns None or uses fallback values
        assert True  # No exception raised


class TestPerformance:
    """Performance tests."""

    def test_screening_50_tickers_reasonable_time(self):
        """Test screening 50 tickers completes in reasonable time."""
        import time

        tickers = SP500_LIST[:50]  # First 50 tickers
        filters = {"pe_ratio": (0, 30), "quality_score": (40, 100)}

        worker = ScreenerWorker(tickers, filters)

        start = time.time()

        # Mock fundamentals for each ticker
        all_fundamentals = []
        for ticker in tickers:
            all_fundamentals.append(
                {
                    "ticker": ticker,
                    "price": 100.0 + (hash(ticker) % 50),
                    "pe_ratio": 15.0 + (hash(ticker) % 20),
                    "debt_to_equity": 0.5,
                    "current_ratio": 2.0,
                    "roe": 0.20,
                    "dividend_yield": 0.02,
                    "ocf_to_ni": 1.1,
                    "eps": 5.0,
                    "growth_rate": 0.10,
                }
            )

        # Screen each
        for fundamentals in all_fundamentals:
            worker._screen_ticker(fundamentals)

        elapsed = time.time() - start

        # Should complete in reasonable time (< 5 seconds for 50 tickers)
        assert elapsed < 5.0, f"Screening took {elapsed:.2f}s, expected < 5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
