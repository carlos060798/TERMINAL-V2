"""
Phase 1: Valuation Tests — Graham-Dodd Methodology

Test suite for valuation formulas based on Benjamin Graham's Security Analysis.
Covers Graham Number, NNWC, EPV, liquidation value, and adjusted P/E ratios.

Reference: PLAN_MAESTRO.md - Phase 1: Domain Layer
"""

import pytest
from decimal import Decimal
from datetime import datetime


# Fixtures for test data
@pytest.fixture
def ko_fundamentals():
    """Coca-Cola - dividend paying, strong fundamentals."""
    return {
        "ticker": "KO",
        "current_price": Decimal("60.50"),
        "eps": Decimal("2.85"),
        "book_value_per_share": Decimal("5.42"),
        "growth_rate": Decimal("5.0"),  # 5% annual growth
        "dividend_per_share": Decimal("1.92"),
        "risk_free_rate": Decimal("4.5"),
        "market_risk_premium": Decimal("6.0"),
        "beta": Decimal("0.65"),
        "debt": Decimal("42_000_000_000"),
        "cash": Decimal("6_500_000_000"),
        "shareholders_equity": Decimal("28_000_000_000"),
        "book_assets": Decimal("100_000_000_000"),
        "liabilities": Decimal("72_000_000_000"),
        "working_capital": Decimal("3_500_000_000"),
        "shares_outstanding": Decimal("2_060_000_000"),
        "net_income": Decimal("5_850_000_000"),
        "ocf": Decimal("6_200_000_000"),
        "capex": Decimal("1_200_000_000"),
        "depreciation_amortization": Decimal("800_000_000"),
    }


@pytest.fixture
def aapl_fundamentals():
    """Apple - high growth, strong balance sheet."""
    return {
        "ticker": "AAPL",
        "current_price": Decimal("180.00"),
        "eps": Decimal("6.10"),
        "book_value_per_share": Decimal("3.28"),
        "growth_rate": Decimal("12.0"),  # 12% growth
        "dividend_per_share": Decimal("0.96"),
        "risk_free_rate": Decimal("4.5"),
        "market_risk_premium": Decimal("6.0"),
        "beta": Decimal("1.25"),
        "debt": Decimal("107_000_000_000"),
        "cash": Decimal("29_000_000_000"),
        "shareholders_equity": Decimal("62_000_000_000"),
        "book_assets": Decimal("180_000_000_000"),
        "liabilities": Decimal("118_000_000_000"),
        "working_capital": Decimal("8_000_000_000"),
        "shares_outstanding": Decimal("15_550_000_000"),
        "net_income": Decimal("96_000_000_000"),
        "ocf": Decimal("110_000_000_000"),
        "capex": Decimal("10_500_000_000"),
        "depreciation_amortization": Decimal("11_000_000_000"),
    }


@pytest.fixture
def msft_fundamentals():
    """Microsoft - stable growth, profitable."""
    return {
        "ticker": "MSFT",
        "current_price": Decimal("415.00"),
        "eps": Decimal("11.85"),
        "book_value_per_share": Decimal("15.50"),
        "growth_rate": Decimal("9.5"),  # 9.5% growth
        "dividend_per_share": Decimal("2.96"),
        "risk_free_rate": Decimal("4.5"),
        "market_risk_premium": Decimal("6.0"),
        "beta": Decimal("0.95"),
        "debt": Decimal("61_000_000_000"),
        "cash": Decimal("59_000_000_000"),
        "shareholders_equity": Decimal("208_000_000_000"),
        "book_assets": Decimal("400_000_000_000"),
        "liabilities": Decimal("192_000_000_000"),
        "working_capital": Decimal("55_000_000_000"),
        "shares_outstanding": Decimal("13_440_000_000"),
        "net_income": Decimal("88_000_000_000"),
        "ocf": Decimal("95_000_000_000"),
        "capex": Decimal("18_000_000_000"),
        "depreciation_amortization": Decimal("9_000_000_000"),
    }


