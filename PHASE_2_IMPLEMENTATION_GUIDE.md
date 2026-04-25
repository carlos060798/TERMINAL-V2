# PHASE 2 IMPLEMENTATION GUIDE
## Quantum Investment Terminal — Adaptadores (API Adapters)

**Estimated Duration**: 2-4 hours (parallel execution with 6-8 agents)  
**Status**: READY TO START  
**Skills Available**: `api-adapter-factory` (generates 200+ line adapters with tests)

---

## 📋 PHASE 2 OVERVIEW

**Goal**: Create 15+ production-ready API adapters with:
- Rate limiting (token bucket, per-provider limits)
- Caching (diskcache with TTL by data type)
- Error handling (specific exceptions, logging)
- Fallback integration (raises correct exceptions for data_provider.py)
- Batch mode (concurrent requests, 50-100 tickers in 1-2 seconds)
- Async/await (non-blocking, suitable for UI)
- Tests (15+ test cases per adapter)

**Fallback Chain Strategy**:
```
Market Data:   Finnhub (live) → yfinance (batch) → Tiingo (clean) → AlphaVantage (slow)
Fundamentals:  FMP (processed) → SEC XBRL (raw, authoritative)
Macro:         FRED (economic) + EIA (energy)
AI:            Groq (fast) → DeepSeek (reasoning) → Qwen (bulk) → OpenRouter (fallback)
Sentiment:     FinBERT (local) → NewsAPI (realtime) → Reddit (sentiment)
```

---

## 🔧 ADAPTERS TO CREATE (15 Total)

### GROUP 1: Market Data (5 adapters)
**Priority**: CRITICAL (Watchlist, Dashboard, Analyzer depend on these)

#### 1. **finnhub_adapter.py**
```python
# Location: infrastructure/market_data/finnhub_adapter.py
# Rate Limit: 60 requests/minute (free tier)
# WebSocket: YES (real-time quotes)
# Data Provided:
#   - Quote: price, bid/ask, volume, timestamp
#   - Company Profile: name, sector, exchange, logo, website
#   - Earnings Calendar: date, eps_estimate, eps_actual
#   - Analyst Recommendations: target, rating, number_of_analysts

class FinnhubAdapter:
    async def get_quote(ticker: str) -> Dict[str, float]
    async def batch_quotes(tickers: List[str]) -> Dict[str, Dict]
    async def get_company_profile(ticker: str) -> Dict
    async def get_earnings_calendar(from_date: str, to_date: str) -> List[Dict]
    async def get_recommendations(ticker: str) -> Dict

# Test Cases (15+):
# - Normal quote fetch
# - Batch of 10 tickers
# - Rate limit handling
# - Cache hits (quote_1min)
# - Error handling (404, 429, timeout)
# - WebSocket connection
```

#### 2. **yfinance_adapter.py**
```python
# Location: infrastructure/market_data/yfinance_adapter.py
# Rate Limit: ~2000 req/day implicit
# WebSocket: NO (batch only)
# Data Provided:
#   - Historical OHLCV: open, high, low, close, volume
#   - Company Info: sector, industry, market_cap, beta, pe_ratio
#   - Dividends & Splits: historical record
#   - Options: call/put chains

class YfinanceAdapter:
    async def batch_download(tickers: List[str], start: str, end: str) -> pd.DataFrame
    async def get_info(ticker: str) -> Dict
    async def get_dividends(ticker: str) -> Dict
    async def get_options_chain(ticker: str, expiration: str) -> Dict

# Test Cases (15+):
# - Single ticker OHLCV
# - Batch 50 tickers (performance test, should be < 2 sec)
# - Historical range (1 month, 1 year, 5 years)
# - Dividends & splits
# - Options chain parsing
# - Cache hits (fundamentals_1h)
# - Error: ticker not found
# - Error: network timeout
```

