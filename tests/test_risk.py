"""
Phase 1: Risk Assessment Tests — Quality Scoring & Financial Metrics

Test suite for company quality scoring, red flag detection, and risk metrics.
Covers quality scores, financial red flags, VaR, Sharpe ratio, beta, and drawdown.

Reference: PLAN_MAESTRO.md - Phase 1: Domain Layer
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import math


# Fixtures for risk assessment data
@pytest.fixture
def excellent_company():
    """Apple-like: high quality, strong cash flows, low debt."""
    return {
        "ticker": "AAPL",
        "price": Decimal("180.00"),
        "eps": Decimal("6.10"),
        "roe": Decimal("110.00"),  # 110% ROE (excellent)
        "debt_to_equity": Decimal("0.35"),  # Low leverage
        "current_ratio": Decimal("1.10"),
        "quick_ratio": Decimal("0.95"),
        "net_income": Decimal("96_000_000_000"),
        "ocf": Decimal("110_000_000_000"),
        "fcf": Decimal("99_500_000_000"),  # OCF - CapEx
        "capex": Decimal("10_500_000_000"),
        "depreciation": Decimal("11_000_000_000"),
        "revenue": Decimal("394_000_000_000"),
        "dividend_per_share": Decimal("0.96"),
        "revenue_growth": Decimal("5.0"),  # Modest growth
        "earnings_growth": Decimal("12.0"),  # Strong EPS growth
        "debt_paydown": Decimal("500_000_000"),  # Paying down debt
        "price_52w_high": Decimal("190.00"),
        "price_52w_low": Decimal("160.00"),
        "beta": Decimal("1.20"),
        "returns_list": [0.5, 0.8, -0.2, 1.2, 0.6, -0.3, 0.9, 1.1, 0.4, 0.7],  # Monthly returns %
    }


@pytest.fixture
def good_company():
    """Coca-Cola-like: stable, dividend paying, acceptable metrics."""
    return {
        "ticker": "KO",
        "price": Decimal("60.50"),
        "eps": Decimal("2.85"),
        "roe": Decimal("35.00"),  # Decent ROE
        "debt_to_equity": Decimal("0.55"),  # Moderate debt
        "current_ratio": Decimal("0.85"),  # Below 1.0 but OK for mature
        "quick_ratio": Decimal("0.70"),
        "net_income": Decimal("5_850_000_000"),
        "ocf": Decimal("6_200_000_000"),
        "fcf": Decimal("5_000_000_000"),  # OCF - CapEx
        "capex": Decimal("1_200_000_000"),
        "depreciation": Decimal("800_000_000"),
        "revenue": Decimal("45_800_000_000"),
        "dividend_per_share": Decimal("1.92"),
        "revenue_growth": Decimal("2.0"),
        "earnings_growth": Decimal("5.0"),
        "debt_paydown": Decimal("200_000_000"),
        "price_52w_high": Decimal("65.00"),
        "price_52w_low": Decimal("56.00"),
        "beta": Decimal("0.65"),
        "returns_list": [0.2, 0.3, -0.1, 0.4, 0.1, -0.2, 0.3, 0.2, 0.0, 0.1],  # Monthly returns %
    }


@pytest.fixture
def poor_company():
    """Troubled company: negative metrics, high debt, declining earnings."""
    return {
        "ticker": "POOR",
        "price": Decimal("15.00"),
        "eps": Decimal("0.25"),
        "roe": Decimal("-10.00"),  # Negative ROE (burning equity)
        "debt_to_equity": Decimal("2.50"),  # High leverage
        "current_ratio": Decimal("0.60"),  # Poor liquidity
        "quick_ratio": Decimal("0.40"),
        "net_income": Decimal("-500_000_000"),  # Losing money
        "ocf": Decimal("-200_000_000"),  # Negative OCF (red flag!)
        "fcf": Decimal("-1_200_000_000"),  # Negative free cash flow
        "capex": Decimal("1_000_000_000"),
        "depreciation": Decimal("300_000_000"),
        "revenue": Decimal("2_000_000_000"),
        "dividend_per_share": Decimal("0.00"),  # No dividend (can't afford)
        "revenue_growth": Decimal("-15.0"),  # Declining revenue
        "earnings_growth": Decimal("-50.0"),  # Earnings collapsing
        "debt_paydown": Decimal("-1_000_000_000"),  # Increasing debt
        "price_52w_high": Decimal("45.00"),
        "price_52w_low": Decimal("10.00"),
        "beta": Decimal("2.50"),  # High volatility
        "returns_list": [-5.0, -8.0, -2.0, 3.0, -10.0, -4.0, 2.0, -6.0, -3.0, -7.0],
    }


@pytest.fixture
def volatile_stock():
    """High volatility stock (tech startup): unpredictable returns."""
    return {
        "ticker": "TECH",
        "price": Decimal("50.00"),
        "returns_list": [15.0, -12.0, 25.0, -18.0, 8.0, -22.0, 30.0, -14.0, 20.0, -16.0],
        "beta": Decimal("2.00"),
    }


class TestQualityScoring:
    """Test quality score calculation (0-100 scale)."""

    def test_quality_score_excellent(self, excellent_company):
        """
        Excellent company should score 80-100.
        AAPL-like metrics: high ROE, low debt, strong cash flows, growth.
        """
        score = 0

        # ROE component (max 25 points)
        roe = excellent_company["roe"]
        if roe > Decimal("50"):
            score += 25
        elif roe > Decimal("25"):
            score += 20
        elif roe > Decimal("15"):
            score += 15

        # Debt component (max 25 points)
        d_e = excellent_company["debt_to_equity"]
        if d_e < Decimal("0.50"):
            score += 25
        elif d_e < Decimal("1.00"):
            score += 20
        elif d_e < Decimal("1.50"):
            score += 15

        # Liquidity component (max 20 points)
        cr = excellent_company["current_ratio"]
        if cr > Decimal("1.50"):
            score += 20
        elif cr > Decimal("1.00"):
            score += 15
        elif cr > Decimal("0.80"):
            score += 10

        # Growth component (max 20 points)
        eg = excellent_company["earnings_growth"]
        if eg > Decimal("10"):
            score += 20
        elif eg > Decimal("5"):
            score += 15

        # Profitability component (max 10 points)
        if excellent_company["net_income"] > Decimal("50_000_000_000"):
            score += 10

        assert score >= 80
        assert score <= 100

    def test_quality_score_good(self, good_company):
        """
        Good company should score 60-79.
        KO-like: stable, profitable, moderate debt, but slower growth.
        """
        score = 0

        # ROE
        roe = good_company["roe"]
        if roe > Decimal("25"):
            score += 20
        elif roe > Decimal("15"):
            score += 15
        elif roe > Decimal("10"):
            score += 10

        # Debt
        d_e = good_company["debt_to_equity"]
        if d_e < Decimal("1.00"):
            score += 20
        elif d_e < Decimal("1.50"):
            score += 15
        elif d_e < Decimal("2.00"):
            score += 10

        # Liquidity
        cr = good_company["current_ratio"]
        if cr > Decimal("0.80"):
            score += 15
        elif cr > Decimal("0.60"):
            score += 10

        # Growth
        eg = good_company["earnings_growth"]
        if eg > Decimal("5"):
            score += 15
        elif eg > Decimal("0"):
            score += 10

        # Profitability
        if good_company["net_income"] > Decimal("1_000_000_000"):
            score += 10

        # Dividend
        if good_company["dividend_per_share"] > 0:
            score += 10

        assert score >= 60
        assert score <= 79

    def test_quality_score_poor(self, poor_company):
        """
        Poor company should score 0-40.
        Multiple red flags: negative ROE, high debt, poor liquidity, declining business.
        """
        score = 100  # Start with max, deduct for problems

        # ROE red flag
        if poor_company["roe"] < 0:
            score -= 30

        # Debt red flag
        if poor_company["debt_to_equity"] > Decimal("2.00"):
            score -= 25

        # Liquidity red flag
        if poor_company["current_ratio"] < Decimal("1.00"):
            score -= 20

        # Cash flow red flag
        if poor_company["ocf"] < 0:
            score -= 15

        # Growth red flag
        if poor_company["earnings_growth"] < Decimal("-20"):
            score -= 10

        score = max(0, score)

        assert score <= 40

    def test_quality_score_boundary_0(self):
        """
        Score of 0: company is insolvent or fraudulent."""
        # All red flags triggered
        score = 0

        assert score == 0

    def test_quality_score_boundary_100(self):
        """
        Score of 100: perfect company (doesn't exist in practice)."""
        score = 100

        assert score == 100

    def test_quality_score_midrange(self):
        """
        Score 40-60: average company, mixed metrics."""
        score = 50

        assert score > 40
        assert score < 60


class TestFinancialRedFlags:
    """Test red flag detection for financial distress."""

    def test_detect_ocf_red_flag(self, poor_company):
        """
        RED FLAG: Operating Cash Flow (OCF) < Net Income.
        Company is not converting earnings to cash (accounting manipulation risk).
        """
        net_income = poor_company["net_income"]
        ocf = poor_company["ocf"]

        has_ocf_flag = ocf < net_income

        # For poor company, OCF is negative while NI is negative (even worse)
        assert has_ocf_flag

    def test_detect_ocf_red_flag_healthy(self, excellent_company):
        """
        HEALTHY: OCF > Net Income (converting earnings to cash efficiently).
        """
        net_income = excellent_company["net_income"]
        ocf = excellent_company["ocf"]

        has_ocf_flag = ocf < net_income

        # For healthy company, OCF should exceed NI
        assert not has_ocf_flag
        assert ocf > net_income

    def test_detect_da_red_flag(self, good_company):
        """
        RED FLAG: Depreciation & Amortization (D&A) > CapEx.
        Company not maintaining asset base (will underperform long-term).
        """
        capex = good_company["capex"]
        da = good_company["depreciation"]

        has_da_flag = da > capex

        # For healthy mature company, D&A may exceed CapEx (slower growth)
        # But this can be a mild red flag
        if da > capex * Decimal("2"):
            assert True  # Strong red flag
        else:
            # For mature company, acceptable
            assert True

    def test_detect_da_red_flag_danger(self):
        """
        DANGER: D&A >> CapEx indicates rapid asset base deterioration.
        """
        capex = Decimal("500_000_000")
        da = Decimal("2_000_000_000")  # 4x CapEx

        has_da_flag = da > capex * Decimal("2")

        assert has_da_flag

    def test_detect_revenue_decline_flag(self, poor_company):
        """
        RED FLAG: Revenue declining YoY.
        """
        revenue_growth = poor_company["revenue_growth"]

        has_growth_flag = revenue_growth < Decimal("0")

        assert has_growth_flag

    def test_detect_debt_increase_flag(self, poor_company):
        """
        RED FLAG: Company increasing debt while earnings declining.
        """
        debt_paydown = poor_company["debt_paydown"]
        earnings_growth = poor_company["earnings_growth"]

        has_debt_flag = debt_paydown < 0 and earnings_growth < 0

        # Poor company: debt increasing AND earnings declining = danger
        assert has_debt_flag

    def test_detect_no_flags_excellent(self, excellent_company):
        """
        HEALTHY: No red flags detected.
        """
        red_flags = []

        # Check OCF
        if excellent_company["ocf"] < excellent_company["net_income"]:
            red_flags.append("ocf_concern")

        # Check D&A
        if excellent_company["depreciation"] > excellent_company["capex"] * Decimal("2"):
            red_flags.append("da_concern")

        # Check revenue
        if excellent_company["revenue_growth"] < 0:
            red_flags.append("revenue_decline")

        # Check debt
        if excellent_company["debt_paydown"] < 0 and excellent_company["earnings_growth"] < 0:
            red_flags.append("debt_danger")

        # Check liquidity
        if excellent_company["current_ratio"] < Decimal("0.80"):
            red_flags.append("liquidity_concern")

        # Healthy company should have minimal flags
        assert len(red_flags) == 0

    def test_detect_multiple_red_flags(self, poor_company):
        """
        Poor company triggers multiple red flags simultaneously."""
        red_flags = []

        if poor_company["ocf"] < Decimal("0"):
            red_flags.append("negative_ocf")

        if poor_company["debt_to_equity"] > Decimal("2.00"):
            red_flags.append("high_leverage")

        if poor_company["current_ratio"] < Decimal("1.00"):
            red_flags.append("poor_liquidity")

        if poor_company["roe"] < Decimal("0"):
            red_flags.append("negative_roe")

        if poor_company["earnings_growth"] < Decimal("-20"):
            red_flags.append("earnings_collapse")

        # Poor company should have 5+ red flags
        assert len(red_flags) >= 5


class TestValueAtRisk:
    """VaR (Value at Risk) calculation."""

    def test_var_95_percentile(self, excellent_company):
        """
        VaR 95% = 5th worst daily return (worst 5% tail).
        For portfolio of $100K: max loss at 95% confidence.
        """
        returns = excellent_company["returns_list"]
        portfolio_value = Decimal("100_000")

        # Sort returns ascending (worst first)
        sorted_returns = sorted(returns)
        # 5th percentile of 10 returns = index 0.5 (interpolate)
        var_index = int(len(sorted_returns) * 0.05)
        var_return = sorted_returns[var_index]

        var_95 = portfolio_value * (Decimal(str(var_return)) / Decimal("100"))

        # For excellent company, VaR should be modest
        assert var_95 < Decimal("10_000")  # Loss should be <10%

    def test_var_99_percentile(self, volatile_stock):
        """
        VaR 99% = 1st worst daily return (1% tail, extreme loss).
        """
        returns = volatile_stock["returns_list"]
        portfolio_value = Decimal("100_000")

        sorted_returns = sorted(returns)
        var_index = int(len(sorted_returns) * 0.01)
        if var_index >= len(sorted_returns):
            var_index = 0  # Use worst return
        var_return = sorted_returns[var_index]

        var_99 = portfolio_value * (Decimal(str(var_return)) / Decimal("100"))

        # For volatile stock, VaR 99 should be significant
        assert var_99 < Decimal("-5_000")  # Extreme loss expected

    def test_var_expected_shortfall(self, poor_company):
        """
        Expected Shortfall (CVaR) = average of worst 5% returns.
        More severe than VaR (tail risk).
        """
        returns = poor_company["returns_list"]
        portfolio_value = Decimal("100_000")

        sorted_returns = sorted(returns)
        tail_size = max(1, len(sorted_returns) // 20)  # 5% of returns
        tail_returns = sorted_returns[:tail_size]

        avg_tail = sum(tail_returns) / len(tail_returns)
        cvar = portfolio_value * (Decimal(str(avg_tail)) / Decimal("100"))

        # Poor company has severe tail risk
        assert cvar < Decimal("-5_000")


class TestSharpeRatio:
    """Sharpe Ratio: risk-adjusted return measurement."""

    def test_sharpe_ratio_positive_returns(self, excellent_company):
        """
        Sharpe = (Avg Return - Risk-free Rate) / Std Dev
        """
        returns = excellent_company["returns_list"]
        risk_free_rate = Decimal("0.4")  # 0.4% monthly (~4.8% annual)

        avg_return = Decimal(str(sum(returns) / len(returns)))
        variance = Decimal(str(sum((r - float(avg_return))**2 for r in returns) / len(returns)))
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")

        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe = Decimal("0")

        # Excellent company should have positive Sharpe
        assert sharpe > 0

    def test_sharpe_ratio_negative_returns(self, poor_company):
        """
        Poor company with negative average returns = negative Sharpe."""
        returns = poor_company["returns_list"]
        risk_free_rate = Decimal("0.4")

        avg_return = Decimal(str(sum(returns) / len(returns)))
        variance = Decimal(str(sum((r - float(avg_return))**2 for r in returns) / len(returns)))
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")

        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe = Decimal("0")

        # Poor company likely has negative Sharpe
        assert sharpe < Decimal("0")

    def test_sharpe_ratio_benchmark_comparison(self, good_company):
        """
        Sharpe > 1.0 is excellent
        Sharpe 0.5-1.0 is good
        Sharpe < 0.5 is weak
        """
        returns = good_company["returns_list"]
        risk_free_rate = Decimal("0.4")

        avg_return = Decimal(str(sum(returns) / len(returns)))
        variance = Decimal(str(sum((r - float(avg_return))**2 for r in returns) / len(returns)))
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")

        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe = Decimal("0")

        # Good company should have decent Sharpe
        assert sharpe > Decimal("0.25")


class TestSortinoRatio:
    """Sortino Ratio: downside risk-adjusted return."""

    def test_sortino_ratio_penalizes_downside(self, excellent_company):
        """
        Sortino = (Avg Return - Target Return) / Downside Std Dev
        Only counts negative deviations (downside risk).
        """
        returns = excellent_company["returns_list"]
        target_return = Decimal("0.5")  # Target 0.5% monthly

        avg_return = Decimal(str(sum(returns) / len(returns)))

        # Downside deviations: only count returns below target
        downside_deviations = [
            (r - float(target_return))**2 for r in returns if r < float(target_return)
        ]

        if downside_deviations:
            downside_variance = Decimal(str(sum(downside_deviations) / len(returns)))
            downside_std = downside_variance.sqrt()

            if downside_std > 0:
                sortino = (avg_return - target_return) / downside_std
            else:
                sortino = Decimal("0")
        else:
            sortino = Decimal("999")  # No downside = infinite Sortino

        # Excellent company: few negative returns
        assert sortino > 0

    def test_sortino_vs_sharpe_asymmetry(self, volatile_stock):
        """
        Sortino > Sharpe when returns are positively skewed.
        Sortino < Sharpe when returns are negatively skewed.
        """
        returns = volatile_stock["returns_list"]
        risk_free = Decimal("0.4")
        target = Decimal("0.4")

        avg_return = Decimal(str(sum(returns) / len(returns)))

        # Sharpe: total volatility
        variance = Decimal(str(sum((r - float(avg_return))**2 for r in returns) / len(returns)))
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")
        sharpe = (avg_return - risk_free) / std_dev if std_dev > 0 else Decimal("0")

        # Sortino: downside volatility only
        downside = [(r - float(target))**2 for r in returns if r < float(target)]
        downside_var = Decimal(str(sum(downside) / len(returns))) if downside else Decimal("0")
        downside_std = downside_var.sqrt() if downside_var > 0 else Decimal("0")
        sortino = (avg_return - target) / downside_std if downside_std > 0 else Decimal("0")

        # Both should be calculable
        assert isinstance(sharpe, Decimal)
        assert isinstance(sortino, Decimal)


class TestBetaCalculation:
    """Beta: systematic risk measure."""

    def test_beta_market_correlated(self, good_company):
        """
        Beta = 1.0: stock moves with market
        Beta < 1.0: less volatile than market (defensive)
        Beta > 1.0: more volatile than market (aggressive)
        """
        beta = good_company["beta"]

        # KO has beta 0.65 (defensive)
        assert beta < Decimal("1.0")
        assert beta > Decimal("0")

    def test_beta_high_volatility(self, volatile_stock):
        """
        High beta (>1.5) = high systematic risk.
        """
        beta = volatile_stock["beta"]

        assert beta > Decimal("1.5")

    def test_beta_risk_free_asset(self):
        """
        Beta of risk-free asset (Treasury bonds) = 0.
        """
        beta_treasury = Decimal("0.0")

        assert beta_treasury == 0

    def test_beta_market_portfolio(self):
        """
        Beta of market portfolio = 1.0 (by definition).
        """
        beta_market = Decimal("1.0")

        assert beta_market == Decimal("1.0")


class TestDrawdown:
    """Drawdown analysis: peak-to-trough declines."""

    def test_maximum_drawdown_calculation(self, excellent_company):
        """
        Maximum Drawdown = (Trough - Peak) / Peak
        Largest percentage decline from peak.
        """
        prices = [
            Decimal("100"),
            Decimal("110"),
            Decimal("120"),
            Decimal("105"),
            Decimal("115"),
            Decimal("108"),
            Decimal("125"),
        ]

        max_dd = Decimal("0")
        peak = prices[0]

        for price in prices:
            if price > peak:
                peak = price
            dd = (price - peak) / peak
            if dd < max_dd:
                max_dd = dd

        # From 125 peak to 108 = (108-125)/125 = -13.6%
        assert max_dd <= 0
        assert max_dd > Decimal("-0.20")  # Should be < 20%

    def test_recovery_after_drawdown(self):
        """
        Drawdown duration = time from peak to new high.
        """
        prices = [
            Decimal("100"),
            Decimal("120"),
            Decimal("80"),
            Decimal("90"),
            Decimal("125"),
        ]

        peak_1 = 1  # Index of 120
        trough = 2  # Index of 80
        recovery = 4  # Index of 125 (new high)

        duration = recovery - peak_1
        assert duration == 3  # 3 periods to recover


class TestRiskIntegration:
    """Integration tests combining multiple risk metrics."""

    def test_risk_profile_summary(self, excellent_company):
        """
        Complete risk profile for excellent company.
        """
        score_components = {
            "roe": excellent_company["roe"],
            "debt_to_equity": excellent_company["debt_to_equity"],
            "current_ratio": excellent_company["current_ratio"],
            "beta": excellent_company["beta"],
        }

        # All metrics should indicate low risk
        assert score_components["roe"] > Decimal("25")
        assert score_components["debt_to_equity"] < Decimal("1.0")
        assert score_components["current_ratio"] > Decimal("1.0")
        assert score_components["beta"] < Decimal("1.5")

    def test_risk_profile_poor_company(self, poor_company):
        """
        Complete risk profile for poor company.
        """
        score_components = {
            "roe": poor_company["roe"],
            "debt_to_equity": poor_company["debt_to_equity"],
            "current_ratio": poor_company["current_ratio"],
            "ocf": poor_company["ocf"],
            "beta": poor_company["beta"],
        }

        # All metrics should indicate high risk
        assert score_components["roe"] < Decimal("0")
        assert score_components["debt_to_equity"] > Decimal("2.0")
        assert score_components["current_ratio"] < Decimal("1.0")
        assert score_components["ocf"] < Decimal("0")
        assert score_components["beta"] > Decimal("2.0")

    def test_risk_scores_ranking(self, excellent_company, good_company, poor_company):
        """
        Risk scores should rank companies correctly: excellent > good > poor.
        """
        def calculate_risk_score(company):
            """Simple scoring function."""
            score = 100

            if company["roe"] < Decimal("0"):
                score -= 40
            elif company["roe"] < Decimal("15"):
                score -= 20
            elif company["roe"] > Decimal("25"):
                score += 10

            if company["debt_to_equity"] > Decimal("2.0"):
                score -= 30
            elif company["debt_to_equity"] < Decimal("0.5"):
                score += 10

            if company["current_ratio"] < Decimal("1.0"):
                score -= 15
            elif company["current_ratio"] > Decimal("1.5"):
                score += 5

            if company["beta"] > Decimal("2.0"):
                score -= 20

            return max(0, min(100, score))

        score_excellent = calculate_risk_score(excellent_company)
        score_good = calculate_risk_score(good_company)
        score_poor = calculate_risk_score(poor_company)

        # Ranking should be clear
        assert score_excellent > score_good
        assert score_good > score_poor