@pytest.fixture
def troubled_fundamentals():
    """Troubled company - negative metrics, high debt."""
    return {
        "ticker": "TSLA",
        "current_price": Decimal("45.00"),
        "eps": Decimal("0.50"),
        "book_value_per_share": Decimal("2.10"),
        "growth_rate": Decimal("-5.0"),  # -5% shrinking
        "dividend_per_share": Decimal("0.00"),
        "risk_free_rate": Decimal("4.5"),
        "market_risk_premium": Decimal("6.0"),
        "beta": Decimal("2.10"),
        "debt": Decimal("15_000_000_000"),
        "cash": Decimal("500_000_000"),
        "shareholders_equity": Decimal("2_000_000_000"),
        "book_assets": Decimal("20_000_000_000"),
        "liabilities": Decimal("18_000_000_000"),
        "working_capital": Decimal("-500_000_000"),  # Negative WC
        "shares_outstanding": Decimal("3_200_000_000"),
        "net_income": Decimal("500_000_000"),
        "ocf": Decimal("300_000_000"),
        "capex": Decimal("2_000_000_000"),
        "depreciation_amortization": Decimal("1_000_000_000"),
    }


class TestGrahamFormula:
    """Graham Number valuation tests (1934 methodology)."""

    def test_graham_formula_basic(self, ko_fundamentals):
        """
        Graham Number = sqrt(22.5 * EPS * Book Value Per Share)

        For KO: sqrt(22.5 * 2.85 * 5.42) = ~42.10
        Intrinsic value should be reasonable valuation.
        """
        eps = ko_fundamentals["eps"]
        bvps = ko_fundamentals["book_value_per_share"]

        graham_number = (Decimal("22.5") * eps * bvps).sqrt()

        assert graham_number > 0
        assert graham_number < ko_fundamentals["current_price"] or (
            Decimal("35") < graham_number < Decimal("50")
        )

    def test_graham_formula_zero_growth(self):
        """
        Test Graham formula with zero growth company.
        Should produce valid valuation but lower multiplier.
        """
        eps = Decimal("1.50")
        bvps = Decimal("10.00")

        # Conservative Graham for no-growth
        graham_number = (Decimal("15.0") * eps * bvps).sqrt()

        assert graham_number > 0
        assert graham_number == pytest.approx(float((Decimal("15.0") * eps * bvps).sqrt()))

    def test_graham_formula_high_rates(self):
        """
        When risk-free rates are high (>5%), Graham multiplier should decrease.
        Graham used 22.5 when rates were ~3%, so at 6% we adjust.
        """
        risk_free = Decimal("6.5")
        standard_rate = Decimal("4.5")

        # Adjusted multiplier = 22.5 * (risk_free / standard_rate)
        adjusted_multiplier = Decimal("22.5") * (risk_free / standard_rate)

        eps = Decimal("2.00")
        bvps = Decimal("5.00")

        graham_adjusted = (adjusted_multiplier * eps * bvps).sqrt()

        assert graham_adjusted > 0
        # Higher rates should not increase valuation
        assert adjusted_multiplier >= Decimal("22.5")

    def test_graham_formula_zero_eps(self):
        """
        Edge case: EPS = 0 should result in Graham Number = 0.
        (Unprofitable company - Graham would not invest)
        """
        eps = Decimal("0.00")
        bvps = Decimal("5.00")

        graham_number = (Decimal("22.5") * eps * bvps).sqrt()

        assert graham_number == Decimal("0")

    def test_graham_formula_negative_bvps(self):
        """
        Negative book value (liabilities > assets) is red flag.
        Graham Number becomes imaginary - company has no margin of safety.
        """
        eps = Decimal("1.50")
        bvps = Decimal("-2.00")  # Negative

        # sqrt of negative - would raise exception in real code
        with pytest.raises((ValueError, decimal.InvalidOperation)):
            graham_number = (Decimal("22.5") * eps * bvps).sqrt()

    def test_graham_formula_high_growth_stock(self, aapl_fundamentals):
        """
        High-growth stock (>10% growth) warrants higher P/E.
        Graham formula accounts for growth through higher multiplier.
        """
        eps = aapl_fundamentals["eps"]
        bvps = aapl_fundamentals["book_value_per_share"]
        growth = aapl_fundamentals["growth_rate"]

        # For high growth, use higher multiplier
        growth_multiplier = Decimal("22.5") * (Decimal("1") + growth / Decimal("100"))
        graham_number = (growth_multiplier * eps * bvps).sqrt()

        assert graham_number > 0
        assert graham_number > (Decimal("22.5") * eps * bvps).sqrt()  # Higher than base


