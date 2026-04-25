"""Finnhub market data adapter with rate limiting and caching.

Provides real-time quotes, company profiles, and earnings calendar data
via Finnhub API. Implements token bucket rate limiting (60 req/min) and
configurable TTL caching.

Rate Limit: 60 requests/minute
Cache TTL:
- Quotes: 1 minute
- Company info: 7 days
- Earnings: 1 day
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class FinnhubAPIError(Exception):
    """Base exception for Finnhub API errors."""

    pass


class FinnhubRateLimitError(FinnhubAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class FinnhubHTTPError(FinnhubAPIError):
    """Exception raised for HTTP errors from Finnhub API."""

    pass


class FinnhubConnectionError(FinnhubAPIError):
    """Exception raised for connection errors."""

    pass


class FinnhubAdapter:
    """Adapter for Finnhub API market data.

    Provides methods for:
    - Real-time quotes (bid/ask/last price)
    - Company profiles (sector, industry, market cap)
    - Earnings calendar events
    - Batch operations with concurrent requests
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Finnhub adapter.

        Args:
            api_key: Finnhub API key. If None, reads from FINNHUB_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found.
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY not provided and not found in environment")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("FinnhubAdapter initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to Finnhub API.

        Args:
            endpoint: API endpoint (e.g., "quote", "company-profile").
            params: Query parameters.

        Returns:
            JSON response as dictionary.

        Raises:
            FinnhubRateLimitError: If rate limit exceeded.
            FinnhubHTTPError: If HTTP error occurs.
            FinnhubConnectionError: If connection fails.
        """
        # Check rate limit
        if not rate_limiter.allow_request("finnhub"):
            raise FinnhubRateLimitError("Finnhub: exceeded 60 req/min rate limit")

        if params is None:
            params = {}
        params["token"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 429:
                    raise FinnhubRateLimitError(f"Finnhub rate limit: {response.reason}")
                elif response.status == 401:
                    raise FinnhubAPIError("Finnhub: Invalid API key")
                elif response.status >= 400:
                    raise FinnhubHTTPError(f"Finnhub HTTP {response.status}: {response.reason}")

                data = await response.json()
                logger.debug(f"Finnhub GET {endpoint}: {response.status}")
                return data

        except aiohttp.ClientError as e:
            raise FinnhubConnectionError(f"Finnhub connection error: {str(e)}") from e

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote for a ticker.

        Args:
            ticker: Stock ticker (e.g., "AAPL").

        Returns:
            Dictionary with quote data:
            {
                "ticker": str,
                "price": float,
                "bid": float,
                "ask": float,
                "timestamp": int (Unix timestamp)
            }

        Raises:
            FinnhubRateLimitError: If rate limit exceeded.
            FinnhubHTTPError: If API error occurs.

        Examples:
            >>> async with FinnhubAdapter() as adapter:
            ...     quote = await adapter.get_quote("AAPL")
            ...     print(quote["price"])
        """
        cache_key = f"finnhub_quote_{ticker}"

        # Try cache first
        cached = cache.get_quote(cache_key)
        if cached:
            logger.debug(f"Quote cache HIT: {ticker}")
            return cached

        try:
            data = await self._get("quote", {"symbol": ticker})

            result = {
                "ticker": ticker,
                "price": data.get("c", 0),
                "bid": data.get("b", 0),
                "ask": data.get("a", 0),
                "high": data.get("h", 0),
                "low": data.get("l", 0),
                "open": data.get("o", 0),
                "previousClose": data.get("pc", 0),
                "timestamp": data.get("t", 0),
            }

            # Cache for 1 minute
            cache.set_with_ttl(cache_key, result, ttl_minutes=1)
            logger.debug(f"Quote cache SET: {ticker}")

            return result

        except FinnhubAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting quote for {ticker}: {e}")
            raise FinnhubAPIError(f"Failed to get quote for {ticker}") from e

    async def batch_quotes(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quotes for multiple tickers concurrently.

        Uses asyncio.gather for efficient concurrent requests.

        Args:
            tickers: List of stock tickers.

        Returns:
            Dictionary mapping ticker to quote data. Includes exceptions for failed requests.

        Examples:
            >>> async with FinnhubAdapter() as adapter:
            ...     quotes = await adapter.batch_quotes(["AAPL", "MSFT", "GOOGL"])
            ...     for ticker, quote in quotes.items():
            ...         print(f"{ticker}: ${quote['price']}")
        """
        logger.info(f"Fetching quotes for {len(tickers)} tickers")

        tasks = [self.get_quote(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        quotes = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get quote for {ticker}: {result}")
                quotes[ticker] = {"error": str(result)}
            else:
                quotes[ticker] = result

        logger.info(f"Batch quotes completed: {len(tickers)} tickers")
        return quotes

    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Get company profile information.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with company info:
            {
                "ticker": str,
                "name": str,
                "exchange": str,
                "sector": str,
                "industry": str,
                "marketCapitalization": float,
                "country": str
            }

        Raises:
            FinnhubHTTPError: If API error occurs.

        Examples:
            >>> async with FinnhubAdapter() as adapter:
            ...     profile = await adapter.get_company_profile("AAPL")
            ...     print(profile["sector"])
        """
        cache_key = f"finnhub_profile_{ticker}"

        # Try cache first (7 day TTL for company info)
        cached = cache.get_company_info(cache_key)
        if cached:
            logger.debug(f"Profile cache HIT: {ticker}")
            return cached

        try:
            data = await self._get("stock/profile2", {"symbol": ticker})

            result = {
                "ticker": ticker,
                "name": data.get("name", ""),
                "exchange": data.get("exchange", ""),
                "sector": data.get("finnhubIndustry", ""),
                "industry": data.get("finnhubIndustry", ""),
                "marketCapitalization": data.get("marketCapitalization", 0),
                "country": data.get("country", ""),
                "currency": data.get("currency", "USD"),
            }

            # Cache for 7 days
            cache.set_with_ttl(cache_key, result, ttl_minutes=7 * 24 * 60)
            logger.debug(f"Profile cache SET: {ticker}")

            return result

        except Exception as e:
            logger.error(f"Error getting profile for {ticker}: {e}")
            raise FinnhubAPIError(f"Failed to get profile for {ticker}") from e

    async def get_earnings_calendar(
        self, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get earnings calendar events.

        Args:
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).

        Returns:
            List of earnings events.

        Raises:
            FinnhubHTTPError: If API error occurs.

        Examples:
            >>> async with FinnhubAdapter() as adapter:
            ...     earnings = await adapter.get_earnings_calendar("2026-01-01", "2026-12-31")
            ...     for event in earnings:
            ...         print(f"{event['ticker']}: {event['date']}")
        """
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        cache_key = f"finnhub_earnings_{from_date}_{to_date}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            return cached

        try:
            data = await self._get("calendar/earnings", params)
            earnings = data.get("earningsCalendar", [])

            # Cache for 1 day
            cache.set_with_ttl(cache_key, earnings, ttl_minutes=60 * 24)

            return earnings

        except Exception as e:
            logger.error(f"Error getting earnings calendar: {e}")
            raise FinnhubAPIError("Failed to get earnings calendar") from e


# Global adapter instance
_finnhub_adapter: Optional[FinnhubAdapter] = None


async def get_quote(ticker: str) -> Dict[str, Any]:
    """Get quote using global adapter.

    Args:
        ticker: Stock ticker.

    Returns:
        Quote dictionary.
    """
    global _finnhub_adapter
    if _finnhub_adapter is None:
        _finnhub_adapter = FinnhubAdapter()

    return await _finnhub_adapter.get_quote(ticker)


async def batch_quotes(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get batch quotes using global adapter.

    Args:
        tickers: List of stock tickers.

    Returns:
        Dictionary of quotes.
    """
    global _finnhub_adapter
    if _finnhub_adapter is None:
        _finnhub_adapter = FinnhubAdapter()

    return await _finnhub_adapter.batch_quotes(tickers)