#### 3. **fmp_adapter.py**
```python
# Location: infrastructure/market_data/fmp_adapter.py
# Rate Limit: 250 requests/day (free tier)
# Key Advantage: Pre-calculated financial ratios (saves computation)
# Data Provided:
#   - Financial Ratios: PE, PB, ROE, ROA, current ratio, quick ratio
#   - Peer Comparison: vs sector, vs industry
#   - Key Metrics: growth rates, profitability, leverage
#   - Company Profile Enhanced: employees, exchange, dividend yield

class FMPAdapter:
    async def get_ratios(ticker: str) -> Dict  # Historical ratios
    async def get_key_metrics(ticker: str) -> Dict
    async def get_company_profile(ticker: str) -> Dict
    async def get_peers(ticker: str) -> List[str]
    async def batch_profiles(tickers: List[str]) -> Dict

# Test Cases (15+):
# - Single ticker ratios
# - Historical ratios (5-year trend)
# - Peer comparison
# - Key metrics calculation verification
# - Cache hits (fundamentals_1h)
# - Rate limit: 250/day strict
# - Error: quota exceeded
```

#### 4. **tiingo_adapter.py**
```python
# Location: infrastructure/market_data/tiingo_adapter.py
# Rate Limit: 500 requests/day (free tier)
# Key Advantage: Clean, adjusted historical data (splits, dividends handled)
# Data Provided:
#   - Adjusted OHLCV: automatically split/dividend adjusted
#   - Fund & ETF Data: NAV, composition
#   - Corporate Actions: historical record

class TiingoAdapter:
    async def get_historical(ticker: str, start: str, end: str, **kwargs) -> pd.DataFrame
    async def batch_historical(tickers: List[str], start: str, end: str) -> Dict
    async def get_metadata(ticker: str) -> Dict

# Test Cases (15+):
# - Single ticker historical data
# - Data quality check (splits, dividends applied)
# - Batch processing
# - Cache hits (historical_1h)
# - Error: insufficient data
# - Rate limit handling (500/day)
# - Performance: 50 tickers < 2 sec
```

#### 5. **sec_adapter.py** (XBRL Filings)
```python
# Location: infrastructure/macro/sec_adapter.py
# Rate Limit: 0.12s delay per request (10 req/sec max)
# Data Provided:
#   - 10-K: Annual financials (65+ fields per company)
#   - 10-Q: Quarterly financials
#   - 8-K: Current reports (M&A, management changes, etc.)
#   - 4: Insider trades (officer, director, 10%+ holder)
#   - 13F: Institutional holdings

class SECAdapter:
    async def get_cik(ticker: str) -> str  # Get CIK from ticker
    async def get_submissions(cik: str) -> List[Dict]  # List of filings
    async def get_filing(cik: str, accession_number: str) -> Dict
    async def get_facts(cik: str) -> Dict  # XBRL facts (standardized accounting data)
    async def get_form4(ticker: str, from_date: str, to_date: str) -> List[Dict]

# Test Cases (15+):
# - CIK lookup (ticker → CIK)
# - Submissions list (all filings for company)
# - 10-K parsing (extract financial statements)
# - 10-Q parsing
# - Form 4 insider trades
# - XBRL fact lookup
# - Cache hits (company_info_7d)
# - Error: company not found
# - Delay compliance (0.12s between requests)
```

---

### GROUP 2: Macro Data (2 adapters)
**Priority**: HIGH (Dashboard, Macro Context module)

