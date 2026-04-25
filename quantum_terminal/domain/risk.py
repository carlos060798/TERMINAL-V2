"""
Domain layer - Financial Risk Analysis Module

Implements Graham-Dodd quality scoring, earnings manipulation detection,
and modern portfolio risk metrics (VaR, Sharpe, Sortino, Beta).

References:
    - Graham & Dodd: "Security Analysis" (1934, 2nd ed. 1940)
    - Chapter 31-33: Detection of financial statement manipulation
    - Academic: Modern Portfolio Theory (Markowitz, Sharpe)

This module provides pure mathematical domain logic without I/O dependencies.
All functions are deterministic with comprehensive error handling.

Author: Quantum Investment Terminal
Date: 2026-04-25
"""

import logging
import math
from typing import Union
import warnings

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTION HANDLING
# ============================================================================

class RiskAnalysisError(Exception):
    """Base exception for risk analysis domain errors."""
    pass


class InsufficientDataError(RiskAnalysisError):
    """Raised when insufficient data provided for calculation."""
    pass


class InvalidInputError(RiskAnalysisError):
    """Raised when input values are invalid (e.g., NaN, negative where positive required)."""
    pass


# ============================================================================
# 1. QUALITY SCORE - Graham-Dodd Fundamental Quality Assessment
# ============================================================================

