# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Quick Orientation

**What is this?** Bloomberg-like desktop investment terminal with Graham-Dodd value investing methodology. Built with PyQt6, multi-LLM AI (Groq/DeepSeek/Qwen), and professional trading journal.

**Status**: Phase 1 (Foundation) — scaffolding complete, domain layer ready to implement.

**Architecture**: Clean layers — domain (pure logic) → infrastructure (I/O) → application (use cases) → ui (PyQt6).

**Key files to read first**:
- `PLAN_MAESTRO.md` — Full architecture, 80+ dependencies, 7-phase timeline, 12 modules
- `README.md` — Quick start, tech stack overview
- `PROJECT_SCAFFOLD_SUMMARY.md` — What was created, verification checklist
- Memory files (`.claude/projects/.../memory/`) — Development practices, API strategy, why each technology choice

---

## Essential Commands

### Setup (Run First)
```bash
# Install all 80+ dependencies (takes 2-3 min)
uv sync

# Copy and configure API keys
cp .env.template .env
# Edit .env with GROQ_API_KEY, FRED_API_KEY minimum

# Verify setup
python scripts/project_orchestrator.py --status
python scripts/dep_checker.py --verbose
```

### Development Workflow

**Generate Phase skeleton**:
```bash
# Phase 1: Domain layer (valuation, risk, models, database)
python scripts/phase_generator.py --phase 1

# Phase 2: All adapters (market data, macro, AI, sentiment)
python scripts/phase_generator.py --phase 2

# Phase 3+: UI and modules
python scripts/phase_generator.py --phase 3
```

**Testing** (always run before committing):
```bash
# Test domain layer (pure logic, no I/O)
pytest domain/ -v

# Test infrastructure adapters
pytest infrastructure/ -v

# Test specific function
pytest tests/test_valuation.py::TestGrahamFormula -v

# Run with coverage
pytest --cov=quantum_terminal domain/
```

**Code Quality**:
```bash
# Format code
black quantum_terminal/ tests/

# Lint (catch style issues)
ruff check quantum_terminal/

# Type checking
mypy quantum_terminal/

# All together (before commit)
black . && ruff check . && mypy quantum_terminal/ && pytest domain/ -v
```

**Database**:
```bash
# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description"

# View schema
sqlite3 investment_data.db ".schema"
```

**Run the app** (Phase 3+):
```bash
# Launch PyQt6 window
python main.py
```

**Project orchestrator** (master command):
```bash
python scripts/project_orchestrator.py --status      # Show state
python scripts/project_orchestrator.py --generate 1  # Gen Phase 1
python scripts/project_orchestrator.py --test domain # Run tests
python scripts/project_orchestrator.py --modules     # List modules
python scripts/project_orchestrator.py --plan        # Show roadmap
```

---

## Architecture Overview

### Clean Architecture (4 Layers)

```
┌─────────────────────────────────────────┐
│            UI (PyQt6)                   │  Thin layer: widgets, dialogs, events
├─────────────────────────────────────────┤
│         Application Layer               │  Use cases: orchestrate domain + infra
├─────────────────────────────────────────┤
│       Infrastructure (I/O)              │  APIs, database, ML models, file I/O
├─────────────────────────────────────────┤
│     Domain (Pure Logic)                 │  Graham formulas, risk scoring, validation
└─────────────────────────────────────────┘
```

**Why this split**:
- Domain is fully testable (no I/O, just math)
- Adapters are swappable (yfinance → Tiingo seamlessly)
- UI is thin (no business logic in PyQt6)
- Changes in one layer don't cascade

### File Structure by Purpose

```
quantum_terminal/
├── domain/              ← Graham-Dodd logic: valuation, risk, thesis scoring
├── infrastructure/      ← APIs, database, ML models (adapters for each source)
│   ├── market_data/     ← finnhub, yfinance, fmp, tiingo, alphavantage (fallback chain)
│   ├── macro/           ← FRED, EIA, SEC XBRL
│   ├── ai/              ← ai_gateway, groq, deepseek, qwen, openrouter, hf backends
│   ├── sentiment/       ← newsapi, finbert, reddit, finra sentiment
│   ├── ml/              ← lightgbm (scoring), prophet (forecasting), lstm (signals)
│   ├── pdf/             ← pdfplumber, vision API
│   └── db/              ← SQLite, SQLAlchemy ORM, Alembic migrations
├── application/         ← Use cases that combine domain + infrastructure
│   ├── market/          ← get_quote, get_fundamentals, run_screener, run_backtest
│   ├── portfolio/       ← add_trade, get_summary, calculate_risk
│   ├── ai/              ← generate_thesis, analyze_sentiment, chat
│   ├── trading/         ← log_trade, evaluate_adherence, postmortem
│   ├── thesis/          ← create_thesis, find_similar (RAG), score
│   ├── pdf/             ← ingest_pdf_report
│   └── alerts/          ← set_price_alert, check_alerts
├── ui/                  ← PyQt6 presentation (12 module panels + widgets)
├── utils/               ← Shared: cache, rate_limiter, logger, security
├── scripts/             ← Development agents (phase_generator, orchestrator, dep_checker)
└── tests/               ← Test files (mirror domain/ structure)
```