#### 6. **fred_adapter.py**
```python
# Location: infrastructure/macro/fred_adapter.py
# Rate Limit: 1000 requests/day (free tier)
# Critical for Graham Formula: Provides 10Y Treasury yield
# Data Provided:
#   - Key Series:
#     DGS10: 10-Year Treasury Constant Maturity (for Graham formula)
#     DGS2: 2-Year Treasury
#     CPIAUCSL: Consumer Price Index All Urban Consumers
#     UNRATE: Unemployment Rate
#     M2SL: Money Supply (M2)
#     FEDFUNDS: Federal Funds Effective Rate
#     NARUSL: Natural Rate of Unemployment

class FREDAdapter:
    async def get_series(series_id: str, from_date: str, to_date: str) -> Dict
    async def get_latest(series_id: str) -> float  # Most recent value
    async def batch_latest(series_ids: List[str]) -> Dict
    async def get_observations(series_id: str, limit: int = 100) -> List[Dict]

# Test Cases (15+):
# - DGS10 latest (used in real-time Graham formula)
# - Multiple series fetch
# - Historical range (10 years of CPI)
# - Cache hits (macro_24h)
# - Rate limit (1000/day)
# - Error: series not found
# - Performance: 10 series < 500ms
# - Data validation (values in reasonable range)
```

#### 7. **eia_adapter.py**
```python
# Location: infrastructure/macro/eia_adapter.py
# Rate Limit: 120 requests/hour (free tier)
# Data Provided:
#   - Crude Oil WTI: West Texas Intermediate
#   - Crude Oil Brent: North Sea Brent
#   - Henry Hub Natural Gas: $/MMBtu
#   - Petroleum Inventories: strategic reserve, commercial
#   - Refinery Utilization: capacity %

class EIAAdapter:
    async def get_crude_oil_wti(from_date: str, to_date: str) -> Dict
    async def get_crude_oil_brent(from_date: str, to_date: str) -> Dict
    async def get_natural_gas(from_date: str, to_date: str) -> Dict
    async def get_inventories() -> Dict  # Latest weekly
    async def get_refinery_utilization() -> float

# Test Cases (15+):
# - WTI current price
# - Historical range
# - Brent vs WTI spread
# - Inventory levels
# - Cache hits (macro_24h)
# - Error: data not available
# - Rate limit (120/hour)
```

---

### GROUP 3: AI Gateways & Backends (5 adapters)
**Priority**: HIGH (Analyzer module, thesis generation)

#### 8. **ai_gateway.py** (Router/Coordinator)
```python
# Location: infrastructure/ai/ai_gateway.py
# Purpose: Intelligent routing to best backend based on task type
# Data Provided:
#   - Route by tipo (fast, reason, vision, sentiment, bulk, fallback)
#   - Token counting per provider per day
#   - Request queuing (avoid thundering herd)

class AIGateway:
    async def generate(prompt: str, tipo: str = "fast") -> str
    # tipo options:
    #   "fast"      → Groq (lowest latency)
    #   "reason"    → DeepSeek (best reasoning for DCF)
    #   "vision"    → Kami (PDF/image analysis)
    #   "sentiment" → HuggingFace/FinBERT (sentiment batch)
    #   "bulk"      → Qwen (massive processing)
    #   "fallback"  → OpenRouter (last resort)
    
    async def count_tokens(provider: str) -> Dict  # Daily usage
    async def estimate_cost(prompt: str, modelo: str) -> float

# Test Cases (15+):
# - Route to Groq for "fast" task
# - Route to DeepSeek for "reason" task
# - Fallback when primary fails
# - Token counting accuracy
# - Cost estimation
# - Error handling (all backends down)
```

#### 9. **groq_backend.py**
```python
# Location: infrastructure/ai/backends/groq_backend.py
# Model: Llama 3.3 70B Versatile
# Rate Limit: 30 requests/minute (free tier)
# Latency: ~500ms
# Cost: Free tier generous (suitable for production MVP)
# Use Cases: Fast analysis, sentiment summaries, chat

class GroqBackend:
    async def generate(prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str
    async def stream(prompt: str, on_chunk: Callable) -> str  # Streaming responses

# Test Cases (15+):
# - Simple prompt
# - Multi-turn conversation
# - Token limit enforcement
# - Error: rate limit (429)
# - Streaming chunks
# - Timeout handling
```