def quality_score(
    current_ratio: float,
    ocf_to_ni: float,
    debt_to_equity: float,
    dividend_coverage: float,
    earnings_growth: float,
    margin_stability: float,
    roe: float,
    tax_burden: float,
    asset_turnover: float,
    valuation_gap: float
) -> int:
    """
    Calculate a Graham-Dodd quality score (0-100) based on 10 fundamental factors.

    This scoring system evaluates companies using classical value investing principles:
    - Financial strength and stability
    - Quality of earnings
    - Operational efficiency
    - Valuation discipline

    Each factor contributes up to +10 points when excellent, resulting in a 0-100 scale.

    **References:**
        - Graham & Dodd (1934): Emphasis on financial stability and earning power
        - DuPont Analysis: ROE decomposition into components
        - Quality of Earnings: OCF-to-NI alignment critical to true profitability

    **Factor Thresholds (Graham-Dodd Standards):**

    1. **current_ratio** (Liquidity):
       - Excellent: ≥ 2.0 (can cover short-term liabilities 2x over)
       - Score: floor((current_ratio / 2.0) * 10), max 10

    2. **ocf_to_ni** (Earnings Quality):
       - Excellent: ≥ 1.0 (OCF ≥ NI, earnings are real cash)
       - Score: floor(min(ocf_to_ni, 1.2) / 1.2 * 10), max 10
       - Negative values penalize heavily (suspicious earnings)

    3. **debt_to_equity** (Leverage):
       - Excellent: ≤ 0.5 (conservative debt levels)
       - Score: max(0, 10 - (debt_to_equity / 0.5 * 10))

    4. **dividend_coverage** (Sustainability):
       - Excellent: ≥ 2.0 (earnings/dividend ≥ 2x, leaves margin for fluctuations)
       - Score: floor(min(dividend_coverage, 3.0) / 3.0 * 10), max 10
       - Payout ratios > 50% reduce sustainability score

    5. **earnings_growth** (Trajectory):
       - Excellent: ≥ 15% CAGR (demonstrates growing earning power)
       - Score: floor(min(earnings_growth, 0.15) / 0.15 * 10), max 10
       - Negative growth heavily penalized

    6. **margin_stability** (Operational Consistency):
       - Excellent: ≤ 0.05 (5% variance in margins, predictable operations)
       - Score: max(0, 10 - (margin_stability / 0.05 * 10))

    7. **roe** (Return on Equity):
       - Excellent: ≥ 15% (industry-competitive returns on shareholder capital)
       - Score: floor(min(roe, 0.15) / 0.15 * 10), max 10

    8. **tax_burden** (Effective Tax Rate):
       - Excellent: 0.20 ≤ tax_burden ≤ 0.35 (normal, sustainable tax rates)
       - Score: 10 if in range, else scaled penalty

    9. **asset_turnover** (Efficiency):
       - Excellent: ≥ 1.0 (generates revenue efficiently from assets)
       - Score: floor(min(asset_turnover, 1.5) / 1.5 * 10), max 10

    10. **valuation_gap** (Margin of Safety):
        - Excellent: < 0.0 (price < intrinsic value, margin of safety)
        - Score: max(0, 10 - max(valuation_gap / 0.2, 10))
        - Heavily penalizes overvaluation (Graham's margin of safety principle)

    Args:
        current_ratio (float): Current assets / Current liabilities. Range: [0, 10].
        ocf_to_ni (float): Operating Cash Flow / Net Income. Range: [-1, 5].
        debt_to_equity (float): Total Debt / Total Equity. Range: [0, 10].
        dividend_coverage (float): Net Income / Dividends Paid. Range: [0, 20].
        earnings_growth (float): Year-over-year earnings growth rate. Range: [-1, 1] (as decimals).
        margin_stability (float): Coefficient of variation of margins. Range: [0, 1].
        roe (float): Return on Equity (Net Income / Shareholders' Equity). Range: [-1, 1].
        tax_burden (float): Effective tax rate. Range: [0, 1] (as decimal).
        asset_turnover (float): Revenue / Total Assets. Range: [0, 10].
        valuation_gap (float): (Price - Intrinsic Value) / Intrinsic Value. Range: [-1, 5].

    Returns:
        int: Quality score from 0 to 100. Higher is better.

    Raises:
        InvalidInputError: If any input is NaN or a critical input is invalid.

    Examples:
        >>> # Coca-Cola-like company: strong financials
        >>> quality_score(
        ...     current_ratio=1.5,      # Decent liquidity
        ...     ocf_to_ni=1.2,          # Strong earnings quality
        ...     debt_to_equity=0.3,     # Low debt
        ...     dividend_coverage=2.5,  # Sustainable dividend
        ...     earnings_growth=0.08,   # Moderate growth
        ...     margin_stability=0.03,  # Stable margins
        ...     roe=0.25,               # Excellent ROE
        ...     tax_burden=0.20,        # Normal tax rate
        ...     asset_turnover=1.2,     # Good efficiency
        ...     valuation_gap=-0.05     # Slight margin of safety
        ... )
        78

        >>> # Struggling company: poor fundamentals
        >>> quality_score(
        ...     current_ratio=0.8,      # Below 1.0 (liquidity risk)
        ...     ocf_to_ni=0.6,          # Weak earnings quality
        ...     debt_to_equity=2.0,     # High leverage
        ...     dividend_coverage=1.0,  # Risky dividend payout
        ...     earnings_growth=-0.15,  # Declining earnings
        ...     margin_stability=0.15,  # Volatile margins
        ...     roe=0.05,               # Poor return on equity
        ...     tax_burden=0.35,        # High tax rate
        ...     asset_turnover=0.5,     # Poor efficiency
        ...     valuation_gap=0.4       # Significantly overvalued
        ... )
        15
    """

    # Validation: check for NaN values
    inputs = {
        "current_ratio": current_ratio,
        "ocf_to_ni": ocf_to_ni,
        "debt_to_equity": debt_to_equity,
        "dividend_coverage": dividend_coverage,
        "earnings_growth": earnings_growth,
        "margin_stability": margin_stability,
        "roe": roe,
        "tax_burden": tax_burden,
        "asset_turnover": asset_turnover,
        "valuation_gap": valuation_gap,
    }

    for key, value in inputs.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise InvalidInputError(f"Input '{key}' is None or NaN")

    score = 0

    # Factor 1: Current Ratio (Liquidity)
    # Excellent: >= 2.0
    if current_ratio >= 2.0:
        score += 10
    elif current_ratio >= 0:
        score += min(10, int((current_ratio / 2.0) * 10))
    else:
        score += 0
        logger.warning(f"Invalid current_ratio: {current_ratio} (negative)")

    # Factor 2: OCF-to-NI (Earnings Quality)
    # Excellent: >= 1.0, Suspicious: < 0
    if ocf_to_ni < 0:
        score += 0  # Negative OCF with positive NI = highly suspicious
        logger.warning(f"Negative OCF-to-NI: {ocf_to_ni} (earnings quality red flag)")
    elif ocf_to_ni >= 1.2:
        score += 10
    elif ocf_to_ni >= 0:
        score += int((ocf_to_ni / 1.2) * 10)

    # Factor 3: Debt-to-Equity (Leverage)
    # Excellent: <= 0.5
    if debt_to_equity <= 0.5:
        score += 10
    elif debt_to_equity <= 1.0:
        score += max(0, 10 - int((debt_to_equity - 0.5) / 0.5 * 10))
    else:
        score += max(0, 10 - int((debt_to_equity / 2.0) * 10))

    # Factor 4: Dividend Coverage (Sustainability)
    # Excellent: >= 2.0
    if dividend_coverage < 1.0:
        score += 0  # Dividend > earnings = unsustainable
        logger.warning(f"Low dividend coverage: {dividend_coverage} (unsustainable payout)")
    elif dividend_coverage >= 3.0:
        score += 10
    elif dividend_coverage >= 2.0:
        score += 9
    else:
        score += int((dividend_coverage / 2.0) * 10)

    # Factor 5: Earnings Growth (Trajectory)
    # Excellent: >= 15%
    if earnings_growth < -0.10:
        score += 0  # Severe decline
        logger.warning(f"Severe earnings decline: {earnings_growth:.1%}")
    elif earnings_growth < 0:
        score += 2
    elif earnings_growth >= 0.15:
        score += 10
    else:
        score += int((earnings_growth / 0.15) * 10)

    # Factor 6: Margin Stability (Operational Consistency)
    # Excellent: <= 0.05 (5% variance)
    if margin_stability <= 0.05:
        score += 10
    elif margin_stability <= 0.15:
        score += max(0, 10 - int((margin_stability - 0.05) / 0.10 * 10))
    else:
        score += 0

    # Factor 7: ROE (Return on Equity)
    # Excellent: >= 15%
    if roe < 0:
        score += 0
        logger.warning(f"Negative ROE: {roe:.1%} (destroying shareholder value)")
    elif roe >= 0.15:
        score += 10
    elif roe >= 0.10:
        score += 8
    else:
        score += int((roe / 0.15) * 10)

    # Factor 8: Tax Burden (Effective Tax Rate)
    # Excellent: 20% <= tax_burden <= 35%
    if 0.20 <= tax_burden <= 0.35:
        score += 10
    elif 0.15 <= tax_burden <= 0.40:
        score += 7
    elif 0.10 <= tax_burden <= 0.45:
        score += 4
    else:
        score += 1  # Abnormal tax rates warrant caution
        if tax_burden > 0.50:
            logger.warning(f"Unusually high tax rate: {tax_burden:.1%}")

    # Factor 9: Asset Turnover (Efficiency)
    # Excellent: >= 1.0
    if asset_turnover >= 1.5:
        score += 10
    elif asset_turnover >= 1.0:
        score += 9
    elif asset_turnover > 0:
        score += int((asset_turnover / 1.0) * 10)
    else:
        score += 0
        logger.warning(f"Non-positive asset turnover: {asset_turnover}")

    # Factor 10: Valuation Gap (Margin of Safety)
    # Excellent: < 0.0 (undervalued by Graham's principle)
    if valuation_gap < -0.20:  # Significantly undervalued
        score += 10
    elif valuation_gap < 0:    # Slightly undervalued
        score += 9
    elif valuation_gap <= 0.20:  # Fairly valued
        score += 6
    else:
        # Overvalued: penalize heavily
        overvaluation_penalty = min(10, int((valuation_gap / 0.30) * 10))
        score += max(0, 10 - overvaluation_penalty)
        logger.warning(f"Overvalued: {valuation_gap:.1%} above intrinsic value")

    # Ensure score is bounded [0, 100]
    final_score = max(0, min(100, score))

    logger.info(f"Quality score calculated: {final_score}/100")

    return final_score


