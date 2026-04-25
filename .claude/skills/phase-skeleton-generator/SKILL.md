---
name: phase-skeleton-generator
description: |
  Generate complete Phase scaffolding for Quantum Investment Terminal (Phase 1-7).
  Creates all directories, Python modules, tests, and __init__.py files for a given phase.
  Use whenever starting a new development phase or when you need to scaffold Phase 1-7 modules.
  Input: phase number (1-7). Output: complete directory structure with skeleton files ready for implementation.
---

# Phase Skeleton Generator

Generate complete scaffolding for Quantum Investment Terminal development phases 1-7. Creates full directory tree with Python modules, tests, and `__init__.py` in every package.

## When to use

- Starting Phase 1, 2, 3... (weekly cycle)
- Need full scaffolding for a phase
- Reference: what modules should Phase X have?

## Quick command

```
Generate Phase 1 scaffolding for quantum_terminal/
```

## Output (Phase 1 example)

```
quantum_terminal/
├── domain/
│   ├── models.py (Portfolio, Trade, Company, Thesis dataclasses)
│   ├── valuation.py (Graham Formula, NNWC, EPV)
│   ├── risk.py (Quality 0-100, manipulation detection)
│   ├── screener_rules.py (Filter predicates)
│   └── __init__.py
├── infrastructure/db/
│   ├── database.py (SQLite setup)
│   ├── migrations/
│   └── __init__.py
├── utils/
│   ├── logger.py (loguru)
│   ├── cache.py (diskcache + TTL)
│   ├── rate_limiter.py (token bucket)
│   └── __init__.py
└── tests/
    ├── test_valuation.py
    ├── test_risk.py
    └── __init__.py
```

## Phases 1-7

**Phase 1 (Weeks 1-2)**: domain/, utils/, infrastructure/db/  
**Phase 2 (Weeks 3-4)**: infrastructure/market_data/, ai/, macro/, sentiment/  
**Phase 3 (Week 5)**: ui/main_window, widgets/, dialogs/, styles/  
**Phase 4 (Weeks 6-8)**: ui/panels/ (dashboard, watchlist, analyzer, macro)  
**Phase 5 (Weeks 9-10)**: ui/panels/ (journal, thesis)  
**Phase 6 (Weeks 11-12)**: ui/panels/ (screener, pdf, earnings, monitor)  
**Phase 7 (Weeks 13-14)**: infrastructure/ml/, backtesting, advanced features