#### 10. **deepseek_backend.py**
```python
# Location: infrastructure/ai/backends/deepseek_backend.py
# Model: DeepSeek R1
# Rate Limit: As per plan (check API docs)
# Latency: ~2-5 seconds (reasoning takes time)
# Cost: Paid tier
# Use Cases: DCF multi-scenario analysis, 7-step Graham analysis, complex reasoning

class DeepSeekBackend:
    async def generate(prompt: str, thinking_budget: int = 10000) -> str
    # Returns both thinking and response

# Test Cases (15+):
# - Simple request
# - Reasoning budget control
# - Response quality
# - Timeout handling (5+ sec)
# - Cost tracking
```

#### 11. **qwen_backend.py**
```python
# Location: infrastructure/ai/backends/qwen_backend.py
# Model: Qwen2.5-72B
# Rate Limit: As per Alibaba cloud plan
# Latency: ~1-2 seconds
# Cost: Pay-per-token
# Use Cases: Bulk screener analysis, 500+ ticker evaluation, Asia-focused

class QwenBackend:
    async def generate(prompt: str, max_tokens: int = 2048) -> str
    async def batch_generate(prompts: List[str]) -> List[str]  # Batch mode

# Test Cases (15+):
# - Single generation
# - Batch processing (10 prompts)
# - Rate limiting
# - Error handling
```

#### 12. **openrouter_backend.py** (Universal Fallback)
```python
# Location: infrastructure/ai/backends/openrouter_backend.py
# Purpose: When primary backends are down/rate-limited
# Routing: Multiple models via OpenRouter API
# Cost: Paid (premium models)

class OpenRouterBackend:
    async def generate(prompt: str, model: str = "auto") -> str

# Test Cases (15+):
# - Fallback routing
# - Model selection
# - Cost tracking
# - Error handling
```

---

### GROUP 4: Sentiment & Specialized (4 adapters)
**Priority**: MEDIUM (Market Monitor, News Feed)

#### 13. **finbert_analyzer.py** (Local NLP)
```python
# Location: infrastructure/sentiment/finbert_analyzer.py
# Model: FinBERT (from HuggingFace, local execution)
# Data: Financial news, earnings calls, social media text
# Advantage: Local = no API cost, no rate limits, privacy

class FinBERTAnalyzer:
    async def analyze_sentiment(text: str) -> Dict[str, float]
    # Returns: {"positive": 0.82, "negative": 0.12, "neutral": 0.06}
    
    async def batch_analyze(texts: List[str]) -> List[Dict]  # Efficient batch

# Test Cases (15+):
# - Single text sentiment
# - Batch 100 headlines
# - Empty text handling
# - Very long text (>512 tokens)
# - Financial jargon (earnings, dilution, EBITDA)
# - Sarcasm detection (if trained)
```

#### 14. **newsapi_adapter.py**
```python
# Location: infrastructure/sentiment/newsapi_adapter.py
# Rate Limit: 100 requests/day (free tier)
# Data: Real-time news across 150+ sources
# Use: Headlines for companies in watchlist/portfolio

class NewsAPIAdapter:
    async def get_headlines(ticker: str, company_name: str, limit: int = 50) -> List[Dict]
    async def search(query: str, from_date: str, to_date: str) -> List[Dict]
    # Returns: [{"title": "...", "description": "...", "source": "...", "published_at": "..."}]

# Test Cases (15+):
# - Recent headlines for ticker
# - Search by keyword
# - Date range filtering
# - Cache hits (sentiment_24h)
# - Rate limit (100/day)
# - Error: invalid ticker
```

#### 15. **reddit_adapter.py**
```python
# Location: infrastructure/sentiment/reddit_adapter.py
# Data: Subreddit discussion (r/stocks, r/investing, r/wallstreetbets)
# Use: Sentiment mining, retail investor perspective
# Requirements: Reddit API credentials (free with account)

class RedditAdapter:
    async def get_posts(subreddit: str, ticker: str, limit: int = 50) -> List[Dict]
    async def get_sentiment_summary(ticker: str, days: int = 7) -> Dict
    # Returns: {"positive_pct": 65, "negative_pct": 20, "neutral_pct": 15, "mentions": 450}

# Test Cases (15+):
# - Fetch posts from r/stocks
# - Filter by ticker/company name
# - Date range
# - Sentiment score calculation
# - Rate limit (Reddit quota)
# - Cache hits (sentiment_24h)
# - Error: subreddit not found
```