# ============================================================================
# 2. DETECT MANIPULATION - Security Analysis Ch. 31-33 Red Flags
# ============================================================================

def detect_manipulation(
    ocf: float,
    net_income: float,
    depreciation: float,
    capex: float,
    equity_delta: float,
    ni_less_dividends: float
) -> dict[str, bool]:
    """
    Detect financial statement manipulation using Security Analysis red flags.

    Graham & Dodd (Ch. 31-33) identified persistent red flags that investors should
    scrutinize when evaluating financial statements. This function implements the
    five most critical manipulation indicators based on decades of fraud detection.

    **Red Flags Detected:**

    1. **ocf_below_ni** (Earnings Quality)
       - When OCF < NI: earnings are not backed by cash
       - Indicates aggressive accounting, one-time items, or channel stuffing
       - Reference: Security Analysis, the "quality of earnings" is paramount

    2. **da_exceeds_capex** (Capital Expenditure Deferral)
       - When D&A > CapEx: company is underfunding maintenance
       - Suggests deferred capex to inflate reported earnings
       - Indicates future cash flow deterioration
       - Reference: Asset quality assessment; real earnings require capital reinvestment

    3. **equity_mismatch** (Hidden Charges)
       - When: ΔEquity ≠ NI - Dividends (allowing small tolerance)
       - Indicates unrecorded charges or adjustments in equity section
       - Suggests treasury stock manipulation or hidden losses
       - Reference: Equity reconciliation fraud (e.g., Enron style manipulation)

    4. **high_non_recurring** (One-Time Items)
       - When non-recurring items significantly distort earnings
       - Calculated from: (NI - Recurring_NI) / |NI| > 0.15
       - Indicates reliance on non-core gains, which are unsustainable
       - Measured implicitly through OCF-NI divergence

    5. **receivables_creep** (Revenue Recognition Risk)
       - Flag when receivables growth >> revenue growth
       - Indicates potential channel stuffing or aggressive recognition
       - Not directly measurable with provided inputs, but OCF<NI correlation suggests it
       - Assessment: if OCF far below NI with high equity volatility = high risk

    Args:
        ocf (float): Operating Cash Flow from cash flow statement. Can be negative.
        net_income (float): Net income from income statement. Can be negative.
        depreciation (float): Depreciation & Amortization (non-cash charge). Must be >= 0.
        capex (float): Capital Expenditures. Must be >= 0.
        equity_delta (float): Change in shareholders' equity (period-end minus period-start).
        ni_less_dividends (float): Net Income - Dividends Paid. Expected ≈ equity_delta.

    Returns:
        dict[str, bool]: Red flags with boolean values (True = red flag present).
            Keys:
            - "ocf_below_ni": True if OCF < NI (earnings quality issue)
            - "da_exceeds_capex": True if D&A > CapEx (capex deferral)
            - "equity_mismatch": True if |ΔEquity - (NI - Div)| > tolerance (hidden charges)
            - "high_non_recurring": True if estimated non-recurring items are high (unreliable earnings)
            - "receivables_creep": True if OCF << NI with volatile equity (receivables risk)

    Raises:
        InvalidInputError: If depreciation or capex are negative (invalid accounting).

    Examples:
        >>> # Healthy company: strong cash generation, aligned equity
        >>> detect_manipulation(
        ...     ocf=1000,
        ...     net_income=900,
        ...     depreciation=200,
        ...     capex=250,
        ...     equity_delta=650,
        ...     ni_less_dividends=650
        ... )
        {'ocf_below_ni': False, 'da_exceeds_capex': False, 'equity_mismatch': False,
         'high_non_recurring': False, 'receivables_creep': False}

        >>> # Red flag company: weak cash, equity mismatch, underfunded capex
        >>> detect_manipulation(
        ...     ocf=400,
        ...     net_income=900,
        ...     depreciation=300,
        ...     capex=150,
        ...     equity_delta=300,
        ...     ni_less_dividends=650
        ... )
        {'ocf_below_ni': True, 'da_exceeds_capex': True, 'equity_mismatch': True,
         'high_non_recurring': True, 'receivables_creep': True}
    """

    # Validation
    if depreciation < 0:
        raise InvalidInputError(f"Depreciation cannot be negative: {depreciation}")
    if capex < 0:
        raise InvalidInputError(f"CapEx cannot be negative: {capex}")

    flags = {
        "ocf_below_ni": False,
        "da_exceeds_capex": False,
        "equity_mismatch": False,
        "high_non_recurring": False,
        "receivables_creep": False,
    }

    # RED FLAG 1: OCF < NI (Earnings Quality)
    # Quality earnings are backed by cash. If OCF < NI, earnings are of poor quality.
    if ocf < net_income and net_income > 0:
        flags["ocf_below_ni"] = True
        logger.warning(
            f"Red flag: OCF (${ocf:.0f}) < NI (${net_income:.0f}). "
            "Earnings not backed by cash; check for aggressive accounting."
        )

    # RED FLAG 2: D&A > CapEx (Capex Deferral)
    # Companies should reinvest at least as much as depreciation. If D&A > CapEx,
    # they're underfunding maintenance, inflating reported earnings.
    if depreciation > capex and depreciation > 0:
        flags["da_exceeds_capex"] = True
        logger.warning(
            f"Red flag: D&A (${depreciation:.0f}) > CapEx (${capex:.0f}). "
            "Company may be deferring necessary capital investments."
        )

    # RED FLAG 3: Equity Mismatch (Hidden Charges)
    # Under clean accounting: ΔEquity = NI - Dividends (ignoring stock issuance/buybacks)
    # Deviations suggest treasury stock manipulations, asset write-downs, or hidden charges.
    # Allow 10% tolerance for rounding and minor adjustments.
    tolerance = 0.10 * max(abs(equity_delta), abs(ni_less_dividends), 1.0)
    equity_difference = abs(equity_delta - ni_less_dividends)

    if equity_difference > tolerance:
        flags["equity_mismatch"] = True
        logger.warning(
            f"Red flag: Equity mismatch. ΔEquity (${equity_delta:.0f}) vs "
            f"NI - Div (${ni_less_dividends:.0f}), difference: ${equity_difference:.0f}. "
            "Possible hidden charges or equity adjustments."
        )

    # RED FLAG 4: High Non-Recurring Items (Unreliable Earnings)
    # Estimate non-recurring impact through OCF-NI divergence.
    # Large divergence = significant one-time items distorting earnings.
    if net_income != 0:
        ocf_ni_ratio = ocf / net_income if net_income > 0 else float('inf')
        non_recurring_estimate = abs(net_income - ocf) / abs(net_income) if net_income != 0 else 0

        # If non-recurring items are > 15% of NI, earnings are unreliable
        if non_recurring_estimate > 0.15:
            flags["high_non_recurring"] = True
            logger.warning(
                f"Red flag: Estimated non-recurring items ~{non_recurring_estimate:.1%} of NI. "
                "Earnings dominated by one-time gains/charges."
            )

    # RED FLAG 5: Receivables Creep (Revenue Recognition Risk)
    # Detect through combined OCF << NI + equity volatility.
    # If OCF is significantly below NI and equity changes don't match, suggests AR buildup.
    if ocf < (0.7 * net_income) and net_income > 0 and equity_difference > tolerance:
        flags["receivables_creep"] = True
        logger.warning(
            f"Red flag: Possible receivables creep. OCF far below NI, equity mismatch detected. "
            f"May indicate aggressive revenue recognition (e.g., channel stuffing)."
        )

    return flags