### API Fallback Chains

When one source fails or rate-limits, automatically try the next:

**Market Data**: Finnhub (live) → yfinance (batch) → Tiingo (clean) → AlphaVantage (slow)  
**Fundamentals**: FMP (processed) → SEC XBRL (raw, authoritative)  
**AI**: Groq (fast) → DeepSeek (reasoning) → Qwen (bulk) → OpenRouter (fallback)  
**Sentiment**: FinBERT (local) → NewsAPI → Reddit  

All coordinated in `infrastructure/market_data/data_provider.py` and `infrastructure/ai/ai_gateway.py`.

---

## Code Rules (Non-Negotiable)

### 1. No Bare Excepts
```python
# ✗ BAD: Bare except hides bugs
except:
    pass

# ✓ GOOD: Specific exception + logging
except ValueError as e:
    logger.error(f"Invalid ticker: {ticker}", exc_info=True)
    return None
```

**Why**: Previous codebase had 235+ bare excepts. They swallow programming errors and make debugging impossible.

### 2. SQLAlchemy ORM Only (No Raw SQL)
```python
# ✓ GOOD: ORM is safe from injection
session.query(Company).filter(Company.ticker == ticker).first()

# ✗ BAD: Raw SQL can be injected
session.execute(f"SELECT * FROM companies WHERE ticker = '{ticker}'")
```

### 3. Respect Clean Architecture Layers
```python
# ✗ BAD: Database query in domain/
def graham_formula(eps, growth, ticker):
    # Don't do this:
    db_session.query(CompanyInfo).filter(...)
    
# ✓ GOOD: Domain is pure logic
def graham_formula(eps, growth, risk_free_rate) -> float:
    return eps * (8.5 + 2*growth) * (4.4 / risk_free_rate)

# ✓ GOOD: Infrastructure fetches data, application orchestrates
fundamentals = await get_fundamentals(ticker)  # infrastructure
iv = graham_formula(fundamentals.eps, ...)      # domain
```

### 4. Rate Limiting (Per-Provider Token Bucket)
When calling external APIs, use rate limiter:
```python
from utils.rate_limiter import RateLimiter

finnhub_limiter = RateLimiter(rate=60, per_minutes=1)
if not finnhub_limiter.allow_request():
    # Fall back to next provider
    return yfinance_fallback(ticker)
```

### 5. Caching with TTL by Data Type
```python
from utils.cache import cache

# Quotes: 1 min (prices change fast)
cache.get_with_ttl("AAPL_quote", fetch_quote_fn, ttl_minutes=1)

# Fundamentals: 1 hour (quarterly updates)
cache.get_with_ttl("AAPL_fundamentals", fetch_fundamentals_fn, ttl_minutes=60)

# Macro: 24 hours (daily releases)
cache.get_with_ttl("DGS10", fetch_fred_fn, ttl_hours=24)
```

### 6. Batch Fetching (Never Per-Ticker Loops)
```python
# ✗ SLOW: 100 tickers = 100 requests
for ticker in ticker_list:
    quote = yfinance.download(ticker)

# ✓ FAST: 100 tickers = 1 request
quotes = yfinance.download(ticker_list)
```

### 7. Multi-LLM Gateway (Never Hardcode Backends)
```python
# ✗ BAD: Tied to single backend
from infrastructure.ai.groq_backend import groq_generate
result = groq_generate(prompt)

# ✓ GOOD: Let gateway pick based on task type
from infrastructure.ai.ai_gateway import ai_gateway
result = ai_gateway.generate(prompt, tipo="fast")  # Groq picks best
```

### 8. Domain-First Testing
Always test domain layer first, before infrastructure/UI:
```bash
# Before ANY UI work, verify domain:
pytest domain/ -v  # All tests pass? Then add infrastructure.

# Domain changes always require test updates:
# Edit domain/valuation.py → update tests/test_valuation.py → pytest domain/
```

---

## Development Workflow by Phase

### Phase 1: Domain Layer (Weeks 1-2)
- Implement `domain/models.py` (dataclasses/Pydantic)
- Implement `domain/valuation.py` (Graham Formula, NNWC, liquidation value, EPV)
- Implement `domain/risk.py` (Quality score 0-100, VaR, manipulation detection)
- Write all tests in `tests/test_*.py`
- Run: `pytest domain/ -v` ✓ All pass before moving on

