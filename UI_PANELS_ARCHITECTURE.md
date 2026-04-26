# UI Panels Architecture

## Overview
Three main UI panels implementing Phase 3 of Quantum Investment Terminal:
- **DashboardPanel**: Portfolio KPIs and performance metrics
- **WatchlistPanel**: Live stock data with real-time updates
- **AnalyzerPanel**: Comprehensive Graham-Dodd analysis (7 tabs)

All panels follow clean architecture: UI layer calls application layer (not implemented yet), which orchestrates domain and infrastructure.

---

## 1. DashboardPanel (363 lines)

### Layout
```
┌─────────────────────────────────────────────────────┐
│ Title: "Portfolio Dashboard"    [Period Buttons]    │
│ [1D] [1W] [1M] [3M] [YTD] [1Y] [All] [Refresh]     │
├─────────────────────────────────────────────────────┤
│ Row 1: KPI Cards (6 metrics)                        │
│ ┌──────────┬──────────┬──────────┬──────────┬──────┐
│ │Total Val │P&L ($)   │P&L (%)   │Sharpe   │Sortino
│ │$1.23M    │+12.3K    │+1.5%     │1.45     │2.10  │
│ └──────────┴──────────┴──────────┴──────────┴──────┘
│
│ Row 2: Advanced Metrics (4 metrics)                 │
│ ┌──────────┬──────────┬──────────┬──────────┐
│ │Max DD    │Beta      │Quality   │Corr SPY │
│ │-8.5%     │0.95      │75.5/100  │0.82     │
│ └──────────┴──────────┴──────────┴──────────┘
│
│ Row 3: Sector Heatmap                              │
│ ┌─────────────────────────────────────────────┐
│ │ Technology     Financials     Healthcare    │
│ │ [28.4% ↑2.1%]  [22.7% ↑1.5%]  [20.3% ↑0.8%] │
│ │ Industrials    Consumer       Energy        │
│ │ [14.6% ↓0.3%]  [7.7% ↑3.2%]   [4.9% ↓1.2%] │
│ └─────────────────────────────────────────────┘
│
│ Row 4: Equity Curve (Animated)                     │
│ ┌─────────────────────────────────────────────┐
│ │  1.5M ├─────────────────────────────────┤  │
│ │       │        /─────────────────────\  │  │
│ │  1.2M │───────/                       \─┤  │
│ │       │ Drawdown: -8.5% at 2024-02    │  │
│ └─────────────────────────────────────────────┘
└─────────────────────────────────────────────────────┘
```

### Key Methods
- `load_portfolio_data(period)`: Fetch portfolio metrics from infrastructure
- `update_metrics()`: Update all KPI card values
- `refresh_equity_curve(dates, values)`: Update equity curve chart
- `start_auto_refresh(interval)`: Enable 60-second auto-refresh
- `_on_sector_clicked(sector)`: Handle sector heatmap click → emit signal

### Signals
- `sector_clicked(str)`: Emitted when user clicks on sector
- `refresh_requested()`: Emitted on manual refresh

### Mock Data
- Portfolio value: $1.23M with daily P&L
- All metrics pre-calculated
- Sector allocation with daily changes
- Equity curve spanning 4 months

---

## 2. WatchlistPanel (574 lines)

### Layout
```
┌──────────────────────────────────────────────────────┐
│ "Watchlist"  ● Live   [4 tickers]   [Auto-update ON] │
├──────────────────────────────────────────────────────┤
│ Search: [AAPL_____________]  [+ Add]                 │
│ Filter: [All] [Tech] [Finance] [Healthcare]          │
├──────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────┐
│ │ Ticker │ Price  │ Δ %   │ Quality│ MoS% │ P/E │ IV │
│ ├────────────────────────────────────────────────────┤
│ │ AAPL   │ $195.42│ +2.34%│   85   │ 18% │28.5│$220│
│ │ MSFT   │ $417.89│ +1.12%│   82   │ 12% │32.1│$480│
│ │ GOOGL  │ $156.23│ -0.89%│   78   │ 8%  │24.5│$180│
│ │ AMZN   │ $184.15│ +3.21%│   76   │ 15% │52.3│$210│
│ └────────────────────────────────────────────────────┘
│ [Watchlist] [Technical] [Dividends] [Fundamentals]   │
│ Last update: 14:32:45  [Refresh Now]                │
└──────────────────────────────────────────────────────┘
```

### Key Methods
- `add_ticker(ticker)`: Add to watchlist, emit signal
- `remove_ticker(ticker)`: Remove from watchlist, emit signal
- `batch_update()`: Fetch all tickers every 60 seconds
- `start_batch_updates(interval)`: Enable auto-update timer
- `_on_table_context_menu(position)`: Right-click → Analyze/Alert/Remove
- `_on_table_double_clicked(index)`: Open analyzer for ticker