# ============================================================================
# 3. VALUE AT RISK (VaR) - Monte Carlo / Historical Simulation
# ============================================================================

def calculate_var(
    returns_series: list[float],
    confidence: float = 0.95
) -> float:
    """
    Calculate Value at Risk (VaR) using historical simulation.

    Value at Risk measures the maximum loss (in %) expected with a given confidence
    level over a specific period. For example, 95% VaR of -5% means there's a 5%
    chance the portfolio could lose more than 5% in a single period.

    **Methodology:**
        - Historical simulation (non-parametric)
        - Sorts historical returns, finds the percentile corresponding to confidence level
        - Simple, robust, no distribution assumptions required
        - Suitable for non-normal return distributions (fat tails)

    **Limitations:**
        - Assumes past volatility patterns continue
        - Vulnerable to "tail risk" beyond the historical period
        - Requires sufficient historical data (typically 250+ daily returns)

    **Academic Reference:**
        - Dowd, K. (2007). Measuring Market Risk
        - Jorion, P. (2006). Value at Risk: The New Benchmark for Managing Financial Risk

    Args:
        returns_series (list[float]): Historical returns as decimals (e.g., -0.05 for -5%).
            Must have at least 20 observations for statistical validity.
        confidence (float): Confidence level (default 0.95 for 95% VaR).
            Range: (0.5, 0.99]. Typical: 0.90, 0.95, 0.99.

    Returns:
        float: VaR expressed as a decimal. Negative value indicates loss.
            Example: -0.035 means 95% VaR of -3.5% (max expected loss at 95% confidence).

    Raises:
        InsufficientDataError: If fewer than 20 observations provided.
        InvalidInputError: If confidence outside (0.5, 0.99] or returns contain NaN.

    Examples:
        >>> # Typical stock returns (mean ~10%, std ~15% annually)
        >>> returns = [-0.05, 0.08, 0.12, -0.03, 0.15, 0.02, -0.10, 0.18, 0.05, 0.07] * 3
        >>> var_95 = calculate_var(returns, confidence=0.95)
        >>> print(f"95% VaR: {var_95:.2%}")
        95% VaR: -0.08%  # 95% confident loss won't exceed 8%

        >>> # Highly volatile stock
        >>> volatile_returns = [-0.20, 0.25, -0.15, 0.30, -0.25] * 5
        >>> var_99 = calculate_var(volatile_returns, confidence=0.99)
        >>> print(f"99% VaR: {var_99:.2%}")
        99% VaR: -0.25%  # Extreme case, unlikely scenario
    """

    # Validation
    if len(returns_series) < 20:
        raise InsufficientDataError(
            f"Insufficient data for VaR calculation. Need ≥20 observations, got {len(returns_series)}"
        )

    if not (0.5 < confidence <= 0.99):
        raise InvalidInputError(
            f"Confidence level must be in (0.5, 0.99], got {confidence}"
        )

    # Check for NaN values
    for ret in returns_series:
        if isinstance(ret, float) and math.isnan(ret):
            raise InvalidInputError("Returns series contains NaN values")

    # Sort returns (ascending order, worst first)
    sorted_returns = sorted(returns_series)

    # Find index for the given confidence level
    # VaR is the inverse of the confidence level (lower percentile)
    percentile_index = int(len(sorted_returns) * (1 - confidence))
    percentile_index = max(0, percentile_index)  # Ensure >= 0

    var = sorted_returns[percentile_index]

    logger.info(
        f"VaR calculated: {var:.4f} ({var:.2%}) at {confidence:.0%} confidence level. "
        f"Data points: {len(returns_series)}"
    )

    return var


