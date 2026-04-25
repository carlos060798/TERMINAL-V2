# Quantum Investment Terminal

Bloomberg-like desktop investment analysis platform with Graham-Dodd methodology, multi-LLM AI analysis, and professional trading journal.

**Status**: Foundation phase (Phase 1 of 7)

## Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Copy and configure environment variables
cp .env.template .env
# Edit .env with your API keys

# 3. Check project status
python scripts/project_orchestrator.py --status

# 4. Generate Phase 1 skeleton
python scripts/phase_generator.py --phase 1

# 5. Run domain tests
pytest domain/ -v
```

## Project Structure

```
quantum_terminal/
├── domain/              # Pure business logic (no I/O)
├── infrastructure/      # APIs, database, ML models
├── application/         # Use cases (orchestrate domain + infra)
├── ui/                  # PyQt6 user interface
└── utils/               # Shared utilities

scripts/                # Development agents
├── phase_generator.py   # Generate phase scaffolding
├── project_orchestrator.py  # Master orchestration
└── dep_checker.py       # Dependency validation
```

## Development Phases

| Phase | Name | Duration | Key Deliverables |
|-------|------|----------|-----------------|
| 1 | Cimientos | Weeks 1-2 | Config, domain layer, database |
| 2 | Adaptadores | Weeks 3-4 | Market data, macro, AI adapters |
| 3 | Esqueleto UI | Week 5 | PyQt6 window, widgets, layout |
| 4 | Módulos Core | Weeks 6-8 | Dashboard, watchlist, analyzer, macro |
| 5 | Trading & Tesis | Weeks 9-10 | Journal, thesis tracking, risk manager |
| 6 | Screener & Intel | Weeks 11-12 | PDF, earnings, market monitor |
| 7 | ML Avanzado | Weeks 13-14 | Backtesting, forecasting, neural nets |

## Technology Stack

**UI**: PyQt6 | **Data**: yfinance, pandas | **Analysis**: pandas-ta, quantstats | **ML**: scikit-learn, lightgbm, PyTorch | **NLP**: FinBERT, sentence-transformers | **AI**: Groq, DeepSeek, HuggingFace | **DB**: SQLite, SQLAlchemy

All free. Python 3.12+.

## Key Features

### 12 Professional Modules

1. **Dashboard** — Portfolio analytics (VaR, Sharpe, drawdown)
2. **Watchlist** — Real-time holdings with batch updates
3. **Analyzer** — 7-step Graham-Dodd analysis by company
4. **Screener** — Multi-factor with Graham presets
5. **Macro** — FRED economic indicators + yield curve
6. **Trading Journal** — Trade logging + performance stats
7. **Investment Thesis** — Structured thesis tracking + RAG search
8. **PDF Intel** — Extract data from 10-K/earnings, cross-check SEC
9. **Earnings Tracker** — Calendar + consensus estimates
10. **Market Monitor** — Real-time movers + heat map + scanner
11. **Backtest** — vectorbt strategies on historical data
12. **Risk Manager** — VaR, correlation, efficient frontier

### Graham-Dodd Methodology

- **Valuation**: Graham Formula, Net-Net, liquidation value, P/E adjusted
- **Quality Scoring**: 10-dimension scoring (0-100)
- **Manipulation Detection**: OCF/NI, D&A/CapEx, hidden charges, recurrent specials
- **Screener Presets**: Classic, Net-Net, Quality+Value, Dividends, Traps to Avoid

### AI Integration

- **Multi-LLM**: Groq (fast) → DeepSeek (reasoning) → Qwen (bulk) → OpenRouter (fallback)
- **Sentiment**: FinBERT + NewsAPI + Reddit
- **RAG**: Semantic search over thesis history
- **Forecasting**: Prophet for EPS/revenue projections
- **Neural**: LSTM for technical signals, LightGBM for scoring

## Commands

### Project Management

```bash
# Show project status
python scripts/project_orchestrator.py --status

# Generate phase skeleton
python scripts/phase_generator.py --phase 1

# Check all dependencies
python scripts/dep_checker.py --verbose

# List all modules
python scripts/project_orchestrator.py --modules
```

### Testing

```bash
# Test domain layer (always first)
pytest domain/ -v

# Test infrastructure adapters
pytest infrastructure/ -v

# Run specific test
pytest -k "test_valuation" -v

# Test with coverage
pytest --cov=quantum_terminal domain/
```

### Database

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# View schema
sqlite3 investment_data.db ".schema"
```

### Development

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy quantum_terminal/

# Run app (Phase 3+)
python main.py
```

## Configuration

### Environment Variables

Copy `.env.template` to `.env` and configure:

```bash
# IA Backends
GROQ_API_KEY=...
DEEPSEEK_API_KEY=...
OPENROUTER_API_KEY=...
KAMI_IA=...

# Market Data
FINNHUB_API_KEY=...
FMP_API_KEY=...
FRED_API_KEY=...

# ... (see .env.template for all)
```

## Architecture Overview

### Clean Architecture

```
domain/              ← Pure logic, no I/O, fully testable
    ↓
infrastructure/      ← APIs, DB, ML models
    ↓
application/         ← Use cases (orchestrate domain + infra)
    ↓
ui/                  ← PyQt6 widgets (thin layer)
```

### Fallback Chains

**Market Data**: Finnhub → yfinance → Tiingo → Alpha Vantage
**IA**: Groq → DeepSeek → Qwen → OpenRouter → Kami Vision
**Sentiment**: FinBERT (batch) + NewsAPI + Reddit

## Design Principles

1. **Domain is Graham-Dodd** — Every metric from Security Analysis (1934)
2. **No bare exceptions** — Specific catches + logging
3. **No SQL injection** — SQLAlchemy ORM only
4. **API rate limiting** — Token bucket per provider
5. **Caching with TTL** — diskcache by data type
6. **Testing first** — `pytest domain/` before commits

## References

- **Plan**: [Architecture & Development Plan](C:\Users\usuario\.claude\plans\)
- **Graham-Dodd**: Security Analysis chapters 1-52
- **APIs**: See `.env.template` for all providers
- **CLAUDE.md**: [Development guidance for future instances](CLAUDE.md)

## Contributing

1. Read CLAUDE.md
2. Run: `pytest domain/ -v` (must pass)
3. Follow clean architecture layers
4. No hardcoded secrets
5. Write tests before implementation

## License

MIT

## Contact

Carlos Angarita — carlosdaniloangaritagarcia@gmail.com