---

## 🔗 INTEGRATION: data_provider.py (Master Coordinator)

```python
# Location: infrastructure/market_data/data_provider.py
# Purpose: Single entry point for all data with transparent fallback

class DataProvider:
    async def get_quote(ticker: str) -> Dict:
        """Try Finnhub → yfinance → Tiingo → AlphaVantage"""
        try:
            return await finnhub_adapter.get_quote(ticker)
        except RateLimitExceeded:
            return await yfinance_adapter.get_quote(ticker)
        except APIError:
            return await tiingo_adapter.get_quote(ticker)
        except Exception:
            return await alphavantage_adapter.get_quote(ticker)
    
    async def get_fundamentals(ticker: str) -> Dict:
        """Try FMP → SEC XBRL"""
        try:
            return await fmp_adapter.get_ratios(ticker)
        except (RateLimitExceeded, APIError):
            return await sec_adapter.get_facts(ticker)
    
    async def get_macro(series_id: str) -> float:
        """Get from FRED (with fallback if needed)"""
        return await fred_adapter.get_latest(series_id)

# Usage in application layer:
#   quote = await data_provider.get_quote("AAPL")
#   Caller doesn't know/care which adapter was used
```

---

## 🧪 TESTING STRATEGY

### Unit Tests (15+ per adapter)
```
test_finnhub_adapter.py
├── test_quote_fetch          ✓ Normal operation
├── test_batch_quotes         ✓ 10 tickers in < 2 sec
├── test_rate_limit           ✓ Respects 60/min limit
├── test_cache_hit            ✓ Quote expires after 1 min
├── test_cache_miss           ✓ Refetch after expiry
├── test_404_error            ✓ Ticker not found
├── test_429_error            ✓ Rate limit exceeded → fallback
├── test_timeout              ✓ Connection timeout handling
├── test_malformed_response   ✓ Invalid JSON handling
└── test_empty_response       ✓ No data scenarios
```

### Integration Tests
```
test_data_provider.py
├── test_fallback_chain       ✓ Finnhub → yfinance → Tiingo
├── test_batch_performance    ✓ 100 tickers < 5 sec
├── test_concurrent_requests  ✓ No race conditions
├── test_cache_coordination   ✓ Cache shared across adapters
└── test_error_propagation    ✓ Proper exception re-raising
```

### Performance Benchmarks
```
benchmark_adapters.py
├── 1 ticker quote:  < 500ms
├── 50 tickers:      < 2 sec
├── 100 tickers:     < 5 sec
├── Fundamentals:    < 1 sec per ticker (cached)
└── Macro data:      < 500ms (10 series batch)
```

---

## 📋 EXECUTION PLAN (How to Run Phase 2)

### Step 1: Use api-adapter-factory Skill
```bash
# For each adapter, invoke the skill:
Skill: api-adapter-factory
Input: finnhub_adapter
Output: infrastructure/market_data/finnhub_adapter.py (200+ lines + tests)

# Repeat for all 15 adapters
```

### Step 2: Create data_provider.py
```bash
# Manually create or use orchestrator to create coordinator
File: infrastructure/market_data/data_provider.py
Content: Fallback chain logic (see Integration section above)
```

### Step 3: Verify All Adapters
```bash
pytest infrastructure/ -v              # All 15 adapters must pass tests
python -m infrastructure.market_data.data_provider AAPL KO MSFT  # Real-world test
```

### Step 4: Benchmark Performance
```bash
python scripts/benchmark_adapters.py
# Output: Latency per adapter, batch performance, cache hit rates
```

