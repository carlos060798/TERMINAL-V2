"""Tiingo market data adapter for clean, adjusted historical data.

Provides high-quality historical price data with built-in adjustments
for splits and dividends. Implements rate limiting (500 req/day) and
configurable TTL caching.

Rate Limit: 500 requests/day
Cache TTL:
- Historical: 1 hour
- Metadata: 7 days
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class TiingoAPIError(Exception):
    """Base exception for Tiingo API errors."""

    pass


class TiingoRateLimitError(TiingoAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class TiingoHTTPError(TiingoAPIError):
    """Exception raised for HTTP errors."""

    pass


class TiingoConnectionError(TiingoAPIError):
    """Exception raised for connection errors."""

    pass


class TiingoAdapter:
    """Adapter for Tiingo API market data.

    Provides methods for:
    - Historical price data (daily, with adjustments)
    - Metadata (ticker information)
    - Batch operations with concurrent requests
    """

    BASE_URL = "https://api.tiingo.com/tiingo"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Tiingo adapter.

        Args:
            api_key: Tiingo API key. If None, reads from TIINGO_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found.
        """
        self.api_key = api_key or os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY not provided and not found in environment")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("TiingoAdapter initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make GET request to Tiingo API.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            JSON response as dictionary or list.

        Raises:
            TiingoRateLimitError: If rate limit exceeded.
            TiingoHTTPError: If HTTP error occurs.
            TiingoConnectionError: If connection fails.
        """
        # Check rate limit (500 req/day)
        if not rate_limiter.allow_request("tiingo"):
            raise TiingoRateLimitError("Tiingo: exceeded 500 req/day rate limit")

        if params is None:
            params = {}
        params["token"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 429:
                    raise TiingoRateLimitError(f"Tiingo rate limit: {response.reason}")
                elif response.status == 401:
                    raise TiingoAPIError("Tiingo: Invalid API key")
                elif response.status == 404:
                    raise TiingoAPIError(f"Tiingo: Ticker not found")
                elif response.status >= 400:
                    raise TiingoHTTPError(f"Tiingo HTTP {response.status}: {response.reason}")

                data = await response.json()
                logger.debug(f"Tiingo GET {endpoint}: {response.status}")
                return data

        except aiohttp.ClientError as e:
            raise TiingoConnectionError(f"Tiingo connection error: {str(e)}") from e

    async def get_historical(
        self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Get historical price data.

        Args:
            ticker: Stock ticker.
            start_date: Start date (YYYY-MM-DD). If None, defaults to 10 years ago.
            end_date: End date (YYYY-MM-DD). If None, defaults to today.

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume, Adj Close.

        Raises:
            TiingoHTTPError: If API error occurs.

        Examples:
            >>> async with TiingoAdapter() as adapter:
            ...     df = await adapter.get_historical("AAPL")
            ...     print(df.head())
        """
        cache_key = f"tiingo_historical_{ticker}_{start_date}_{end_date}"

        # Try cache (1 hour TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60)
        if cached is not None:
            logger.debug(f"Historical cache HIT: {ticker}")
            return cached

        try:
            params = {"startDate": start_date, "endDate": end_date}
            params = {k: v for k, v in params.items() if v is not None}

            data = await self._get(f"daily/{ticker}/prices", params)

            if not data:
                raise TiingoAPIError(f"No historical data for {ticker}")

            # Convert to DataFrame
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            # Rename columns to match expected format
            df = df[["open", "high", "low", "close", "volume", "adjClose"]]
            df.columns = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]

            if df.empty:
                raise TiingoAPIError(f"No data retrieved for {ticker}")

            # Cache for 1 hour
            cache.set_with_ttl(cache_key, df, ttl_minutes=60)
            logger.debug(f"Historical cache SET: {ticker} ({len(df)} rows)")

            return df

        except TiingoAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {e}")
            raise TiingoAPIError(f"Failed to get historical data for {ticker}") from e

    async def batch_historical(
        self, tickers: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple tickers concurrently.

        Args:
            tickers: List of stock tickers.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            Dictionary mapping ticker to historical DataFrame.

        Examples:
            >>> async with TiingoAdapter() as adapter:
            ...     data = await adapter.batch_historical(["AAPL", "MSFT"])
            ...     for ticker, df in data.items():
            ...         print(f"{ticker}: {len(df)} rows")
        """
        logger.info(f"Fetching historical data for {len(tickers)} tickers")

        tasks = [self.get_historical(ticker, start_date, end_date) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get historical data for {ticker}: {result}")
                data[ticker] = None
            else:
                data[ticker] = result

        logger.info(f"Batch historical completed: {len(tickers)} tickers")
        return data

    async def get_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get ticker metadata.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with metadata:
            {
                "ticker": str,
                "name": str,
                "exchange": str,
                "startDate": str,
                "endDate": str,
                "dataType": str
            }

        Raises:
            TiingoHTTPError: If API error occurs.

        Examples:
            >>> async with TiingoAdapter() as adapter:
            ...     meta = await adapter.get_metadata("AAPL")
            ...     print(meta["exchange"])
        """
        cache_key = f"tiingo_metadata_{ticker}"

        # Try cache (7 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=7 * 24 * 60)
        if cached:
            logger.debug(f"Metadata cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"daily/{ticker}/meta")

            result = {
                "ticker": data.get("ticker", ticker),
                "name": data.get("name", ""),
                "exchange": data.get("exchange", ""),
                "startDate": data.get("startDate", ""),
                "endDate": data.get("endDate", ""),
                "dataType": data.get("dataType", ""),
                "sessionStart": data.get("sessionStart", ""),
                "sessionEnd": data.get("sessionEnd", ""),
            }

            # Cache for 7 days
            cache.set_with_ttl(cache_key, result, ttl_minutes=7 * 24 * 60)
            logger.debug(f"Metadata cache SET: {ticker}")

            return result

        except Exception as e:
            logger.error(f"Error getting metadata for {ticker}: {e}")
            raise TiingoAPIError(f"Failed to get metadata for {ticker}") from e

    async def get_latest_quote(self, ticker: str) -> Dict[str, Any]:
        """Get latest quote.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with quote data.

        Raises:
            TiingoHTTPError: If API error occurs.

        Examples:
            >>> async with TiingoAdapter() as adapter:
            ...     quote = await adapter.get_latest_quote("AAPL")
            ...     print(quote["last"])
        """
        cache_key = f"tiingo_quote_{ticker}"

        # Try cache (1 minute TTL for quotes)
        cached = cache.get_quote(cache_key)
        if cached:
            logger.debug(f"Quote cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"daily/{ticker}")

            if not isinstance(data, dict):
                raise TiingoAPIError(f"Invalid response for {ticker}")

            result = {
                "ticker": ticker,
                "last": data.get("last", 0),
                "lastSalePrice": data.get("lastSalePrice", 0),
                "lastSaleTime": data.get("lastSaleTime", ""),
                "lastUpdated": data.get("lastUpdated", ""),
                "bid": data.get("bid", 0),
                "ask": data.get("ask", 0),
                "bidSize": data.get("bidSize", 0),
                "askSize": data.get("askSize", 0),
            }

            # Cache for 1 minute
            cache.set_with_ttl(cache_key, result, ttl_minutes=1)
            logger.debug(f"Quote cache SET: {ticker}")

            return result

        except Exception as e:
            logger.error(f"Error getting quote for {ticker}: {e}")
            raise TiingoAPIError(f"Failed to get quote for {ticker}") from e


# Global adapter instance
_tiingo_adapter: Optional[TiingoAdapter] = None


async def get_historical(
    ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> pd.DataFrame:
    """Get historical data using global adapter."""
    global _tiingo_adapter
    if _tiingo_adapter is None:
        _tiingo_adapter = TiingoAdapter()
    return await _tiingo_adapter.get_historical(ticker, start_date, end_date)


async def batch_historical(
    tickers: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """Get batch historical data using global adapter."""
    global _tiingo_adapter
    if _tiingo_adapter is None:
        _tiingo_adapter = TiingoAdapter()
    return await _tiingo_adapter.batch_historical(tickers, start_date, end_date)


async def get_metadata(ticker: str) -> Dict[str, Any]:
    """Get metadata using global adapter."""
    global _tiingo_adapter
    if _tiingo_adapter is None:
        _tiingo_adapter = TiingoAdapter()
    return await _tiingo_adapter.get_metadata(ticker)


async def get_latest_quote(ticker: str) -> Dict[str, Any]:
    """Get latest quote using global adapter."""
    global _tiingo_adapter
    if _tiingo_adapter is None:
        _tiingo_adapter = TiingoAdapter()
    return await _tiingo_adapter.get_latest_quote(ticker)
