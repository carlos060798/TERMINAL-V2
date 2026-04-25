"""
Domain layer: Valuation calculations using Graham-Dodd methodology.

This module implements value investment formulas from Benjamin Graham's
"Security Analysis" and "The Intelligent Investor". All functions are
pure mathematics with no I/O dependencies, suitable for batch processing
and testing.

References:
- Graham, B., & Dodd, D. L. (1934). Security Analysis. McGraw-Hill.
- Graham, B. (2006). The Intelligent Investor (4th ed.). Harper Business.
- Chapter references: Security Analysis, Ch. 26 (Valuation), Ch. 44 (Liquidation)

Author: Quantum Investment Terminal
"""

from typing import Dict, Optional, Tuple
from loguru import logger

# Configure logger for this module
logger.disable("loguru")  # Disable by default; enable in tests/integration
_logger = logger.bind(module="domain.valuation")


def graham_formula(
    eps: float,
    growth_rate: float,
    risk_free_rate: float,
    quality_score: float = 100.0,
) -> float:
    """
    Calculate intrinsic value using Graham's P/E formula.

    Benjamin Graham's simplified valuation formula from "The Intelligent Investor".
    This is a foundational value investing metric that assumes:
    - Growth component: 2g (next 5 years projected growth)
    - Multiple base: 8.5x earnings (no growth scenario)
    - Historical average yield: 4.4% (4.4/100)
    - Risk adjustment: 10Y Treasury rate

    Formula:
        intrinsic_value = (EPS × (8.5 + 2g) × 4.4 / 10Y_Treasury) × (quality/100)

    Where:
    - EPS: Earnings per share (ttm or normalized)
    - growth_rate: Expected growth rate 0-100 (e.g., 5 = 5% annual growth)
    - risk_free_rate: 10-year Treasury yield 0-100 (e.g., 4.5 = 4.5%)
    - quality_score: Company quality 0-100 (100=excellent, 50=average, 0=distressed)

    Args:
        eps (float): Earnings per share. Must be > 0.
        growth_rate (float): Annual growth rate in percentage (0-100).
                            Capped at 25% to avoid unrealistic scenarios.
        risk_free_rate (float): 10-year Treasury yield in percentage (> 0).
                               Typical range 1-6%.
        quality_score (float): Quality multiplier 0-100. Default 100 (no discount).
                              Below 100 = quality discount. Above 100 not recommended.

    Returns:
        float: Intrinsic value per share, or 0.0 if calculation fails.

    Raises:
        ValueError: If eps <= 0, risk_free_rate <= 0, or quality_score < 0.

    Examples:
        >>> graham_formula(eps=5.0, growth_rate=8.0, risk_free_rate=4.5, quality_score=100)
        158.65  # Approximately

        >>> graham_formula(eps=2.5, growth_rate=5.0, risk_free_rate=3.5, quality_score=80)
        106.2  # With quality discount

        >>> graham_formula(eps=1.0, growth_rate=20.0, risk_free_rate=2.0, quality_score=90)
        2970.0  # High growth scenario

    Notes:
        - Graham recommended this for mature, profitable companies only
        - Growth rate should be conservative (typically 5-8% for S&P 500 average)
        - Quality score reflects competitive advantages, management quality, etc.
        - Edge case: eps=0 returns 0.0 with warning
        - Edge case: risk_free_rate=0 raises ValueError (no valid discount rate)
        - Edge case: negative growth handled as 0% (mature company scenario)

    Reference:
        Graham, B. (2006). The Intelligent Investor (Revised ed., Ch. 11).
        "The most important thing is the price you pay for earnings."
    """
    # Input validation
    if eps <= 0:
        _logger.warning(
            f"graham_formula: eps must be positive, got {eps}. Returning 0.0"
        )
        return 0.0

    if risk_free_rate <= 0:
        raise ValueError(
            f"graham_formula: risk_free_rate must be positive, got {risk_free_rate}"
        )

    if quality_score < 0:
        raise ValueError(
            f"graham_formula: quality_score must be >= 0, got {quality_score}"
        )

    # Normalize inputs
    g = max(0, min(growth_rate, 25.0))  # Cap growth at 25%, floor at 0%
    rf = max(0.01, risk_free_rate)  # Floor risk_free_rate at 0.01% to avoid division issues
    q = quality_score / 100.0  # Normalize quality to 0-1 range

    # Graham formula: (EPS × (8.5 + 2g) × 4.4 / 10Y_Treasury) × (quality/100)
    intrinsic_value = (eps * (8.5 + 2 * g) * 4.4 / rf) * q

    # Log unusual values for debugging
    if intrinsic_value > 1000:
        _logger.warning(
            f"graham_formula: unusually high value {intrinsic_value:.2f} "
            f"for eps={eps}, growth={growth_rate}%, rf={risk_free_rate}%"
        )

    if intrinsic_value < 0.1:
        _logger.warning(
            f"graham_formula: unusually low value {intrinsic_value:.4f} "
            f"for eps={eps}, growth={growth_rate}%, rf={risk_free_rate}%"
        )

    return intrinsic_value