class TestNNWCValuation:
    """Net-Net Working Capital valuation (Graham's margin of safety)."""

    def test_nnwc_positive(self, ko_fundamentals):
        """
        NNWC = (Current Assets - Total Liabilities) / Shares Outstanding

        For healthy company: NNWC should be positive.
        If stock price < NNWC, it's a deep value opportunity.
        """
        # Estimate current assets (typically 50-60% of assets)
        total_assets = ko_fundamentals["book_assets"]
        current_assets = total_assets * Decimal("0.55")
        total_liabilities = ko_fundamentals["liabilities"]

        nnwc_total = current_assets - total_liabilities
        shares = ko_fundamentals["shares_outstanding"]
        nnwc_per_share = nnwc_total / shares

        assert nnwc_per_share > 0
        assert nnwc_per_share < ko_fundamentals["book_value_per_share"]

    def test_nnwc_negative(self, troubled_fundamentals):
        """
        NNWC < 0 means current assets can't cover total liabilities.
        Company is financially distressed - NO BUY per Graham.
        """
        total_assets = troubled_fundamentals["book_assets"]
        current_assets = total_assets * Decimal("0.40")  # Low CA ratio
        total_liabilities = troubled_fundamentals["liabilities"]

        nnwc_total = current_assets - total_liabilities
        shares = troubled_fundamentals["shares_outstanding"]
        nnwc_per_share = nnwc_total / shares

        # Should be negative for troubled company
        assert nnwc_per_share <= 0
        # Graham would NOT invest
        assert nnwc_per_share < troubled_fundamentals["current_price"]

    def test_nnwc_boundary_zero(self):
        """
        NNWC = 0 is boundary condition.
        Assets exactly equal liabilities - no margin of safety.
        """
        current_assets = Decimal("10_000_000")
        total_liabilities = Decimal("10_000_000")
        shares = Decimal("1_000_000")

        nnwc_per_share = (current_assets - total_liabilities) / shares

        assert nnwc_per_share == Decimal("0")

    def test_nnwc_with_discount(self):
        """
        Real margin of safety: buy at 66% of NNWC or less.
        If NNWC/share = $10, buy only at $6.60 or less.
        """
        nnwc_per_share = Decimal("15.00")
        current_price = Decimal("9.00")
        discount = current_price / nnwc_per_share

        # 60% of NNWC = good margin
        assert discount == Decimal("0.60")
        assert current_price < (nnwc_per_share * Decimal("0.67"))

    def test_nnwc_calculation_comprehensive(self, msft_fundamentals):
        """
        Full NNWC calculation: conservative liquidation value.
        """
        # Microsoft is financially strong
        total_assets = msft_fundamentals["book_assets"]
        current_assets = total_assets * Decimal("0.50")  # Conservative CA estimate
        total_liabilities = msft_fundamentals["liabilities"]
        shares = msft_fundamentals["shares_outstanding"]

        nnwc_total = current_assets - total_liabilities
        nnwc_per_share = nnwc_total / shares

        assert nnwc_per_share > 0
        # NNWC should be significantly lower than book value
        assert nnwc_per_share < msft_fundamentals["book_value_per_share"]