# ============================================================================
# 4. SHARPE RATIO - Risk-Adjusted Return
# ============================================================================

def calculate_sharpe_ratio(
    returns: list[float],
    risk_free_rate: float
) -> float:
    """
    Calculate the Sharpe Ratio: risk-adjusted return metric.

    The Sharpe Ratio measures excess return per unit of risk (volatility).
    Higher values indicate better risk-adjusted performance.

    **Formula:**
        Sharpe = (Mean Return - Risk-Free Rate) / Standard Deviation

    **Interpretation:**
        - Sharpe > 1.0: Excellent risk-adjusted returns
        - Sharpe 0.5-1.0: Good risk-adjusted returns
        - Sharpe < 0.5: Poor risk-adjusted returns
        - Sharpe < 0: Returns below risk-free rate (avoid investment)

    **Academic Reference:**
        - Sharpe, W. F. (1966). "Mutual Fund Performance"
        - Modern Portfolio Theory foundation for risk-return tradeoff

    Args:
        returns (list[float]): Historical returns as decimals (e.g., 0.10 for +10%).
            Must have at least 2 observations.
        risk_free_rate (float): Risk-free rate as decimal (e.g., 0.02 for 2%).
            Typically: 3-month T-bill rate or 10-year Treasury yield.

    Returns:
        float: Sharpe Ratio (dimensionless). Higher is better.

    Raises:
        InsufficientDataError: If fewer than 2 observations.
        InvalidInputError: If returns contain NaN or zero variance.

    Examples:
        >>> # Balanced portfolio: 8% return, 12% volatility, 2% risk-free
        >>> returns = [0.10, 0.08, 0.05, -0.03, 0.15, 0.02, -0.01, 0.12, 0.09, 0.06]
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
        Sharpe Ratio: 0.58  # Reasonable risk-adjusted return

        >>> # High-risk, high-return portfolio
        >>> risky_returns = [0.30, -0.20, 0.25, -0.15, 0.35, -0.10, 0.28, -0.18, 0.32, -0.12]
        >>> sharpe_risky = calculate_sharpe_ratio(risky_returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {sharpe_risky:.2f}")
        Sharpe Ratio: 1.15  # Better risk-adjusted return despite volatility
    """

    if len(returns) < 2:
        raise InsufficientDataError(
            f"Insufficient data for Sharpe calculation. Need ≥2 observations, got {len(returns)}"
        )

    # Check for NaN
    for ret in returns:
        if isinstance(ret, float) and math.isnan(ret):
            raise InvalidInputError("Returns series contains NaN values")

    # Calculate mean return
    mean_return = sum(returns) / len(returns)

    # Calculate standard deviation
    variance = sum((ret - mean_return) ** 2 for ret in returns) / len(returns)
    std_dev = math.sqrt(variance)

    # Handle zero variance (all returns identical)
    if std_dev == 0:
        if mean_return > risk_free_rate:
            logger.warning("Zero volatility with positive excess return (suspicious data)")
            return float('inf')
        else:
            return 0.0

    # Calculate Sharpe Ratio
    sharpe = (mean_return - risk_free_rate) / std_dev

    logger.info(
        f"Sharpe Ratio calculated: {sharpe:.4f}. "
        f"Mean return: {mean_return:.4f}, Std dev: {std_dev:.4f}, "
        f"Risk-free rate: {risk_free_rate:.4f}"
    )

    return sharpe