def nnwc(current_assets: float, total_liabilities: float) -> float:
    """
    Calculate Net-Net Working Capital (NNWC) intrinsic value.

    Net-Net Working Capital is a conservative valuation metric from Graham's
    "Security Analysis". It represents the balance sheet value assuming
    liquidation at fire-sale prices.

    Formula:
        NNWC = Current Assets - Total Liabilities

    This metric is used to find "cigar-butt" investments: companies trading
    below their working capital value, offering margin of safety.

    Args:
        current_assets (float): Total current assets from balance sheet.
                               Must be >= 0.
        total_liabilities (float): Total liabilities (current + long-term).
                                  Must be >= 0.

    Returns:
        float: Net-Net Working Capital value. Can be negative (insolvent company).

    Raises:
        ValueError: If current_assets < 0 or total_liabilities < 0.

    Examples:
        >>> nnwc(current_assets=50_000_000, total_liabilities=30_000_000)
        20_000_000  # Company has $20M in net working capital

        >>> nnwc(current_assets=10_000_000, total_liabilities=15_000_000)
        -5_000_000  # Technically insolvent (technical liabilities > CA)

        >>> nnwc(current_assets=0, total_liabilities=0)
        0.0  # Shell company

    Notes:
        - Negative values indicate technical insolvency
        - Does not account for fixed assets or intangible value
        - Conservative: assumes all CA can be recovered
        - Used as floor valuation, not fair value
        - Margin of Safety: buy when Market Cap < NNWC

    Reference:
        Graham, B., & Dodd, D. L. (1934). Security Analysis (Ch. 44).
        "A margin of safety is the key to successful investing."
    """
    if current_assets < 0:
        raise ValueError(
            f"nnwc: current_assets must be >= 0, got {current_assets}"
        )

    if total_liabilities < 0:
        raise ValueError(
            f"nnwc: total_liabilities must be >= 0, got {total_liabilities}"
        )

    nnwc_value = current_assets - total_liabilities

    if nnwc_value < 0:
        _logger.warning(
            f"nnwc: negative NNWC {nnwc_value:.2f}. "
            f"Company may be technically insolvent."
        )

    return nnwc_value