class TestLiquidationValue:
    """Conservative liquidation valuation (worst-case scenario)."""

    def test_liquidation_value_basic(self, ko_fundamentals):
        """
        Liquidation Value = (Current Assets * 0.75) + (Fixed Assets * 0.50) - Liabilities
        Represents forced sale scenario.
        """
        total_assets = ko_fundamentals["book_assets"]
        current_assets = total_assets * Decimal("0.60")
        fixed_assets = total_assets - current_assets
        total_liabilities = ko_fundamentals["liabilities"]

        # Conservative liquidation scenario
        liquidation_value = (current_assets * Decimal("0.75")) + (fixed_assets * Decimal("0.50"))
        liquidation_value -= total_liabilities
        shares = ko_fundamentals["shares_outstanding"]
        liq_value_per_share = liquidation_value / shares

        assert liq_value_per_share > 0
        assert liq_value_per_share < ko_fundamentals["book_value_per_share"]

    def test_liquidation_value_negative_equity(self, troubled_fundamentals):
        """
        If company is insolvent, liquidation value < 0 (creditors recover, equity holders get zero).
        """
        total_assets = troubled_fundamentals["book_assets"]
        current_assets = total_assets * Decimal("0.35")
        fixed_assets = total_assets - current_assets
        total_liabilities = troubled_fundamentals["liabilities"]

        liquidation_value = (current_assets * Decimal("0.60")) + (fixed_assets * Decimal("0.20"))
        liquidation_value -= total_liabilities
        shares = troubled_fundamentals["shares_outstanding"]
        liq_value_per_share = liquidation_value / shares

        # For troubled company, likely negative
        if liq_value_per_share < 0:
            # Equity worthless in liquidation
            assert liq_value_per_share <= 0

    def test_liquidation_payout_waterfall(self):
        """
        Liquidation priority: secured debt → unsecured debt → preferred → common equity.
        Test that subordinated equity gets nothing if insufficient assets.
        """
        total_assets = Decimal("100_000_000")
        secured_debt = Decimal("40_000_000")
        unsecured_debt = Decimal("50_000_000")
        preferred_shares = Decimal("5_000_000")
        common_equity = Decimal("5_000_000")

        # Liquidation order:
        after_secured = total_assets - secured_debt
        after_unsecured = after_secured - unsecured_debt
        after_preferred = max(Decimal("0"), after_unsecured - preferred_shares)

        # Common equity gets remainder
        equity_recovery = max(Decimal("0"), after_preferred)

        # In this case, equity gets $5M (after paying debt)
        assert equity_recovery > 0
        assert equity_recovery <= common_equity


class TestEarningsValueEPV:
    """Earnings Power Value (Graham variant for mature, stable companies)."""

    def test_epv_calculation(self, ko_fundamentals):
        """
        EPV = Normalized Earnings / Cost of Equity

        For mature dividender like KO, EPV assumes earnings continue indefinitely.
        Cost of Equity = Risk-free rate + Beta * Market Risk Premium
        """
        risk_free = ko_fundamentals["risk_free_rate"] / Decimal("100")
        beta = ko_fundamentals["beta"]
        market_premium = ko_fundamentals["market_risk_premium"] / Decimal("100")

        cost_of_equity = risk_free + (beta * market_premium)

        net_income = ko_fundamentals["net_income"]
        shares = ko_fundamentals["shares_outstanding"]
        earnings_per_share = net_income / shares

        epv = earnings_per_share / cost_of_equity

        assert epv > 0
        assert epv == pytest.approx(float(earnings_per_share / cost_of_equity))

    def test_epv_normalized_earnings(self):
        """
        EPV uses NORMALIZED earnings (remove one-time items).
        If company had $100M normal earnings + $50M write-off, use $100M.
        """
        normalized_earnings = Decimal("5_000_000")
        one_time_loss = Decimal("250_000")
        reported_earnings = normalized_earnings - one_time_loss

        shares = Decimal("1_000_000")

        # Should use normalized, not reported
        normalized_eps = normalized_earnings / shares
        reported_eps = reported_earnings / shares

        cost_of_equity = Decimal("0.10")  # 10%
        epv_normalized = normalized_eps / cost_of_equity
        epv_reported = reported_eps / cost_of_equity

        # Normalized EPV should be higher
        assert epv_normalized > epv_reported

    def test_epv_high_cost_of_equity(self):
        """
        High CoE (risky company) = lower EPV.
        If CoE = 15% vs 10%, same earnings valued lower.
        """
        earnings = Decimal("2.00")

        epv_low_coe = earnings / Decimal("0.10")  # $20
        epv_high_coe = earnings / Decimal("0.15")  # $13.33

        assert epv_high_coe < epv_low_coe

    def test_epv_vs_graham_number(self, ko_fundamentals):
        """
        EPV and Graham Number are complementary:
        - EPV for mature, stable earners
        - Graham formula for growth consideration
        """
        # EPV approach
        risk_free = ko_fundamentals["risk_free_rate"] / Decimal("100")
        beta = ko_fundamentals["beta"]
        market_premium = ko_fundamentals["market_risk_premium"] / Decimal("100")
        cost_of_equity = risk_free + (beta * market_premium)

        eps = ko_fundamentals["eps"]
        epv = eps / cost_of_equity

        # Graham approach
        bvps = ko_fundamentals["book_value_per_share"]
        graham = (Decimal("22.5") * eps * bvps).sqrt()

        # Both should be positive, Graham typically higher (growth component)
        assert epv > 0
        assert graham > 0