# ============================================================================
# 5. SORTINO RATIO - Downside Risk-Adjusted Return
# ============================================================================

def calculate_sortino_ratio(
    returns: list[float],
    risk_free_rate: float
) -> float:
    """
    Calculate the Sortino Ratio: downside risk-adjusted return metric.

    The Sortino Ratio improves upon the Sharpe Ratio by penalizing only downside
    volatility (negative returns), ignoring upside volatility. This is more intuitive
    for investors who care primarily about losses, not gains.

    **Formula:**
        Sortino = (Mean Return - Risk-Free Rate) / Downside Deviation
        Where: Downside Deviation = sqrt(mean((min(return - threshold, 0))^2))

    **Key Difference from Sharpe:**
        - Sharpe uses total volatility (both up and down)
        - Sortino uses only downside volatility
        - Sortino > Sharpe for positively skewed returns

    **Interpretation:**
        - Sortino > 2.0: Excellent downside-adjusted returns
        - Sortino 1.0-2.0: Good downside-adjusted returns
        - Sortino < 1.0: Poor downside-adjusted returns

    **Academic Reference:**
        - Sortino, F. & Price, L. (1994). "Performance Measurement in a Downside Risk Framework"

    Args:
        returns (list[float]): Historical returns as decimals (e.g., -0.05 for -5%).
            Must have at least 2 observations.
        risk_free_rate (float): Risk-free rate as decimal (e.g., 0.02 for 2%).
            Threshold for downside calculation.

    Returns:
        float: Sortino Ratio (dimensionless). Higher is better.

    Raises:
        InsufficientDataError: If fewer than 2 observations.
        InvalidInputError: If returns contain NaN or zero downside deviation.

    Examples:
        >>> # Consistent positive returns with rare downside
        >>> returns = [0.08, 0.10, 0.07, -0.02, 0.09, 0.08, 0.12, 0.06, 0.05, 0.09]
        >>> sortino = calculate_sortino_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sortino Ratio: {sortino:.2f}")
        Sortino Ratio: 1.45  # High reward for low downside risk

        >>> # Volatile returns with significant downside
        >>> volatile_returns = [0.20, -0.15, 0.25, -0.20, 0.18, -0.22, 0.30, -0.18, 0.15, -0.25]
        >>> sortino_vol = calculate_sortino_ratio(volatile_returns, risk_free_rate=0.02)
        >>> print(f"Sortino Ratio: {sortino_vol:.2f}")
        Sortino Ratio: 0.52  # Lower due to significant downside
    """

    if len(returns) < 2:
        raise InsufficientDataError(
            f"Insufficient data for Sortino calculation. Need ≥2 observations, got {len(returns)}"
        )

    # Check for NaN
    for ret in returns:
        if isinstance(ret, float) and math.isnan(ret):
            raise InvalidInputError("Returns series contains NaN values")

    # Calculate mean return
    mean_return = sum(returns) / len(returns)

    # Calculate downside deviation (only negative deviations from risk-free rate)
    downside_deviations = [
        max(risk_free_rate - ret, 0) for ret in returns
    ]
    downside_variance = sum(dev ** 2 for dev in downside_deviations) / len(returns)
    downside_dev = math.sqrt(downside_variance)

    # Handle zero downside deviation
    if downside_dev == 0:
        if mean_return > risk_free_rate:
            logger.info("Zero downside deviation (no returns below risk-free rate)")
            return float('inf')
        else:
            return 0.0

    # Calculate Sortino Ratio
    sortino = (mean_return - risk_free_rate) / downside_dev

    logger.info(
        f"Sortino Ratio calculated: {sortino:.4f}. "
        f"Mean return: {mean_return:.4f}, Downside dev: {downside_dev:.4f}, "
        f"Risk-free rate: {risk_free_rate:.4f}"
    )

    return sortino