### Context Menu
- **Analyze**: Open AnalyzerPanel with ticker
- **Add Price Alert**: Emit alert_requested signal
- **Remove**: Remove ticker from watchlist

### Signals
- `ticker_double_clicked(str)`: Open analyzer
- `ticker_added(str)`: Ticker added
- `ticker_removed(str)`: Ticker removed
- `alert_requested(str)`: User wants to add alert

### Batch Update Strategy
- Fetch quotes every 60 seconds
- Update table rows in-place (no reload)
- WebSocket-ready for real-time updates (Phase 4)
- Fallback chain: Finnhub → yfinance → Tiingo

---

## 3. AnalyzerPanel (816 lines)

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Title: "Company Analyzer"    Ticker: [AAPL____] [Load]          │
├─────────────────────────────────────────────────────────────────┤
│ TABS:                                                 SIDEBAR:   │
│ [Screening] [Income] [Margins] [Balance] [Hist] [Comp] [Val]   │
│                                                                  │
│ Tab Content Area                          │ Price Chart        │
│ ┌────────────────────────────────────┐   │ ┌──────────────┐   │
│ │ Screening (10 Quality Semaphores)  │   │ │ TradingView  │   │
│ │ ● ● ● ● ●   ● ● ● ● ●             │   │ │ Chart        │   │
│ │ CR QR D/E OCF ROE  ROIC EPS D/E IC │   │ │              │   │
│ │ ✓  ✓  ✓  ✓  ✓    ✓  ✓  ✓  ✓  ✓   │   │ └──────────────┘   │
│ │                                    │   │                    │
│ │ Or:                                │   │ AI Thesis Panel   │
│ │ Income Statement (10-year history) │   │ [Generate] ────┐  │
│ │ ┌─────────────────────────────────┐│   │ ┌────────────┐│  │
│ │ │ Manipulation Detection:         ││   │ │ Thesis:    ││  │
│ │ │ ✓ OCF/NI Divergence             ││   │ │ Apple has  ││  │
│ │ │ ✓ D&A/CapEx Ratio               ││   │ │ strong     ││  │
│ │ │ ✓ Hidden Liabilities            ││   │ │ moat...    ││  │
│ │ │ ✓ Revenue Recognition           ││   │ │            ││  │
│ │ │ ✓ Working Capital               ││   │ └────────────┘│  │
│ │ └─────────────────────────────────┘│   │                    │
│ │                                    │   │ AI Chat            │
│ │ Income Table (Revenue, EPS, OCF)  │   │ ┌────────────────┐ │
│ │ ┌─────────────────────────────────┐│   │ User: Why...   │ │
│ │ │ Year │ Revenue │ EPS │ OCF      ││   │ Claude: Based..│ │
│ │ │ 2023 │ 383.3B  │6.05 │121.1B    ││   │ └────────────────┘ │
│ │ │ 2022 │ 394.3B  │5.61 │122.2B    ││   └────────────────────┘
│ │ └─────────────────────────────────┘│
│ └────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Tab 1: Screening (Quality Semaphores)
**10 factors with color indicators (Green ✓ / Red ✗)**

1. Current Ratio (> 1.5)
2. Quick Ratio (> 1.0)
3. D/E Ratio (< 0.5)
4. OCF/NI (> 0.8)
5. ROE (> 15%)
6. ROIC (> WACC)
7. EPS Growth (5-15% CAGR)
8. Debt/EBITDA (< 2.5x)
9. Interest Coverage (> 3.0x)
10. D&A/CapEx (< 0.8)

### Tab 2: Income Statement
**Manipulation Detection (from Security Analysis ch. 31-33)**

1. OCF/NI Divergence
2. D&A/CapEx Ratio
3. Hidden Liabilities
4. Revenue Recognition
5. Working Capital Anomalies

**10-Year History Table**: Year, Revenue, EBITDA, EPS, OCF, OCF/NI, D&A/CapEx

### Tab 3: Margins
**Trend Analysis with 10-year history**

- Gross Margin %
- Operating Margin %
- Net Margin %
- vs Sector Average
- YoY Change %

### Tab 4: Balance Sheet
**NNWC & Liquidation Analysis**

NNWC (Net-Net Working Capital):
- Current Assets - Total Liabilities
- Per share calculation
- Compared to current price

Debt Maturity Ladder:
- Year by year schedule
- Interest rates
- Status (Active/Refinanced)

Liquidity Ratios:
- Current Ratio
- Quick Ratio
- Working Capital

### Tab 5: Historical
**Recession Performance & Management**

- Last 3 downturns: performance vs SPY
- Management changes: dates, events, notes
- ROE/ROA/ROIC 10-year trend

### Tab 6: Comparables
**5-Peer Benchmarking**