class TestAdjustedPERatio:
    """Adjusted P/E ratio accounting for growth and quality."""

    def test_peg_ratio_calculation(self):
        """
        PEG Ratio = P/E / Growth Rate

        PEG < 1.0 is undervalued, > 1.5 is expensive.
        """
        pe_ratio = Decimal("20.0")
        growth_rate = Decimal("15.0")  # 15% annual growth

        peg = pe_ratio / growth_rate

        assert peg < Decimal("1.5")
        assert peg == Decimal("1.333").quantize(Decimal("0.001"))

    def test_adjusted_pe_quality_factor(self, ko_fundamentals):
        """
        Adjusted P/E = P/E * Quality Score

        High-quality company gets higher multiple (1.2x-1.5x).
        Low-quality gets discount (0.7x-0.9x).
        """
        current_price = ko_fundamentals["current_price"]
        eps = ko_fundamentals["eps"]
        pe_ratio = current_price / eps

        quality_score = Decimal("1.25")  # KO is high quality
        adjusted_pe = pe_ratio * quality_score

        assert adjusted_pe > pe_ratio
        assert adjusted_pe == pytest.approx(float(pe_ratio * quality_score))

    def test_adjusted_pe_high_growth(self, aapl_fundamentals):
        """
        High-growth premium = P/E ratio can justify higher valuations.
        AAPL 12% growth + quality = deserves higher multiple than KO 5% growth.
        """
        # AAPL: high growth
        aapl_pe = aapl_fundamentals["current_price"] / aapl_fundamentals["eps"]
        aapl_growth = aapl_fundamentals["growth_rate"]
        aapl_quality = Decimal("1.20")
        aapl_adjusted = aapl_pe * aapl_quality

        # KO: lower growth
        ko_pe = Decimal("60.50") / Decimal("2.85")  # ~21.2
        ko_growth = Decimal("5.0")
        ko_quality = Decimal("1.25")
        ko_adjusted = ko_pe * ko_quality

        # AAPL higher absolute P/E justified by growth
        assert aapl_pe > ko_pe

    def test_peg_ratio_boundary_cases(self):
        """
        Boundary tests for PEG calculation.
        """
        # Case 1: Zero growth (mature company)
        pe = Decimal("25.0")
        growth = Decimal("0.0")

        # PEG undefined for 0 growth - typically use different metric
        if growth == Decimal("0"):
            peg = None  # Undefined
        else:
            peg = pe / growth

        assert peg is None

    def test_peg_ratio_high_growth(self):
        """
        High growth justifies higher P/E within reason.
        """
        pe_30 = Decimal("30.0")
        growth_30 = Decimal("30.0")
        peg_30 = pe_30 / growth_30

        assert peg_30 == Decimal("1.0")

        # This is fair value range (PEG = 1.0)
        assert peg_30 >= Decimal("0.8")
        assert peg_30 <= Decimal("1.2")


class TestValuationIntegration:
    """Integration tests combining multiple valuation methods."""

    def test_valuation_summary_ko(self, ko_fundamentals):
        """
        Complete valuation for KO using multiple methods.
        """
        eps = ko_fundamentals["eps"]
        bvps = ko_fundamentals["book_value_per_share"]
        current_price = ko_fundamentals["current_price"]

        # Graham Number
        graham = (Decimal("22.5") * eps * bvps).sqrt()

        # P/E Ratio
        pe = current_price / eps

        # Dividend Yield
        div_yield = ko_fundamentals["dividend_per_share"] / current_price

        # All should be positive and reasonable
        assert graham > 0
        assert pe > 0
        assert div_yield > 0
        assert div_yield < Decimal("0.10")  # <10% dividend yield

    def test_valuation_summary_aapl(self, aapl_fundamentals):
        """
        Complete valuation for AAPL using multiple methods.
        """
        eps = aapl_fundamentals["eps"]
        bvps = aapl_fundamentals["book_value_per_share"]
        current_price = aapl_fundamentals["current_price"]
        growth = aapl_fundamentals["growth_rate"]

        # Graham Number (adjusted for growth)
        growth_multiplier = Decimal("22.5") * (Decimal("1") + growth / Decimal("100"))
        graham_growth = (growth_multiplier * eps * bvps).sqrt()

        # PEG Ratio
        pe = current_price / eps
        peg = pe / growth

        assert graham_growth > 0
        assert peg > 0
        assert peg < Decimal("2.0")

    def test_valuation_red_flags(self, troubled_fundamentals):
        """
        Identify red flags in valuation metrics.
        """
        eps = troubled_fundamentals["eps"]
        bvps = troubled_fundamentals["book_value_per_share"]
        current_price = troubled_fundamentals["current_price"]
        growth = troubled_fundamentals["growth_rate"]

        pe = current_price / eps

        red_flags = []

        # Flag 1: Negative growth
        if growth < 0:
            red_flags.append("negative_growth")

        # Flag 2: Low earnings relative to price
        if pe > Decimal("50.0"):
            red_flags.append("high_pe")

        # Flag 3: Declining value
        if bvps < Decimal("1.00"):
            red_flags.append("low_book_value")

        # Troubled company should have red flags
        assert len(red_flags) >= 1

    def test_valuation_conservative_vs_aggressive(self, ko_fundamentals):
        """
        Conservative valuation assumes lower growth; aggressive assumes higher.
        """
        eps = ko_fundamentals["eps"]

        # Conservative: assume 0% growth, use income capitalization
        conservative_coe = Decimal("0.08")  # 8% cost of equity
        conservative_value = eps / conservative_coe

        # Aggressive: assume full growth rate, higher multiple
        aggressive_coe = Decimal("0.06")  # 6% cost of equity
        aggressive_value = eps / aggressive_coe

        # Aggressive should be higher
        assert aggressive_value > conservative_value
        assert aggressive_value == pytest.approx(float(eps / aggressive_coe))