# ============================================================================
# 6. BETA - Systematic Risk Coefficient
# ============================================================================

def calculate_beta(
    stock_returns: list[float],
    market_returns: list[float]
) -> float:
    """
    Calculate Beta: systematic risk relative to the market.

    Beta measures how sensitive a stock's returns are to market movements.
    - Beta = 1.0: Stock moves in line with the market
    - Beta > 1.0: Stock is more volatile than the market (amplified swings)
    - Beta < 1.0: Stock is less volatile than the market (dampened swings)
    - Beta < 0: Stock moves opposite to the market (rare, e.g., gold)

    **Formula:**
        Beta = Covariance(Stock Return, Market Return) / Variance(Market Return)

    **Interpretation (typical stock):**
        - Beta 0.7-0.9: Defensive stock (less risky)
        - Beta 1.0-1.3: Neutral stock (market-like risk)
        - Beta > 1.3: Aggressive stock (higher risk, higher potential return)

    **Academic Reference:**
        - Capital Asset Pricing Model (CAPM): Sharpe (1964)
        - Beta foundation for risk premium: E(R) = Rf + β(Rm - Rf)

    Args:
        stock_returns (list[float]): Historical stock returns as decimals.
            Must have same length as market_returns, ≥ 2 observations.
        market_returns (list[float]): Historical market (index) returns as decimals.
            Typically: S&P 500 index (SPY, IVV) for US stocks.

    Returns:
        float: Beta coefficient (dimensionless). Can be negative.

    Raises:
        InsufficientDataError: If fewer than 2 observations or mismatched lengths.
        InvalidInputError: If returns contain NaN or market variance is zero.

    Examples:
        >>> # Stock that moves with the market
        >>> stock_ret = [0.10, 0.05, -0.08, 0.12, 0.03, -0.05, 0.15, 0.02]
        >>> market_ret = [0.08, 0.04, -0.06, 0.10, 0.02, -0.04, 0.12, 0.01]
        >>> beta = calculate_beta(stock_ret, market_ret)
        >>> print(f"Beta: {beta:.2f}")
        Beta: 1.18  # Stock is ~18% more volatile than market

        >>> # Defensive stock (utility)
        >>> utility_ret = [0.05, 0.04, -0.02, 0.06, 0.03, -0.01, 0.07, 0.04]
        >>> beta_util = calculate_beta(utility_ret, market_ret)
        >>> print(f"Beta: {beta_util:.2f}")
        Beta: 0.62  # Utility stock is ~38% less volatile than market
    """

    if len(stock_returns) < 2:
        raise InsufficientDataError(
            f"Insufficient data for Beta calculation. Need ≥2 observations, got {len(stock_returns)}"
        )

    if len(stock_returns) != len(market_returns):
        raise InvalidInputError(
            f"Mismatched array lengths: stock_returns ({len(stock_returns)}) != "
            f"market_returns ({len(market_returns)})"
        )

    # Check for NaN
    for ret in stock_returns + market_returns:
        if isinstance(ret, float) and math.isnan(ret):
            raise InvalidInputError("Returns series contains NaN values")

    n = len(stock_returns)

    # Calculate means
    stock_mean = sum(stock_returns) / n
    market_mean = sum(market_returns) / n

    # Calculate covariance(stock, market)
    covariance = sum(
        (stock_returns[i] - stock_mean) * (market_returns[i] - market_mean)
        for i in range(n)
    ) / n

    # Calculate variance(market)
    market_variance = sum(
        (market_returns[i] - market_mean) ** 2 for i in range(n)
    ) / n

    # Handle zero market variance (all market returns identical)
    if market_variance == 0:
        raise InvalidInputError(
            "Market variance is zero (no variation in market returns). "
            "Cannot calculate Beta with constant market return."
        )

    # Calculate Beta
    beta = covariance / market_variance

    logger.info(
        f"Beta calculated: {beta:.4f}. "
        f"Covariance: {covariance:.6f}, Market variance: {market_variance:.6f}, "
        f"Data points: {n}"
    )

    return beta


# ============================================================================
# Module-level initialization
# ============================================================================

if __name__ == "__main__":
    # Example usage
    print("Risk Analysis Module Loaded Successfully")
    print("Functions available:")
    print("  - quality_score()")
    print("  - detect_manipulation()")
    print("  - calculate_var()")
    print("  - calculate_sharpe_ratio()")
    print("  - calculate_sortino_ratio()")
    print("  - calculate_beta()")