### Step 5: Commit & Push
```bash
git add infrastructure/ tests/
git commit -m "✓ Phase 2 Complete: 15+ API adapters with fallback chains"
git push origin main
```

---

## 🚨 COMMON PITFALLS TO AVOID

### 1. ❌ Per-Ticker Loops
```python
# WRONG: 100 requests = 100 API calls
for ticker in tickers:
    quote = yfinance.download(ticker)

# RIGHT: 100 requests = 1 API call
quotes = yfinance.download(tickers)
```

### 2. ❌ Hardcoded Fallback Logic
```python
# WRONG: Client code knows about fallbacks
try:
    return finnhub_adapter.get_quote(ticker)
except:
    return yfinance_adapter.get_quote(ticker)

# RIGHT: Adapter handles fallback
return data_provider.get_quote(ticker)  # Transparent fallback
```

### 3. ❌ Expired Cache Not Refreshed
```python
# WRONG: Cache never expires (stale data forever)
cache[ticker] = quote

# RIGHT: TTL-based cache (auto-expiry)
cache.set_with_ttl(f"quote_{ticker}", quote, ttl_minutes=1)
```

### 4. ❌ No Rate Limit Accounting
```python
# WRONG: Ignore API limits
for ticker in 100_tickers:
    finnhub_adapter.get_quote(ticker)  # 100 req in 1 sec = 429 error

# RIGHT: Respect rate limits
if not limiter.allow_request():
    raise RateLimitExceeded()  # Caller uses fallback
```

### 5. ❌ Swallowing Exceptions
```python
# WRONG: Bare except hides bugs
try:
    result = adapter.fetch()
except:
    return None

# RIGHT: Specific exception handling
try:
    result = adapter.fetch()
except RateLimitExceeded:
    raise  # Caller handles fallback
except APIError as e:
    logger.error(f"API error: {e}", exc_info=True)
    raise
```

---

## ✅ PHASE 2 SUCCESS CRITERIA

- ✅ All 15 adapters implemented with tests passing
- ✅ `pytest infrastructure/ -v` → 100% pass rate
- ✅ Batch performance: 100 tickers < 5 seconds
- ✅ Fallback chains tested (simulate primary failure)
- ✅ Rate limiting respected (no 429 errors)
- ✅ Caching verified (>80% hit rate on repeats)
- ✅ No bare excepts in any adapter
- ✅ Type hints on all functions
- ✅ Comprehensive docstrings
- ✅ Committed & pushed to GitHub

---

## 📅 TIMELINE

```
Start Phase 2: When Phase 1 committed ✅
├── 15 min: Generate 5 market data adapters (parallel)
├── 10 min: Generate 2 macro adapters (parallel)
├── 15 min: Generate 5 AI backends + gateway (parallel)
├── 10 min: Generate 4 sentiment adapters (parallel)
├── 15 min: Create data_provider.py + ai_gateway.py coordinators
├── 15 min: Run integration tests + benchmarks
├── 10 min: Fix any failing tests
├── 5 min: Commit & push to GitHub
└── Total: ~90 minutes (parallel execution)
```

---

## 🎯 READY TO START PHASE 2?

**Prerequisites**:
- ✅ Phase 1 complete and committed
- ✅ API keys ready (at minimum: GROQ, FRED, FINNHUB, FMP, HF_TOKEN)
- ✅ api-adapter-factory skill available
- ✅ Ability to spawn 6-8 parallel agents

**Command to Start**:
```
Invoke quantum-dev-orchestrator skill:
"Orchestrate Phase 2: Generate 15 API adapters in parallel"
```

**Expected Output**:
- 15 new files in infrastructure/
- 15 test files updated
- data_provider.py with fallback chains
- ai_gateway.py with intelligent routing
- All tests passing
- Ready for Phase 3 (UI skeleton)

---

**Next Session**: Start Phase 2 with orchestrator and api-adapter-factory skill  
**Duration**: 2-4 hours with parallel execution  
**Complexity**: Moderate (templates provided, standardized patterns)