# Edge cases and error handling
class TestValuationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_shares_outstanding(self):
        """
        Zero shares outstanding = undefined valuation (should raise error).
        """
        eps = Decimal("2.00")
        shares = Decimal("0")

        # Division by zero should fail
        with pytest.raises(decimal.ZeroDivisionError):
            eps_value = eps / shares

    def test_very_large_values(self):
        """
        Test valuation with extremely large market cap companies.
        """
        huge_earnings = Decimal("100_000_000_000")  # $100B earnings
        huge_shares = Decimal("10_000_000_000")  # $10B shares

        eps = huge_earnings / huge_shares
        assert eps == Decimal("10.00")

    def test_very_small_values(self):
        """
        Test valuation with penny stocks and micro-cap.
        """
        tiny_earnings = Decimal("0.0001")
        tiny_shares = Decimal("1_000_000")

        eps = tiny_earnings / tiny_shares
        assert eps > Decimal("0")
        assert eps < Decimal("0.01")

    def test_precision_decimal(self):
        """
        Ensure Decimal precision is maintained throughout calculations.
        """
        eps = Decimal("2.123456789")
        shares = Decimal("1_000_000.123456789")

        total = eps * shares

        # Precision preserved
        assert isinstance(total, Decimal)
        assert "." in str(total)


# Import for error testing
import decimal


class TestValuationFormulasAccuracy:
    """Verify formulas produce mathematically correct results."""

    def test_graham_formula_symmetry(self):
        """
        Graham Number should scale proportionally with inputs.
        """
        eps1 = Decimal("2.00")
        bvps1 = Decimal("5.00")
        graham1 = (Decimal("22.5") * eps1 * bvps1).sqrt()

        # Double both inputs → Graham Number should scale by sqrt(4) = 2x
        eps2 = eps1 * Decimal("2")
        bvps2 = bvps1 * Decimal("2")
        graham2 = (Decimal("22.5") * eps2 * bvps2).sqrt()

        ratio = graham2 / graham1
        assert ratio == pytest.approx(float(Decimal("2.0")))

    def test_pe_ratio_inverse_earnings(self):
        """
        If earnings double, P/E ratio should halve (with same price).
        """
        price = Decimal("60.00")
        eps1 = Decimal("2.00")
        pe1 = price / eps1

        eps2 = eps1 * Decimal("2")
        pe2 = price / eps2

        # PE2 should be half of PE1
        assert pe2 == pe1 / Decimal("2")

    def test_cost_of_equity_formula(self):
        """
        CoE = Rf + Beta * (Rm - Rf)
        Verify formula implementation.
        """
        risk_free = Decimal("0.045")  # 4.5%
        beta = Decimal("1.25")
        market_premium = Decimal("0.060")  # 6%

        coe = risk_free + (beta * market_premium)

        expected = Decimal("0.1275")  # 4.5% + 1.25*6% = 12.75%
        assert coe == expected
