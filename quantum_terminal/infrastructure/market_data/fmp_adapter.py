"""Financial Modeling Prep API adapter for fundamental data.

Provides financial ratios, key metrics, company profiles, and peer
information via FMP API. Implements rate limiting (250 req/day) and
configurable TTL caching.

Rate Limit: 250 requests/day
Cache TTL:
- Ratios: 1 day
- Key metrics: 1 day
- Company info: 7 days
- Peers: 7 days
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class FMPAPIError(Exception):
    """Base exception for FMP API errors."""

    pass


class FMPRateLimitError(FMPAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class FMPHTTPError(FMPAPIError):
    """Exception raised for HTTP errors."""

    pass


class FMPConnectionError(FMPAPIError):
    """Exception raised for connection errors."""

    pass


class FMPAdapter:
    """Adapter for Financial Modeling Prep API.

    Provides methods for:
    - Financial ratios (PE, PB, ROE, ROA, etc.)
    - Key metrics (market cap, shares outstanding, etc.)
    - Company profiles
    - Peer companies
    - Batch operations with concurrent requests
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize FMP adapter.

        Args:
            api_key: FMP API key. If None, reads from FMP_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found.
        """
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY not provided and not found in environment")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("FMPAdapter initialized")

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
        """Make GET request to FMP API.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            JSON response as dictionary or list.

        Raises:
            FMPRateLimitError: If rate limit exceeded.
            FMPHTTPError: If HTTP error occurs.
            FMPConnectionError: If connection fails.
        """
        # Check rate limit (FMP allows 250 req/day)
        if not rate_limiter.allow_request("fmp"):
            raise FMPRateLimitError("FMP: exceeded 250 req/day rate limit")

        if params is None:
            params = {}
        params["apikey"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 429:
                    raise FMPRateLimitError(f"FMP rate limit: {response.reason}")
                elif response.status == 401:
                    raise FMPAPIError("FMP: Invalid API key")
                elif response.status >= 400:
                    raise FMPHTTPError(f"FMP HTTP {response.status}: {response.reason}")

                data = await response.json()
                logger.debug(f"FMP GET {endpoint}: {response.status}")
                return data

        except aiohttp.ClientError as e:
            raise FMPConnectionError(f"FMP connection error: {str(e)}") from e

    async def get_ratios(self, ticker: str) -> Dict[str, Any]:
        """Get financial ratios for a company.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with financial ratios:
            {
                "ticker": str,
                "peRatio": float,
                "pbRatio": float,
                "psRatio": float,
                "roe": float,
                "roa": float,
                "debtRatio": float,
                "currentRatio": float
            }

        Raises:
            FMPHTTPError: If API error occurs.

        Examples:
            >>> async with FMPAdapter() as adapter:
            ...     ratios = await adapter.get_ratios("AAPL")
            ...     print(ratios["peRatio"])
        """
        cache_key = f"fmp_ratios_{ticker}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            logger.debug(f"Ratios cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"ratios/{ticker}")

            if not data or (isinstance(data, list) and len(data) == 0):
                raise FMPAPIError(f"No ratio data for {ticker}")

            # Handle list response
            if isinstance(data, list):
                ratio_data = data[0] if data else {}
            else:
                ratio_data = data

            result = {
                "ticker": ticker,
                "peRatio": ratio_data.get("peRatio", 0),
                "pbRatio": ratio_data.get("pbRatio", 0),
                "psRatio": ratio_data.get("psRatio", 0),
                "roe": ratio_data.get("roe", 0),
                "roa": ratio_data.get("roa", 0),
                "debtRatio": ratio_data.get("debtRatio", 0),
                "currentRatio": ratio_data.get("currentRatio", 0),
                "quickRatio": ratio_data.get("quickRatio", 0),
                "operatingProfitMargin": ratio_data.get("operatingProfitMargin", 0),
            }

            # Cache for 1 day
            cache.set_with_ttl(cache_key, result, ttl_minutes=60 * 24)
            logger.debug(f"Ratios cache SET: {ticker}")

            return result

        except FMPAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting ratios for {ticker}: {e}")
            raise FMPAPIError(f"Failed to get ratios for {ticker}") from e

    async def get_key_metrics(self, ticker: str) -> Dict[str, Any]:
        """Get key metrics for a company.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with key metrics:
            {
                "ticker": str,
                "marketCap": float,
                "sharesOutstanding": float,
                "bookValue": float,
                "tangibleBookValue": float
            }

        Raises:
            FMPHTTPError: If API error occurs.

        Examples:
            >>> async with FMPAdapter() as adapter:
            ...     metrics = await adapter.get_key_metrics("AAPL")
            ...     print(metrics["marketCap"])
        """
        cache_key = f"fmp_metrics_{ticker}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            logger.debug(f"Metrics cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"key-metrics/{ticker}")

            if not data or (isinstance(data, list) and len(data) == 0):
                raise FMPAPIError(f"No metric data for {ticker}")

            # Handle list response
            if isinstance(data, list):
                metric_data = data[0] if data else {}
            else:
                metric_data = data

            result = {
                "ticker": ticker,
                "marketCap": metric_data.get("marketCap", 0),
                "sharesOutstanding": metric_data.get("sharesOutstanding", 0),
                "bookValue": metric_data.get("bookValue", 0),
                "tangibleBookValue": metric_data.get("tangibleBookValue", 0),
                "eps": metric_data.get("eps", 0),
                "bvps": metric_data.get("bvps", 0),
                "pbRatio": metric_data.get("pbRatio", 0),
                "peRatio": metric_data.get("peRatio", 0),
            }

            # Cache for 1 day
            cache.set_with_ttl(cache_key, result, ttl_minutes=60 * 24)
            logger.debug(f"Metrics cache SET: {ticker}")

            return result

        except FMPAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting metrics for {ticker}: {e}")
            raise FMPAPIError(f"Failed to get metrics for {ticker}") from e

    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Get company profile.

        Args:
            ticker: Stock ticker.

        Returns:
            Dictionary with company info.

        Raises:
            FMPHTTPError: If API error occurs.

        Examples:
            >>> async with FMPAdapter() as adapter:
            ...     profile = await adapter.get_company_profile("AAPL")
            ...     print(profile["sector"])
        """
        cache_key = f"fmp_profile_{ticker}"

        # Try cache (7 day TTL)
        cached = cache.get_company_info(cache_key)
        if cached:
            logger.debug(f"Profile cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"profile/{ticker}")

            if not data or (isinstance(data, list) and len(data) == 0):
                raise FMPAPIError(f"No profile data for {ticker}")

            # Handle list response
            if isinstance(data, list):
                profile_data = data[0] if data else {}
            else:
                profile_data = data

            result = {
                "ticker": ticker,
                "companyName": profile_data.get("companyName", ""),
                "sector": profile_data.get("sector", ""),
                "industry": profile_data.get("industry", ""),
                "country": profile_data.get("country", ""),
                "marketCap": profile_data.get("marketCap", 0),
                "employees": profile_data.get("employees", 0),
                "website": profile_data.get("website", ""),
            }

            # Cache for 7 days
            cache.set_with_ttl(cache_key, result, ttl_minutes=7 * 24 * 60)
            logger.debug(f"Profile cache SET: {ticker}")

            return result

        except FMPAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting profile for {ticker}: {e}")
            raise FMPAPIError(f"Failed to get profile for {ticker}") from e

    async def get_peers(self, ticker: str) -> List[str]:
        """Get peer companies.

        Args:
            ticker: Stock ticker.

        Returns:
            List of peer company tickers.

        Raises:
            FMPHTTPError: If API error occurs.

        Examples:
            >>> async with FMPAdapter() as adapter:
            ...     peers = await adapter.get_peers("AAPL")
            ...     print(peers)
        """
        cache_key = f"fmp_peers_{ticker}"

        # Try cache (7 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=7 * 24 * 60)
        if cached:
            logger.debug(f"Peers cache HIT: {ticker}")
            return cached

        try:
            data = await self._get(f"peers/{ticker}")

            if not data:
                logger.warning(f"No peers data for {ticker}")
                return []

            peers = data if isinstance(data, list) else data.get("peersList", [])

            # Cache for 7 days
            cache.set_with_ttl(cache_key, peers, ttl_minutes=7 * 24 * 60)
            logger.debug(f"Peers cache SET: {ticker}")

            return peers

        except Exception as e:
            logger.error(f"Error getting peers for {ticker}: {e}")
            raise FMPAPIError(f"Failed to get peers for {ticker}") from e

    async def batch_profiles(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get profiles for multiple tickers concurrently.

        Args:
            tickers: List of stock tickers.

        Returns:
            Dictionary mapping ticker to profile data.

        Examples:
            >>> async with FMPAdapter() as adapter:
            ...     profiles = await adapter.batch_profiles(["AAPL", "MSFT"])
            ...     for ticker, profile in profiles.items():
            ...         print(f"{ticker}: {profile['sector']}")
        """
        logger.info(f"Fetching profiles for {len(tickers)} tickers")

        tasks = [self.get_company_profile(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        profiles = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get profile for {ticker}: {result}")
                profiles[ticker] = {"error": str(result)}
            else:
                profiles[ticker] = result

        logger.info(f"Batch profiles completed: {len(tickers)} tickers")
        return profiles


# Global adapter instance
_fmp_adapter: Optional[FMPAdapter] = None


async def get_ratios(ticker: str) -> Dict[str, Any]:
    """Get ratios using global adapter."""
    global _fmp_adapter
    if _fmp_adapter is None:
        _fmp_adapter = FMPAdapter()
    return await _fmp_adapter.get_ratios(ticker)


async def get_key_metrics(ticker: str) -> Dict[str, Any]:
    """Get key metrics using global adapter."""
    global _fmp_adapter
    if _fmp_adapter is None:
        _fmp_adapter = FMPAdapter()
    return await _fmp_adapter.get_key_metrics(ticker)


async def get_company_profile(ticker: str) -> Dict[str, Any]:
    """Get company profile using global adapter."""
    global _fmp_adapter
    if _fmp_adapter is None:
        _fmp_adapter = FMPAdapter()
    return await _fmp_adapter.get_company_profile(ticker)


async def get_peers(ticker: str) -> List[str]:
    """Get peers using global adapter."""
    global _fmp_adapter
    if _fmp_adapter is None:
        _fmp_adapter = FMPAdapter()
    return await _fmp_adapter.get_peers(ticker)


async def batch_profiles(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get batch profiles using global adapter."""
    global _fmp_adapter
    if _fmp_adapter is None:
        _fmp_adapter = FMPAdapter()
    return await _fmp_adapter.batch_profiles(tickers)
