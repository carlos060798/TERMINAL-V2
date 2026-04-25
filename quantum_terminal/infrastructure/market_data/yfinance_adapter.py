"""Yahoo Finance market data adapter with caching and batch support.

Provides historical price data, company information, dividends, and
options chain data via yfinance. Implements caching with TTL and
batch operations using concurrent requests.

Rate Limit: 2000 requests/day (soft limit)
Cache TTL:
- Quotes: 1 minute
- Historical: 1 hour
- Company info: 7 days
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class YFinanceAPIError(Exception):
    """Base exception for yfinance API errors."""

    pass


class YFinanceDataError(YFinanceAPIError):
    """Exception raised for data retrieval errors."""

    pass


class YFinanceConnectionError(YFinanceAPIError):
    """Exception raised for connection errors."""

    pass


class YFinanceAdapter:
    """Adapter for Yahoo Finance market data.

    Provides methods for:
    - Historical price data (OHLCV)
    - Company information and details
    - Dividend history
    - Options chains
    - Batch operations with concurrent requests
    """

    def __init__(self):
        """Initialize yfinance adapter."""
        # Suppress yfinance logging
        logging.getLogger("yfinance").setLevel(logging.WARNING)
        logger.info("YFinanceAdapter initialized")

    async def get_historical(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical price data.

        Args:
            ticker: Stock ticker.
            period: Time period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max").
            interval: Candle interval ("1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo").

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Dividends, Stock Splits.

        Raises:
            YFinanceDataError: If data retrieval fails.

        Examples:
            >>> adapter = YFinanceAdapter()
            >>> df = await adapter.get_historical("AAPL", "1y")
            >>> print(df.head())
        """
        cache_key = f"yfinance_historical_{ticker}_{period}_{interval}"

        # Try cache (1 hour TTL for historical data)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60)
        if cached is not None:
            logger.debug(f"Historical cache HIT: {ticker}")
            return cached

        try:
            # Run blocking yfinance call in executor
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, lambda: yf.download(ticker, period=period, interval=interval, progress=False)
            )

            if df.empty:
                raise YFinanceDataError(f"No data retrieved for {ticker}")

            # Cache for 1 hour
            cache.set_with_ttl(cache_key, df, ttl_minutes=60)
            logger.debug(f"Historical cache SET: {ticker} ({len(df)} rows)")

            return df

        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {e}")
            raise YFinanceDataError(f"Failed to get historical data for {ticker}") from e

    async def batch_historical(
        self, tickers: List[str], period: str = "1y", interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple tickers concurrently.

        Args:
            tickers: List of stock tickers.
            period: Time period.
            interval: Candle interval.

        Returns:
            Dictionary mapping ticker to historical DataFrame.

        Examples:
            >>> adapter = YFinanceAdapter()
            >>> data = await adapter.batch_historical(["AAPL", "MSFT", "GOOGL"])
            >>> for ticker, df in data.items():
            ...     print(f"{ticker}: {len(df)} rows")
        """
        logger.info(f"Fetching historical data for {len(tickers)} tickers")

        tasks = [self.get_historical(ticker, period, interval) for ticker in tickers]
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

    async def get_info(self, ticker: str) -> Dict[str, Any]:
        """Get company information.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with company info:
            {
                "ticker": str,
                "longName": str,
                "sector": str,
                "industry": str,
                "marketCap": float,
                "dividendRate": float,
                "dividendYield": float,
                "trailingPE": float,
                "forwardPE": float
            }

        Raises:
            YFinanceDataError: If data retrieval fails.

        Examples:
            >>> adapter = YFinanceAdapter()
            >>> info = await adapter.get_info("AAPL")
            >>> print(info["sector"])
        """
        cache_key = f"yfinance_info_{ticker}"

        # Try cache (7 day TTL for company info)
        cached = cache.get_company_info(cache_key)
        if cached:
            logger.debug(f"Info cache HIT: {ticker}")
            return cached

        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, ticker)
            info_dict = await loop.run_in_executor(None, lambda: ticker_obj.info)

            result = {
                "ticker": ticker,
                "longName": info_dict.get("longName", ""),
                "sector": info_dict.get("sector", ""),
                "industry": info_dict.get("industry", ""),
                "marketCap": info_dict.get("marketCap", 0),
                "dividendRate": info_dict.get("dividendRate", 0),
                "dividendYield": info_dict.get("dividendYield", 0),
                "trailingPE": info_dict.get("trailingPE", 0),
                "forwardPE": info_dict.get("forwardPE", 0),
                "profitMargins": info_dict.get("profitMargins", 0),
                "operatingMargins": info_dict.get("operatingMargins", 0),
            }

            # Cache for 7 days
            cache.set_with_ttl(cache_key, result, ttl_minutes=7 * 24 * 60)
            logger.debug(f"Info cache SET: {ticker}")

            return result

        except Exception as e:
            logger.error(f"Error getting info for {ticker}: {e}")
            raise YFinanceDataError(f"Failed to get info for {ticker}") from e

    async def get_dividends(self, ticker: str) -> pd.Series:
        """Get dividend history.

        Args:
            ticker: Stock ticker.

        Returns:
            Pandas Series with dividend dates as index and amounts as values.

        Raises:
            YFinanceDataError: If data retrieval fails.

        Examples:
            >>> adapter = YFinanceAdapter()
            >>> dividends = await adapter.get_dividends("KO")
            >>> print(dividends.head())
        """
        cache_key = f"yfinance_dividends_{ticker}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached is not None:
            logger.debug(f"Dividends cache HIT: {ticker}")
            return cached

        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, ticker)
            dividends = await loop.run_in_executor(None, lambda: ticker_obj.dividends)

            if dividends.empty:
                logger.debug(f"No dividend data for {ticker}")
            else:
                # Cache for 1 day
                cache.set_with_ttl(cache_key, dividends, ttl_minutes=60 * 24)
                logger.debug(f"Dividends cache SET: {ticker} ({len(dividends)} records)")

            return dividends

        except Exception as e:
            logger.error(f"Error getting dividends for {ticker}: {e}")
            raise YFinanceDataError(f"Failed to get dividends for {ticker}") from e

    async def get_options_chain(self, ticker: str, expiration: str) -> Dict[str, pd.DataFrame]:
        """Get options chain data for a specific expiration.

        Args:
            ticker: Stock ticker.
            expiration: Expiration date (YYYY-MM-DD or from available expirations).

        Returns:
            Dictionary with 'calls' and 'puts' DataFrames.

        Raises:
            YFinanceDataError: If data retrieval fails.

        Examples:
            >>> adapter = YFinanceAdapter()
            >>> chain = await adapter.get_options_chain("AAPL", "2026-05-15")
            >>> print(chain["calls"].head())
        """
        cache_key = f"yfinance_options_{ticker}_{expiration}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached is not None:
            logger.debug(f"Options cache HIT: {ticker} ({expiration})")
            return cached

        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, ticker)
            option_chain = await loop.run_in_executor(
                None, lambda: ticker_obj.option_chain(expiration)
            )

            result = {
                "calls": option_chain.calls,
                "puts": option_chain.puts,
            }

            # Cache for 1 day
            cache.set_with_ttl(cache_key, result, ttl_minutes=60 * 24)
            logger.debug(f"Options cache SET: {ticker} ({expiration})")

            return result

        except Exception as e:
            logger.error(f"Error getting options for {ticker} ({expiration}): {e}")
            raise YFinanceDataError(f"Failed to get options for {ticker}") from e

    async def get_splits(self, ticker: str) -> pd.Series:
        """Get stock split history.

        Args:
            ticker: Stock ticker.

        Returns:
            Pandas Series with split dates as index and ratios as values.

        Raises:
            YFinanceDataError: If data retrieval fails.
        """
        cache_key = f"yfinance_splits_{ticker}"

        # Try cache (7 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=7 * 24 * 60)
        if cached is not None:
            logger.debug(f"Splits cache HIT: {ticker}")
            return cached

        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, ticker)
            splits = await loop.run_in_executor(None, lambda: ticker_obj.splits)

            if splits.empty:
                logger.debug(f"No split data for {ticker}")
            else:
                # Cache for 7 days
                cache.set_with_ttl(cache_key, splits, ttl_minutes=7 * 24 * 60)
                logger.debug(f"Splits cache SET: {ticker} ({len(splits)} records)")

            return splits

        except Exception as e:
            logger.error(f"Error getting splits for {ticker}: {e}")
            raise YFinanceDataError(f"Failed to get splits for {ticker}") from e


# Global adapter instance
_yfinance_adapter: Optional[YFinanceAdapter] = None


def _get_adapter() -> YFinanceAdapter:
    """Get or create global adapter instance."""
    global _yfinance_adapter
    if _yfinance_adapter is None:
        _yfinance_adapter = YFinanceAdapter()
    return _yfinance_adapter


async def get_historical(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Get historical data using global adapter."""
    adapter = _get_adapter()
    return await adapter.get_historical(ticker, period, interval)


async def batch_historical(tickers: List[str], period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """Get batch historical data using global adapter."""
    adapter = _get_adapter()
    return await adapter.batch_historical(tickers, period, interval)


async def get_info(ticker: str) -> Dict[str, Any]:
    """Get company info using global adapter."""
    adapter = _get_adapter()
    return await adapter.get_info(ticker)


async def get_dividends(ticker: str) -> pd.Series:
    """Get dividends using global adapter."""
    adapter = _get_adapter()
    return await adapter.get_dividends(ticker)


async def get_options_chain(ticker: str, expiration: str) -> Dict[str, pd.DataFrame]:
    """Get options chain using global adapter."""
    adapter = _get_adapter()
    return await adapter.get_options_chain(ticker, expiration)