Columns: Company, P/E, P/B, ROE, D/E, Dividend %, EPS Growth, Rating

Shows outliers and valuation vs peers.

### Tab 7: Valuation (Main)
**Graham-Dodd Intrinsic Value**

Components:
- EPS (normalized)
- Growth Rate (%)
- Risk-Free Rate (%)
- Beta
- **Intrinsic Value**: $220.50
- **Current Price**: $195.42
- **Margin of Safety**: 12.8%
- **Decision**: BUY

Alternative Methods:
- P/E Adjusted
- Earnings Power Value (EPV)
- Comparable valuation

### Sidebar
**Right 30% of panel**

1. **TradingView Chart Embed** (QWebEngineView)
   - 1D, 1W, 1M, 3M, 1Y, 5Y views
   - Technical indicators

2. **AI Thesis Panel**
   - [Generate Thesis] button
   - Async call to ai_gateway
   - Displays thesis summary (Groq/DeepSeek)

3. **AI Chat Widget**
   - Ask questions about company
   - Multi-turn conversation
   - Context-aware responses

### Key Methods
- `load_company(ticker)`: Load all data and run analyses
- `update_all_tabs()`: Populate all 7 tabs with data
- `_update_screening_tab()`: Color semaphores green/red
- `_update_income_statement_tab()`: Populate tables
- `_update_valuation_tab()`: Graham formula + IV display
- `_on_generate_thesis()`: Call AI gateway asynchronously

### Signals
- `company_loaded(str)`: Company data loaded
- `analysis_complete(str)`: Analysis finished
- `ai_thesis_generated(str, str)`: Thesis ready (ticker, text)

### Mock Data
- Apple Inc. (AAPL) with complete financials
- 10-year history
- 5 peer companies
- Graham IV: $220.50 vs Price: $195.42
- Quality Score: 85/100

---

## Integration Flow

### Data Flow
```
User Input
    ↓
Panel (UI Layer)
    ↓
Application Layer (not yet implemented)
    ↓
Infrastructure Layer (adapters: Finnhub, FMP, etc.)
    ↓
Domain Layer (Graham formulas, risk scoring)
    ↓
Mock Data (MVP fallback)
```

### Event Flow (PyQt6 Signals/Slots)
```
User clicks "Analyze" in Watchlist
    ↓
ticker_double_clicked("AAPL") signal
    ↓
MainWindow receives signal
    ↓
MainWindow.set_analyzer_ticker("AAPL")
    ↓
AnalyzerPanel.load_company("AAPL")
    ↓
company_loaded("AAPL") signal
```

---

## Code Quality Standards

### Error Handling
- ✓ No bare `except:`
- ✓ Specific exceptions with logging
- ✓ Graceful degradation (mock data fallback)
- ✓ User-friendly error messages

### Performance
- ✓ Batch fetching (watchlist 60-second intervals)
- ✓ Timer-based refresh (non-blocking UI)
- ✓ Caching with TTL (ready for Phase 2)
- ✓ Rate limiting framework (ready)
- ✓ WebSocket support (ready for Phase 4)

### Testing
- ✓ 160+ test cases
- ✓ Mock data generators
- ✓ Signal/slot verification
- ✓ Error handling tests
- ✓ Integration workflow tests

### Architecture
- ✓ Clean layer separation (no business logic in UI)
- ✓ Signal/slot pattern (loose coupling)
- ✓ Async-ready (infrastructure calls marked for await)
- ✓ Fallback chains (adapters priority order)
- ✓ Comprehensive docstrings (phase annotations)

---

## Deployment Checklist

- [x] 3 main panels created (1,753 lines)
- [x] 3 test files created (1,007 lines)
- [x] Mock data generators
- [x] Signal/slot connections
- [x] Error handling and logging
- [ ] main_window.py (Phase 3)
- [ ] bloomberg_dark.qss stylesheet (Phase 3)
- [ ] Infrastructure adapters (Phase 2)
- [ ] Application layer use cases (Phase 2)
- [ ] Database setup (Phase 1 complete)

---

## Next Phases

**Phase 3 (UI Complete)**
1. Create main_window.py linking 3 panels
2. Implement dark theme stylesheet
3. Add menu bar and status bar

**Phase 2 (Infrastructure)**
1. Market data adapters (Finnhub, yfinance, FMP)
2. AI backends (Groq, DeepSeek, Qwen)
3. Application layer use cases
4. Rate limiting and caching

**Phase 4+ (Features)**
1. Trading journal
2. Portfolio management
3. Alerts and notifications
4. Backtesting engine
5. Research integration

---

**Created**: 2026-04-25  
**Total LOC**: 2,760 (panels + tests)  
**Status**: Ready for integration  
**Phase**: 3 - UI Skeleton Implementation
