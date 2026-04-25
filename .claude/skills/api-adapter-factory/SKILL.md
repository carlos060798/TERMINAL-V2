---
name: api-adapter-factory
description: |
  Create API adapters for Quantum Investment Terminal with rate limiting, caching, and fallback chains.
  Generates production-ready adapters for market data (Finnhub, yfinance, FMP, Tiingo, SEC),
  macro data (FRED, EIA), AI backends (Groq, DeepSeek, Qwen), and sentiment analysis.
  Use when implementing Phase 2 or adding new data sources.
  Input: API name. Output: complete adapter with token bucket, caching, error handling, tests (200+ lines).
---

# API Adapter Factory

Create production-ready API adapters with rate limiting, caching, and fallback chains.

## What it generates

**infrastructure/market_data/[api]_adapter.py**
- Rate limiter (token bucket per API limits)
- Caching (diskcache with TTL: quotes 1min, fundamentals 1h, macro 24h)
- Error handling (specific exceptions, no bare excepts)
- Fallback integration (raises correct exceptions for data_provider.py)
- Batch mode (50-100 tickers in 1-2 seconds, not sequential)

**tests/test_[api]_adapter.py**
- 15+ test cases covering happy path, rate limit, cache, errors, timeouts
- All tests pass before Phase 2

## Adapters available

**Market Data**:
- finnhub_adapter.py (60 req/min, live quotes + earnings calendar)
- yfinance_adapter.py (batch OHLCV, fundamentals, dividends)
- fmp_adapter.py (250 req/day, pre-calculated ratios + peers)
- tiingo_adapter.py (500 req/day, clean adjusted data)
- sec_adapter.py (XBRL filings, 10-K/10-Q data)

**Macro**:
- fred_adapter.py (1000 req/day, DGS10, CPI, unemployment)
- eia_adapter.py (oil, gas, inventories)

**AI**:
- groq_backend.py (Llama 3.3 70B, 30 req/min free)
- deepseek_backend.py (DeepSeek R1, reasoning)
- qwen_backend.py (Qwen2.5-72B, bulk processing)
- openrouter_backend.py (universal fallback)
- hf_backend.py (FinBERT, embeddings, local)

## Example (finnhub_adapter.py)

```python
async def get_quote(ticker: str) -> dict:
    """Fetch quote with rate limit + cache"""
    cached = cache.get_with_ttl(f"finnhub_quote_{ticker}", ttl_minutes=1)
    if cached: return cached
    
    if not finnhub_limiter.allow_request():
        raise RateLimitExceeded()  # Caller uses fallback
    
    # API call with error handling
    response = await client.get(...)
    quote = {...}
    cache.set_with_ttl(...)
    return quote

async def batch_quotes(tickers: list[str]) -> dict:
    """Fetch 100 tickers in 2 seconds (concurrent)"""
    tasks = [get_quote(t) for t in tickers]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Integration with data_provider.py

```python
# Fallback chain: try Finnhub → yfinance → Tiingo → AlphaVantage
try:
    return await finnhub_adapter.get_quote(ticker)
except RateLimitExceeded: pass  # Try next
except APIError: pass            # Try next
# ... try yfinance, tiingo, alphavantage ...
```

## Key features

✅ Rate limiting (respects API limits)  
✅ Caching (saves 90% API calls)  
✅ Error handling (specific exceptions, logging)  
✅ Fallback-aware (raises RateLimitExceeded, APIError, HTTPError)  
✅ Batch mode (concurrent requests)  
✅ Async/await (non-blocking)  
✅ Tests (15+ cases per adapter)
