---
name: domain-layer-scaffolder
description: |
  Create complete domain layer for Quantum Investment Terminal with Graham-Dodd formulas.
  Generates domain/models.py, domain/valuation.py, domain/risk.py with full implementations,
  quality scoring (0-100), manipulation detection, and 30+ test cases.
  Use when starting Phase 1 implementation or adding new domain logic.
  Output: production-ready domain layer (500+ lines code + 300+ lines tests).
---

# Domain Layer Scaffolder

Create production-ready domain layer with Graham-Dodd valuation, quality scoring, and tests.

## What it generates

**domain/models.py** — Pydantic v2 models
- Portfolio, Trade, Company, Thesis, Alert, Quote, Screener
- Full type hints, validation, docstrings

**domain/valuation.py** — Graham-Dodd formulas
- Graham Formula: (EPS × (8.5 + 2g) × 4.4 / 10Y) × quality_adj
- Net-Net Working Capital (NNWC)
- Liquidation Value (conservative asset breakdown)
- Earnings Power Value (EPV - no growth)
- P/E adjusted by sector

**domain/risk.py** — Quality & manipulation detection
- Quality Score 0-100 (10 Graham factors)
- Manipulation Detection (5 red flags from Security Analysis ch. 31-33)
- VaR, Sharpe, Sortino, Beta, Max Drawdown

**tests/test_*.py** — 30+ test cases
- Happy path, edge cases, validation, error handling
- All tests pass before Phase 2

## When to use

- Phase 1 kickoff (create domain foundation)
- Adding new domain modules (thesis_scorer.py, trading_metrics.py)
- Verify formulas match Security Analysis textbook

## Example output (valuation.py)

```python
def graham_formula(eps, growth_rate, risk_free_rate, quality_score=100.0):
    """Graham Formula: (EPS × (8.5 + 2g) × 4.4 / 10Y) × quality"""
    if eps <= 0 or risk_free_rate <= 0:
        raise ValueError("eps and risk_free_rate must be positive")
    
    peg_multiple = 8.5 + (2 * growth_rate * 100)
    normalized = peg_multiple * (4.4 / risk_free_rate)
    intrinsic_value = eps * normalized
    return intrinsic_value * (quality_score / 100.0)

def quality_score(current_ratio, ocf_to_ni, debt_to_equity, ...):
    """Quality 0-100: Graham's 10-factor methodology"""
    score = 0
    if current_ratio > 1.5: score += 10
    if ocf_to_ni > 0.8: score += 10
    # ... 8 more factors
    return min(100, max(0, score))

def detect_manipulation(ocf, ni, depreciation, capex, ...):
    """Detect 5 accounting red flags from Security Analysis"""
    return {
        "ocf_below_ni": ocf < ni,
        "da_exceeds_capex": depreciation > capex,
        "equity_mismatch": ...,
        "high_non_recurring": ...,
        "receivables_creep": ...
    }
```

## Key features

✅ Graham-Dodd formulas from Security Analysis (1934)  
✅ Type hints (Python 3.12)  
✅ Comprehensive docstrings  
✅ Edge case handling  
✅ Ready for pytest domain/ -v  
✅ No I/O — pure math, fully testable