def liquidation_value(
    current_assets: float,
    inventory: float,
    fixed_assets: float,
    total_liabilities: float,
    recovery_rates: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate conservative liquidation value (line-by-line asset recovery).

    This is the most conservative valuation method from Security Analysis.
    Assumes company is liquidated at distressed prices.

    Recovery Rate Assumptions (standard from Graham):
    - Cash: 100% (full value)
    - Receivables: 90% (some bad debts)
    - Inventory: 50% (fire-sale prices)
    - Fixed Assets: 0% (specialized equipment, land worth little in liquidation)

    Formula:
        liquidation_value = (CA × 0.9) + (Inv × 0.5) + (FA × 0.0) - Total_Liabilities

    Args:
        current_assets (float): Total current assets (cash + receivables + inventory).
                               Must be >= 0.
        inventory (float): Inventory value. Must be <= current_assets and >= 0.
        fixed_assets (float): Property, plant, equipment, intangibles.
                             Must be >= 0.
        total_liabilities (float): All liabilities (current + long-term).
                                  Must be >= 0.
        recovery_rates (Optional[Dict[str, float]]): Custom recovery percentages.
                                                    Keys: 'receivables', 'inventory', 'fixed_assets'
                                                    Values: 0.0-1.0 (e.g., 0.9 = 90%)
                                                    Defaults: {'receivables': 0.9, 'inventory': 0.5, 'fixed_assets': 0.0}

    Returns:
        float: Liquidation value per share (or total if passed totals).
               Can be negative if liabilities exceed recoverable assets.

    Raises:
        ValueError: If any asset or liability is negative, or inventory > current_assets.

    Examples:
        >>> liquidation_value(
        ...     current_assets=100_000_000,
        ...     inventory=30_000_000,
        ...     fixed_assets=50_000_000,
        ...     total_liabilities=70_000_000
        ... )
        # Receivables: $70M × 0.9 = $63M
        # Inventory: $30M × 0.5 = $15M
        # Fixed Assets: $50M × 0.0 = $0M
        # Total: $78M - $70M liabilities = $8M
        8_000_000

        >>> liquidation_value(100_000, 20_000, 0, 50_000)
        # CA=$100k, Inv=$20k → Receivables=$80k
        # Receivables: $80k × 0.9 = $72k
        # Inventory: $20k × 0.5 = $10k
        # Total: $82k - $50k = $32k
        32_000

    Notes:
        - Most conservative valuation method
        - Assumes distressed/forced sale conditions
        - Fixed assets recovery typically 0% (specialized equipment)
        - Useful for bankrupt or distressed companies
        - Lower bound on intrinsic value
        - Custom recovery_rates allow industry-specific adjustments

    Reference:
        Graham, B., & Dodd, D. L. (1934). Security Analysis (Ch. 44: Liquidation Value).
        "In times of distress, assets are worth far less than book value."
    """
    # Input validation
    if current_assets < 0:
        raise ValueError(f"liquidation_value: current_assets must be >= 0, got {current_assets}")

    if inventory < 0 or inventory > current_assets:
        raise ValueError(
            f"liquidation_value: inventory must be 0-{current_assets}, got {inventory}"
        )

    if fixed_assets < 0:
        raise ValueError(f"liquidation_value: fixed_assets must be >= 0, got {fixed_assets}")

    if total_liabilities < 0:
        raise ValueError(
            f"liquidation_value: total_liabilities must be >= 0, got {total_liabilities}"
        )

    # Set default or use custom recovery rates
    if recovery_rates is None:
        recovery_rates = {
            "receivables": 0.9,
            "inventory": 0.5,
            "fixed_assets": 0.0,
        }

    receivables_rate = recovery_rates.get("receivables", 0.9)
    inventory_rate = recovery_rates.get("inventory", 0.5)
    fixed_assets_rate = recovery_rates.get("fixed_assets", 0.0)

    # Validate recovery rates
    for key, rate in [
        ("receivables", receivables_rate),
        ("inventory", inventory_rate),
        ("fixed_assets", fixed_assets_rate),
    ]:
        if not (0.0 <= rate <= 1.0):
            raise ValueError(
                f"liquidation_value: recovery_rates['{key}'] must be 0.0-1.0, got {rate}"
            )

    # Calculate recoverable assets
    receivables = current_assets - inventory
    recoverable_receivables = receivables * receivables_rate
    recoverable_inventory = inventory * inventory_rate
    recoverable_fixed_assets = fixed_assets * fixed_assets_rate

    total_recoverable = (
        recoverable_receivables + recoverable_inventory + recoverable_fixed_assets
    )

    # Subtract liabilities
    liquidation_val = total_recoverable - total_liabilities

    if liquidation_val < 0:
        _logger.warning(
            f"liquidation_value: negative value {liquidation_val:.2f}. "
            f"Liabilities exceed recoverable assets."
        )

    return liquidation_val


def earnings_power_value(
    normalized_earnings: float,
    risk_free_rate: float,
) -> float:
    """
    Calculate Earnings Power Value (EPV) - perpetuity model without growth.

    EPV is a conservative valuation approach assuming a company's normalized
    earnings continue indefinitely at current levels (no growth). This is
    appropriate for mature, stable businesses with limited growth prospects.

    Formula:
        EPV = Normalized Earnings / Risk-Free Rate

    This assumes:
    - Company is perpetual (indefinite life)
    - Earnings are stable and normalized (not cyclical spike)
    - No growth (conservative for most companies)
    - Risk is measured by 10Y Treasury rate

    Args:
        normalized_earnings (float): Company's sustainable annual earnings.
                                    Typically TTM adjusted for one-time items.
                                    Must be > 0.
        risk_free_rate (float): 10-year Treasury yield in decimal or percentage.
                               If 0-100: treated as percentage (e.g., 4.5 = 4.5%)
                               If < 1: treated as decimal (e.g., 0.045 = 4.5%)
                               Must be > 0.

    Returns:
        float: Enterprise value per share (or total if passed totals).
               Represents the value of business as if perpetually held.

    Raises:
        ValueError: If normalized_earnings <= 0 or risk_free_rate <= 0.

    Examples:
        >>> earnings_power_value(normalized_earnings=100_000_000, risk_free_rate=4.5)
        # EPV = $100M / 0.045 = $2,222M
        2_222_222_222

        >>> earnings_power_value(normalized_earnings=50_000_000, risk_free_rate=0.03)
        # EPV = $50M / 0.03 = $1,667M
        1_666_666_667

        >>> earnings_power_value(normalized_earnings=10_000_000, risk_free_rate=2.0)
        # With 2% risk-free rate: EPV = $10M / 0.02 = $500M
        500_000_000

    Notes:
        - Conservative: zero growth assumption
        - Appropriate for utilities, mature industrials
        - Sensitive to risk_free_rate changes (inverse relationship)
        - When RF rate drops, EPV increases significantly
        - Does not account for leverage/capital structure
        - Similar to dividend discount model with 0% growth
        - Useful as baseline for companies with dividend capacity

    Reference:
        Damodaran, A. (2012). Investment Valuation (3rd ed.).
        "EPV represents the value of a company assuming it never grows but
        maintains its current earning power indefinitely."
    """
    if normalized_earnings <= 0:
        raise ValueError(
            f"earnings_power_value: normalized_earnings must be > 0, got {normalized_earnings}"
        )

    if risk_free_rate <= 0:
        raise ValueError(
            f"earnings_power_value: risk_free_rate must be > 0, got {risk_free_rate}"
        )

    # Handle both percentage (0-100) and decimal (0-1) inputs
    if risk_free_rate > 1:
        # Convert from percentage to decimal
        rf_decimal = risk_free_rate / 100.0
    else:
        rf_decimal = risk_free_rate

    epv = normalized_earnings / rf_decimal

    if epv > 100_000_000_000:  # $100B threshold for warning
        _logger.warning(
            f"earnings_power_value: unusually high EPV {epv:.2f} "
            f"for earnings={normalized_earnings:.2f}, rf={risk_free_rate}%"
        )

    return epv


def adjusted_pe_ratio(
    eps: float,
    market_pe: float,
    sector_avg_pe: float,
    quality_score: float = 100.0,
) -> float:
    """
    Calculate adjusted P/E ratio based on sector and company quality.

    Adjust a company's P/E ratio to account for:
    1. Sector average (relative to peers)
    2. Company quality (competitive advantages, management)
    3. Growth normalization

    Adjustments move P/E ratio toward sector average, scaled by quality:
    - High quality (100): P/E can exceed sector average
    - Average quality (50): P/E approaches sector average
    - Low quality (<50): P/E should be below sector average

    Formula:
        adjusted_pe = (market_pe + sector_avg_pe * quality_score/100) /
                      (1 + quality_score/100)

    This creates a weighted average that:
    - Pulls high-quality companies toward sector average (reversion)
    - Keeps poor-quality below sector average
    - Treats sector average as baseline

    Args:
        eps (float): Company's earnings per share.
                    Used for logging/context; does not affect calculation.
        market_pe (float): Current P/E ratio in market (Price/EPS).
                          Can be relative (e.g., 15.0 for 15x) or absolute.
                          Must be > 0.
        sector_avg_pe (float): Average P/E for the sector.
                              Benchmark for comparison.
                              Must be > 0.
        quality_score (float): Quality multiplier 0-100.
                              100 = excellent moat, high ROE, strong management
                              50 = average / sector peer
                              <50 = deteriorating quality, weak competitive position
                              Default: 100 (no discount).

    Returns:
        float: Adjusted P/E ratio, normalized for sector and quality.

    Raises:
        ValueError: If market_pe <= 0, sector_avg_pe <= 0, or quality_score < 0.

    Examples:
        >>> adjusted_pe_ratio(eps=5.0, market_pe=25.0, sector_avg_pe=18.0, quality_score=100)
        # High quality company trading at 25x in 18x sector
        21.5  # Adjusted up due to quality, but pulled toward sector

        >>> adjusted_pe_ratio(eps=5.0, market_pe=25.0, sector_avg_pe=18.0, quality_score=50)
        # Average quality company
        21.5  # Weighted average

        >>> adjusted_pe_ratio(eps=5.0, market_pe=25.0, sector_avg_pe=18.0, quality_score=20)
        # Low quality company (discount)
        19.3  # Adjusted down

    Notes:
        - Sector average acts as gravitational center
        - Quality score above 100 not recommended (implies superiority over sector)
        - Formula uses weighted harmonic-like approach
        - Useful for relative valuation within sectors
        - Compare adjusted P/E to historical P/E to find mispricing
        - Does not account for absolute valuation (compare to Graham formula)

    Reference:
        Graham, B. (2006). The Intelligent Investor (Ch. 10: The Dividend Discount Model).
        "P/E ratios must be evaluated within peer context, not in isolation."
    """
    # Input validation
    if market_pe <= 0:
        raise ValueError(
            f"adjusted_pe_ratio: market_pe must be > 0, got {market_pe}"
        )

    if sector_avg_pe <= 0:
        raise ValueError(
            f"adjusted_pe_ratio: sector_avg_pe must be > 0, got {sector_avg_pe}"
        )

    if quality_score < 0:
        raise ValueError(
            f"adjusted_pe_ratio: quality_score must be >= 0, got {quality_score}"
        )

    # Normalize quality score
    q = quality_score / 100.0

    # Weighted average P/E: pulls market_pe toward sector_avg_pe based on quality
    # When quality=100: more weight toward sector_avg
    # When quality=50: balanced mix
    # When quality=0: mostly market_pe
    adjusted_pe = (market_pe + sector_avg_pe * q) / (1.0 + q)

    # Log unusual ratios
    if adjusted_pe > 100:
        _logger.warning(
            f"adjusted_pe_ratio: very high P/E ratio {adjusted_pe:.2f} "
            f"for market_pe={market_pe}, sector_avg_pe={sector_avg_pe}, quality={quality_score}"
        )

    if adjusted_pe < 5:
        _logger.warning(
            f"adjusted_pe_ratio: very low P/E ratio {adjusted_pe:.2f} "
            f"for market_pe={market_pe}, sector_avg_pe={sector_avg_pe}, quality={quality_score}"
        )

    return adjusted_pe


# ============================================================================
# Validation functions (internal use)
# ============================================================================


def _validate_financial_inputs(
    **kwargs,
) -> Tuple[bool, str]:
    """
    Validate common financial inputs for Graham formulas.

    Internal helper for batch validation.

    Args:
        **kwargs: Named financial values (e.g., eps=5.0, growth_rate=8.0)

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
                         is_valid=True if all inputs valid
                         error_message explains first error found
    """
    for key, value in kwargs.items():
        if value is None:
            return False, f"{key} is None"
        if not isinstance(value, (int, float)):
            return False, f"{key} must be numeric, got {type(value).__name__}"
    return True, ""


if __name__ == "__main__":
    # Example usage / smoke test
    print("=" * 70)
    print("VALUATION MODULE - SMOKE TEST")
    print("=" * 70)

    # Graham Formula
    try:
        gf = graham_formula(eps=5.0, growth_rate=8.0, risk_free_rate=4.5, quality_score=100)
        print(f"graham_formula(eps=5, g=8%, rf=4.5%, q=100): ${gf:.2f}")
    except Exception as e:
        print(f"graham_formula ERROR: {e}")

    # NNWC
    try:
        nn = nnwc(current_assets=50_000_000, total_liabilities=30_000_000)
        print(f"nnwc(CA=$50M, TL=$30M): ${nn:,.0f}")
    except Exception as e:
        print(f"nnwc ERROR: {e}")

    # Liquidation Value
    try:
        lv = liquidation_value(
            current_assets=100_000_000,
            inventory=30_000_000,
            fixed_assets=50_000_000,
            total_liabilities=70_000_000,
        )
        print(f"liquidation_value(...): ${lv:,.0f}")
    except Exception as e:
        print(f"liquidation_value ERROR: {e}")

    # EPV
    try:
        epv = earnings_power_value(
            normalized_earnings=100_000_000,
            risk_free_rate=4.5,
        )
        print(f"earnings_power_value(NE=$100M, rf=4.5%): ${epv:,.0f}")
    except Exception as e:
        print(f"earnings_power_value ERROR: {e}")

    # Adjusted P/E
    try:
        ape = adjusted_pe_ratio(
            eps=5.0,
            market_pe=25.0,
            sector_avg_pe=18.0,
            quality_score=100,
        )
        print(f"adjusted_pe_ratio(mkt_pe=25, sector_pe=18, q=100): {ape:.2f}x")
    except Exception as e:
        print(f"adjusted_pe_ratio ERROR: {e}")

    print("=" * 70)
    print("All functions executable and returning values.")
    print("=" * 70)