### Phase 2: Adapters (Weeks 3-4)
- Create `infrastructure/market_data/finnhub_adapter.py`, etc.
- Create `infrastructure/macro/fred_adapter.py`, etc.
- Create `infrastructure/ai/ai_gateway.py` + backends
- Test: `python -m infrastructure.market_data.data_provider AAPL` (< 500ms)
- Verify: `pytest infrastructure/ -v`

### Phase 3: UI Skeleton (Week 5)
- Create `ui/main_window.py` (QMainWindow, 3-column layout)
- Create `ui/widgets/metric_card.py`, `chart_widget.py`, `data_table.py`
- Create `ui/styles/bloomberg_dark.qss` (dark theme)
- Test: `python main.py` (window opens)

### Phase 4+: Modules & Features
- Each module (Dashboard, Watchlist, Analyzer, etc.) combines domain + infrastructure + UI
- Always: domain tests pass first, then infrastructure, then UI

---

## Common Pitfalls

### ✗ Don't
- Use bare `except:` or `except Exception:` (be specific)
- Write raw SQL (use SQLAlchemy ORM)
- Put business logic in UI layer or infrastructure layer
- Call APIs in domain/ (move to infrastructure/)
- Hardcode API keys (use .env + config.py)
- Fetch single ticker per request (batch!)
- Skip domain tests before committing

### ✓ Do
- Log exceptions with context: `logger.error("message", exc_info=True)`
- Use fallback chains (try Finnhub, then yfinance, then Tiingo)
- Respect layer boundaries (domain ← infrastructure ← application → ui)
- Test domain layer first: `pytest domain/ -v`
- Cache with TTL: quotes 1min, fundamentals 1h, macro 24h
- Commit regularly with clear messages: `"✓ Module X: Add Y feature"`

---

## Graham-Dodd Methodology (Core Logic)

This terminal is built around Security Analysis (1934), not ML price prediction.

**Quality Score (0-100)**: 10 factors trained on S&P500 (2010-2024), LightGBM
**Manipulation Detection**: 5 schemes from ch. 31-33 (OCF/NI, D&A/CapEx, hidden charges, etc.)
**Valuation**: Graham Formula, Net-Net Working Capital, Liquidation Value, P/E adjusted

All in `domain/valuation.py` and `domain/risk.py` — pure math, fully testable.

---

## Configuration

### API Keys (.env)
```bash
# Critical (minimum to start)
GROQ_API_KEY=...        # Free: 30 req/min
FRED_API_KEY=...        # Free: 1000 req/day

# Recommended
FINNHUB_API_KEY=...     # Free: 60 req/min (WebSocket)
FMP_API_KEY=...         # Free: 250 req/day (fundamentals)
HF_TOKEN=...            # Free: FinBERT, embeddings

# Optional
DEEPSEEK_API_KEY=...    # Paid (reasoning, optional)
OPENROUTER_API_KEY=...  # Fallback (paid, optional)
```

### Environment (quantum_terminal/config.py)
Uses Pydantic v2 to load and validate `.env`. Access via:
```python
from quantum_terminal.config import settings
print(settings.groq_api_key)
print(settings.project_root)
print(settings.database_path)
```

---

## When Stuck

1. **"How do I add a new data source?"**
   → Create `infrastructure/market_data/new_source_adapter.py`, integrate into `data_provider.py` fallback chain.

2. **"How do I add a new module?"**
   → Create `ui/panels/new_module_panel.py` + `application/*/new_module_usecase.py` + tests.

3. **"How do I test this?"**
   → Domain logic: `pytest domain/ -v`. Infrastructure: `pytest infrastructure/ -v`. UI: `pytest -k "test_widget_name"`.

4. **"Why does the API call fail?"**
   → Check rate limiter (token bucket), cache TTL, or try fallback chain. Look in `infrastructure/market_data/data_provider.py`.

5. **"Where's the master plan?"**
   → `PLAN_MAESTRO.md` (full architecture, 7 phases, 12 modules).

---

## Quick Links

- **Architecture & Plan**: `PLAN_MAESTRO.md`, `README.md`
- **Memory (why choices matter)**: `.claude/projects/.../memory/`
- **Development Agents**: `scripts/phase_generator.py`, `project_orchestrator.py`
- **Graham-Dodd Logic**: `domain/valuation.py`, `domain/risk.py`
- **Fallback Chains**: `infrastructure/market_data/data_provider.py`, `infrastructure/ai/ai_gateway.py`
- **Config**: `quantum_terminal/config.py`, `.env.template`

---

**Last Updated**: 2026-04-25  
**Current Phase**: 1 (Foundation — Domain Layer Ready)  
**Next Step**: `uv sync` → Configure `.env` → `python scripts/phase_generator.py --phase 1` → Implement domain logic
