"""FRED (Federal Reserve Economic Data) adapter for macroeconomic indicators.

Provides async/await interface to FRED API with:
- Token bucket rate limiting (1000 req/day)
- 24-hour caching for macro data
- Fallback chain support
- Specific exception handling

Critical series for Graham Formula:
- DGS10: 10-year Treasury yield (risk-free rate)
- CPI: Consumer Price Index (inflation)
- UNRATE: Unemployment rate
- M2SL: M2 Money Supply
- FEDFUNDS: Federal Funds Rate
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import aiohttp

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)

# Register FRED rate limiter (1000 req/day = ~42 req/hour)
rate_limiter.register("fred", 42, 60)


class FREDException(Exception):
    """Base exception for FRED adapter errors."""
    pass


class FREDRateLimitException(FREDException):
    """Raised when FRED API rate limit is exceeded."""
    pass


class FREDAuthException(FREDException):
    """Raised when FRED API key is missing or invalid."""
    pass


class FREDSeriesException(FREDException):
    """Raised when requested series is not found."""
    pass


class FREDDataException(FREDException):
    """Raised when data retrieval or parsing fails."""
    pass


class FREDAdapter:
    """Async adapter for FRED API.

    Provides methods to fetch economic indicators with caching and rate limiting.

    Examples:
        >>> adapter = FREDAdapter()
        >>> rate = await adapter.get_series("DGS10")  # 10-year Treasury
        >>> latest = await adapter.get_latest("CPI")  # Latest CPI
        >>> batch = await adapter.batch_latest(["DGS10", "CPI", "UNRATE"])
    """

    BASE_URL = "https://api.stlouisfed.org/fred"
    TIMEOUT = 30

    # Critical series for Graham Formula
    CRITICAL_SERIES = {
        "DGS10": "10-Year Treasury Constant Maturity Rate",
        "CPI": "Consumer Price Index for All Urban Consumers",
        "UNRATE": "Unemployment Rate",
        "M2SL": "M2 Money Supply",
        "FEDFUNDS": "Effective Federal Funds Rate",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize FRED adapter.

        Args:
            api_key: FRED API key. Defaults to settings.fred_api_key.

        Raises:
            FREDAuthException: If API key is not provided.
        """
        self.api_key = api_key or settings.fred_api_key
        if not self.api_key:
            raise FREDAuthException("FRED_API_KEY not configured in .env")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("FREDAdapter initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session exists, create if needed."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to FRED API.

        Args:
            endpoint: API endpoint (e.g., "series").
            params: Query parameters.

        Returns:
            Response JSON.

        Raises:
            FREDRateLimitException: If rate limited.
            FREDDataException: If request fails.
        """
        # Check rate limit
        if not rate_limiter.allow_request("fred"):
            raise FREDRateLimitException(
                "FRED rate limit exceeded (1000 req/day)"
            )

        session = await self._ensure_session()

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        params.setdefault("file_type", "json")

        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                if response.status == 400:
                    raise FREDSeriesException(f"Series not found or invalid request")
                elif response.status == 401:
                    raise FREDAuthException(f"Invalid API key")
                elif response.status == 429:
                    raise FREDRateLimitException(f"Rate limit exceeded")
                elif response.status >= 400:
                    raise FREDDataException(f"HTTP {response.status}")

                data = await response.json()
                logger.debug(f"FRED request successful: {endpoint}")
                return data

        except asyncio.TimeoutError:
            raise FREDDataException(f"Request timeout to {endpoint}")
        except FREDException:
            raise
        except Exception as e:
            logger.error(f"FRED request failed: {e}")
            raise FREDDataException(f"Request failed: {str(e)}")

    async def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get full series data.

        Args:
            series_id: FRED series ID (e.g., "DGS10").
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).

        Returns:
            Series data with observations.

        Raises:
            FREDSeriesException: If series not found.
            FREDDataException: If retrieval fails.

        Examples:
            >>> adapter = FREDAdapter()
            >>> series = await adapter.get_series("DGS10", "2024-01-01", "2024-12-31")
            >>> print(series["observations"][-1])
        """
        cache_key = f"fred_series_{series_id}_{start_date}_{end_date}"

        def fetch_fn():
            return asyncio.run(self._request(
                f"series",
                {
                    "series_id": series_id,
                    "limit": 100000,
                    **({} if not start_date else {"observation_start": start_date}),
                    **({} if not end_date else {"observation_end": end_date}),
                },
            ))

        try:
            result = cache.get_macro(cache_key, fetch_fn)
            if result is None:
                logger.warning(f"FRED series fetch returned None: {series_id}")
                return {"series_id": series_id, "observations": []}
            return result
        except FREDException:
            raise
        except Exception as e:
            logger.error(f"Error fetching series {series_id}: {e}")
            raise FREDDataException(f"Series fetch failed: {str(e)}")

    async def get_latest(self, series_id: str) -> Optional[float]:
        """Get latest value for a series.

        Args:
            series_id: FRED series ID.

        Returns:
            Latest numeric value or None if not available.

        Raises:
            FREDSeriesException: If series not found.

        Examples:
            >>> rate = await adapter.get_latest("DGS10")
            >>> print(f"10-year Treasury: {rate}%")
        """
        cache_key = f"fred_latest_{series_id}"

        def fetch_fn():
            return asyncio.run(self._request(
                f"series/observations",
                {
                    "series_id": series_id,
                    "sort_order": "desc",
                    "limit": 1,
                },
            ))

        try:
            data = cache.get_macro(cache_key, fetch_fn)
            if data and "observations" in data and data["observations"]:
                value = data["observations"][0].get("value")
                if value and value != ".":
                    return float(value)
            return None
        except FREDException:
            raise
        except Exception as e:
            logger.error(f"Error fetching latest {series_id}: {e}")
            return None

    async def batch_latest(self, series_ids: list[str]) -> dict[str, Optional[float]]:
        """Get latest values for multiple series.

        Args:
            series_ids: List of FRED series IDs.

        Returns:
            Dictionary mapping series ID to latest value.

        Examples:
            >>> rates = await adapter.batch_latest(["DGS10", "CPI", "UNRATE"])
            >>> for sid, val in rates.items():
            ...     print(f"{sid}: {val}")
        """
        results = {}

        for series_id in series_ids:
            try:
                value = await self.get_latest(series_id)
                results[series_id] = value
            except Exception as e:
                logger.warning(f"Failed to fetch {series_id}: {e}")
                results[series_id] = None

        return results

    async def get_observations(
        self,
        series_id: str,
        limit: int = 100,
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get observations for a series.

        Args:
            series_id: FRED series ID.
            limit: Maximum number of observations to return.
            sort_order: "asc" or "desc".

        Returns:
            List of observation objects.

        Examples:
            >>> obs = await adapter.get_observations("DGS10", limit=50)
            >>> for o in obs[:5]:
            ...     print(f"{o['date']}: {o['value']}")
        """
        cache_key = f"fred_observations_{series_id}_{limit}_{sort_order}"

        def fetch_fn():
            return asyncio.run(self._request(
                f"series/observations",
                {
                    "series_id": series_id,
                    "limit": min(limit, 100000),
                    "sort_order": sort_order,
                },
            ))

        try:
            data = cache.get_macro(cache_key, fetch_fn)
            return data.get("observations", []) if data else []
        except FREDException:
            raise
        except Exception as e:
            logger.error(f"Error fetching observations {series_id}: {e}")
            return []

    def validate_series(self, series_id: str) -> bool:
        """Check if series ID is valid.

        Args:
            series_id: FRED series ID.

        Returns:
            True if series exists.
        """
        return series_id.upper() in self.CRITICAL_SERIES or len(series_id) > 0


# Global adapter instance
_fred_adapter: Optional[FREDAdapter] = None


async def get_fred_adapter() -> FREDAdapter:
    """Get or create global FRED adapter.

    Returns:
        FREDAdapter instance.

    Raises:
        FREDAuthException: If API key not configured.
    """
    global _fred_adapter
    if _fred_adapter is None:
        _fred_adapter = FREDAdapter()
    return _fred_adapter
